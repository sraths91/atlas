"""
Application Performance Monitor - Crash detection and application health tracking

Monitors:
- Application crashes (DiagnosticReports parsing)
- Application hangs and unresponsive apps
- Per-application resource usage (CPU, memory, network, disk I/O)
- Application launch/exit events
- Crash frequency and patterns

Enterprise Value:
- Identify problematic applications affecting productivity
- Proactive crash detection before users report issues
- Track resource-intensive applications
- Software quality insights for IT procurement
"""

import os
import logging
import threading
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import plistlib
import re

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)


class ApplicationMonitor:
    """Monitor application crashes, hangs, and resource usage"""

    def __init__(self, data_dir: str = None):
        """Initialize application monitor

        Args:
            data_dir: Directory for CSV log files (default: ~/Library/Application Support/AtlasAgent/data)
        """
        if data_dir is None:
            data_dir = os.path.expanduser("~/Library/Application Support/AtlasAgent/data")

        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir

        # CSV loggers for different metrics
        self.crash_logger = CSVLogger(
            log_file=os.path.join(data_dir, "app_crashes.csv"),
            fieldnames=[
                'timestamp', 'app_name', 'app_version', 'crash_type',
                'exception_type', 'crash_count_24h', 'process_path', 'error_message'
            ],
            max_history=10000  # Keep up to 10k crash records
        )

        self.hang_logger = CSVLogger(
            log_file=os.path.join(data_dir, "app_hangs.csv"),
            fieldnames=[
                'timestamp', 'app_name', 'pid', 'hang_duration_seconds',
                'cpu_percent', 'memory_mb', 'recovered'
            ],
            max_history=5000
        )

        self.app_resource_logger = CSVLogger(
            log_file=os.path.join(data_dir, "app_resources.csv"),
            fieldnames=[
                'timestamp', 'app_name', 'pid', 'cpu_percent', 'memory_mb',
                'threads', 'network_bytes_sent', 'network_bytes_recv',
                'disk_read_ops', 'disk_write_ops', 'open_files'
            ],
            max_history=50000  # Keep 50k resource samples
        )

        # Tracking state
        self._lock = threading.RLock()
        self._running = False
        self._monitor_thread = None

        # Crash report tracking
        self._last_crash_check = None
        self._processed_crash_files = set()

        # Hang detection state
        self._hang_candidates = {}  # pid -> {first_seen, last_cpu, app_name}

        # Diagnostic reports directory
        self._diagnostic_reports_dir = os.path.expanduser("~/Library/Logs/DiagnosticReports")

        logger.info("Application Monitor initialized")

    def start(self, collection_interval: int = 60):
        """Start background monitoring

        Args:
            collection_interval: Seconds between collection cycles (default: 60)
        """
        with self._lock:
            if self._running:
                logger.warning("Application monitor already running")
                return

            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(collection_interval,),
                daemon=True,
                name="AppMonitor"
            )
            self._monitor_thread.start()
            logger.info(f"Application monitor started (interval: {collection_interval}s)")

    def stop(self):
        """Stop background monitoring"""
        with self._lock:
            if not self._running:
                return

            self._running = False
            logger.info("Application monitor stopped")

    def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self._running:
            try:
                # Check for new crashes
                self._check_crash_reports()

                # Monitor application resource usage
                self._collect_app_resources()

                # Check for hung applications
                self._detect_hangs()

            except Exception as e:
                logger.error(f"Error in application monitor loop: {e}")

            # Sleep until next collection
            time.sleep(interval)

    def _check_crash_reports(self):
        """Scan DiagnosticReports for new application crashes"""
        try:
            if not os.path.exists(self._diagnostic_reports_dir):
                return

            current_time = datetime.now()

            # Only check files from the last 24 hours
            cutoff_time = current_time - timedelta(hours=24)

            # Get all crash report files
            crash_files = []
            for filename in os.listdir(self._diagnostic_reports_dir):
                if not (filename.endswith('.crash') or filename.endswith('.ips')):
                    continue

                filepath = os.path.join(self._diagnostic_reports_dir, filename)

                # Skip already processed files
                if filepath in self._processed_crash_files:
                    continue

                # Check file modification time
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff_time:
                        continue
                except (OSError, IOError, ValueError):
                    continue

                crash_files.append((filepath, filename, mtime))

            # Process new crash files
            for filepath, filename, mtime in crash_files:
                try:
                    crash_info = self._parse_crash_report(filepath, filename)
                    if crash_info:
                        # Count recent crashes for this app
                        crash_count_24h = self._count_recent_crashes(crash_info['app_name'])

                        # Log the crash
                        self.crash_logger.append({
                            'timestamp': mtime.isoformat(),
                            'app_name': crash_info['app_name'],
                            'app_version': crash_info.get('app_version', ''),
                            'crash_type': crash_info.get('crash_type', 'unknown'),
                            'exception_type': crash_info.get('exception_type', ''),
                            'crash_count_24h': crash_count_24h + 1,  # Include this crash
                            'process_path': crash_info.get('process_path', ''),
                            'error_message': crash_info.get('error_message', '')[:200]  # Truncate
                        })

                        logger.warning(f"Application crash detected: {crash_info['app_name']} "
                                     f"(count in 24h: {crash_count_24h + 1})")

                    # Mark as processed
                    self._processed_crash_files.add(filepath)

                except Exception as e:
                    logger.error(f"Error parsing crash report {filename}: {e}")
                    self._processed_crash_files.add(filepath)  # Don't retry

            # Clean up old processed files set (keep last 1000)
            if len(self._processed_crash_files) > 1000:
                # Remove oldest entries
                self._processed_crash_files = set(list(self._processed_crash_files)[-1000:])

        except Exception as e:
            logger.error(f"Error checking crash reports: {e}")

    def _parse_crash_report(self, filepath: str, filename: str) -> Optional[Dict]:
        """Parse macOS crash report file

        Args:
            filepath: Full path to crash report
            filename: Filename of crash report

        Returns:
            Dict with crash information, or None if parsing failed
        """
        try:
            # Extract app name from filename
            # Format: AppName-YYYY-MM-DD-HHMMSS.crash or AppName-YYYY-MM-DD-HHMMSS.ips
            app_name = filename.split('-')[0]

            # Read crash report
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000)  # Read first 50KB

            # Parse crash report (simplified for .crash and .ips formats)
            crash_info = {
                'app_name': app_name,
                'app_version': '',
                'crash_type': 'crash',
                'exception_type': '',
                'process_path': '',
                'error_message': ''
            }

            # Extract version
            version_match = re.search(r'Version:\s+(.+?)(?:\s|$)', content)
            if version_match:
                crash_info['app_version'] = version_match.group(1).strip()

            # Extract process path
            path_match = re.search(r'Path:\s+(.+?)(?:\n|$)', content)
            if path_match:
                crash_info['process_path'] = path_match.group(1).strip()

            # Extract exception type
            exception_match = re.search(r'Exception Type:\s+(.+?)(?:\n|$)', content)
            if exception_match:
                crash_info['exception_type'] = exception_match.group(1).strip()

            # Extract exception codes/message
            codes_match = re.search(r'Exception Codes:\s+(.+?)(?:\n|$)', content)
            if codes_match:
                crash_info['error_message'] = codes_match.group(1).strip()

            # Determine crash type
            if 'Hang' in content or 'Application Specific Information: Unresponsive' in content:
                crash_info['crash_type'] = 'hang'
            elif 'EXC_BAD_ACCESS' in content or 'SIGSEGV' in content:
                crash_info['crash_type'] = 'segfault'
            elif 'SIGABRT' in content or 'abort()' in content:
                crash_info['crash_type'] = 'abort'
            elif 'EXC_CRASH' in content:
                crash_info['crash_type'] = 'crash'

            return crash_info

        except Exception as e:
            logger.error(f"Error parsing crash report {filepath}: {e}")
            return None

    def _count_recent_crashes(self, app_name: str, hours: int = 24) -> int:
        """Count recent crashes for an application

        Args:
            app_name: Application name
            hours: Time window in hours (default: 24)

        Returns:
            Number of crashes in the time window
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            crashes = self.crash_logger.get_history()
            count = 0

            for crash in crashes:
                try:
                    crash_time = datetime.fromisoformat(crash.get('timestamp', ''))
                    if crash_time >= cutoff_time and crash.get('app_name') == app_name:
                        count += 1
                except (ValueError, TypeError, KeyError):
                    continue

            return count

        except Exception as e:
            logger.error(f"Error counting recent crashes: {e}")
            return 0

    def _collect_app_resources(self):
        """Collect per-application resource usage"""
        try:
            # Use ps to get process information
            cmd = [
                'ps', 'aux', '-m', '-o',
                'pid,command,%cpu,%mem,rss,threads'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return

            lines = result.stdout.strip().split('\n')[1:]  # Skip header

            current_time = datetime.now().isoformat()

            # Track only applications (not system processes)
            app_processes = {}

            for line in lines:
                try:
                    parts = line.split(None, 5)
                    if len(parts) < 6:
                        continue

                    pid = int(parts[0])
                    cpu = float(parts[2])
                    mem_percent = float(parts[3])
                    rss_kb = int(parts[4])  # Resident memory in KB
                    threads = int(parts[5]) if parts[5].isdigit() else 1
                    command = parts[5] if len(parts) > 5 else ''

                    # Extract app name from command
                    app_name = self._extract_app_name(command)
                    if not app_name:
                        continue

                    # Skip system processes
                    if app_name.startswith('/System/') or app_name.startswith('/usr/libexec'):
                        continue

                    # Get network and disk I/O stats (requires additional commands)
                    network_stats = self._get_process_network_stats(pid)
                    disk_stats = self._get_process_disk_stats(pid)
                    open_files = self._get_process_open_files(pid)

                    # Aggregate by app name (sum resources for multi-process apps)
                    if app_name not in app_processes:
                        app_processes[app_name] = {
                            'pid': pid,
                            'cpu': 0,
                            'mem_mb': 0,
                            'threads': 0,
                            'network_sent': 0,
                            'network_recv': 0,
                            'disk_read_ops': 0,
                            'disk_write_ops': 0,
                            'open_files': 0
                        }

                    proc = app_processes[app_name]
                    proc['cpu'] += cpu
                    proc['mem_mb'] += rss_kb / 1024  # Convert to MB
                    proc['threads'] += threads
                    proc['network_sent'] += network_stats['sent']
                    proc['network_recv'] += network_stats['recv']
                    proc['disk_read_ops'] += disk_stats.get('read_ops', 0)
                    proc['disk_write_ops'] += disk_stats.get('write_ops', 0)
                    proc['open_files'] += open_files

                except (ValueError, IndexError) as e:
                    continue

            # Log top resource consumers (top 20 by CPU)
            top_apps = sorted(
                app_processes.items(),
                key=lambda x: x[1]['cpu'],
                reverse=True
            )[:20]

            for app_name, stats in top_apps:
                self.app_resource_logger.append({
                    'timestamp': current_time,
                    'app_name': app_name,
                    'pid': stats['pid'],
                    'cpu_percent': round(stats['cpu'], 2),
                    'memory_mb': round(stats['mem_mb'], 2),
                    'threads': stats['threads'],
                    'network_bytes_sent': stats['network_sent'],
                    'network_bytes_recv': stats['network_recv'],
                    'disk_read_ops': stats['disk_read_ops'],
                    'disk_write_ops': stats['disk_write_ops'],
                    'open_files': stats['open_files']
                })

        except Exception as e:
            logger.error(f"Error collecting app resources: {e}")

    def _extract_app_name(self, command: str) -> Optional[str]:
        """Extract application name from command string

        Args:
            command: Process command line

        Returns:
            Application name or None
        """
        # Look for .app bundles
        app_match = re.search(r'/([^/]+\.app)/', command)
        if app_match:
            return app_match.group(1).replace('.app', '')

        # Extract from path
        parts = command.split()
        if parts:
            path = parts[0]
            return os.path.basename(path)

        return None

    def _get_process_network_stats(self, pid: int) -> Dict[str, int]:
        """Get network I/O stats for a process using nettop

        Args:
            pid: Process ID

        Returns:
            Dict with 'sent' and 'recv' bytes per second
        """
        try:
            # Use nettop to get per-process network statistics
            # nettop -P -J bytes_in,bytes_out -p <pid> -L 1 -x
            result = subprocess.run(
                ['nettop', '-P', '-J', 'bytes_in,bytes_out', '-p', str(pid), '-L', '1', '-x'],
                capture_output=True,
                text=True,
                timeout=3
            )

            if result.returncode != 0:
                return {'sent': 0, 'recv': 0}

            # Parse nettop JSON output
            import json
            try:
                data = json.loads(result.stdout)
                # nettop returns bytes/sec for the sampling period
                sent = data.get('bytes_out', 0)
                recv = data.get('bytes_in', 0)
                return {'sent': int(sent), 'recv': int(recv)}
            except (json.JSONDecodeError, KeyError):
                # Fallback: parse text output
                # Format: "process.pid bytes_in bytes_out"
                for line in result.stdout.split('\n'):
                    if str(pid) in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return {
                                'sent': int(parts[2]) if parts[2].isdigit() else 0,
                                'recv': int(parts[1]) if parts[1].isdigit() else 0
                            }

            return {'sent': 0, 'recv': 0}

        except subprocess.TimeoutExpired:
            logger.debug(f"nettop timed out for PID {pid}")
            return {'sent': 0, 'recv': 0}
        except Exception as e:
            logger.debug(f"Error getting network stats for PID {pid}: {e}")
            return {'sent': 0, 'recv': 0}

    def _get_process_disk_stats(self, pid: int) -> Dict[str, float]:
        """Get disk I/O stats for a process using ps and lsof

        Args:
            pid: Process ID

        Returns:
            Dict with 'read_ops' and 'write_ops' per second (approximate)
        """
        try:
            # Method 1: Use iostat with process filter (requires sudo, skip)
            # Method 2: Use fs_usage (requires sudo, skip)
            # Method 3: Approximate via lsof + file size changes
            # Method 4: Use ps to get disk I/O wait time as proxy

            # Get disk I/O wait time from ps (not actual bytes, but useful metric)
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'pid,command,%cpu,%mem,state'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode != 0:
                return {'read_ops': 0, 'write_ops': 0}

            # Parse ps output
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return {'read_ops': 0, 'write_ops': 0}

            # Check if process is in disk wait state (D = uninterruptible sleep)
            state = lines[1].split()[-1] if len(lines[1].split()) > 0 else ''
            in_disk_wait = 'D' in state

            # Use lsof to count open files as proxy for disk activity
            try:
                lsof_result = subprocess.run(
                    ['lsof', '-p', str(pid), '-F', 'n'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

                # Count file descriptors (rough proxy for I/O activity)
                if lsof_result.returncode == 0:
                    file_count = lsof_result.stdout.count('\nn')

                    # Heuristic: More open files + disk wait = higher I/O
                    # This is not accurate bytes, but indicates I/O activity level
                    io_activity = file_count if in_disk_wait else file_count // 4

                    return {
                        'read_ops': io_activity // 2,  # Estimate read ops
                        'write_ops': io_activity // 2  # Estimate write ops
                    }

            except subprocess.TimeoutExpired:
                pass

            # Fallback: Return disk wait indicator
            return {
                'read_ops': 1 if in_disk_wait else 0,
                'write_ops': 1 if in_disk_wait else 0
            }

        except subprocess.TimeoutExpired:
            logger.debug(f"ps timed out for PID {pid}")
            return {'read_ops': 0, 'write_ops': 0}
        except Exception as e:
            logger.debug(f"Error getting disk stats for PID {pid}: {e}")
            return {'read_ops': 0, 'write_ops': 0}

    def _get_process_open_files(self, pid: int) -> int:
        """Get count of open files for a process

        Args:
            pid: Process ID

        Returns:
            Number of open files (best effort)
        """
        try:
            result = subprocess.run(
                ['lsof', '-p', str(pid)],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                # Count lines (each line is an open file)
                return len(result.stdout.strip().split('\n')) - 1  # Subtract header
            return 0
        except (subprocess.SubprocessError, OSError):
            return 0

    def _detect_hangs(self):
        """Detect hung/unresponsive applications"""
        try:
            # Use ps to find processes with high CPU but potentially hung
            cmd = ['ps', 'aux', '-o', 'pid,command,%cpu,state']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return

            current_time = datetime.now()
            lines = result.stdout.strip().split('\n')[1:]  # Skip header

            for line in lines:
                try:
                    parts = line.split(None, 3)
                    if len(parts) < 4:
                        continue

                    pid = int(parts[0])
                    cpu = float(parts[2])
                    state = parts[3]
                    command = parts[3] if len(parts) > 3 else ''

                    app_name = self._extract_app_name(command)
                    if not app_name:
                        continue

                    # Check for hung state (uninterruptible sleep or zombie)
                    is_hung = 'U' in state or 'Z' in state

                    # Track potential hangs
                    if is_hung or (cpu > 90 and state == 'R'):  # Runaway CPU
                        if pid not in self._hang_candidates:
                            self._hang_candidates[pid] = {
                                'first_seen': current_time,
                                'app_name': app_name,
                                'last_cpu': cpu
                            }
                        else:
                            # Check if hung for > 30 seconds
                            hang_duration = (current_time - self._hang_candidates[pid]['first_seen']).total_seconds()

                            if hang_duration > 30:
                                # Log hang event
                                self.hang_logger.append({
                                    'timestamp': current_time.isoformat(),
                                    'app_name': app_name,
                                    'pid': pid,
                                    'hang_duration_seconds': int(hang_duration),
                                    'cpu_percent': cpu,
                                    'memory_mb': 0,  # Would need additional lookup
                                    'recovered': False
                                })

                                logger.warning(f"Application hang detected: {app_name} (PID {pid}, duration: {hang_duration}s)")

                                # Remove from candidates (logged)
                                del self._hang_candidates[pid]
                    else:
                        # Process recovered or was never hung
                        if pid in self._hang_candidates:
                            hang_duration = (current_time - self._hang_candidates[pid]['first_seen']).total_seconds()

                            if hang_duration > 5:  # Only log if hung for >5s
                                self.hang_logger.append({
                                    'timestamp': current_time.isoformat(),
                                    'app_name': self._hang_candidates[pid]['app_name'],
                                    'pid': pid,
                                    'hang_duration_seconds': int(hang_duration),
                                    'cpu_percent': cpu,
                                    'memory_mb': 0,
                                    'recovered': True
                                })

                            del self._hang_candidates[pid]

                except (ValueError, IndexError):
                    continue

            # Clean up stale candidates (process exited)
            stale_pids = []
            for pid in self._hang_candidates:
                age = (current_time - self._hang_candidates[pid]['first_seen']).total_seconds()
                if age > 300:  # 5 minutes
                    stale_pids.append(pid)

            for pid in stale_pids:
                del self._hang_candidates[pid]

        except Exception as e:
            logger.error(f"Error detecting hangs: {e}")

    def get_recent_crashes(self, hours: int = 24) -> List[Dict]:
        """Get recent application crashes

        Args:
            hours: Time window in hours (default: 24)

        Returns:
            List of crash events
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            crashes = []

            for crash in self.crash_logger.get_history():
                try:
                    crash_time = datetime.fromisoformat(crash.get('timestamp', ''))
                    if crash_time >= cutoff_time:
                        crashes.append(crash)
                except (ValueError, TypeError, KeyError):
                    continue

            return crashes

        except Exception as e:
            logger.error(f"Error getting recent crashes: {e}")
            return []

    def get_crash_summary(self, hours: int = 24) -> Dict:
        """Get crash summary statistics

        Args:
            hours: Time window in hours (default: 24)

        Returns:
            Summary dict with crash statistics
        """
        try:
            crashes = self.get_recent_crashes(hours)

            # Count by app
            app_crashes = {}
            total_crashes = len(crashes)

            for crash in crashes:
                app_name = crash.get('app_name', 'Unknown')
                if app_name not in app_crashes:
                    app_crashes[app_name] = 0
                app_crashes[app_name] += 1

            # Sort by crash count
            top_crashing_apps = sorted(
                app_crashes.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            return {
                'total_crashes': total_crashes,
                'unique_apps': len(app_crashes),
                'top_crashing_apps': [
                    {'app_name': app, 'crash_count': count}
                    for app, count in top_crashing_apps
                ]
            }

        except Exception as e:
            logger.error(f"Error getting crash summary: {e}")
            return {
                'total_crashes': 0,
                'unique_apps': 0,
                'top_crashing_apps': []
            }

    def get_top_resource_consumers(self, metric: str = 'cpu', limit: int = 10) -> List[Dict]:
        """Get top resource-consuming applications

        Args:
            metric: Metric to sort by ('cpu', 'memory', 'network', 'disk')
            limit: Number of apps to return

        Returns:
            List of top consuming apps
        """
        try:
            # Get recent resource logs (last 100 samples)
            recent_logs = self.app_resource_logger.get_history()[-100:]

            # Aggregate by app name
            app_stats = {}
            for log in recent_logs:
                app_name = log.get('app_name', 'Unknown')
                if app_name not in app_stats:
                    app_stats[app_name] = {
                        'cpu': [],
                        'memory': [],
                        'network': [],
                        'disk': []
                    }

                app_stats[app_name]['cpu'].append(float(log.get('cpu_percent', 0)))
                app_stats[app_name]['memory'].append(float(log.get('memory_mb', 0)))

                network_total = (
                    int(log.get('network_bytes_sent', 0)) +
                    int(log.get('network_bytes_recv', 0))
                )
                app_stats[app_name]['network'].append(network_total)

                disk_total = (
                    float(log.get('disk_read_mb', 0)) +
                    float(log.get('disk_write_mb', 0))
                )
                app_stats[app_name]['disk'].append(disk_total)

            # Calculate averages
            app_averages = []
            for app_name, stats in app_stats.items():
                avg_cpu = sum(stats['cpu']) / len(stats['cpu']) if stats['cpu'] else 0
                avg_mem = sum(stats['memory']) / len(stats['memory']) if stats['memory'] else 0
                avg_network = sum(stats['network']) / len(stats['network']) if stats['network'] else 0
                avg_disk = sum(stats['disk']) / len(stats['disk']) if stats['disk'] else 0

                app_averages.append({
                    'app_name': app_name,
                    'avg_cpu_percent': round(avg_cpu, 2),
                    'avg_memory_mb': round(avg_mem, 2),
                    'avg_network_bytes': int(avg_network),
                    'avg_disk_mb': round(avg_disk, 2)
                })

            # Sort by requested metric
            metric_key = {
                'cpu': 'avg_cpu_percent',
                'memory': 'avg_memory_mb',
                'network': 'avg_network_bytes',
                'disk': 'avg_disk_mb'
            }.get(metric, 'avg_cpu_percent')

            sorted_apps = sorted(
                app_averages,
                key=lambda x: x[metric_key],
                reverse=True
            )

            return sorted_apps[:limit]

        except Exception as e:
            logger.error(f"Error getting top resource consumers: {e}")
            return []


# Singleton instance
_app_monitor_instance = None
_app_monitor_lock = threading.Lock()


def get_app_monitor() -> ApplicationMonitor:
    """Get singleton application monitor instance

    Returns:
        ApplicationMonitor instance
    """
    global _app_monitor_instance

    if _app_monitor_instance is None:
        with _app_monitor_lock:
            if _app_monitor_instance is None:
                _app_monitor_instance = ApplicationMonitor()
                _app_monitor_instance.start(collection_interval=60)

    return _app_monitor_instance


# Export
__all__ = ['ApplicationMonitor', 'get_app_monitor']
