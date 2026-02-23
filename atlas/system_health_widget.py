"""
System Health Widget - Dashboard widget showing overview of all monitor statuses

Also provides backend health-score functions (previously in health_widget.py):
- get_system_health(): uptime, load averages, health score
- calculate_health_score(): 0-100 score based on CPU, memory, disk, load
- get_cached_cpu_percent(): cached psutil.cpu_percent() to avoid blocking
"""
import psutil
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration: Health Score Thresholds
# =============================================================================
# Each tuple is (threshold_percent, penalty_points).
# Thresholds are checked in order - first match wins.
# Max penalty per category: CPU=30, Memory=30, Disk=20, Load=20 -> total 100.
CPU_THRESHOLDS = [(90, 30), (70, 20), (50, 10)]
MEMORY_THRESHOLDS = [(90, 30), (75, 20), (60, 10)]
DISK_THRESHOLDS = [(95, 20), (85, 10), (75, 5)]
LOAD_THRESHOLDS = [(2.0, 20), (1.5, 10), (1.0, 5)]  # normalized to CPU count

# Overall status mapping: (min_score, label, color_hex).
# Checked in order - first threshold the score meets wins.
STATUS_THRESHOLDS = [
    (80, "Healthy", "#00ff64"),
    (60, "Good", "#ffc800"),
    (40, "Fair", "#ff6400"),
    (0, "Poor", "#ff3000"),
]

# CPU metrics cache to avoid blocking calls
_cpu_cache: Dict[str, Any] = {
    'value': 0.0,
    'timestamp': 0.0,
    'ttl': 1.0  # Cache for 1 second
}


def get_cached_cpu_percent() -> float:
    """
    Get CPU percentage with caching to avoid blocking calls.

    Uses psutil.cpu_percent(interval=0.1) which blocks for 100ms,
    but caches the result for 1 second to avoid repeated blocking calls.
    """
    global _cpu_cache
    current_time = time.time()

    if current_time - _cpu_cache['timestamp'] < _cpu_cache['ttl']:
        return _cpu_cache['value']

    try:
        cpu_value = psutil.cpu_percent(interval=0.1)
        _cpu_cache['value'] = cpu_value
        _cpu_cache['timestamp'] = current_time
        return cpu_value
    except Exception as e:
        logger.warning(f"Failed to get CPU percent: {e}, using cached value")
        return _cpu_cache['value']


def calculate_health_score() -> int:
    """Calculate overall system health score (0-100) based on CPU, memory, disk, and load."""
    try:
        score = 100

        cpu_percent = get_cached_cpu_percent()
        for threshold, penalty in CPU_THRESHOLDS:
            if cpu_percent > threshold:
                score -= penalty
                break

        memory = psutil.virtual_memory()
        for threshold, penalty in MEMORY_THRESHOLDS:
            if memory.percent > threshold:
                score -= penalty
                break

        try:
            disk = None
            for mount_point in ['/', '/System/Volumes/Data', '/Volumes/Macintosh HD']:
                try:
                    disk = psutil.disk_usage(mount_point)
                    break
                except (PermissionError, FileNotFoundError):
                    continue
            if disk:
                for threshold, penalty in DISK_THRESHOLDS:
                    if disk.percent > threshold:
                        score -= penalty
                        break
        except Exception as e:
            logger.warning(f"Failed to get disk usage: {e}")

        try:
            load_avg = psutil.getloadavg()
            cpu_count = psutil.cpu_count()
            normalized_load = load_avg[0] / cpu_count if cpu_count > 0 else 0
            for threshold, penalty in LOAD_THRESHOLDS:
                if normalized_load > threshold:
                    score -= penalty
                    break
        except (AttributeError, OSError):
            pass

        return max(0, min(100, score))

    except Exception as e:
        logger.error(f"Failed to calculate health score: {e}")
        return 50


