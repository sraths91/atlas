# 🔍 Process Monitoring Feature

## Overview

The Process Monitoring feature automatically detects and alerts you about problematic processes on your Mac, including:

- **Zombie processes** 🧟 - Dead processes that haven't been cleaned up
- **Stuck processes** 🔒 - Processes consuming high CPU but not making progress
- **Unresponsive processes** ❌ - Processes in uninterruptible sleep
- **High CPU consumers** 📊 - Processes using excessive CPU
- **High memory consumers** 💾 - Processes using excessive memory

---

## Features

### Automatic Detection
- Scans all running processes every 30 seconds
- Tracks process behavior over time
- Detects patterns indicating problems
- Triggers alerts for critical issues

### Smart Thresholds
- **Stuck detection**: 3 consecutive checks with high CPU but no progress
- **High CPU**: > 90% usage
- **High memory**: > 50% usage
- **Unresponsive**: In disk sleep for > 5 minutes

### macOS Notifications
Get instant alerts when problems are detected:
- Zombie process notifications
- Stuck process warnings
- Unresponsive process alerts

---

## Usage

### Enable Process Monitoring (Default)
```bash
# Process monitoring is enabled by default
python3 -m atlas.app --simulated
```

### Disable Process Monitoring
```bash
python3 -m atlas.app --simulated --no-process-monitor
```

### View Problematic Processes
```bash
python3 -m atlas.app --show-processes
```

Output:
```
⚠️  Problematic Processes
======================================================================
  Zombie processes:      0
  Stuck processes:       0
  High CPU processes:    0
  High memory processes: 0
======================================================================

📊 Top CPU Processes:
  - WindowServer                 (PID:    123)   15.3%
  - Google Chrome Helper         (PID:   4567)   12.1%
  - python3                      (PID:   8901)    8.5%

💾 Top Memory Processes:
  - Google Chrome                (PID:   1234)   18.2%
  - Windsurf                     (PID:   5678)   12.5%
  - Slack                        (PID:   9012)    8.7%
======================================================================
```

### Customize Top Process Count
```bash
# Show top 10 CPU and memory processes
python3 -m atlas.app --show-processes --top-cpu 10 --top-memory 10
```

---

## Alert Types

### 1. Zombie Process Alert
**When:** A zombie process is detected
**Message:** `Zombie process detected: [name] (PID: [pid])`
**Action:** Usually harmless, but indicates parent process isn't cleaning up properly

### 2. Stuck Process Alert
**When:** Process uses high CPU (>95%) for 3+ checks without making progress
**Message:** `Stuck process: [name] (PID: [pid], CPU: [percent]%)`
**Action:** May need to kill the process

### 3. Unresponsive Process Alert
**When:** Process is in uninterruptible sleep for > 5 minutes
**Message:** `Unresponsive process: [name] (PID: [pid])`
**Action:** Check if waiting on I/O, may need system restart

---

## Configuration

### Adjust Thresholds (Python API)

```python
from atlas.process_monitor import get_process_monitor

monitor = get_process_monitor()

# Adjust thresholds
monitor.high_cpu_threshold = 80.0  # Alert at 80% instead of 90%
monitor.high_memory_threshold = 60.0  # Alert at 60% instead of 50%
monitor.stuck_threshold_seconds = 600  # 10 minutes instead of 5

# Adjust check interval
monitor.check_interval = 60  # Check every 60 seconds instead of 30
```

### Enable/Disable Specific Checks

```python
monitor = get_process_monitor()

# Disable zombie checking
monitor.zombie_check_enabled = False

# Disable stuck process detection
monitor.stuck_check_enabled = False
```

---

## Advanced Usage

### Get Process Details

```python
from atlas.process_monitor import get_process_monitor

monitor = get_process_monitor()

# Get detailed info about a specific process
details = monitor.get_process_details(1234)
print(details)
```

Output:
```python
{
    'pid': 1234,
    'name': 'Google Chrome',
    'status': 'running',
    'cpu_percent': 15.3,
    'memory_percent': 18.2,
    'memory_mb': 2048.5,
    'num_threads': 42,
    'create_time': '2025-11-08 09:00:00',
    'cmdline': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'username': 'samraths'
}
```

### Kill a Problematic Process

```python
from atlas.process_monitor import get_process_monitor

monitor = get_process_monitor()

# Terminate gracefully (SIGTERM)
monitor.kill_process(1234, force=False)

# Force kill (SIGKILL)
monitor.kill_process(1234, force=True)
```

### Scan for Issues Programmatically

```python
from atlas.process_monitor import get_process_monitor

monitor = get_process_monitor()

# Scan all processes
issues = monitor.scan_processes()

# Check what was found
if issues['zombie']:
    print(f"Found {len(issues['zombie'])} zombie processes")

if issues['stuck']:
    print(f"Found {len(issues['stuck'])} stuck processes")
    for proc in issues['stuck']:
        print(f"  - {proc.name} (PID: {proc.pid})")

# Get summary counts
summary = monitor.get_problem_summary()
print(f"Total issues: {sum(summary.values())}")
```

---

## Integration with Alerts

