"""
Live Widget System - Real-time HTML/CSS/JavaScript widgets instead of images
Uses WebSockets for live data streaming and client-side rendering
"""
import json
import time
import threading
import logging
import sys
import fcntl
import atexit
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import hashlib
import base64
import struct
import os

from atlas.network.monitors.wifi import get_wifi_monitor
from atlas.routes.widget_routes import dispatch_get as _dispatch_widget_get
from atlas.routes.api_routes import (
    dispatch_get as _dispatch_api_get,
    dispatch_post as _dispatch_api_post,
)

# Import Phase 4 monitors (optional)
try:
    from atlas.display_monitor import get_display_monitor
    DISPLAY_MONITOR_AVAILABLE = True
except ImportError:
    DISPLAY_MONITOR_AVAILABLE = False

try:
    from atlas.power_monitor import get_power_monitor
    POWER_MONITOR_AVAILABLE = True
except ImportError:
    POWER_MONITOR_AVAILABLE = False

try:
    from atlas.peripheral_monitor import get_peripheral_monitor
    PERIPHERAL_MONITOR_AVAILABLE = True
except ImportError:
    PERIPHERAL_MONITOR_AVAILABLE = False

try:
    from atlas.security_monitor import get_security_monitor
    SECURITY_MONITOR_AVAILABLE = True
except ImportError:
    SECURITY_MONITOR_AVAILABLE = False

try:
    from atlas.disk_health_monitor import get_disk_monitor
    DISK_MONITOR_AVAILABLE = True
except ImportError:
    DISK_MONITOR_AVAILABLE = False

try:
    from atlas.software_inventory_monitor import get_software_monitor
    SOFTWARE_MONITOR_AVAILABLE = True
except ImportError:
    SOFTWARE_MONITOR_AVAILABLE = False

try:
    from atlas.application_monitor import get_app_monitor
    APP_MONITOR_AVAILABLE = True
except ImportError:
    APP_MONITOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# Singleton lock file path
LOCK_FILE_PATH = Path.home() / ".atlas-agent.lock"
_lock_file = None


