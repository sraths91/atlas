"""
Theme showcase - cycles through all available themes
"""
import time
from atlas.app import Atlas
from atlas.themes import ThemeManager

def main():
    """Showcase all themes"""
    print("Atlas - Theme Showcase")
    print("=" * 50)
    
    # Create app instance with simulated display
    app = Atlas(simulated=True)
    
    # Get all available themes
    themes = app.theme_manager.list_themes()
    
    print(f"\nFound {len(themes)} themes:")
    for theme_name in themes:
        theme = app.theme_manager.get_theme(theme_name)
        print(f"  - {theme_name}: {theme.description}")
    
    print("\nCycling through themes (10 seconds each)...")
    print("Press Ctrl+C to stop\n")
    
    try:
        for theme_name in themes:
            print(f"Now showing: {theme_name}")
            app.theme_manager.set_theme(theme_name)
            app._init_ui_components()  # Reinitialize UI with new theme
            
            # Run for 10 seconds
            start_time = time.time()
            while time.time() - start_time < 10:
                system_info = app.get_system_info()
                app.update_display(system_info)
                time.sleep(1)
            
            print(f"  Preview saved to /tmp/atlas_preview.png\n")
    
    except KeyboardInterrupt:
        print("\n\nTheme showcase stopped.")
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()
