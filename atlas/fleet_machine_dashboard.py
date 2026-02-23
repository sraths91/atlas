"""
Fleet Machine Dashboard - Server-Hosted Agent Dashboard

This module generates a full dashboard page for a specific machine,
displaying synced data from the fleet server's data store.

The dashboard mimics the agent's local dashboard design but pulls
data from the server instead of the local machine.

Created: January 2026
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string"""
    if bytes_val == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while bytes_val >= 1024 and i < len(units) - 1:
        bytes_val /= 1024
        i += 1
    return f"{bytes_val:.1f} {units[i]}"


def format_uptime(seconds: float) -> str:
    """Format uptime seconds to human readable string"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def format_time_ago(iso_timestamp: str) -> str:
    """Format ISO timestamp to relative time"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h ago"
        else:
            return f"{int(seconds // 86400)}d ago"
    except (ValueError, TypeError):
        return "Unknown"


def get_machine_dashboard_html(machine: Dict[str, Any], identifier: str, history: list = None) -> str:
    """Generate the server-hosted machine dashboard HTML.

    Args:
        machine: Machine data from data_store
        identifier: Serial number or machine_id
        history: Optional metrics history list

    Returns:
        Complete HTML page as string
    """
    if not machine:
        return _get_not_found_html(identifier)

    info = machine.get('info', {})
    metrics = machine.get('latest_metrics', {})
    status = machine.get('status', 'unknown')
    last_seen = machine.get('last_seen', 'Unknown')
    first_seen = machine.get('first_seen', 'Unknown')

    # Machine info
    computer_name = info.get('computer_name', info.get('hostname', identifier))
    serial_number = info.get('serial_number', 'Unknown')
    os_info = f"{info.get('os', 'macOS')} {info.get('os_version', '')}"
    local_ip = info.get('local_ip', 'Unknown')

    # CPU metrics
    cpu = metrics.get('cpu', {})
    cpu_percent = cpu.get('percent', 0)
    cpu_cores = cpu.get('count', 0)
    cpu_threads = cpu.get('threads', info.get('cpu_threads', 0))
    load_avg = cpu.get('load_avg', [0, 0, 0])

    # Memory metrics
    memory = metrics.get('memory', {})
    mem_percent = memory.get('percent', 0)
    mem_total = memory.get('total', info.get('total_memory', 0))
    mem_used = memory.get('used', 0)
    mem_available = memory.get('available', 0)
    swap_percent = memory.get('swap_percent', 0)

    # Disk metrics
    disk = metrics.get('disk', {})
    disk_percent = disk.get('percent', 0)
    disk_total = disk.get('total', 0)
    disk_used = disk.get('used', 0)
    disk_free = disk.get('free', 0)

    # Network metrics
    network = metrics.get('network', {})
    net_sent = network.get('bytes_sent', 0)
    net_recv = network.get('bytes_recv', 0)
    net_connections = network.get('connections', 0)

    # Process info
    processes = metrics.get('processes', {})
    process_count = processes.get('total', 0)
    top_cpu_procs = processes.get('top_cpu', [])
    top_mem_procs = processes.get('top_memory', [])

    # Battery
    battery = metrics.get('battery')
    battery_html = ""
    if battery:
        bat_percent = battery.get('percent', 0)
        bat_plugged = battery.get('plugged', False)
        bat_icon = "🔌" if bat_plugged else "🔋"
        battery_html = f'''
        <div class="widget">
            <div class="widget-header">
                <span class="widget-title">{bat_icon} Battery</span>
                <span class="widget-value">{bat_percent:.0f}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill {'charging' if bat_plugged else ''}" style="width: {bat_percent}%"></div>
            </div>
            <div class="widget-detail">{'Charging' if bat_plugged else 'On Battery'}</div>
        </div>
        '''

    # Security
    security = metrics.get('security', {})
    security_enhanced = metrics.get('security_enhanced', {})
    firewall_enabled = security.get('firewall_enabled', security_enhanced.get('firewall', {}).get('enabled', False))
    filevault_enabled = security.get('filevault_enabled', security_enhanced.get('filevault', {}).get('enabled', False))
    sip_enabled = security.get('sip_enabled', security_enhanced.get('sip', {}).get('enabled', True))

    # Status styling
    status_colors = {
        'online': ('#00E5A0', '🟢'),
        'warning': ('#FFB84D', '🟡'),
        'offline': ('#ff6b6b', '🔴'),
        'unknown': ('#666', '⚪')
    }
    status_color, status_icon = status_colors.get(status, status_colors['unknown'])

    # Format times
    last_seen_ago = format_time_ago(last_seen) if last_seen != 'Unknown' else 'Unknown'
    uptime = format_uptime(metrics.get('uptime_seconds', 0))

    # Top processes HTML
    top_procs_html = ""
    for proc in top_cpu_procs[:5]:
        top_procs_html += f'''
        <div class="process-row">
            <span class="process-name">{proc.get('name', 'Unknown')[:20]}</span>
            <span class="process-cpu">{proc.get('cpu', 0):.1f}%</span>
            <span class="process-mem">{proc.get('memory', 0):.1f}%</span>
        </div>
        '''

    # VPN status
    vpn = metrics.get('vpn', {})
    vpn_html = ""
    if vpn:
        vpn_connected = vpn.get('connected', False)
        vpn_name = vpn.get('name', 'VPN')
        vpn_icon = "🔒" if vpn_connected else "🔓"
        vpn_html = f'''
        <div class="info-badge {'active' if vpn_connected else 'inactive'}">
            {vpn_icon} {vpn_name if vpn_connected else 'No VPN'}
        </div>
        '''

    # Network quality
    net_quality = metrics.get('network_quality', {})

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{computer_name} - Fleet Dashboard</title>
    <style>
        :root {{
            --bg: #121212;
            --bg-elevated: #1a1a1a;
            --bg-card: #1e1e1e;
            --text-primary: #E0E0E0;
            --text-secondary: #999;
            --text-tertiary: #666;
            --accent: #00E5A0;
            --accent-dim: rgba(0, 229, 160, 0.15);
            --info: #00C8FF;
            --warning: #FFB84D;
            --error: #ff6b6b;
            --success: #4ECDC4;
            --border: rgba(255, 255, 255, 0.06);
            --border-accent: rgba(0, 229, 160, 0.3);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            background: var(--bg);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }}

        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }}

        .header-left {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .machine-name {{
            font-size: 28px;
            font-weight: 600;
            color: var(--text-primary);
        }}

        .machine-meta {{
            display: flex;
            gap: 16px;
            color: var(--text-secondary);
            font-size: 13px;
        }}

        .header-right {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            background: {status_color}22;
            border: 1px solid {status_color};
            border-radius: 20px;
            color: {status_color};
            font-size: 13px;
            font-weight: 500;
        }}

        .last-seen {{
            font-size: 12px;
            color: var(--text-tertiary);
        }}

        .info-badges {{
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }}

        .info-badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
        }}

        .info-badge.active {{
            background: var(--accent-dim);
            color: var(--accent);
        }}

        .info-badge.inactive {{
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-tertiary);
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }}

        .widget {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
        }}

        .widget-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .widget-title {{
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
        }}

        .widget-value {{
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
        }}

        .widget-value.small {{
            font-size: 18px;
        }}

        .progress-bar {{
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
            margin: 8px 0;
        }}

        .progress-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }}

        .progress-fill.cpu {{ background: linear-gradient(90deg, #00E5A0, #00C890); }}
        .progress-fill.memory {{ background: linear-gradient(90deg, #00C8FF, #0099CC); }}
        .progress-fill.disk {{ background: linear-gradient(90deg, #FFB84D, #FF9500); }}
        .progress-fill.charging {{ background: linear-gradient(90deg, #4ECDC4, #00E5A0); }}

        .widget-detail {{
            font-size: 12px;
            color: var(--text-tertiary);
            margin-top: 4px;
        }}

        .widget-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 12px;
        }}

        .stat {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .stat-label {{
            font-size: 11px;
            color: var(--text-tertiary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .stat-value {{
            font-size: 15px;
            color: var(--text-primary);
            font-weight: 500;
        }}

        .processes-list {{
            margin-top: 12px;
        }}

        .process-header, .process-row {{
            display: grid;
            grid-template-columns: 1fr 60px 60px;
            gap: 8px;
            padding: 8px 0;
        }}

        .process-header {{
            font-size: 11px;
            color: var(--text-tertiary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
        }}

        .process-row {{
            font-size: 13px;
            border-bottom: 1px solid var(--border);
        }}

        .process-row:last-child {{
            border-bottom: none;
        }}

        .process-name {{
            color: var(--text-primary);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .process-cpu, .process-mem {{
            text-align: right;
            color: var(--text-secondary);
        }}

        .security-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 12px;
        }}

        .security-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: 12px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
        }}

        .security-icon {{
            font-size: 20px;
        }}

        .security-label {{
            font-size: 11px;
            color: var(--text-tertiary);
        }}

        .security-status {{
            font-size: 12px;
            font-weight: 500;
        }}

        .security-status.enabled {{ color: var(--accent); }}
        .security-status.disabled {{ color: var(--error); }}

        .nav-bar {{
            display: flex;
            gap: 12px;
            margin-top: 24px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.2s;
            cursor: pointer;
            border: none;
        }}

        .btn-primary {{
            background: var(--accent);
            color: #000;
        }}

        .btn-primary:hover {{
            background: #00C890;
        }}

        .btn-secondary {{
            background: transparent;
            color: var(--accent);
            border: 1px solid var(--accent);
        }}

        .btn-secondary:hover {{
            background: var(--accent-dim);
        }}

        .btn-info {{
            background: transparent;
            color: var(--info);
            border: 1px solid var(--info);
        }}

        .btn-info:hover {{
            background: rgba(0, 200, 255, 0.1);
        }}

        .data-notice {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 16px;
            background: rgba(255, 184, 77, 0.1);
            border: 1px solid rgba(255, 184, 77, 0.3);
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
            color: var(--warning);
        }}

        .data-notice.live {{
            background: rgba(0, 229, 160, 0.1);
            border-color: rgba(0, 229, 160, 0.3);
            color: var(--accent);
        }}

        .wide {{
            grid-column: span 2;
        }}

        @media (max-width: 768px) {{
            .header {{
                flex-direction: column;
                gap: 16px;
            }}
            .header-right {{
                align-items: flex-start;
            }}
            .wide {{
                grid-column: span 1;
            }}
            .security-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="data-notice {'live' if status == 'online' else ''}">
        {'📡 Live data from agent' if status == 'online' else '📦 Showing cached data from last sync'}
        &nbsp;•&nbsp; Last updated: {last_seen_ago}
    </div>

    <div class="header">
        <div class="header-left">
            <h1 class="machine-name">{computer_name}</h1>
            <div class="machine-meta">
                <span>S/N: {serial_number}</span>
                <span>•</span>
                <span>{os_info}</span>
                <span>•</span>
                <span>IP: {local_ip}</span>
            </div>
            <div class="info-badges">
                {vpn_html}
                <div class="info-badge {'active' if firewall_enabled else 'inactive'}">
                    {'🛡️ Firewall' if firewall_enabled else '⚠️ No Firewall'}
                </div>
                <div class="info-badge {'active' if filevault_enabled else 'inactive'}">
                    {'🔐 FileVault' if filevault_enabled else '⚠️ No FileVault'}
                </div>
            </div>
        </div>
        <div class="header-right">
            <div class="status-badge">{status_icon} {status.title()}</div>
            <div class="last-seen">Uptime: {uptime}</div>
        </div>
    </div>

    <div class="grid">
        <!-- CPU Widget -->
        <div class="widget">
            <div class="widget-header">
                <span class="widget-title">💻 CPU</span>
                <span class="widget-value">{cpu_percent:.1f}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill cpu" style="width: {min(cpu_percent, 100)}%"></div>
            </div>
            <div class="widget-grid">
                <div class="stat">
                    <span class="stat-label">Cores</span>
                    <span class="stat-value">{cpu_cores} ({cpu_threads} threads)</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Load Avg</span>
                    <span class="stat-value">{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}</span>
                </div>
            </div>
        </div>

        <!-- Memory Widget -->
        <div class="widget">
            <div class="widget-header">
                <span class="widget-title">🧠 Memory</span>
                <span class="widget-value">{mem_percent:.1f}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill memory" style="width: {min(mem_percent, 100)}%"></div>
            </div>
            <div class="widget-grid">
                <div class="stat">
                    <span class="stat-label">Used</span>
                    <span class="stat-value">{format_bytes(mem_used)} / {format_bytes(mem_total)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Available</span>
                    <span class="stat-value">{format_bytes(mem_available)}</span>
                </div>
            </div>
        </div>

        <!-- Disk Widget -->
        <div class="widget">
            <div class="widget-header">
                <span class="widget-title">💾 Disk</span>
                <span class="widget-value">{disk_percent:.1f}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill disk" style="width: {min(disk_percent, 100)}%"></div>
            </div>
            <div class="widget-grid">
                <div class="stat">
                    <span class="stat-label">Used</span>
                    <span class="stat-value">{format_bytes(disk_used)} / {format_bytes(disk_total)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Free</span>
                    <span class="stat-value">{format_bytes(disk_free)}</span>
                </div>
            </div>
        </div>

        <!-- Network Widget -->
        <div class="widget">
            <div class="widget-header">
                <span class="widget-title">🌐 Network</span>
                <span class="widget-value small">{net_connections} conn</span>
            </div>
            <div class="widget-grid">
                <div class="stat">
                    <span class="stat-label">Sent</span>
                    <span class="stat-value">{format_bytes(net_sent)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Received</span>
                    <span class="stat-value">{format_bytes(net_recv)}</span>
                </div>
            </div>
        </div>

        {battery_html}

        <!-- Top Processes Widget -->
        <div class="widget wide">
            <div class="widget-header">
                <span class="widget-title">⚙️ Top Processes</span>
                <span class="widget-value small">{process_count} total</span>
            </div>
            <div class="processes-list">
                <div class="process-header">
                    <span>Name</span>
                    <span style="text-align: right">CPU</span>
                    <span style="text-align: right">Mem</span>
                </div>
                {top_procs_html if top_procs_html else '<div class="process-row"><span class="process-name" style="color: var(--text-tertiary);">No process data available</span><span></span><span></span></div>'}
            </div>
        </div>

        <!-- Security Widget -->
        <div class="widget">
            <div class="widget-header">
                <span class="widget-title">🔒 Security</span>
            </div>
            <div class="security-grid">
                <div class="security-item">
                    <span class="security-icon">🛡️</span>
                    <span class="security-label">Firewall</span>
                    <span class="security-status {'enabled' if firewall_enabled else 'disabled'}">
                        {'Enabled' if firewall_enabled else 'Disabled'}
                    </span>
                </div>
                <div class="security-item">
                    <span class="security-icon">🔐</span>
                    <span class="security-label">FileVault</span>
                    <span class="security-status {'enabled' if filevault_enabled else 'disabled'}">
                        {'Enabled' if filevault_enabled else 'Disabled'}
                    </span>
                </div>
                <div class="security-item">
                    <span class="security-icon">🛡️</span>
                    <span class="security-label">SIP</span>
                    <span class="security-status {'enabled' if sip_enabled else 'disabled'}">
                        {'Enabled' if sip_enabled else 'Disabled'}
                    </span>
                </div>
            </div>
        </div>
    </div>

    <div class="nav-bar">
        <a href="/dashboard" class="btn btn-secondary">&larr; Back to Fleet</a>
        <a href="/machine/{identifier}" class="btn btn-secondary">View Full Details</a>
        {f'<a id="agentLink" href="http://{local_ip}:8767/dashboard" target="_blank" class="btn btn-info" style="display:none">Open Live Agent Dashboard &rarr;</a>' if local_ip and local_ip != 'Unknown' else ''}
    </div>

    <script>
        // Auto-refresh every 30 seconds if online
        const status = "{status}";
        if (status === "online") {{
            setTimeout(() => location.reload(), 30000);
        }}

        // Detect if agent dashboard is reachable on the local network
        (function() {{
            const link = document.getElementById('agentLink');
            if (!link) return;
            const agentUrl = link.href.replace('/dashboard', '/api/health');
            const ctrl = new AbortController();
            const timer = setTimeout(() => ctrl.abort(), 3000);
            fetch(agentUrl, {{ signal: ctrl.signal, mode: 'no-cors' }})
                .then(() => {{
                    clearTimeout(timer);
                    link.style.display = '';
                }})
                .catch(() => {{
                    clearTimeout(timer);
                }});
        }})();
    </script>
</body>
</html>'''

    return html


def _get_not_found_html(identifier: str) -> str:
    """Generate HTML for machine not found"""
    return f'''<!DOCTYPE html>
<html><head><title>Machine Not Found</title>
<style>
body {{ font-family: -apple-system, sans-serif; background: #121212; color: #e0e0e0;
       display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
.container {{ text-align: center; padding: 40px; background: #1a1a1a; border-radius: 12px; max-width: 500px; }}
h1 {{ color: #ff6b6b; margin-bottom: 20px; }}
p {{ color: #999; margin-bottom: 20px; }}
code {{ background: #2a2a2a; padding: 4px 8px; border-radius: 4px; color: #00C8FF; }}
a {{ color: #00E5A0; text-decoration: none; padding: 12px 24px; border: 1px solid #00E5A0;
     border-radius: 6px; display: inline-block; margin-top: 20px; }}
a:hover {{ background: rgba(0,229,160,0.1); }}
</style></head>
<body><div class="container">
<h1>Machine Not Found</h1>
<p>No machine with identifier <code>{identifier}</code> has been registered with this fleet server.</p>
<p>The machine may not have reported yet, or the serial number may be incorrect.</p>
<a href="/dashboard">Back to Fleet Dashboard</a>
</div></body></html>'''
