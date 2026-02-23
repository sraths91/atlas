"""
Security & Compliance Monitor - Track security posture and compliance status

Monitors:
- Firewall status
- FileVault encryption status
- OS update status (pending security updates)
- Failed login attempts
- Antivirus/EDR status
- Screen lock policy compliance
- Gatekeeper status
- System Integrity Protection (SIP) status

Supports macOS versions:
- macOS 10.x (Catalina and earlier)
- macOS 11.x (Big Sur)
- macOS 12.x (Monterey)
- macOS 13.x (Ventura)
- macOS 14.x (Sonoma)
- macOS 15.x (Sequoia)
- macOS 26.x (Tahoe)
"""

import logging
import subprocess
import re
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)


def get_macos_version() -> Tuple[int, int, int]:
    """Get macOS version as tuple (major, minor, patch)

    Returns:
        Tuple of (major, minor, patch) version numbers
        e.g., (26, 2, 0) for macOS Tahoe 26.2
    """
    try:
        result = subprocess.run(
            ['sw_vers', '-productVersion'],
            capture_output=True, text=True, timeout=5
        )
        version_str = result.stdout.strip()
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except Exception as e:
        logger.error(f"Error getting macOS version: {e}")
        return (0, 0, 0)


def get_macos_name(major_version: int) -> str:
    """Get macOS marketing name from major version number"""
    names = {
        10: "Catalina or earlier",
        11: "Big Sur",
        12: "Monterey",
        13: "Ventura",
        14: "Sonoma",
        15: "Sequoia",
        26: "Tahoe"
    }
    return names.get(major_version, f"macOS {major_version}")


