# ATLAS Fleet Monitoring Dashboard

Enterprise macOS fleet monitoring platform with real-time dashboards, network analysis, and remote agent management.

## Quick Start

```bash
# Install dependencies
pip3 install --user psutil requests cryptography bcrypt rumps PyJWT

# Start agent dashboard (port 8767)
python3 start_atlas_agent.py --no-menubar --port 8767

# Start fleet server (port 8778)
bash start_fleet_server.sh
```

## Architecture

Two services, both using `BaseHTTPRequestHandler`:

| Service | Port | Entry Point | Purpose |
|---------|------|-------------|---------|
| Agent Dashboard | 8767 | `start_atlas_agent.py` → `atlas/live_widgets.py` | Per-machine monitoring UI |
| Fleet Server | 8778 | `atlas/fleet_server.py` | Central fleet management |

### Request Flow

```
Browser → live_widgets.py (port 8767)
  ├─ /widget/* → atlas/routes/widget_routes.py (HTML pages)
  ├─ /api/*    → atlas/routes/api_routes.py    (JSON GET+POST)
  └─ /login    → atlas/dashboard_auth.py       (authentication)
```

### Key Directories

```
atlas/
├── core/logging.py              # CSVLogger (all monitors use this)
├── routes/
│   ├── api_routes.py            # All API endpoints (GET+POST)
│   └── widget_routes.py         # Widget HTML page routes
├── network/monitors/
│   ├── base.py                  # BaseNetworkMonitor abstract class
│   ├── wifi.py                  # WiFi quality (60s interval)
│   ├── ping.py                  # Ping latency (10s interval)
│   ├── speedtest.py             # Speed tests (300s interval)
│   ├── vpn_monitor.py           # VPN health (30s interval)
│   ├── saas_endpoint_monitor.py # SaaS health (60s interval)
│   ├── network_quality_monitor.py # TCP/DNS/TLS/HTTP (60s)
│   ├── wifi_roaming_monitor.py  # AP roaming (30s interval)
│   └── [tcp, udp, throughput testers]
├── fleet/server/                # Fleet server modules
│   ├── auth/                    # JWT, OAuth2, API keys, RBAC
│   ├── routes/                  # Fleet API routes
│   └── data_store.py            # Fleet data persistence
├── *_widget.py                  # 25+ widget HTML generators
├── *_monitor.py                 # System monitors (power, display, etc.)
├── dashboard_preferences.py     # WIDGET_REGISTRY + WidgetConfig
├── shared_styles.py             # Shared CSS/JS (toast, a11y)
├── encryption.py                # AES-256-GCM E2EE
├── fleet_agent_builder.py       # .pkg installer builder
└── fleet_settings_page.py       # Fleet settings UI
```

## Critical Patterns

### 1. Widget Pattern
Each widget is a standalone `*_widget.py` file exporting `get_*_widget_html()`.
Widgets are registered in `WIDGET_REGISTRY` in `atlas/dashboard_preferences.py`.

### 2. Monitor Pattern
All network monitors inherit from `BaseNetworkMonitor` (`atlas/network/monitors/base.py`):
- Implement `_run_monitoring_cycle()` and `get_monitor_name()`
- Override `get_default_interval()` for custom timing
- All are singletons via `get_*_monitor()` factory functions
- Log to CSV via `CSVLogger` from `atlas/core/logging.py`

**Important**: Monitor intervals in `live_widgets.py` override the monitor defaults.
Check both the monitor's `get_default_interval()` AND the `start(interval=X)` call in `live_widgets.py`.

### 3. Route Matching
Routes use `path == '/api/...'` and `path.startswith('/api/...')` in `api_routes.py`.
**Order matters**: more specific prefixes must come first.
Example: `/api/wifi/events/export` must appear before `/api/wifi/export`.

### 4. CSV Logging
`CSVLogger` (atlas/core/logging.py):
- Thread-safe CSV writes with in-memory ring buffer
- Automatic cleanup of entries older than `retention_days` (default 7)
- Cleanup runs on every `__init__` (i.e., on agent restart)
- ~50 CSV files across all monitors in `~/`, `~/.atlas_agent/data/`, and `~/Library/Application Support/AtlasAgent/data/`

### 5. Singleton Services
All monitors and managers use singleton pattern:
```python
_instance = None
def get_foo_monitor() -> FooMonitor:
    global _instance
    if _instance is None:
        _instance = FooMonitor()
    return _instance
```

## Known Pitfalls

1. **`safe_int_param` import**: Must NOT be placed inside multi-line import blocks. Put it on its own import line.

2. **macOS `airport` binary removed**: Apple removed `/System/Library/PrivateFrameworks/Apple80211.framework/.../airport` in macOS 14.4+. The `wifi_roaming_monitor.py` guards against this with `_airport_available` check. WiFi monitor uses `system_profiler SPAirPortDataType` (cached) instead.

