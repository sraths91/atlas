"""
Dashboard Authentication for Standalone Mode

Provides optional password protection for the ATLAS dashboard when running locally.
Supports multiple authentication methods:
- Simple password protection
- Username/password login (using fleet user management)
- TouchID/biometric authentication on macOS
- Local macOS user password authentication (system login password)

Features:
- Password protection with bcrypt hashing
- Session cookies with configurable timeout
- Login page with rate limiting
- TouchID support on macOS
- Local macOS password authentication (uses LocalAuthentication framework)
- Integration with fleet user management
- Configurable via environment variables or config file

Usage:
    # Enable via environment variable (simple password mode)
    export ATLAS_DASHBOARD_PASSWORD="your-secure-password"

    # Or enable user-based auth (uses fleet_user_manager)
    export ATLAS_DASHBOARD_AUTH_MODE="users"

    # Or enable local macOS user password auth
    export ATLAS_DASHBOARD_AUTH_MODE="local"

    # Or via config file (~/.config/atlas-agent/dashboard_auth.json)
    {
        "enabled": true,
        "auth_mode": "local",  // "simple", "users", "touchid", "hybrid", or "local"
        "password_hash": "<bcrypt hash>",  // for simple mode only
        "session_timeout_hours": 24,
        "require_auth_for_api": false,
        "allow_touchid": true
    }
"""

import os
import json
import time
import logging
import secrets
import hashlib
import threading
import subprocess
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
from http.cookies import SimpleCookie

logger = logging.getLogger(__name__)

# Try to import bcrypt, fall back to hashlib if not available
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not available, using SHA-256 for password hashing (less secure)")

# Check if we're on macOS for TouchID support
IS_MACOS = platform.system() == 'Darwin'


