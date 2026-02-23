# ATLAS Agent - Feature Comparison

## Overview

ATLAS (Advanced Telemetry & Live Analysis System) is an enterprise-grade system monitoring agent for macOS. It provides comprehensive monitoring, advanced network analysis, and flexible deployment options.

---

## Installation Modes

ATLAS supports three installation modes to fit different use cases:

### 1. **Standalone Mode**
*Perfect for individual users, home labs, and local monitoring*

- ✅ No server required
- ✅ All features work locally
- ✅ Zero configuration needed
- ✅ Private - no data leaves your machine
- ✅ Can upgrade to fleet mode later

### 2. **Fleet Mode**
*For organizations managing multiple machines*

- ✅ All standalone features PLUS
- ✅ Central dashboard for all machines
- ✅ Remote command execution
- ✅ Aggregated metrics and reporting
- ✅ Fleet-wide network analysis
- ✅ Multi-machine comparisons

### 3. **Hybrid Mode** (Recommended)
*Best of both worlds*

- ✅ Works offline (standalone features)
- ✅ Reports to fleet when online
- ✅ Local dashboard always available
- ✅ Automatic failover
- ✅ Local data cache when disconnected

---

## Feature Matrix

| Feature | Standalone | Fleet | Hybrid |
|---------|------------|-------|--------|
| **MONITORING** | | | |
| Real-Time CPU Monitoring | ✅ | ✅ | ✅ |
| Memory Monitoring | ✅ | ✅ | ✅ |
| Disk I/O Monitoring | ✅ | ✅ | ✅ |
| Network Monitoring | ✅ | ✅ | ✅ |
| Process Monitoring | ✅ | ✅ | ✅ |
| Battery Monitoring (macOS) | ✅ | ✅ | ✅ |
| Temperature Monitoring (macOS) | ✅ | ✅ | ✅ |
| | | | |
| **NETWORK ANALYSIS** | | | |
| WiFi Quality Tracking | ✅ | ✅ | ✅ |
| Speed Test Automation | ✅ | ✅ | ✅ |
| Ping Monitoring | ✅ | ✅ | ✅ |
| Network Diagnostics | ✅ | ✅ | ✅ |
| **Root Cause Analysis** | ✅ | ✅ | ✅ |
| Slowdown Detection | ✅ | ✅ | ✅ |
| Before/During Comparisons | ✅ | ✅ | ✅ |
| Trigger Identification | ✅ | ✅ | ✅ |
| Actionable Recommendations | ✅ | ✅ | ✅ |
| | | | |
| **DASHBOARDS** | | | |
| Local Web Dashboard | ✅ | ✅ | ✅ |
| Feature Homepage | ✅ | ✅ | ✅ |
| Help & Documentation | ✅ | ✅ | ✅ |
| Real-Time Widgets | ✅ | ✅ | ✅ |
| Network Analysis Widget | ✅ | ✅ | ✅ |
| Fleet Central Dashboard | ❌ | ✅ | ✅ (when online) |
| Multi-Machine View | ❌ | ✅ | ✅ (when online) |
| | | | |
| **DATA MANAGEMENT** | | | |
| 7-Day Local Retention | ✅ | ✅ | ✅ |
| CSV Exports | ✅ | ✅ | ✅ |
| JSON API Access | ✅ | ✅ | ✅ |
| Export Time Ranges (1h, 24h, All) | ✅ | ✅ | ✅ |
| 4 Export Data Types | ✅ | ✅ | ✅ |
| Auto Cleanup | ✅ | ✅ | ✅ |
| Central Storage | ❌ | ✅ | ✅ (when online) |
| | | | |
| **USER INTERFACE** | | | |
| macOS Menu Bar App | ✅ | ✅ | ✅ |
| Quick Stats Display | ✅ | ✅ | ✅ |
| Quick Actions Menu | ✅ | ✅ | ✅ |
| Status Indicators | ✅ | ✅ | ✅ |
| Notifications | ✅ | ✅ | ✅ |
| | | | |
| **FLEET MANAGEMENT** | | | |
| Fleet Reporting | ❌ | ✅ | ✅ (when online) |
| Remote Commands | ❌ | ✅ | ✅ (when online) |
| Fleet Health Monitoring | ❌ | ✅ | ✅ (when online) |
| E2EE Encryption | ❌ | ✅ | ✅ |
| Certificate Management | ❌ | ✅ | ✅ |
| | | | |
| **ADVANCED FEATURES** | | | |
| Network Analysis Tool | ✅ | ✅ | ✅ |
| Process Kill Capability | ✅ | ✅ | ✅ |
| Custom Thresholds | ✅ | ✅ | ✅ |
| Custom Alerts | ✅ | ✅ | ✅ |
| Plugin System | Planned | Planned | Planned |

