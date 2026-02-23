# Speed Test Aggregation System

## Overview

The Speed Test Aggregation System automatically collects, stores, and analyzes speed test data from all machines in your fleet. It provides comprehensive analytics, comparisons, anomaly detection, and reporting capabilities.

## Features

### ✅ Automatic Data Collection
- **Seamless Integration**: Automatically captures speed test results from widget logs
- **No Configuration Required**: Works out-of-the-box with existing speed test widgets
- **Persistent Storage**: Stores all results in SQLite database for historical analysis

### 📊 Analytics & Reporting
- **Fleet-Wide Summary**: Aggregate statistics across all machines
- **Machine-Specific Stats**: Detailed analysis for individual machines
- **Comparison Reports**: Side-by-side performance comparison
- **Time Series Data**: Track trends over time
- **Anomaly Detection**: Automatically identify unusual results

### 🎯 Key Metrics Tracked
- Download speed (Mbps)
- Upload speed (Mbps)
- Ping latency (ms)
- Jitter (ms)
- Packet loss (%)
- Server information
- ISP details
- Test duration

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Fleet Agents                         │
│  (Run speed tests via widgets, send results to server)  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Fleet Server                           │
│  - Receives widget logs                                 │
│  - Extracts speed test results                          │
│  - Stores in aggregation database                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            SpeedTestAggregator                          │
│  - Stores results in SQLite                             │
│  - Calculates statistics                                │
│  - Detects anomalies                                    │
│  - Generates reports                                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  API Endpoints                          │
│  /api/fleet/speedtest/summary                           │
│  /api/fleet/speedtest/machine                           │
│  /api/fleet/speedtest/comparison                        │
│  /api/fleet/speedtest/anomalies                         │
│  /api/fleet/speedtest/recent                            │
└─────────────────────────────────────────────────────────┘
```

### Database Schema

**speedtest_results** table:
```sql
- id (PRIMARY KEY)
- machine_id (indexed)
- timestamp (indexed)
- download_mbps
- upload_mbps
- ping_ms
- jitter_ms
- packet_loss
- server_name
- server_location
- isp
- external_ip
- result_url
- test_duration_seconds
- raw_data (JSON)
- created_at
```

**speedtest_stats** table (aggregated):
```sql
- id (PRIMARY KEY)
- machine_id
- period (hourly/daily/weekly)
- period_start
- period_end
- test_count
- avg/min/max/median for download/upload/ping
- created_at
```

## Usage

### API Endpoints

#### 1. Fleet Summary
Get aggregate statistics for entire fleet:

```bash
GET /api/fleet/speedtest/summary?hours=24
```

**Response:**
```json
{
  "period_hours": 24,
  "test_count": 48,
  "machine_count": 3,
  "avg_download_mbps": 245.67,
  "avg_upload_mbps": 32.45,
  "avg_ping_ms": 12.3,
  "min_download_mbps": 180.5,
  "max_download_mbps": 310.2,
  "machines": [
    {
      "machine_id": "MacBook-Pro",
      "test_count": 16,
      "avg_download_mbps": 280.5,
      "avg_upload_mbps": 35.2,
      "avg_ping_ms": 10.5,
      "last_test": "2025-11-19T23:30:00"
    }
  ]
}
```

#### 2. Machine Statistics
Get detailed stats for specific machine:

```bash
GET /api/fleet/speedtest/machine?machine_id=Mac&hours=168
```

**Response:**
```json
{
  "machine_id": "Mac",
  "period_hours": 168,
  "test_count": 112,
  "download": {
    "avg": 250.5,
    "median": 248.3,
    "min": 180.2,
    "max": 310.5,
    "stdev": 25.3
  },
  "upload": {
    "avg": 32.5,
    "median": 31.8,
    "min": 25.0,
    "max": 38.2,
    "stdev": 3.2
  },
  "ping": {
    "avg": 12.5,
    "median": 11.8,
    "min": 8.5,
    "max": 25.3,
    "stdev": 4.2
  },
  "time_series": [
    {
      "timestamp": "2025-11-19T00:00:00",
      "download": 245.5,
      "upload": 32.0,
      "ping": 12.0
    }
  ]
}
```

#### 3. Comparison Report
Compare all machines side-by-side:

```bash
GET /api/fleet/speedtest/comparison?hours=24
```

**Response:**
```json
{
  "period_hours": 24,
  "fleet_avg_download": 245.67,
  "fleet_avg_upload": 32.45,
  "fleet_avg_ping": 12.3,
  "machines": [
    {
      "machine_id": "MacBook-Pro",
      "avg_download": 280.5,
      "avg_upload": 35.2,
      "avg_ping": 10.5,
      "download_vs_fleet": 14.2,
      "upload_vs_fleet": 8.5,
      "variability": 45.3,
      "test_count": 16
    }
  ]
}
```

#### 4. Anomaly Detection
Detect unusual speed test results:

```bash
GET /api/fleet/speedtest/anomalies?machine_id=Mac
```

**Response:**
```json
{
  "anomalies": [
    {
      "timestamp": "2025-11-19T15:30:00",
      "issues": [
        "Download: 120.5 Mbps (avg: 250.5)",
        "Ping: 45.2 ms (avg: 12.5)"
      ],
      "download_mbps": 120.5,
      "upload_mbps": 30.2,
      "ping_ms": 45.2
    }
  ],
  "count": 1
}
```

#### 5. Recent Results
Get raw speed test results:

```bash
GET /api/fleet/speedtest/recent?machine_id=Mac&hours=24&limit=10
```

### CLI Tool

Generate reports from command line:

```bash
# Fleet summary (last 24 hours)
python3 -m atlas.speedtest_report