def get_system_health() -> Dict[str, Any]:
    """Get system health and uptime information."""
    try:
        boot_timestamp = psutil.boot_time()
        boot_time = datetime.fromtimestamp(boot_timestamp)

        uptime_seconds = time.time() - boot_timestamp
        uptime_delta = timedelta(seconds=int(uptime_seconds))

        days = uptime_delta.days
        hours = uptime_delta.seconds // 3600
        minutes = (uptime_delta.seconds % 3600) // 60

        try:
            load_avg = psutil.getloadavg()
            load_1m = round(load_avg[0], 2)
            load_5m = round(load_avg[1], 2)
            load_15m = round(load_avg[2], 2)
        except (AttributeError, OSError):
            load_1m = load_5m = load_15m = 0.0

        cpu_count = psutil.cpu_count()
        health_score = calculate_health_score()

        status = "Poor"
        status_color = "#ff3000"
        for threshold, label, color in STATUS_THRESHOLDS:
            if health_score >= threshold:
                status = label
                status_color = color
                break

        return {
            'uptime': {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'total_seconds': int(uptime_seconds)
            },
            'boot_time': boot_time.strftime('%b %d, %I:%M %p'),
            'boot_timestamp': boot_time.isoformat(),
            'load_avg': {
                '1m': load_1m,
                '5m': load_5m,
                '15m': load_15m
            },
            'cpu_count': cpu_count,
            'health_score': health_score,
            'status': status,
            'status_color': status_color
        }

    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return {
            'uptime': {'days': 0, 'hours': 0, 'minutes': 0, 'total_seconds': 0},
            'boot_time': 'Unknown',
            'boot_timestamp': None,
            'load_avg': {'1m': 0, '5m': 0, '15m': 0},
            'cpu_count': 0,
            'health_score': 0,
            'status': 'Unknown',
            'status_color': '#666'
        }


