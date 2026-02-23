"""
Fleet Agent - Runs on each Mac and reports metrics to central server
"""
import json
import time
import socket
import platform
import logging
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import psutil
import urllib3

# Import encryption module
try:
    from .encryption import DataEncryption, ENCRYPTION_AVAILABLE
except ImportError:
    # Fallback for direct execution
    from encryption import DataEncryption, ENCRYPTION_AVAILABLE

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class FleetAgent:
    """Agent that collects and reports system metrics to central server"""
    
    def __init__(self, server_url: str, machine_id: Optional[str] = None, api_key: Optional[str] = None,
                 encryption_key: Optional[str] = None, verify_ssl: bool = True):
        """
        Initialize fleet agent
        
        Args:
            server_url: URL of central server (e.g., https://fleet-server:8768)
            machine_id: Unique identifier for this machine (defaults to hostname)
            api_key: Optional API key for authentication
            encryption_key: Optional encryption key for end-to-end encryption (base64)
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.server_url = server_url.rstrip('/')
        self.machine_id = machine_id or socket.gethostname()
        self.api_key = api_key
        self.running = False
        self.thread = None
        self.command_thread = None
        self.report_interval = 10  # seconds
        self.command_poll_interval = 30  # seconds
        self.last_report = None
        
        # Initialize end-to-end encryption
        self.encryption = DataEncryption(encryption_key)
        
        # Create a session for connection pooling and reuse
        self.session = requests.Session()
        
        # Configure SSL verification
        if verify_ssl:
            self.session.verify = True  # Verify SSL certificates
            logger.info("SSL certificate verification enabled")
        else:
            self.session.verify = False
            # Only disable warnings if explicitly choosing to not verify
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL certificate verification disabled - not recommended for production")
        
        # Warn if using HTTP (not HTTPS)
        if not self.server_url.startswith('https://'):
            logger.warning("Using HTTP (not HTTPS) - data transmitted without transport encryption!")
            logger.warning("Strongly recommend using HTTPS for production deployments")
        
        # Get machine info once at startup
        self.machine_info = self._get_machine_info()
        
        logger.info(f"Fleet agent initialized for machine: {self.machine_id}")
    
    def _get_machine_info(self) -> Dict[str, Any]:
        """Get static machine information"""
        try:
            info = {
                'hostname': socket.gethostname(),
                'os': platform.system(),
                'os_version': platform.mac_ver()[0] if platform.system() == 'Darwin' else platform.version(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'cpu_count': psutil.cpu_count(logical=False),
                'cpu_threads': psutil.cpu_count(logical=True),
                'total_memory': psutil.virtual_memory().total,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            
            # Add local IP address
            info['local_ip'] = self._get_local_ip()
            
            # Add Mac-specific information
            if platform.system() == 'Darwin':
                info['computer_name'] = self._get_computer_name()
                info['serial_number'] = self._get_serial_number()
            
            # Add disk information
            info['disks'] = self._get_disk_info()
            
            return info
        except Exception as e:
            logger.error(f"Error getting machine info: {e}")
            return {}
    
    def _get_local_ip(self) -> str:
        """Get the local IP address (non-loopback)"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except (OSError, socket.error):
            try:
                addrs = psutil.net_if_addrs()
                for iface, addr_list in addrs.items():
                    if iface.startswith(('lo', 'utun', 'awdl')):
                        continue
                    for addr in addr_list:
                        if addr.family == socket.AF_INET:
                            ip = addr.address
                            if not ip.startswith('127.'):
                                return ip
            except (OSError, KeyError):
                pass
            return 'localhost'
    
    def _get_disk_info(self) -> list:
        """Get information about all disks"""
        disks = []
        try:
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free
                    })
                except (OSError, PermissionError):
                    pass
        except Exception as e:
            logger.debug(f"Error getting disk info: {e}")
        return disks
    
    def _get_computer_name(self) -> str:
        """Get the Mac computer name"""
        try:
            import subprocess
            result = subprocess.run(
                ['scutil', '--get', 'ComputerName'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass
        return socket.gethostname()
    
    def _get_serial_number(self) -> str:
        """Get the Mac serial number"""
        try:
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                output = result.stdout
                for line in output.split('\n'):
                    if 'Serial Number' in line:
                        serial = line.split(':', 1)[1].strip()
                        return serial
        except (subprocess.SubprocessError, OSError, IndexError):
            pass
        return 'Unknown'
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            mem = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            net_io = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            # Load average (macOS/Unix)
            try:
                load_avg = psutil.getloadavg()
            except (AttributeError, OSError):
                load_avg = [0, 0, 0]
            
            # Battery (if laptop)
            battery = None
            try:
                bat = psutil.sensors_battery()
                if bat:
                    battery = {
                        'percent': bat.percent,
                        'plugged': bat.power_plugged,
                        'time_left': bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else None
                    }
            except (AttributeError, RuntimeError):
                pass
            
            # System uptime
            uptime_seconds = time.time() - psutil.boot_time()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': uptime_seconds,
                'cpu': {
                    'percent': cpu_percent,
                    'load_avg': load_avg,
                    'count': psutil.cpu_count(logical=False),
                    'threads': psutil.cpu_count(logical=True)
                },
                'memory': {
                    'total': mem.total,
                    'available': mem.available,
                    'used': mem.used,
                    'percent': mem.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                },
                'processes': {
                    'total': process_count
                },
                'battery': battery
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {}
    
    def _send_report(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics to central server with end-to-end encryption"""
        try:
            # Create payload
            payload = {
                'machine_id': self.machine_id,
                'machine_info': self.machine_info,
                'metrics': metrics
            }
            
            # Encrypt payload if encryption is enabled
            encrypted_payload = self.encryption.encrypt_payload(payload)
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            # Send encrypted payload
            response = self.session.post(
                f"{self.server_url}/api/fleet/report",
                json=encrypted_payload,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                self.last_report = datetime.now()
                logger.debug(f"Successfully reported metrics to server")
                return True
            else:
                logger.warning(f"Server returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Connection error (will retry): {str(e)[:100]}")
            return False
        except requests.exceptions.Timeout:
            logger.error(f"Timeout connecting to server")
            return False
        except Exception as e:
            logger.error(f"Error sending report: {e}")
            return False
    
    def _report_loop(self):
        """Main reporting loop"""
        logger.info(f"Agent reporting loop started (interval: {self.report_interval}s)")
        
        while self.running:
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                
                if metrics:
                    # Send to server
                    self._send_report(metrics)
                
                # Wait for next interval
                time.sleep(self.report_interval)
                
            except Exception as e:
                logger.error(f"Error in report loop: {e}")
                time.sleep(5)  # Wait a bit before retrying
    
    def start(self, interval: int = 10):
        """
        Start the agent
        
        Args:
            interval: Reporting interval in seconds
        """
        if self.running:
            logger.warning("Agent is already running")
            return
        
        self.report_interval = interval
        self.running = True
        
        # Start reporting thread
        self.thread = threading.Thread(target=self._report_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Fleet agent started for {self.machine_id}")
    
    def stop(self):
        """Stop the agent"""
        if not self.running:
            return
        
        logger.info("Stopping fleet agent...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("Fleet agent stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            'machine_id': self.machine_id,
            'server_url': self.server_url,
            'running': self.running,
            'report_interval': self.report_interval,
            'last_report': self.last_report.isoformat() if self.last_report else None
        }


def main():
    """Run agent as standalone process"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Mac Fleet Agent')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--server', required=False, help='Central server URL')
    parser.add_argument('--machine-id', help='Machine identifier (default: hostname)')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--interval', type=int, default=10, help='Reporting interval in seconds')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    server_url = args.server
    api_key = args.api_key
    interval = args.interval
    machine_id = args.machine_id
    encryption_key = None
    verify_ssl = True
    
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
                server_url = server_url or config.get('server_url')
                api_key = api_key or config.get('api_key')
                interval = args.interval if args.interval != 10 else config.get('interval', 10)
                machine_id = machine_id or config.get('machine_id')
                encryption_key = config.get('encryption_key')
                verify_ssl = config.get('verify_ssl', True)
                logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            sys.exit(1)
    
    if not server_url:
        logger.error("Server URL is required. Use --server or --config")
        sys.exit(1)
    
    # Create and start agent
    agent = FleetAgent(
        server_url=server_url,
        machine_id=machine_id,
        api_key=api_key,
        encryption_key=encryption_key,
        verify_ssl=verify_ssl
    )
    
    agent.start(interval=interval)
    
    logger.info(f"Fleet agent running. Reporting to {server_url} every {interval}s")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        agent.stop()
        logger.info("Agent stopped")


if __name__ == '__main__':
    main()