# Fleet summary (last 7 days)
python3 -m atlas.speedtest_report --hours 168

# Machine-specific stats
python3 -m atlas.speedtest_report --machine Mac --hours 168

# Comparison report
python3 -m atlas.speedtest_report --comparison --hours 24

# Detect anomalies
python3 -m atlas.speedtest_report --machine Mac --anomalies

# JSON output
python3 -m atlas.speedtest_report --format json --hours 24
```

### Python API

Use the aggregator directly in your code:

```python
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

# Create aggregator
aggregator = SpeedTestAggregator()

# Get fleet summary
summary = aggregator.get_fleet_summary(hours=24)
print(f"Fleet average download: {summary['avg_download_mbps']} Mbps")

# Get machine stats
stats = aggregator.get_machine_stats('Mac', hours=168)
print(f"Download: {stats['download']['avg']} ± {stats['download']['stdev']} Mbps")

# Detect anomalies
anomalies = aggregator.detect_anomalies('Mac')
if anomalies:
    print(f"Found {len(anomalies)} anomalous results")

# Generate text report
report = aggregator.generate_report(format='text', hours=24)
print(report)
```

## Example Reports

### Fleet Summary Report

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

Speed Range:
  Download: 180.5 - 310.2 Mbps
  Upload: 25.0 - 38.2 Mbps
  Ping: 8.5 - 25.3 ms

------------------------------------------------------------
Per-Machine Results:
------------------------------------------------------------

MacBook-Pro:
  Tests: 16
  Download: 280.5 Mbps
  Upload: 35.2 Mbps
  Ping: 10.5 ms
  Last Test: 2025-11-19T23:30:00

iMac-Office:
  Tests: 16
  Download: 245.0 Mbps
  Upload: 32.0 Mbps
  Ping: 12.0 ms
  Last Test: 2025-11-19T23:25:00

Mac-Mini:
  Tests: 16
  Download: 211.5 Mbps
  Upload: 30.3 Mbps
  Ping: 14.5 ms
  Last Test: 2025-11-19T23:20:00

============================================================
```

### Comparison Report

```
============================================================
FLEET COMPARISON REPORT - Last 24 Hours
============================================================

Fleet Averages:
  Download: 245.67 Mbps
  Upload:   32.45 Mbps
  Ping:     12.30 ms

Machine Performance
------------------------------------------------------------
Machine              Down       Up   Ping   vs Fleet  Tests
------------------------------------------------------------
MacBook-Pro        280.50    35.20  10.50     +14.2%     16
iMac-Office        245.00    32.00  12.00      -0.3%     16
Mac-Mini           211.50    30.30  14.50     -13.9%     16
```

### Machine Statistics

```
============================================================
MACHINE STATISTICS - Mac
============================================================

Period: Last 168 hours
Tests: 112
First Test: 2025-11-12T23:30:00
Last Test: 2025-11-19T23:30:00

Download Speed (Mbps)----------------------------------------
  Average:    250.50
  Median:     248.30
  Min:        180.20
  Max:        310.50
  Std Dev:     25.30

Upload Speed (Mbps)------------------------------------------
  Average:     32.50
  Median:      31.80
  Min:         25.00
  Max:         38.20
  Std Dev:      3.20

Ping (ms)----------------------------------------------------
  Average:     12.50
  Median:      11.80
  Min:          8.50
  Max:         25.30
  Std Dev:      4.20
```

