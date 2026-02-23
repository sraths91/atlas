"""
Fleet Agent - Runs on each Mac and reports metrics to central server
"""
import json
import time
import socket
import platform
import logging
import random
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import psutil
import urllib3

# SSL warning suppression moved to _configure_ssl_verification() method

# Import E2EE encryption
try:
    from atlas.encryption import DataEncryption, ENCRYPTION_AVAILABLE as E2EE_AVAILABLE
except ImportError:
    E2EE_AVAILABLE = False
    DataEncryption = None

# Import new monitoring capabilities
try:
    from atlas.network.monitors.vpn_monitor import get_vpn_monitor
    VPN_MONITOR_AVAILABLE = True
except ImportError:
    VPN_MONITOR_AVAILABLE = False

try:
    from atlas.network.monitors.saas_endpoint_monitor import get_saas_endpoint_monitor
    SAAS_MONITOR_AVAILABLE = True
except ImportError:
    SAAS_MONITOR_AVAILABLE = False

try:
    from atlas.network.monitors.network_quality_monitor import get_network_quality_monitor
    NETWORK_QUALITY_MONITOR_AVAILABLE = True
except ImportError:
    NETWORK_QUALITY_MONITOR_AVAILABLE = False

try:
    from atlas.network.monitors.wifi_roaming_monitor import get_wifi_roaming_monitor
    WIFI_ROAMING_MONITOR_AVAILABLE = True
except ImportError:
    WIFI_ROAMING_MONITOR_AVAILABLE = False

try:
    from atlas.security_monitor import get_security_monitor
    SECURITY_MONITOR_AVAILABLE = True
except ImportError:
    SECURITY_MONITOR_AVAILABLE = False

try:
    from atlas.database import get_database
    LOCAL_DB_AVAILABLE = True
except ImportError:
    LOCAL_DB_AVAILABLE = False

logger = logging.getLogger(__name__)


