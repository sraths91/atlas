"""
Main application module for Atlas
"""
import os
import sys
import signal
import logging
import platform
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from PIL import Image

from .config import ConfigManager
from .system_monitor import SystemMonitor
from .display_driver import DisplayDriver, SimulatedDisplay
from .themes import ThemeManager
from .ui_components import (
    ProgressBar, GaugeChart, TextLabel, 
    NetworkGraph, SystemInfoPanel
)
from .alerts import alert_manager, AlertType, AlertRule
from .alert_rules_manager import get_alert_rules_manager
from .database import get_database
from .layout_manager import get_layout_manager
from .process_monitor import get_process_monitor
from .web_viewer import start_web_viewer
from .widget_server import start_widget_server
from .live_widgets import start_live_widget_server

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class SystemInfo:
    """System information data class"""
    cpu_usage: float
    memory_usage: float
    disk_usage: Dict[str, float]
    network_usage: Dict[str, float]
    gpu_usage: Optional[float] = None
    temperatures: Optional[Dict[str, float]] = None

class Atlas:
    """Main application class for Atlas"""
    
    def __init__(self, config_path: Optional[str] = None, simulated: bool = False, enable_alerts: bool = True, enable_history: bool = True, enable_process_monitor: bool = True, enable_web_viewer: bool = True, enable_widget_server: bool = True):
        """
        Initialize the Atlas application
        
        Args:
            config_path: Path to configuration file
            simulated: Use simulated display for testing
            enable_alerts: Enable system alerts
            enable_history: Enable historical data tracking
            enable_process_monitor: Enable process monitoring
            enable_web_viewer: Enable web-based live viewer
            enable_widget_server: Enable individual widget server
        """
        self.running = False
        self.enable_alerts = enable_alerts
        self.enable_history = enable_history
        self.enable_process_monitor = enable_process_monitor
        self.enable_web_viewer = enable_web_viewer
        self.enable_widget_server = enable_widget_server
        self.web_viewer_thread = None
        self.widget_server_thread = None
        self.setup_signal_handlers()
        self.validate_platform()
        
        # Initialize new features
        if self.enable_history:
            self.db = get_database()
            logger.info("Historical data tracking enabled")
        
        if self.enable_alerts:
            self.alert_manager = alert_manager
            self.custom_rules_manager = get_alert_rules_manager()
            logger.info("System alerts enabled (with custom rules support)")
        
        if self.enable_process_monitor:
            self.process_monitor = get_process_monitor()
            logger.info("Process monitoring enabled")
        
        self.layout_manager = get_layout_manager()
        logger.info("Layout manager initialized")
        
        # Initialize components
        self.config_manager = ConfigManager(config_path)
        self.system_monitor = SystemMonitor()
        self.theme_manager = ThemeManager()
        
        # Set theme from config
        theme_name = self.config_manager.get('display.theme', 'dark')
        self.theme_manager.set_theme(theme_name)
        
        # Initialize display
        if simulated:
            self.display = SimulatedDisplay()
        else:
            display_model = self.config_manager.get('display.model', 'turing_3.5')
            self.display = DisplayDriver(model=display_model)
        
        # Initialize UI components
        self._init_ui_components()
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def validate_platform(self):
        """Verify we're running on a supported platform"""
        if platform.system() != 'Darwin':
            logger.error("This application is designed to run on macOS only.")
            sys.exit(1)
    
    def _init_ui_components(self):
        """Initialize UI components based on current theme"""
        theme = self.theme_manager.current_theme
        
        # CPU Gauge
        cpu_layout = theme.layout.cpu_gauge
        self.cpu_gauge = GaugeChart(
            x=cpu_layout['x'],
            y=cpu_layout['y'],
            radius=cpu_layout['radius'],
            bg_color=theme.colors.secondary,
            fg_color=theme.colors.primary,
            text_color=theme.colors.text_primary
        )
        
        # Memory Gauge
        mem_layout = theme.layout.memory_gauge
        self.memory_gauge = GaugeChart(
            x=mem_layout['x'],
            y=mem_layout['y'],
            radius=mem_layout['radius'],
            bg_color=theme.colors.secondary,
            fg_color=theme.colors.accent,
            text_color=theme.colors.text_primary
        )
        
        # Network Graph
        net_layout = theme.layout.network_graph
        self.network_graph = NetworkGraph(
            x=net_layout['x'],
            y=net_layout['y'],
            width=net_layout['width'],
            height=net_layout['height'],
            upload_color=theme.colors.danger,
            download_color=theme.colors.success,
            bg_color=theme.colors.secondary
        )
        
        # Disk Progress Bar
        disk_layout = theme.layout.disk_bar
        self.disk_bar = ProgressBar(
            x=disk_layout['x'],
            y=disk_layout['y'],
            width=disk_layout['width'],
            height=disk_layout['height'],
            bg_color=theme.colors.secondary,
            fg_color=theme.colors.warning,
            border_color=theme.colors.text_secondary
        )
        
        # System Info Panel
        info_layout = theme.layout.info_panel
        self.info_panel = SystemInfoPanel(
            x=info_layout['x'],
            y=info_layout['y'],
            width=info_layout['width'],
            height=info_layout['height'],
            bg_color=theme.colors.secondary,
            text_color=theme.colors.text_primary,
            accent_color=theme.colors.primary
        )
        
        # Title Label
        self.title_label = TextLabel(
            x=self.display.width // 2,
            y=10,
            font_size=theme.font_sizes['title'],
            color=theme.colors.text_primary,
            align='center'
        )
    
    def get_system_info(self) -> SystemInfo:
        """Gather system information using native macOS tools"""
        stats = self.system_monitor.get_all_stats()
        
        return SystemInfo(
            cpu_usage=stats['cpu'],
            memory_usage=stats['memory'],
            disk_usage=stats['disks'],
            network_usage=stats['network'],
            gpu_usage=stats.get('gpu'),
            temperatures=stats.get('temperatures', {})
        )
    
    def update_display(self, system_info: SystemInfo):
        """Update the display with current system information"""
        theme = self.theme_manager.current_theme
        
        # Clear display with background color
        canvas = Image.new('RGB', (self.display.width, self.display.height), 
                          color=theme.colors.background)
        
        # Render title
        self.title_label.render(canvas, "Atlas")
        
        # Render CPU gauge
        self.cpu_gauge.render(canvas, system_info.cpu_usage, "CPU")
        
        # Render Memory gauge
        self.memory_gauge.render(canvas, system_info.memory_usage, "RAM")
        
        # Render Network graph
        self.network_graph.render(canvas, system_info.network_usage)
        
        # Render Disk bar (use root partition)
        disk_usage = system_info.disk_usage.get('/', 0.0)
        self.disk_bar.render(canvas, disk_usage)
        
        # Render System Info Panel
        info_items = []
        
        # Add temperature info if available
        if system_info.temperatures:
            cpu_temp = system_info.temperatures.get('cpu')
            if cpu_temp:
                info_items.append({'label': 'CPU Temp', 'value': f'{cpu_temp:.1f}°C'})
        
        # Add GPU info if available
        if system_info.gpu_usage is not None:
            info_items.append({'label': 'GPU', 'value': f'{int(system_info.gpu_usage * 100)}%'})
        
        # Add network speeds
        up_speed = system_info.network_usage.get('up', 0)
        down_speed = system_info.network_usage.get('down', 0)
        info_items.append({'label': 'Upload', 'value': self._format_bytes(up_speed) + '/s'})
        info_items.append({'label': 'Download', 'value': self._format_bytes(down_speed) + '/s'})
        
        info_data = {
            'title': 'System Info',
            'items': info_items
        }
        self.info_panel.render(canvas, info_data)
        
        # Update display
        self.display.display_image(canvas)
    
    @staticmethod
    def _format_bytes(bytes_value: float) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
    
    def run(self):
        """Main application loop"""
        self.running = True
        logger.info("Starting Atlas...")
        
        # Start web viewer if enabled
        if self.enable_web_viewer:
            refresh_rate = self.config_manager.get('display.refresh_rate', 1.0)
            refresh_ms = int(refresh_rate * 1000)
            self.web_viewer_thread = start_web_viewer(refresh_ms=refresh_ms, open_browser=False)
            logger.info("Web viewer started at http://localhost:8765")
        
        # Start widget server if enabled
        if self.enable_widget_server:
            self.widget_server_thread = start_widget_server(port=8766, system_monitor=self.system_monitor)
            logger.info("Widget server started at http://localhost:8766")
        
        # Start live widget server (always enabled for now)
        self.live_widget_thread = start_live_widget_server(port=8767, system_monitor=self.system_monitor)
        logger.info("Live widget server started at http://localhost:8767")
        
        # Connect to display
        if not self.display.connect():
            logger.error("Failed to connect to display")
            return
        
        try:
            refresh_rate = self.config_manager.get('display.refresh_rate', 1.0)
            
            while self.running:
                # Get system information
                system_info = self.get_system_info()
                
                # Update display
                self.update_display(system_info)
                
                # Store metrics in database if enabled
                if self.enable_history:
                    stats = self.system_monitor.get_all_stats()
                    metrics = {
                        'timestamp': time.time(),
                        'cpu': stats['cpu'],
                        'gpu': stats.get('gpu', 0),
                        'memory': stats['memory'],
                        'memory_used': stats.get('memory_used', 0),
                        'memory_total': stats.get('memory_total', 0),
                        'disk': stats.get('disks', {}).get('/', 0),
                        'network_up': stats['network'].get('upload', 0),
                        'network_down': stats['network'].get('download', 0),
                        'battery': stats.get('battery', {}).get('percent', 0),
                        'battery_plugged': 1 if stats.get('battery', {}).get('plugged', False) else 0,
                        'temperature': stats.get('temperatures', {}).get('cpu', 0)
                    }
                    self.db.insert_metrics(metrics)
                
                # Check alerts if enabled
                if self.enable_alerts:
                    alert_metrics = {
                        'cpu': stats['cpu'],
                        'gpu': stats.get('gpu', 0) * 100,  # Convert to percentage
                        'memory': stats['memory'],
                        'temperature': stats.get('temperatures', {}).get('cpu', 0),
                        'battery': stats.get('battery', {}).get('percent', 100),
                        'disk': stats.get('disks', {}).get('/', 0),
                        'network_up': stats.get('network', {}).get('upload', 0) / 1024.0,
                        'network_down': stats.get('network', {}).get('download', 0) / 1024.0,
                    }
                    triggered_alerts = self.alert_manager.check_metrics(alert_metrics)

                    # Evaluate custom alert rules (new system)
                    try:
                        custom_events = self.custom_rules_manager.evaluate_metrics(alert_metrics)
                        # Custom rules handle their own notifications and storage
                    except Exception as e:
                        logger.debug(f"Custom rules evaluation skipped: {e}")

                    # Check for process issues
                    if self.enable_process_monitor:
                        process_issues = self.process_monitor.scan_processes()
                        process_alerts = self.alert_manager.check_process_issues(process_issues)
                        triggered_alerts.extend(process_alerts)

                    # Store alerts in database
                    if self.enable_history and triggered_alerts:
                        for alert in triggered_alerts:
                            self.db.insert_alert(alert)
                
                # Sleep for refresh rate
                time.sleep(refresh_rate)
                
        except Exception as e:
            logger.exception("Error in main loop")
        finally:
            self.cleanup()
    
    def handle_shutdown(self, signum, frame):
        """Handle application shutdown"""
        logger.info("Shutting down...")
        self.running = False
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        self.display.disconnect()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Atlas - System Monitor')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--simulated', action='store_true', help='Use simulated display')
    parser.add_argument('--theme', type=str, help='Theme name to use')
    parser.add_argument('--list-themes', action='store_true', help='List available themes')
    parser.add_argument('--refresh-rate', type=float, default=1.0, help='Update interval in seconds (default: 1.0, faster: 0.1-0.5)')
    
    # New feature arguments
    parser.add_argument('--no-alerts', action='store_true', help='Disable system alerts')
    parser.add_argument('--no-history', action='store_true', help='Disable historical data tracking')
    parser.add_argument('--no-process-monitor', action='store_true', help='Disable process monitoring')
    parser.add_argument('--no-web-viewer', action='store_true', help='Disable web-based live viewer')
    parser.add_argument('--no-widget-server', action='store_true', help='Disable individual widget server')
    parser.add_argument('--layout', type=str, help='Layout name to use (default, minimal, performance, gaming, monitoring)')
    parser.add_argument('--list-layouts', action='store_true', help='List available layouts')
    
    # Process monitoring arguments
    parser.add_argument('--show-processes', action='store_true', help='Show problematic processes')
    parser.add_argument('--top-cpu', type=int, default=5, help='Show top N CPU processes (default: 5)')
    parser.add_argument('--top-memory', type=int, default=5, help='Show top N memory processes (default: 5)')
    
    # Data export arguments
    parser.add_argument('--export-csv', type=str, help='Export metrics to CSV file')
    parser.add_argument('--export-json', type=str, help='Export metrics to JSON file')
    parser.add_argument('--export-hours', type=int, default=24, help='Hours of data to export (default: 24)')
    parser.add_argument('--show-stats', action='store_true', help='Show performance statistics')
    parser.add_argument('--show-alerts', action='store_true', help='Show recent alerts')
    
    args = parser.parse_args()
    
    if args.list_themes:
        theme_manager = ThemeManager()
        print("Available themes:")
        for theme_name in theme_manager.list_themes():
            theme = theme_manager.get_theme(theme_name)
            print(f"  - {theme_name}: {theme.description}")
        return
    
    # List layouts if requested
    if args.list_layouts:
        layout_mgr = get_layout_manager()
        print("Available layouts:")
        for layout_name in layout_mgr.list_layouts():
            print(f"  - {layout_name}")
        return
    
    # Handle data export commands
    if args.export_csv or args.export_json:
        db = get_database()
        if args.export_csv:
            success = db.export_to_csv(args.export_csv, hours=args.export_hours)
            print(f"{'✓' if success else '✗'} Exported to {args.export_csv}")
        if args.export_json:
            success = db.export_to_json(args.export_json, hours=args.export_hours)
            print(f"{'✓' if success else '✗'} Exported to {args.export_json}")
        return
    
    # Show statistics if requested
    if args.show_stats:
        db = get_database()
        stats = db.get_stats(hours=24)
        print("\nPerformance Statistics (Last 24 Hours)")
        print("=" * 50)
        if stats and stats.get('count', 0) > 0:
            print(f"  CPU Average:    {stats.get('avg_cpu') or 0:.1f}%")
            print(f"  CPU Peak:       {stats.get('max_cpu') or 0:.1f}%")
            print(f"  GPU Average:    {stats.get('avg_gpu') or 0:.1f}%")
            print(f"  GPU Peak:       {stats.get('max_gpu') or 0:.1f}%")
            print(f"  Memory Average: {stats.get('avg_memory') or 0:.1f}%")
            print(f"  Memory Peak:    {stats.get('max_memory') or 0:.1f}%")
            print(f"  Temp Average:   {stats.get('avg_temp') or 0:.1f}°C")
            print(f"  Temp Peak:      {stats.get('max_temp') or 0:.1f}°C")
            print(f"  Data Points:    {stats.get('count', 0)}")
        else:
            print("  No data collected yet. Run the app to start collecting metrics.")
        print("=" * 50)
        return
    
    # Show recent alerts if requested
    if args.show_alerts:
        db = get_database()
        alerts = db.get_alerts(hours=24)
        print("\n🔔 Recent Alerts (Last 24 Hours)")
        print("=" * 50)
        if alerts:
            for alert in alerts[:10]:  # Show last 10
                timestamp = datetime.fromtimestamp(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"  [{timestamp}] {alert['message']}")
        else:
            print("  No alerts in the last 24 hours")
        print("=" * 50)
        return
    
    # Show problematic processes if requested
    if args.show_processes:
        proc_monitor = get_process_monitor()
        issues = proc_monitor.scan_processes()
        summary = proc_monitor.get_problem_summary()
        
        print("\n Problematic Processes")
        print("=" * 70)
        print(f"  Zombie processes:      {summary['zombie']}")
        print(f"  Stuck processes:       {summary['stuck']}")
        print(f"  High CPU processes:    {summary['high_cpu']}")
        print(f"  High memory processes: {summary['high_memory']}")
        print("=" * 70)
        
        if issues.get('zombie'):
            print("\n🧟 Zombie Processes:")
            for proc in issues['zombie'][:5]:
                print(f"  - {proc.name} (PID: {proc.pid})")
        
        if issues.get('stuck'):
            print("\nStuck Processes:")
            for proc in issues['stuck'][:5]:
                print(f"  - {proc.name} (PID: {proc.pid}, CPU: {proc.cpu_percent:.1f}%)")
        
        if issues.get('unresponsive'):
            print("\nUnresponsive Processes:")
            for proc in issues['unresponsive'][:5]:
                print(f"  - {proc.name} (PID: {proc.pid})")
        
        print("\nTop CPU Processes:")
        for name, pid, cpu in proc_monitor.get_top_cpu_processes(args.top_cpu):
            print(f"  - {name:30} (PID: {pid:6}) {cpu:6.1f}%")
        
        print("\nTop Memory Processes:")
        for name, pid, mem in proc_monitor.get_top_memory_processes(args.top_memory):
            print(f"  - {name:30} (PID: {pid:6}) {mem:6.1f}%")
        
        print("=" * 70)
        return
    
    # Create app with feature flags
    app = Atlas(
        config_path=args.config,
        simulated=args.simulated,
        enable_alerts=not args.no_alerts,
        enable_history=not args.no_history,
        enable_process_monitor=not args.no_process_monitor,
        enable_web_viewer=not args.no_web_viewer,
        enable_widget_server=not args.no_widget_server
    )
    
    if args.theme:
        app.theme_manager.set_theme(args.theme)
    
    # Set layout if provided
    if args.layout:
        layout_mgr = get_layout_manager()
        if layout_mgr.set_current_layout(args.layout):
            logger.info(f"Using layout: {args.layout}")
        else:
            logger.warning(f"Layout '{args.layout}' not found, using default")
    
    # Set custom refresh rate if provided
    if args.refresh_rate != 1.0:
        app.config_manager.config['display']['refresh_rate'] = args.refresh_rate
    
    app.run()

if __name__ == "__main__":
    main()
