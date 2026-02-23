# Speed Test: Recent 20 Average & Subnet Analysis

## New Features Added

### 1. **Recent 20 Tests Average**
Get the average of the most recent 20 speed tests per machine for a more current and stable performance metric.

### 2. **Subnet Analysis**
Analyze speed test performance grouped by IP subnet to identify network-specific issues or compare different locations/ISPs.

---

## Recent 20 Tests Average

### Why Use This?

Instead of averaging ALL tests over a time period, this gives you:
- ✅ **More current data** - Only the 20 most recent tests
- ✅ **Stable baseline** - Enough samples to smooth out anomalies
- ✅ **Consistent comparison** - Same sample size for all machines
- ✅ **Quick snapshot** - Current performance without time-based filtering

### CLI Usage

#### All Machines
```bash
python3 -m atlas.speedtest_report --recent20
```

**Output:**
```
============================================================
RECENT 20 TESTS AVERAGE - All Machines
============================================================

Machine              Tests   Download     Upload     Ping
------------------------------------------------------------
Mac                     20     221.65      33.44    20.89
MacBook-Pro             20     241.64      33.55    19.72
iMac                    20     227.40      33.35    20.53
```

#### Single Machine
```bash
python3 -m atlas.speedtest_report --recent20 --machine Mac
```

**Output:**
```
============================================================
RECENT 20 TESTS AVERAGE - Mac
============================================================

Machine: Mac
Tests Used: 20/20

Averages:
  Download: 221.65 Mbps
  Upload:   33.44 Mbps
  Ping:     20.89 ms
  Jitter:   2.45 ms
  Packet Loss: 0.15%
```

### API Usage

#### All Machines
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/recent20"
```

**Response:**
```json
{
  "Mac": {
    "test_count": 20,
    "avg_download_mbps": 221.65,
    "avg_upload_mbps": 33.44,
    "avg_ping_ms": 20.89,
    "avg_jitter_ms": 2.45,
    "avg_packet_loss": 0.15
  },
  "MacBook-Pro": {
    "test_count": 20,
    "avg_download_mbps": 241.64,
    "avg_upload_mbps": 33.55,
    "avg_ping_ms": 19.72,
    "avg_jitter_ms": 2.12,
    "avg_packet_loss": 0.08
  }
}
```

#### Single Machine
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/recent20?machine_id=Mac"
```

**Response:**
```json
{
  "machine_id": "Mac",
  "test_count": 20,
  "avg_download_mbps": 221.65,
  "avg_upload_mbps": 33.44,
  "avg_ping_ms": 20.89,
  "avg_jitter_ms": 2.45,
  "avg_packet_loss": 0.15
}
```

### Python Usage

```python
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

agg = SpeedTestAggregator()

# All machines
results = agg.get_recent_20_average()
for machine_id, stats in results.items():
    print(f"{machine_id}: {stats['avg_download_mbps']:.2f} Mbps")

# Single machine
stats = agg.get_recent_20_average('Mac')
print(f"Download: {stats['avg_download_mbps']:.2f} Mbps")
```

---

## Subnet Analysis

### Why Use This?

Analyze speed tests by IP subnet to:
- ✅ **Compare locations** - Office A vs Office B
- ✅ **Compare ISPs** - Different internet providers
- ✅ **Identify network issues** - Specific subnet performing poorly
- ✅ **Geographic analysis** - Different regions/cities
- ✅ **VPN vs Direct** - Compare connection types

### How It Works

The system:
1. Extracts the external IP from each speed test
2. Groups IPs into subnets (auto-detects /24 for IPv4, /64 for IPv6)
3. Calculates statistics per subnet
4. Shows which machines are in each subnet

### CLI Usage

#### All Subnets (Auto-detect)
```bash
python3 -m atlas.speedtest_report --subnet
```

**Output:**
```
============================================================
SUBNET ANALYSIS - All Subnets
============================================================

Total Subnets: 3
Total Tests: 76

Subnet Performance
------------------------------------------------------------

1.2.3.0/24:
  Machines: 3 (Mac, MacBook-Pro, iMac)
  IPs: 2
  Tests: 32
  Download: 235.35 Mbps (range: 160.00 - 320.00)
  Upload:   32.84 Mbps
  Ping:     20.15 ms

10.0.1.0/24:
  Machines: 3 (Mac, MacBook-Pro, iMac)
  IPs: 2
  Tests: 31
  Download: 237.69 Mbps (range: 165.00 - 315.00)
  Upload:   33.75 Mbps
  Ping:     19.85 ms

192.168.1.0/24:
  Machines: 3 (Mac, MacBook-Pro, iMac)
  IPs: 1
  Tests: 13
  Download: 228.00 Mbps (range: 170.00 - 310.00)
  Upload:   33.04 Mbps
  Ping:     21.25 ms
```

