# Quick Start Guide - Enhanced Features

## 🚀 5-Minute Setup

### 1. Install Dependencies
```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
pip install -r requirements.txt
```

### 2. Choose Your Interface

#### Option A: Menu Bar App (Recommended)
```bash
python -m atlas.menubar_app
```
- Click the 🖥️ icon in your menu bar
- Select "Start Monitor"
- Choose your theme
- Done! ✅

#### Option B: Command Line
```bash
python -m atlas.app --simulated --theme cyberpunk
```

#### Option C: Web Theme Editor
```bash
python -m atlas.web_editor
```
Then open: http://127.0.0.1:5000

## 🎨 Try the New Features

### 1. Menu Bar App (30 seconds)
```bash
# Start the app
python -m atlas.menubar_app

# Look for 🖥️ in your menu bar
# Click it and explore:
# - Start/Stop Monitor
# - Change Themes
# - Adjust Brightness
# - Preferences
```

### 2. Web Theme Editor (2 minutes)
```bash
# Start editor
python -m atlas.web_editor

# In browser (http://127.0.0.1:5000):
# 1. Click a theme to load it
# 2. Adjust colors with color picker
# 3. See live preview
# 4. Click "Save Theme"
```

### 3. Custom Widgets (3 minutes)
```bash
# Run widget demo
python examples/widget_demo.py

# Check output
open /tmp/atlas_preview.png

# See different layouts:
# - Dashboard (clock, battery, processes)
# - Minimal (just clock)
# - Monitoring (detailed stats)
```

### 4. LED Control (2 minutes - requires hardware)
```bash
# Run LED demo
python examples/led_demo.py

# Watch your display:
# - Static colors
# - Breathing effect
# - Rainbow animation
# - Wave effect
# - Presets (gaming, work, night, party)
```

### 5. Integrated Demo (5 minutes)
```bash
# Run full demo
python examples/integrated_demo.py

# Or specific features:
python examples/integrated_demo.py --demo themes
python examples/integrated_demo.py --demo widgets
python examples/integrated_demo.py --demo led
```

## 📋 Common Tasks

### Change Theme
```bash
# Via command line
python -m atlas.app --theme matrix

# Via menu bar
# Click 🖥️ → Themes → Select theme

# Via web editor
python -m atlas.web_editor
# Then edit in browser
```

### Adjust Brightness
```bash
# Via menu bar
# Click 🖥️ → Brightness → Select level

# Via Python
from atlas.display_driver import DisplayDriver
display = DisplayDriver()
display.connect()
display.set_brightness(75)  # 75%
```

### Control LEDs
```python
from atlas.display_driver import DisplayDriver
from atlas.led_control import LEDController

display = DisplayDriver()
display.connect()
led = LEDController(display.serial_conn)

# Quick presets
led.set_preset('rainbow')
led.set_preset('gaming')
led.set_preset('work')

# Custom color
led.set_color(255, 0, 255)  # Magenta
```

### Create Custom Widget
```python
from atlas.widgets import Widget, WidgetManager
from PIL import ImageDraw

class MyWidget(Widget):
    def render(self, canvas, data=None):
        draw = ImageDraw.Draw(canvas)
        draw.text((self.x, self.y), "Hello!", fill=(255, 255, 255))

# Use it
manager = WidgetManager()
manager.add_widget(MyWidget(10, 10, 300, 50))
```

## 🎯 Quick Commands Reference

### Installation
```bash
pip install -r requirements.txt
pip install -e .
```

### Run Applications
```bash
# Main app
atlas --simulated

# Menu bar app
atlas-menubar

# Theme editor
atlas-editor
```

### Demos
```bash
# All demos
python examples/integrated_demo.py

# LED only
python examples/led_demo.py

# Widgets only
python examples/widget_demo.py
```

### Configuration
```bash
# Open config folder
open ~/.config/atlas/

# Edit config
nano ~/.config/atlas/config.json
```

## 🐛 Troubleshooting

### Menu Bar App Won't Start
```bash
# Install rumps
pip install rumps

# Try again
python -m atlas.menubar_app
```

### Web Editor Won't Start
```bash
# Install Flask
pip install Flask

# Try again
python -m atlas.web_editor
```

### Display Not Detected
```bash
# List ports
python detect_display.py

# Use specific port
python -m atlas.app --port /dev/cu.usbmodem...
```

### LEDs Not Working
- Check if your display supports RGB LEDs
- Try running original software once (Windows)
- Power cycle the display

## 📚 Learn More

- **Full Documentation**: See [ENHANCEMENTS.md](ENHANCEMENTS.md)
- **Improvements Summary**: See [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)
- **Main README**: See [README.md](README.md)
- **Original Project**: [turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python)

## 💡 Tips

1. **Start with Simulated Mode**
   - No hardware needed
   - Test all features
   - Preview themes

2. **Use Menu Bar App**
   - Most convenient
   - Always accessible
   - Native experience

3. **Try Web Editor**
   - Easy theme creation
   - Visual feedback
   - No coding needed

4. **Explore Widgets**
   - Customize your display
   - Create unique layouts
   - Share with community

5. **Experiment with LEDs**
   - Sync with themes
   - Create moods
   - Use presets

## 🎉 Next Steps

1. ✅ Install dependencies
2. ✅ Try menu bar app
3. ✅ Create custom theme
4. ✅ Test widgets
5. ✅ Control LEDs
6. 📤 Share your themes!

---

**Questions?** Check the full documentation or open an issue on GitHub.

**Enjoying the project?** ⭐ Star it on GitHub!
