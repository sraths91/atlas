# ATLAS Fleet Monitoring — Developer Skills Guide

Domain knowledge, development patterns, and troubleshooting recipes for the ATLAS project.

---

## Table of Contents

1. [Adding a New Widget](#1-adding-a-new-widget)
2. [Adding a New Monitor](#2-adding-a-new-monitor)
3. [Adding a New API Route](#3-adding-a-new-api-route)
4. [Widget Catalog](#4-widget-catalog)
5. [Monitor Catalog](#5-monitor-catalog)
6. [API Route Map](#6-api-route-map)
7. [Fleet Server Routes](#7-fleet-server-routes)
8. [Authentication & Security](#8-authentication--security)
9. [Encryption](#9-encryption)
10. [Shared Styles & Utilities](#10-shared-styles--utilities)
11. [Widget Log Collector](#11-widget-log-collector)
12. [Fleet Agent Builder](#12-fleet-agent-builder)
13. [Configuration & Preferences](#13-configuration--preferences)
14. [Testing](#14-testing)
15. [Troubleshooting Recipes](#15-troubleshooting-recipes)
16. [macOS Kernel Safety](#16-macos-kernel-safety)

---

## 1. Adding a New Widget

### Step-by-step

1. **Create** `atlas/my_feature_widget.py`:

```python
from atlas.shared_styles import get_toast_css, get_toast_script, get_api_helpers_script

def get_my_feature_widget_html() -> str:
    return f'''<!DOCTYPE html>
<html><head>
<style>{get_toast_css()}
/* widget-specific styles */
</style>
</head><body>
<div id="widget-content">...</div>
<script>
{get_toast_script()}
{get_api_helpers_script()}
// widget logic — use apiFetch('/api/my-feature') for data
</script>
</body></html>'''
```

2. **Register** in `atlas/dashboard_preferences.py` → `WIDGET_REGISTRY`:

```python
"my-feature": {
    "name": "My Feature",
    "route": "/widget/my-feature",
    "default_size": "widget-span-1",   # or widget-span-2, widget-full-width
    "default_height": "450px",
    "category": "network",             # system|network|enterprise|security|hardware
    "description": "One-line description"
}
```

3. **Add route** in `atlas/routes/widget_routes.py`:

```python
elif path == '/widget/my-feature':
    from atlas.my_feature_widget import get_my_feature_widget_html
    return get_my_feature_widget_html()
```

4. **Add API endpoint** if needed (see [Adding a New API Route](#3-adding-a-new-api-route)).

### Lazy loading (for heavy widgets)

Use deferred import in widget_routes.py (already shown above). This avoids importing heavy dependencies at server startup.

### Size classes

| CSS Class | Grid Span | Use When |
|-----------|-----------|----------|
| `widget-span-1` | 1 column | Simple metric cards |
| `widget-span-2` | 2 columns | Charts, detailed tables |
| `widget-full-width` | Full row | Dashboards, multi-section views |

---

## 2. Adding a New Monitor

### Step-by-step

1. **Create** `atlas/my_feature_monitor.py` (or `atlas/network/monitors/my_feature.py` for network monitors):

```python
from atlas.core.logging import CSVLogger
import threading, time

class MyFeatureMonitor:
    def __init__(self):
        self.logger = CSVLogger("my_feature_data", retention_days=7)
        self.collection_interval = 60
        self._running = False
        self._thread = None

    def start(self, interval=None):
        if interval:
            self.collection_interval = interval
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run_loop(self):
        while self._running:
            try:
                self._collect()
            except Exception as e:
                pass
            time.sleep(self.collection_interval)

    def _collect(self):
        # Gather data, then log
        self.logger.write({'timestamp': ..., 'value': ...})

# Singleton factory
_instance = None
def get_my_feature_monitor() -> MyFeatureMonitor:
    global _instance
    if _instance is None:
        _instance = MyFeatureMonitor()
    return _instance
```

For **network monitors**, inherit from `BaseNetworkMonitor` (`atlas/network/monitors/base.py`) instead:

```python
from atlas.network.monitors.base import BaseNetworkMonitor

class MyNetworkMonitor(BaseNetworkMonitor):
    def get_monitor_name(self) -> str:
        return "my_network_monitor"

    def get_default_interval(self) -> int:
        return 60

    def _run_monitoring_cycle(self):
        # Collect and log data
        pass
```

2. **Start in** `atlas/live_widgets.py` (inside `start_monitoring()`):

```python
from atlas.my_feature_monitor import get_my_feature_monitor
monitor = get_my_feature_monitor()
monitor.start(interval=60)
```

3. **Add API endpoint** in `atlas/routes/api_routes.py` to expose data.

### Important: interval overrides

The interval passed to `start(interval=X)` in `live_widgets.py` **overrides** the monitor's default. Always check both locations when debugging timing.

---

## 3. Adding a New API Route

### GET endpoint

In `atlas/routes/api_routes.py` → `dispatch_get(handler, path)`:

```python
elif path == '/api/my-feature/status':
    from atlas.my_feature_monitor import get_my_feature_monitor
    monitor = get_my_feature_monitor()
    data = monitor.get_status()
    return json.dumps(data)
```

### POST endpoint

In `atlas/routes/api_routes.py` → `dispatch_post(handler, path, post_data)`:

```python
elif path == '/api/my-feature/configure':
    # post_data is already parsed dict
    result = configure_feature(post_data)
    return json.dumps({'success': True})
```

### Route ordering rule

More specific prefixes **must come before** generic ones:

```python
# CORRECT:
elif path.startswith('/api/wifi/events/export'):  # specific first
    ...
elif path.startswith('/api/wifi/export'):          # generic second
    ...
```

### Export endpoint pattern

Follow the existing export pattern for CSV/JSON with optional encryption:

```python
elif path == '/api/my-feature/export' or path.startswith('/api/my-feature/export'):
    if handler.command == 'POST':
        return _handle_encrypted_export(handler, post_data, 'my_feature')
    else:
        return _handle_export(handler, path, 'my_feature')
```

---

## 4. Widget Catalog

| Widget File | Function | Route | Registry ID |
|---|---|---|---|
| `system_monitor_widget.py` | `get_system_monitor_widget_html()` | `/widget/system-monitor` | `system-monitor` |
| `wifi_widget.py` | `get_wifi_widget_html()` | `/widget/wifi` | `wifi` |
| `speedtest_widget.py` | `get_speedtest_widget_html()` | `/widget/speedtest` | `speedtest` |
| `speedtest_widget.py` | `get_speedtest_history_widget_html()` | `/widget/speedtest-history` | `speedtest-history` |
| `ping_widget.py` | `get_ping_widget_html()` | `/widget/ping` | — |
| `process_widget.py` | `get_process_widget_html()` | `/widget/processes` | `processes` |
| `security_dashboard_widget.py` | `get_security_dashboard_widget_html()` | `/widget/security-dashboard` | `security-dashboard` |
| `vpn_status_widget.py` | `get_vpn_status_widget_html()` | `/widget/vpn-status` | `vpn-status` |
| `saas_health_widget.py` | `get_saas_health_widget_html()` | `/widget/saas-health` | `saas-health` |
| `network_quality_widget.py` | `get_network_quality_widget_html()` | `/widget/network-quality` | `network-quality` |
| `wifi_roaming_widget.py` | `get_wifi_roaming_widget_html()` | `/widget/wifi-roaming` | `wifi-roaming` |
| `power_widget.py` | `get_power_widget_html()` | `/widget/power` | `power` |
| `display_widget.py` | `get_display_widget_html()` | `/widget/display` | `display` |
| `peripherals_widget.py` | `get_peripherals_widget_html()` | `/widget/peripherals` | `peripherals` |
| `system_health_widget.py` | `get_system_health_widget_html()` | `/widget/system-health` | `system-health` |
| `disk_health_widget.py` | `get_disk_health_widget_html()` | `/widget/disk-health` | `disk-health` |
| `network_analysis_widget.py` | `get_network_analysis_widget_html()` | `/widget/network-analysis` | `network-analysis` |
| `network_testing_widget.py` | `get_network_testing_widget_html()` | `/widget/network-testing` | `network-testing` |
| `voip_quality_widget.py` | `get_voip_quality_widget_html()` | `/widget/voip-quality` | — |
| `connection_rate_widget.py` | `get_connection_rate_widget_html()` | `/widget/connection-rate` | — |
| `throughput_widget.py` | `get_throughput_widget_html()` | `/widget/throughput` | — |
| `tools_widget.py` | `get_tools_widget_html()` | `/widget/tools` | lazy |
| `network_path_widget.py` | `get_network_path_widget_html()` | `/widget/network-path` | lazy |
| `alert_rules_widget.py` | `get_alert_rules_widget_html()` | `/widget/alert-rules` | lazy |
| `trend_visualization_widget.py` | `get_trend_visualization_widget_html()` | `/widget/trends` | lazy |
| `machine_comparison_widget.py` | `get_machine_comparison_widget_html()` | `/widget/comparison` | lazy |

**Generated widgets** in `widget_html_generators.py`: `cpu`, `gpu`, `memory`, `disk`, `network`, `info`, `wifi-analyzer`, `wifi-analyzer-compact`, `speed-correlation`.

---

## 5. Monitor Catalog

### System monitors

| File | Factory | What it monitors | Interval | Log file |
|---|---|---|---|---|
| `peripheral_monitor.py` | `get_peripheral_monitor()` | USB, Bluetooth, Thunderbolt devices | 300s | peripherals CSV |
| `display_monitor.py` | `get_display_monitor()` | Displays, resolution, GPU, refresh rate | 300s | displays CSV |
| `power_monitor.py` | `get_power_monitor()` | Battery health, charge, thermal | 120s | power CSV |
| `security_monitor.py` | `get_security_monitor()` | Firewall, FileVault, Gatekeeper, XProtect | 300s | security CSV |
| `disk_health_monitor.py` | `get_disk_monitor()` | SMART data, disk capacity, wear | 300s | disk_health CSV |
| `application_monitor.py` | `get_app_monitor()` | App crashes, hangs, startup failures | 60s | crashes CSV |
| `software_inventory_monitor.py` | `get_software_monitor()` | Installed apps and versions | 3600s | software_inventory CSV |
| `process_monitor.py` | `get_process_monitor()` | Top processes by CPU/memory | 5s | process CSV |
| `system_monitor.py` | `get_system_monitor()` | CPU temp, load avg, uptime | 5s | in-memory only |

### Network monitors (`atlas/network/monitors/`)

| File | Factory | What it monitors | Interval | Log file |
|---|---|---|---|---|
| `ping.py` | `PingMonitor()` | Latency to 8.8.8.8, 1.1.1.1 | 10s | ping_latency CSV |
| `wifi.py` | `get_wifi_monitor()` | SSID, signal, channel, security | 60s | wifi_quality CSV |
| `speedtest.py` | `get_speed_test_monitor()` | Download/upload speed, jitter | 300s | speedtest CSV |
| `vpn_monitor.py` | `get_vpn_monitor()` | VPN connection, protocol, IP | 30s | vpn CSV |
| `saas_endpoint_monitor.py` | `get_saas_endpoint_monitor()` | SaaS endpoint reachability | 60s | saas_health CSV |
| `network_quality_monitor.py` | `get_network_quality_monitor()` | TCP/DNS/TLS/HTTP quality | 60s | network_quality CSV |
| `wifi_roaming_monitor.py` | `get_wifi_roaming_monitor()` | AP switches, roaming events | 30s | wifi_roaming CSV |

---

## 6. API Route Map

### System & health

| Route | Method | Purpose |
|---|---|---|
| `/api/system/comprehensive` | GET | All system metrics at once |
| `/api/system/pressure` | GET | Normalized pressure score (0-100) |
| `/api/system-health/overview` | GET | Multi-monitor health summary |
| `/api/health` | GET | Simple health check |
| `/api/stats` | GET | Current statistics |
| `/api/agent/health` | GET | Agent uptime, version, E2EE status |
| `/api/metrics/aggregated` | GET | Aggregated metrics (`?hours=&interval=`) |
| `/api/metrics/history` | GET | Raw metrics history (`?hours=&limit=`) |

### Pressure history

`/api/pressure/current`, `/api/pressure/history/10m`, `/1h`, `/24h`, `/7d`

### Speed test

| Route | Method | Purpose |
|---|---|---|
| `/api/speedtest` | GET | Last result |
| `/api/speedtest/history` | GET | All history |
| `/api/speedtest/mode` | GET/POST | Get/set mode (lite/full) |
| `/api/speedtest/run` | POST | Run quick test |
| `/api/speedtest/run-full` | POST | Run full test |
| `/api/speedtest/export` | GET/POST | Export (plain or encrypted) |

### Ping

| Route | Method | Purpose |
|---|---|---|
| `/api/ping` | GET | Last result |
| `/api/ping/stats` | GET | Aggregate stats |
| `/api/ping/history` | GET | History |
| `/api/ping/local-ip` | GET | Local IP |
| `/api/ping/export` | GET/POST | Export |

### WiFi

| Route | Method | Purpose |
|---|---|---|
| `/api/wifi` | GET | Current status |
| `/api/wifi/history` | GET | Quality history |
| `/api/wifi/diagnosis` | GET | Diagnostics |
| `/api/wifi/nearby` | GET | Nearby networks scan |
| `/api/wifi/channels` | GET | Channel utilization |
| `/api/wifi/spectrum` | GET | Spectrum data |
| `/api/wifi/signal/history/{period}` | GET | Signal timeline (10m/1h/24h/7d) |
| `/api/wifi/signal/current` | GET | Current signal |
| `/api/wifi/alias/*` | GET/POST | Network aliases (current, all, set, remove) |
| `/api/wifi/roaming` | GET | Roaming status |
| `/api/wifi/roaming/events` | GET | AP switch events (`?hours=&type=`) |
| `/api/wifi/roaming/sessions` | GET | Sessions |
| `/api/wifi/roaming/stats` | GET | Stats |
| `/api/wifi/roaming/timeline` | GET | Timeline |
| `/api/wifi/roaming/current` | GET | Current state |
| `/api/wifi/export` | GET/POST | Export WiFi data |
| `/api/wifi/events/export` | GET/POST | Export WiFi events |

### Network quality & testing

| Route | Method | Purpose |
|---|---|---|
| `/api/network/quality` | GET | Network quality (TCP/DNS/TLS/HTTP) |
| `/api/network/udp-quality` | GET | UDP jitter/loss |
| `/api/network/mos` | GET | VoIP Mean Opinion Score |
| `/api/network/path-summary` | GET | Traceroute summary |
| `/api/network/analysis` | GET | Deep analysis (`?hours=`) |
| `/api/network/analysis/latest` | GET | Latest analysis |
| `/api/network/analysis/settings` | GET/POST | Analysis settings |
| `/api/network/connection-test` | POST | TCP connection test |
| `/api/network/throughput-test` | POST | Throughput test |
| `/api/network/udp-test` | POST | UDP test |
| `/api/traceroute` | GET | Traceroute (`?target=&count=`) |
| `/api/traceroute/quick` | GET | Quick trace (`?target=`) |

### Speed correlation

`/api/speed-correlation/analysis`, `/data`, `/summary` — all GET, accept `?hours=`

### Hardware

| Route | Method | Purpose |
|---|---|---|
| `/api/display/status` | GET | Displays |
| `/api/power/status` | GET | Battery/power |
| `/api/peripherals/devices` | GET | USB/BT devices |
| `/api/security/status` | GET | macOS security |
| `/api/disk/health` | GET | Disk health |
| `/api/disk/status` | GET | Detailed disk info |
| `/api/software/inventory` | GET | Installed apps |
| `/api/applications/status` | GET | App crashes |

### Processes

| Route | Method | Purpose |
|---|---|---|
| `/api/processes` | GET | Top processes (`?sort=&limit=`) |
| `/api/processes/search` | GET | Search (`?q=`) |
| `/api/processes/problematic` | GET | Problem processes |
| `/api/processes/kill/:pid` | POST | Kill process |

### SaaS, tools, notifications

| Route | Method | Purpose |
|---|---|---|
| `/api/saas/health` | GET | Cloud service health |
| `/api/tools/status` | GET | Tool installation status |
| `/api/tools/licensing` | GET | License info |
| `/api/notifications/*` | GET/POST | Status, history, enable, disable, test |

### Alert rules (CRUD)

| Route | Method | Purpose |
|---|---|---|
| `/api/alerts/rules` | GET/POST | List/create rules |
| `/api/alerts/rules/:id` | GET | Get rule |
| `/api/alerts/rules/:id/update` | POST | Update |
| `/api/alerts/rules/:id/delete` | POST | Delete |
| `/api/alerts/rules/:id/toggle` | POST | Enable/disable |
| `/api/alerts/rules/reset` | POST | Reset to defaults |
| `/api/alerts/events` | GET | Alert events (`?rule_id=&severity=&hours=&limit=`) |
| `/api/alerts/events/:id/acknowledge` | POST | Ack event |
| `/api/alerts/statistics` | GET | Stats (`?hours=`) |
| `/api/alerts/email-config` | GET/POST | Email config |
| `/api/alerts/email-test` | POST | Test email |
| `/api/alerts/evaluate` | POST | Evaluate rules |
| `/api/alerts/cleanup` | POST | Clean old events |
| `/api/alerts/metrics` | GET | Available metrics |

### Dashboard layout

| Route | Method | Purpose |
|---|---|---|
| `/api/dashboard/layout` | GET/POST | Get/save layout |
| `/api/dashboard/layout/reset` | POST | Reset layout |
| `/api/dashboard/widgets` | GET | All widgets with states |

---

## 7. Fleet Server Routes

Fleet routes live in `atlas/fleet/server/routes/`:

| File | Prefix | Purpose |
|---|---|---|
| `auth_routes.py` | `/login`, `/logout`, `/api/auth/*` | Login, session management |
| `machine_routes.py` | `/api/fleet/machines*` | Machine registration, status, metrics |
| `agent_routes.py` | `/api/fleet/agents`, `/api/fleet/health`, `/api/fleet/widget-logs` | Agent heartbeat, widget log ingestion |
| `dashboard_routes.py` | `/fleet`, `/fleet/dashboard` | Fleet dashboard HTML pages |
| `admin_routes.py` | `/api/fleet/admin/*`, `/api/fleet/users/*` | User management, admin ops |
| `package_routes.py` | `/api/fleet/packages`, `/download/agent-*.pkg` | Installer downloads |
| `security_routes.py` | `/api/fleet/security`, `/api/fleet/audit-logs` | Audit trail |
| `analysis_routes.py` | `/api/fleet/analysis`, `/api/fleet/trends`, `/api/fleet/widget-logs` (GET) | Fleet-wide analysis, log queries |
| `cluster_routes.py` | `/api/fleet/cluster/*` | Multi-server clustering |
| `e2ee_routes.py` | `/api/fleet/e2ee/*` | Key exchange for E2EE |
| `ui_routes.py` | `/fleet/settings`, `/fleet/machines` | Fleet UI pages |

Routing hub: `atlas/fleet/server/router.py` dispatches to the correct route handler.

---

## 8. Authentication & Security

### Dashboard auth (`atlas/dashboard_auth.py`)

| Mode | Config Value | Mechanism |
|---|---|---|
| Simple password | `"simple"` | bcrypt hash, session cookies |
| Local macOS user | `"local"` | PAM authentication |
| TouchID | `"touchid"` | LocalAuthentication framework |
| Fleet users | `"users"` | Fleet user manager integration |
| Hybrid | `"hybrid"` | Local user + TouchID |

Config file: `~/.config/atlas-agent/dashboard_auth.json`

Session management: HttpOnly + SameSite=Strict cookies, configurable timeout (default 24h), CSRF tokens on POST.

### Fleet auth (`atlas/fleet/server/auth/`)

| Module | Purpose |
|---|---|
| `jwt_manager.py` | JWT tokens (RS256, HS256) |
| `oauth2_manager.py` | OAuth2 OIDC (Google, Microsoft, GitHub) |
| `api_key_manager.py` | API key generation/validation |
| `decorators.py` | `@require_auth`, `@require_role`, `@require_scope` |
| `middleware.py` | CORS, CSP, security headers |
| `audit_log.py` | Login attempts, role changes |
| `scopes.py` | Permission scopes (`machines:read`, `alerts:write`, `admin:*`) |
| `cli.py` | CLI user/key management |

### CSP (Content Security Policy)

Nonce-based: each response generates a random nonce, only `<script nonce="...">` blocks execute.

---

## 9. Encryption

### `atlas/encryption.py` — AES-256-GCM

```python
from atlas.encryption import DataEncryption

# With raw key
enc = DataEncryption(base64_key)
encrypted = enc.encrypt_payload({'sensitive': 'data'})
original = enc.decrypt_payload(encrypted)

# From password
key, salt = DataEncryption.derive_key_from_password("password")
enc = DataEncryption(key)

# Generate random key
key = DataEncryption.generate_key()
```

### Export encryption modes

| Mode | Layers | Use Case |
|---|---|---|
| `password` | AES-256-GCM with user password | Personal exports |
| `fleet_key` | AES inner + Fernet outer (agent key) | Fleet-auditable exports |

---

## 10. Shared Styles & Utilities

### `atlas/shared_styles.py` exports

| Function | Returns | Use |
|---|---|---|
| `get_toast_css()` | CSS | Toast notification styling |
| `get_toast_script()` | JS | `ToastManager.success/error/warning/info(msg)` |
| `get_api_helpers_script()` | JS | `apiFetch()`, `safeBool()`, `safeGet()`, constants |
| `get_accessibility_css()` | CSS | Skip links, sr-only, focus states |
| `get_loading_css()` | CSS | Skeleton loaders, spinners |

### JS constants (from `get_api_helpers_script()`)

```javascript
UPDATE_INTERVAL = { REALTIME: 2000, FREQUENT: 5000, STANDARD: 10000, RELAXED: 30000, RARE: 60000 }
THRESHOLDS = {
    QUALITY: { EXCELLENT: 95, GOOD: 80, FAIR: 60 },
    LATENCY: { EXCELLENT: 50, GOOD: 150, FAIR: 300 },
    TREND_MAX: { DNS: 100, TLS: 200, HTTP: 500 }
}
```

### Toast API

```javascript
ToastManager.success('Saved!');
ToastManager.error('Connection failed', 5000);
ToastManager.warning('Low battery');
ToastManager.info('Update available');
```

### `apiFetch(url, options)`

Returns `{ok: true, data: {...}}` or `{ok: false, error: "..."}`. Handles HTTP errors and JSON parsing automatically.

---

## 11. Widget Log Collector

### `atlas/widget_log_collector.py`

Collects widget events and sends to fleet server for central visibility.

```python
from atlas.widget_log_collector import log_widget_event

# Log an event (queued, sent in batches every ~300s)
log_widget_event('INFO', 'speedtest', 'Speed test completed', {
    'download_mbps': 150.5,
    'upload_mbps': 45.2
})
```

Fleet endpoint: `POST /api/fleet/widget-logs`
Query endpoint: `GET /api/fleet/widget-logs?widget_type=export&machine_id=X&limit=200`

Features: thread-safe ring buffer (max 1000), retry on failure, optional E2EE.

---

## 12. Fleet Agent Builder

### `atlas/fleet_agent_builder.py`

Builds `.pkg` installers for deploying agents to fleet machines.

| Method | Output | Install Location |
|---|---|---|
| `build_agent_package()` | `agent-X.X.X.pkg` | Menu bar agent + core daemon |
| `build_menubar_package()` | Menu bar `.pkg` | `~/Library/LaunchAgents/` |
| `build_fleet_server_package()` | Fleet server `.pkg` | `/Library/LaunchDaemons/` |

### Plist template variables

| Variable | Substituted With |
|---|---|
| `__PYTHON_PATH__` | Path to python3 |
| `__INSTALL_DIR__` | Agent install directory |
| `__ACTUAL_USER__` | macOS username |
| `__ACTUAL_HOME__` | User home directory |
| `__FLEET_PORT__` | Fleet server port (8778) |

### LaunchDaemon locations

| Plist | Type | Timing |
|---|---|---|
| `com.atlas.menubar.plist` | LaunchAgent | Login-time (user-owned) |
| `com.atlas.agent.daemon.plist` | LaunchDaemon | Boot-time (root:wheel) |
| `com.atlas.fleetserver.daemon.plist` | LaunchDaemon | Boot-time (root:wheel) |

---

## 13. Configuration & Preferences

### Dashboard layout (`atlas/dashboard_preferences.py`)

```python
from atlas.dashboard_preferences import DashboardPreferences

prefs = DashboardPreferences()
layout = prefs.get_layout()       # {order: [...], hidden: [...], sizes: {...}, heights: {...}}
prefs.update_layout(new_layout)   # Save changes
prefs.reset_to_default()          # Reset
visible = prefs.get_visible_widgets()      # Ordered visible widgets
all_widgets = prefs.get_all_widgets_with_state()  # All with visibility state
```

Persisted to: `~/.config/atlas-agent/dashboard_layout.json`

### `WIDGET_REGISTRY` structure

```python
WIDGET_REGISTRY = {
    "widget-id": {
        "name": "Display Name",
        "route": "/widget/widget-id",
        "default_size": "widget-span-1",
        "default_height": "450px",
        "category": "system",
        "description": "What it does"
    }
}
```

### Categories

`system`, `network`, `enterprise`, `security`, `hardware`

---

## 14. Testing

### Structure

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Fast, isolated
├── integration/         # Multi-component
└── security/            # Vulnerability scans
```

### Commands

```bash
pytest tests/                          # All tests
pytest tests/unit/                     # Unit only
pytest -m "not slow"                   # Skip slow
pytest -m "security"                   # Security only
pytest -v tests/unit/test_auth.py      # Specific file, verbose
```

### Markers

`@pytest.mark.unit`, `.integration`, `.security`, `.performance`, `.e2e`, `.slow`

### Key fixtures (conftest.py)

| Fixture | Provides |
|---|---|
| `temp_dir` | Auto-cleanup temp directory |
| `sample_machine_info` | Mock machine info dict |
| `sample_metrics` | Mock system metrics dict |
| `fleet_data_store` | Test FleetDataStore instance |
| `retry_config` | Retry policy config |
| `circuit_breaker_config` | Circuit breaker config |

---

## 15. Troubleshooting Recipes

### Widget stuck loading / API hangs

**Symptom**: Widget shows spinner indefinitely.
**Cause**: Blocking subprocess call in the BaseHTTPRequestHandler thread.
**Fix**: Wrap the blocking call in a daemon thread with `join(timeout=N)`:

```python
import threading
t = threading.Thread(target=blocking_func, daemon=True)
t.start()
t.join(timeout=10)
if t.is_alive():
    logger.warning("Timed out")
```

### `ModuleNotFoundError: No module named 'rumps'`

**Cause**: `from atlas.menubar_agent import start_menubar_app` at top level.
**Fix**: Defer import to inside the `else` branch of the `--no-menubar` check in `start_atlas_agent.py`.

### `airport` binary not found errors

**Cause**: Apple removed `/System/Library/PrivateFrameworks/Apple80211.framework/.../airport` in macOS 14.4+.
**Fix**: Guard with `Path(AIRPORT_BIN).exists()` check. Use `system_profiler SPAirPortDataType` as alternative (with caching).

### `safe_int_param` import syntax errors

**Cause**: Placing import inside multi-line `from X import (a, b, c)` blocks.
**Fix**: Always use a standalone import line:

```python
from atlas.config.defaults import safe_int_param
```

### CSV logs disappearing after restart

**Not a bug**: `CSVLogger.__init__()` calls `_cleanup_old_logs()` which removes entries older than `retention_days` (default 7). Logs within 7 days survive reboots.

### High kernel stress / potential kernel panics

See [macOS Kernel Safety](#16-macos-kernel-safety).

---

## 16. macOS Kernel Safety

### The problem

`system_profiler` walks the IOKit device tree, stressing kernel drivers. Frequent calls (every 5-30s) can destabilize macOS, especially on Apple Silicon.

### Current safeguards

| Monitor | Old Interval | New Interval | Mitigation |
|---|---|---|---|
| Peripheral (3x system_profiler) | 30s | 300s | Reduced frequency |
| WiFi (SPAirPortDataType) | 10s | 60s | 55s response cache |
| Power (SPPowerDataType) | 60s | 120s | 10-minute response cache |
| Ping | 5s | 10s | Reduced frequency |
| WiFi roaming (airport) | 5s | 30s | `_airport_available` guard |
| GPU (ioreg) | Every call | 10s cache | In-memory cache |

### Rules for new monitors

1. **Never** call `system_profiler` more than once per 60 seconds
2. **Always** cache `system_profiler` output (TTL just under the polling interval)
3. **Never** call `ioreg` without caching (minimum 10s)
4. **Guard** against missing binaries with `Path(...).exists()` before use
5. **Wrap** external commands in threads with timeouts to prevent HTTP handler blocking
6. **Prefer** lightweight alternatives: `sysctl` > `ioreg` > `system_profiler`

### Kernel-heavy calls to avoid at high frequency

| Command | Kernel Impact | Safe Interval |
|---|---|---|
| `system_profiler SPUSBDataType` | High (IOKit USB tree) | 300s+ |
| `system_profiler SPBluetoothDataType` | High (IOKit BT tree) | 300s+ |
| `system_profiler SPThunderboltDataType` | High (IOKit TB tree) | 300s+ |
| `system_profiler SPAirPortDataType` | Medium (WiFi driver) | 60s+ |
| `system_profiler SPPowerDataType` | Medium (power driver) | 120s+ |
| `ioreg -c IOAccelerator` | Medium (GPU driver) | 10s+ |
| `airport -I` / `airport -s` | Low (removed in 14.4+) | Guard existence |
