"""
Unified System Monitor Widget
Combines health, CPU, memory, disk, network, and process monitoring
"""
import psutil
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from atlas.agent_widget_styles import get_widget_api_helpers_script, get_widget_toast_script, get_tab_keyboard_script

logger = logging.getLogger(__name__)

# Cache for comprehensive stats to avoid redundant psutil calls
# when multiple widgets/API endpoints poll within the same second
_stats_cache: Dict[str, Any] = {'data': None, 'timestamp': 0.0, 'ttl': 1.0}


def get_comprehensive_system_stats() -> Dict[str, Any]:
    """Get all system stats in one call for the unified monitor.

    Results are cached for 1 second to avoid redundant psutil calls
    when multiple API endpoints are polled simultaneously.
    """
    now = time.time()
    if _stats_cache['data'] is not None and (now - _stats_cache['timestamp']) < _stats_cache['ttl']:
        return _stats_cache['data']

    result = _collect_system_stats()
    _stats_cache['data'] = result
    _stats_cache['timestamp'] = now
    return result


def _collect_system_stats() -> Dict[str, Any]:
    """Internal: collect all system stats from psutil."""
    stats = {
        'timestamp': datetime.now().isoformat(),
        'uptime': {},
        'cpu': {},
        'memory': {},
        'swap': {},
        'disk': {},
        'network': {},
        'pressure': {},
        'top_cpu_processes': [],
        'top_memory_processes': []
    }
    
    try:
        # Uptime
        boot_timestamp = psutil.boot_time()
        uptime_seconds = time.time() - boot_timestamp
        uptime_delta = timedelta(seconds=int(uptime_seconds))
        stats['uptime'] = {
            'days': uptime_delta.days,
            'hours': uptime_delta.seconds // 3600,
            'minutes': (uptime_delta.seconds % 3600) // 60,
            'seconds': uptime_delta.seconds % 60,
            'boot_time': datetime.fromtimestamp(boot_timestamp).strftime('%b %d, %I:%M %p')
        }
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_count_physical = psutil.cpu_count(logical=False)
        per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
        
        try:
            cpu_freq = psutil.cpu_freq()
            freq_current = cpu_freq.current if cpu_freq else 0
            freq_max = cpu_freq.max if cpu_freq else 0
        except (AttributeError, RuntimeError):
            freq_current = freq_max = 0

        try:
            load_avg = psutil.getloadavg()
        except (AttributeError, OSError):
            load_avg = (0, 0, 0)
        
        stats['cpu'] = {
            'percent': round(cpu_percent, 1),
            'cores_logical': cpu_count,
            'cores_physical': cpu_count_physical or cpu_count,
            'per_core': [round(p, 1) for p in per_cpu],
            'frequency_mhz': round(freq_current, 0),
            'frequency_max_mhz': round(freq_max, 0),
            'load_1m': round(load_avg[0], 2),
            'load_5m': round(load_avg[1], 2),
            'load_15m': round(load_avg[2], 2),
            'load_normalized': round(load_avg[0] / cpu_count if cpu_count > 0 else 0, 2)
        }
        
        # Memory
        memory = psutil.virtual_memory()
        stats['memory'] = {
            'percent': round(memory.percent, 1),
            'total_gb': round(memory.total / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'cached_gb': round(getattr(memory, 'cached', 0) / (1024**3), 2),
            'active_gb': round(getattr(memory, 'active', 0) / (1024**3), 2),
            'inactive_gb': round(getattr(memory, 'inactive', 0) / (1024**3), 2),
            'wired_gb': round(getattr(memory, 'wired', 0) / (1024**3), 2)
        }
        
        # Swap
        swap = psutil.swap_memory()
        stats['swap'] = {
            'percent': round(swap.percent, 1),
            'total_gb': round(swap.total / (1024**3), 2),
            'used_gb': round(swap.used / (1024**3), 2),
            'free_gb': round(swap.free / (1024**3), 2)
        }
        
        # Disk - filter to only show meaningful partitions
        disk_partitions = []
        seen_sizes = set()  # Track to avoid duplicate APFS container volumes
        
        # System volume paths to exclude
        excluded_paths = [
            '/System/Volumes/VM',
            '/System/Volumes/Preboot', 
            '/System/Volumes/Update',
            '/System/Volumes/xarts',
            '/System/Volumes/iSCPreboot',
            '/System/Volumes/Hardware',
            '/private/var/vm'
        ]
        
        for part in psutil.disk_partitions():
            try:
                # Skip system/virtual volumes
                if any(part.mountpoint.startswith(exc) for exc in excluded_paths):
                    continue
                
                # Skip snap/loop devices on Linux
                if 'snap' in part.mountpoint or 'loop' in part.device:
                    continue
                
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = round(usage.total / (1024**3), 2)
                
                # For APFS, "/" and "/System/Volumes/Data" share the same container
                # Only show the Data volume which has actual usage, or root if Data not present
                if part.mountpoint == '/':
                    # Check if we'll also see /System/Volumes/Data
                    continue  # Skip root, prefer Data volume
                
                # Create a size key to detect duplicate container views
                size_key = f"{total_gb}"
                
                # For /System/Volumes/Data, show it as "Macintosh HD" or similar
                display_name = part.mountpoint
                if part.mountpoint == '/System/Volumes/Data':
                    display_name = 'Macintosh HD'
                elif part.mountpoint.startswith('/Volumes/'):
                    display_name = part.mountpoint.replace('/Volumes/', '')
                
                disk_partitions.append({
                    'device': part.device,
                    'mountpoint': display_name,
                    'fstype': part.fstype,
                    'total_gb': total_gb,
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2),
                    'percent': round(usage.percent, 1)
                })
            except (PermissionError, OSError):
                continue
        
        # If no partitions found (unlikely), add root
        if not disk_partitions:
            try:
                usage = psutil.disk_usage('/')
                disk_partitions.append({
                    'device': '/',
                    'mountpoint': 'Macintosh HD',
                    'fstype': 'apfs',
                    'total_gb': round(usage.total / (1024**3), 2),
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2),
                    'percent': round(usage.percent, 1)
                })
            except (PermissionError, OSError):
                pass
        
        # Disk I/O (cumulative since boot)
        try:
            disk_io = psutil.disk_io_counters()
            stats['disk'] = {
                'partitions': disk_partitions,
                'read_gb': round(disk_io.read_bytes / (1024**3), 2),
                'write_gb': round(disk_io.write_bytes / (1024**3), 2),
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count
            }
        except (AttributeError, RuntimeError):
            stats['disk'] = {'partitions': disk_partitions, 'read_gb': 0, 'write_gb': 0}
        
        # Network
        net_io = psutil.net_io_counters()
        stats['network'] = {
            'bytes_sent_gb': round(net_io.bytes_sent / (1024**3), 2),
            'bytes_recv_gb': round(net_io.bytes_recv / (1024**3), 2),
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errors_in': net_io.errin,
            'errors_out': net_io.errout
        }
        
        # System Pressure Score
        pressure_score = 0
        if cpu_percent > 90: pressure_score += 40
        elif cpu_percent > 75: pressure_score += 30
        elif cpu_percent > 50: pressure_score += 15
        elif cpu_percent > 25: pressure_score += 5
        
        if memory.percent > 90: pressure_score += 40
        elif memory.percent > 80: pressure_score += 30
        elif memory.percent > 65: pressure_score += 15
        elif memory.percent > 50: pressure_score += 5
        
        normalized_load = load_avg[0] / cpu_count if cpu_count > 0 else 0
        if normalized_load > 2.0: pressure_score += 20
        elif normalized_load > 1.5: pressure_score += 15
        elif normalized_load > 1.0: pressure_score += 10
        elif normalized_load > 0.7: pressure_score += 5
        
        if pressure_score >= 60:
            pressure_level = 'Critical'
        elif pressure_score >= 40:
            pressure_level = 'High'
        elif pressure_score >= 20:
            pressure_level = 'Moderate'
        else:
            pressure_level = 'Normal'
        
        stats['pressure'] = {
            'score': pressure_score,
            'level': pressure_level
        }
        
        # Top processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is not None and pinfo['memory_percent'] is not None:
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'] or 'Unknown',
                        'cpu': round(pinfo['cpu_percent'], 1),
                        'memory': round(pinfo['memory_percent'], 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                continue
        
        # Top 5 by CPU
        stats['top_cpu_processes'] = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:5]
        # Top 5 by Memory
        stats['top_memory_processes'] = sorted(processes, key=lambda x: x['memory'], reverse=True)[:5]
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        stats['error'] = str(e)
    
    return stats


