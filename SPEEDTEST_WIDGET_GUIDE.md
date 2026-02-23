# 🚀 Speed Test Widget - Internet Speed Monitor

## Overview

The Speed Test Widget automatically tests your internet connection speed using speedtest.net every 60 seconds. You can also trigger manual tests on demand.

## Features

✅ **Automatic Testing** - Runs every 60 seconds
✅ **Manual Testing** - Click "Run Test Now" button
✅ **Beautiful UI** - Animated gradients and smooth transitions
✅ **Real-time Updates** - See results as they come in
✅ **Server Information** - Shows which speedtest server was used
✅ **Ping Monitoring** - Displays latency

---

## Installation

### 1. Install speedtest-cli

```bash
pip3 install speedtest-cli
```

### 2. Start the App

```bash
python3 -m atlas.app --simulated --refresh-rate 1.0
```

The speed test monitor will start automatically and run tests every 60 seconds.

---

## Usage

### View the Widget

**Standalone Widget:**
```
http://localhost:8767/widget/speedtest
```

**Full Dashboard:**
```
http://localhost:8767
```

### API Endpoints

**Get Last Result:**
```bash
curl http://localhost:8767/api/speedtest
```

**Response:**
```json
{
    "download": 125.45,
    "upload": 45.23,
    "ping": 12.5,
    "server": "Comcast - San Francisco, CA",
    "timestamp": "2025-11-12T18:15:30.123456",
    "status": "complete",
    "error": null
}
```

**Trigger Manual Test:**
```bash
curl -X POST http://localhost:8767/api/speedtest/run
```

**Response:**
```json
{
    "status": "started",
    "message": "Speed test started"
}
```

---

## Widget Display

### Layout

```
┌─────────────────────────────┐
│      SPEED TEST             │
│   Comcast - San Francisco   │
├─────────────────────────────┤
│                             │
│    ↓ Download               │
│      125.45 Mbps            │
│                             │
│    ↑ Upload                 │
│      45.23 Mbps             │
│                             │
├─────────────────────────────┤
│   Ping: 12.5   Jitter: --   │
├─────────────────────────────┤
│    [Run Test Now]           │
│                             │
│   Test complete             │
│   Last test: 6:15:30 PM     │
└─────────────────────────────┘
```

### Status Indicators

- **Waiting for test...** - Initial state, no test run yet
- **Testing speed...** - Test in progress (animated)
- **Test complete** - Test finished successfully
- **Error: [message]** - Test failed

---

## Features

### 1. Automatic Testing

The widget automatically runs a speed test every 60 seconds:
- Download speed (Mbps)
- Upload speed (Mbps)
- Ping latency (ms)
- Server information

### 2. Manual Testing

Click the "Run Test Now" button to trigger an immediate test:
- Button disables during test
- Widget shows animated "Testing..." state
- Results update in real-time

### 3. Visual Feedback

**Download Speed:**
- Green gradient (#00ff64 → #00c850)
- Large, bold numbers

**Upload Speed:**
- Orange gradient (#ff6400 → #ff3000)
- Large, bold numbers

**Ping:**
- Cyan color (#00c8ff)
- Displayed with jitter

**Testing Animation:**
- Pulsing opacity effect
- Yellow status text
- Disabled button

---

## Configuration

### Change Test Interval

Edit `live_widgets.py`:

```python
# Change from 60 seconds to 120 seconds
speed_monitor.start(interval=120)
```

### Disable Auto-Testing

To only run manual tests:

```python
# Don't start automatic testing
# speed_monitor.start(interval=60)
```

Then use the "Run Test Now" button or API to trigger tests manually.

---

## Troubleshooting

### "speedtest-cli not installed" Error

**Solution:**
```bash
pip3 install speedtest-cli
```

### Speed Test Takes Too Long

Speed tests typically take 15-30 seconds. If they're taking longer:
- Check your internet connection
- Try a different speedtest server
- Increase the test interval

### Widget Shows "Error"

**Common Causes:**
1. No internet connection
2. Speedtest.net is down
3. Firewall blocking connection

**Check logs:**
```bash
# Look for speedtest errors in app output
python3 -m atlas.app --simulated 2>&1 | grep -i speedtest
```

### Widget Not Updating

**Refresh the page:**
- The widget polls every 2 seconds
- If stuck, hard refresh (Cmd+Shift+R)

---

## Performance

### Resource Usage

**Per Test:**
- Duration: 15-30 seconds
- CPU: 5-10% during test
- Network: ~100MB download + ~50MB upload
- Memory: ~20MB

**Idle:**
- CPU: < 0.1%
- Memory: ~5MB

### Bandwidth Impact

Running tests every 60 seconds will use approximately:
- **Download:** ~6GB/hour
- **Upload:** ~3GB/hour

**Recommendation:** Use 5-minute intervals (300 seconds) for continuous monitoring to reduce bandwidth usage.

---

## Integration Examples

### Example 1: Embed in Dashboard

```html
<iframe src="http://localhost:8767/widget/speedtest" 
        width="320" height="420" 
        frameborder="0">
</iframe>
```

### Example 2: Get Data with JavaScript

```javascript
async function getSpeedTestResults() {
    const response = await fetch('http://localhost:8767/api/speedtest');
    const data = await response.json();
    
    console.log(`Download: ${data.download} Mbps`);
    console.log(`Upload: ${data.upload} Mbps`);
    console.log(`Ping: ${data.ping} ms`);
    
    return data;
}

// Trigger a new test
async function runSpeedTest() {
    const response = await fetch('http://localhost:8767/api/speedtest/run', {
        method: 'POST'
    });
    const result = await response.json();
    console.log(result.message);
}
```

### Example 3: Monitor Speed Over Time

```python
import requests
import time
import csv

# Collect speed test results
results = []

while True:
    response = requests.get('http://localhost:8767/api/speedtest')
    data = response.json()
    
    if data['status'] == 'complete':
        results.append({
            'timestamp': data['timestamp'],
            'download': data['download'],
            'upload': data['upload'],
            'ping': data['ping']
        })
        
        # Save to CSV
        with open('speed_history.csv', 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'download', 'upload', 'ping'])
            writer.writeheader()
            writer.writerows(results)
    
    time.sleep(60)
```

---

## API Reference

### GET /api/speedtest

Get the last speed test result.

**Response:**
```json
{
    "download": 125.45,      // Download speed in Mbps
    "upload": 45.23,         // Upload speed in Mbps
    "ping": 12.5,            // Ping latency in ms
    "server": "Server Name", // Speedtest server used
    "timestamp": "ISO8601",  // When test completed
    "status": "complete",    // idle|testing|complete|error
    "error": null            // Error message if failed
}
```

### POST /api/speedtest/run

Trigger an immediate speed test.

**Response:**
```json
{
    "status": "started",
    "message": "Speed test started"
}
```

### GET /widget/speedtest

HTML widget for displaying speed test results.

---

## Summary

The Speed Test Widget provides:

✅ **Automatic monitoring** every 60 seconds
✅ **Manual testing** on demand
✅ **Beautiful UI** with animations
✅ **Real-time updates** via polling
✅ **JSON API** for integration
✅ **Low overhead** when idle

Perfect for:
- Monitoring ISP performance
- Debugging network issues
- Tracking speed over time
- Displaying in dashboards

**Quick Start:**
1. Install: `pip3 install speedtest-cli`
2. Open: http://localhost:8767/widget/speedtest
3. Click "Run Test Now" to start!

🚀 Happy speed testing!
