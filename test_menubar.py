#!/usr/bin/env python3
"""
Simple test to verify rumps menu bar icon works
"""

import rumps
from pathlib import Path

# Get icon path
icon_dir = Path(__file__).parent / 'atlas' / 'menubar_icons'
icon_path = icon_dir / 'atlas_connected@2x.png'

class TestApp(rumps.App):
    def __init__(self):
        super().__init__(
            name="ATLAS Test",
            icon=str(icon_path) if icon_path.exists() else None,
            quit_button="Quit"
        )
        
        self.menu = [
            rumps.MenuItem("Test Menu Item"),
            rumps.separator,
            rumps.MenuItem("Status: Testing...")
        ]
        
        print("Menu bar app initialized")
        print(f"📍 Icon path: {icon_path}")
        print(f"📍 Icon exists: {icon_path.exists()}")
        print("\n👀 Check your menu bar (top-right corner)!")
        print("   Look for the ATLAS icon next to WiFi/battery/clock\n")

if __name__ == '__main__':
    print("Starting simple menu bar test...")
    print("=" * 50)
    
    app = TestApp()
    app.run()
