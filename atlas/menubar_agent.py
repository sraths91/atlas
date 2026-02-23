#!/usr/bin/env python3
"""
ATLAS Menu Bar Agent
Displays Fleet Agent status in macOS menu bar with ATLAS logo icon
"""

import rumps
import threading
import time
import logging
import requests
import webbrowser
import subprocess
import sys
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def hide_dock_icon():
    """Hide the Python app from the Dock (macOS only)
    
    This uses Apple's LSBackgroundOnly/LSUIElement approach via PyObjC
    to make the app a pure menu bar agent with no Dock presence.
    """
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        app = NSApplication.sharedApplication()
        # ActivationPolicyAccessory = menu bar only, no Dock icon
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        logger.info("Dock icon hidden - running as menu bar agent only")
        return True
    except ImportError:
        logger.warning("PyObjC not available - Dock icon will be visible. Install with: pip install pyobjc-framework-Cocoa")
        return False
    except Exception as e:
        logger.warning(f"Could not hide Dock icon: {e}")
        return False


class AtlasMenuBarApp(rumps.App):
    """
    ATLAS Fleet Agent menu bar application
    Shows connection status with colored indicator dots
    """
    
    def __init__(self, fleet_server_url: Optional[str] = None, agent_port: int = 8767):
        """
        Initialize menu bar app
        
        Args:
            fleet_server_url: Fleet server URL for health checks
            agent_port: Local agent port (default: 8767)
        """
        # Get icon directory
        icon_dir = Path(__file__).parent / 'menubar_icons'
        
        # Use connected icon as default
        default_icon = str(icon_dir / 'atlas_connected@2x.png')
        
        super().__init__(
            name="ATLAS Agent",
            icon=default_icon,
            quit_button=None  # Custom quit handling
        )
        
        self.fleet_server_url = fleet_server_url
        self.agent_port = agent_port
        self.icon_dir = icon_dir

        # SSL verification: use CA cert if available, else disable with warning
        ca_cert = Path.home() / '.fleet-certs' / 'cert.pem'
        if ca_cert.exists():
            self._ssl_verify = str(ca_cert)
            logger.info(f"SSL verification enabled using CA cert: {ca_cert}")
        else:
            self._ssl_verify = False
            if fleet_server_url and fleet_server_url.startswith('https://'):
                logger.warning(
                    "SSL verification disabled: no CA cert at %s. "
                    "Copy the server's cert.pem to ~/.fleet-certs/cert.pem",
                    ca_cert,
                )

        # Status tracking
        self.agent_running = False
        self.fleet_connected = False
        self.last_check = None
        self.status_message = "Initializing..."
        
        # Slow speed alert tracking
        self.slow_speed_alert_active = False
        self.slow_speed_info = None

        # Quick stats tracking
        self.cpu_percent = 0
        self.memory_percent = 0
        self.network_down = 0.0
        self.network_up = 0.0

        # Menu items
        self.status_item = rumps.MenuItem("Status: Initializing...")
        self.speed_alert_item = rumps.MenuItem("Speed: Normal")
        self.separator1 = rumps.separator

        # Quick Stats submenu
        self.stats_item = rumps.MenuItem("Quick Stats")
        self.cpu_item = rumps.MenuItem("CPU: --")
        self.memory_item = rumps.MenuItem("Memory: --")
        self.network_item = rumps.MenuItem("Network: --")

        self.separator2 = rumps.separator
        self.dashboard_item = rumps.MenuItem("Open Dashboard", callback=self.open_dashboard)
        self.network_analysis_item = rumps.MenuItem("Network Analysis", callback=self.open_network_analysis)
        self.fleet_dashboard_item = rumps.MenuItem("Open Fleet Dashboard", callback=self.open_fleet_dashboard)

        self.separator3 = rumps.separator
        self.speed_test_item = rumps.MenuItem("Run Speed Test", callback=self.run_speed_test)
        self.export_item = rumps.MenuItem("Export Recent Data", callback=self.export_data)

        self.separator4 = rumps.separator
        self.start_agent_item = rumps.MenuItem("Start Agent", callback=self.start_agent)
        self.restart_agent_item = rumps.MenuItem("Restart Agent", callback=self.restart_agent)
        self.reconnect_item = rumps.MenuItem("Reconnect", callback=self.reconnect)
        self.separator5 = rumps.separator
        self.quit_item = rumps.MenuItem("Quit ATLAS Agent", callback=self.quit_app)

        # Build menu
        self.menu = [
            self.status_item,
            self.speed_alert_item,
            self.separator1,
            self.stats_item,
            self.separator2,
            self.dashboard_item,
            self.network_analysis_item,
            self.fleet_dashboard_item,
            self.separator3,
            self.speed_test_item,
            self.export_item,
            self.separator4,
            self.start_agent_item,
            self.restart_agent_item,
            self.reconnect_item,
            self.separator5,
            self.quit_item
        ]

        # Add submenu items to Quick Stats
        self.stats_item.add(self.cpu_item)
        self.stats_item.add(self.memory_item)
        self.stats_item.add(self.network_item)
        
        # Start status checker thread
        self.running = True
        self.checker_thread = threading.Thread(target=self._status_checker, daemon=True)
        self.checker_thread.start()
        
        logger.info("ATLAS menu bar app initialized")
    
    def _status_checker(self):
        """Background thread to check agent and fleet status"""
        check_counter = 0
        while self.running:
            try:
                # Check local agent health
                agent_healthy = self._check_agent_health()

                # Check fleet connection if URL provided
                fleet_connected = False
                if self.fleet_server_url:
                    fleet_connected = self._check_fleet_connection()

                # Check slow speed alert status
                self._check_slow_speed_status()

                # Update quick stats every 10 seconds (every other check)
                if check_counter % 2 == 0 and agent_healthy:
                    self._update_quick_stats()

                # Update status
                self.agent_running = agent_healthy
                self.fleet_connected = fleet_connected

                # Determine overall status - slow speed alert takes priority for warning
                if self.slow_speed_alert_active:
                    status = 'warning'
                    self.status_message = "[!] Slow Internet Speed"
                elif agent_healthy and (fleet_connected or not self.fleet_server_url):
                    status = 'connected'
                    self.status_message = "Running & Connected"
                elif agent_healthy and not fleet_connected:
                    status = 'warning'
                    self.status_message = "[!] Running (Disconnected from Fleet)"
                elif not agent_healthy:
                    status = 'error'
                    self.status_message = "[X] Agent Not Running"
                else:
                    status = 'disconnected'
                    self.status_message = "Disconnected"

                # Update icon and menu
                self._update_icon(status)
                self._update_menu()

                self.last_check = time.time()
                check_counter += 1

            except Exception as e:
                logger.error(f"Error in status checker: {e}")
                self.status_message = f"[!] Error: {str(e)[:50]}"
                self._update_icon('error')

            # Check every 5 seconds
            time.sleep(5)
    
    def _check_agent_health(self) -> bool:
        """Check if local agent is running and healthy"""
        try:
            response = requests.get(
                f"http://localhost:{self.agent_port}/api/agent/health",
                timeout=2
            )
            return response.status_code == 200
        except (requests.RequestException, OSError):
            return False
    
    def _check_fleet_connection(self) -> bool:
        """Check if agent can connect to fleet server"""
        if not self.fleet_server_url:
            return False

        try:
            # Try to reach fleet server
            response = requests.get(
                f"{self.fleet_server_url}/api/fleet/machines",
                timeout=2,
                verify=self._ssl_verify
            )
            return response.status_code in [200, 401]  # 401 means server is up but auth required
        except (requests.RequestException, OSError):
            return False
    
    def _check_slow_speed_status(self):
        """Check slow speed alert status from the agent API"""
        try:
            response = requests.get(
                f"http://localhost:{self.agent_port}/api/speedtest/slow-status",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                self.slow_speed_alert_active = data.get('alert_active', False)
                self.slow_speed_info = data
            else:
                self.slow_speed_alert_active = False
                self.slow_speed_info = None
        except (requests.RequestException, OSError, ValueError):
            # If we can't reach the API, don't change alert status
            pass

    def _update_quick_stats(self):
        """Fetch and update quick stats from agent API"""
        try:
            response = requests.get(
                f"http://localhost:{self.agent_port}/api/system/comprehensive",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()

                # Extract stats
                self.cpu_percent = data.get('cpu', {}).get('percent', 0)
                self.memory_percent = data.get('memory', {}).get('percent', 0)

                # Network stats - convert bytes to Mbps
                net = data.get('network', {})
                self.network_down = net.get('bytes_recv_per_sec', 0) * 8 / 1_000_000  # bytes/s to Mbps
                self.network_up = net.get('bytes_sent_per_sec', 0) * 8 / 1_000_000

                # Update menu items
                self.cpu_item.title = f"CPU: {self.cpu_percent:.0f}%"
                self.memory_item.title = f"Memory: {self.memory_percent:.0f}%"
                self.network_item.title = f"Network: ↓{self.network_down:.1f} ↑{self.network_up:.1f} Mbps"

        except Exception as e:
            logger.debug(f"Could not update quick stats: {e}")
            # Keep last known values
    
    def _update_icon(self, status: str):
        """Update menu bar icon based on status"""
        try:
            icon_map = {
                'connected': 'atlas_connected@2x.png',
                'warning': 'atlas_warning@2x.png',
                'error': 'atlas_error@2x.png',
                'disconnected': 'atlas_disconnected@2x.png'
            }
            
            icon_file = self.icon_dir / icon_map.get(status, 'atlas_disconnected@2x.png')
            if icon_file.exists():
                self.icon = str(icon_file)
        except Exception as e:
            logger.error(f"Error updating icon: {e}")
    
    def _update_menu(self):
        """Update menu item text with current status"""
        try:
            self.status_item.title = f"Status: {self.status_message}"

            # Show Start Agent when agent is down, Restart Agent when running
            self.start_agent_item.hidden = self.agent_running
            self.restart_agent_item.hidden = not self.agent_running

            # Update speed alert menu item
            if self.slow_speed_alert_active and self.slow_speed_info:
                count = self.slow_speed_info.get('consecutive_slow_count', 0)
                threshold = self.slow_speed_info.get('threshold', 20)
                self.speed_alert_item.title = f"[!] Speed: {count} slow tests (<{threshold} Mbps)"
            else:
                self.speed_alert_item.title = "Speed: Normal"
        except Exception as e:
            logger.error(f"Error updating menu: {e}")
    
    @rumps.clicked("Open Dashboard")
    def open_dashboard(self, _):
        """Open local agent dashboard in browser"""
        try:
            webbrowser.open(f"http://localhost:{self.agent_port}")
            rumps.notification(
                title="ATLAS Agent",
                subtitle="Dashboard Opened",
                message=f"Opening http://localhost:{self.agent_port}"
            )
        except Exception as e:
            logger.error(f"Error opening dashboard: {e}")
            rumps.alert(
                title="Error",
                message=f"Could not open dashboard: {e}"
            )
    
    @rumps.clicked("Network Analysis")
    def open_network_analysis(self, _):
        """Open network analysis widget in browser"""
        try:
            webbrowser.open(f"http://localhost:{self.agent_port}/widget/network-analysis")
            rumps.notification(
                title="ATLAS Agent",
                subtitle="Network Analysis Opened",
                message="Opening root cause analysis tool"
            )
        except Exception as e:
            logger.error(f"Error opening network analysis: {e}")
            rumps.alert(
                title="Error",
                message=f"Could not open network analysis: {e}"
            )

    @rumps.clicked("Open Fleet Dashboard")
    def open_fleet_dashboard(self, _):
        """Open fleet server dashboard in browser"""
        if not self.fleet_server_url:
            rumps.alert(
                title="No Fleet Server",
                message="Fleet server URL not configured"
            )
            return

        try:
            # Extract base URL and add /dashboard
            base_url = self.fleet_server_url.rstrip('/')
            dashboard_url = f"{base_url}/dashboard"

            webbrowser.open(dashboard_url)
            rumps.notification(
                title="ATLAS Agent",
                subtitle="Fleet Dashboard Opened",
                message=f"Opening {dashboard_url}"
            )
        except Exception as e:
            logger.error(f"Error opening fleet dashboard: {e}")
            rumps.alert(
                title="Error",
                message=f"Could not open fleet dashboard: {e}"
            )

    @rumps.clicked("Run Speed Test")
    def run_speed_test(self, _):
        """Trigger a manual speed test"""
        rumps.notification(
            title="ATLAS Agent",
            subtitle="Speed Test Started",
            message="Running speed test... check dashboard for results"
        )
        # Open speedtest widget which will show the test in progress
        try:
            webbrowser.open(f"http://localhost:{self.agent_port}/widget/speedtest")
        except Exception as e:
            logger.error(f"Error opening speedtest widget: {e}")

    @rumps.clicked("Export Recent Data")
    def export_data(self, _):
        """Open dashboard to export menu"""
        try:
            # Open dashboard where user can access export menu
            webbrowser.open(f"http://localhost:{self.agent_port}/dashboard")
            rumps.notification(
                title="ATLAS Agent",
                subtitle="Export Data",
                message="Click the menu icon, then Export Data to download CSV files"
            )
        except Exception as e:
            logger.error(f"Error opening dashboard: {e}")
            rumps.alert(
                title="Error",
                message=f"Could not open dashboard: {e}"
            )
    
    def _launch_agent(self):
        """Launch the agent using saved startup config. Returns True on success."""
        import json as _json

        config_path = Path.home() / '.atlas' / 'agent-startup.json'
        if not config_path.exists():
            rumps.alert(
                title="Cannot Start Agent",
                message="No startup config found at ~/.atlas/agent-startup.json.\n\n"
                        "Start the agent manually first with start_atlas_agent.py "
                        "to create the config."
            )
            return False

        try:
            with open(config_path) as f:
                config = _json.load(f)

            project_dir = config.get('project_dir', '')
            python_path = config.get('python_path', sys.executable)
            script = Path(project_dir) / 'start_atlas_agent.py'

            if not script.exists():
                rumps.alert(
                    title="Cannot Start Agent",
                    message=f"Agent script not found at:\n{script}"
                )
                return False

            # Build command (--no-menubar since this menubar is already running)
            cmd = [python_path, str(script), '--no-menubar']
            if config.get('port'):
                cmd += ['--port', str(config['port'])]
            if config.get('fleet_server'):
                cmd += ['--fleet-server', config['fleet_server']]
            if config.get('machine_id'):
                cmd += ['--machine-id', config['machine_id']]
            if config.get('api_key'):
                cmd += ['--api-key', config['api_key']]
            if config.get('encryption_key'):
                cmd += ['--encryption-key', config['encryption_key']]

            # Launch agent as detached subprocess
            subprocess.Popen(
                cmd,
                cwd=project_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            logger.info(f"Launched agent: {' '.join(cmd)}")
            return True

        except Exception as e:
            logger.error(f"Error starting agent: {e}")
            rumps.alert(
                title="Error Starting Agent",
                message=str(e)
            )
            return False

    def _kill_agent(self):
        """Kill any running agent processes."""
        try:
            result = subprocess.run(
                ['pkill', '-f', 'start_atlas_agent.py'],
                capture_output=True, text=True
            )
            # Also kill any standalone live_widgets server
            subprocess.run(
                ['pkill', '-f', 'atlas.live_widgets'],
                capture_output=True, text=True
            )
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error killing agent: {e}")
            return False

    @rumps.clicked("Start Agent")
    def start_agent(self, _):
        """Start the ATLAS agent"""
        self.status_message = "Starting agent..."
        self._update_menu()

        if self._launch_agent():
            rumps.notification(
                title="ATLAS Agent",
                subtitle="Agent Starting",
                message="The agent is launching. It should be ready in a few seconds."
            )

    @rumps.clicked("Restart Agent")
    def restart_agent(self, _):
        """Restart the ATLAS agent"""
        self.status_message = "Restarting agent..."
        self._update_menu()

        self._kill_agent()

        if self._launch_agent():
            rumps.notification(
                title="ATLAS Agent",
                subtitle="Agent Restarting",
                message="The agent is restarting. It should be ready in a few seconds."
            )

    @rumps.clicked("Reconnect")
    def reconnect(self, _):
        """Force reconnection check"""
        self.status_message = "Reconnecting..."
        self._update_menu()

        # Trigger immediate check
        threading.Thread(target=self._force_check, daemon=True).start()
    
    def _force_check(self):
        """Force immediate status check"""
        time.sleep(0.5)  # Brief delay for UI feedback
        # Status checker will run on next iteration
    
    @rumps.clicked("Quit ATLAS Agent")
    def quit_app(self, _):
        """Quit the menu bar app"""
        response = rumps.alert(
            title="Quit ATLAS Agent?",
            message="This will close the menu bar app but the agent will continue running in the background.",
            ok="Quit Menu Bar App",
            cancel="Cancel"
        )
        
        if response == 1:  # OK clicked
            self.running = False
            rumps.quit_application()


def start_menubar_app(fleet_server_url: Optional[str] = None, agent_port: int = 8767, hide_dock: bool = True):
    """
    Start the ATLAS menu bar application
    
    Args:
        fleet_server_url: Fleet server URL for health checks
        agent_port: Local agent port (default: 8767)
        hide_dock: If True, hide the app from the Dock (default: True)
    
    Note: This function blocks and runs the menu bar app main loop
    """
    # Hide from Dock before creating the app
    if hide_dock:
        hide_dock_icon()
    
    app = AtlasMenuBarApp(fleet_server_url=fleet_server_url, agent_port=agent_port)
    app.run()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ATLAS Fleet Agent Menu Bar App')
    parser.add_argument('--fleet-server', type=str, help='Fleet server URL')
    parser.add_argument('--agent-port', type=int, default=8767, help='Local agent port')
    parser.add_argument('--show-dock', action='store_true', help='Show app in Dock (default: hidden)')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting ATLAS menu bar app...")
    logger.info(f"Agent port: {args.agent_port}")
    if args.fleet_server:
        logger.info(f"Fleet server: {args.fleet_server}")
    if not args.show_dock:
        logger.info("Dock icon: Hidden (use --show-dock to show)")
    
    start_menubar_app(
        fleet_server_url=args.fleet_server,
        agent_port=args.agent_port,
        hide_dock=not args.show_dock
    )