Process monitoring is fully integrated with the alert system:

```python
from atlas.alerts import alert_manager
from atlas.process_monitor import get_process_monitor

monitor = get_process_monitor()
issues = monitor.scan_processes()

# Check and trigger alerts
alerts = alert_manager.check_process_issues(issues)

# Alerts are automatically:
# 1. Sent as macOS notifications
# 2. Stored in alert history
# 3. Saved to database (if history enabled)
```

---

## Database Integration

All process alerts are stored in the database:

```bash
# View recent process alerts
python3 -m atlas.app --show-alerts
```

Output:
```
🔔 Recent Alerts (Last 24 Hours)
==================================================
  [2025-11-08 09:15:30] Stuck process: Chrome Helper (PID: 4567, CPU: 98.5%)
  [2025-11-08 08:45:12] Zombie process detected: defunct (PID: 1234)
  [2025-11-08 07:30:45] Unresponsive process: diskutil (PID: 8901)
==================================================
```

---

## Common Scenarios

### Scenario 1: Find What's Slowing Down Your Mac
```bash
python3 -m atlas.app --show-processes --top-cpu 10
```

### Scenario 2: Check for Memory Leaks
```bash
# Run app with monitoring
python3 -m atlas.app --simulated

# Check memory usage over time
python3 -m atlas.app --show-stats
```

### Scenario 3: Debug Stuck Application
```bash
# Enable process monitoring with fast refresh
python3 -m atlas.app --simulated --refresh-rate 0.5

# You'll get alerts if any process gets stuck
```

### Scenario 4: Clean System Monitoring
```bash
# Monitor without process checking (less overhead)
python3 -m atlas.app --simulated --no-process-monitor
```

---

## Performance Impact

### Resource Usage
- **CPU overhead:** < 0.5% (scans every 30 seconds)
- **Memory overhead:** ~2-3MB
- **Disk I/O:** Minimal (only when writing alerts)

### Optimization Tips
1. Increase check interval for less overhead:
   ```python
   monitor.check_interval = 60  # Check every minute
   ```

2. Disable specific checks you don't need:
   ```python
   monitor.zombie_check_enabled = False
   ```

3. Disable process monitoring entirely:
   ```bash
   --no-process-monitor
   ```

---

## Troubleshooting

### No Alerts Showing
- Check if process monitoring is enabled (not using `--no-process-monitor`)
- Verify alert system is enabled (not using `--no-alerts`)
- Check macOS notification permissions

### False Positives
- Adjust thresholds higher:
  ```python
  monitor.high_cpu_threshold = 95.0  # More strict
  ```
- Increase stuck detection time:
  ```python
  monitor.stuck_threshold_seconds = 600  # 10 minutes
  ```

### High CPU Usage from Monitoring
- Increase check interval:
  ```python
  monitor.check_interval = 60  # Check less frequently
  ```
- Disable stuck process detection (most CPU-intensive):
  ```python
  monitor.stuck_check_enabled = False
  ```

---

## Examples

### Example 1: Monitor Development Environment
```bash
# Fast refresh with process monitoring
python3 -m atlas.app \
  --simulated \
  --layout performance \
  --refresh-rate 0.5
```

### Example 2: Server Monitoring
```bash
# Slower refresh, focus on process issues
python3 -m atlas.app \
  --simulated \
  --refresh-rate 5.0 \
  --no-history
```

### Example 3: Debugging Session
```bash
# Show current process status
python3 -m atlas.app --show-processes

# Run with monitoring
python3 -m atlas.app --simulated --refresh-rate 1.0

# Check alerts after a while
python3 -m atlas.app --show-alerts
```

---

## API Reference

### ProcessMonitor Class

```python
class ProcessMonitor:
    # Configuration
    stuck_threshold_seconds: int = 300
    high_cpu_threshold: float = 90.0
    high_memory_threshold: float = 50.0
    zombie_check_enabled: bool = True
    stuck_check_enabled: bool = True
    check_interval: int = 30
    
    # Methods
    def scan_processes() -> Dict[str, List[ProcessInfo]]
    def get_problem_summary() -> Dict[str, int]
    def get_top_cpu_processes(limit: int) -> List[Tuple[str, int, float]]
    def get_top_memory_processes(limit: int) -> List[Tuple[str, int, float]]
    def kill_process(pid: int, force: bool) -> bool
    def get_process_details(pid: int) -> Optional[Dict]
```

### ProcessInfo Class

```python
@dataclass
class ProcessInfo:
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    create_time: float
    num_threads: int
    
    def is_zombie() -> bool
    def is_high_cpu(threshold: float) -> bool
    def is_high_memory(threshold: float) -> bool
    def runtime_hours() -> float
```

---

## Summary

Process monitoring adds intelligent process management to Atlas:

✅ **Automatic detection** of problematic processes
✅ **Real-time alerts** via macOS notifications
✅ **Historical tracking** in database
✅ **Top process lists** for CPU and memory
✅ **Customizable thresholds** and behavior
✅ **Low overhead** (< 0.5% CPU)

Now you can catch stuck processes, memory leaks, and system issues before they become problems! 🚀