def get_system_health_widget_html():
    """Generate System Health overview widget HTML"""
    from atlas.agent_widget_styles import (
        get_widget_base_styles,
        get_widget_toast_script,
        get_widget_api_helpers_script
    )

    base_styles = get_widget_base_styles()
    toast_script = get_widget_toast_script()
    api_helpers = get_widget_api_helpers_script()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Health - ATLAS Agent</title>
    <style>
{base_styles}
        body {{
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }}
        .widget-title {{
            font-size: 24px;
            font-weight: bold;
            color: #3b82f6;
            text-align: center;
            margin-bottom: 20px;
        }}
        .overall-status {{
            background: var(--bg-elevated);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            margin-bottom: 25px;
        }}
        .overall-indicator {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            margin: 0 auto 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
        }}
        .overall-indicator.healthy {{
            background: rgba(16, 185, 129, 0.2);
            border: 3px solid #10b981;
            color: #10b981;
        }}
        .overall-indicator.warning {{
            background: rgba(245, 158, 11, 0.2);
            border: 3px solid #f59e0b;
            color: #f59e0b;
        }}
        .overall-indicator.critical {{
            background: rgba(239, 68, 68, 0.2);
            border: 3px solid #ef4444;
            color: #ef4444;
        }}
        .overall-text {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
        }}
        .overall-sub {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 5px;
        }}
        .monitor-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        @media (max-width: 480px) {{
            .monitor-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .monitor-card {{
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 15px;
            display: flex;
            align-items: center;
            gap: 15px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
        }}
        .monitor-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        .monitor-icon {{
            width: 50px;
            height: 50px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }}
        .monitor-icon.power {{
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }}
        .monitor-icon.display {{
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
        }}
        .monitor-icon.peripherals {{
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
        }}
        .monitor-icon.security {{
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }}
        .monitor-icon.disk {{
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
        }}
        .monitor-icon.software {{
            background: rgba(236, 72, 153, 0.2);
            color: #f472b6;
        }}
        .monitor-icon.network {{
            background: rgba(34, 211, 238, 0.2);
            color: #22d3ee;
        }}
        .monitor-icon.apps {{
            background: rgba(168, 85, 247, 0.2);
            color: #c084fc;
        }}
        .monitor-info {{
            flex: 1;
            min-width: 0;
        }}
        .monitor-name {{
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
        }}
        .monitor-status {{
            font-size: 12px;
            color: var(--text-muted);
        }}
        .monitor-badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            flex-shrink: 0;
        }}
        .monitor-badge.healthy {{
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }}
        .monitor-badge.warning {{
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
        }}
        .monitor-badge.critical {{
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }}
        .monitor-badge.unavailable {{
            background: rgba(107, 114, 128, 0.2);
            color: #9ca3af;
        }}
        .quick-stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 20px;
        }}
        .quick-stat {{
            background: var(--bg-elevated);
            border-radius: 10px;
            padding: 12px;
            text-align: center;
        }}
        .quick-stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: var(--text-primary);
        }}
        .quick-stat-label {{
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-top: 4px;
        }}
        .refresh-time {{
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1 class="widget-title">System Health Overview</h1>

    <div class="overall-status">
        <div class="overall-indicator" id="overallIndicator">...</div>
        <div class="overall-text" id="overallText">Checking System Health</div>
        <div class="overall-sub" id="overallSub">Gathering data from all monitors...</div>
    </div>

    <div class="monitor-grid" id="monitorGrid">
        <!-- Will be populated by JavaScript -->
    </div>

    <div class="quick-stats" id="quickStats">
        <div class="quick-stat">
            <div class="quick-stat-value" id="statMonitors">--</div>
            <div class="quick-stat-label">Monitors</div>
        </div>
        <div class="quick-stat">
            <div class="quick-stat-value" id="statHealthy">--</div>
            <div class="quick-stat-label">Healthy</div>
        </div>
        <div class="quick-stat">
            <div class="quick-stat-value" id="statWarnings">--</div>
            <div class="quick-stat-label">Warnings</div>
        </div>
        <div class="quick-stat">
            <div class="quick-stat-value" id="statCritical">--</div>
            <div class="quick-stat-label">Critical</div>
        </div>
    </div>

    <div class="refresh-time" id="refreshTime">Last updated: --</div>

    <script>
{api_helpers}
{toast_script}
        const monitors = [
            {{ id: 'power', name: 'Power & Battery', icon: 'PWR', iconClass: 'power', link: '/widget/power', api: '/api/power/status' }},
            {{ id: 'display', name: 'Display & Graphics', icon: 'DSP', iconClass: 'display', link: '/widget/display', api: '/api/display/status' }},
            {{ id: 'peripherals', name: 'Peripherals', icon: 'USB', iconClass: 'peripherals', link: '/widget/peripherals', api: '/api/peripherals/devices' }},
            {{ id: 'security', name: 'Security', icon: 'SEC', iconClass: 'security', link: '/widget/security-dashboard', api: '/api/security/status' }},
            {{ id: 'disk', name: 'Disk Health', icon: 'HDD', iconClass: 'disk', link: '/widget/disk-health', api: '/api/disk/health' }},
            {{ id: 'software', name: 'Software Inventory', icon: 'APP', iconClass: 'software', link: '/widget/tools', api: '/api/software/inventory' }},
            {{ id: 'network', name: 'Network Testing', icon: 'NET', iconClass: 'network', link: '/widget/network-testing', api: '/api/network/quality' }},
            {{ id: 'apps', name: 'Applications', icon: 'CPU', iconClass: 'apps', link: '/widget/process', api: '/api/applications/status' }}
        ];

        function getStatusFromData(data) {{
            if (!data || data.error || data.status === 'unavailable') {{
                return {{ status: 'unavailable', text: 'Unavailable' }};
            }}

            // Check for explicit status field
            if (data.status) {{
                if (data.status === 'healthy' || data.status === 'ok' || data.status === 'good') {{
                    return {{ status: 'healthy', text: 'Healthy' }};
                }}
                if (data.status === 'warning' || data.status === 'degraded') {{
                    return {{ status: 'warning', text: 'Warning' }};
                }}
                if (data.status === 'critical' || data.status === 'error' || data.status === 'failed') {{
                    return {{ status: 'critical', text: 'Critical' }};
                }}
            }}

            // Check for health indicators
            if (data.health_status) {{
                const h = data.health_status.toLowerCase();
                if (h === 'healthy' || h === 'ok' || h === 'good') {{
                    return {{ status: 'healthy', text: 'Healthy' }};
                }}
                if (h === 'warning' || h === 'degraded') {{
                    return {{ status: 'warning', text: 'Warning' }};
                }}
                return {{ status: 'critical', text: 'Critical' }};
            }}

            // Default to healthy if we have data
            return {{ status: 'healthy', text: 'Active' }};
        }}

        function getStatusSummary(data, monitorId) {{
            if (!data || data.error) return 'No data available';

            switch (monitorId) {{
                case 'power':
                    const battery = data.battery || {{}};
                    return `Battery ${{battery.health_percentage || '--'}}% | ${{battery.is_charging ? 'Charging' : 'On Battery'}}`;
                case 'display':
                    const display = data.display || {{}};
                    return `${{display.display_count || 0}} display(s) | ${{display.primary_resolution || 'Unknown'}}`;
                case 'peripherals':
                    const bt = (data.bluetooth?.devices || []).length;
                    const usb = (data.usb?.devices || []).length;
                    return `${{bt}} Bluetooth | ${{usb}} USB devices`;
                case 'security':
                    const checks = ['firewall', 'filevault', 'sip', 'gatekeeper'].filter(k => data[k] === true).length;
                    return `${{checks}}/4 security checks passed`;
                case 'disk':
                    const disks = data.disks || [];
                    const healthy = disks.filter(d => d.smart_status === 'Verified').length;
                    return `${{healthy}}/${{disks.length}} disks healthy`;
                case 'software':
                    const apps = data.installed_apps?.length || 0;
                    const updates = data.pending_updates?.length || 0;
                    return `${{apps}} apps | ${{updates}} updates pending`;
                case 'network':
                    return data.dns_latency_ms ? `DNS: ${{data.dns_latency_ms}}ms` : 'Monitoring network';
                case 'apps':
                    const crashes = data.recent_crashes?.length || 0;
                    const hangs = data.recent_hangs?.length || 0;
                    return crashes + hangs > 0 ? `${{crashes}} crashes, ${{hangs}} hangs` : 'No recent issues';
                default:
                    return 'Monitoring active';
            }}
        }}

        async function fetchMonitorStatus(monitor) {{
            try {{
                const result = await apiFetch(monitor.api);
                if (!result.ok) {{
                    return {{ monitor, data: null, success: false }};
                }}
                return {{ monitor, data: result.data, success: true }};
            }} catch (e) {{
                return {{ monitor, data: null, success: false }};
            }}
        }}

        async function update() {{
            try {{
                // Fetch all monitor statuses in parallel
                const results = await Promise.all(monitors.map(fetchMonitorStatus));

                let healthyCount = 0;
                let warningCount = 0;
                let criticalCount = 0;
                let unavailableCount = 0;

                // Render monitor cards
                const grid = document.getElementById('monitorGrid');
                grid.innerHTML = results.map(result => {{
                    const {{ monitor, data, success }} = result;
                    const statusInfo = success ? getStatusFromData(data) : {{ status: 'unavailable', text: 'Offline' }};
                    const summary = success ? getStatusSummary(data, monitor.id) : 'Monitor unavailable';

                    // Count statuses
                    if (statusInfo.status === 'healthy') healthyCount++;
                    else if (statusInfo.status === 'warning') warningCount++;
                    else if (statusInfo.status === 'critical') criticalCount++;
                    else unavailableCount++;

                    return `
                        <a href="${{monitor.link}}" class="monitor-card">
                            <div class="monitor-icon ${{monitor.iconClass}}">${{monitor.icon}}</div>
                            <div class="monitor-info">
                                <div class="monitor-name">${{monitor.name}}</div>
                                <div class="monitor-status">${{summary}}</div>
                            </div>
                            <span class="monitor-badge ${{statusInfo.status}}">${{statusInfo.text}}</span>
                        </a>
                    `;
                }}).join('');

                // Update quick stats
                const activeMonitors = monitors.length - unavailableCount;
                document.getElementById('statMonitors').textContent = activeMonitors;
                document.getElementById('statHealthy').textContent = healthyCount;
                document.getElementById('statWarnings').textContent = warningCount;
                document.getElementById('statCritical').textContent = criticalCount;

                // Update overall status
                const indicator = document.getElementById('overallIndicator');
                const text = document.getElementById('overallText');
                const sub = document.getElementById('overallSub');

                if (criticalCount > 0) {{
                    indicator.className = 'overall-indicator critical';
                    indicator.textContent = 'X';
                    text.textContent = 'Issues Detected';
                    sub.textContent = `${{criticalCount}} critical issue(s) require attention`;
                }} else if (warningCount > 0) {{
                    indicator.className = 'overall-indicator warning';
                    indicator.textContent = '!';
                    text.textContent = 'Some Warnings';
                    sub.textContent = `${{warningCount}} warning(s) to review`;
                }} else {{
                    indicator.className = 'overall-indicator healthy';
                    indicator.textContent = 'OK';
                    text.textContent = 'All Systems Healthy';
                    sub.textContent = `${{healthyCount}} monitors reporting healthy status`;
                }}

                document.getElementById('refreshTime').textContent =
                    'Last updated: ' + new Date().toLocaleTimeString();

            }} catch (e) {{
                console.error('Update failed:', e);
            }}
        }}

        update();
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.RELAXED);
        window.addEventListener('beforeunload', () => {{ clearInterval(_ivUpdate); }});
    </script>
</body>
</html>'''
