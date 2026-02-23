# Speed Test Aggregation - Quick Start Guide

## What Is This?

The Speed Test Aggregation System automatically collects and analyzes all speed test data from your fleet machines. No configuration needed - it just works!

## ✅ Already Working!

The system is **already collecting data** from your speed test widgets. Every time a machine runs a speed test, the results are automatically:
1. Stored in the aggregation database
2. Available for analysis
3. Ready for reporting

## Quick Commands

### View Fleet Summary
```bash
# Last 24 hours
python3 -m atlas.speedtest_report

# Last 7 days
python3 -m atlas.speedtest_report --hours 168
```

### View Machine Stats
```bash
# Detailed statistics for a specific machine
python3 -m atlas.speedtest_report --machine Mac --hours 168
```

### Compare All Machines
```bash
# Side-by-side comparison
python3 -m atlas.speedtest_report --comparison --hours 24
```

### Detect Anomalies
```bash
# Find unusual speed test results
python3 -m atlas.speedtest_report --machine Mac --anomalies
```

## API Examples

### Get Fleet Summary
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/summary?hours=24"
```

### Get Machine Stats
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/machine?machine_id=Mac&hours=168"
```

### Get Comparison Report
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/comparison?hours=24"
```

### Detect Anomalies
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/anomalies?machine_id=Mac"
```

## Example Output

### Fleet Summary
```
============================================================
FLEET SPEED TEST REPORT - Last 24 Hours
============================================================

Fleet Summary:
  Total Tests: 48
  Machines Tested: 3

Average Speeds:
  Download: 245.7 Mbps
  Upload: 32.5 Mbps
  Ping: 12.3 ms

Per-Machine Results:

MacBook-Pro:
  Tests: 16
  Download: 280.5 Mbps
  Upload: 35.2 Mbps
  Ping: 10.5 ms
```

### Machine Statistics
```
============================================================
MACHINE STATISTICS - Mac
============================================================

Period: Last 168 hours
Tests: 112

Download Speed (Mbps)
  Average:    250.50
  Median:     248.30
  Min:        180.20
  Max:        310.50
  Std Dev:     25.30
```

### Comparison Report
```
Machine              Down       Up   Ping   vs Fleet  Tests
------------------------------------------------------------
MacBook-Pro        280.50    35.20  10.50     +14.2%     16
iMac-Office        245.00    32.00  12.00      -0.3%     16
Mac-Mini           211.50    30.30  14.50     -13.9%     16
```

## Python Usage

```python
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

# Create aggregator
agg = SpeedTestAggregator()

# Get fleet summary
summary = agg.get_fleet_summary(hours=24)
print(f"Fleet avg: {summary['avg_download_mbps']} Mbps")

# Get machine stats
stats = agg.get_machine_stats('Mac', hours=168)
print(f"Download: {stats['download']['avg']} Mbps")

# Detect anomalies
anomalies = agg.detect_anomalies('Mac')
print(f"Found {len(anomalies)} anomalies")
```

## What Data Is Tracked?

For each speed test:
- ✅ Download speed (Mbps)
- ✅ Upload speed (Mbps)
- ✅ Ping latency (ms)
- ✅ Jitter (ms)
- ✅ Packet loss (%)
- ✅ Server information
- ✅ ISP details
- ✅ Timestamp

## Where Is Data Stored?

```
~/.fleet-data/speedtest.sqlite3
```

You can query this database directly:
```bash
sqlite3 ~/.fleet-data/speedtest.sqlite3 "SELECT * FROM speedtest_results LIMIT 5"
```

## Use Cases

### 1. Monitor Network Performance
Track internet speeds across your fleet over time.

### 2. Troubleshoot Slow Connections
When a user reports slow internet, check their speed test history.

### 3. Compare Locations
See which office/location has the fastest internet.

### 4. Detect Issues
Automatically identify machines with consistently slow speeds.

### 5. Verify ISP Performance
Check if you're getting the speeds you're paying for.

## Tips

### Schedule Reports
```bash
# Add to crontab for weekly reports
0 9 * * 1 python3 -m atlas.speedtest_report --hours 168 | mail -s "Weekly Speed Test Report" admin@company.com
```

### Export to JSON
```bash
python3 -m atlas.speedtest_report --format json --hours 24 > speedtest_report.json
```

### Check Specific Time Period
```bash
# Last hour
python3 -m atlas.speedtest_report --hours 1

# Last month
python3 -m atlas.speedtest_report --hours 720
```

## Troubleshooting

### No Data Available
**Cause**: No speed tests have been run yet.

**Solution**: Wait for machines to run their scheduled speed tests, or run one manually from the dashboard.

### Old Data Missing
**Cause**: Aggregation started when feature was enabled.

**Solution**: Historical data before this feature won't be available. New data is collected going forward.

### Database Location
Check if database exists:
```bash
ls -lh ~/.fleet-data/speedtest.sqlite3
```

Count records:
```bash
sqlite3 ~/.fleet-data/speedtest.sqlite3 "SELECT COUNT(*) FROM speedtest_results"
```

## Next Steps

1. **Wait for data**: Let machines run speed tests naturally
2. **Check reports**: Run `python3 -m atlas.speedtest_report` after a few hours
3. **Set up alerts**: Create scripts to notify you of slow speeds
4. **Schedule reports**: Add to cron for regular updates

## Full Documentation

For complete details, see `SPEEDTEST_AGGREGATION.md`

---

**That's it! The system is already working and collecting data.** 🎉