---

## Unique Features

### 🔍 Network Analysis Tool
**The most powerful feature in ATLAS** - No other monitoring tool offers this.

- **Automatic slowdown detection**: Identifies network issues from speed test patterns
- **Root cause analysis**: Correlates 5 data sources to explain WHY internet is slow
- **Before/During comparison**: Shows what changed right before the slowdown
- **Trigger identification**: Highlights events in the 2 minutes before issues
- **Actionable recommendations**: Specific advice, not generic troubleshooting

**Example Analysis Output**:
```
WiFi slowdown detected from 2024-01-01 08:15 to 08:42 (27 minutes).

LIKELY TRIGGERS:
 📶 WiFi signal degraded (dropped from -55 to -72 dBm)
 📡 Wireless interference increased (SNR dropped from 45 to 23 dB)

RECOMMENDATIONS:
 • Move closer to your WiFi router or access point
 • Change WiFi channel to reduce interference (try channels 1, 6, or 11)
 • Consider switching to 5GHz band if available
```

### 📊 Comprehensive Export System

Export your data for external analysis:

- **4 data types**: Speed Tests, Ping Tests, WiFi Quality, WiFi Events
- **3 time ranges**: Last 1 Hour, Last 24 Hours, All Data (7 days)
- **12 combinations** total
- **CSV format**: Compatible with Excel, Google Sheets, pandas
- **One-click access**: Via dashboard hamburger menu

### 💾 Smart 7-Day Retention

Perfect balance of history and disk space:

- **Automatic cleanup**: No manual maintenance required
- **Efficient storage**: ~50-100MB for full 7 days
- **Trend analysis**: Enough history to identify patterns
- **Privacy-focused**: All data stored locally, never cloud

### 🎯 Feature Discovery Homepage

Professional landing page that showcases all capabilities:

- **Organized by category**: Real-Time Monitoring, Network Analysis, Data Management
- **Interactive cards**: Click to navigate to any feature
- **Status indicators**: See agent health at a glance
- **Quick actions**: Direct links to most-used features

### 📚 Built-in Help System

Comprehensive documentation accessible at `http://localhost:8767/help`:

- **Feature highlights**: Discover advanced capabilities
- **Quick start guide**: 5-step getting started
- **FAQ section**: 9 common questions answered
- **Examples**: Real-world use cases and outputs

---

## Comparison with Other Tools

| Feature | ATLAS | Activity Monitor | iStat Menus | Commercial Tools |
|---------|-------|------------------|-------------|------------------|
| **Price** | Free | Free | $11.99 | $50-500/year |
| **Network Root Cause Analysis** | ✅ | ❌ | ❌ | ❌ |
| **WiFi Quality Monitoring** | ✅ | ❌ | ✅ | Some |
| **Speed Test Automation** | ✅ | ❌ | ❌ | Some |
| **CSV Data Export** | ✅ | ❌ | ❌ | Some |
| **Local Dashboard** | ✅ | N/A | N/A | Some |
| **Fleet Management** | ✅ | ❌ | ❌ | ✅ |
| **Open Source** | ✅ | ❌ | ❌ | ❌ |
| **No Cloud Required** | ✅ | ✅ | ✅ | ❌ |
| **macOS Menu Bar** | ✅ | ✅ | ✅ | ✅ |
| **Process Management** | ✅ | ✅ | ✅ | ✅ |

