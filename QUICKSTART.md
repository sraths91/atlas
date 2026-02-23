# Quick Start Guide

Get up and running with Atlas in 5 minutes!

## 1. Installation

```bash
# Clone or download the project
cd /path/to/atlas

# Run the installer
./install.sh
```

Or install manually:

```bash
pip install -r requirements.txt
pip install -e .
```

## 2. Test Your Installation

```bash
python test_installation.py
```

This will verify that everything is working correctly.

## 3. Run in Simulated Mode

Perfect for testing without hardware:

```bash
atlas --simulated
```

The display preview will be saved to `/tmp/atlas_preview.png`

## 4. Try Different Themes

List available themes:

```bash
atlas --list-themes
```

Run with a specific theme:

```bash
atlas --simulated --theme cyberpunk
```

## 5. Connect Your Display

Once you have a Turing Atlas:

```bash
# Auto-detect and connect
atlas

# Or specify the port
atlas --port /dev/cu.usbserial-XXXX
```

## Configuration

Edit `~/.config/atlas/config.json` to customize:

- Display refresh rate
- Default theme
- Monitoring options
- And more!

## Examples

Check out the `examples/` directory:

- `basic_usage.py` - Simple example
- `theme_showcase.py` - Cycle through all themes
- `custom_theme.py` - Create your own theme
- `custom_ui.py` - Build custom layouts

## Troubleshooting

### Display not detected?

```python
from atlas.display_driver import DisplayDriver
driver = DisplayDriver()
print(driver.list_available_ports())
```

### Want better temperature monitoring?

```bash
brew install osx-cpu-temp
```

## Next Steps

- Read the full [README.md](README.md)
- Create custom themes
- Explore the Python API
- Join the community!

## Need Help?

- Check [GitHub Issues](https://github.com/yourusername/atlas/issues)
- Read the documentation
- Ask in [Discussions](https://github.com/yourusername/atlas/discussions)

---

Happy monitoring! 🖥️✨