def check_touchid_available() -> bool:
    """Check if TouchID is available on this system"""
    if not IS_MACOS:
        return False

    try:
        # Check if the device supports biometric authentication
        result = subprocess.run(
            ['bioutil', '-r'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return 'Touch ID' in result.stdout or result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # Fallback: assume TouchID might be available on modern Macs
        try:
            # Check for T2/Apple Silicon chip which typically has TouchID
            result = subprocess.run(
                ['system_profiler', 'SPiBridgeDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'T2' in result.stdout or 'Apple' in result.stdout
        except Exception:
            return False


def authenticate_with_touchid(reason: str = "authenticate to ATLAS Dashboard") -> Tuple[bool, str]:
    """
    Authenticate using TouchID on macOS.

    Returns:
        Tuple of (success, message)
    """
    if not IS_MACOS:
        return False, "TouchID is only available on macOS"

    try:
        # Use AppleScript to trigger TouchID authentication
        # This uses the LocalAuthentication framework indirectly
        # Policy 1 = LAPolicyDeviceOwnerAuthenticationWithBiometrics (TouchID only)
        script = f'''
        use framework "LocalAuthentication"
        use scripting additions

        set authContext to current application's LAContext's alloc()'s init()
        set authReason to "{reason}"

        set {{authResult, authError}} to authContext's canEvaluatePolicy:1 |error|:(reference)

        if authResult then
            set {{evalResult, evalError}} to authContext's evaluatePolicy:1 localizedReason:authReason |reply|:(missing value) |error|:(reference)
            if evalResult then
                return "success"
            else
                return "failed"
            end if
        else
            return "unavailable"
        end if
        '''

        result = subprocess.run(
            ['osascript', '-l', 'AppleScript', '-e', script],
            capture_output=True,
            text=True,
            timeout=60  # Give user time to authenticate
        )

        output = result.stdout.strip()
        if output == 'success':
            logger.info("TouchID authentication successful")
            return True, "TouchID authentication successful"
        elif output == 'unavailable':
            return False, "TouchID not available on this device"
        else:
            return False, "TouchID authentication failed or cancelled"

    except subprocess.TimeoutExpired:
        return False, "TouchID authentication timed out"
    except Exception as e:
        logger.error(f"TouchID error: {e}")
        return False, f"TouchID error: {str(e)}"


def _pam_authenticate(username: str, password: str) -> bool:
    """
    Authenticate using PAM via ctypes. Password never appears in process args.
    Uses the 'chkpasswd' PAM service on macOS (which invokes pam_opendirectory).
    """
    import ctypes
    import ctypes.util

    pam_lib_path = ctypes.util.find_library('pam')
    if not pam_lib_path:
        raise OSError("PAM library not found")

    libpam = ctypes.CDLL(pam_lib_path)
    libc = ctypes.CDLL(ctypes.util.find_library('c'))

    # Set proper argtypes/restypes for libc
    libc.calloc.restype = ctypes.c_void_p
    libc.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]

    PAM_SUCCESS = 0
    PAM_PROMPT_ECHO_OFF = 1

    class PamMessage(ctypes.Structure):
        _fields_ = [
            ("msg_style", ctypes.c_int),
            ("msg", ctypes.c_char_p),
        ]

    class PamResponse(ctypes.Structure):
        _fields_ = [
            ("resp", ctypes.c_char_p),
            ("resp_retcode", ctypes.c_int),
        ]

    CONV_FUNC = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.POINTER(PamMessage)),
        ctypes.POINTER(ctypes.POINTER(PamResponse)),
        ctypes.c_void_p,
    )

    class PamConv(ctypes.Structure):
        _fields_ = [
            ("conv", CONV_FUNC),
            ("appdata_ptr", ctypes.c_void_p),
        ]

    # Set proper argtypes/restypes for PAM functions
    libpam.pam_start.restype = ctypes.c_int
    libpam.pam_start.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p,
        ctypes.POINTER(PamConv), ctypes.POINTER(ctypes.c_void_p),
    ]
    libpam.pam_authenticate.restype = ctypes.c_int
    libpam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
    libpam.pam_end.restype = ctypes.c_int
    libpam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]

    password_bytes = password.encode('utf-8')

    @CONV_FUNC
    def _conv_callback(num_msg, msg, resp, appdata_ptr):
        resp_array_ptr = libc.calloc(num_msg, ctypes.sizeof(PamResponse))
        resp_array = ctypes.cast(resp_array_ptr, ctypes.POINTER(PamResponse))
        for i in range(num_msg):
            if msg[i].contents.msg_style == PAM_PROMPT_ECHO_OFF:
                pw_buf = libc.calloc(1, len(password_bytes) + 1)
                ctypes.memmove(pw_buf, password_bytes, len(password_bytes))
                resp_array[i].resp = ctypes.cast(pw_buf, ctypes.c_char_p)
                resp_array[i].resp_retcode = 0
        resp[0] = resp_array
        return PAM_SUCCESS

    conv = PamConv()
    conv.conv = _conv_callback
    conv.appdata_ptr = None

    handle = ctypes.c_void_p()
    ret = libpam.pam_start(
        b'chkpasswd',
        username.encode('utf-8'),
        ctypes.byref(conv),
        ctypes.byref(handle),
    )
    if ret != PAM_SUCCESS:
        return False

    ret = libpam.pam_authenticate(handle, 0)
    libpam.pam_end(handle, ret)
    return ret == PAM_SUCCESS


