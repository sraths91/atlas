# 🚀 Quick Start: New Features

Get started with the three new major features in under 5 minutes!

---

## ⚡ Quick Commands

### Basic Usage (All Features Enabled)
```bash
# Run with all new features
python3 -m atlas.app --simulated --theme cyberpunk
```

### Try Different Layouts
```bash
# Gaming layout (GPU-focused)
python3 -m atlas.app --simulated --layout gaming

# Minimal layout (clean)
python3 -m atlas.app --simulated --layout minimal

# Performance layout (all metrics)
python3 -m atlas.app --simulated --layout performance
```

### View Your Data
```bash
# Show performance statistics
python3 -m atlas.app --show-stats

# Show recent alerts
python3 -m atlas.app --show-alerts

# Export data
python3 -m atlas.app --export-csv metrics.csv
```

---

## 🎯 5-Minute Tutorial

### Step 1: Run the App (30 seconds)
```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
python3 -m atlas.app --simulated --layout gaming --refresh-rate 0.5
```

**What's happening:**
- ✅ System alerts are monitoring your CPU, GPU, memory, temperature, and battery
- ✅ Historical data is being collected every 0.5 seconds
- ✅ Using the "gaming" layout with GPU-focused display

### Step 2: Let It Run (2 minutes)
Leave the app running for 2-3 minutes to collect some data.

### Step 3: Check Your Stats (1 minute)
Open a new terminal and run:
```bash
python3 -m atlas.app --show-stats
```

You'll see:
```
📊 Performance Statistics (Last 24 Hours)
==================================================
  CPU Average:    45.3%
  CPU Peak:       92.5%
  GPU Average:    12.7%
  GPU Peak:       65.2%
  Memory Average: 58.9%
  Memory Peak:    78.3%
  ...
==================================================
```

### Step 4: Try Different Layouts (1 minute)
Stop the app (Ctrl+C) and try:
```bash
# Minimal layout
python3 -m atlas.app --simulated --layout minimal

# Performance layout
python3 -m atlas.app --simulated --layout performance
```

### Step 5: Export Your Data (30 seconds)
```bash
python3 -m atlas.app --export-csv my_metrics.csv
open my_metrics.csv
```

---

## 🔔 Testing Alerts

### Trigger a Test Alert
Run a CPU-intensive task:
```bash
# In another terminal
yes > /dev/null &
```

Within seconds, you should see a macOS notification:
```
CPU Alert
High CPU usage detected: 95.2%
```

Kill the process:
```bash
killall yes
```

View the alert history:
```bash
python3 -m atlas.app --show-alerts
```

---

## 📊 Understanding Your Data

### Database Location
```
~/.atlas/metrics.db
```

### What's Being Tracked
- CPU usage (%)
- GPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Network up/down (KB/s)
- Battery level (%)
- Temperature (°C)
- All triggered alerts

### Data Retention
- Automatic cleanup after 7 days
- ~1MB per day of data
- Efficient SQLite storage

---

## 🎨 Layout Customization

### Available Layouts
```bash
python3 -m atlas.app --list-layouts
```

### Layout Comparison

| Layout | Best For | Widgets |
|--------|----------|---------|
| **default** | General use | CPU, RAM, Network, Battery, Info |
| **minimal** | Clean look | CPU, RAM, Clock, Battery |
| **performance** | Monitoring | CPU, GPU, RAM, Temp, Network, Processes |
| **gaming** | Gaming/GPU work | Large GPU, CPU, RAM, Temp, Network |
| **monitoring** | Detailed stats | All metrics + process list |

---

## 🛠️ Common Scenarios

### Scenario 1: Gaming Session
```bash
# High refresh rate, gaming layout, alerts enabled
python3 -m atlas.app \
  --simulated \
  --layout gaming \
  --theme cyberpunk \
  --refresh-rate 0.2
```

### Scenario 2: Work Monitoring
```bash
# Standard refresh, performance layout
python3 -m atlas.app \
  --simulated \
  --layout performance \
  --theme dark \
  --refresh-rate 1.0
```

### Scenario 3: Minimal Resource Usage
```bash
# Slow refresh, minimal layout, no history
python3 -m atlas.app \
  --simulated \
  --layout minimal \
  --no-history \
  --refresh-rate 2.0
```

### Scenario 4: Data Collection Only
```bash
# No display updates, just collect data
python3 -m atlas.app \
  --simulated \
  --no-alerts \
  --refresh-rate 5.0
```

---

## 📈 Analyzing Your Performance

### Daily Report
```bash
# Export today's data
python3 -m atlas.app --export-csv daily_$(date +%Y%m%d).csv

# View stats
python3 -m atlas.app --show-stats

# Check alerts
python3 -m atlas.app --show-alerts
```

### Weekly Report
```bash
# Export last 7 days
python3 -m atlas.app --export-csv weekly.csv --export-hours 168

# Or JSON format
python3 -m atlas.app --export-json weekly.json --export-hours 168
```

---

## 🎛️ Feature Toggles

### Disable Alerts
```bash
python3 -m atlas.app --simulated --no-alerts
```

### Disable History
```bash
python3 -m atlas.app --simulated --no-history
```

### Disable Both
```bash
python3 -m atlas.app --simulated --no-alerts --no-history
```

---

## 🐛 Troubleshooting

### No Alerts Showing?
1. Check macOS notification settings
2. Verify alerts are enabled (not using `--no-alerts`)
3. Trigger a test alert (see above)

### No Data in Stats?
1. Make sure you ran the app for at least 1 minute
2. Check that `--no-history` is not set
3. Verify database exists: `ls ~/.atlas/metrics.db`

### Layout Not Working?
1. List available layouts: `--list-layouts`
2. Check spelling of layout name
3. Try default layout first

---

## 💡 Pro Tips

### Tip 1: Fast Updates for Gaming
```bash
--refresh-rate 0.1  # Update 10 times per second
```

### Tip 2: Battery Saving
```bash
--refresh-rate 5.0  # Update every 5 seconds
--no-history        # Don't write to disk
```

### Tip 3: Custom Alert Thresholds
Edit `atlas/alerts.py` to customize alert rules.

### Tip 4: View Live Data
```bash
# Terminal 1: Run app
python3 -m atlas.app --simulated

# Terminal 2: Watch stats
watch -n 5 "python3 -m atlas.app --show-stats"
```

### Tip 5: Automated Exports
```bash
# Add to crontab for daily exports
0 0 * * * cd /path/to/project && python3 -m atlas.app --export-csv ~/metrics/$(date +\%Y\%m\%d).csv
```

---

## 🎉 You're Ready!

You now know how to:
- ✅ Use all 5 built-in layouts
- ✅ Monitor system alerts
- ✅ Track historical performance
- ✅ Export and analyze data
- ✅ Customize for different scenarios

**Next Steps:**
- Read `NEW_FEATURES.md` for detailed documentation
- Create custom layouts (see Python API section)
- Set up automated data exports
- Customize alert thresholds

Enjoy your enhanced Atlas! 🚀