---

## System Requirements

### Minimum Requirements

- **OS**: macOS 11.0 (Big Sur) or later
- **RAM**: 100 MB
- **Disk**: 200 MB (including 7 days of data)
- **Python**: 3.8+ (bundled with macOS)
- **Network**: None (for standalone mode)

### Recommended

- **OS**: macOS 13.0 (Ventura) or later
- **RAM**: 200 MB
- **Disk**: 500 MB
- **Python**: 3.10+
- **Network**: 10+ Mbps for speed tests

---

## Installation Guide

### Quick Start (Standalone Mode)

1. Download `atlas-standalone-agent.pkg`
2. Double-click to install
3. Follow setup wizard
4. Open http://localhost:8767

**That's it!** No configuration needed.

### Fleet Mode Setup

1. Install ATLAS agent (same as standalone)
2. Run setup wizard and provide:
   - Fleet server URL
   - API key (from fleet admin)
   - Optional: Encryption key (for E2EE)
3. Agent automatically connects and reports

### Hybrid Mode (Recommended)

Same as Fleet Mode - hybrid is automatic! The agent will:
- Work offline using local features
- Report to fleet when server is reachable
- Seamlessly switch between modes

---

## What's Included in Each Package?

### Standalone Package

```
atlas-standalone-agent.pkg
├── ATLAS Agent (1,088 lines)
│   ├── System monitoring
│   ├── Network monitoring
│   ├── Widget integrations
│   └── Local storage
├── Local Dashboard Server (1,840 lines)
│   ├── Feature homepage
│   ├── Help system
│   ├── Real-time widgets
│   └── Export functionality
├── Menu Bar App (345 lines)
│   ├── Quick stats
│   ├── Status indicator
│   └── Quick actions
├── Network Analysis Tool (1,175 lines)
│   ├── Root cause analysis
│   ├── 5-source correlation
│   └── Recommendation engine
└── Setup Wizard
    ├── Auto-configuration
    ├── Preference selection
    └── Launch on startup
```

### Fleet Package

Everything in Standalone PLUS:
- Fleet server credentials
- E2EE encryption setup
- Fleet dashboard access
- Remote command capability
- Auto-enrollment

---

## FAQ

### Can I upgrade from Standalone to Fleet mode?

**Yes!** Simply run the configuration tool:

```bash
python3 update_fleet_config.py
```

Enter your fleet server URL and API key. No reinstall needed.

### Does Standalone mode have all features?

**Yes!** Standalone has 100% feature parity with Fleet for local monitoring. The only differences are fleet management features (central dashboard, remote commands, multi-machine view).

### How much data does it store?

**~50-100MB** for 7 days of monitoring data. This includes:
- System metrics (CPU, memory, disk, network)
- WiFi quality logs
- Speed test results
- Ping test results
- Network diagnostic data
- WiFi event logs

### Can I run both local and fleet dashboards?

**Yes!** In fleet/hybrid mode:
- **Local dashboard**: http://localhost:8767 (always available)
- **Fleet dashboard**: https://your-fleet-server/dashboard (when online)

Both show the same data, but fleet dashboard adds multi-machine views.

### Is my data sent to any cloud service?

**No.** In standalone mode, all data stays on your machine. Even in fleet mode, data only goes to YOUR fleet server (which you control). No third-party cloud services are used.

### Can I customize the monitoring thresholds?

**Yes!** You can customize network analysis thresholds via:

1. **Network Analysis Widget** - Click the Settings (⚙️) button to adjust:
   - Slow download threshold (default: 20 Mbps)
   - Slow upload threshold (default: 5 Mbps)
   - High ping threshold (default: 100 ms)
   - Consecutive slow test count (default: 3)

