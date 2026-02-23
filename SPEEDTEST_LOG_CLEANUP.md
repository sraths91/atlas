# 🧹 Automatic Speed Test Log Cleanup

## Overview

The speed test logging system now automatically removes entries older than 1 week to prevent the log file from growing indefinitely.

---

## How It Works

### 1. Cleanup on Startup
When the application starts, it automatically:
- Reads the log file (`~/speedtest_history.csv`)
- Removes all entries older than 7 days
- Rewrites the file with only recent entries
- Logs how many entries were removed

### 2. Periodic Cleanup
While running, the system:
- Checks every 24 hours if cleanup is needed
- Automatically removes old entries
- Runs in the background without interrupting tests

### 3. Retention Policy
- **Keep:** All entries from the last 7 days
- **Remove:** Any entries older than 7 days
- **Cutoff:** Rolling 7-day window from current time

---

## Configuration

### Log File Location
```
~/speedtest_history.csv
```

### Retention Period
```python
# In speedtest_widget.py
cutoff_time = datetime.now() - timedelta(days=7)  # 7 days
```

### Cleanup Frequency
```python
# In speedtest_widget.py
self.cleanup_interval = 86400  # 24 hours (in seconds)
```

---

## Customization

### Change Retention Period

To keep logs for a different duration, edit `speedtest_widget.py`:

**Keep 30 days:**
```python
cutoff_time = datetime.now() - timedelta(days=30)
```

**Keep 3 days:**
```python
cutoff_time = datetime.now() - timedelta(days=3)
```

**Keep 1 month:**
```python
cutoff_time = datetime.now() - timedelta(days=30)
```

### Change Cleanup Frequency

**Run cleanup every 12 hours:**
```python
self.cleanup_interval = 43200  # 12 hours
```

**Run cleanup every week:**
```python
self.cleanup_interval = 604800  # 7 days
```

---

## Manual Cleanup

### View Current Log Size
```bash
wc -l ~/speedtest_history.csv
ls -lh ~/speedtest_history.csv
```

### Manually Remove Old Entries

**Keep last 7 days:**
```bash
python3 << 'EOF'
import csv
from datetime import datetime, timedelta

log_file = '~/speedtest_history.csv'
cutoff = datetime.now() - timedelta(days=7)

with open(log_file, 'r') as f:
    reader = csv.DictReader(f)
    recent = [row for row in reader 
              if datetime.fromisoformat(row['timestamp']) >= cutoff]

with open(log_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['timestamp', 'download', 'upload', 'ping', 'server'])
    writer.writeheader()
    writer.writerows(recent)

print(f"Kept {len(recent)} recent entries")
EOF
```

### Backup Before Cleanup
```bash
cp ~/speedtest_history.csv ~/speedtest_backup_$(date +%Y%m%d).csv
```

---

## Log Messages

### Startup Cleanup
```
INFO - Cleaned up 15 log entries older than 1 week. 120 entries remain.
```

### Periodic Cleanup
```
INFO - Running scheduled log cleanup...
INFO - Cleaned up 3 log entries older than 1 week. 125 entries remain.
```

### No Cleanup Needed
If no old entries exist, cleanup runs silently without logging.

---

## Benefits

### Automatic Maintenance
- ✅ No manual intervention required
- ✅ Log file stays manageable size
- ✅ Prevents disk space issues
- ✅ Maintains recent history

### Performance
- ✅ Faster file reads/writes
- ✅ Quicker exports
- ✅ Lower memory usage
- ✅ Efficient data access

### Data Management
- ✅ Keeps relevant data (1 week)
- ✅ Removes stale data automatically
- ✅ Predictable file size
- ✅ Easy to analyze recent trends

---

## Example Timeline

**Day 1 (Monday):**
- Test runs at 9:00 AM → Logged
- Test runs at 10:00 AM → Logged

**Day 7 (Sunday):**
- Test runs at 8:00 PM → Logged
- All tests from Day 1-7 remain

**Day 8 (Monday):**
- Cleanup runs at startup
- Tests from Day 1 (older than 7 days) → **Removed**
- Tests from Day 2-7 → Kept
- New test at 9:00 AM → Logged

**Day 9 (Tuesday):**
- Cleanup runs (24 hours since last)
- Tests from Day 2 (now older than 7 days) → **Removed**
- Tests from Day 3-8 → Kept

---

## Troubleshooting

### Cleanup Not Running

**Check logs:**
```bash
python3 -m atlas.app --simulated 2>&1 | grep -i cleanup
```

**Verify cleanup interval:**
```python
# Should see in logs on startup
logger.info(f"Cleanup interval: {self.cleanup_interval} seconds")
```

### Too Much Data Removed

**Increase retention period:**
```python
# Keep 14 days instead of 7
cutoff_time = datetime.now() - timedelta(days=14)
```

### Want to Keep All Data

**Disable automatic cleanup:**
```python
# Comment out cleanup calls in __init__ and _monitor_loop
# self._cleanup_old_logs()
```

**Or set very long retention:**
```python
# Keep 10 years
cutoff_time = datetime.now() - timedelta(days=3650)
```

---

## File Size Estimates

### With 1-minute test interval:
- **Tests per day:** 1,440
- **Tests per week:** 10,080
- **File size (7 days):** ~1.5 MB
- **File size (30 days):** ~6 MB

### With 5-minute test interval:
- **Tests per day:** 288
- **Tests per week:** 2,016
- **File size (7 days):** ~300 KB
- **File size (30 days):** ~1.2 MB

### With 1-hour test interval:
- **Tests per day:** 24
- **Tests per week:** 168
- **File size (7 days):** ~25 KB
- **File size (30 days):** ~100 KB

---

## Summary

✅ **Automatic cleanup** every 24 hours
✅ **7-day retention** by default
✅ **Runs on startup** to clean existing logs
✅ **Configurable** retention period
✅ **Silent operation** unless entries removed
✅ **No data loss** for recent tests

Your speed test logs will now stay clean and manageable automatically! 🎉
