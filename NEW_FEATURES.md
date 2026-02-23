# 🚀 New Features Guide

This document describes the three major feature upgrades added to Atlas:

1. **Real-Time System Alerts** 🔔
2. **Historical Data & Performance Graphs** 📊
3. **Multi-Display & Custom Layouts** 🖥️

---

## 🔔 Feature 1: Real-Time System Alerts

### Overview
Get instant macOS notifications when system metrics exceed configurable thresholds.

### Features
- **CPU/GPU/RAM monitoring** - Alert when usage exceeds thresholds
- **Temperature warnings** - Prevent thermal throttling
- **Battery alerts** - Low battery notifications
- **Customizable thresholds** - Set your own limits
- **Cooldown periods** - Prevent alert spam
- **Alert history** - Track all triggered alerts

### Default Alert Rules
```
CPU > 90%        - High CPU usage warning
GPU > 90%        - High GPU usage warning
Memory > 90%     - High memory usage warning
Temperature > 80°C - Thermal warning
Battery < 20%    - Low battery warning
Battery < 10%    - Critical battery warning
```

### Usage

#### Enable/Disable Alerts
```bash
# Alerts are enabled by default
python3 -m atlas.app --simulated

# Disable alerts
python3 -m atlas.app --simulated --no-alerts
```

#### View Recent Alerts
```bash
python3 -m atlas.app --show-alerts
```

Output:
```
🔔 Recent Alerts (Last 24 Hours)
==================================================
  [2025-11-07 22:15:30] High CPU usage detected: 92.5%
  [2025-11-07 21:45:12] High temperature: 85.0°C
  [2025-11-07 20:30:45] Low battery: 18.0% remaining
==================================================
```

#### Customize Alert Rules (Python API)
```python
from atlas.alerts import alert_manager, AlertRule, AlertType

# Add custom alert
rule = AlertRule(
    alert_type=AlertType.CPU,
    threshold=75,  # Alert at 75% instead of 90%
    condition='>',
    duration=60,
    cooldown=300,
    message="CPU usage is high: {value}%"
)
alert_manager.add_rule(rule)
```

---

## 📊 Feature 2: Historical Data & Performance Graphs

### Overview
Track and analyze system performance over time with automatic data collection and visualization.

### Features
- **SQLite database** - Efficient local storage
- **24/7 data collection** - Automatic metric logging
- **Performance statistics** - Averages, peaks, trends
- **Data export** - CSV and JSON formats
- **Alert history** - All triggered alerts stored
- **Automatic cleanup** - Old data removed after 7 days

### Database Location
```
~/.atlas/metrics.db
```

### Usage

#### View Performance Statistics
```bash
python3 -m atlas.app --show-stats
```

Output:
```
📊 Performance Statistics (Last 24 Hours)
==================================================
  CPU Average:    45.3%
  CPU Peak:       92.5%
  GPU Average:    12.7%
  GPU Peak:       65.2%
  Memory Average: 58.9%
  Memory Peak:    78.3%
  Temp Average:   52.4°C
  Temp Peak:      85.0°C
  Data Points:    86400
==================================================
```

#### Export Data to CSV
```bash
# Export last 24 hours
python3 -m atlas.app --export-csv metrics.csv

# Export last 7 days
python3 -m atlas.app --export-csv metrics.csv --export-hours 168
```

#### Export Data to JSON
```bash
python3 -m atlas.app --export-json metrics.json --export-hours 48
```

#### Disable Historical Tracking
```bash
python3 -m atlas.app --simulated --no-history
```

### Python API

```python
from atlas.database import get_database

db = get_database()

# Get recent metrics
metrics = db.get_metrics(hours=24, limit=100)

# Get aggregated data (5-minute intervals)
aggregated = db.get_aggregated_metrics(hours=24, interval_minutes=5)

# Get statistics
stats = db.get_stats(hours=24)

# Export data
db.export_to_csv('output.csv', hours=48)
db.export_to_json('output.json', hours=24)

# Cleanup old data
db.cleanup_old_data(days=7)
```

### Visualization

```python
from atlas.visualization import create_performance_report

# Create comprehensive performance report
aggregated_data = db.get_aggregated_metrics(hours=24)
stats = db.get_stats(hours=24)

create_performance_report(
    aggregated_data,
    stats,
    output_path='performance_report.png'
)
```

---

## 🖥️ Feature 3: Multi-Display & Custom Layouts

### Overview
Customize your display with pre-built layouts or create your own widget arrangements.

### Built-in Layouts

#### 1. **Default** - Balanced view
- CPU and Memory gauges
- Network graph
- Battery bar
- System info panel

#### 2. **Minimal** - Clean and simple
- CPU and Memory gauges
- Clock widget
- Battery bar

#### 3. **Performance** - Metrics focused
- CPU, GPU, Memory gauges
- Temperature display
- Network graph
- Top processes list

#### 4. **Gaming** - GPU-centric
- Large GPU gauge
- CPU and Memory gauges
- Temperature monitor
- Network stats

#### 5. **Monitoring** - Detailed stats
- System info panel
- All metric gauges
- Disk usage
- Process list
- Network graph

### Usage

#### List Available Layouts
```bash
python3 -m atlas.app --list-layouts
```

