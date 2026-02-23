#!/usr/bin/env python3
"""
Widget System Demo
Demonstrates custom widget layouts and rendering
"""
import time
from PIL import Image
from atlas.widgets import (
    WidgetManager, ClockWidget, ProcessListWidget,
    UptimeWidget, BatteryWidget, CustomTextWidget
)
from atlas.display_driver import SimulatedDisplay

def demo_basic_widgets():
    """Demo basic widget usage"""
    print("🧩 Basic Widgets Demo")
    print("=" * 50)
    
    # Create simulated display
    display = SimulatedDisplay()
    display.connect()
    
    # Create widget manager
    manager = WidgetManager()
    
    # Add widgets
    print("\n1. Adding widgets...")
    manager.add_widget(
        ClockWidget(10, 10, 300, 60, font_size=32, show_date=True),
        layout_name='basic'
    )
    
    manager.add_widget(
        UptimeWidget(10, 80, 300, 30, font_size=16),
        layout_name='basic'
    )
    
    manager.add_widget(
        BatteryWidget(10, 120, 300, 30, font_size=16),
        layout_name='basic'
    )
    
    manager.add_widget(
        ProcessListWidget(10, 160, 300, 150, max_processes=5, font_size=12),
        layout_name='basic'
    )
    
    print("✓ Widgets added!")
    
    # Render for 10 seconds
    print("\n2. Rendering layout...")
    print("   Preview saved to: /tmp/atlas_preview.png")
    
    for i in range(10):
        canvas = Image.new('RGB', (320, 480), color=(0, 0, 0))
        manager.render_layout(canvas, 'basic')
        display.display_image(canvas)
        time.sleep(1)
    
    display.disconnect()
    print("\n✓ Demo complete!")

def demo_preset_layouts():
    """Demo preset layouts"""
    print("\nPreset Layouts Demo")
    print("=" * 50)
    
    display = SimulatedDisplay()
    display.connect()
    
    manager = WidgetManager()
    
    # Create preset layouts
    print("\n1. Creating preset layouts...")
    manager.create_preset_layout('dashboard', width=320, height=480)
    manager.create_preset_layout('minimal', width=320, height=480)
    manager.create_preset_layout('monitoring', width=320, height=480)
    
    print("✓ Presets created!")
    print(f"   Available layouts: {', '.join(manager.list_layouts())}")
    
    # Cycle through layouts
    print("\n2. Cycling through layouts...")
    layouts = ['dashboard', 'minimal', 'monitoring']
    
    for layout in layouts:
        print(f"\n   Rendering '{layout}' layout...")
        for i in range(5):
            canvas = Image.new('RGB', (320, 480), color=(0, 0, 0))
            manager.render_layout(canvas, layout)
            display.display_image(canvas)
            time.sleep(1)
    
    display.disconnect()
    print("\n✓ Demo complete!")

def demo_custom_widget():
    """Demo custom widget creation"""
    print("\nCustom Widget Demo")
    print("=" * 50)
    
    from atlas.widgets import Widget
    from PIL import ImageDraw, ImageFont
    
    class CustomProgressWidget(Widget):
        """Custom progress bar widget"""
        
        def __init__(self, x, y, width, height, **kwargs):
            super().__init__(x, y, width, height, **kwargs)
            self.label = kwargs.get('label', 'Progress')
            self.color = kwargs.get('color', (0, 255, 0))
            self.progress = 0
        
        def render(self, canvas, data=None):
            draw = ImageDraw.Draw(canvas)
            
            # Draw label
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            except:
                font = ImageFont.load_default()
            
            draw.text((self.x, self.y), self.label, font=font, fill=(255, 255, 255))
            
            # Draw progress bar
            bar_y = self.y + 20
            bar_height = 20
            
            # Background
            draw.rectangle(
                [self.x, bar_y, self.x + self.width, bar_y + bar_height],
                outline=(100, 100, 100),
                fill=(30, 30, 30)
            )
            
            # Progress
            progress_width = int(self.width * self.progress)
            if progress_width > 0:
                draw.rectangle(
                    [self.x, bar_y, self.x + progress_width, bar_y + bar_height],
                    fill=self.color
                )
            
            # Percentage text
            pct_text = f"{int(self.progress * 100)}%"
            bbox = draw.textbbox((0, 0), pct_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = self.x + (self.width - text_width) // 2
            draw.text((text_x, bar_y + 3), pct_text, font=font, fill=(255, 255, 255))
    
    # Use custom widget
    display = SimulatedDisplay()
    display.connect()
    
    manager = WidgetManager()
    
    print("\n1. Creating custom progress widget...")
    progress_widget = CustomProgressWidget(
        10, 200, 300, 50,
        label='Custom Progress',
        color=(0, 200, 255)
    )
    manager.add_widget(progress_widget, 'custom')
    
    # Add other widgets
    manager.add_widget(
        ClockWidget(10, 10, 300, 60, font_size=28),
        'custom'
    )
    
    manager.add_widget(
        CustomTextWidget(10, 80, 300, 30, 
                        text='Custom Widget Demo',
                        font_size=18,
                        align='center'),
        'custom'
    )
    
    print("✓ Custom widget created!")
    
    # Animate progress
    print("\n2. Animating progress...")
    for i in range(101):
        progress_widget.progress = i / 100
        
        canvas = Image.new('RGB', (320, 480), color=(0, 0, 0))
        manager.render_layout(canvas, 'custom')
        display.display_image(canvas)
        
        time.sleep(0.05)
    
    display.disconnect()
    print("\n✓ Demo complete!")

def demo_dynamic_updates():
    """Demo dynamic widget updates"""
    print("\nDynamic Updates Demo")
    print("=" * 50)
    
    display = SimulatedDisplay()
    display.connect()
    
    manager = WidgetManager()
    
    # Create text widget
    text_widget = CustomTextWidget(
        10, 200, 300, 40,
        text='Starting...',
        font_size=20,
        align='center',
        color=(0, 255, 255)
    )
    
    manager.add_widget(
        ClockWidget(10, 10, 300, 60, font_size=32, show_seconds=True),
        'dynamic'
    )
    
    manager.add_widget(text_widget, 'dynamic')
    
    print("\n1. Updating text dynamically...")
    messages = [
        "Hello World!",
        "Dynamic Updates",
        "Widget System",
        "Atlas",
        "Demo Complete!"
    ]
    
    for msg in messages:
        print(f"   Message: {msg}")
        text_widget.set_text(msg)
        
        for _ in range(3):
            canvas = Image.new('RGB', (320, 480), color=(0, 0, 0))
            manager.render_layout(canvas, 'dynamic')
            display.display_image(canvas)
            time.sleep(1)
    
    display.disconnect()
    print("\n✓ Demo complete!")

def main():
    """Run all demos"""
    print("\n" + "=" * 50)
    print("  MAC SMART SCREEN - WIDGET SYSTEM DEMOS")
    print("=" * 50 + "\n")
    
    try:
        # Run demos
        demo_basic_widgets()
        time.sleep(2)
        
        demo_preset_layouts()
        time.sleep(2)
        
        demo_custom_widget()
        time.sleep(2)
        
        demo_dynamic_updates()
        
        print("\n" + "=" * 50)
        print("  ALL DEMOS COMPLETE!")
        print("=" * 50)
        print("\nCheck /tmp/atlas_preview.png for output")
        
    except KeyboardInterrupt:
        print("\n\n Demos interrupted by user")

if __name__ == "__main__":
    main()
