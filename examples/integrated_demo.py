#!/usr/bin/env python3
"""
Integrated Demo - All Enhanced Features
Demonstrates all new features working together
"""
import time
import threading
from atlas.app import Atlas
from atlas.led_control import LEDController, LEDPresetManager
from atlas.widgets import WidgetManager, ClockWidget, BatteryWidget, UptimeWidget
from atlas.themes import ThemeManager

class EnhancedAtlas:
    """Enhanced Atlas with all features"""
    
    def __init__(self, simulated=True):
        print("Initializing Enhanced Atlas...")
        
        # Initialize base app
        self.app = Atlas(simulated=simulated)
        
        # Initialize LED controller (if hardware available)
        self.led = None
        if not simulated and self.app.display.serial_conn:
            self.led = LEDController(self.app.display.serial_conn)
            if self.led.supported:
                self.led_presets = LEDPresetManager(self.led)
                print("✓ LED control enabled")
        
        # Initialize widget manager
        self.widget_manager = WidgetManager()
        self._setup_widgets()
        
        # Theme manager
        self.theme_manager = ThemeManager()
        
        print("✓ Initialization complete!")
    
    def _setup_widgets(self):
        """Setup custom widgets"""
        # Create a custom layout with widgets
        self.widget_manager.add_widget(
            ClockWidget(10, 10, 300, 50, font_size=24, show_date=True),
            'enhanced'
        )
        
        self.widget_manager.add_widget(
            UptimeWidget(10, 70, 300, 30, font_size=14),
            'enhanced'
        )
        
        self.widget_manager.add_widget(
            BatteryWidget(10, 110, 300, 30, font_size=14),
            'enhanced'
        )
    
    def sync_led_with_theme(self, theme_name):
        """Sync LED colors with current theme"""
        if not self.led or not self.led.supported:
            return
        
        theme = self.theme_manager.get_theme(theme_name)
        if theme:
            # Extract primary color
            primary = theme.colors.primary
            if isinstance(primary, tuple) and len(primary) == 3:
                self.led.set_color(*primary)
                print(f"✓ LED synced with {theme_name} theme")
    
    def cycle_themes_with_led(self):
        """Cycle through themes and sync LEDs"""
        print("\nTheme Cycling Demo (with LED sync)")
        print("=" * 50)
        
        themes = self.theme_manager.list_themes()
        
        for theme_name in themes:
            print(f"\n   Applying theme: {theme_name}")
            
            # Change theme
            self.app.theme_manager.set_theme(theme_name)
            self.app._init_ui_components()
            
            # Sync LED
            self.sync_led_with_theme(theme_name)
            
            # Run for a few seconds
            for _ in range(5):
                system_info = self.app.get_system_info()
                self.app.update_display(system_info)
                time.sleep(1)
    
    def widget_showcase(self):
        """Showcase custom widgets"""
        print("\n🧩 Widget Showcase")
        print("=" * 50)
        
        from PIL import Image
        
        print("\n   Rendering custom widget layout...")
        
        for _ in range(10):
            # Create canvas
            canvas = Image.new('RGB', 
                             (self.app.display.width, self.app.display.height),
                             color=(0, 0, 0))
            
            # Render widgets
            self.widget_manager.render_layout(canvas, 'enhanced')
            
            # Display
            self.app.display.display_image(canvas)
            time.sleep(1)
    
    def led_mood_lighting(self):
        """Demo LED mood lighting presets"""
        if not self.led or not self.led.supported:
            print("\n LED control not available")
            return
        
        print("\nLED Mood Lighting Demo")
        print("=" * 50)
        
        presets = ['work', 'focus', 'gaming', 'night', 'party']
        
        for preset in presets:
            print(f"\n   Mood: {preset.upper()}")
            self.led_presets.apply_preset(preset)
            
            # Show system info with this mood
            for _ in range(5):
                system_info = self.app.get_system_info()
                self.app.update_display(system_info)
                time.sleep(1)
    
    def run_full_demo(self):
        """Run complete integrated demo"""
        print("\n" + "=" * 50)
        print("  ENHANCED SMART SCREEN - FULL DEMO")
        print("=" * 50)
        
        try:
            # Connect display
            if not self.app.display.connect():
                print("Failed to connect to display")
                return
            
            # Demo 1: Basic monitoring
            print("\n1️⃣  Basic System Monitoring (10 seconds)")
            print("-" * 50)
            for _ in range(10):
                system_info = self.app.get_system_info()
                self.app.update_display(system_info)
                time.sleep(1)
            
            # Demo 2: Theme cycling with LED sync
            self.cycle_themes_with_led()
            
            # Demo 3: Widget showcase
            self.widget_showcase()
            
            # Demo 4: LED mood lighting
            self.led_mood_lighting()
            
            # Demo 5: Combined features
            print("\n5️⃣  Combined Features Demo")
            print("-" * 50)
            print("   Combining: Custom theme + Widgets + LED effects")
            
            # Set a nice theme
            self.app.theme_manager.set_theme('cyberpunk')
            self.app._init_ui_components()
            
            # Sync LED
            if self.led and self.led.supported:
                self.led.set_preset('rainbow')
            
            # Run with custom widgets overlay
            from PIL import Image, ImageDraw
            
            for i in range(20):
                # Get system info
                system_info = self.app.get_system_info()
                
                # Create base display
                canvas = Image.new('RGB',
                                 (self.app.display.width, self.app.display.height),
                                 color=(0, 0, 0))
                
                # Render main UI
                self.app.update_display(system_info)
                
                time.sleep(1)
            
            print("\nFull demo complete!")
            
        except KeyboardInterrupt:
            print("\n\n Demo interrupted by user")
        finally:
            # Cleanup
            if self.led and self.led.supported:
                self.led.turn_off()
            self.app.cleanup()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Atlas Demo')
    parser.add_argument('--hardware', action='store_true',
                       help='Use actual hardware (default: simulated)')
    parser.add_argument('--demo', choices=['full', 'themes', 'widgets', 'led'],
                       default='full', help='Which demo to run')
    
    args = parser.parse_args()
    
    # Create enhanced app
    app = EnhancedAtlas(simulated=not args.hardware)
    
    # Run selected demo
    if args.demo == 'full':
        app.run_full_demo()
    elif args.demo == 'themes':
        if not app.app.display.connect():
            print("Failed to connect")
            return
        app.cycle_themes_with_led()
        app.app.cleanup()
    elif args.demo == 'widgets':
        if not app.app.display.connect():
            print("Failed to connect")
            return
        app.widget_showcase()
        app.app.cleanup()
    elif args.demo == 'led':
        if not app.app.display.connect():
            print("Failed to connect")
            return
        app.led_mood_lighting()
        app.app.cleanup()

if __name__ == "__main__":
    main()
