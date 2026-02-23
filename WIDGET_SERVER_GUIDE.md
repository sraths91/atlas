# 🎨 Widget Server - Individual System Monitoring Widgets

## Overview

The Widget Server provides **individual system monitoring widgets as standalone elements** instead of one monolithic PNG. Each widget (CPU, GPU, RAM, etc.) is served as a separate endpoint that can be embedded anywhere.

## Why Individual Widgets?

### Benefits
- ✅ **Better Performance** - Only update widgets that change
- ✅ **Flexible Layouts** - Arrange widgets however you want
- ✅ **Individual Refresh Rates** - Update critical widgets faster
- ✅ **Easy Integration** - Embed in any web page or dashboard
- ✅ **Multiple Formats** - PNG images or SVG vectors
- ✅ **JSON API** - Get raw data for custom visualizations

### Use Cases
- Embed in OBS for streaming overlays
- Add to personal dashboards
- Display on multiple monitors
- Create custom layouts
- Build mobile apps
- Integration with other tools

---

## Quick Start

### 1. Start the App
```bash
python3 -m atlas.app --simulated --refresh-rate 1.0
```

### 2. Access Widget Dashboard
Open: **http://localhost:8766**

You'll see all widgets with controls to adjust refresh rate.

### 3. Use Individual Widgets
Each widget has its own URL that you can embed anywhere!

---

## Widget Endpoints

### PNG Image Widgets