def acquire_singleton_lock():
    """
    Acquire a singleton lock to prevent multiple agent instances.
    Uses file locking (flock) which is automatically released when the process exits.

    Returns:
        bool: True if lock acquired, False if another instance is running
    """
    global _lock_file

    try:
        _lock_file = open(LOCK_FILE_PATH, 'w')
        fcntl.flock(_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Write PID to lock file for debugging
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()

        # Register cleanup on exit
        atexit.register(release_singleton_lock)

        logger.info(f"Singleton lock acquired (PID: {os.getpid()})")
        return True

    except (IOError, OSError):
        # Lock is held by another process
        try:
            with open(LOCK_FILE_PATH, 'r') as f:
                other_pid = f.read().strip()
            logger.error(f"Another agent instance is already running (PID: {other_pid})")
        except (IOError, OSError, ValueError):
            logger.error("Another agent instance is already running")

        if _lock_file:
            _lock_file.close()
            _lock_file = None
        return False


def release_singleton_lock():
    """Release the singleton lock"""
    global _lock_file

    if _lock_file:
        try:
            fcntl.flock(_lock_file.fileno(), fcntl.LOCK_UN)
            _lock_file.close()
            _lock_file = None

            # Remove lock file
            if LOCK_FILE_PATH.exists():
                LOCK_FILE_PATH.unlink()

            logger.info("Singleton lock released")
        except Exception as e:
            logger.warning(f"Error releasing singleton lock: {e}")


class WebSocketHandler:
    """Simple WebSocket handler for live data streaming"""

    @staticmethod
    def compute_accept_key(key):
        """Compute WebSocket accept key"""
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        sha1 = hashlib.sha1((key + GUID).encode()).digest()
        return base64.b64encode(sha1).decode()

    @staticmethod
    def send_frame(socket, data):
        """Send WebSocket frame"""
        message = json.dumps(data).encode('utf-8')
        length = len(message)

        # Frame format: FIN + opcode (text = 1)
        frame = bytearray([0x81])

        if length <= 125:
            frame.append(length)
        elif length <= 65535:
            frame.append(126)
            frame.extend(struct.pack('>H', length))
        else:
            frame.append(127)
            frame.extend(struct.pack('>Q', length))

        frame.extend(message)

        try:
            socket.sendall(bytes(frame))
            return True
        except (OSError, BrokenPipeError, ConnectionError):
            return False


class LiveWidgetHandler(BaseHTTPRequestHandler):
    """HTTP handler for live widgets"""

    system_monitor = None
    websocket_clients = []
    _ws_lock = threading.Lock()

    # Agent health tracking
    agent_start_time = time.time()
    fleet_server_url = None
    last_fleet_report = None
    agent_version = "1.0.0"

    # E2EE encryption status
    e2ee_enabled = False
    e2ee_server_verified = False  # True if server confirmed it can decrypt our data
    last_e2ee_verification = None

    # Public paths that don't require authentication
    PUBLIC_PATHS = {'/login', '/api/health', '/favicon.ico', '/api/agent/health'}

    def log_message(self, format, *args):
        """Log requests"""
        logger.debug(f"Live widget request: {format % args}")

    def _check_auth(self) -> bool:
        """Check if request is authenticated. Returns True if allowed to proceed."""
        from atlas.dashboard_auth import get_dashboard_auth

        auth = get_dashboard_auth()
        if not auth.is_enabled():
            return True  # Auth not enabled, allow all

        path = self.path.split('?')[0]

        # Allow public paths
        if path in self.PUBLIC_PATHS:
            return True

        # Check if it's an API request and API auth is not required
        if path.startswith('/api/') and not auth.requires_auth_for_api():
            return True

        # Check session cookie
        session_token = auth.get_session_cookie_value(dict(self.headers))
        if auth.validate_session(session_token):
            return True

        # Not authenticated - redirect to login
        self.send_response(302)
        self.send_header('Location', '/login')
        self.end_headers()
        return False

    def _get_client_ip(self) -> str:
        """Get client IP address"""
        forwarded = self.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return self.client_address[0] if self.client_address else 'unknown'

    def do_GET(self):
        """Handle GET requests"""
        path = self.path.split('?')[0]
        if 'health' in path:
            logger.debug(f"do_GET: path={path}, class_e2ee={LiveWidgetHandler.e2ee_enabled}, fleet_url={LiveWidgetHandler.fleet_server_url}")

        try:
            # Handle login page (must be before auth check)
            if path == '/login':
                self._handle_login_get()
                return

            # Handle logout
            if path == '/logout':
                self._handle_logout()
                return

            # Check authentication for protected paths
            if not self._check_auth():
                return

            # Try widget/page routes first
            if _dispatch_widget_get(self, path):
                return

            # Try API routes
            if _dispatch_api_get(self, path):
                return

            self.send_error(404, "Not found")

        except Exception as e:
            logger.error(f"Error serving live widget: {e}", exc_info=True)
            self.send_error(500, str(e))

    def _handle_login_get(self):
        """Serve login page."""
        from atlas.dashboard_auth import get_dashboard_auth, get_login_page_html, IS_MACOS, AuthMode
        from atlas.security_headers import generate_csp_nonce, SecurityHeaders
        auth = get_dashboard_auth()
        if not auth.is_enabled():
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        auth_mode = auth.get_auth_mode()
        csrf_token = auth.generate_csrf_token()
        nonce = generate_csp_nonce()
        csp_headers = SecurityHeaders(use_ssl=False).get_security_headers(nonce=nonce)
        self.serve_html(get_login_page_html(
            auth_mode=auth_mode,
            touchid_available=auth.is_touchid_available(),
            local_password_available=IS_MACOS and auth_mode == AuthMode.LOCAL_PASSWORD,
            csrf_token=csrf_token,
            nonce=nonce,
        ), extra_headers=csp_headers)

    def _handle_logout(self):
        """Handle logout request."""
        from atlas.dashboard_auth import get_dashboard_auth
        auth = get_dashboard_auth()
        session_token = auth.get_session_cookie_value(dict(self.headers))
        if session_token:
            auth.logout(session_token)
        self.send_response(302)
        self.send_header('Location', '/login')
        self.send_header('Set-Cookie', 'atlas_session=; Max-Age=0; Path=/; HttpOnly')
        self.end_headers()

    # Allowed CORS origins for local widget server
    ALLOWED_ORIGINS = {'http://127.0.0.1', 'http://localhost', 'https://127.0.0.1', 'https://localhost'}

    def _get_cors_origin(self):
        """Return the request Origin if it's allowed, else None."""
        origin = self.headers.get('Origin', '')
        for allowed in self.ALLOWED_ORIGINS:
            if origin == allowed or origin.startswith(allowed + ':'):
                return origin
        return None

    def serve_html(self, html, extra_headers=None):
        """Serve HTML response with optional extra headers (e.g. CSP nonce)."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        cors_origin = self._get_cors_origin()
        if cors_origin:
            self.send_header('Access-Control-Allow-Origin', cors_origin)
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_json(self, data):
        """Serve JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        cors_origin = self._get_cors_origin()
        if cors_origin:
            self.send_header('Access-Control-Allow-Origin', cors_origin)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB

    def _read_body(self, max_size=None):
        """Read and validate request body size.

        Returns bytes or None if rejected (response already sent).
        """
        max_size = max_size or self.MAX_BODY_SIZE
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length < 0 or content_length > max_size:
            self.send_response(413 if content_length > max_size else 400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Request body too large"}')
            return None
        if content_length == 0:
            return b''
        return self.rfile.read(content_length)

    def do_POST(self):
        """Handle POST requests"""
        path = self.path.split('?')[0]

        try:
            # Handle login form submission (before auth check)
            if path == '/login':
                self._handle_login_post()
                return

            # Handle auth API endpoints (before auth check)
            if path.startswith('/api/auth/'):
                self._handle_auth_api(path)
                return

            # Check authentication for other POST requests
            if not self._check_auth():
                return

            # Try API POST routes
            if _dispatch_api_post(self, path):
                return

            self.send_error(404, "Not found")
        except Exception as e:
            logger.error(f"Error handling POST: {e}", exc_info=True)
            self.send_error(500, "Internal server error")

    def _handle_login_post(self):
        """Handle login form submission."""
        from atlas.dashboard_auth import get_dashboard_auth, get_login_page_html
        from atlas.security_headers import generate_csp_nonce, SecurityHeaders
        from urllib.parse import parse_qs

        auth = get_dashboard_auth()
        if not auth.is_enabled():
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return

        body = self._read_body()
        if body is None:
            return

        # Parse form data
        form_data = parse_qs(body.decode('utf-8'))

        # Validate CSRF token before processing authentication
        csrf_token = form_data.get('_csrf_token', [''])[0]
        if not auth.validate_csrf_token(csrf_token):
            from atlas.dashboard_auth import IS_MACOS, AuthMode
            auth_mode = auth.get_auth_mode()
            new_csrf = auth.generate_csrf_token()
            nonce = generate_csp_nonce()
            csp_headers = SecurityHeaders(use_ssl=False).get_security_headers(nonce=nonce)
            self.serve_html(get_login_page_html(
                error_message="Session expired. Please try again.",
                auth_mode=auth_mode,
                touchid_available=auth.is_touchid_available(),
                local_password_available=IS_MACOS and auth_mode == AuthMode.LOCAL_PASSWORD,
                csrf_token=new_csrf,
                nonce=nonce,
            ), extra_headers=csp_headers)
            return

        username = form_data.get('username', [''])[0]
        password = form_data.get('password', [''])[0]
        use_touchid = form_data.get('use_touchid', [''])[0] == 'true'
        use_local_password = form_data.get('use_local_password', [''])[0] == 'true'
        ip_address = self._get_client_ip()

        from atlas.dashboard_auth import IS_MACOS, AuthMode

        success, session_token, message = auth.authenticate(
            password=password if password else None,
            username=username if username else None,
            ip_address=ip_address,
            use_touchid=use_touchid,
            use_local_password=use_local_password
        )

        if success:
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', f'atlas_session={session_token}; Path=/; HttpOnly; SameSite=Strict')
            self.end_headers()
        else:
            auth_mode = auth.get_auth_mode()
            new_csrf = auth.generate_csrf_token()
            nonce = generate_csp_nonce()
            csp_headers = SecurityHeaders(use_ssl=False).get_security_headers(nonce=nonce)
            self.serve_html(get_login_page_html(
                error_message=message,
                auth_mode=auth_mode,
                touchid_available=auth.is_touchid_available(),
                local_password_available=IS_MACOS and auth_mode == AuthMode.LOCAL_PASSWORD,
                csrf_token=new_csrf,
                nonce=nonce,
            ), extra_headers=csp_headers)

    def _handle_auth_api(self, path):
        """Handle /api/auth/* POST endpoints."""
        if path == '/api/auth/status':
            from atlas.dashboard_auth import get_dashboard_auth, IS_MACOS, AuthMode
            auth = get_dashboard_auth()
            session_token = auth.get_session_cookie_value(dict(self.headers))
            auth_mode = auth.get_auth_mode()
            self.serve_json({
                'auth_enabled': auth.is_enabled(),
                'authenticated': auth.validate_session(session_token) if auth.is_enabled() else True,
                'auth_mode': auth_mode,
                'touchid_available': auth.is_touchid_available(),
                'local_password_available': IS_MACOS and auth_mode == AuthMode.LOCAL_PASSWORD,
            })

        elif path == '/api/auth/set-password':
            from atlas.dashboard_auth import get_dashboard_auth
            auth = get_dashboard_auth()
            body = self._read_body()
            if body is None:
                return
            data = json.loads(body.decode('utf-8'))
            new_password = data.get('password')
            if not new_password or len(new_password) < 8:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Password must be at least 8 characters'}).encode())
                return
            if auth.set_password(new_password):
                self.serve_json({'status': 'success', 'message': 'Password set successfully'})
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to set password'}).encode())

        elif path == '/api/auth/disable':
            from atlas.dashboard_auth import get_dashboard_auth
            auth = get_dashboard_auth()
            session_token = auth.get_session_cookie_value(dict(self.headers))
            if auth.is_enabled() and not auth.validate_session(session_token):
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Not authenticated'}).encode())
                return
            if auth.disable_auth():
                self.serve_json({'status': 'success', 'message': 'Authentication disabled'})
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to disable authentication'}).encode())

        elif path == '/api/auth/configure':
            from atlas.dashboard_auth import get_dashboard_auth, AuthMode
            auth = get_dashboard_auth()
            body = self._read_body()
            if body is None:
                return
            data = json.loads(body.decode('utf-8'))
            auth_mode = data.get('auth_mode')
            password = data.get('password')
            allow_touchid = data.get('allow_touchid', True)
            valid_modes = [AuthMode.SIMPLE, AuthMode.USERS, AuthMode.TOUCHID, AuthMode.HYBRID]
            if auth_mode not in valid_modes:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': f'Invalid auth_mode. Must be one of: {valid_modes}'
                }).encode())
                return
            if auth_mode == AuthMode.SIMPLE and not password:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Password required for simple mode'}).encode())
                return
            try:
                config = {
                    'enabled': True,
                    'auth_mode': auth_mode,
                    'allow_touchid': allow_touchid,
                }
                if auth_mode == AuthMode.SIMPLE and password:
                    config['password_hash'] = auth._hash_password(password)
                auth.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(auth.CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=2)
                auth._config = auth._load_config()
                self.serve_json({
                    'status': 'success',
                    'message': f'Authentication configured with mode: {auth_mode}',
                    'auth_mode': auth_mode,
                    'touchid_available': auth.is_touchid_available()
                })
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

        else:
            self.send_error(404, "Not found")

    def handle_websocket(self):
        """Handle WebSocket upgrade"""
        if 'Upgrade' not in self.headers or self.headers['Upgrade'].lower() != 'websocket':
            self.send_error(400, "Not a WebSocket request")
            return

        key = self.headers.get('Sec-WebSocket-Key')
        if not key:
            self.send_error(400, "Missing WebSocket key")
            return

        # Send upgrade response
        accept_key = WebSocketHandler.compute_accept_key(key)
        self.send_response(101)
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        self.send_header('Sec-WebSocket-Accept', accept_key)
        self.end_headers()

        # Add client to list
        with self._ws_lock:
            self.websocket_clients.append(self.connection)
            client_count = len(self.websocket_clients)
        logger.info(f"WebSocket client connected. Total: {client_count}")

        # Keep connection alive
        try:
            while True:
                time.sleep(0.1)
        except (KeyboardInterrupt, ConnectionError, BrokenPipeError):
            pass
        finally:
            with self._ws_lock:
                if self.connection in self.websocket_clients:
                    self.websocket_clients.remove(self.connection)
                client_count = len(self.websocket_clients)
            logger.info(f"WebSocket client disconnected. Total: {client_count}")

    def get_current_stats(self):
        """Get current system stats"""
        if self.system_monitor:
            stats = self.system_monitor.get_all_stats()
            cpu = stats.get('cpu', 0) * 100 if stats.get('cpu', 0) < 1 else stats.get('cpu', 0)
            memory = stats.get('memory', 0) * 100 if stats.get('memory', 0) < 1 else stats.get('memory', 0)
            disk = stats.get('disks', {}).get('/', 0) * 100 if stats.get('disks', {}).get('/', 0) < 1 else stats.get('disks', {}).get('/', 0)
            gpu = stats.get('gpu', 0) * 100 if stats.get('gpu', 0) < 1 else stats.get('gpu', 0)

            network = stats.get('network', {})
            network_up = network.get('upload', network.get('up', 0)) / 1024.0
            network_down = network.get('download', network.get('down', 0)) / 1024.0

            battery_info = stats.get('battery')
            if isinstance(battery_info, dict):
                battery_percent = battery_info.get('percent', 0)
            else:
                battery_percent = 0

            return {
                'cpu': round(cpu, 1),
                'gpu': round(gpu, 1),
                'memory': round(memory, 1),
                'disk': round(disk, 1),
                'network_up': round(network_up, 1),
                'network_down': round(network_down, 1),
                'battery': battery_percent,
                'temperature': stats.get('temperatures', {}).get('cpu', 0),
                'timestamp': time.time()
            }
        return {
            'cpu': 45.0, 'gpu': 30.0, 'memory': 65.0, 'disk': 55.0,
            'network_up': 10.5, 'network_down': 125.3,
            'battery': 85, 'temperature': 45, 'timestamp': time.time()
        }


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling multiple connections"""
    daemon_threads = True


def get_speed_test_monitor():
    """Get or create speed test monitor instance"""
    from atlas.network.monitors.speedtest import get_speed_test_monitor as _get_monitor
    return _get_monitor()

def get_ping_monitor():
    """Get or create ping monitor instance"""
    from atlas.network.monitors.ping import PingMonitor
    if not hasattr(get_ping_monitor, '_instance'):
        get_ping_monitor._instance = PingMonitor()
    return get_ping_monitor._instance

def start_live_widget_server(port=8767, system_monitor=None, fleet_server=None, machine_id=None, api_key=None, encryption_key=None):
    """
    Start the live widget server

    Args:
        port: Port to listen on
        system_monitor: System monitor instance
        fleet_server: Fleet server URL for log collection
        machine_id: Machine ID for log collection
        api_key: API key for fleet server authentication
        encryption_key: Optional encryption key for end-to-end encryption

    Returns:
        threading.Thread: Server thread

    Note:
        This function assumes the singleton lock has already been acquired.
        When called from __main__, the lock is acquired before this function.
        When called programmatically, call acquire_singleton_lock() first.
    """
    # Ensure osx-cpu-temp is installed for CPU temperature monitoring
    try:
        from atlas.power_monitor import ensure_osx_cpu_temp_installed
        ensure_osx_cpu_temp_installed()
    except Exception as e:
        logger.warning(f"Could not check/install osx-cpu-temp: {e}")

    LiveWidgetHandler.system_monitor = system_monitor
    LiveWidgetHandler.fleet_server_url = fleet_server
    LiveWidgetHandler.agent_start_time = time.time()
    LiveWidgetHandler.e2ee_enabled = bool(encryption_key)
    LiveWidgetHandler.e2ee_server_verified = bool(encryption_key)  # If we have a key, assume verified
    logger.info(f"E2EE status set: enabled={LiveWidgetHandler.e2ee_enabled}, verified={LiveWidgetHandler.e2ee_server_verified}")

    # Initialize Fleet Agent if fleet server is provided
    fleet_agent = None
    if fleet_server and machine_id:
        from atlas.fleet_agent import FleetAgent
        from atlas.widget_log_collector import init_log_collector, log_widget_event

        # Start Fleet Agent (reports metrics every 10 seconds)
        fleet_agent = FleetAgent(
            server_url=fleet_server,
            machine_id=machine_id,
            api_key=api_key,
            encryption_key=encryption_key
        )
        fleet_agent.start()
        e2ee_status = "with E2EE" if encryption_key else "without E2EE"
        logger.info(f"Fleet agent started {e2ee_status} (reports every 10 seconds to {fleet_server})")

        # Store reference for E2EE verification updates
        LiveWidgetHandler.fleet_agent = fleet_agent

        # Start widget log collector (sends logs every 5 minutes)
        log_collector = init_log_collector(machine_id, fleet_server, api_key, interval=300, encryption_key=encryption_key)
        logger.info(f"Widget log collector initialized (sends every 5 minutes to {fleet_server})")

        # Log startup
        log_widget_event('INFO', 'system', 'Live widget server starting', {
            'port': port,
            'machine_id': machine_id
        })

    # Start speed test monitor (runs every 60 seconds)
    speed_monitor = get_speed_test_monitor()
    speed_monitor.start(interval=60)
    logger.info("Speed test monitor started (interval: 60s)")

    # Start ping monitor (runs every 10 seconds to reduce kernel stress)
    ping_monitor = get_ping_monitor()
    ping_monitor.start(interval=10)
    logger.info("Ping monitor started (interval: 10s)")

    # Start WiFi monitor (runs every 60 seconds to reduce kernel stress)
    wifi_monitor = get_wifi_monitor()
    wifi_monitor.start(interval=60)
    logger.info(f"WiFi monitor started (interval: 60s), id={id(wifi_monitor)}")

    # Start WiFi roaming tracker
    try:
        from atlas.wifi_roaming import get_wifi_roaming_tracker
        roaming_tracker = get_wifi_roaming_tracker()
        roaming_tracker.start()
        logger.info("WiFi roaming tracker started (interval: 60s)")
    except Exception as e:
        logger.error(f"Failed to start WiFi roaming tracker: {e}")

    # Start Phase 4 monitors
    if POWER_MONITOR_AVAILABLE:
        try:
            power_monitor = get_power_monitor()
            power_monitor.start()
            logger.info("Power monitor started")
        except Exception as e:
            logger.error(f"Failed to start power monitor: {e}")

    # Note: Display monitor collects data on-demand and doesn't need to be started
    if DISPLAY_MONITOR_AVAILABLE:
        logger.info("Display monitor available (on-demand collection)")

    if PERIPHERAL_MONITOR_AVAILABLE:
        try:
            peripheral_monitor = get_peripheral_monitor()
            peripheral_monitor.start()
            logger.info("Peripheral monitor started")
        except Exception as e:
            logger.error(f"Failed to start peripheral monitor: {e}")

    if SECURITY_MONITOR_AVAILABLE:
        try:
            security_monitor = get_security_monitor()
            security_monitor.start()
            logger.info("Security monitor started")
        except Exception as e:
            logger.error(f"Failed to start security monitor: {e}")

    if DISK_MONITOR_AVAILABLE:
        try:
            disk_monitor = get_disk_monitor()
            disk_monitor.start()
            logger.info("Disk health monitor started")
        except Exception as e:
            logger.error(f"Failed to start disk monitor: {e}")

    if SOFTWARE_MONITOR_AVAILABLE:
        try:
            software_monitor = get_software_monitor()
            software_monitor.start()
            logger.info("Software inventory monitor started")
        except Exception as e:
            logger.error(f"Failed to start software monitor: {e}")

    if APP_MONITOR_AVAILABLE:
        try:
            app_monitor = get_app_monitor()
            app_monitor.start()
            logger.info("Application monitor started")
        except Exception as e:
            logger.error(f"Failed to start application monitor: {e}")

    try:
        from atlas.network.monitors.osi_diagnostic_monitor import get_osi_diagnostic_monitor
        osi_monitor = get_osi_diagnostic_monitor()
        osi_monitor.start(interval=300)
        logger.info("OSI Diagnostic monitor started (interval: 300s)")
    except Exception as e:
        logger.error(f"Failed to start OSI Diagnostic monitor: {e}")

    # Capture e2ee settings for the thread
    _e2ee_enabled = bool(encryption_key)
    _e2ee_verified = bool(encryption_key)

    def run_server():
        # Set E2EE status on the class right before server starts
        LiveWidgetHandler.e2ee_enabled = _e2ee_enabled
        LiveWidgetHandler.e2ee_server_verified = _e2ee_verified
        logger.info(f"HTTP thread: E2EE set to enabled={_e2ee_enabled}, verified={_e2ee_verified}")
        server = ThreadedHTTPServer(('0.0.0.0', port), LiveWidgetHandler)
        logger.info(f"Live widget server started at http://0.0.0.0:{port}")
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f"Live widget server error: {e}")

    # Start data broadcaster thread
    def broadcast_data():
        """Broadcast data to all WebSocket clients"""
        while True:
            time.sleep(1)
            if LiveWidgetHandler.websocket_clients:
                stats = LiveWidgetHandler.system_monitor.get_all_stats() if LiveWidgetHandler.system_monitor else {}
                data = {
                    'cpu': stats.get('cpu', 0) * 100,
                    'gpu': stats.get('gpu', 0) * 100,
                    'memory': stats.get('memory', 0) * 100,
                    'timestamp': time.time()
                }

                # Send to all connected clients
                with LiveWidgetHandler._ws_lock:
                    clients = LiveWidgetHandler.websocket_clients[:]
                failed = []
                for client in clients:
                    if not WebSocketHandler.send_frame(client, data):
                        failed.append(client)
                if failed:
                    with LiveWidgetHandler._ws_lock:
                        for client in failed:
                            if client in LiveWidgetHandler.websocket_clients:
                                LiveWidgetHandler.websocket_clients.remove(client)

    threading.Thread(target=broadcast_data, daemon=True).start()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    import argparse
    import socket

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Live Widget Server with Fleet Integration')
    parser.add_argument('--port', type=int, default=8767, help='Port to listen on (default: 8767)')
    parser.add_argument('--fleet-server', type=str, help='Fleet server URL for log collection (e.g., http://localhost:8778)')
    parser.add_argument('--machine-id', type=str, help='Machine ID for fleet reporting (default: hostname)')
    parser.add_argument('--api-key', type=str, help='API key for fleet server authentication')
    parser.add_argument('--encryption-key', type=str, help='Encryption key for end-to-end encryption (base64)')

    args = parser.parse_args()

    # Check singleton lock FIRST before any other initialization
    if not acquire_singleton_lock():
        logger.error("Another ATLAS agent instance is already running on this machine.")
        logger.error("Kill the existing process or wait for it to exit.")
        sys.exit(1)

    # Get machine ID
    machine_id = args.machine_id or socket.gethostname().split('.')[0]

    logger.info(f"Starting live widget server on http://0.0.0.0:{args.port}")
    logger.info(f"Access locally: http://localhost:{args.port}")

    if args.fleet_server:
        logger.info("Fleet integration enabled:")
        logger.info(f"  Server: {args.fleet_server}")
        logger.info(f"  Machine ID: {machine_id}")
        logger.info("  Log interval: 5 minutes")
        if args.encryption_key:
            logger.info("  Encryption: ENABLED (AES-256-GCM)")
        else:
            logger.info("  Encryption: DISABLED")

    start_live_widget_server(
        port=args.port,
        fleet_server=args.fleet_server,
        machine_id=machine_id,
        api_key=args.api_key,
        encryption_key=args.encryption_key
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