def get_system_monitor_widget_html():
    """Generate HTML for the unified system monitor widget"""
    api_helpers = get_widget_api_helpers_script()
    toast_script = get_widget_toast_script()
    tab_keyboard_script = get_tab_keyboard_script()
    return '''<!DOCTYPE html>
<html>
<head>
    <title>System Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0d0d0d;
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 15px;
            min-height: 100vh;
        }
        .monitor-container {
            max-width: 100%;
        }
        .widget-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid rgba(0, 255, 100, 0.3);
        }
        .widget-title {
            font-size: 20px;
            font-weight: bold;
            color: var(--color-primary);
            letter-spacing: -0.3px;
        }
        .widget-subtitle {
            font-size: 11px;
            color: #666;
            margin-top: 3px;
        }
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 8px 16px;
            background: var(--bg-primary);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 12px;
            font-family: inherit;
            transition: all 0.2s;
        }
        .tab:hover { background: var(--bg-elevated); color: var(--text-primary); }
        .tab.active {
            background: var(--color-primary);
            color: #000;
            border-color: var(--color-primary);
            font-weight: bold;
        }
        .panel { display: none; }
        .panel.active { display: block; }
        
        /* Overview Panel */
        .overview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        .stat-card {
            background: var(--bg-primary);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid var(--border-subtle);
        }
        .stat-card-title {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .stat-card-value {
            font-size: 28px;
            font-weight: bold;
            color: var(--color-primary);
        }
        .stat-card-sub {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        .pressure-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
        }
        .pressure-normal { background: rgba(0,255,100,0.2); color: var(--color-primary); }
        .pressure-moderate { background: rgba(255,200,0,0.2); color: var(--color-warning); }
        .pressure-high { background: rgba(255,100,0,0.2); color: #ff6400; }
        .pressure-critical { background: rgba(255,48,0,0.2); color: #ff3000; }
        
        /* Metrics Bars */
        .metric-row {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            gap: 10px;
        }
        .metric-label {
            width: 80px;
            font-size: 12px;
            color: var(--text-muted);
        }
        .metric-bar {
            flex: 1;
            height: 20px;
            background: var(--bg-elevated);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }
        .metric-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }
        .metric-fill.cpu { background: linear-gradient(90deg, #00c8ff, #0080ff); }
        .metric-fill.memory { background: linear-gradient(90deg, #00ff64, #00cc50); }
        .metric-fill.disk { background: linear-gradient(90deg, #ff6400, #ff3000); }
        .metric-fill.swap { background: linear-gradient(90deg, #8000ff, #ff00ff); }
        .metric-value {
            width: 50px;
            text-align: right;
            font-size: 12px;
            font-weight: bold;
            color: var(--text-primary);
        }
        
        /* CPU Cores */
        .cores-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
            gap: 8px;
            margin-top: 15px;
        }
        .core-box {
            background: var(--bg-primary);
            border-radius: 6px;
            padding: 10px;
            text-align: center;
            border: 1px solid var(--border-subtle);
        }
        .core-label {
            font-size: 9px;
            color: #666;
            margin-bottom: 5px;
        }
        .core-value {
            font-size: 16px;
            font-weight: bold;
        }
        
        /* Process List */
        .process-mini {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #222;
            font-size: 12px;
        }
        .process-mini:last-child { border-bottom: none; }
        .process-name { color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .process-stat { 
            min-width: 50px; 
            text-align: right; 
            font-weight: bold;
            margin-left: 10px;
        }
        
        /* Memory Breakdown */
        .mem-breakdown {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-top: 15px;
        }
        .mem-item {
            background: var(--bg-primary);
            border-radius: 6px;
            padding: 12px;
        }
        .mem-item-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
        }
        .mem-item-value {
            font-size: 18px;
            font-weight: bold;
            color: var(--color-primary);
            margin-top: 5px;
        }
        
        /* Load Avg */
        .load-container {
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }
        .load-item {
            text-align: center;
        }
        .load-label {
            font-size: 10px;
            color: #666;
        }
        .load-value {
            font-size: 20px;
            font-weight: bold;
            color: var(--color-secondary);
        }
        
        /* Section */
        .section-title {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 20px 0 10px 0;
            padding-bottom: 5px;
            border-bottom: 1px solid var(--border-subtle);
        }

        /* Disk Partitions */
        .partition-item {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .partition-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .partition-name {
            font-size: 13px;
            font-weight: bold;
        }
        .partition-size {
            font-size: 12px;
            color: #666;
        }

        /* SMART Health Styles */
        .smart-card {
            background: var(--bg-primary);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 12px;
            border: 1px solid var(--border-subtle);
        }
        .smart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .smart-disk-info {
            flex: 1;
        }
        .smart-disk-name {
            font-size: 14px;
            font-weight: bold;
            color: var(--text-primary);
        }
        .smart-disk-model {
            font-size: 11px;
            color: #666;
            margin-top: 2px;
        }
        .smart-health-badge {
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
        }
        .smart-health-excellent { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .smart-health-good { background: rgba(139, 195, 74, 0.2); color: #8bc34a; }
        .smart-health-fair { background: rgba(255, 200, 0, 0.2); color: var(--color-warning); }
        .smart-health-poor { background: rgba(255, 100, 0, 0.2); color: #ff6400; }
        .smart-health-critical { background: rgba(255, 48, 0, 0.2); color: #ff3000; }
        .smart-health-bar {
            width: 100%;
            height: 6px;
            background: var(--border-subtle);
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 12px;
        }
        .smart-health-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s;
        }
        .smart-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        .smart-metric {
            background: #222;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }
        .smart-metric-label {
            font-size: 9px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .smart-metric-value {
            font-size: 16px;
            font-weight: bold;
            margin-top: 4px;
        }
        .smart-metric-value.good { color: #10b981; }
        .smart-metric-value.warning { color: var(--color-warning); }
        .smart-metric-value.critical { color: #ff3000; }
        .smart-status-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-top: 1px solid var(--bg-elevated);
            font-size: 12px;
        }
        .smart-status-row:first-child {
            border-top: none;
        }
        .smart-status-label {
            color: var(--text-muted);
        }
        .smart-status-value {
            font-weight: 500;
        }
        .smartctl-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            background: rgba(16, 185, 129, 0.15);
            border-radius: 4px;
            font-size: 10px;
            color: #10b981;
            margin-top: 15px;
        }
        .smartctl-badge.unavailable {
            background: rgba(255, 200, 0, 0.15);
            color: var(--color-warning);
        }
        .no-smart-data {
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 13px;
        }
        
        /* History Panel */
        .history-period-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
        }
        .period-btn {
            padding: 8px 16px;
            background: var(--bg-primary);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        .period-btn:hover { background: var(--bg-elevated); color: var(--text-primary); }
        .period-btn.active {
            background: var(--color-secondary);
            color: #000;
            border-color: var(--color-secondary);
            font-weight: bold;
        }
        .time-span-indicator {
            background: var(--bg-primary);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 8px 12px;
            margin-bottom: 12px;
            font-size: 11px;
            color: var(--text-muted);
            text-align: center;
        }
        .time-span-indicator .time-span-label {
            color: var(--color-secondary);
            font-weight: bold;
        }
        .time-span-indicator .sample-count {
            color: var(--text-muted);
            margin-right: 8px;
        }
        .time-span-indicator .gap-warning {
            color: var(--color-warning);
            margin-left: 8px;
            font-size: 10px;
        }
        .time-span-indicator.has-gaps {
            border-color: var(--color-warning);
        }
        .history-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        .history-stat {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .history-stat-label {
            display: block;
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .history-stat-value {
            display: block;
            font-size: 20px;
            font-weight: bold;
            color: var(--color-primary);
        }
        .history-stat-range {
            display: block;
            font-size: 10px;
            color: #666;
            margin-top: 3px;
        }
        .chart-container {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .spike-list {
            background: var(--bg-primary);
            border-radius: 8px;
            max-height: 200px;
            overflow-y: auto;
        }
        .spike-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-subtle);
            font-size: 12px;
        }
        .spike-item:last-child { border-bottom: none; }
        .spike-time {
            color: #666;
            font-size: 11px;
        }
        .spike-type {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .spike-type.warning { background: var(--color-warning); color: #000; }
        .spike-type.critical { background: #ff3000; color: var(--text-primary); }
        .spike-value {
            font-weight: bold;
            color: var(--text-primary);
        }
    </style>
</head>
<body>
    <div class="monitor-container">
        <div class="widget-header">
            <div>
                <div class="widget-title">System Monitor</div>
                <div class="widget-subtitle">Real-time system performance metrics</div>
            </div>
        </div>

        <div class="tabs" role="tablist" aria-label="System monitor sections">
            <button class="tab active" role="tab" aria-selected="true" aria-controls="panel-overview" id="tab-overview" tabindex="0" onclick="showPanel('overview')">Overview</button>
            <button class="tab" role="tab" aria-selected="false" aria-controls="panel-cpu" id="tab-cpu" tabindex="-1" onclick="showPanel('cpu')">CPU</button>
            <button class="tab" role="tab" aria-selected="false" aria-controls="panel-memory" id="tab-memory" tabindex="-1" onclick="showPanel('memory')">Memory</button>
            <button class="tab" role="tab" aria-selected="false" aria-controls="panel-disk" id="tab-disk" tabindex="-1" onclick="showPanel('disk')">Storage</button>
            <button class="tab" role="tab" aria-selected="false" aria-controls="panel-network" id="tab-network" tabindex="-1" onclick="showPanel('network')">Network</button>
            <button class="tab" role="tab" aria-selected="false" aria-controls="panel-history" id="tab-history" tabindex="-1" onclick="showPanel('history')">History</button>
        </div>
        
        <!-- Overview Panel -->
        <div class="panel active" id="panel-overview" role="tabpanel" aria-labelledby="tab-overview">
            <div class="overview-grid">
                <div class="stat-card">
                    <div class="stat-card-title">System Status</div>
                    <div class="pressure-badge pressure-normal" id="pressureBadge">Normal</div>
                    <div class="stat-card-sub" id="pressureScore">Score: 0/100</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">Uptime</div>
                    <div class="stat-card-value" id="uptimeValue">--</div>
                    <div class="stat-card-sub" id="bootTime">Boot: --</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">CPU</div>
                    <div class="stat-card-value" id="cpuOverview">--%</div>
                    <div class="stat-card-sub" id="cpuCores">-- cores</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">Memory</div>
                    <div class="stat-card-value" id="memOverview">--%</div>
                    <div class="stat-card-sub" id="memUsed">-- / -- GB</div>
                </div>
            </div>
            
            <div class="section-title">Resource Usage</div>
            <div class="metric-row">
                <span class="metric-label">CPU</span>
                <div class="metric-bar"><div class="metric-fill cpu" id="cpuBar" style="width: 0%"></div></div>
                <span class="metric-value" id="cpuPct">--%</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Memory</span>
                <div class="metric-bar"><div class="metric-fill memory" id="memBar" style="width: 0%"></div></div>
                <span class="metric-value" id="memPct">--%</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Swap</span>
                <div class="metric-bar"><div class="metric-fill swap" id="swapBar" style="width: 0%"></div></div>
                <span class="metric-value" id="swapPct">--%</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Disk</span>
                <div class="metric-bar"><div class="metric-fill disk" id="diskBar" style="width: 0%"></div></div>
                <span class="metric-value" id="diskPct">--%</span>
            </div>
            
            <div class="section-title">Top CPU Consumers</div>
            <div id="topCpuList"></div>
            
            <div class="section-title">Top Memory Consumers</div>
            <div id="topMemList"></div>
        </div>
        
        <!-- CPU Panel -->
        <div class="panel" id="panel-cpu" role="tabpanel" aria-labelledby="tab-cpu">
            <div class="stat-card" style="margin-bottom: 15px;">
                <div class="stat-card-title">CPU Usage</div>
                <div class="stat-card-value" id="cpuTotal">--%</div>
                <div class="stat-card-sub" id="cpuFreq">Frequency: -- MHz</div>
            </div>
            
            <div class="section-title">Load Average</div>
            <div class="load-container">
                <div class="load-item">
                    <div class="load-label">1 min</div>
                    <div class="load-value" id="load1m">--</div>
                </div>
                <div class="load-item">
                    <div class="load-label">5 min</div>
                    <div class="load-value" id="load5m">--</div>
                </div>
                <div class="load-item">
                    <div class="load-label">15 min</div>
                    <div class="load-value" id="load15m">--</div>
                </div>
                <div class="load-item">
                    <div class="load-label">Normalized</div>
                    <div class="load-value" id="loadNorm">--</div>
                </div>
            </div>
            
            <div class="section-title">Per-Core Usage</div>
            <div class="cores-grid" id="coresGrid"></div>
        </div>
        
        <!-- Memory Panel -->
        <div class="panel" id="panel-memory" role="tabpanel" aria-labelledby="tab-memory">
            <div class="metric-row">
                <span class="metric-label">Used</span>
                <div class="metric-bar"><div class="metric-fill memory" id="memBarDetail" style="width: 0%"></div></div>
                <span class="metric-value" id="memPctDetail">--%</span>
            </div>
            
            <div class="mem-breakdown">
                <div class="mem-item">
                    <div class="mem-item-label">Total</div>
                    <div class="mem-item-value" id="memTotal">-- GB</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Used</div>
                    <div class="mem-item-value" id="memUsedDetail">-- GB</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Available</div>
                    <div class="mem-item-value" id="memAvail">-- GB</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Wired</div>
                    <div class="mem-item-value" id="memWired">-- GB</div>
                </div>
            </div>
            
            <div class="section-title">Swap</div>
            <div class="metric-row">
                <span class="metric-label">Used</span>
                <div class="metric-bar"><div class="metric-fill swap" id="swapBarDetail" style="width: 0%"></div></div>
                <span class="metric-value" id="swapPctDetail">--%</span>
            </div>
            <div class="stat-card-sub" id="swapInfo" style="margin-top: 10px;">-- / -- GB</div>
        </div>
        
        <!-- Disk Panel -->
        <div class="panel" id="panel-disk" role="tabpanel" aria-labelledby="tab-disk">
            <div class="section-title">Drive Health (SMART)</div>
            <div id="smartDiskList">
                <div class="no-smart-data">Loading SMART data...</div>
            </div>
            <div class="smartctl-badge" id="smartctlBadge" style="display: none;">
                <span>smartmontools</span>
                <span id="smartctlStatus">Active</span>
            </div>

            <div class="section-title">Volumes</div>
            <div id="diskPartitions"></div>

            <div class="section-title">I/O Statistics</div>
            <div class="mem-breakdown">
                <div class="mem-item">
                    <div class="mem-item-label">Total Read</div>
                    <div class="mem-item-value" id="diskRead">-- GB</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Total Written</div>
                    <div class="mem-item-value" id="diskWrite">-- GB</div>
                </div>
            </div>
        </div>
        
        <!-- Network Panel -->
        <div class="panel" id="panel-network" role="tabpanel" aria-labelledby="tab-network">
            <div class="mem-breakdown">
                <div class="mem-item">
                    <div class="mem-item-label">Data Sent</div>
                    <div class="mem-item-value" id="netSent">-- GB</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Data Received</div>
                    <div class="mem-item-value" id="netRecv">-- GB</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Packets Sent</div>
                    <div class="mem-item-value" id="netPktSent">--</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Packets Received</div>
                    <div class="mem-item-value" id="netPktRecv">--</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Errors In</div>
                    <div class="mem-item-value" id="netErrIn">--</div>
                </div>
                <div class="mem-item">
                    <div class="mem-item-label">Errors Out</div>
                    <div class="mem-item-value" id="netErrOut">--</div>
                </div>
            </div>
        </div>
        
        <!-- History Panel -->
        <div class="panel" id="panel-history" role="tabpanel" aria-labelledby="tab-history">
            <div class="history-period-tabs">
                <button class="period-btn active" onclick="loadHistory('10m')">10 Min</button>
                <button class="period-btn" onclick="loadHistory('1h')">1 Hour</button>
                <button class="period-btn" onclick="loadHistory('24h')">24 Hours</button>
                <button class="period-btn" onclick="loadHistory('7d')">7 Days</button>
            </div>
            <div class="time-span-indicator" id="timeSpanIndicator" style="display: none;">
                <span id="timeSpanText"></span>
            </div>
            
            <div class="history-stats" id="historyStats">
                <div class="history-stat">
                    <span class="history-stat-label">CPU Avg</span>
                    <span class="history-stat-value" id="histCpuAvg">--%</span>
                    <span class="history-stat-range" id="histCpuRange">-- - --%</span>
                </div>
                <div class="history-stat">
                    <span class="history-stat-label">Memory Avg</span>
                    <span class="history-stat-value" id="histMemAvg">--%</span>
                    <span class="history-stat-range" id="histMemRange">-- - --%</span>
                </div>
                <div class="history-stat">
                    <span class="history-stat-label">Pressure Avg</span>
                    <span class="history-stat-value" id="histPressureAvg">--</span>
                    <span class="history-stat-range" id="histPressureRange">-- - --</span>
                </div>
                <div class="history-stat">
                    <span class="history-stat-label">Spikes</span>
                    <span class="history-stat-value" id="histSpikeCount">0</span>
                </div>
            </div>
            
            <div class="section-title">CPU & Memory Over Time</div>
            <div class="chart-container">
                <canvas id="historyChart" height="150" role="img" aria-label="CPU and memory usage history chart"></canvas>
                <div class="sr-only" id="historyChartDesc">System resource usage chart. Data updates in real-time.</div>
            </div>
            
            <div class="section-title">Recent Spikes</div>
            <div class="spike-list" id="spikeList">
                <div style="color: #666; font-size: 12px; text-align: center; padding: 20px;">No spikes recorded</div>
            </div>
        </div>
    </div>
    
    <script>
''' + api_helpers + '''
''' + toast_script + '''
        function showPanel(name) {
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab[role="tab"]').forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
                t.setAttribute('tabindex', '-1');
            });
            document.getElementById('panel-' + name).classList.add('active');
            const activeTab = document.getElementById('tab-' + name);
            if (activeTab) {
                activeTab.classList.add('active');
                activeTab.setAttribute('aria-selected', 'true');
                activeTab.setAttribute('tabindex', '0');
            }
        }
        
        function formatNumber(n) {
            if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
            if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
            return n.toString();
        }
        
        function getCpuColor(pct) {
            if (pct > 80) return '#ff3000';
            if (pct > 50) return cssVar('--color-warning');
            return cssVar('--color-primary');
        }
        
        async function updateStats() {
            try {
                const result = await apiFetch('/api/system/comprehensive');
                if (!result.ok) {
                    console.error('Failed to update stats:', result.error);
                    return;
                }
                const data = result.data;
                
                // Overview
                const badge = document.getElementById('pressureBadge');
                badge.textContent = data.pressure.level;
                badge.className = 'pressure-badge pressure-' + data.pressure.level.toLowerCase();
                document.getElementById('pressureScore').textContent = 'Score: ' + data.pressure.score + '/100';
                
                // Uptime
                const u = data.uptime;
                let uptimeStr = '';
                if (u.days > 0) uptimeStr += u.days + 'd ';
                uptimeStr += u.hours + 'h ' + u.minutes + 'm';
                document.getElementById('uptimeValue').textContent = uptimeStr;
                document.getElementById('bootTime').textContent = 'Boot: ' + u.boot_time;
                
                // Quick stats
                document.getElementById('cpuOverview').textContent = data.cpu.percent + '%';
                document.getElementById('cpuCores').textContent = data.cpu.cores_logical + ' cores (' + data.cpu.cores_physical + ' physical)';
                document.getElementById('memOverview').textContent = data.memory.percent + '%';
                document.getElementById('memUsed').textContent = data.memory.used_gb + ' / ' + data.memory.total_gb + ' GB';
                
                // Resource bars
                document.getElementById('cpuBar').style.width = data.cpu.percent + '%';
                document.getElementById('cpuPct').textContent = data.cpu.percent + '%';
                document.getElementById('memBar').style.width = data.memory.percent + '%';
                document.getElementById('memPct').textContent = data.memory.percent + '%';
                document.getElementById('swapBar').style.width = data.swap.percent + '%';
                document.getElementById('swapPct').textContent = data.swap.percent + '%';
                
                const mainDisk = data.disk.partitions.find(p => p.mountpoint === '/') || data.disk.partitions[0];
                if (mainDisk) {
                    document.getElementById('diskBar').style.width = mainDisk.percent + '%';
                    document.getElementById('diskPct').textContent = mainDisk.percent + '%';
                }
                
                // Top processes
                let cpuHtml = '';
                data.top_cpu_processes.forEach(p => {
                    cpuHtml += `<div class="process-mini">
                        <span class="process-name">${p.name}</span>
                        <span class="process-stat" style="color: ${getCpuColor(p.cpu)}">${p.cpu}%</span>
                    </div>`;
                });
                document.getElementById('topCpuList').innerHTML = cpuHtml || '<div style="color:#666;font-size:12px;">No high CPU processes</div>';
                
                let memHtml = '';
                data.top_memory_processes.forEach(p => {
                    memHtml += `<div class="process-mini">
                        <span class="process-name">${p.name}</span>
                        <span class="process-stat" style="color: var(--color-primary)">${p.memory}%</span>
                    </div>`;
                });
                document.getElementById('topMemList').innerHTML = memHtml || '<div style="color:#666;font-size:12px;">No data</div>';
                
                // CPU Panel
                document.getElementById('cpuTotal').textContent = data.cpu.percent + '%';
                document.getElementById('cpuFreq').textContent = 'Frequency: ' + data.cpu.frequency_mhz + ' MHz';
                document.getElementById('load1m').textContent = data.cpu.load_1m;
                document.getElementById('load5m').textContent = data.cpu.load_5m;
                document.getElementById('load15m').textContent = data.cpu.load_15m;
                document.getElementById('loadNorm').textContent = data.cpu.load_normalized;
                
                let coresHtml = '';
                data.cpu.per_core.forEach((pct, i) => {
                    coresHtml += `<div class="core-box">
                        <div class="core-label">Core ${i}</div>
                        <div class="core-value" style="color: ${getCpuColor(pct)}">${pct}%</div>
                    </div>`;
                });
                document.getElementById('coresGrid').innerHTML = coresHtml;
                
                // Memory Panel
                document.getElementById('memBarDetail').style.width = data.memory.percent + '%';
                document.getElementById('memPctDetail').textContent = data.memory.percent + '%';
                document.getElementById('memTotal').textContent = data.memory.total_gb + ' GB';
                document.getElementById('memUsedDetail').textContent = data.memory.used_gb + ' GB';
                document.getElementById('memAvail').textContent = data.memory.available_gb + ' GB';
                document.getElementById('memWired').textContent = data.memory.wired_gb + ' GB';
                document.getElementById('swapBarDetail').style.width = data.swap.percent + '%';
                document.getElementById('swapPctDetail').textContent = data.swap.percent + '%';
                document.getElementById('swapInfo').textContent = data.swap.used_gb + ' / ' + data.swap.total_gb + ' GB';
                
                // Disk Panel
                let diskHtml = '';
                data.disk.partitions.forEach(p => {
                    diskHtml += `<div class="partition-item">
                        <div class="partition-header">
                            <span class="partition-name">${p.mountpoint}</span>
                            <span class="partition-size">${p.used_gb} / ${p.total_gb} GB</span>
                        </div>
                        <div class="metric-bar"><div class="metric-fill disk" style="width: ${p.percent}%"></div></div>
                    </div>`;
                });
                document.getElementById('diskPartitions').innerHTML = diskHtml || '<div style="color:#666">No partitions found</div>';
                document.getElementById('diskRead').textContent = (data.disk.read_gb || 0) + ' GB';
                document.getElementById('diskWrite').textContent = (data.disk.write_gb || 0) + ' GB';
                
                // Network Panel
                document.getElementById('netSent').textContent = data.network.bytes_sent_gb + ' GB';
                document.getElementById('netRecv').textContent = data.network.bytes_recv_gb + ' GB';
                document.getElementById('netPktSent').textContent = formatNumber(data.network.packets_sent);
                document.getElementById('netPktRecv').textContent = formatNumber(data.network.packets_recv);
                document.getElementById('netErrIn').textContent = data.network.errors_in;
                document.getElementById('netErrOut').textContent = data.network.errors_out;
                
            } catch (e) {
                console.error('Failed to update stats:', e);
                showToast(e.message || 'Failed to load', 'error');
            }
        }
        
        // History functionality
        let currentPeriod = '10m';
        let historyChart = null;
        
        async function loadHistory(period) {
            currentPeriod = period;

            // Update active button
            document.querySelectorAll('.period-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            try {
                const result = await apiFetch('/api/pressure/history/' + period);
                if (!result.ok) {
                    console.error('Failed to load history:', result.error);
                    return;
                }
                const data = result.data;

                // Update time span indicator
                const timeSpanEl = document.getElementById('timeSpanIndicator');
                const timeSpanTextEl = document.getElementById('timeSpanText');
                if (data.time_span) {
                    const startDate = new Date(data.time_span.start_time);
                    const endDate = new Date(data.time_span.end_time);
                    const formatTime = (d) => d.toLocaleString('en-US', {
                        month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit'
                    });

                    // Build info string with sample count
                    let infoHtml = '<span class="sample-count">' + data.time_span.sample_count + ' samples</span>';
                    infoHtml += '<span class="time-span-label">spanning:</span> ';
                    infoHtml += data.time_span.duration_human;
                    infoHtml += ' (' + formatTime(startDate) + ' → ' + formatTime(endDate) + ')';

                    // Add gap warning if there are gaps
                    if (data.time_span.has_gaps) {
                        timeSpanEl.classList.add('has-gaps');
                        infoHtml += '<span class="gap-warning">⚠ ' + data.time_span.gap_count + ' gap' +
                            (data.time_span.gap_count > 1 ? 's' : '') + ' (includes data from before restart)</span>';
                    } else {
                        timeSpanEl.classList.remove('has-gaps');
                    }

                    timeSpanTextEl.innerHTML = infoHtml;
                    timeSpanEl.style.display = 'block';
                } else {
                    timeSpanEl.style.display = 'none';
                }

                // Update stats
                if (data.stats) {
                    document.getElementById('histCpuAvg').textContent = data.stats.cpu_avg + '%';
                    document.getElementById('histCpuRange').textContent = data.stats.cpu_min + ' - ' + data.stats.cpu_max + '%';
                    document.getElementById('histMemAvg').textContent = data.stats.memory_avg + '%';
                    document.getElementById('histMemRange').textContent = data.stats.memory_min + ' - ' + data.stats.memory_max + '%';
                    document.getElementById('histPressureAvg').textContent = data.stats.pressure_avg;
                    document.getElementById('histPressureRange').textContent = data.stats.pressure_min + ' - ' + data.stats.pressure_max;
                    document.getElementById('histSpikeCount').textContent = data.stats.spike_count;

                    // Color code spike count
                    const spikeEl = document.getElementById('histSpikeCount');
                    if (data.stats.spike_count > 10) spikeEl.style.color = '#ff3000';
                    else if (data.stats.spike_count > 0) spikeEl.style.color = cssVar('--color-warning');
                    else spikeEl.style.color = cssVar('--color-primary');
                }

                // Draw chart
                drawChart(data.samples);

                // Update spike list
                updateSpikeList(data.spikes);

            } catch (e) {
                console.error('Failed to load history:', e);
                showToast(e.message || 'Failed to load', 'error');
            }
        }
        
        function drawChart(samples) {
            const canvas = document.getElementById('historyChart');
            const ctx = canvas.getContext('2d');
            
            // Set canvas size
            canvas.width = canvas.parentElement.clientWidth - 30;
            canvas.height = 150;
            
            // Clear
            ctx.fillStyle = cssVar('--bg-primary');
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            if (!samples || samples.length < 2) {
                ctx.fillStyle = '#666';
                ctx.font = '12px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Not enough data yet. Collecting samples...', canvas.width / 2, canvas.height / 2);
                return;
            }

            const padding = { top: 10, right: 10, bottom: 35, left: 35 };
            const chartWidth = canvas.width - padding.left - padding.right;
            const chartHeight = canvas.height - padding.top - padding.bottom;

            // Draw grid lines
            ctx.strokeStyle = cssVar('--border-subtle');
            ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i++) {
                const y = padding.top + (chartHeight / 4) * i;
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(canvas.width - padding.right, y);
                ctx.stroke();

                // Y-axis labels
                ctx.fillStyle = '#666';
                ctx.font = '10px sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText((100 - i * 25) + '%', padding.left - 5, y + 3);
            }

            // Draw time labels on X-axis
            ctx.fillStyle = '#666';
            ctx.font = '9px sans-serif';
            ctx.textAlign = 'center';

            // Show 4-5 time labels evenly spaced
            const timeLabels = Math.min(5, samples.length);
            for (let i = 0; i < timeLabels; i++) {
                const sampleIndex = Math.floor(i * (samples.length - 1) / (timeLabels - 1));
                const sample = samples[sampleIndex];
                const x = padding.left + (sampleIndex / (samples.length - 1)) * chartWidth;

                // Format time as HH:MM
                const time = new Date(sample.timestamp);
                const timeStr = time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });

                ctx.fillText(timeStr, x, canvas.height - 8);
            }
            
            // Draw CPU line
            ctx.strokeStyle = cssVar('--color-secondary');
            ctx.lineWidth = 2;
            ctx.beginPath();
            samples.forEach((s, i) => {
                const x = padding.left + (i / (samples.length - 1)) * chartWidth;
                const y = padding.top + (1 - s.cpu / 100) * chartHeight;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();
            
            // Draw Memory line
            ctx.strokeStyle = cssVar('--color-primary');
            ctx.lineWidth = 2;
            ctx.beginPath();
            samples.forEach((s, i) => {
                const x = padding.left + (i / (samples.length - 1)) * chartWidth;
                const y = padding.top + (1 - s.memory / 100) * chartHeight;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();
            
            // Draw warning threshold line (75%)
            ctx.strokeStyle = cssVar('--color-warning');
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            const warnY = padding.top + (1 - 0.75) * chartHeight;
            ctx.moveTo(padding.left, warnY);
            ctx.lineTo(canvas.width - padding.right, warnY);
            ctx.stroke();
            ctx.setLineDash([]);
            
            // Legend
            ctx.fillStyle = cssVar('--color-secondary');
            ctx.fillRect(canvas.width - 100, padding.top, 10, 10);
            ctx.fillStyle = cssVar('--text-primary');
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText('CPU', canvas.width - 85, padding.top + 9);

            ctx.fillStyle = cssVar('--color-primary');
            ctx.fillRect(canvas.width - 100, padding.top + 15, 10, 10);
            ctx.fillStyle = cssVar('--text-primary');
            ctx.fillText('Memory', canvas.width - 85, padding.top + 24);
        }
        
        function updateSpikeList(spikes) {
            const container = document.getElementById('spikeList');
            
            if (!spikes || spikes.length === 0) {
                container.innerHTML = '<div style="color: var(--color-primary); font-size: 12px; text-align: center; padding: 20px;">No spikes recorded - system running smoothly</div>';
                return;
            }
            
            // Sort by time descending (most recent first)
            const sorted = [...spikes].sort((a, b) => b.epoch - a.epoch);
            
            let html = '';
            sorted.slice(0, 20).forEach(spike => {
                const time = new Date(spike.timestamp).toLocaleTimeString();
                const typeLabel = spike.type.toUpperCase();
                const value = spike.type === 'pressure' ? spike.value : spike.value + '%';
                
                html += `<div class="spike-item">
                    <span class="spike-time">${time}</span>
                    <span class="spike-type ${spike.severity}">${typeLabel}</span>
                    <span class="spike-value">${value}</span>
                </div>`;
            });
            
            container.innerHTML = html;
        }

        // SMART disk health functions
        function formatBytes(gb) {
            if (gb >= 1000) {
                return (gb / 1000).toFixed(1) + ' TB';
            }
            return gb.toFixed(0) + ' GB';
        }

        function formatHours(hours) {
            if (hours >= 8760) {
                return (hours / 8760).toFixed(1) + ' years';
            } else if (hours >= 720) {
                return (hours / 720).toFixed(1) + ' months';
            } else if (hours >= 24) {
                return (hours / 24).toFixed(0) + ' days';
            }
            return hours + ' hrs';
        }

        function getHealthClass(percentage) {
            if (percentage >= 90) return 'excellent';
            if (percentage >= 80) return 'good';
            if (percentage >= 60) return 'fair';
            if (percentage >= 40) return 'poor';
            return 'critical';
        }

        function getHealthColor(percentage) {
            if (percentage >= 90) return '#10b981';
            if (percentage >= 80) return '#8bc34a';
            if (percentage >= 60) return cssVar('--color-warning');
            if (percentage >= 40) return '#ff6400';
            return '#ff3000';
        }

        async function updateSmartData() {
            try {
                const result = await apiFetch('/api/disk/status');
                if (!result.ok) {
                    console.error('Failed to update SMART data:', result.error);
                    document.getElementById('smartDiskList').innerHTML =
                        '<div class="no-smart-data">Failed to load SMART data</div>';
                    return;
                }
                const data = result.data;

                const container = document.getElementById('smartDiskList');

                if (data.error) {
                    container.innerHTML = '<div class="no-smart-data">' + data.error + '</div>';
                    return;
                }

                const disks = data.disks || [];

                if (disks.length === 0) {
                    container.innerHTML = '<div class="no-smart-data">No SMART data available. Install smartmontools for detailed health info.</div>';
                    return;
                }

                let html = '';

                disks.forEach(disk => {
                    const healthClass = getHealthClass(disk.health_percentage);
                    const healthColor = getHealthColor(disk.health_percentage);
                    const tempClass = disk.temperature_c > 50 ? 'critical' : disk.temperature_c > 40 ? 'warning' : 'good';
                    const wearClass = disk.wear_leveling < 50 ? 'critical' : disk.wear_leveling < 80 ? 'warning' : 'good';

                    html += `
                        <div class="smart-card">
                            <div class="smart-header">
                                <div class="smart-disk-info">
                                    <div class="smart-disk-name">${disk.disk_identifier}</div>
                                    <div class="smart-disk-model">${disk.model}</div>
                                </div>
                                <span class="smart-health-badge smart-health-${healthClass}">${disk.health_label}</span>
                            </div>

                            <div class="smart-health-bar">
                                <div class="smart-health-fill" style="width: ${disk.health_percentage}%; background: ${healthColor};"></div>
                            </div>

                            <div class="smart-metrics">
                                <div class="smart-metric">
                                    <div class="smart-metric-label">Health</div>
                                    <div class="smart-metric-value ${healthClass === 'critical' || healthClass === 'poor' ? 'critical' : healthClass === 'fair' ? 'warning' : 'good'}">${disk.health_percentage}%</div>
                                </div>
                                <div class="smart-metric">
                                    <div class="smart-metric-label">Temperature</div>
                                    <div class="smart-metric-value ${tempClass}">${disk.temperature_c > 0 ? disk.temperature_c + '°C' : 'N/A'}</div>
                                </div>
                                <div class="smart-metric">
                                    <div class="smart-metric-label">Wear Level</div>
                                    <div class="smart-metric-value ${wearClass}">${disk.wear_leveling}%</div>
                                </div>
                            </div>

                            <div style="margin-top: 12px;">
                                <div class="smart-status-row">
                                    <span class="smart-status-label">SMART Status</span>
                                    <span class="smart-status-value" style="color: ${disk.smart_status === 'PASSED' ? '#10b981' : '#ff3000'}">${disk.smart_status}</span>
                                </div>
                                <div class="smart-status-row">
                                    <span class="smart-status-label">Power On Time</span>
                                    <span class="smart-status-value">${disk.power_on_hours > 0 ? formatHours(disk.power_on_hours) : 'N/A'}</span>
                                </div>
                                <div class="smart-status-row">
                                    <span class="smart-status-label">Total Written</span>
                                    <span class="smart-status-value">${disk.total_bytes_written_gb > 0 ? formatBytes(disk.total_bytes_written_gb) : 'N/A'}</span>
                                </div>
                                <div class="smart-status-row">
                                    <span class="smart-status-label">Power Cycles</span>
                                    <span class="smart-status-value">${disk.power_cycle_count || 'N/A'}</span>
                                </div>
                                <div class="smart-status-row">
                                    <span class="smart-status-label">Unsafe Shutdowns</span>
                                    <span class="smart-status-value" style="color: ${disk.unsafe_shutdowns > 50 ? 'var(--color-warning)' : 'inherit'}">${disk.unsafe_shutdowns || 0}</span>
                                </div>
                                <div class="smart-status-row">
                                    <span class="smart-status-label">Media Errors</span>
                                    <span class="smart-status-value" style="color: ${disk.media_errors > 0 ? '#ff3000' : '#10b981'}">${disk.media_errors || 0}</span>
                                </div>
                            </div>
                        </div>
                    `;
                });

                container.innerHTML = html;

                // Show smartctl status badge
                const badge = document.getElementById('smartctlBadge');
                badge.style.display = 'inline-flex';
                if (data.smartctl_available) {
                    badge.className = 'smartctl-badge';
                    document.getElementById('smartctlStatus').textContent = 'Active';
                } else {
                    badge.className = 'smartctl-badge unavailable';
                    document.getElementById('smartctlStatus').textContent = 'Not Installed';
                }

            } catch (e) {
                console.error('Failed to update SMART data:', e);
                showToast(e.message || 'Failed to load', 'error');
                document.getElementById('smartDiskList').innerHTML =
                    '<div class="no-smart-data">Failed to load SMART data</div>';
            }
        }

        // Initial load
        updateStats();
        const _iv1 = setInterval(updateStats, UPDATE_INTERVAL.REALTIME);

        // Load SMART data (less frequently since it doesn't change often)
        updateSmartData();
        const _iv2 = setInterval(updateSmartData, UPDATE_INTERVAL.RELAXED);

        // Load history when tab is first shown
        setTimeout(() => loadHistory('10m'), 1000);

        // Cleanup intervals on page unload
        window.addEventListener('beforeunload', () => {
            clearInterval(_iv1);
            clearInterval(_iv2);
        });

        // Tab keyboard navigation
''' + tab_keyboard_script + '''
    </script>
</body>
</html>'''
