#!/usr/bin/env python3
"""
LED Control Demo
Demonstrates RGB LED backplate control features
"""
import time
from atlas.display_driver import DisplayDriver
from atlas.led_control import LEDController, LEDMode, LEDPresetManager

def main():
    print("🌈 LED Control Demo")
    print("=" * 50)
    
    # Connect to display
    print("\n1. Connecting to display...")
    display = DisplayDriver()
    if not display.connect():
        print("Failed to connect to display")
        print("Tip: This demo requires actual hardware")
        return
    
    # Initialize LED controller
    print("✓ Connected!")
    led = LEDController(display.serial_conn)
    
    if not led.supported:
        print(" RGB LEDs not supported on this display")
        display.disconnect()
        return
    
    print("✓ LED support detected!")
    
    try:
        # Demo 1: Static Colors
        print("\n2. Static Colors Demo")
        colors = [
            ("Red", 255, 0, 0),
            ("Green", 0, 255, 0),
            ("Blue", 0, 0, 255),
            ("Purple", 128, 0, 128),
            ("Cyan", 0, 255, 255),
        ]
        
        for name, r, g, b in colors:
            print(f"   Setting {name}...")
            led.set_color(r, g, b, LEDMode.STATIC)
            time.sleep(2)
        
        # Demo 2: Breathing Effect
        print("\n3. Breathing Effect Demo")
        print("   Blue breathing...")
        led.set_breathing(0, 100, 255, speed=50)
        time.sleep(5)
        
        # Demo 3: Rainbow Animation
        print("\n4. Rainbow Animation Demo")
        print("   Rainbow effect...")
        led.set_rainbow(speed=70)
        time.sleep(5)
        
        # Demo 4: Wave Animation
        print("\n5. Wave Animation Demo")
        print("   Wave effect...")
        led.set_wave(speed=60)
        time.sleep(5)
        
        # Demo 5: Presets
        print("\n6. Preset Demo")
        preset_manager = LEDPresetManager(led)
        
        presets = ['gaming', 'work', 'night', 'party', 'focus']
        for preset in presets:
            print(f"   Applying '{preset}' preset...")
            preset_manager.apply_preset(preset)
            time.sleep(3)
        
        # Demo 6: Custom Preset
        print("\n7. Custom Preset Demo")
        print("   Creating custom 'sunset' preset...")
        preset_manager.create_custom_preset(
            name='sunset',
            colors=[(255, 100, 0)],  # Orange
            mode=LEDMode.BREATHING,
            speed=30
        )
        preset_manager.apply_preset('sunset')
        time.sleep(5)
        
        # Demo 7: Brightness Control
        print("\n8. Brightness Control Demo")
        led.set_color(255, 255, 255, LEDMode.STATIC)
        for brightness in [100, 75, 50, 25, 0, 50, 100]:
            print(f"   Brightness: {brightness}%")
            led.set_brightness(brightness)
            time.sleep(1)
        
        # Demo 8: Quick Presets
        print("\n9. Quick Preset Demo")
        quick_presets = ['red', 'green', 'blue', 'purple', 'rainbow', 'off']
        for preset in quick_presets:
            print(f"   {preset.title()}...")
            led.set_preset(preset)
            time.sleep(2)
        
        print("\n✓ Demo complete!")
        
    except KeyboardInterrupt:
        print("\n\n Demo interrupted by user")
    finally:
        # Turn off LEDs
        print("\n10. Turning off LEDs...")
        led.turn_off()
        display.disconnect()
        print("✓ Disconnected")

if __name__ == "__main__":
    main()
