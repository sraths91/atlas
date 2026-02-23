"""
Example of creating custom UI components
"""
from PIL import Image
from atlas.ui_components import (
    GaugeChart, ProgressBar, TextLabel, NetworkGraph, SystemInfoPanel
)
from atlas.themes import ThemeManager

def main():
    """Demonstrate custom UI components"""
    print("Creating custom UI layout...")
    
    # Create a canvas
    width, height = 320, 480
    image = Image.new('RGB', (width, height), color=(15, 15, 20))
    
    # Get theme colors
    theme_manager = ThemeManager()
    theme = theme_manager.get_theme('cyberpunk')
    
    # Create custom components
    
    # Title
    title = TextLabel(x=width // 2, y=20, font_size=24, 
                     color=theme.colors.primary, align='center')
    title.render(image, "Custom Layout")
    
    # CPU Gauge (larger)
    cpu_gauge = GaugeChart(
        x=width // 2, y=120, radius=70,
        bg_color=theme.colors.secondary,
        fg_color=theme.colors.primary,
        text_color=theme.colors.text_primary
    )
    cpu_gauge.render(image, 0.65, "CPU")
    
    # Memory Progress Bar (horizontal)
    mem_bar = ProgressBar(
        x=20, y=240, width=280, height=30,
        bg_color=theme.colors.secondary,
        fg_color=theme.colors.accent,
        border_color=theme.colors.text_secondary,
        show_percentage=True
    )
    mem_bar.render(image, 0.42)
    
    # Network Graph
    net_graph = NetworkGraph(
        x=20, y=290, width=280, height=80,
        upload_color=theme.colors.danger,
        download_color=theme.colors.success,
        bg_color=theme.colors.secondary
    )
    
    # Add some sample data
    import random
    for _ in range(60):
        net_graph.add_data(
            upload=random.uniform(0, 1000000),
            download=random.uniform(0, 5000000)
        )
    
    net_graph.render(image, {'up': 500000, 'down': 2000000})
    
    # System Info Panel
    info_panel = SystemInfoPanel(
        x=20, y=390, width=280, height=70,
        bg_color=theme.colors.secondary,
        text_color=theme.colors.text_primary,
        accent_color=theme.colors.accent
    )
    
    info_data = {
        'title': 'System Status',
        'items': [
            {'label': 'Uptime', 'value': '5d 12h'},
            {'label': 'Temp', 'value': '45.2°C'},
        ]
    }
    info_panel.render(image, info_data)
    
    # Save the result
    output_path = "custom_ui_demo.png"
    image.save(output_path)
    
    print(f"Custom UI layout created!")
    print(f"   Saved to: {output_path}")
    print("\nThis demonstrates how you can create custom layouts")
    print("with different component arrangements and sizes.")

if __name__ == "__main__":
    main()