Output:
```
Available layouts:
  - default
  - minimal
  - performance
  - gaming
  - monitoring
```

#### Use a Specific Layout
```bash
# Use gaming layout
python3 -m atlas.app --simulated --layout gaming

# Use minimal layout
python3 -m atlas.app --simulated --layout minimal
```

#### Create Custom Layout (Python API)

```python
from atlas.layout_manager import get_layout_manager, Widget, WidgetType

layout_mgr = get_layout_manager()

# Create new layout
custom = layout_mgr.create_custom_layout("my_layout", width=320, height=480)

# Add widgets
custom.add_widget(Widget(
    widget_type=WidgetType.CPU_GAUGE,
    x=50, y=50,
    width=100, height=100
))

custom.add_widget(Widget(
    widget_type=WidgetType.GPU_GAUGE,
    x=170, y=50,
    width=100, height=100
))

custom.add_widget(Widget(
    widget_type=WidgetType.CLOCK,
    x=60, y=200,
    width=200, height=60,
    config={'format': '24h'}
))

# Save layout
layout_mgr.save_layout(custom)
```

#### Duplicate and Modify Layout

```python
# Duplicate existing layout
new_layout = layout_mgr.duplicate_layout("gaming", "my_gaming")

# Modify widgets
new_layout.widgets[0].x = 100  # Move first widget
new_layout.widgets[0].width = 150  # Resize

# Save
layout_mgr.save_layout(new_layout)
```

### Available Widget Types

- `CPU_GAUGE` - CPU usage circular gauge
- `GPU_GAUGE` - GPU usage circular gauge
- `MEMORY_GAUGE` - Memory usage circular gauge
- `BATTERY_BAR` - Battery level progress bar
- `NETWORK_GRAPH` - Network usage graph
- `TEMPERATURE` - Temperature display
- `CLOCK` - Current time display
- `SYSTEM_INFO` - System information panel
- `PROCESS_LIST` - Top processes by CPU/RAM
- `DISK_USAGE` - Disk space usage

### Layout Files

Custom layouts are saved to:
```
~/.atlas/layouts/[layout_name].json
```

---

## 🎯 Combined Usage Examples

### Example 1: Gaming Setup with Alerts
```bash
python3 -m atlas.app \
  --simulated \
  --layout gaming \
  --theme cyberpunk \
  --refresh-rate 0.2
```

### Example 2: Monitoring with History (No Alerts)
```bash
python3 -m atlas.app \
  --simulated \
  --layout monitoring \
  --no-alerts \
  --refresh-rate 1.0
```

### Example 3: Minimal Display (No Tracking)
```bash
python3 -m atlas.app \
  --simulated \
  --layout minimal \
  --no-alerts \
  --no-history \
  --refresh-rate 2.0
```

### Example 4: Export Performance Data
```bash
# Run app for a while to collect data, then:
python3 -m atlas.app --export-csv daily_metrics.csv --export-hours 24
python3 -m atlas.app --show-stats
python3 -m atlas.app --show-alerts
```

---

## 📁 File Structure

```
~/.atlas/
├── metrics.db              # Historical data database
└── layouts/
    ├── my_layout.json      # Custom layout 1
    └── my_gaming.json      # Custom layout 2
```

---

## 🔧 Configuration

### Alert Configuration
Alerts are configured programmatically. See `atlas/alerts.py` for default rules.

### Database Configuration
Database automatically manages:
- Data retention (7 days default)
- Index optimization
- Connection pooling

### Layout Configuration
Layouts are JSON files with widget definitions:

```json
{
  "name": "my_layout",
  "width": 320,
  "height": 480,
  "theme": "cyberpunk",
  "background_color": [0, 0, 0],
  "widgets": [
    {
      "type": "cpu_gauge",
      "x": 50,
      "y": 50,
      "width": 100,
      "height": 100,
      "config": {},
      "visible": true
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Alerts Not Showing
- Check macOS notification permissions
- Verify alerts are enabled (not using `--no-alerts`)
- Check alert cooldown periods

### Database Issues
- Check disk space in `~/.atlas/`
- Verify write permissions
- Run cleanup: `db.cleanup_old_data(days=1)`

### Layout Not Loading
- Verify layout name with `--list-layouts`
- Check JSON syntax in custom layout files
- Use default layout as template

---

## 📊 Performance Impact

### Resource Usage
- **Alerts**: Negligible (<0.1% CPU)
- **Database**: ~1MB per day of data
- **Layouts**: No performance impact

### Recommendations
- Use `--refresh-rate 1.0` or higher for normal use
- Use `--no-history` if disk space is limited
- Use `--no-alerts` for unattended operation

---

## 🚀 What's Next?

Future enhancements:
- Web dashboard for viewing historical data
- Custom alert actions (run scripts, etc.)
- Multi-monitor support
- Cloud sync for layouts
- Mobile app companion

---

## 📝 Summary

You now have three powerful new features:

1. ✅ **Alerts** - Never miss critical system events
2. ✅ **History** - Track performance over time
3. ✅ **Layouts** - Customize your display

All features work together seamlessly and can be enabled/disabled independently!

Enjoy your enhanced Atlas! 🎉