#### Specific Subnet
```bash
python3 -m atlas.speedtest_report --subnet 192.168.1.0/24
```

**Output:**
```
============================================================
SUBNET ANALYSIS - 192.168.1.0/24
============================================================

Total Subnets: 1
Total Tests: 13

192.168.1.0/24:
  Machines: 3 (Mac, MacBook-Pro, iMac)
  IPs: 1
  Tests: 13
  Download: 228.00 Mbps (range: 170.00 - 310.00)
  Upload:   33.04 Mbps
  Ping:     21.25 ms
```

### API Usage

#### All Subnets
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/subnet"
```

**Response:**
```json
{
  "subnets": {
    "1.2.3.0/24": {
      "machine_count": 3,
      "machines": ["Mac", "MacBook-Pro", "iMac"],
      "ip_count": 2,
      "ips": ["1.2.3.4", "1.2.3.5"],
      "test_count": 32,
      "avg_download_mbps": 235.35,
      "avg_upload_mbps": 32.84,
      "avg_ping_ms": 20.15,
      "min_download_mbps": 160.00,
      "max_download_mbps": 320.00
    },
    "10.0.1.0/24": {
      "machine_count": 3,
      "machines": ["Mac", "MacBook-Pro", "iMac"],
      "ip_count": 2,
      "ips": ["10.0.1.100", "10.0.1.101"],
      "test_count": 31,
      "avg_download_mbps": 237.69,
      "avg_upload_mbps": 33.75,
      "avg_ping_ms": 19.85,
      "min_download_mbps": 165.00,
      "max_download_mbps": 315.00
    }
  },
  "total_subnets": 2,
  "total_tests": 63
}
```

#### Specific Subnet
```bash
curl -k "https://localhost:8768/api/fleet/speedtest/subnet?subnet=192.168.1.0/24"
```

### Python Usage

```python
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

agg = SpeedTestAggregator()

# All subnets
analysis = agg.get_subnet_analysis()
for subnet, data in analysis['subnets'].items():
    print(f"{subnet}: {data['avg_download_mbps']:.2f} Mbps")

# Specific subnet
analysis = agg.get_subnet_analysis('192.168.1.0/24')
for subnet, data in analysis['subnets'].items():
    print(f"Machines in {subnet}: {', '.join(data['machines'])}")
```

---

## Use Cases

### Use Case 1: Current Performance Snapshot

**Scenario:** You want to know current network performance, not historical averages.

**Solution:**
```bash
python3 -m atlas.speedtest_report --recent20
```

This gives you the most recent 20 tests per machine, providing a current baseline without being affected by old data.

### Use Case 2: Compare Office Locations

**Scenario:** You have machines in different offices with different ISPs.

**Solution:**
```bash
python3 -m atlas.speedtest_report --subnet
```

Each office's public IP will be in a different subnet, allowing you to compare:
- Office A (1.2.3.0/24): 235 Mbps average
- Office B (10.0.1.0/24): 238 Mbps average
- Home Office (192.168.1.0/24): 228 Mbps average

### Use Case 3: VPN Performance Analysis

**Scenario:** Some machines use VPN, others don't. VPN gives different external IP.

**Solution:**
```bash
python3 -m atlas.speedtest_report --subnet
```

Compare:
- VPN subnet: Lower speeds, higher latency
- Direct subnet: Higher speeds, lower latency

### Use Case 4: ISP Comparison

**Scenario:** You have machines using different ISPs.

**Solution:**
```bash
python3 -m atlas.speedtest_report --subnet
```

Each ISP assigns IPs from different subnets, allowing direct comparison.

### Use Case 5: Troubleshooting Network Issues

**Scenario:** Users in one location report slow internet.

**Solution:**
```bash
# Check their subnet
python3 -m atlas.speedtest_report --subnet 10.0.1.0/24