3. **Kernel stress from monitors**: `system_profiler` calls walk the IOKit device tree and can stress the kernel. All `system_profiler` calls are now rate-limited:
   - Peripheral monitor: 300s interval (was 30s)
   - WiFi monitor: 60s with response caching
   - Power monitor: 120s with 10-minute `SPPowerDataType` cache
   - GPU `ioreg` calls: 10s cache in system_monitor.py

4. **Traceroute blocks HTTP handler**: `network_analyzer.py` `_capture_traceroute()` runs in a thread with 10s timeout to avoid blocking the synchronous BaseHTTPRequestHandler.

5. **`start_atlas_agent.py` menubar import**: `from atlas.menubar_agent import start_menubar_app` is deferred to the `else` branch (when `--no-menubar` is NOT set) because `rumps` may not be installed.

6. **Fleet agent builder plist locations**:
   - Menubar agent → `~/Library/LaunchAgents/` (login-time, user-owned)
   - Core agent daemon → `/Library/LaunchDaemons/` (boot-time, root:wheel)
   - Fleet server daemon → `/Library/LaunchDaemons/` (boot-time, root:wheel)

## Monitor Intervals (Current)

| Monitor | Interval | Config Location |
|---------|----------|-----------------|
| Ping | 10s | `live_widgets.py:728` overrides `ping.py:62` |
| WiFi Quality | 60s | `live_widgets.py:733` overrides `wifi.py:381` |
| WiFi Diagnosis | 120s | `wifi.py:325` |
| WiFi Roaming Monitor | 30s | `wifi_roaming_monitor.py:30` |
| WiFi Roaming Tracker | 60s | `wifi_roaming.py:83` |
| Speed Test | 60s | `speedtest.py` (configurable) |
| VPN | 30s | `vpn_monitor.py` |
| SaaS Health | 60s | `saas_endpoint_monitor.py` |
| Network Quality | 60s | `network_quality_monitor.py` |
| Power | 120s | `power_monitor.py:210` |
| Peripheral | 300s | `peripheral_monitor.py:121` |
| Display | 300s | `display_monitor.py:562` |
| Security | 300s | `security_monitor.py` |
| Disk Health | 300s | `disk_health_monitor.py` |
| Application | 60s | `application_monitor.py` |
| Software Inventory | 3600s | `software_inventory_monitor.py` |
| Fleet Agent Reports | 10s | `fleet_agent.py` |

## Security Architecture

- **Dashboard auth**: Optional password, local macOS user, or TouchID (`atlas/dashboard_auth.py`)
- **Fleet auth**: JWT + OAuth2 + API keys with RBAC (`atlas/fleet/server/auth/`)
- **Encryption**: AES-256-GCM for agent↔server E2EE (`atlas/encryption.py`)
- **Passwords**: bcrypt (12 rounds), SHA-256 fallback
- **Sessions**: HttpOnly, SameSite cookies, configurable timeout
- **CSRF**: Token-based protection on POST endpoints
- **CSP**: Nonce-based Content Security Policy

## Testing

```bash
# Run all tests
pytest tests/

# By category
pytest tests/unit/
pytest tests/integration/
pytest tests/security/

# Markers: @pytest.mark.unit, .integration, .security, .performance, .slow
```

## Workflow: Commit After Every Change

**After each feature, fix, or improvement is tested and verified, immediately commit and push to GitHub.**

1. Verify the change works (restart agent, test endpoints, check HTML generation)
2. `git add <specific files>` — only stage the files you changed
3. `git commit -m "type: description"` — use conventional commits (feat/fix/refactor/docs)
4. `git push origin main`

Do NOT batch multiple unrelated changes into one large commit. Each logical change gets its own commit. This ensures:
- Every working state is preserved in git history
- Changes can be individually reverted if something breaks
- The commit log tells a clear story of what was built and when

## LaunchDaemon Plist Templates

Template variables substituted at install time:
- `__PYTHON_PATH__` — path to python3
- `__INSTALL_DIR__` — agent installation directory
- `__ACTUAL_USER__` — macOS username
- `__ACTUAL_HOME__` — user home directory
- `__FLEET_PORT__` — fleet server port

## Dependencies

```
psutil>=5.9.0       # System monitoring (CPU, memory, disk, network)
cryptography>=41.0.0 # AES-256-GCM encryption
bcrypt>=4.0.0       # Password hashing
PyJWT>=2.8.0        # JWT token auth
rumps>=0.4.0        # macOS menu bar (optional, only for GUI mode)
requests            # HTTP client for fleet communication
Pillow>=9.0.0       # Image processing
matplotlib>=3.5.0   # Charting
```
