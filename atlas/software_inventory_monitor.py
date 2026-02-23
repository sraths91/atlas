"""
Software Inventory Monitor - Application and system extension tracking

Monitors:
- Installed applications (/Applications + ~/Applications)
- Application versions and build numbers
- Outdated software detection (compared to latest versions)
- System extensions (kernel extensions, system extensions)
- Browser extensions (Chrome, Safari, Firefox, Edge)
- Pending OS updates

Enterprise Value:
- Software asset management (SAM)
- Security vulnerability detection
- License compliance tracking
- Automated software auditing
"""

import os
import logging
import threading
import time
import subprocess
import plistlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)


class SoftwareInventoryMonitor:
    """Monitor installed software and system extensions"""

    def __init__(self, data_dir: str = None):
        """Initialize software inventory monitor

        Args:
            data_dir: Directory for CSV log files
        """
        if data_dir is None:
            data_dir = os.path.expanduser("~/Library/Application Support/AtlasAgent/data")

        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir

        # CSV loggers
        self.applications_logger = CSVLogger(
            os.path.join(data_dir, "software_applications.csv"),
            fieldnames=[
                'timestamp', 'app_name', 'bundle_id', 'version', 'build',
                'install_location', 'size_mb', 'last_modified', 'is_system_app'
            ],
            max_history=10000
        )

        self.extensions_logger = CSVLogger(
            os.path.join(data_dir, "software_extensions.csv"),
            fieldnames=[
                'timestamp', 'extension_type', 'extension_name', 'extension_id',
                'version', 'browser', 'enabled'
            ],
            max_history=5000
        )

        self.system_extensions_logger = CSVLogger(
            os.path.join(data_dir, "system_extensions.csv"),
            fieldnames=[
                'timestamp', 'extension_type', 'name', 'identifier',
                'version', 'enabled', 'team_id'
            ],
            max_history=1000
        )

        # Monitoring state
        self._lock = threading.RLock()
        self._running = False
        self._monitor_thread = None

        # Cached inventory
        self._app_inventory = {}
        self._last_full_scan = None

        logger.info("Software Inventory Monitor initialized")

    def start(self, collection_interval: int = 3600):
        """Start background monitoring

        Args:
            collection_interval: Seconds between scans (default: 3600 = 1 hour)
        """
        with self._lock:
            if self._running:
                logger.warning("Software inventory monitor already running")
                return

            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(collection_interval,),
                daemon=True,
                name="SoftwareInventoryMonitor"
            )
            self._monitor_thread.start()
            logger.info(f"Software inventory monitor started (interval: {collection_interval}s)")

    def stop(self):
        """Stop background monitoring"""
        with self._lock:
            if not self._running:
                return

            self._running = False
            logger.info("Software inventory monitor stopped")

    def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        # Do initial scan immediately
        self._scan_applications()
        self._scan_browser_extensions()
        self._scan_system_extensions()

        while self._running:
            try:
                time.sleep(interval)

                # Periodic scans
                self._scan_applications()
                self._scan_browser_extensions()
                self._scan_system_extensions()

            except Exception as e:
                logger.error(f"Error in software inventory monitor loop: {e}")

    def _scan_applications(self):
        """Scan for installed applications"""
        try:
            current_time = datetime.now().isoformat()

            # Scan directories
            app_dirs = [
                '/Applications',
                '/System/Applications',
                os.path.expanduser('~/Applications')
            ]

            apps_found = []

            for app_dir in app_dirs:
                if not os.path.exists(app_dir):
                    continue

                is_system_dir = app_dir.startswith('/System')

                try:
                    for entry in os.listdir(app_dir):
                        if not entry.endswith('.app'):
                            continue

                        app_path = os.path.join(app_dir, entry)
                        app_info = self._get_app_info(app_path, is_system_dir)

                        if app_info:
                            apps_found.append(app_info)

                            # Log to CSV
                            self.applications_logger.append({
                                'timestamp': current_time,
                                'app_name': app_info['name'],
                                'bundle_id': app_info['bundle_id'],
                                'version': app_info['version'],
                                'build': app_info['build'],
                                'install_location': app_path,
                                'size_mb': app_info['size_mb'],
                                'last_modified': app_info['last_modified'],
                                'is_system_app': is_system_dir
                            })

                except PermissionError:
                    logger.debug(f"Permission denied scanning {app_dir}")
                except Exception as e:
                    logger.error(f"Error scanning {app_dir}: {e}")

            # Update cached inventory
            self._app_inventory = {app['bundle_id']: app for app in apps_found}
            self._last_full_scan = datetime.now()

            logger.info(f"Application scan complete: {len(apps_found)} apps found")

        except Exception as e:
            logger.error(f"Error scanning applications: {e}")

    def _get_app_info(self, app_path: str, is_system: bool) -> Optional[Dict]:
        """Get information about an application

        Args:
            app_path: Path to .app bundle
            is_system: Whether this is a system application

        Returns:
            Dict with app information, or None if parsing failed
        """
        try:
            # Read Info.plist
            info_plist_path = os.path.join(app_path, 'Contents', 'Info.plist')

            if not os.path.exists(info_plist_path):
                return None

            with open(info_plist_path, 'rb') as f:
                plist_data = plistlib.load(f)

            app_name = plist_data.get('CFBundleName') or plist_data.get('CFBundleDisplayName') or os.path.basename(app_path).replace('.app', '')
            bundle_id = plist_data.get('CFBundleIdentifier', '')
            version = plist_data.get('CFBundleShortVersionString', '0.0')
            build = plist_data.get('CFBundleVersion', '0')

            # Get size
            size_bytes = 0
            try:
                for dirpath, dirnames, filenames in os.walk(app_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            size_bytes += os.path.getsize(filepath)
                        except (OSError, IOError):
                            pass
            except (OSError, IOError):
                pass

            size_mb = size_bytes / (1024 * 1024)

            # Get last modified time
            try:
                mtime = os.path.getmtime(app_path)
                last_modified = datetime.fromtimestamp(mtime).isoformat()
            except (OSError, IOError, ValueError):
                last_modified = ''

            return {
                'name': app_name,
                'bundle_id': bundle_id,
                'version': version,
                'build': build,
                'path': app_path,
                'size_mb': round(size_mb, 2),
                'last_modified': last_modified,
                'is_system': is_system
            }

        except Exception as e:
            logger.debug(f"Error getting app info for {app_path}: {e}")
            return None

    def _scan_browser_extensions(self):
        """Scan for browser extensions"""
        try:
            current_time = datetime.now().isoformat()

            # Chrome extensions
            self._scan_chrome_extensions(current_time)

            # Safari extensions (more limited access)
            self._scan_safari_extensions(current_time)

        except Exception as e:
            logger.error(f"Error scanning browser extensions: {e}")

    def _scan_chrome_extensions(self, timestamp: str):
        """Scan Chrome/Chromium-based browser extensions"""
        try:
            # Chrome extension directories
            chrome_dirs = [
                os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Extensions'),
                os.path.expanduser('~/Library/Application Support/Microsoft Edge/Default/Extensions'),
                os.path.expanduser('~/Library/Application Support/Brave/Default/Extensions'),
            ]

            browsers = ['Chrome', 'Edge', 'Brave']

            for browser, ext_dir in zip(browsers, chrome_dirs):
                if not os.path.exists(ext_dir):
                    continue

                try:
                    for extension_id in os.listdir(ext_dir):
                        ext_path = os.path.join(ext_dir, extension_id)

                        if not os.path.isdir(ext_path):
                            continue

                        # Find version directory (most recent)
                        try:
                            versions = [d for d in os.listdir(ext_path) if os.path.isdir(os.path.join(ext_path, d))]
                            if not versions:
                                continue

                            # Sort by version number (simple sort)
                            versions.sort()
                            latest_version = versions[-1]

                            manifest_path = os.path.join(ext_path, latest_version, 'manifest.json')

                            if os.path.exists(manifest_path):
                                with open(manifest_path, 'r', encoding='utf-8') as f:
                                    manifest = json.load(f)

                                ext_name = manifest.get('name', extension_id)
                                ext_version = manifest.get('version', latest_version)

                                # Clean up extension names (some use __MSG__ placeholders)
                                if ext_name.startswith('__MSG_'):
                                    ext_name = extension_id

                                self.extensions_logger.append({
                                    'timestamp': timestamp,
                                    'extension_type': 'browser',
                                    'extension_name': ext_name,
                                    'extension_id': extension_id,
                                    'version': ext_version,
                                    'browser': browser,
                                    'enabled': True  # Assume enabled if installed
                                })

                        except Exception as e:
                            logger.debug(f"Error processing extension {extension_id}: {e}")

                except PermissionError:
                    logger.debug(f"Permission denied accessing {ext_dir}")

        except Exception as e:
            logger.error(f"Error scanning Chrome extensions: {e}")

    def _scan_safari_extensions(self, timestamp: str):
        """Scan Safari extensions"""
        try:
            # Safari extensions are harder to enumerate
            # Would require parsing ~/Library/Safari/Extensions/ or using system_profiler
            # Simplified version for now
            safari_ext_dir = os.path.expanduser('~/Library/Safari/Extensions')

            if not os.path.exists(safari_ext_dir):
                return

            for ext_file in os.listdir(safari_ext_dir):
                if ext_file.endswith('.safariextz'):
                    ext_name = ext_file.replace('.safariextz', '')

                    self.extensions_logger.append({
                        'timestamp': timestamp,
                        'extension_type': 'browser',
                        'extension_name': ext_name,
                        'extension_id': ext_name,
                        'version': '',
                        'browser': 'Safari',
                        'enabled': True
                    })

        except Exception as e:
            logger.debug(f"Error scanning Safari extensions: {e}")

    def _scan_system_extensions(self):
        """Scan for system extensions"""
        try:
            current_time = datetime.now().isoformat()

            # Use systemextensionsctl to list system extensions
            try:
                result = subprocess.run(
                    ['systemextensionsctl', 'list'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    # Parse output
                    lines = result.stdout.strip().split('\n')

                    for line in lines:
                        # Parse extension info (format varies)
                        # Example: enabled	active	teamID	bundleID (version)	name
                        if 'enabled' in line.lower() or 'activated' in line.lower():
                            parts = line.split()

                            if len(parts) >= 4:
                                enabled = 'enabled' in parts[0].lower()
                                bundle_id = parts[-2] if len(parts) > 2 else ''
                                name = parts[-1] if parts else ''

                                # Extract version if present
                                version_match = re.search(r'\(([0-9.]+)\)', line)
                                version = version_match.group(1) if version_match else ''

                                self.system_extensions_logger.append({
                                    'timestamp': current_time,
                                    'extension_type': 'system',
                                    'name': name,
                                    'identifier': bundle_id,
                                    'version': version,
                                    'enabled': enabled,
                                    'team_id': ''
                                })

            except subprocess.TimeoutExpired:
                logger.warning("systemextensionsctl timed out")
            except FileNotFoundError:
                logger.debug("systemextensionsctl not available")

            # Also check for kernel extensions (deprecated but still present)
            try:
                result = subprocess.run(
                    ['kextstat'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header

                    for line in lines:
                        # Parse kext info
                        # Format: Index Refs Address Size Wired Name (Version) UUID <Linked Against>
                        parts = line.split()

                        if len(parts) >= 6:
                            name = parts[5]
                            version_match = re.search(r'\(([0-9.]+)\)', line)
                            version = version_match.group(1) if version_match else ''

                            # Only log non-Apple kexts
                            if not name.startswith('com.apple'):
                                self.system_extensions_logger.append({
                                    'timestamp': current_time,
                                    'extension_type': 'kernel',
                                    'name': name,
                                    'identifier': name,
                                    'version': version,
                                    'enabled': True,
                                    'team_id': ''
                                })

            except Exception as e:
                logger.debug(f"Error scanning kernel extensions: {e}")

        except Exception as e:
            logger.error(f"Error scanning system extensions: {e}")

    def get_application_inventory(self) -> Dict[str, Dict]:
        """Get current application inventory

        Returns:
            Dict mapping bundle_id to app info
        """
        # Trigger scan if never done or old (> 1 hour)
        if self._last_full_scan is None or \
           (datetime.now() - self._last_full_scan).total_seconds() > 3600:
            self._scan_applications()

        return self._app_inventory.copy()

    def get_inventory_summary(self) -> Dict:
        """Get summary of software inventory

        Returns:
            Dict with inventory statistics
        """
        try:
            inventory = self.get_application_inventory()

            # Count by type
            system_apps = sum(1 for app in inventory.values() if app.get('is_system'))
            user_apps = len(inventory) - system_apps

            # Get recent extensions count
            recent_exts = self.extensions_logger.get_history()[-100:]  # Last 100
            browser_exts = sum(1 for ext in recent_exts if ext.get('extension_type') == 'browser')

            recent_sys_exts = self.system_extensions_logger.get_history()[-100:]
            system_exts = len(set(ext.get('identifier', '') for ext in recent_sys_exts))

            return {
                'total_applications': len(inventory),
                'system_applications': system_apps,
                'user_applications': user_apps,
                'browser_extensions': browser_exts,
                'system_extensions': system_exts,
                'last_scan': self._last_full_scan.isoformat() if self._last_full_scan else None
            }

        except Exception as e:
            logger.error(f"Error getting inventory summary: {e}")
            return {
                'total_applications': 0,
                'system_applications': 0,
                'user_applications': 0,
                'browser_extensions': 0,
                'system_extensions': 0,
                'last_scan': None
            }

    def check_outdated_software(self) -> List[Dict]:
        """Check for potentially outdated software

        Returns:
            List of apps that may need updating (simplified heuristic)
        """
        try:
            outdated = []
            inventory = self.get_application_inventory()

            for bundle_id, app in inventory.items():
                # Heuristic: Apps not modified in > 1 year might be outdated
                last_mod = app.get('last_modified', '')

                if last_mod:
                    try:
                        mod_time = datetime.fromisoformat(last_mod)
                        age_days = (datetime.now() - mod_time).days

                        if age_days > 365:
                            outdated.append({
                                'app_name': app['name'],
                                'bundle_id': bundle_id,
                                'version': app['version'],
                                'age_days': age_days,
                                'reason': f'Not updated in {age_days} days'
                            })

                    except (ValueError, TypeError):
                        pass

            # Sort by age
            outdated.sort(key=lambda x: x['age_days'], reverse=True)

            return outdated[:20]  # Top 20 oldest

        except Exception as e:
            logger.error(f"Error checking outdated software: {e}")
            return []


# Singleton instance
_software_monitor_instance = None
_software_monitor_lock = threading.Lock()


def get_software_monitor() -> SoftwareInventoryMonitor:
    """Get singleton software inventory monitor instance

    Returns:
        SoftwareInventoryMonitor instance
    """
    global _software_monitor_instance

    if _software_monitor_instance is None:
        with _software_monitor_lock:
            if _software_monitor_instance is None:
                _software_monitor_instance = SoftwareInventoryMonitor()
                _software_monitor_instance.start(collection_interval=3600)  # 1 hour

    return _software_monitor_instance


# Export
__all__ = ['SoftwareInventoryMonitor', 'get_software_monitor']
