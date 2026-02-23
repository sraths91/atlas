"""
Process Monitor Widget
Shows top processes by CPU and Memory usage with management capabilities
"""
import psutil
import heapq
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict
from atlas.agent_widget_styles import get_widget_api_helpers_script, get_widget_toast_script

logger = logging.getLogger(__name__)

class ProcessMonitor:
    """Monitor and manage system processes"""
    
    def __init__(self):
        self.last_update = None
        # Track high CPU processes over time for stuck detection
        self.high_cpu_tracker: Dict[int, Dict] = {}  # pid -> {start_time, cpu_samples}
        self.HIGH_CPU_THRESHOLD = 90  # CPU % to consider as high
        self.STUCK_DURATION = 30  # Seconds of sustained high CPU to consider stuck
        self.CPU_SAMPLE_INTERVAL = 3  # Seconds between samples
        self.MAX_TRACKER_SIZE = 1000  # Maximum entries to prevent memory leak
    
    # Maximum time (seconds) to spend iterating processes before returning partial results
    ITERATION_TIMEOUT = 5.0

    def get_top_processes(self, sort_by='cpu', limit=10) -> List[Dict[str, Any]]:
        """
        Get top processes sorted by CPU or memory usage.

        Uses heapq.nlargest for O(n log k) performance instead of full sort.
        Enforces an iteration timeout to avoid blocking on systems with
        thousands of processes or unresponsive /proc entries.

        Args:
            sort_by: 'cpu' or 'memory'
            limit: Number of processes to return

        Returns:
            List of process dictionaries
        """
        processes = []
        deadline = time.monotonic() + self.ITERATION_TIMEOUT

        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
                # Timeout guard: return best results collected so far
                if time.monotonic() > deadline:
                    logger.warning(
                        f"Process iteration timed out after {self.ITERATION_TIMEOUT}s "
                        f"({len(processes)} processes collected)"
                    )
                    break

                try:
                    pinfo = proc.info

                    # Get memory info
                    try:
                        mem_info = proc.memory_info()
                        memory_mb = mem_info.rss / (1024 * 1024)  # Convert to MB
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        memory_mb = 0

                    # Calculate runtime
                    try:
                        runtime_seconds = datetime.now().timestamp() - pinfo['create_time']
                        runtime = self._format_runtime(runtime_seconds)
                    except (TypeError, KeyError):
                        runtime = "Unknown"

                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'] or 'Unknown',
                        'username': pinfo['username'] or 'Unknown',
                        'cpu_percent': pinfo['cpu_percent'] or 0,
                        'memory_percent': pinfo['memory_percent'] or 0,
                        'memory_mb': memory_mb,
                        'status': pinfo['status'] or 'unknown',
                        'runtime': runtime
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Use heap selection instead of full sort — O(n log k) vs O(n log n)
            sort_key = 'cpu_percent' if sort_by == 'cpu' else 'memory_percent'
            top_processes = heapq.nlargest(limit, processes, key=lambda x: x[sort_key])

            self.last_update = datetime.now().isoformat()
            return top_processes

        except Exception as e:
            logger.error(f"Error getting processes: {e}")
            return []
    
    def _format_runtime(self, seconds: float) -> str:
        """Format runtime in human-readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            return f"{days}d {hours}h"
    
    def kill_process(self, pid: int) -> Dict[str, Any]:
        """
        Attempt to kill a process by PID

        Security: Only allows killing processes owned by the current user.
        System processes and other users' processes are protected.

        Args:
            pid: Process ID to kill

        Returns:
            Dictionary with success status and message
        """
        try:
            import os
            proc = psutil.Process(pid)
            proc_name = proc.name()

            # SECURITY CHECK: Verify process ownership
            try:
                proc_username = proc.username()
                current_user = os.getenv('USER') or os.getenv('USERNAME')

                if proc_username != current_user:
                    logger.warning(f"User {current_user} attempted to kill process {pid} owned by {proc_username}")
                    return {
                        'success': False,
                        'message': f'Permission denied: Process {proc_name} (PID: {pid}) is owned by {proc_username}. Can only kill your own processes.'
                    }
            except (psutil.AccessDenied, AttributeError):
                # If we can't read the username, we definitely can't kill it
                return {
                    'success': False,
                    'message': f'Permission denied: Cannot access process {pid} information'
                }

            # Additional protection: Prevent killing critical system processes
            # PID 1 (init/launchd), kernel processes, and very low PIDs
            if pid < 100:
                logger.warning(f"Attempt to kill low PID system process {pid} ({proc_name})")
                return {
                    'success': False,
                    'message': f'Protection: Cannot kill system process {proc_name} (PID: {pid})'
                }

            # Try graceful termination first
            proc.terminate()

            # Wait up to 3 seconds for process to terminate
            try:
                proc.wait(timeout=3)
                logger.info(f"Process {proc_name} (PID: {pid}) terminated successfully by user {current_user}")
                return {
                    'success': True,
                    'message': f'Process {proc_name} (PID: {pid}) terminated successfully'
                }
            except psutil.TimeoutExpired:
                # Force kill if graceful termination fails
                proc.kill()
                logger.info(f"Process {proc_name} (PID: {pid}) force killed by user {current_user}")
                return {
                    'success': True,
                    'message': f'Process {proc_name} (PID: {pid}) force killed'
                }

        except psutil.NoSuchProcess:
            return {
                'success': False,
                'message': f'Process with PID {pid} not found'
            }
        except psutil.AccessDenied:
            return {
                'success': False,
                'message': f'Access denied. Cannot kill process {pid} (requires elevated privileges)'
            }
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
            return {
                'success': False,
                'message': f'Error killing process: {str(e)}'
            }
    
    def search_processes(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for processes by name
        
        Args:
            query: Search string
        
        Returns:
            List of matching processes
        """
        query_lower = query.lower()
        all_processes = self.get_top_processes(limit=1000)
        
        return [
            proc for proc in all_processes
            if query_lower in proc['name'].lower() or query_lower in str(proc['pid'])
        ]
    
    def get_problematic_processes(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect stuck, zombie, and stopped processes
        
        Returns:
            Dictionary with categories: zombie, stuck, stopped, high_cpu
        """
        problematic = {
            'zombie': [],
            'stuck': [],
            'stopped': [],
            'high_cpu': [],
            'unresponsive': []
        }
        
        current_time = time.time()
        active_pids = set()
        deadline = time.monotonic() + self.ITERATION_TIMEOUT

        try:
            for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'create_time']):
                if time.monotonic() > deadline:
                    logger.warning(
                        f"Problematic process scan timed out after {self.ITERATION_TIMEOUT}s"
                    )
                    break

                try:
                    pinfo = proc.info
                    pid = pinfo['pid']
                    active_pids.add(pid)
                    
                    status = pinfo['status']
                    cpu_percent = pinfo['cpu_percent'] or 0
                    name = pinfo['name'] or 'Unknown'
                    
                    # Calculate runtime
                    try:
                        runtime_seconds = current_time - pinfo['create_time']
                        runtime = self._format_runtime(runtime_seconds)
                    except (TypeError, KeyError):
                        runtime_seconds = 0
                        runtime = "Unknown"
                    
                    proc_info = {
                        'pid': pid,
                        'name': name,
                        'status': status,
                        'cpu_percent': round(cpu_percent, 1),
                        'runtime': runtime
                    }
                    
                    # Detect zombie processes
                    if status == 'zombie':
                        proc_info['issue'] = 'Zombie process - terminated but not reaped'
                        problematic['zombie'].append(proc_info)
                        continue
                    
                    # Detect stopped processes
                    if status == 'stopped':
                        proc_info['issue'] = 'Process is stopped/suspended'
                        problematic['stopped'].append(proc_info)
                        continue
                    
                    # Track high CPU processes for stuck detection
                    if cpu_percent >= self.HIGH_CPU_THRESHOLD:
                        if pid not in self.high_cpu_tracker:
                            self.high_cpu_tracker[pid] = {
                                'start_time': current_time,
                                'name': name,
                                'samples': [cpu_percent]
                            }
                        else:
                            tracker = self.high_cpu_tracker[pid]
                            tracker['samples'].append(cpu_percent)
                            # Keep only recent samples
                            if len(tracker['samples']) > 20:
                                tracker['samples'] = tracker['samples'][-20:]
                            
                            # Check if sustained high CPU (stuck)
                            duration = current_time - tracker['start_time']
                            avg_cpu = sum(tracker['samples']) / len(tracker['samples'])
                            
                            if duration >= self.STUCK_DURATION and avg_cpu >= self.HIGH_CPU_THRESHOLD:
                                proc_info['issue'] = f'Sustained {avg_cpu:.0f}% CPU for {self._format_runtime(duration)}'
                                proc_info['duration'] = round(duration, 0)
                                proc_info['avg_cpu'] = round(avg_cpu, 1)
                                problematic['stuck'].append(proc_info)
                            elif duration < self.STUCK_DURATION:
                                # High CPU but not yet stuck
                                proc_info['issue'] = f'High CPU: {cpu_percent:.0f}% for {self._format_runtime(duration)}'
                                proc_info['duration'] = round(duration, 0)
                                problematic['high_cpu'].append(proc_info)
                    else:
                        # CPU dropped, remove from tracker
                        if pid in self.high_cpu_tracker:
                            del self.high_cpu_tracker[pid]
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Clean up tracker for processes that no longer exist
            dead_pids = set(self.high_cpu_tracker.keys()) - active_pids
            for pid in dead_pids:
                del self.high_cpu_tracker[pid]

            # RESOURCE LEAK PROTECTION: Limit tracker size to prevent unbounded growth
            if len(self.high_cpu_tracker) > self.MAX_TRACKER_SIZE:
                # Remove oldest entries (those with earliest start_time)
                sorted_pids = sorted(
                    self.high_cpu_tracker.items(),
                    key=lambda x: x[1]['start_time']
                )
                # Keep only the most recent MAX_TRACKER_SIZE entries
                pids_to_remove = [pid for pid, _ in sorted_pids[:-self.MAX_TRACKER_SIZE]]
                for pid in pids_to_remove:
                    del self.high_cpu_tracker[pid]

                if pids_to_remove:
                    logger.warning(
                        f"high_cpu_tracker exceeded max size ({self.MAX_TRACKER_SIZE}). "
                        f"Removed {len(pids_to_remove)} oldest entries."
                    )

            # Add summary counts
            problematic['summary'] = {
                'zombie_count': len(problematic['zombie']),
                'stuck_count': len(problematic['stuck']),
                'stopped_count': len(problematic['stopped']),
                'high_cpu_count': len(problematic['high_cpu']),
                'total_issues': (len(problematic['zombie']) + len(problematic['stuck']) + 
                               len(problematic['stopped']))
            }
            
        except Exception as e:
            logger.error(f"Error detecting problematic processes: {e}")
            problematic['error'] = str(e)
        
        return problematic

# Global process monitor instance
process_monitor = ProcessMonitor()

def get_process_widget_html():
    """Generate HTML for process monitor widget"""
    api_helpers = get_widget_api_helpers_script()
    toast_script = get_widget_toast_script()
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Process Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            background: #1a1a1a;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 20px;
            height: 100vh;
            overflow: hidden;
        }
        .container {
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(0, 229, 160, 0.4);
        }
        h2 {
            color: #00E5A0;
            font-size: 24px;
            margin: 0;
            white-space: nowrap;
        }
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }
        .search-box {
            padding: 8px 12px;
            background: rgba(42, 42, 42, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 229, 160, 0.3);
            border-radius: 8px;
            color: #fff;
            font-size: 13px;
            width: 150px;
            min-width: 120px;
            transition: all 0.2s;
        }
        .search-box:focus {
            outline: none;
            border-color: #00E5A0;
            box-shadow: 0 0 20px rgba(0, 229, 160, 0.3);
            background: rgba(42, 42, 42, 0.9);
        }
        .sort-btn {
            padding: 6px 12px;
            background: rgba(42, 42, 42, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 229, 160, 0.3);
            border-radius: 8px;
            color: #00E5A0;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .sort-btn:hover {
            background: rgba(0, 229, 160, 0.15);
            border-color: #00E5A0;
            transform: translateY(-1px);
        }
        .sort-btn.active {
            background: #00E5A0;
            color: #0a0a0a;
            font-weight: bold;
            box-shadow: 0 0 20px rgba(0, 229, 160, 0.3);
        }
        .refresh-btn {
            padding: 6px 12px;
            background: #00E5A0;
            border: none;
            border-radius: 8px;
            color: #0a0a0a;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
            transition: all 0.2s;
            white-space: nowrap;
            box-shadow: 0 0 15px rgba(0, 229, 160, 0.2);
        }
        .refresh-btn:hover {
            background: #00C890;
            transform: translateY(-1px);
            box-shadow: 0 0 25px rgba(0, 229, 160, 0.4);
        }
        .stats {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 15px;
            font-size: 13px;
            color: #999;
            align-items: center;
        }
        .stat {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .stat-value {
            color: #00E5A0;
            font-weight: bold;
        }
        .stat-separator {
            width: 1px;
            height: 20px;
            background: #444;
        }
        .pressure-indicator {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
        }
        .pressure-normal {
            background: rgba(0, 255, 100, 0.2);
            color: #00ff64;
        }
        .pressure-moderate {
            background: rgba(255, 200, 0, 0.2);
            color: #ffc800;
        }
        .pressure-high {
            background: rgba(255, 100, 0, 0.2);
            color: #ff6400;
        }
        .pressure-critical {
            background: rgba(255, 48, 0, 0.2);
            color: #ff3000;
        }
        .cpu-warning {
            color: #ffc800 !important;
        }
        .cpu-danger {
            color: #ff3000 !important;
        }
        .mem-warning {
            color: #ffc800 !important;
        }
        .mem-danger {
            color: #ff3000 !important;
        }
        .alerts-container {
            margin-bottom: 10px;
        }
        .alerts-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: rgba(255, 100, 0, 0.2);
            border: 1px solid #ff6400;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
        }
        .alerts-header.no-issues {
            background: rgba(0, 255, 100, 0.1);
            border-color: #00ff64;
        }
        .alerts-header-text {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: bold;
            font-size: 13px;
        }
        .alerts-badge {
            background: #ff3000;
            color: #fff;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }
        .alerts-badge.ok {
            background: #00ff64;
            color: #000;
        }
        .alerts-toggle {
            font-size: 12px;
            color: #999;
        }
        .alerts-content {
            display: none;
            background: #1a1a1a;
            border: 1px solid #ff6400;
            border-top: none;
            border-radius: 0 0 8px 8px;
            max-height: 200px;
            overflow-y: auto;
        }
        .alerts-content.no-issues {
            border-color: #00ff64;
        }
        .alerts-content.expanded {
            display: block;
        }
        .alert-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            border-bottom: 1px solid #333;
            font-size: 12px;
        }
        .alert-item:last-child {
            border-bottom: none;
        }
        .alert-item-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .alert-item-name {
            font-weight: bold;
            color: #fff;
        }
        .alert-item-detail {
            color: #999;
            font-size: 11px;
        }
        .alert-type {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .alert-type-zombie {
            background: #8b0000;
            color: #fff;
        }
        .alert-type-stuck {
            background: #ff6400;
            color: #fff;
        }
        .alert-type-stopped {
            background: #666;
            color: #fff;
        }
        .alert-type-high-cpu {
            background: #ffc800;
            color: #000;
        }
        .alert-kill-btn {
            padding: 4px 8px;
            background: #ff3000;
            border: none;
            border-radius: 4px;
            color: #fff;
            font-size: 10px;
            cursor: pointer;
        }
        .alert-kill-btn:hover {
            background: #ff0000;
        }
        .table-container {
            flex: 1;
            overflow-y: auto;
            background: rgba(26, 26, 26, 0.7);
            backdrop-filter: blur(20px) saturate(180%);
            border-radius: 12px;
            border: 1px solid rgba(0, 229, 160, 0.3);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        thead {
            position: sticky;
            top: 0;
            background: #1a1a1a;
            z-index: 10;
        }
        th {
            padding: 12px;
            text-align: left;
            color: #00E5A0;
            font-weight: bold;
            border-bottom: 2px solid rgba(0, 229, 160, 0.4);
            cursor: pointer;
            user-select: none;
        }
        th:hover {
            background: #333;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #333;
        }
        tr:hover {
            background: #333;
        }
        .process-name {
            font-weight: bold;
            color: #fff;
        }
        .pid {
            color: #999;
            font-family: monospace;
        }
        .cpu-high {
            color: #ff6b6b;
            font-weight: bold;
        }
        .cpu-medium {
            color: #ffd93d;
            font-weight: bold;
        }
        .cpu-low {
            color: #6bcf7f;
        }
        .memory-bar {
            width: 100px;
            height: 8px;
            background: #333;
            border-radius: 4px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 8px;
        }
        .memory-fill {
            height: 100%;
            background: linear-gradient(90deg, #00E5A0, #00C890);
            transition: width 0.3s ease;
        }
        .kill-btn {
            padding: 4px 10px;
            background: #ff4444;
            border: none;
            border-radius: 4px;
            color: #fff;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        .kill-btn:hover {
            background: #ff0000;
            transform: scale(1.05);
        }
        .status {
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-running {
            background: #00E5A0;
            color: #0a0a0a;
        }
        .status-sleeping {
            background: #666;
            color: #fff;
        }
        .status-stopped {
            background: #ff4444;
            color: #fff;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 16px;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal.active {
            display: flex;
        }
        .modal-content {
            background: rgba(26, 26, 26, 0.95);
            backdrop-filter: blur(40px) saturate(180%);
            border: 1px solid rgba(0, 229, 160, 0.3);
            border-radius: 16px;
            padding: 30px;
            max-width: 500px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        }
        .modal-title {
            color: #ff4444;
            font-size: 20px;
            margin-bottom: 15px;
        }
        .modal-message {
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .modal-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
        }
        .modal-btn-confirm {
            background: #ff4444;
            color: #fff;
        }
        .modal-btn-confirm:hover {
            background: #ff0000;
        }
        .modal-btn-cancel {
            background: #666;
            color: #fff;
        }
        .modal-btn-cancel:hover {
            background: #888;
        }
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            font-weight: bold;
            z-index: 2000;
            animation: slideIn 0.3s ease;
            max-width: 400px;
        }
        .notification-success {
            background: #00E5A0;
            color: #0a0a0a;
        }
        .notification-error {
            background: #ff4444;
            color: #fff;
        }
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        ::-webkit-scrollbar {
            width: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        ::-webkit-scrollbar-thumb {
            background: #00E5A0;
            border-radius: 5px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #00C890;
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Process Monitor</h2>
            <div class="controls">
                <input type="text" class="search-box" id="searchBox" placeholder="Search processes...">
                <button class="sort-btn active" id="sortCpu" onclick="sortBy('cpu')">Sort by CPU</button>
                <button class="sort-btn" id="sortMemory" onclick="sortBy('memory')">Sort by Memory</button>
                <button class="refresh-btn" onclick="refresh()">Refresh</button>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat">
                <span>Processes:</span>
                <span class="stat-value" id="totalProcesses">--</span>
            </div>
            <div class="stat">
                <span>Running:</span>
                <span class="stat-value" id="runningProcesses">--</span>
            </div>
            <div class="stat-separator"></div>
            <div class="stat">
                <span>CPU:</span>
                <span class="stat-value" id="cpuPercent">--%</span>
            </div>
            <div class="stat">
                <span>Memory:</span>
                <span class="stat-value" id="memoryPercent">--%</span>
            </div>
            <div class="stat">
                <span>Load:</span>
                <span class="stat-value" id="loadAvg">--</span>
            </div>
            <div class="stat-separator"></div>
            <div class="stat">
                <span>System:</span>
                <span class="stat-value pressure-indicator" id="pressureLevel">--</span>
            </div>
            <div class="stat">
                <span>Updated:</span>
                <span class="stat-value" id="lastUpdate">--</span>
            </div>
        </div>
        
        <!-- Problematic Processes Alert Section -->
        <div class="alerts-container" id="alertsContainer">
            <div class="alerts-header no-issues" id="alertsHeader" onclick="toggleAlerts()">
                <div class="alerts-header-text">
                    <span>Process Health</span>
                    <span class="alerts-badge ok" id="alertsBadge">OK</span>
                </div>
                <span class="alerts-toggle" id="alertsToggle">[show]</span>
            </div>
            <div class="alerts-content no-issues" id="alertsContent">
                <div id="alertsList">
                    <div class="alert-item" style="color: #00ff64; justify-content: center;">
                        No problematic processes detected
                    </div>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Process</th>
                        <th>PID</th>
                        <th>User</th>
                        <th>CPU %</th>
                        <th>Memory</th>
                        <th>Status</th>
                        <th>Runtime</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="processTable">
                    <tr>
                        <td colspan="8" class="no-results">Loading processes...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="modal" id="killModal">
        <div class="modal-content">
            <div class="modal-title">Confirm Kill Process</div>
            <div class="modal-message" id="killMessage"></div>
            <div class="modal-buttons">
                <button class="modal-btn modal-btn-confirm" onclick="confirmKill()">Kill Process</button>
                <button class="modal-btn modal-btn-cancel" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    </div>
    
    <script>
''' + api_helpers + '''
''' + toast_script + '''
        let currentSort = 'cpu';
        let searchQuery = '';
        let killPid = null;
        let killName = null;
        
        async function loadProcesses() {
            try {
                const url = searchQuery 
                    ? `/api/processes/search?q=${encodeURIComponent(searchQuery)}`
                    : `/api/processes?sort=${currentSort}`;
                
                const result = await apiFetch(url);
                if (!result.ok) {
                    console.error('Failed to load processes:', result.error);
                    showNotification('Failed to load processes', 'error');
                    return;
                }
                const data = result.data;

                updateStats(data);
                renderProcessTable(data.processes);
            } catch (e) {
                console.error('Failed to load processes:', e);
                showNotification('Failed to load processes', 'error');
            }
        }
        
        function updateStats(data) {
            document.getElementById('totalProcesses').textContent = data.total || 0;
            document.getElementById('runningProcesses').textContent = data.running || 0;
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }
        
        async function loadSystemPressure() {
            try {
                const result = await apiFetch('/api/system/pressure');
                if (!result.ok) {
                    console.error('Failed to load system pressure:', result.error);
                    return;
                }
                const data = result.data;
                
                // Update CPU
                const cpuEl = document.getElementById('cpuPercent');
                cpuEl.textContent = data.cpu.percent + '%';
                cpuEl.className = 'stat-value';
                if (data.cpu.percent > 80) cpuEl.classList.add('cpu-danger');
                else if (data.cpu.percent > 50) cpuEl.classList.add('cpu-warning');

                // Update Memory
                const memEl = document.getElementById('memoryPercent');
                memEl.textContent = data.memory.percent + '%';
                memEl.className = 'stat-value';
                if (data.memory.percent > 85) memEl.classList.add('mem-danger');
                else if (data.memory.percent > 65) memEl.classList.add('mem-warning');
                
                // Update Load Average
                document.getElementById('loadAvg').textContent = data.load['1m'];
                
                // Update System Pressure
                const pressureEl = document.getElementById('pressureLevel');
                pressureEl.textContent = data.pressure.level;
                pressureEl.className = 'stat-value pressure-indicator pressure-' + data.pressure.level.toLowerCase();
                
            } catch (e) {
                console.error('Failed to load system pressure:', e);
                showToast(e.message || 'Failed to load', 'error');
            }
        }
        
        let alertsExpanded = false;
        
        function toggleAlerts() {
            alertsExpanded = !alertsExpanded;
            const content = document.getElementById('alertsContent');
            const toggle = document.getElementById('alertsToggle');
            
            if (alertsExpanded) {
                content.classList.add('expanded');
                toggle.textContent = '[hide]';
            } else {
                content.classList.remove('expanded');
                toggle.textContent = '[show]';
            }
        }
        
        async function loadProblematicProcesses() {
            try {
                const result = await apiFetch('/api/processes/problematic');
                if (!result.ok) {
                    console.error('Failed to load problematic processes:', result.error);
                    return;
                }
                const data = result.data;
                
                const header = document.getElementById('alertsHeader');
                const content = document.getElementById('alertsContent');
                const badge = document.getElementById('alertsBadge');
                const list = document.getElementById('alertsList');
                
                const totalIssues = data.summary?.total_issues || 0;
                const highCpu = data.high_cpu?.length || 0;
                
                // Update badge and styling
                if (totalIssues > 0) {
                    badge.textContent = totalIssues + ' issue' + (totalIssues > 1 ? 's' : '');
                    badge.className = 'alerts-badge';
                    header.className = 'alerts-header';
                    content.className = alertsExpanded ? 'alerts-content expanded' : 'alerts-content';
                } else if (highCpu > 0) {
                    badge.textContent = highCpu + ' warning' + (highCpu > 1 ? 's' : '');
                    badge.className = 'alerts-badge';
                    badge.style.background = '#ffc800';
                    badge.style.color = '#000';
                    header.className = 'alerts-header';
                    header.style.background = 'rgba(255, 200, 0, 0.2)';
                    header.style.borderColor = '#ffc800';
                    content.className = alertsExpanded ? 'alerts-content expanded' : 'alerts-content';
                    content.style.borderColor = '#ffc800';
                } else {
                    badge.textContent = 'OK';
                    badge.className = 'alerts-badge ok';
                    badge.style.background = '';
                    badge.style.color = '';
                    header.className = 'alerts-header no-issues';
                    header.style.background = '';
                    header.style.borderColor = '';
                    content.className = alertsExpanded ? 'alerts-content no-issues expanded' : 'alerts-content no-issues';
                    content.style.borderColor = '';
                }
                
                // Build alerts list
                let alertsHtml = '';
                
                // Zombie processes (most critical)
                data.zombie?.forEach(proc => {
                    alertsHtml += renderAlertItem(proc, 'zombie', 'Zombie');
                });
                
                // Stuck processes
                data.stuck?.forEach(proc => {
                    alertsHtml += renderAlertItem(proc, 'stuck', 'Stuck');
                });
                
                // Stopped processes
                data.stopped?.forEach(proc => {
                    alertsHtml += renderAlertItem(proc, 'stopped', 'Stopped');
                });
                
                // High CPU (warnings)
                data.high_cpu?.forEach(proc => {
                    alertsHtml += renderAlertItem(proc, 'high-cpu', 'High CPU');
                });
                
                if (!alertsHtml) {
                    alertsHtml = '<div class="alert-item" style="color: #00ff64; justify-content: center;">No problematic processes detected</div>';
                }
                
                list.innerHTML = alertsHtml;
                
            } catch (e) {
                console.error('Failed to load problematic processes:', e);
                showToast(e.message || 'Failed to load', 'error');
            }
        }
        
        function renderAlertItem(proc, type, label) {
            return `
                <div class="alert-item">
                    <div class="alert-item-info">
                        <span class="alert-item-name">${escapeHtml(proc.name)} (PID: ${proc.pid})</span>
                        <span class="alert-item-detail">${escapeHtml(proc.issue || proc.status)}</span>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span class="alert-type alert-type-${type}">${label}</span>
                        <button class="alert-kill-btn" onclick="showKillModal(${proc.pid}, '${escapeHtml(proc.name)}')">Kill</button>
                    </div>
                </div>
            `;
        }
        
        function renderProcessTable(processes) {
            const tbody = document.getElementById('processTable');
            
            if (!processes || processes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="no-results">No processes found</td></tr>';
                return;
            }
            
            tbody.innerHTML = processes.map(proc => `
                <tr>
                    <td class="process-name">${escapeHtml(proc.name)}</td>
                    <td class="pid">${proc.pid}</td>
                    <td>${escapeHtml(proc.username)}</td>
                    <td class="${getCpuClass(proc.cpu_percent)}">${proc.cpu_percent.toFixed(1)}%</td>
                    <td>
                        <div class="memory-bar">
                            <div class="memory-fill" style="width: ${Math.min(proc.memory_percent, 100)}%"></div>
                        </div>
                        ${proc.memory_mb.toFixed(0)} MB
                    </td>
                    <td><span class="status status-${proc.status}">${proc.status}</span></td>
                    <td>${proc.runtime}</td>
                    <td>
                        <button class="kill-btn" onclick="showKillModal(${proc.pid}, '${escapeHtml(proc.name)}')">
                            Kill
                        </button>
                    </td>
                </tr>
            `).join('');
        }
        
        function getCpuClass(cpu) {
            if (cpu > 50) return 'cpu-high';
            if (cpu > 20) return 'cpu-medium';
            return 'cpu-low';
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function sortBy(type) {
            currentSort = type;
            document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(`sort${type.charAt(0).toUpperCase() + type.slice(1)}`).classList.add('active');
            loadProcesses();
        }
        
        function refresh() {
            loadProcesses();
        }
        
        function showKillModal(pid, name) {
            killPid = pid;
            killName = name;
            document.getElementById('killMessage').innerHTML = `
                Are you sure you want to kill process:<br><br>
                <strong>${escapeHtml(name)}</strong> (PID: ${pid})<br><br>
                This action cannot be undone.
            `;
            document.getElementById('killModal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('killModal').classList.remove('active');
            killPid = null;
            killName = null;
        }
        
        async function confirmKill() {
            if (!killPid) return;
            
            closeModal();
            
            try {
                const result = await apiFetch(`/api/processes/kill/${killPid}`, {
                    method: 'POST'
                });
                if (!result.ok) {
                    showNotification(result.error || 'Failed to kill process', 'error');
                    return;
                }
                const data = result.data;

                if (data.success) {
                    showNotification(data.message, 'success');
                    setTimeout(loadProcesses, 1000);
                } else {
                    showNotification(data.message, 'error');
                }
            } catch (e) {
                console.error('Failed to kill process:', e);
                showNotification('Failed to kill process', 'error');
            }
        }
        
        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
        
        // Search functionality
        let searchTimeout;
        document.getElementById('searchBox').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchQuery = e.target.value.trim();
            searchTimeout = setTimeout(() => {
                loadProcesses();
            }, 300);
        });
        
        // Initial load and auto-refresh
        loadProcesses();
        loadSystemPressure();
        loadProblematicProcesses();
        const _iv1 = setInterval(loadProcesses, UPDATE_INTERVAL.FREQUENT);
        const _iv2 = setInterval(loadSystemPressure, UPDATE_INTERVAL.FREQUENT);
        const _iv3 = setInterval(loadProblematicProcesses, UPDATE_INTERVAL.STANDARD);

        // Cleanup intervals on page unload
        window.addEventListener('beforeunload', () => {
            clearInterval(_iv1);
            clearInterval(_iv2);
            clearInterval(_iv3);
        });
    </script>
</body>
</html>'''
