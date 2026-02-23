"""
Example of creating and using a custom theme
"""
from atlas.themes import ThemeManager, Theme, ColorScheme, ThemeLayout

def create_custom_theme():
    """Create a custom theme"""
    
    # Define custom colors
    colors = ColorScheme(
        background=(20, 20, 30),
        foreground=(255, 255, 255),
        primary=(138, 43, 226),  # Blue Violet
        secondary=(60, 60, 80),
        accent=(255, 105, 180),  # Hot Pink
        success=(50, 205, 50),   # Lime Green
        warning=(255, 215, 0),   # Gold
        danger=(220, 20, 60),    # Crimson
        text_primary=(255, 255, 255),
        text_secondary=(200, 200, 220)
    )
    
    # Use default layout
    layout = ThemeLayout()
    
    # Create theme
    theme = Theme(
        name="purple_dream",
        description="A dreamy purple and pink theme",
        colors=colors,
        layout=layout
    )
    
    return theme

def main():
    """Demonstrate custom theme creation"""
    print("Creating custom theme...")
    
    # Create theme manager
    theme_manager = ThemeManager()
    
    # Create custom theme
    custom_theme = create_custom_theme()
    
    # Add to theme manager
    theme_manager.themes[custom_theme.name] = custom_theme
    
    # Save theme to file
    theme_manager.save_theme(custom_theme)
    
    print(f"Custom theme '{custom_theme.name}' created and saved!")
    print(f"   Description: {custom_theme.description}")
    print(f"   Location: {theme_manager.theme_dir}/{custom_theme.name}.json")
    print("\nYou can now use it with:")
    print(f"   atlas --theme {custom_theme.name}")
    
    # Export a template for users to customize
    template_path = "my_theme_template.json"
    theme_manager.export_theme_template(template_path)
    print(f"\nTheme template exported to: {template_path}")
    print("   Edit this file to create your own themes!")

if __name__ == "__main__":
    main()