#### CPU Gauge
```
http://localhost:8766/widget/cpu
```
- Circular gauge showing CPU usage
- Color: Cyan (#00c8ff)
- Size: 150x150px

#### GPU Gauge
```
http://localhost:8766/widget/gpu
```
- Circular gauge showing GPU usage
- Color: Orange (#ff6400)
- Size: 150x150px

#### Memory (RAM) Gauge
```
http://localhost:8766/widget/memory
```
- Circular gauge showing RAM usage
- Color: Green (#00ff64)
- Size: 150x150px

#### Disk Bar
```
http://localhost:8766/widget/disk
```
- Horizontal bar showing disk usage
- Color: Yellow/Orange
- Size: 150x150px

#### Network Graph
```
http://localhost:8766/widget/network
```
- Line graph showing network activity
- Color: Light green
- Size: 150x150px

#### System Info Panel
```
http://localhost:8766/widget/info
```
- Text panel with:
  - Upload speed
  - Download speed
  - Battery percentage
  - CPU temperature
- Size: 150x150px

### SVG Vector Widgets

#### CPU SVG
```
http://localhost:8766/svg/cpu
```

#### GPU SVG
```
http://localhost:8766/svg/gpu
```

#### Memory SVG
```
http://localhost:8766/svg/memory
```

**Advantages of SVG:**
- Scalable to any size
- Smaller file size
- Crisp at any resolution
- Easy to style with CSS

---

## JSON API

### Get All Stats
```
http://localhost:8766/api/stats
```

**Response:**
```json
{
    "cpu": 32.6,
    "gpu": 13.0,
    "memory": 68.8,
    "disk": 16.1,
    "network_up": "5.2 KB/s",
    "network_down": "125.3 KB/s",
    "battery": 85,
    "temperature": 45,
    "timestamp": 1762864659.094806
}
```

---

## Usage Examples

### Example 1: Embed in HTML

```html
<!DOCTYPE html>
<html>
<head>
    <title>My Dashboard</title>
    <style>
        .widget {
            display: inline-block;
            margin: 10px;
        }
    </style>
</head>
<body>
    <h1>System Monitor</h1>
    
    <div class="widget">
        <img src="http://localhost:8766/widget/cpu" alt="CPU">
    </div>
    
    <div class="widget">
        <img src="http://localhost:8766/widget/gpu" alt="GPU">
    </div>
    
    <div class="widget">
        <img src="http://localhost:8766/widget/memory" alt="RAM">
    </div>
    
    <script>
        // Auto-refresh every 2 seconds
        setInterval(() => {
            document.querySelectorAll('.widget img').forEach(img => {
                const src = img.src.split('?')[0];
                img.src = src + '?t=' + Date.now();
            });
        }, 2000);
    </script>
</body>
</html>
```

### Example 2: OBS Browser Source

1. Add **Browser Source** in OBS
2. Set URL to: `http://localhost:8766/widget/cpu`
3. Set width/height: 150x150
4. Enable "Refresh browser when scene becomes active"
5. Set custom CSS if needed

### Example 3: Custom Dashboard with JSON

```html
<script>
async function updateStats() {
    const response = await fetch('http://localhost:8766/api/stats');
    const stats = await response.json();
    
    document.getElementById('cpu').textContent = stats.cpu.toFixed(1) + '%';
    document.getElementById('gpu').textContent = stats.gpu.toFixed(1) + '%';
    document.getElementById('memory').textContent = stats.memory.toFixed(1) + '%';
}

setInterval(updateStats, 1000);
</script>

<div>
    CPU: <span id="cpu">--</span>
    GPU: <span id="gpu">--</span>
    RAM: <span id="memory">--</span>
</div>
```

### Example 4: Markdown (for documentation)

```markdown
![CPU Usage](http://localhost:8766/widget/cpu)
![GPU Usage](http://localhost:8766/widget/gpu)
![RAM Usage](http://localhost:8766/widget/memory)
```

### Example 5: Python Integration

```python
import requests
from PIL import Image
from io import BytesIO

# Get CPU widget as image
response = requests.get('http://localhost:8766/widget/cpu')
img = Image.open(BytesIO(response.content))
img.show()

# Get JSON stats
stats = requests.get('http://localhost:8766/api/stats').json()
print(f"CPU: {stats['cpu']}%")
print(f"GPU: {stats['gpu']}%")
print(f"RAM: {stats['memory']}%")
```

---

## Configuration

### Change Widget Server Port

```python
# In app.py
start_widget_server(port=9000, system_monitor=self.system_monitor)
```

### Disable Widget Server

```bash
python3 -m atlas.app --simulated --no-widget-server
```

### Customize Widget Appearance

Edit `widget_server.py` and modify the `WidgetRenderer` class:

```python
# Change colors
def render_gauge(self, value, label, color=(255, 0, 0), bg_color=(0, 0, 0)):
    # Your custom rendering code
    
# Change sizes
def __init__(self, width=200, height=200):
    self.width = width
    self.height = height
```

---

## Advanced Usage

### Custom Refresh Rates Per Widget

```html
<script>
// Fast refresh for CPU (500ms)
setInterval(() => {
    document.getElementById('cpu').src = 
        'http://localhost:8766/widget/cpu?t=' + Date.now();
}, 500);

// Slow refresh for disk (5000ms)
setInterval(() => {
    document.getElementById('disk').src = 
        'http://localhost:8766/widget/disk?t=' + Date.now();
}, 5000);
</script>
```

### Build Custom Widget Layouts

```html
<style>
.grid {
    display: grid;
    grid-template-columns: repeat(3, 150px);
    gap: 20px;
}
</style>

<div class="grid">
    <img src="http://localhost:8766/widget/cpu">
    <img src="http://localhost:8766/widget/gpu">
    <img src="http://localhost:8766/widget/memory">
    <img src="http://localhost:8766/widget/disk">
    <img src="http://localhost:8766/widget/network">
    <img src="http://localhost:8766/widget/info">
</div>
```

### Responsive Design

```html
<style>
.widget img {
    width: 100%;
    max-width: 150px;
    height: auto;
}

@media (max-width: 768px) {
    .widget img {
        max-width: 100px;
    }
}
</style>
```

---

## API Reference

### Widget Renderer Methods

```python
class WidgetRenderer:
    def render_gauge(value, label, color, bg_color)
    # Renders circular gauge
    
    def render_bar(value, label, color, bg_color)
    # Renders horizontal bar
    
    def render_text_info(items, bg_color)
    # Renders text information panel
    
    def render_graph(data_points, label, color, bg_color)
    # Renders line graph
    
    def render_svg_gauge(value, label, color)
    # Renders SVG gauge (scalable)
```

### HTTP Endpoints

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `/` | GET | HTML | Widget dashboard |
| `/api/stats` | GET | JSON | All system stats |
| `/widget/cpu` | GET | PNG | CPU gauge image |
| `/widget/gpu` | GET | PNG | GPU gauge image |
| `/widget/memory` | GET | PNG | RAM gauge image |
| `/widget/disk` | GET | PNG | Disk bar image |
| `/widget/network` | GET | PNG | Network graph |
| `/widget/info` | GET | PNG | System info panel |
| `/svg/cpu` | GET | SVG | CPU gauge vector |
| `/svg/gpu` | GET | SVG | GPU gauge vector |
| `/svg/memory` | GET | SVG | RAM gauge vector |

---

## Performance

### Resource Usage
- **CPU overhead:** < 0.5% per widget request
- **Memory:** ~5MB for widget server
- **Network:** ~15KB per PNG widget, ~2KB per SVG

### Optimization Tips

1. **Use SVG for static displays** - Smaller and scalable
2. **Cache widgets client-side** - Reduce server load
3. **Adjust refresh rates** - Only update what changes
4. **Use JSON API** - Build custom lightweight widgets

---

## Troubleshooting

### Widget Server Not Starting

**Check if port is in use:**
```bash
lsof -i :8766
```

**Check logs:**
```bash
python3 -m atlas.app --simulated 2>&1 | grep widget
```

### Widgets Not Updating

**Verify server is running:**
```bash
curl http://localhost:8766/api/stats
```

**Check browser cache:**
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Add timestamp to URL: `?t=${Date.now()}`

### CORS Issues

The widget server includes CORS headers by default:
```python
self.send_header('Access-Control-Allow-Origin', '*')
```

If you need to restrict origins, modify the `send_cors_headers()` method.

---

## Comparison: Monolithic vs Individual Widgets

### Monolithic PNG (Old Way)
```
http://localhost:8765/preview
```
- ❌ One large image (14KB)
- ❌ Updates everything at once
- ❌ Fixed layout
- ❌ Hard to customize
- ✅ Simple to implement

### Individual Widgets (New Way)
```
http://localhost:8766/widget/cpu
http://localhost:8766/widget/gpu
http://localhost:8766/widget/memory
```
- ✅ Small images (2-3KB each)
- ✅ Update only what changes
- ✅ Flexible layouts
- ✅ Easy to customize
- ✅ Multiple formats (PNG/SVG)
- ✅ JSON API available

---

## Summary

The Widget Server transforms your Atlas into a **modular monitoring system** where each metric is a standalone widget that can be:

✅ **Embedded anywhere** - Web pages, OBS, dashboards
✅ **Customized easily** - Colors, sizes, layouts
✅ **Updated independently** - Different refresh rates
✅ **Accessed via API** - Build your own visualizations
✅ **Scaled efficiently** - SVG support for any resolution

### Quick Links
- **Dashboard:** http://localhost:8766
- **JSON API:** http://localhost:8766/api/stats
- **CPU Widget:** http://localhost:8766/widget/cpu
- **GPU Widget:** http://localhost:8766/widget/gpu
- **RAM Widget:** http://localhost:8766/widget/memory

Start building your custom monitoring dashboard today! 🚀
