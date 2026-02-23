#!/usr/bin/env python3
"""
Launch script for Atlas with automatic port detection
"""
import sys
from atlas.app import Atlas
from atlas.display_driver import DisplayDriver

def main():
    print("🖥️  Atlas Launcher")
    print("=" * 50)
    print()
    
    # Detect available ports
    driver = DisplayDriver()
    ports = driver.list_available_ports()
    
    print("📱 Available serial ports:")
    for port in ports:
        print(f"   - {port}")
    print()
    
    # Find the display port (usbmodem or usbserial)
    display_port = None
    for port in ports:
        if 'usbmodem' in port.lower() or 'usbserial' in port.lower():
            display_port = port
            break
    
    if not display_port:
        print(" No display detected. Available options:")
        print()
        print("1. Run in simulated mode:")
        print("   python3 -m atlas.app --simulated")
        print()
        print("2. Specify port manually:")
        print("   python3 launch.py /dev/cu.YOUR_PORT")
        print()
        return 1
    
    # Allow manual port override
    if len(sys.argv) > 1:
        display_port = sys.argv[1]
    
    print(f"Found display at: {display_port}")
    print()
    
    # Create and configure app with detected port
    app = Atlas(simulated=False)
    app.display.port = display_port
    
    # Set revision if known (XuanFang is Revision B)
    if 'xuanfang' in display_port.lower() or '2017-2-25' in display_port:
        app.display.revision = "B"
    
    print(f"Theme: {app.theme_manager.current_theme.name}")
    print(f"Resolution: {app.display.width}x{app.display.height}")
    print(f"Refresh rate: {app.config_manager.get('display.refresh_rate')}s")
    print()
    print("Starting Atlas...")
    print("   Press Ctrl+C to stop")
    print()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print()
        print("👋 Shutting down gracefully...")
        app.cleanup()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        app.cleanup()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