# Compare to recent 20 average
python3 -m atlas.speedtest_report --recent20 --machine MacBook-Pro
```

Identify if issue is:
- Subnet-wide (affects all machines in that location)
- Machine-specific (only one machine affected)

---

## Comparison: Recent 20 vs Time-Based

### Time-Based (--hours 24)
- ✅ Shows trends over time
- ✅ Good for historical analysis
- ❌ Sample size varies by machine
- ❌ Affected by test frequency
- ❌ May include very old data

### Recent 20 (--recent20)
- ✅ Consistent sample size
- ✅ Current performance snapshot
- ✅ Not affected by test frequency
- ✅ Stable baseline
- ❌ No time-based trends

**Best Practice:** Use both!
- **Recent 20** for current status
- **Time-based** for trend analysis

---

## Advanced Examples

### Dashboard Integration

```javascript
// Fetch recent 20 average for all machines
async function loadCurrentPerformance() {
    const response = await fetch('/api/fleet/speedtest/recent20');
    const data = await response.json();
    
    // Display current speeds
    for (const [machine, stats] of Object.entries(data)) {
        updateMachineCard(machine, stats.avg_download_mbps);
    }
}

// Fetch subnet analysis
async function loadSubnetComparison() {
    const response = await fetch('/api/fleet/speedtest/subnet');
    const data = await response.json();
    
    // Create comparison chart
    createSubnetChart(data.subnets);
}
```

### Alerting Based on Recent Performance

```python
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

def check_current_performance():
    """Alert if recent performance is below threshold"""
    agg = SpeedTestAggregator()
    results = agg.get_recent_20_average()
    
    for machine_id, stats in results.items():
        if stats['avg_download_mbps'] < 50:  # Threshold
            send_alert(
                f"⚠️ {machine_id} current speed: {stats['avg_download_mbps']:.1f} Mbps "
                f"(based on last {stats['test_count']} tests)"
            )
```

### Subnet Performance Report

```python
from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

def generate_subnet_report():
    """Generate subnet comparison report"""
    agg = SpeedTestAggregator()
    analysis = agg.get_subnet_analysis()
    
    report = []
    report.append("SUBNET PERFORMANCE COMPARISON\n")
    
    # Sort by download speed
    subnets = sorted(
        analysis['subnets'].items(),
        key=lambda x: x[1]['avg_download_mbps'],
        reverse=True
    )
    
    for subnet, data in subnets:
        report.append(f"\n{subnet}:")
        report.append(f"  Machines: {', '.join(data['machines'])}")
        report.append(f"  Download: {data['avg_download_mbps']:.1f} Mbps")
        report.append(f"  Upload: {data['avg_upload_mbps']:.1f} Mbps")
        report.append(f"  Ping: {data['avg_ping_ms']:.1f} ms")
    
    return '\n'.join(report)
```

---

## API Reference

### GET /api/fleet/speedtest/recent20

Get average of recent 20 tests per machine.

**Parameters:**
- `machine_id` (optional): Specific machine ID

**Response:**
```json
{
  "machine_id": {
    "test_count": 20,
    "avg_download_mbps": 250.5,
    "avg_upload_mbps": 32.5,
    "avg_ping_ms": 12.5,
    "avg_jitter_ms": 2.3,
    "avg_packet_loss": 0.1
  }
}
```

### GET /api/fleet/speedtest/subnet

Analyze speed tests by IP subnet.

**Parameters:**
- `subnet` (optional): Specific subnet in CIDR notation (e.g., `192.168.1.0/24`)

**Response:**
```json
{
  "subnets": {
    "192.168.1.0/24": {
      "machine_count": 3,
      "machines": ["Mac", "MacBook-Pro"],
      "ip_count": 2,
      "ips": ["192.168.1.50", "192.168.1.51"],
      "test_count": 45,
      "avg_download_mbps": 245.5,
      "avg_upload_mbps": 32.5,
      "avg_ping_ms": 12.5,
      "min_download_mbps": 180.0,
      "max_download_mbps": 310.0
    }
  },
  "total_subnets": 1,
  "total_tests": 45
}
```

---

## Summary

### Recent 20 Average
- ✅ Current performance snapshot
- ✅ Consistent sample size across machines
- ✅ Stable baseline without anomalies
- ✅ Quick to calculate
- 📊 Perfect for dashboards and current status

### Subnet Analysis
- ✅ Compare locations/offices
- ✅ Compare ISPs
- ✅ Identify network-specific issues
- ✅ Geographic performance analysis
- 🌐 Perfect for multi-location deployments

**Both features are available now via CLI, API, and Python!** 🚀

---

*For complete speed test documentation, see `SPEEDTEST_AGGREGATION.md`*
