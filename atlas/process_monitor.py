"""Process monitoring module for detecting stuck, zombie, and problematic processes."""
import psutil
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ProcessInfo:
    """Information about a monitored process."""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    create_time: float
    num_threads: int
    first_seen: float = field(default_factory=time.time)
    last_cpu_time: float = 0.0
    stuck_count: int = 0
    
    def is_zombie(self) -> bool:
        """Check if process is a zombie."""
        return self.status == psutil.STATUS_ZOMBIE
    
    def is_high_cpu(self, threshold: float = 90.0) -> bool:
        """Check if process is using high CPU."""
        return self.cpu_percent > threshold
    
    def is_high_memory(self, threshold: float = 50.0) -> bool:
        """Check if process is using high memory."""
        return self.memory_percent > threshold
    
    def runtime_hours(self) -> float:
        """Get process runtime in hours."""
        return (time.time() - self.create_time) / 3600

class ProcessMonitor:
    """Monitors system processes for issues."""
    
    def __init__(self):
        self.tracked_processes: Dict[int, ProcessInfo] = {}
        self.zombie_pids: Set[int] = set()
        self.stuck_pids: Set[int] = set()
        self.high_cpu_pids: Set[int] = set()
        self.high_memory_pids: Set[int] = set()
        
        # Configuration
        self.stuck_threshold_seconds = 300  # 5 minutes
        self.high_cpu_threshold = 90.0  # 90%
        self.high_memory_threshold = 50.0  # 50%
        self.zombie_check_enabled = True
        self.stuck_check_enabled = True
        
        # Tracking
        self.last_check_time = time.time()
        self.check_interval = 30  # Check every 30 seconds
    
    def should_check(self) -> bool:
        """Check if enough time has passed for another check."""
        return (time.time() - self.last_check_time) >= self.check_interval
    
    def update_process_info(self, proc: psutil.Process) -> Optional[ProcessInfo]:
        """Update information for a single process."""
        try:
            with proc.oneshot():
                info = ProcessInfo(
                    pid=proc.pid,
                    name=proc.name(),
                    status=proc.status(),
                    cpu_percent=proc.cpu_percent(interval=0.1),
                    memory_percent=proc.memory_percent(),
                    create_time=proc.create_time(),
                    num_threads=proc.num_threads()
                )
                
                # If we've seen this process before, preserve tracking data
                if proc.pid in self.tracked_processes:
                    old_info = self.tracked_processes[proc.pid]
                    info.first_seen = old_info.first_seen
                    info.last_cpu_time = old_info.last_cpu_time
                    info.stuck_count = old_info.stuck_count
                
                return info
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
    
    def detect_stuck_process(self, info: ProcessInfo) -> bool:
        """Detect if a process appears to be stuck."""
        if not self.stuck_check_enabled:
            return False
        
        # Check if process has been using high CPU consistently
        if info.cpu_percent > 95.0:
            # Get CPU times to see if it's actually doing work
            try:
                proc = psutil.Process(info.pid)
                cpu_times = proc.cpu_times()
                current_cpu_time = cpu_times.user + cpu_times.system
                
                # If CPU time hasn't changed much but CPU% is high, might be stuck
                if info.last_cpu_time > 0:
                    time_delta = current_cpu_time - info.last_cpu_time
                    if time_delta < 0.1:  # Very little actual CPU work
                        info.stuck_count += 1
                        if info.stuck_count >= 3:  # Stuck for 3 checks
                            return True
                    else:
                        info.stuck_count = 0
                
                info.last_cpu_time = current_cpu_time
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        else:
            info.stuck_count = 0
        
        return False
    
    def detect_unresponsive_process(self, info: ProcessInfo) -> bool:
        """Detect if a process is unresponsive (not responding to signals)."""
        try:
            proc = psutil.Process(info.pid)
            
            # Check if process is in uninterruptible sleep for too long
            if info.status == psutil.STATUS_DISK_SLEEP:
                runtime = time.time() - info.first_seen
                if runtime > self.stuck_threshold_seconds:
                    return True
            
            # Check for processes with "not responding" in their status
            if hasattr(proc, 'status') and 'not responding' in str(proc.status()).lower():
                return True
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return False
    
    def scan_processes(self) -> Dict[str, List[ProcessInfo]]:
        """Scan all processes and categorize issues."""
        if not self.should_check():
            return {}
        
        self.last_check_time = time.time()
        
        issues = {
            'zombie': [],
            'stuck': [],
            'high_cpu': [],
            'high_memory': [],
            'unresponsive': []
        }
        
        # Clear old tracking sets
        self.zombie_pids.clear()
        self.stuck_pids.clear()
        self.high_cpu_pids.clear()
        self.high_memory_pids.clear()
        
        # Scan all processes
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                info = self.update_process_info(proc)
                if not info:
                    continue
                
                # Update tracked processes
                self.tracked_processes[info.pid] = info
                
                # Check for zombie processes
                if self.zombie_check_enabled and info.is_zombie():
                    issues['zombie'].append(info)
                    self.zombie_pids.add(info.pid)
                
                # Check for stuck processes
                if self.detect_stuck_process(info):
                    issues['stuck'].append(info)
                    self.stuck_pids.add(info.pid)
                
                # Check for unresponsive processes
                if self.detect_unresponsive_process(info):
                    issues['unresponsive'].append(info)
                
                # Check for high CPU usage
                if info.is_high_cpu(self.high_cpu_threshold):
                    issues['high_cpu'].append(info)
                    self.high_cpu_pids.add(info.pid)
                
                # Check for high memory usage
                if info.is_high_memory(self.high_memory_threshold):
                    issues['high_memory'].append(info)
                    self.high_memory_pids.add(info.pid)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Clean up tracked processes that no longer exist
        current_pids = {p.pid for p in psutil.process_iter(['pid'])}
        dead_pids = set(self.tracked_processes.keys()) - current_pids
        for pid in dead_pids:
            del self.tracked_processes[pid]
        
        return issues
    
    def get_problem_summary(self) -> Dict[str, int]:
        """Get a summary count of current problems."""
        return {
            'zombie': len(self.zombie_pids),
            'stuck': len(self.stuck_pids),
            'high_cpu': len(self.high_cpu_pids),
            'high_memory': len(self.high_memory_pids)
        }
    
    def get_top_cpu_processes(self, limit: int = 5) -> List[Tuple[str, int, float]]:
        """Get top CPU-consuming processes."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                cpu = proc.info['cpu_percent']
                if cpu is not None:
                    processes.append((
                        proc.info['name'],
                        proc.info['pid'],
                        cpu
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        processes.sort(key=lambda x: x[2] or 0, reverse=True)
        return processes[:limit]
    
    def get_top_memory_processes(self, limit: int = 5) -> List[Tuple[str, int, float]]:
        """Get top memory-consuming processes."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                mem = proc.info['memory_percent']
                if mem is not None:
                    processes.append((
                        proc.info['name'],
                        proc.info['pid'],
                        mem
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        processes.sort(key=lambda x: x[2] or 0, reverse=True)
        return processes[:limit]
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Kill a problematic process."""
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()  # SIGKILL
            else:
                proc.terminate()  # SIGTERM
            logger.info(f"{'Killed' if force else 'Terminated'} process {pid} ({proc.name()})")
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to kill process {pid}: {e}")
            return False
    
    def get_process_details(self, pid: int) -> Optional[Dict[str, any]]:
        """Get detailed information about a specific process."""
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                return {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'status': proc.status(),
                    'cpu_percent': proc.cpu_percent(interval=0.1),
                    'memory_percent': proc.memory_percent(),
                    'memory_mb': proc.memory_info().rss / 1024 / 1024,
                    'num_threads': proc.num_threads(),
                    'create_time': datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                    'cmdline': ' '.join(proc.cmdline()[:3]) if proc.cmdline() else '',
                    'username': proc.username()
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

# Singleton instance
_process_monitor = None

def get_process_monitor() -> ProcessMonitor:
    """Get the singleton process monitor instance."""
    global _process_monitor
    if _process_monitor is None:
        _process_monitor = ProcessMonitor()
    return _process_monitor