class SecurityMonitor:
    """Monitor macOS security posture and compliance"""

    def __init__(self, sample_interval: int = 300):  # 5 minutes default
        """
        Initialize security monitor

        Args:
            sample_interval: Seconds between security checks (default: 300)
        """
        self.sample_interval = sample_interval
        self._running = False
        self._thread = None

        # Detect macOS version for version-specific behavior
        self.macos_version = get_macos_version()
        self.macos_major = self.macos_version[0]
        self.macos_name = get_macos_name(self.macos_major)
        logger.info(f"SecurityMonitor initialized for {self.macos_name} ({'.'.join(map(str, self.macos_version))})")

        # CSV Loggers
        log_dir = Path.home()
        self.security_status_logger = CSVLogger(
            str(log_dir / 'security_status.csv'),
            fieldnames=['timestamp', 'firewall_enabled', 'filevault_enabled',
                    'gatekeeper_enabled', 'sip_enabled', 'screen_lock_enabled',
                    'auto_updates_enabled', 'pending_updates_count',
                    'security_score'],
            retention_days=30,
            max_history=500
        )

        self.security_events_logger = CSVLogger(
            str(log_dir / 'security_events.csv'),
            fieldnames=['timestamp', 'event_type', 'severity', 'details', 'recommendation'],
            retention_days=90,
            max_history=1000
        )

        self.failed_logins_logger = CSVLogger(
            str(log_dir / 'failed_logins.csv'),
            fieldnames=['timestamp', 'user', 'source_ip', 'auth_method', 'reason'],
            retention_days=90,
            max_history=1000
        )

        # Previous state for change detection
        self._prev_security_state: Optional[Dict] = None

    def start(self):
        """Start security monitoring"""
        if self._running:
            logger.warning("Security monitor already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Security monitor started with {self.sample_interval}s interval")

        # Also start failed login monitoring
        self._start_failed_login_monitor()

    def stop(self):
        """Stop monitoring"""
        self._running = False
        # Terminate login monitor subprocess if running
        if hasattr(self, '_login_monitor_process'):
            proc = self._login_monitor_process
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Security monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._collect_security_status()
            except Exception as e:
                logger.error(f"Error in security monitoring loop: {e}")

            # Sleep in small intervals to allow graceful shutdown
            for _ in range(self.sample_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _collect_security_status(self):
        """Collect comprehensive security status"""
        current_time = datetime.now()

        # Collect all security metrics
        firewall_status = self._check_firewall()
        filevault_status = self._check_filevault()
        gatekeeper_status = self._check_gatekeeper()
        sip_status = self._check_sip()
        screen_lock_status = self._check_screen_lock()
        update_status = self._check_os_updates()

        # Calculate security score (0-100)
        security_score = self._calculate_security_score({
            'firewall': firewall_status,
            'filevault': filevault_status,
            'gatekeeper': gatekeeper_status,
            'sip': sip_status,
            'screen_lock': screen_lock_status,
            'updates': update_status
        })

        # Log security status
        self.security_status_logger.append({
            'timestamp': current_time.isoformat(),
            'firewall_enabled': firewall_status.get('enabled', False),
            'filevault_enabled': filevault_status.get('enabled', False),
            'gatekeeper_enabled': gatekeeper_status.get('enabled', False),
            'sip_enabled': sip_status.get('enabled', False),
            'screen_lock_enabled': screen_lock_status.get('enabled', False),
            'auto_updates_enabled': update_status.get('auto_updates_enabled', False),
            'pending_updates_count': update_status.get('pending_count', 0),
            'security_score': security_score
        })

        # Detect and log security events (changes in status)
        if self._prev_security_state:
            self._detect_security_events({
                'firewall': firewall_status,
                'filevault': filevault_status,
                'gatekeeper': gatekeeper_status,
                'sip': sip_status,
                'screen_lock': screen_lock_status,
                'updates': update_status
            }, current_time)

        # Log warnings for security issues
        self._check_security_compliance({
            'firewall': firewall_status,
            'filevault': filevault_status,
            'gatekeeper': gatekeeper_status,
            'sip': sip_status,
            'screen_lock': screen_lock_status,
            'updates': update_status
        }, current_time)

        self._prev_security_state = {
            'firewall': firewall_status,
            'filevault': filevault_status,
            'gatekeeper': gatekeeper_status,
            'sip': sip_status,
            'screen_lock': screen_lock_status,
            'updates': update_status
        }

    def _check_firewall(self) -> Dict:
        """Check macOS firewall status"""
        try:
            result = subprocess.run(
                ['sudo', '-n', '/usr/libexec/ApplicationFirewall/socketfilterfw', '--getglobalstate'],
                capture_output=True, text=True, timeout=5
            )

            enabled = 'enabled' in result.stdout.lower()

            # Try to get stealth mode status
            stealth_result = subprocess.run(
                ['sudo', '-n', '/usr/libexec/ApplicationFirewall/socketfilterfw', '--getstealthmode'],
                capture_output=True, text=True, timeout=5
            )
            stealth_enabled = 'enabled' in stealth_result.stdout.lower()

            return {
                'enabled': enabled,
                'stealth_mode': stealth_enabled
            }

        except Exception as e:
            logger.error(f"Error checking firewall status: {e}")
            return {'enabled': False, 'stealth_mode': False}

    def _check_filevault(self) -> Dict:
        """Check FileVault encryption status"""
        try:
            result = subprocess.run(
                ['fdesetup', 'status'],
                capture_output=True, text=True, timeout=5
            )

            enabled = 'FileVault is On' in result.stdout

            return {'enabled': enabled}

        except Exception as e:
            logger.error(f"Error checking FileVault status: {e}")
            return {'enabled': False}

    def _check_gatekeeper(self) -> Dict:
        """Check Gatekeeper status"""
        try:
            result = subprocess.run(
                ['spctl', '--status'],
                capture_output=True, text=True, timeout=5
            )

            enabled = 'enabled' in result.stdout.lower()

            return {'enabled': enabled}

        except Exception as e:
            logger.error(f"Error checking Gatekeeper status: {e}")
            return {'enabled': False}

    def _check_sip(self) -> Dict:
        """Check System Integrity Protection status"""
        try:
            result = subprocess.run(
                ['csrutil', 'status'],
                capture_output=True, text=True, timeout=5
            )

            enabled = 'enabled' in result.stdout.lower()

            return {'enabled': enabled}

        except Exception as e:
            logger.error(f"Error checking SIP status: {e}")
            return {'enabled': False}

    def _check_screen_lock(self) -> Dict:
        """Check screen lock policy"""
        try:
            delay_seconds = None
            enabled = False

            # Method 1: Try sysadminctl (most reliable on modern macOS)
            try:
                result = subprocess.run(
                    ['sysadminctl', '-screenLock', 'status'],
                    capture_output=True, text=True, timeout=5
                )
                # Output like: "screenLock delay is 300 seconds" or "screenLock is off"
                output = result.stderr + result.stdout  # sysadminctl outputs to stderr
                if 'delay is' in output.lower():
                    import re
                    match = re.search(r'delay is (\d+)', output)
                    if match:
                        delay_seconds = int(match.group(1))
                        enabled = True  # Screen lock is configured
                elif 'is off' in output.lower():
                    enabled = False
                    delay_seconds = 0
            except Exception:
                pass

            # Method 2: Fallback to defaults if sysadminctl didn't work
            if delay_seconds is None:
                # Check if screen saver requires password
                result = subprocess.run(
                    ['defaults', 'read', 'com.apple.screensaver', 'askForPassword'],
                    capture_output=True, text=True, timeout=5
                )
                ask_for_password = '1' in result.stdout

                # Check delay time
                delay_result = subprocess.run(
                    ['defaults', 'read', 'com.apple.screensaver', 'askForPasswordDelay'],
                    capture_output=True, text=True, timeout=5
                )

                delay_seconds = 0
                if delay_result.returncode == 0:
                    try:
                        delay_seconds = int(delay_result.stdout.strip())
                    except (ValueError, TypeError):
                        pass

                enabled = ask_for_password

            return {
                'enabled': enabled,
                'delay_seconds': delay_seconds or 0
            }

        except Exception as e:
            logger.error(f"Error checking screen lock status: {e}")
            return {'enabled': False, 'delay_seconds': 0}

    def _check_os_updates(self) -> Dict:
        """Check for pending OS updates (version-aware)"""
        try:
            auto_updates_enabled = False

            # Version-specific update preference keys
            # macOS 26 (Tahoe) and newer use these keys
            # Older versions may use different keys
            if self.macos_major >= 26:
                # macOS Tahoe and later
                update_keys = [
                    'AutomaticDownload',
                    'AutomaticallyInstallMacOSUpdates',
                    'CriticalUpdateInstall',
                    'ConfigDataInstall'
                ]
            elif self.macos_major >= 13:
                # macOS Ventura, Sonoma, Sequoia (13-15)
                update_keys = [
                    'AutomaticDownload',
                    'AutomaticallyInstallMacOSUpdates',
                    'AutomaticCheckEnabled',
                    'CriticalUpdateInstall'
                ]
            else:
                # macOS Monterey and earlier (10-12)
                update_keys = [
                    'AutomaticCheckEnabled',
                    'AutomaticDownload',
                    'CriticalUpdateInstall'
                ]

            for key in update_keys:
                try:
                    result = subprocess.run(
                        ['defaults', 'read', '/Library/Preferences/com.apple.SoftwareUpdate', key],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and '1' in result.stdout:
                        auto_updates_enabled = True
                        logger.debug(f"Auto-updates enabled via key: {key}")
                        break
                except Exception:
                    pass

            # Check for pending updates
            update_result = subprocess.run(
                ['softwareupdate', '-l'],
                capture_output=True, text=True, timeout=30
            )

            # Count pending updates
            pending_count = 0
            security_updates = 0

            for line in update_result.stdout.split('\n'):
                if '* ' in line or 'Title:' in line:
                    pending_count += 1
                    if 'security' in line.lower() or 'patch' in line.lower():
                        security_updates += 1

            return {
                'auto_updates_enabled': auto_updates_enabled,
                'pending_count': pending_count,
                'security_updates_count': security_updates
            }

        except Exception as e:
            logger.error(f"Error checking OS updates: {e}")
            return {
                'auto_updates_enabled': False,
                'pending_count': 0,
                'security_updates_count': 0
            }

    def _calculate_security_score(self, status: Dict) -> int:
        """Calculate overall security score (0-100)"""
        score = 0
        max_score = 100

        # Firewall (20 points)
        if status['firewall'].get('enabled'):
            score += 20
            if status['firewall'].get('stealth_mode'):
                score += 5

        # FileVault (25 points - very important)
        if status['filevault'].get('enabled'):
            score += 25

        # Gatekeeper (15 points)
        if status['gatekeeper'].get('enabled'):
            score += 15

        # SIP (15 points)
        if status['sip'].get('enabled'):
            score += 15

        # Screen Lock (15 points)
        if status['screen_lock'].get('enabled'):
            score += 15

        # Updates (10 points)
        if status['updates'].get('auto_updates_enabled'):
            score += 5

        # Deduct points for pending security updates
        pending_security = status['updates'].get('security_updates_count', 0)
        if pending_security == 0:
            score += 5
        elif pending_security > 5:
            score -= 10

        return min(max_score, max(0, score))

    def _detect_security_events(self, current_state: Dict, current_time: datetime):
        """Detect changes in security posture"""
        prev_state = self._prev_security_state

        # Firewall disabled
        if prev_state['firewall'].get('enabled') and not current_state['firewall'].get('enabled'):
            self._log_security_event('firewall_disabled', 'critical', current_time,
                                    'Firewall has been disabled',
                                    'Re-enable firewall immediately')

        # FileVault disabled
        if prev_state['filevault'].get('enabled') and not current_state['filevault'].get('enabled'):
            self._log_security_event('filevault_disabled', 'critical', current_time,
                                    'FileVault encryption has been disabled',
                                    'Re-enable FileVault encryption')

        # Gatekeeper disabled
        if prev_state['gatekeeper'].get('enabled') and not current_state['gatekeeper'].get('enabled'):
            self._log_security_event('gatekeeper_disabled', 'high', current_time,
                                    'Gatekeeper has been disabled',
                                    'Re-enable Gatekeeper')

        # SIP disabled
        if prev_state['sip'].get('enabled') and not current_state['sip'].get('enabled'):
            self._log_security_event('sip_disabled', 'high', current_time,
                                    'System Integrity Protection has been disabled',
                                    'Re-enable SIP (requires recovery mode)')

    def _check_security_compliance(self, status: Dict, current_time: datetime):
        """Check for security compliance issues"""
        # Critical: FileVault not enabled
        if not status['filevault'].get('enabled'):
            self._log_security_event('filevault_not_enabled', 'critical', current_time,
                                    'Disk encryption (FileVault) is not enabled',
                                    'Enable FileVault in System Preferences > Security & Privacy')

        # High: Firewall not enabled
        if not status['firewall'].get('enabled'):
            self._log_security_event('firewall_not_enabled', 'high', current_time,
                                    'Firewall is not enabled',
                                    'Enable firewall in System Preferences > Security & Privacy')

        # Medium: Screen lock delay too long
        screen_lock = status['screen_lock']
        if not screen_lock.get('enabled') or screen_lock.get('delay_seconds', 999) > 5:
            self._log_security_event('screen_lock_not_secure', 'medium', current_time,
                                    'Screen lock is not configured securely',
                                    'Require password immediately after screen saver begins')

        # Medium: Pending security updates
        security_updates = status['updates'].get('security_updates_count', 0)
        if security_updates > 0:
            self._log_security_event('pending_security_updates', 'medium', current_time,
                                    f'{security_updates} pending security update(s)',
                                    'Install security updates as soon as possible')

    def _log_security_event(self, event_type: str, severity: str, timestamp: datetime,
                           details: str, recommendation: str):
        """Log security event"""
        self.security_events_logger.append({
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'severity': severity,
            'details': details,
            'recommendation': recommendation
        })

        log_func = logger.critical if severity == 'critical' else \
                   logger.warning if severity == 'high' else logger.info

        log_func(f"Security event [{severity}]: {details}")

    def _start_failed_login_monitor(self):
        """Monitor failed login attempts"""
        # Start background thread to monitor system log for failed logins
        def monitor_failed_logins():
            import select
            try:
                # Use log stream to monitor authentication failures
                process = subprocess.Popen(
                    ['log', 'stream', '--predicate', 'eventMessage CONTAINS "authentication failure"',
                     '--style', 'syslog'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self._login_monitor_process = process

                while self._running:
                    # Use select with timeout to avoid blocking indefinitely on readline
                    ready, _, _ = select.select([process.stdout], [], [], 1.0)
                    if ready:
                        line = process.stdout.readline()
                        if line:
                            self._parse_failed_login(line)
                        else:
                            break  # EOF - process exited

            except Exception as e:
                logger.error(f"Error monitoring failed logins: {e}")
            finally:
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

        threading.Thread(target=monitor_failed_logins, daemon=True).start()

    def _parse_failed_login(self, log_line: str):
        """Parse failed login attempt from log"""
        try:
            # Extract user and source if possible
            user = 'unknown'
            source_ip = 'local'

            user_match = re.search(r'user[= ](\w+)', log_line, re.IGNORECASE)
            if user_match:
                user = user_match.group(1)

            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', log_line)
            if ip_match:
                source_ip = ip_match.group(1)

            self.failed_logins_logger.append({
                'timestamp': datetime.now().isoformat(),
                'user': user,
                'source_ip': source_ip,
                'auth_method': 'unknown',
                'reason': 'authentication_failure'
            })

            logger.warning(f"Failed login attempt: user={user}, source={source_ip}")

        except Exception as e:
            logger.error(f"Error parsing failed login: {e}")

    def get_current_security_status(self) -> Dict:
        """Get current security status with full nested structure"""
        recent_entries = self.security_status_logger.get_history()

        # If no data collected yet, trigger immediate collection
        if not recent_entries:
            try:
                self._collect_security_status()
                recent_entries = self.security_status_logger.get_history()
            except Exception as e:
                logger.error(f"Error collecting security status on demand: {e}")
                return {}

        if not recent_entries:
            return {}

        # Get latest CSV entry (flattened format)
        latest = recent_entries[-1]

        # Helper to convert string booleans to actual booleans
        def to_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)

        # Helper to convert to int
        def to_int(value):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0

        # Reconstruct full nested structure for API/widget consumption
        return {
            'security_score': to_int(latest.get('security_score', 0)),
            'macos_version': '.'.join(map(str, self.macos_version)),
            'macos_name': self.macos_name,
            'firewall': {
                'enabled': to_bool(latest.get('firewall_enabled', False))
            },
            'filevault': {
                'enabled': to_bool(latest.get('filevault_enabled', False))
            },
            'gatekeeper': {
                'enabled': to_bool(latest.get('gatekeeper_enabled', False))
            },
            'sip': {
                'enabled': to_bool(latest.get('sip_enabled', False))
            },
            'screen_lock': {
                'enabled': to_bool(latest.get('screen_lock_enabled', False))
            },
            'updates': {
                'auto_updates_enabled': to_bool(latest.get('auto_updates_enabled', False)),
                'pending_count': to_int(latest.get('pending_updates_count', 0)),
                'security_updates_count': to_int(latest.get('pending_updates_count', 0))
            }
        }

    def get_security_events(self, severity: Optional[str] = None) -> List[Dict]:
        """Get security events, optionally filtered by severity"""
        events = self.security_events_logger.get_history()

        if severity:
            events = [e for e in events if e.get('severity') == severity]

        return events

    def get_failed_login_attempts(self, hours: int = 24) -> List[Dict]:
        """Get failed login attempts"""
        return self.failed_logins_logger.get_history()


# Singleton instance
_security_monitor_instance = None
_monitor_lock = threading.Lock()

def get_security_monitor(sample_interval: int = 300) -> SecurityMonitor:
    """Get or create singleton security monitor instance"""
    global _security_monitor_instance

    with _monitor_lock:
        if _security_monitor_instance is None:
            _security_monitor_instance = SecurityMonitor(sample_interval=sample_interval)
            _security_monitor_instance.start()

        return _security_monitor_instance