def authenticate_with_local_password(username: str = None, password: str = None) -> Tuple[bool, str]:
    """
    Authenticate using the local macOS user password.

    Uses PAM for secure password verification (password never in process args).
    Falls back to dscl if PAM is unavailable.

    Args:
        username: macOS username (defaults to current user)
        password: The user's macOS login password

    Returns:
        Tuple of (success, message)
    """
    if not IS_MACOS:
        return False, "Local password authentication is only available on macOS"

    if not password:
        return False, "Password is required"

    if not username:
        username = get_current_macos_user()

    try:
        # Use PAM - password stays in process memory, never in CLI args
        success = _pam_authenticate(username, password)
        if success:
            logger.info(f"Local password authentication successful for user: {username}")
            return True, "Authentication successful"
        else:
            logger.warning(f"Local password authentication failed for user: {username}")
            return False, "Invalid macOS password"

    except OSError as e:
        # PAM unavailable, fall back to dscl with warning
        logger.warning(f"PAM unavailable ({e}), falling back to dscl")
        try:
            result = subprocess.run(
                ['dscl', '.', '-authonly', username, password],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info(f"Local password authentication successful for user: {username}")
                return True, "Authentication successful"
            else:
                logger.warning(f"Local password authentication failed for user: {username}")
                return False, "Invalid macOS password"
        except subprocess.TimeoutExpired:
            return False, "Authentication timed out"

    except Exception as e:
        logger.error(f"Local password auth error: {e}")
        return False, f"Authentication error: {str(e)}"


def get_current_macos_user() -> str:
    """Get the current macOS username"""
    if not IS_MACOS:
        return "unknown"
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return "user"


class AuthMode:
    """Authentication mode constants"""
    SIMPLE = "simple"           # Single password (original mode)
    USERS = "users"             # Username/password from fleet_user_manager
    TOUCHID = "touchid"         # TouchID only
    HYBRID = "hybrid"           # Username/password + optional TouchID
    LOCAL_PASSWORD = "local"    # macOS local user password (uses LAPolicy 2)


class DashboardAuth:
    """
    Authentication for the standalone dashboard.

    Supports multiple authentication modes:
    - simple: Single password protection
    - users: Username/password using fleet_user_manager
    - touchid: TouchID only (macOS)
    - hybrid: Username/password with optional TouchID
    """

    CONFIG_PATH = Path.home() / ".config" / "atlas-agent" / "dashboard_auth.json"
    DEFAULT_SESSION_TIMEOUT = 24  # hours
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 300  # seconds (5 minutes)

    CSRF_TOKEN_EXPIRY = 600  # 10 minutes

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, dict] = {}
        self._failed_attempts: Dict[str, list] = {}  # ip -> [timestamps]
        self._csrf_tokens: Dict[str, float] = {}  # token -> expiry timestamp
        self._touchid_available = check_touchid_available()
        self._config = self._load_config()
        self._user_manager = None  # Lazy load

    def generate_csrf_token(self) -> str:
        """Generate a single-use CSRF token with expiry."""
        token = secrets.token_urlsafe(32)
        expiry = time.time() + self.CSRF_TOKEN_EXPIRY
        with self._lock:
            # Prune expired tokens
            now = time.time()
            self._csrf_tokens = {
                t: exp for t, exp in self._csrf_tokens.items() if exp > now
            }
            self._csrf_tokens[token] = expiry
        return token

    def validate_csrf_token(self, token: str) -> bool:
        """Validate and consume a single-use CSRF token."""
        if not token:
            return False
        with self._lock:
            expiry = self._csrf_tokens.pop(token, None)
            if expiry is None:
                return False
            return time.time() < expiry

    def _get_user_manager(self):
        """Lazy load the fleet user manager"""
        if self._user_manager is None:
            try:
                from atlas.fleet_user_manager import FleetUserManager
                self._user_manager = FleetUserManager()
            except ImportError:
                logger.warning("FleetUserManager not available for user-based auth")
        return self._user_manager

    def _load_config(self) -> dict:
        """Load configuration from file or environment"""
        config = {
            'enabled': False,
            'auth_mode': AuthMode.SIMPLE,
            'password_hash': None,
            'session_timeout_hours': self.DEFAULT_SESSION_TIMEOUT,
            'require_auth_for_api': False,
            'allow_touchid': True,  # Allow TouchID as alternative in hybrid mode
        }

        # Check environment variables first
        env_password = os.environ.get('ATLAS_DASHBOARD_PASSWORD')
        env_auth_mode = os.environ.get('ATLAS_DASHBOARD_AUTH_MODE')

        if env_auth_mode:
            config['enabled'] = True
            config['auth_mode'] = env_auth_mode
            if env_auth_mode == AuthMode.SIMPLE and env_password:
                config['password_hash'] = self._hash_password(env_password)
            logger.info(f"Dashboard authentication enabled via environment (mode: {env_auth_mode})")
            return config

        if env_password:
            config['enabled'] = True
            config['auth_mode'] = AuthMode.SIMPLE
            config['password_hash'] = self._hash_password(env_password)
            logger.info("Dashboard authentication enabled via environment variable")
            return config

        # Check config file
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH) as f:
                    file_config = json.load(f)
                    config.update(file_config)
                    if config.get('enabled'):
                        logger.info(f"Dashboard authentication enabled via config (mode: {config.get('auth_mode')})")
                        return config
            except Exception as e:
                logger.warning(f"Failed to load auth config: {e}")

        # Auto-enable macOS local password auth when no config exists
        # Agent-only users authenticate with their Mac login — no separate account needed
        if not config.get('enabled') and IS_MACOS:
            config['enabled'] = True
            config['auth_mode'] = AuthMode.LOCAL_PASSWORD
            logger.info("Auto-enabled macOS local password authentication (no config found)")

        return config

    def get_auth_mode(self) -> str:
        """Get current authentication mode"""
        return self._config.get('auth_mode', AuthMode.SIMPLE)

    def is_touchid_available(self) -> bool:
        """Check if TouchID is available"""
        return self._touchid_available and self._config.get('allow_touchid', True)

    def _hash_password(self, password: str) -> str:
        """Hash a password"""
        if BCRYPT_AVAILABLE:
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        else:
            # Fallback to SHA-256 with salt
            salt = secrets.token_hex(16)
            hash_val = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
            return f"sha256:{salt}:{hash_val}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        if BCRYPT_AVAILABLE and not password_hash.startswith('sha256:'):
            try:
                return bcrypt.checkpw(password.encode(), password_hash.encode())
            except Exception:
                return False
        elif password_hash.startswith('sha256:'):
            # SHA-256 fallback
            parts = password_hash.split(':')
            if len(parts) != 3:
                return False
            _, salt, stored_hash = parts
            computed_hash = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
            return secrets.compare_digest(computed_hash, stored_hash)
        return False

    def is_enabled(self) -> bool:
        """Check if authentication is enabled"""
        if not self._config.get('enabled', False):
            return False
        auth_mode = self.get_auth_mode()
        # Local password and TouchID modes don't need a password_hash
        if auth_mode in (AuthMode.LOCAL_PASSWORD, AuthMode.TOUCHID):
            return True
        return self._config.get('password_hash') is not None

    def requires_auth_for_api(self) -> bool:
        """Check if API endpoints require authentication"""
        return self._config.get('require_auth_for_api', False)

    def is_locked_out(self, ip_address: str) -> Tuple[bool, int]:
        """Check if an IP is locked out due to failed attempts"""
        with self._lock:
            attempts = self._failed_attempts.get(ip_address, [])
            # Clean old attempts
            cutoff = time.time() - self.LOCKOUT_DURATION
            attempts = [t for t in attempts if t > cutoff]
            self._failed_attempts[ip_address] = attempts

            if len(attempts) >= self.MAX_FAILED_ATTEMPTS:
                remaining = int(self.LOCKOUT_DURATION - (time.time() - attempts[0]))
                return True, max(0, remaining)
            return False, 0

    def record_failed_attempt(self, ip_address: str):
        """Record a failed login attempt"""
        with self._lock:
            if ip_address not in self._failed_attempts:
                self._failed_attempts[ip_address] = []
            self._failed_attempts[ip_address].append(time.time())

    def clear_failed_attempts(self, ip_address: str):
        """Clear failed attempts after successful login"""
        with self._lock:
            self._failed_attempts.pop(ip_address, None)

    def authenticate(
        self,
        password: str = None,
        username: str = None,
        ip_address: str = None,
        use_touchid: bool = False,
        use_local_password: bool = False
    ) -> Tuple[bool, Optional[str], str]:
        """
        Authenticate using the configured method.

        Args:
            password: Password for simple or user-based auth
            username: Username for user-based auth
            ip_address: Client IP for rate limiting
            use_touchid: Use TouchID authentication
            use_local_password: Use macOS local user password authentication

        Returns:
            Tuple of (success, session_token, message)
        """
        if not self.is_enabled():
            return False, None, "Authentication not enabled"

        # Check lockout
        if ip_address:
            locked, remaining = self.is_locked_out(ip_address)
            if locked:
                return False, None, f"Too many failed attempts. Try again in {remaining} seconds."

        auth_mode = self.get_auth_mode()
        success = False
        message = "Authentication failed"
        authenticated_user = None

        # Local password authentication (macOS system password)
        if use_local_password or (auth_mode == AuthMode.LOCAL_PASSWORD and not use_touchid):
            if not IS_MACOS:
                return False, None, "Local password authentication is only available on macOS"
            if not password:
                return False, None, "Password is required"
            local_username = username if username else get_current_macos_user()
            success, message = authenticate_with_local_password(username=local_username, password=password)
            if success:
                authenticated_user = local_username

        # TouchID authentication
        elif use_touchid and self.is_touchid_available():
            success, message = authenticate_with_touchid()
            if success:
                authenticated_user = "touchid_user"
        elif use_touchid:
            return False, None, "TouchID not available on this device"

        # Simple password mode
        elif auth_mode == AuthMode.SIMPLE:
            if password and self._config.get('password_hash'):
                if self._verify_password(password, self._config['password_hash']):
                    success = True
                    message = "Login successful"
                    authenticated_user = "admin"
                else:
                    message = "Invalid password"

        # User-based authentication (username/password)
        elif auth_mode in (AuthMode.USERS, AuthMode.HYBRID):
            if username and password:
                user_manager = self._get_user_manager()
                if user_manager:
                    user_info = user_manager.verify_password(username, password, ip_address)
                    if user_info:
                        success = True
                        message = "Login successful"
                        authenticated_user = user_info.get('username')
                    else:
                        message = "Invalid username or password"
                else:
                    message = "User authentication not available"
            else:
                message = "Username and password required"

        # TouchID-only mode
        elif auth_mode == AuthMode.TOUCHID:
            if not use_touchid:
                return False, None, "TouchID authentication required"

        # Create session on success
        if success:
            session_token = secrets.token_urlsafe(32)
            timeout_hours = self._config.get('session_timeout_hours', self.DEFAULT_SESSION_TIMEOUT)

            with self._lock:
                self._sessions[session_token] = {
                    'created_at': datetime.now(),
                    'expires_at': datetime.now() + timedelta(hours=timeout_hours),
                    'ip_address': ip_address,
                    'username': authenticated_user,
                    'auth_method': 'touchid' if use_touchid else auth_mode,
                }

            if ip_address:
                self.clear_failed_attempts(ip_address)

            logger.info(f"Successful dashboard login from {ip_address} (user: {authenticated_user})")
            return True, session_token, message
        else:
            if ip_address:
                self.record_failed_attempt(ip_address)
            logger.warning(f"Failed dashboard login attempt from {ip_address}")
            return False, None, message

    def authenticate_simple(self, password: str, ip_address: str = None) -> Tuple[bool, Optional[str], str]:
        """Authenticate with simple password (backwards compatible)"""
        return self.authenticate(password=password, ip_address=ip_address)

    def validate_session(self, session_token: str) -> bool:
        """Validate a session token"""
        if not session_token:
            return False

        with self._lock:
            session = self._sessions.get(session_token)
            if not session:
                return False

            if datetime.now() > session['expires_at']:
                del self._sessions[session_token]
                return False

            return True

    def logout(self, session_token: str) -> bool:
        """Invalidate a session"""
        with self._lock:
            if session_token in self._sessions:
                del self._sessions[session_token]
                return True
            return False

    def get_session_cookie_value(self, headers: dict) -> Optional[str]:
        """Extract session token from Cookie header"""
        cookie_header = headers.get('Cookie', '')
        if not cookie_header:
            return None

        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
            if 'atlas_session' in cookie:
                return cookie['atlas_session'].value
        except Exception:
            pass
        return None

    def set_password(self, new_password: str) -> bool:
        """Set or update the dashboard password"""
        try:
            self._config['enabled'] = True
            self._config['password_hash'] = self._hash_password(new_password)

            # Save to config file
            self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_PATH, 'w') as f:
                # Don't save the hash in plaintext if it came from env
                save_config = {
                    'enabled': self._config['enabled'],
                    'password_hash': self._config['password_hash'],
                    'session_timeout_hours': self._config.get('session_timeout_hours', self.DEFAULT_SESSION_TIMEOUT),
                    'require_auth_for_api': self._config.get('require_auth_for_api', False),
                }
                json.dump(save_config, f, indent=2)

            logger.info("Dashboard password updated")
            return True
        except Exception as e:
            logger.error(f"Failed to set password: {e}")
            return False

    def disable_auth(self) -> bool:
        """Disable authentication"""
        try:
            self._config['enabled'] = False
            self._sessions.clear()

            if self.CONFIG_PATH.exists():
                with open(self.CONFIG_PATH, 'w') as f:
                    json.dump({'enabled': False}, f, indent=2)

            logger.info("Dashboard authentication disabled")
            return True
        except Exception as e:
            logger.error(f"Failed to disable auth: {e}")
            return False

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        with self._lock:
            now = datetime.now()
            expired = [k for k, v in self._sessions.items() if now > v['expires_at']]
            for token in expired:
                del self._sessions[token]
            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired sessions")