## Use Cases

### 1. Network Performance Monitoring
Track internet speed across your fleet to identify:
- Slow connections
- Network degradation over time
- ISP performance issues
- Peak usage times

### 2. Troubleshooting
When a user reports slow internet:
- Check their machine's speed test history
- Compare to fleet average
- Identify if issue is machine-specific or fleet-wide
- Detect anomalies in recent tests

### 3. Capacity Planning
Analyze trends to:
- Predict when bandwidth upgrades are needed
- Identify machines that need better connectivity
- Plan for remote work requirements

### 4. SLA Monitoring
If you have ISP SLAs:
- Track actual vs promised speeds
- Generate reports for ISP disputes
- Monitor uptime and reliability

### 5. Location Comparison
Compare speeds across:
- Different offices
- Home vs office connections
- Different ISPs

## Integration Examples

### Dashboard Widget

```javascript
// Fetch and display fleet summary
async function loadSpeedTestSummary() {
    const response = await fetch('/api/fleet/speedtest/summary?hours=24');
    const data = await response.json();
    
    document.getElementById('avg-download').textContent = 
        `${data.avg_download_mbps.toFixed(1)} Mbps`;
    document.getElementById('avg-upload').textContent = 
        `${data.avg_upload_mbps.toFixed(1)} Mbps`;
    document.getElementById('avg-ping').textContent = 
        `${data.avg_ping_ms.toFixed(1)} ms`;
}
```

### Alerting System

```python
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

def check_slow_connections():
    """Alert if any machine has consistently slow speeds"""
    aggregator = SpeedTestAggregator()
    summary = aggregator.get_fleet_summary(hours=24)
    
    for machine in summary['machines']:
        if machine['avg_download_mbps'] < 50:  # Threshold
            send_alert(
                f"⚠️ Slow connection detected on {machine['machine_id']}: "
                f"{machine['avg_download_mbps']:.1f} Mbps"
            )
```

### Scheduled Reports

```python
import schedule
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

def weekly_report():
    """Generate and email weekly speed test report"""
    aggregator = SpeedTestAggregator()
    report = aggregator.generate_report(format='text', hours=168)
    send_email('admin@company.com', 'Weekly Speed Test Report', report)

# Run every Monday at 9am
schedule.every().monday.at("09:00").do(weekly_report)
```

## Performance Considerations

### Database Size
- Each speed test result: ~1-2 KB
- 100 machines × 24 tests/day × 30 days = ~72,000 records = ~144 MB
- Recommended: Implement cleanup for results older than 90 days

### Query Performance
- Indexes on `machine_id` and `timestamp` for fast queries
- Aggregated stats table for pre-computed summaries
- Typical query time: <100ms for 30 days of data

### Storage Location
- Default: `~/.fleet-data/speedtest.sqlite3`
- Can be configured to use different path
- Separate from main fleet database for modularity

## Troubleshooting

### No Data Showing Up

**Check if speed tests are running:**
```bash
# Check widget logs
curl -k https://localhost:8768/api/fleet/widget-logs?widget_type=speedtest&limit=10
```

**Check aggregator database:**
```bash
sqlite3 ~/.fleet-data/speedtest.sqlite3 "SELECT COUNT(*) FROM speedtest_results"
```

### Anomaly Detection Too Sensitive

Adjust the threshold (default is 2 standard deviations):
```python
anomalies = aggregator.detect_anomalies('Mac', threshold_std=3.0)  # Less sensitive
```

### Missing Historical Data

Speed test aggregation was added recently. Historical data before this feature won't be available. Data collection starts from when the feature is enabled.

## Future Enhancements

Potential additions:
- [ ] Automated cleanup of old results
- [ ] Export to CSV/Excel
- [ ] Graphical charts and visualizations
- [ ] Email/Slack notifications for anomalies
- [ ] Bandwidth usage correlation
- [ ] ISP comparison reports
- [ ] Geographic location tracking
- [ ] Cost analysis (if bandwidth is metered)

## Summary

The Speed Test Aggregation System provides:

✅ **Automatic collection** of speed test data from all machines
✅ **Comprehensive analytics** with statistics and trends
✅ **Anomaly detection** to identify unusual results
✅ **Comparison reports** across machines
✅ **Flexible API** for custom integrations
✅ **CLI tool** for quick reports
✅ **Historical tracking** for long-term analysis

**No configuration required** - it works automatically with your existing speed test widgets!

---

*For questions or issues, check the server logs at `~/Library/Logs/fleet_server.log`*