2. **API** - `POST /api/network/analysis/settings` with JSON body

3. **Config file** - Edit `~/.config/atlas-agent/network_analysis_settings.json`

For gigabit connections, you might set the slow download threshold to 100+ Mbps.

### Can I create custom alert rules?

**Yes!** ATLAS includes a powerful custom alert rules system:

1. **Alert Rules Widget** - Visit http://localhost:8767/widget/alert-rules to:
   - Create custom rules for any metric (CPU, memory, disk, temperature, network, etc.)
   - Set severity levels (info, warning, critical)
   - Configure notification channels (system, webhook, email)
   - View alert history and statistics
   - Reset to default rules

2. **Supported Metrics**:
   - CPU, GPU, Memory, Disk usage (%)
   - Temperature (°C), Battery (%)
   - Network upload/download (KB/s)
   - Download/Upload speed (Mbps)
   - Ping (ms), Packet loss (%)

3. **Notification Channels**:
   - **System**: Native macOS/Linux notifications
   - **Webhook**: Send alerts to Slack, Discord, or custom endpoints
   - **Email**: SMTP-based email notifications

4. **API Endpoints**:
   - `GET /api/alerts/rules` - List all rules
   - `POST /api/alerts/rules` - Create a new rule
   - `POST /api/alerts/rules/{id}/update` - Update a rule
   - `POST /api/alerts/rules/{id}/delete` - Delete a rule
   - `GET /api/alerts/events` - View alert history
   - `GET /api/alerts/statistics` - Get alert statistics

### How do I protect my dashboard with a password?

ATLAS supports multiple authentication methods:

1. **Simple Password** (recommended for single user):
   ```bash
   export ATLAS_DASHBOARD_PASSWORD="your-secure-password"
   ```

2. **Username/Password** (uses fleet user management):
   ```bash
   export ATLAS_DASHBOARD_AUTH_MODE="users"
   ```

3. **TouchID** (macOS only):
   ```bash
   export ATLAS_DASHBOARD_AUTH_MODE="touchid"
   ```

4. **Hybrid** (username/password + optional TouchID):
   ```bash
   export ATLAS_DASHBOARD_AUTH_MODE="hybrid"
   ```

Or configure via the API:
```bash
curl -X POST http://localhost:8767/api/auth/configure \
  -H "Content-Type: application/json" \
  -d '{"auth_mode": "simple", "password": "your-password"}'
```

### What makes the Network Analysis tool unique?

**No other tool does this.** ATLAS correlates multiple data sources (speed tests, WiFi quality, ping tests, network diagnostics, events) to identify:
- What changed right before slowdowns
- The root cause of network issues
- Specific recommendations to fix problems

Most tools just show you that your internet is slow. ATLAS tells you WHY.

---

## Getting Help

- **Built-in Help**: http://localhost:8767/help
- **API Documentation**: http://localhost:8767/api/system/comprehensive
- **GitHub Issues**: Report bugs and request features
- **Community**: Share tips and get support

---

## Roadmap

### Future (v2.0)
- ML-based anomaly detection
- Plugin architecture
- Cloud export (S3, GCS)

## Recently Completed

### v1.1 Features (Implemented)
- **Trend Visualization** - Interactive 7-day charts at `/widget/trends`
- **Multi-Machine Comparison** - Fleet comparison at `/widget/comparison`
- **Custom Alert Rules** - Create/edit rules at `/widget/alert-rules`
- **Dashboard Authentication** - Password, username/password, or TouchID protection
- **Email Notifications** - SMTP-based alert delivery
- **Webhook Notifications** - Send alerts to Slack, Discord, etc.

---

## License

MIT License - Free for personal and commercial use.

---

## Credits

**ATLAS Agent** - Enterprise-grade monitoring for everyone.

Built with ❤️ for the macOS community.