def get_login_page_html(
    error_message: str = None,
    auth_mode: str = AuthMode.SIMPLE,
    touchid_available: bool = False,
    local_password_available: bool = False,
    csrf_token: str = '',
    nonce: str = '',
) -> str:
    """Generate the login page HTML based on auth mode"""
    error_html = f'<div class="error">{error_message}</div>' if error_message else ''

    # Determine which form fields to show
    show_username = auth_mode in (AuthMode.USERS, AuthMode.HYBRID)
    show_password = auth_mode in (AuthMode.SIMPLE, AuthMode.USERS, AuthMode.HYBRID)
    show_touchid = touchid_available and auth_mode in (AuthMode.TOUCHID, AuthMode.HYBRID)
    show_local_password = local_password_available and auth_mode == AuthMode.LOCAL_PASSWORD

    username_field = '''
            <div class="form-group">
                <label class="form-label">Username</label>
                <input type="text" name="username" class="form-input" placeholder="Enter username" required autofocus>
            </div>
    ''' if show_username else ''

    password_field = f'''
            <div class="form-group">
                <label class="form-label">Password</label>
                <input type="password" name="password" class="form-input" placeholder="Enter {'your ' if show_username else 'dashboard '}password" required {'autofocus' if not show_username else ''}>
            </div>
    ''' if show_password else ''

    touchid_section = '''
            <div class="divider">
                <span>or</span>
            </div>

            <button type="button" class="btn btn-touchid" onclick="authenticateWithTouchID()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M17.81 4.47c-.08 0-.16-.02-.23-.06C15.66 3.42 14 3 12.01 3c-1.98 0-3.86.47-5.57 1.41-.24.13-.54.04-.68-.2-.13-.24-.04-.55.2-.68C7.82 2.52 9.86 2 12.01 2c2.13 0 3.99.47 6.03 1.52.25.13.34.43.21.67-.09.18-.26.28-.44.28zM3.5 9.72c-.1 0-.2-.03-.29-.09-.23-.16-.28-.47-.12-.7.99-1.4 2.25-2.5 3.75-3.27C9.98 4.04 14 4.03 17.15 5.65c1.5.77 2.76 1.86 3.75 3.25.16.22.11.54-.12.7-.23.16-.54.11-.7-.12-.9-1.26-2.04-2.25-3.39-2.94-2.87-1.47-6.54-1.47-9.4.01-1.36.7-2.5 1.7-3.4 2.96-.08.14-.23.21-.39.21zm6.25 12.07c-.13 0-.26-.05-.35-.15-.87-.87-1.34-1.43-2.01-2.64-.69-1.23-1.05-2.73-1.05-4.34 0-2.97 2.54-5.39 5.66-5.39s5.66 2.42 5.66 5.39c0 .28-.22.5-.5.5s-.5-.22-.5-.5c0-2.42-2.09-4.39-4.66-4.39-2.57 0-4.66 1.97-4.66 4.39 0 1.44.32 2.77.93 3.85.64 1.15 1.08 1.64 1.85 2.42.19.2.19.51 0 .71-.11.1-.24.15-.37.15zm7.17-1.85c-1.19 0-2.24-.3-3.1-.89-1.49-1.01-2.38-2.65-2.38-4.39 0-.28.22-.5.5-.5s.5.22.5.5c0 1.41.72 2.74 1.94 3.56.71.48 1.54.71 2.54.71.24 0 .64-.03 1.04-.1.27-.05.53.13.58.41.05.27-.13.53-.41.58-.57.11-1.07.12-1.21.12zM14.91 22c-.04 0-.09-.01-.13-.02-1.59-.44-2.63-1.03-3.72-2.1-1.4-1.39-2.17-3.24-2.17-5.22 0-1.62 1.38-2.94 3.08-2.94 1.7 0 3.08 1.32 3.08 2.94 0 1.07.93 1.94 2.08 1.94s2.08-.87 2.08-1.94c0-3.77-3.25-6.83-7.25-6.83-2.84 0-5.44 1.58-6.61 4.03-.39.81-.59 1.76-.59 2.8 0 .78.07 2.01.67 3.61.1.26-.03.55-.29.64-.26.1-.55-.04-.64-.29-.49-1.31-.73-2.61-.73-3.96 0-1.2.23-2.29.68-3.24 1.33-2.79 4.28-4.6 7.51-4.6 4.55 0 8.25 3.51 8.25 7.83 0 1.62-1.38 2.94-3.08 2.94s-3.08-1.32-3.08-2.94c0-1.07-.93-1.94-2.08-1.94s-2.08.87-2.08 1.94c0 1.71.66 3.31 1.87 4.51.95.94 1.86 1.46 3.27 1.85.27.07.42.35.35.61-.05.23-.26.38-.47.38z"/>
                </svg>
                Sign in with Touch ID
            </button>

            <script nonce="{nonce}">
                async function authenticateWithTouchID() {
                    try {
                        const response = await fetch('/login', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                            body: 'use_touchid=true'
                        });

                        if (response.redirected) {
                            window.location.href = response.url;
                        } else {
                            const text = await response.text();
                            if (text.includes('error')) {
                                // Parse error from response
                                document.querySelector('.login-container').innerHTML = text;
                            } else {
                                window.location.reload();
                            }
                        }
                    } catch (err) {
                        console.error('TouchID auth error:', err);
                        alert('TouchID authentication failed. Please try again.');
                    }
                }
            </script>
    ''' if show_touchid else ''

    # Local macOS password section - form-based password entry verified via dscl
    macos_user = get_current_macos_user()
    local_password_section = f'''
            <div class="logo">
                <h1>ATLAS</h1>
                <p>System Monitor Dashboard</p>
            </div>

            <p style="color: #888; text-align: center; margin-bottom: 24px;">
                Sign in with your macOS user account
            </p>

            <form method="POST" action="/login">
                <input type="hidden" name="use_local_password" value="true">
                <input type="hidden" name="_csrf_token" value="{csrf_token}">
                <div class="form-group">
                    <label class="form-label" for="username">macOS Username</label>
                    <input type="text" id="username" name="username" class="form-input" value="{macos_user}" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="password">Password</label>
                    <input type="password" id="password" name="password" class="form-input" placeholder="Enter your Mac login password" required autofocus>
                </div>
                <button type="submit" class="btn btn-local-password">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
                    </svg>
                    Sign In
                </button>
            </form>

            <p style="color: #666; text-align: center; margin-top: 16px; font-size: 12px;">
                Uses your Mac login password for authentication
            </p>

            <style nonce="{nonce}">
                .form-group {{
                    margin-bottom: 16px;
                }}
                .form-label {{
                    display: block;
                    color: #ccc;
                    font-size: 13px;
                    font-weight: 500;
                    margin-bottom: 6px;
                }}
                .form-input {{
                    width: 100%;
                    padding: 12px 14px;
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    background: rgba(255, 255, 255, 0.05);
                    color: #fff;
                    font-size: 15px;
                    outline: none;
                    transition: border-color 0.2s;
                    box-sizing: border-box;
                }}
                .form-input:focus {{
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
                }}
                .btn-local-password {{
                    width: 100%;
                    padding: 14px;
                    border-radius: 8px;
                    border: none;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    margin-top: 8px;
                }}
                .btn-local-password:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                }}
            </style>
    ''' if show_local_password else ''

    password_form = f'''
        <form method="POST" action="/login">
            <input type="hidden" name="_csrf_token" value="{csrf_token}">
            {username_field}
            {password_field}
            <button type="submit" class="btn">Sign In</button>
        </form>
    ''' if show_password else ''

    # For local password mode, show a simplified page with just the auth button
    if show_local_password:
        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATLAS - Login</title>
    <style nonce="{nonce}">
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-container {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            backdrop-filter: blur(10px);
        }}
        .error {{
            background: rgba(231, 76, 60, 0.2);
            border: 1px solid rgba(231, 76, 60, 0.5);
            color: #e74c3c;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            margin-top: 24px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        {error_html}
        {local_password_section}
        <div class="footer">
            Protected by ATLAS Dashboard Authentication
        </div>
    </div>
</body>
</html>
'''

    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATLAS - Login</title>
    <style nonce="{nonce}">
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .login-container {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            backdrop-filter: blur(10px);
        }}

        .logo {{
            text-align: center;
            margin-bottom: 30px;
        }}

        .logo h1 {{
            font-size: 32px;
            color: #fff;
            font-weight: 700;
            letter-spacing: 2px;
        }}

        .logo p {{
            color: #888;
            margin-top: 8px;
            font-size: 14px;
        }}

        .form-group {{
            margin-bottom: 20px;
        }}

        .form-label {{
            display: block;
            color: #ccc;
            font-size: 14px;
            margin-bottom: 8px;
        }}

        .form-input {{
            width: 100%;
            padding: 14px 16px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            font-size: 16px;
            transition: border-color 0.2s;
        }}

        .form-input:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .btn {{
            width: 100%;
            padding: 14px;
            border-radius: 8px;
            border: none;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}

        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}

        .btn-touchid {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            margin-top: 12px;
        }}

        .btn-touchid:hover {{
            background: rgba(255, 255, 255, 0.15);
            box-shadow: none;
        }}

        .divider {{
            display: flex;
            align-items: center;
            margin: 24px 0;
            color: #666;
            font-size: 13px;
        }}

        .divider::before,
        .divider::after {{
            content: "";
            flex: 1;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .divider span {{
            padding: 0 16px;
        }}

        .error {{
            background: rgba(231, 76, 60, 0.2);
            border: 1px solid rgba(231, 76, 60, 0.5);
            color: #e74c3c;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}

        .footer {{
            text-align: center;
            margin-top: 24px;
            color: #666;
            font-size: 12px;
        }}

        .auth-mode-hint {{
            text-align: center;
            color: #555;
            font-size: 12px;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>ATLAS</h1>
            <p>System Monitor Dashboard</p>
        </div>

        {error_html}

        {password_form}
        {touchid_section}

        <div class="footer">
            Protected by ATLAS Dashboard Authentication
        </div>
    </div>
</body>
</html>
'''


# Singleton instance
_auth_instance: Optional[DashboardAuth] = None
_auth_lock = threading.Lock()


def get_dashboard_auth() -> DashboardAuth:
    """Get the singleton DashboardAuth instance"""
    global _auth_instance
    if _auth_instance is None:
        with _auth_lock:
            if _auth_instance is None:
                _auth_instance = DashboardAuth()
    return _auth_instance
