"""
macOS Menu Bar Application for Atlas
Provides native menu bar integration with system tray icon
"""
import subprocess
import sys
import threading
import logging
from pathlib import Path
from typing import Optional
import rumps  # Requires: pip install rumps

from .app import Atlas
from .themes import ThemeManager
from .config import ConfigManager

logger = logging.getLogger(__name__)


class AtlasMenuBar(rumps.App):
    """Native macOS menu bar application"""
    
    def __init__(self):
        super().__init__(
            "Atlas",
            icon=self._create_icon(),
            quit_button=None  # Custom quit handler
        )
        
        self.config = ConfigManager()
        self.theme_manager = ThemeManager()
        self.smart_screen: Optional[Atlas] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Build menu
        self._build_menu()
        
    def _create_icon(self) -> Optional[str]:
        """Create or load menu bar icon"""
        # For now, use emoji. Can be replaced with custom icon file
        return "🖥️"
    
    def _build_menu(self):
        """Build the menu bar menu"""
        # Status section
        self.menu.add(rumps.MenuItem("Status: Stopped", callback=None))
        self.menu.add(rumps.separator)
        
        # Control buttons
        self.start_button = rumps.MenuItem("Start Monitor", callback=self.start_monitor)
        self.stop_button = rumps.MenuItem("Stop Monitor", callback=self.stop_monitor)
        self.stop_button.set_callback(None)  # Disabled initially
        
        self.menu.add(self.start_button)
        self.menu.add(self.stop_button)
        self.menu.add(rumps.separator)
        
        # Display mode
        display_menu = rumps.MenuItem("Display Mode")
        display_menu.add(rumps.MenuItem("Hardware", callback=self.set_hardware_mode))
        display_menu.add(rumps.MenuItem("Simulated", callback=self.set_simulated_mode))
        self.menu.add(display_menu)
        self.menu.add(rumps.separator)
        
        # Themes submenu
        themes_menu = rumps.MenuItem("Themes")
        for theme_name in self.theme_manager.list_themes():
            themes_menu.add(
                rumps.MenuItem(
                    theme_name.title(),
                    callback=lambda sender: self.change_theme(sender.title.lower())
                )
            )
        self.menu.add(themes_menu)
        self.menu.add(rumps.separator)
        
        # Brightness control
        brightness_menu = rumps.MenuItem("Brightness")
        for level in [25, 50, 75, 100]:
            brightness_menu.add(
                rumps.MenuItem(
                    f"{level}%",
                    callback=lambda sender, l=level: self.set_brightness(l)
                )
            )
        self.menu.add(brightness_menu)
        self.menu.add(rumps.separator)
        
        # Settings
        self.menu.add(rumps.MenuItem("Open Config Folder", callback=self.open_config))
        self.menu.add(rumps.MenuItem("Preferences...", callback=self.show_preferences))
        self.menu.add(rumps.separator)
        
        # About and Quit
        self.menu.add(rumps.MenuItem("About", callback=self.show_about))
        self.menu.add(rumps.MenuItem("Quit", callback=self.quit_app))
    
    def start_monitor(self, _):
        """Start the system monitor"""
        if self.running:
            rumps.alert("Already Running", "The monitor is already running.")
            return
        
        try:
            # Get display mode from config
            simulated = self.config.get('display.simulated', False)
            
            # Create and start monitor
            self.smart_screen = Atlas(simulated=simulated)
            
            # Start in background thread
            self.monitor_thread = threading.Thread(target=self.smart_screen.run, daemon=True)
            self.monitor_thread.start()
            
            self.running = True
            self._update_status("Running")
            
            # Update menu
            self.start_button.set_callback(None)  # Disable
            self.stop_button.set_callback(self.stop_monitor)  # Enable
            
            logger.info("Monitor started")
            
        except Exception as e:
            logger.exception("Failed to start monitor")
            rumps.alert("Error", f"Failed to start monitor: {str(e)}")
    
    def stop_monitor(self, _):
        """Stop the system monitor"""
        if not self.running:
            return
        
        try:
            if self.smart_screen:
                self.smart_screen.running = False
                self.smart_screen.cleanup()
            
            self.running = False
            self._update_status("Stopped")
            
            # Update menu
            self.start_button.set_callback(self.start_monitor)  # Enable
            self.stop_button.set_callback(None)  # Disable
            
            logger.info("Monitor stopped")
            
        except Exception as e:
            logger.exception("Failed to stop monitor")
            rumps.alert("Error", f"Failed to stop monitor: {str(e)}")
    
    def set_hardware_mode(self, _):
        """Set display mode to hardware"""
        self.config.set('display.simulated', False)
        self.config.save()
        
        if self.running:
            rumps.alert("Restart Required", "Please stop and restart the monitor for changes to take effect.")
    
    def set_simulated_mode(self, _):
        """Set display mode to simulated"""
        self.config.set('display.simulated', True)
        self.config.save()
        
        if self.running:
            rumps.alert("Restart Required", "Please stop and restart the monitor for changes to take effect.")
    
    def change_theme(self, theme_name: str):
        """Change the current theme"""
        try:
            self.config.set('display.theme', theme_name)
            self.config.save()
            
            if self.smart_screen:
                self.smart_screen.theme_manager.set_theme(theme_name)
                logger.info(f"Theme changed to: {theme_name}")
            
            rumps.notification(
                "Theme Changed",
                f"Now using {theme_name.title()} theme",
                ""
            )
            
        except Exception as e:
            logger.exception("Failed to change theme")
            rumps.alert("Error", f"Failed to change theme: {str(e)}")
    
    def set_brightness(self, level: int):
        """Set display brightness"""
        try:
            self.config.set('display.brightness', level)
            self.config.save()
            
            if self.smart_screen and self.smart_screen.display:
                self.smart_screen.display.set_brightness(level)
                logger.info(f"Brightness set to: {level}%")
            
        except Exception as e:
            logger.exception("Failed to set brightness")
            rumps.alert("Error", f"Failed to set brightness: {str(e)}")
    
    def open_config(self, _):
        """Open configuration folder in Finder"""
        config_dir = Path.home() / ".config" / "atlas"
        subprocess.run(['open', str(config_dir)], check=False, timeout=5)
    
    def show_preferences(self, _):
        """Show preferences dialog"""
        # Get current settings
        refresh_rate = self.config.get('display.refresh_rate', 1.0)
        
        # Create dialog
        window = rumps.Window(
            message="Enter refresh rate (seconds):",
            title="Preferences",
            default_text=str(refresh_rate),
            ok="Save",
            cancel="Cancel"
        )
        
        response = window.run()
        
        if response.clicked:
            try:
                new_rate = float(response.text)
                if 0.1 <= new_rate <= 10.0:
                    self.config.set('display.refresh_rate', new_rate)
                    self.config.save()
                    
                    if self.running:
                        rumps.alert("Restart Required", "Please stop and restart the monitor for changes to take effect.")
                else:
                    rumps.alert("Invalid Value", "Refresh rate must be between 0.1 and 10.0 seconds.")
            except ValueError:
                rumps.alert("Invalid Value", "Please enter a valid number.")
    
    def show_about(self, _):
        """Show about dialog"""
        about_text = """Atlas v1.0.0

An enhanced system monitor for Turing Atlas
and compatible USB-C displays.

Optimized for macOS with native integration.

© 2024 Atlas
MIT License"""
        
        rumps.alert("About Atlas", about_text)
    
    def quit_app(self, _):
        """Quit the application"""
        if self.running:
            self.stop_monitor(None)
        
        rumps.quit_application()
    
    def _update_status(self, status: str):
        """Update status in menu"""
        self.menu["Status: Stopped"].title = f"Status: {status}"


def main():
    """Main entry point for menu bar app"""
    try:
        app = AtlasMenuBar()
        app.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted")
        sys.exit(0)
    except Exception as e:
        logger.exception("Application error")
        sys.exit(1)


if __name__ == "__main__":
    main()