class FleetAgent:
    """Agent that collects and reports system metrics to central server"""

    def __init__(self, server_url: Optional[str] = None, machine_id: Optional[str] = None,
                 api_key: Optional[str] = None, encryption_key: Optional[str] = None):
        """
        Initialize fleet agent

        Args:
            server_url: URL of central server (None for standalone/local-only mode)
            machine_id: Unique identifier for this machine (defaults to hostname)
            api_key: API key for fleet server authentication (required for fleet mode)
            encryption_key: Optional E2EE encryption key (shared with server)
        """
        self.server_url = server_url.rstrip('/') if server_url else None
        self.machine_id = machine_id or socket.gethostname()
        self.api_key = api_key
        self.fleet_mode = bool(self.server_url and self.api_key)
        self.running = False
        self.thread = None
        self.command_thread = None
        self.widget_thread = None
        self.report_interval = 10  # seconds
        self.command_poll_interval = 30  # seconds
        self.last_report = None

        # Only set up fleet connection when in fleet mode
        self.session = requests.Session()
        if self.fleet_mode:
            self._configure_ssl_verification()
        else:
            logger.info("Running in standalone mode (local monitoring only)")
        
        # Initialize E2EE encryption if key provided
        self.encryptor = None
        if encryption_key and E2EE_AVAILABLE and DataEncryption:
            self.encryptor = DataEncryption(encryption_key)
            if self.encryptor.enabled:
                logger.info("E2EE payload encryption enabled")
            else:
                logger.warning("E2EE encryption key provided but encryption failed to initialize")
        elif encryption_key and not E2EE_AVAILABLE:
            logger.warning("Encryption key provided but cryptography library not available")
        
        # Agent DB key sharing state
        self._db_key_shared = False
        self._last_shared_db_key = None

        # Widget monitors (initialized later if enabled)
        self.widget_monitors = {}
        self.widget_log_collector = None
        
        # Get machine info once at startup
        self.machine_info = self._get_machine_info()
        
        logger.info(f"Fleet agent initialized for machine: {self.machine_id}")

    def _configure_ssl_verification(self):
        """Configure SSL verification using fleet CA cert if available."""
        from pathlib import Path

        ca_cert_path = Path.home() / '.fleet-certs' / 'cert.pem'

        if ca_cert_path.exists():
            self.session.verify = str(ca_cert_path)
            logger.info(f"SSL verification enabled using CA cert: {ca_cert_path}")
        elif self.server_url.startswith('https://'):
            # HTTPS but no CA cert - warn and fall back to unverified
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.session.verify = False
            logger.warning(
                "SSL verification DISABLED: no CA cert at %s. "
                "Run fleet_cert_auto to generate certs, or copy the server's "
                "cert.pem to ~/.fleet-certs/cert.pem",
                ca_cert_path,
            )
        else:
            self.session.verify = True

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
            
            # Add local IP address for Atlas widget access
            info['local_ip'] = self._get_local_ip()
            
            # Add Mac-specific information (computer name and serial number)
            if platform.system() == 'Darwin':
                info['computer_name'] = self._get_computer_name()
                info['serial_number'] = self._get_serial_number()
            
            # Add disk information
            info['disks'] = self._get_disk_info()
            
            # Add network interfaces
            info['network_interfaces'] = self._get_network_interfaces()
            
            # Add GPU information (macOS)
            if platform.system() == 'Darwin':
                info['gpu'] = self._get_gpu_info()
            
            return info
        except Exception as e:
            logger.error(f"Error getting machine info: {e}")
            return {}
    
    def _get_local_ip(self) -> str:
        """Get the local IP address (non-loopback)"""
        try:
            # Try to get IP by connecting to an external address (doesn't actually send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except (OSError, socket.error):
            # Fallback: parse network interfaces
            try:
                addrs = psutil.net_if_addrs()
                for iface, addr_list in addrs.items():
                    # Skip loopback and virtual interfaces
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
                except (PermissionError, OSError):
                    pass
        except Exception as e:
            logger.debug(f"Error getting disk info: {e}")
        return disks
    
    def _get_network_interfaces(self) -> list:
        """Get network interface information"""
        interfaces = []
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for iface, addr_list in addrs.items():
                iface_info = {
                    'name': iface,
                    'addresses': [],
                    'is_up': stats[iface].isup if iface in stats else False,
                    'speed': stats[iface].speed if iface in stats else 0
                }
                
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        iface_info['addresses'].append({
                            'type': 'IPv4',
                            'address': addr.address
                        })
                    elif addr.family == socket.AF_INET6:
                        iface_info['addresses'].append({
                            'type': 'IPv6',
                            'address': addr.address
                        })
                
                if iface_info['addresses']:
                    interfaces.append(iface_info)
        except Exception as e:
            logger.debug(f"Error getting network interfaces: {e}")
        return interfaces
    
    def _get_computer_name(self) -> str:
        """Get the Mac computer name (as shown in System Preferences)"""
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
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass
        return socket.gethostname()  # Fallback to hostname
    
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
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass
        return 'Unknown'
    
    def _get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """Get GPU information (macOS specific)"""
        try:
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout
                # Parse GPU name
                for line in output.split('\n'):
                    if 'Chipset Model:' in line:
                        gpu_name = line.split(':', 1)[1].strip()
                        return {'name': gpu_name}
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass
        return None
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
            
            # Memory metrics
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            net_io = psutil.net_io_counters()
            
            # Process count and details
            process_count = len(psutil.pids())
            
            # Load average (macOS/Unix)
            try:
                load_avg = psutil.getloadavg()
            except (OSError, AttributeError):
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
            except (RuntimeError, OSError):
                pass
            
            # Top processes by CPU and Memory
            top_cpu_processes = []
            top_mem_processes = []
            try:
                procs = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']))

                # Top 5 by CPU (handle None values)
                for proc in sorted(procs, key=lambda p: p.info.get('cpu_percent') or 0, reverse=True)[:5]:
                    top_cpu_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info.get('cpu_percent') or 0,
                        'memory': proc.info.get('memory_percent') or 0,
                        'user': proc.info.get('username', 'unknown')
                    })

                # Top 5 by Memory (handle None values)
                for proc in sorted(procs, key=lambda p: p.info.get('memory_percent') or 0, reverse=True)[:5]:
                    top_mem_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info.get('cpu_percent') or 0,
                        'memory': proc.info.get('memory_percent') or 0,
                        'user': proc.info.get('username', 'unknown')
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                pass
            
            # System uptime
            uptime_seconds = time.time() - psutil.boot_time()
            
            # Network connections count
            connections_count = 0
            try:
                connections_count = len(psutil.net_connections())
            except (psutil.AccessDenied, OSError):
                pass
            
            # Logged in users
            users = []
            try:
                for user in psutil.users():
                    users.append({
                        'name': user.name,
                        'terminal': user.terminal,
                        'host': user.host,
                        'started': datetime.fromtimestamp(user.started).isoformat()
                    })
            except (OSError, KeyError):
                pass
            
            # Temperature (macOS specific)
            temperature = self._get_temperature()
            
            # Security status
            security = self._get_security_status()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': uptime_seconds,
                'cpu': {
                    'percent': cpu_percent,
                    'per_core': cpu_per_core,
                    'load_avg': load_avg,
                    'count': psutil.cpu_count(logical=False),
                    'threads': psutil.cpu_count(logical=True)
                },
                'memory': {
                    'total': mem.total,
                    'available': mem.available,
                    'used': mem.used,
                    'percent': mem.percent,
                    'swap_total': swap.total,
                    'swap_used': swap.used,
                    'swap_percent': swap.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent,
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0,
                    'read_count': disk_io.read_count if disk_io else 0,
                    'write_count': disk_io.write_count if disk_io else 0
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv,
                    'errin': net_io.errin,
                    'errout': net_io.errout,
                    'dropin': net_io.dropin,
                    'dropout': net_io.dropout,
                    'connections': connections_count
                },
                'processes': {
                    'total': process_count,
                    'top_cpu': top_cpu_processes,
                    'top_memory': top_mem_processes
                },
                'battery': battery,
                'temperature': temperature,
                'users': users,
                'security': security,
                # New Phase 1 & 2 metrics
                'vpn': self._get_vpn_metrics(),
                'saas_endpoints': self._get_saas_metrics(),
                'network_quality': self._get_network_quality_metrics(),
                'wifi_roaming': self._get_wifi_roaming_metrics(),
                'security_enhanced': self._get_enhanced_security_metrics()
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {}
    
    def _get_temperature(self) -> Optional[Dict[str, Any]]:
        """Get system temperature (macOS specific)"""
        try:
            import subprocess
            # Try to get temperature using powermetrics (requires sudo)
            result = subprocess.run(
                ['sudo', '-n', 'powermetrics', '--samplers', 'smc', '-n', '1'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'CPU die temperature' in line:
                        temp = float(line.split(':')[1].strip().split()[0])
                        return {'cpu': temp, 'unit': 'C'}
        except (subprocess.SubprocessError, OSError, TimeoutError, ValueError):
            pass
        return None
    
    def _get_security_status(self) -> Dict[str, Any]:
        """Get security status information"""
        security = {
            'firewall_enabled': False,
            'filevault_enabled': False,
            'gatekeeper_enabled': False,
            'sip_enabled': False
        }
        
        try:
            import subprocess
            
            # Check firewall status
            try:
                result = subprocess.run(
                    ['defaults', 'read', '/Library/Preferences/com.apple.alf', 'globalstate'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    security['firewall_enabled'] = '1' in result.stdout or '2' in result.stdout
            except (subprocess.SubprocessError, OSError, TimeoutError):
                pass
            
            # Check FileVault status
            try:
                result = subprocess.run(
                    ['fdesetup', 'status'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    security['filevault_enabled'] = 'On' in result.stdout
            except (subprocess.SubprocessError, OSError, TimeoutError):
                pass
            
            # Check Gatekeeper status
            try:
                result = subprocess.run(
                    ['spctl', '--status'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    security['gatekeeper_enabled'] = 'enabled' in result.stdout.lower()
            except (subprocess.SubprocessError, OSError, TimeoutError):
                pass
            
            # Check SIP status
            try:
                result = subprocess.run(
                    ['csrutil', 'status'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    security['sip_enabled'] = 'enabled' in result.stdout.lower()
            except (subprocess.SubprocessError, OSError, TimeoutError):
                pass
        except Exception as e:
            logger.debug(f"Error getting security status: {e}")
        
        return security

    def _get_vpn_metrics(self) -> Optional[Dict[str, Any]]:
        """Get VPN connection metrics"""
        if not VPN_MONITOR_AVAILABLE:
            return None

        try:
            monitor = get_vpn_monitor()
            status = monitor.get_current_status()
            return {
                'connected': status.get('connected', False),
                'vpn_client': status.get('vpn_client'),
                'interface_count': status.get('connection_count', 0),
                'interfaces': list(status.get('interfaces', {}).keys())
            }
        except Exception as e:
            logger.debug(f"Error getting VPN metrics: {e}")
            return None

    def _get_saas_metrics(self) -> Optional[Dict[str, Any]]:
        """Get SaaS endpoint availability metrics"""
        if not SAAS_MONITOR_AVAILABLE:
            return None

        try:
            monitor = get_saas_endpoint_monitor()
            summary = monitor.get_category_summary()

            # Convert to simplified format for transmission
            simplified = {}
            for category, stats in summary.items():
                simplified[category] = {
                    'availability': stats.get('availability_percent', 0),
                    'avg_latency': stats.get('avg_latency_ms', 0)
                }

            return simplified
        except Exception as e:
            logger.debug(f"Error getting SaaS metrics: {e}")
            return None

    def _get_network_quality_metrics(self) -> Optional[Dict[str, Any]]:
        """Get network quality metrics"""
        if not NETWORK_QUALITY_MONITOR_AVAILABLE:
            return None

        try:
            monitor = get_network_quality_monitor()
            summary = monitor.get_quality_summary()

            return {
                'tcp_retransmit_rate': summary.get('tcp', {}).get('avg_retransmit_rate_percent', 0),
                'dns_avg_latency': summary.get('dns', {}).get('avg_query_time_ms', 0),
                'dns_availability': summary.get('dns', {}).get('availability_percent', 0),
                'tls_avg_latency': summary.get('tls', {}).get('avg_handshake_time_ms', 0),
                'http_avg_latency': summary.get('http', {}).get('avg_response_time_ms', 0)
            }
        except Exception as e:
            logger.debug(f"Error getting network quality metrics: {e}")
            return None

    def _get_wifi_roaming_metrics(self) -> Optional[Dict[str, Any]]:
        """Get WiFi roaming metrics"""
        if not WIFI_ROAMING_MONITOR_AVAILABLE:
            return None

        try:
            monitor = get_wifi_roaming_monitor()
            summary = monitor.get_roaming_summary()
            channel_quality = monitor.get_current_channel_quality()

            return {
                'roaming_events': summary.get('total_roaming_events', 0),
                'sticky_client_incidents': summary.get('sticky_client_incidents', 0),
                'avg_roaming_latency': summary.get('avg_roaming_latency_ms', 0),
                'current_channel': channel_quality.get('channel'),
                'channel_utilization': channel_quality.get('utilization_percent', 0),
                'interfering_aps': channel_quality.get('interfering_aps', 0)
            }
        except Exception as e:
            logger.debug(f"Error getting WiFi roaming metrics: {e}")
            return None

    def _get_enhanced_security_metrics(self) -> Optional[Dict[str, Any]]:
        """Get enhanced security monitoring metrics"""
        if not SECURITY_MONITOR_AVAILABLE:
            return None

        try:
            monitor = get_security_monitor()
            status = monitor.get_current_security_status()

            # Get recent security events
            critical_events = monitor.get_security_events(severity='critical')
            high_events = monitor.get_security_events(severity='high')

            return {
                'security_score': status.get('security_score', 0),
                'firewall_enabled': status.get('firewall_enabled', False),
                'filevault_enabled': status.get('filevault_enabled', False),
                'gatekeeper_enabled': status.get('gatekeeper_enabled', False),
                'sip_enabled': status.get('sip_enabled', False),
                'screen_lock_enabled': status.get('screen_lock_enabled', False),
                'auto_updates_enabled': status.get('auto_updates_enabled', False),
                'pending_updates': status.get('pending_updates_count', 0),
                'critical_events_24h': len(critical_events),
                'high_events_24h': len(high_events)
            }
        except Exception as e:
            logger.debug(f"Error getting enhanced security metrics: {e}")
            return None

    def _update_e2ee_verification(self, verified: bool):
        """Update E2EE verification status in LiveWidgetHandler"""
        try:
            from atlas.live_widgets import LiveWidgetHandler
            LiveWidgetHandler.e2ee_server_verified = verified
            LiveWidgetHandler.last_e2ee_verification = datetime.now().isoformat()
        except Exception as e:
            logger.debug(f"Could not update E2EE verification status: {e}")
    
    def _save_new_encryption_key(self, new_key: str):
        """Save new encryption key to agent config file"""
        import json
        from pathlib import Path
        
        # Try agent config first (installed agent)
        agent_config_path = Path.home() / "Library" / "FleetAgent" / "config.json"
        if agent_config_path.exists():
            try:
                with open(agent_config_path, 'r') as f:
                    config = json.load(f)
                config['encryption_key'] = new_key
                with open(agent_config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                logger.info(f"Saved new encryption key to {agent_config_path}")
                return
            except Exception as e:
                logger.warning(f"Could not update agent config: {e}")
        
        # Fall back to fleet config (development mode)
        fleet_config_path = Path.home() / ".fleet-config.json"
        try:
            # Try encrypted config first
            encrypted_path = str(fleet_config_path) + '.encrypted'
            if Path(encrypted_path).exists():
                from .fleet_config_encryption import EncryptedConfigManager
                manager = EncryptedConfigManager(str(fleet_config_path))
                config = manager.decrypt_config() or {}
                if 'server' not in config:
                    config['server'] = {}
                config['server']['encryption_key'] = new_key
                manager.encrypt_config(config)
                logger.info("Saved new encryption key to encrypted fleet config")
                return
            
            # Plaintext config
            if fleet_config_path.exists():
                with open(fleet_config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            if 'server' not in config:
                config['server'] = {}
            config['server']['encryption_key'] = new_key
            
            with open(fleet_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Saved new encryption key to fleet config")
            
        except Exception as e:
            logger.error(f"Failed to save new encryption key: {e}")
            raise
    
    def _send_report(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics to central server (single attempt)"""
        if not self.fleet_mode:
            return False
        try:
            payload = {
                'machine_id': self.machine_id,
                'machine_info': self.machine_info,
                'metrics': metrics
            }

            # Include agent DB key when E2EE active and not yet shared (or key changed)
            if self.encryptor and self.encryptor.enabled and LOCAL_DB_AVAILABLE:
                try:
                    db = get_database()
                    db_key = db.encryption_key_b64
                    if db_key and (not self._db_key_shared or db_key != self._last_shared_db_key):
                        payload['agent_db_key'] = db_key
                except Exception:
                    pass

            # Encrypt payload if E2EE is enabled
            if self.encryptor and self.encryptor.enabled:
                payload = self.encryptor.encrypt_payload(payload)
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            response = self.session.post(
                f"{self.server_url}/api/fleet/report",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.last_report = datetime.now()
                self._consecutive_failures = 0  # Reset failure counter on success
                
                # Check server response for E2EE verification
                try:
                    resp_data = response.json()
                    if resp_data.get('e2ee_verified'):
                        self._update_e2ee_verification(True)
                        logger.debug("Server confirmed E2EE decryption successful")
                    if resp_data.get('db_key_stored') and LOCAL_DB_AVAILABLE:
                        try:
                            self._last_shared_db_key = get_database().encryption_key_b64
                            self._db_key_shared = True
                            logger.info("Fleet server stored agent DB encryption key")
                        except Exception:
                            pass
                except (json.JSONDecodeError, KeyError):
                    pass
                
                logger.info(f"Report sent successfully to {self.server_url}")
                return True
            else:
                logger.warning(f"Server returned status {response.status_code}: {response.text[:200]}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error to {self.server_url}: {str(e)[:100]}")
            return False
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout connecting to server (10s)")
            return False
        except Exception as e:
            logger.error(f"Error sending report: {e}")
            return False
    
    def _send_report_with_retry(self, metrics: Dict[str, Any], max_retries: int = 3) -> bool:
        """
        Send metrics to central server with exponential backoff retry.
        
        Args:
            metrics: Metrics data to send
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            True if report was sent successfully, False otherwise
        """
        for attempt in range(max_retries + 1):
            if self._send_report(metrics):
                if attempt > 0:
                    logger.info(f"Report succeeded after {attempt} retry attempt(s)")
                return True
            
            if attempt < max_retries:
                # Exponential backoff with jitter: 2^attempt + random(0-1) seconds
                # Attempt 0: 1-2s, Attempt 1: 2-3s, Attempt 2: 4-5s
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying report in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
        
        # Track consecutive failures for health monitoring
        if not hasattr(self, '_consecutive_failures'):
            self._consecutive_failures = 0
        self._consecutive_failures += 1
        
        if self._consecutive_failures >= 5:
            logger.error(f"Server unreachable: {self._consecutive_failures} consecutive report failures")
        else:
            logger.warning(f"Report failed after {max_retries} retries")
        
        return False
    
    def _execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a whitelisted command and return result"""
        action = command.get('action')
        params = command.get('params', {})
        
        try:
            if action == 'kill_process':
                pid = params.get('pid')
                if not pid:
                    return {'success': False, 'message': 'Missing PID parameter'}
                
                try:
                    process = psutil.Process(pid)
                    process_name = process.name()
                    process.terminate()
                    logger.info(f"Terminated process {process_name} (PID: {pid})")
                    return {'success': True, 'message': f'Process {process_name} (PID: {pid}) terminated'}
                except psutil.NoSuchProcess:
                    return {'success': False, 'message': f'Process {pid} not found'}
                except psutil.AccessDenied:
                    return {'success': False, 'message': f'Access denied to kill process {pid}'}
            
            elif action == 'restart_agent':
                logger.info("Restarting agent as requested")
                # Stop the agent gracefully; LaunchAgent/service will restart it
                threading.Thread(target=lambda: (time.sleep(1), self.stop(), exit(0)), daemon=True).start()
                return {'success': True, 'message': 'Agent restart initiated'}
            
            elif action == 'clear_dns_cache':
                import subprocess
                try:
                    # macOS DNS cache clear commands
                    subprocess.run(['sudo', '-n', 'dscacheutil', '-flushcache'], timeout=5, check=False)
                    subprocess.run(['sudo', '-n', 'killall', '-HUP', 'mDNSResponder'], timeout=5, check=False)
                    logger.info("DNS cache cleared")
                    return {'success': True, 'message': 'DNS cache cleared'}
                except Exception as e:
                    logger.warning(f"Error clearing DNS cache: {e}")
                    return {'success': False, 'message': f'Error: {str(e)}'}
            
            elif action == 'rotate_encryption_key':
                # Remote key rotation - new key is encrypted with old key
                encrypted_new_key = params.get('encrypted_new_key')
                if not encrypted_new_key:
                    return {'success': False, 'message': 'Missing encrypted_new_key parameter'}
                
                if not self.encryptor or not self.encryptor.enabled:
                    return {'success': False, 'message': 'E2EE not enabled on this agent'}
                
                try:
                    # Decrypt the new key using current key
                    decrypted_data = self.encryptor.decrypt_payload(encrypted_new_key)
                    new_key = decrypted_data.get('new_key')
                    
                    if not new_key:
                        return {'success': False, 'message': 'Invalid key rotation payload'}
                    
                    # Save new key to config
                    self._save_new_encryption_key(new_key)
                    
                    # Reinitialize encryptor with new key
                    from .encryption import DataEncryption
                    self.encryptor = DataEncryption(new_key)
                    
                    logger.info("E2EE encryption key rotated successfully")
                    return {'success': True, 'message': 'Encryption key rotated successfully'}
                    
                except Exception as e:
                    logger.error(f"Key rotation failed: {e}")
                    return {'success': False, 'message': f'Key rotation failed: {str(e)}'}
            
            else:
                return {'success': False, 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error executing command {action}: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    def _poll_commands(self):
        """Poll server for pending commands"""
        if not self.fleet_mode:
            return
        try:
            headers = {}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            response = self.session.get(
                f"{self.server_url}/api/fleet/commands/{self.machine_id}",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                commands = data.get('commands', [])
                
                for command in commands:
                    command_id = command.get('id')
                    logger.info(f"Executing command: {command.get('action')} (ID: {command_id})")
                    
                    # Execute command
                    result = self._execute_command(command)
                    
                    # Acknowledge command
                    status = 'completed' if result.get('success') else 'failed'
                    ack_payload = {
                        'id': command_id,
                        'status': status,
                        'result': result
                    }
                    
                    try:
                        ack_response = self.session.post(
                            f"{self.server_url}/api/fleet/command/{self.machine_id}/ack",
                            json=ack_payload,
                            headers=headers,
                            timeout=5
                        )
                        if ack_response.status_code == 200:
                            logger.info(f"Command {command_id} acknowledged")
                        else:
                            logger.warning(f"Failed to acknowledge command {command_id}")
                    except Exception as e:
                        logger.error(f"Error acknowledging command: {e}")
                        
        except requests.exceptions.ConnectionError:
            logger.debug("Cannot connect to server for command polling")
        except Exception as e:
            logger.error(f"Error polling commands: {e}")
    
    def _command_loop(self):
        """Command polling loop"""
        logger.info(f"Command polling loop started (interval: {self.command_poll_interval}s)")
        
        while self.running:
            try:
                self._poll_commands()
                time.sleep(self.command_poll_interval)
            except Exception as e:
                logger.error(f"Error in command loop: {e}")
                time.sleep(5)
    
    def _report_loop(self):
        """Main reporting loop with retry support"""
        logger.info(f"Agent reporting loop started (interval: {self.report_interval}s)")
        
        while self.running:
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                
                if metrics:
                    # Send to server with automatic retry on failure
                    self._send_report_with_retry(metrics, max_retries=3)
                
                # Wait for next interval
                time.sleep(self.report_interval)
                
            except Exception as e:
                logger.error(f"Error in report loop: {e}", exc_info=True)
                time.sleep(5)  # Wait a bit before retrying
    
    def _init_widget_monitors(self, widget_config):
        """Initialize widget monitors based on configuration"""
        try:
            # Import widget monitors
            from .live_widgets import (
                get_wifi_monitor,
                get_speed_test_monitor,
                get_ping_monitor,
                get_system_monitor
            )
            
            logger.info("Initializing widget monitors...")
            
            # Initialize WiFi monitor if enabled
            if widget_config.get('wifi', True):
                try:
                    wifi_monitor = get_wifi_monitor()
                    wifi_monitor.start(interval=widget_config.get('wifi_interval', 10))
                    self.widget_monitors['wifi'] = wifi_monitor
                    logger.info("WiFi monitor started")
                except Exception as e:
                    logger.error(f"Failed to start WiFi monitor: {e}")
            
            # Initialize Speed Test monitor if enabled
            if widget_config.get('speedtest', True):
                try:
                    speed_monitor = get_speed_test_monitor()
                    speed_monitor.start(interval=widget_config.get('speedtest_interval', 300))
                    self.widget_monitors['speedtest'] = speed_monitor
                    logger.info("Speed Test monitor started")
                except Exception as e:
                    logger.error(f"Failed to start Speed Test monitor: {e}")
            
            # Initialize Ping monitor if enabled
            if widget_config.get('ping', True):
                try:
                    ping_monitor = get_ping_monitor()
                    ping_monitor.start(interval=widget_config.get('ping_interval', 5))
                    self.widget_monitors['ping'] = ping_monitor
                    logger.info("Ping monitor started")
                except Exception as e:
                    logger.error(f"Failed to start Ping monitor: {e}")
            
            # Initialize System Health monitor if enabled
            if widget_config.get('health', True):
                try:
                    system_monitor = get_system_monitor()
                    system_monitor.start(interval=widget_config.get('health_interval', 2))
                    self.widget_monitors['health'] = system_monitor
                    logger.info("System Health monitor started")
                except Exception as e:
                    logger.error(f"Failed to start System Health monitor: {e}")
            
            # Initialize Widget Log Collector if logs are enabled
            if widget_config.get('enabled', True):
                try:
                    from .widget_log_collector import WidgetLogCollector
                    
                    self.widget_log_collector = WidgetLogCollector(
                        fleet_server_url=self.server_url,
                        machine_id=self.machine_id,
                        api_key=self.api_key
                    )
                    
                    # Start log collector thread
                    log_interval = widget_config.get('log_interval', 300)
                    self.widget_log_collector.start(interval=log_interval)
                    logger.info(f"Widget log collector started (interval: {log_interval}s)")
                except Exception as e:
                    logger.error(f"Failed to start widget log collector: {e}")
            
            logger.info(f"Widget monitors initialized: {list(self.widget_monitors.keys())}")
            
        except Exception as e:
            logger.error(f"Error initializing widget monitors: {e}")
    
    def start(self, interval: int = 10, widget_config: Optional[Dict] = None):
        """
        Start the agent
        
        Args:
            interval: Reporting interval in seconds
            widget_config: Widget configuration dict (optional)
        """
        if self.running:
            logger.warning("Agent is already running")
            return
        
        self.report_interval = interval
        self.running = True

        # Only start fleet reporting/command threads in fleet mode
        if self.fleet_mode:
            self.thread = threading.Thread(target=self._report_loop, daemon=True)
            self.thread.start()

            self.command_thread = threading.Thread(target=self._command_loop, daemon=True)
            self.command_thread.start()
            logger.info(f"Fleet agent started for {self.machine_id} (fleet mode)")
        else:
            logger.info(f"Fleet agent started for {self.machine_id} (standalone mode)")

        # Start widget monitors if configured
        if widget_config:
            self._init_widget_monitors(widget_config)

    
    def stop(self):
        """Stop the agent"""
        if not self.running:
            return
        
        logger.info("Stopping fleet agent...")
        self.running = False
        
        # Stop widget monitors
        for name, monitor in self.widget_monitors.items():
            try:
                if hasattr(monitor, 'stop'):
                    monitor.stop()
                    logger.info(f"Stopped {name} monitor")
            except Exception as e:
                logger.error(f"Error stopping {name} monitor: {e}")
        
        # Stop widget log collector
        if self.widget_log_collector:
            try:
                self.widget_log_collector.stop()
                logger.info("Stopped widget log collector")
            except Exception as e:
                logger.error(f"Error stopping widget log collector: {e}")
        
        if self.thread:
            self.thread.join(timeout=5)
        
        if self.command_thread:
            self.command_thread.join(timeout=5)
        
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
    
    parser = argparse.ArgumentParser(description='Atlas Fleet Agent')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--server', help='Central server URL')
    parser.add_argument('--machine-id', help='Machine identifier (default: hostname)')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--interval', type=int, help='Reporting interval in seconds')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure persistent logging with 7-day retention
    from pathlib import Path
    log_dir = Path.home() / 'Library' / 'Logs' / 'FleetAgent'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = str(log_dir / 'fleet_agent.log')
    
    from logging.handlers import TimedRotatingFileHandler
    
    # Create formatter
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler with 7-day retention (rotate daily, keep 7 backups)
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG if args.debug else logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG if args.debug else logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logger.info(f"Logging to file: {log_file} (7-day retention)")
    
    # Load configuration from file if provided
    server_url = args.server
    api_key = args.api_key
    interval = args.interval or 10
    machine_id = args.machine_id
    widget_config = None
    
    if args.config:
        try:
            # Try to load encrypted config first
            try:
                from .fleet_config_encryption import EncryptedConfigManager, ENCRYPTION_AVAILABLE
                if ENCRYPTION_AVAILABLE:
                    enc_manager = EncryptedConfigManager(args.config)
                    config = enc_manager.decrypt_config()
                    if config:
                        logger.info(f"Loaded encrypted configuration from {args.config}")
                    else:
                        # Fall back to plaintext
                        with open(args.config, 'r') as f:
                            config = json.load(f)
                        logger.info(f"Loaded plaintext configuration from {args.config}")
                else:
                    with open(args.config, 'r') as f:
                        config = json.load(f)
                    logger.info(f"Loaded plaintext configuration from {args.config}")
            except ImportError:
                # Encryption not available, use plaintext
                with open(args.config, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded plaintext configuration from {args.config}")
                
            # Load fleet server config
            fleet_config = config.get('fleet_server', {})
            server_url = server_url or fleet_config.get('url') or config.get('server_url')
            api_key = api_key or fleet_config.get('api_key') or config.get('api_key')
            
            # Load agent config
            agent_config = config.get('agent', {})
            interval = args.interval or agent_config.get('report_interval', 10)
            machine_id = machine_id or config.get('machine_id')
            
            # Load widget config
            widget_config = config.get('widgets', {})
            
            if widget_config.get('enabled'):
                    logger.info(f"Widget monitoring enabled")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return
    
    if not server_url:
        logger.error("Server URL is required (use --server or --config)")
        return
    
    # Create and start agent
    agent = FleetAgent(
        server_url=server_url,
        machine_id=machine_id,
        api_key=api_key
    )
    
    try:
        agent.start(interval=interval, widget_config=widget_config)
        
        # Keep running
        print(f"Fleet agent running for {agent.machine_id}")
        print(f"Reporting to: {server_url}")
        print(f"Interval: {interval}s")
        print("Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping agent...")
        agent.stop()
        print("Agent stopped")


if __name__ == '__main__':
    main()
