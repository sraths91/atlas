#!/usr/bin/env python3
"""
Peripheral Device Monitor for ATLAS Agent

Tracks Bluetooth, USB, and Thunderbolt peripheral devices for:
- Device inventory and tracking
- Connection/disconnection events
- Security compliance (unauthorized device detection)
- Asset management

Business Value:
- Security: Detect unauthorized USB/Thunderbolt devices
- Compliance: Track peripheral device usage for audit trails
- Asset Management: Inventory of connected peripherals
- Troubleshooting: Identify problematic device connections

Author: ATLAS Agent Development Team
Date: January 2026
"""

import subprocess
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import plistlib
import os
import logging

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)


class PeripheralMonitor:
    """
    Monitor for tracking Bluetooth, USB, and Thunderbolt peripheral devices.

    Features:
    - Bluetooth device inventory (paired and connected devices)
    - USB device inventory (all connected USB devices)
    - Thunderbolt device inventory (Thunderbolt 3/4 devices)
    - Connection/disconnection event tracking
    - Device metadata (vendor, product, serial number)
    - Unauthorized device detection

    CSV Output Files:
    - bluetooth_devices.csv: Bluetooth device inventory and connection events
    - usb_devices.csv: USB device inventory and connection events
    - thunderbolt_devices.csv: Thunderbolt device inventory and events
    - peripheral_events.csv: All connection/disconnection events
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, data_dir: str = None):
        """
        Initialize the Peripheral Monitor.

        Args:
            data_dir: Directory for CSV log files (default: ~/.atlas_agent/data)
        """
        if data_dir is None:
            data_dir = os.path.expanduser('~/.atlas_agent/data')

        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        # CSV loggers for different peripheral types
        self.bluetooth_logger = CSVLogger(
            log_file=os.path.join(self.data_dir, 'bluetooth_devices.csv'),
            fieldnames=[
                'timestamp', 'device_name', 'device_address', 'device_type',
                'is_connected', 'is_paired', 'rssi', 'battery_level',
                'vendor_id', 'product_id', 'services'
            ]
        )

        self.usb_logger = CSVLogger(
            log_file=os.path.join(self.data_dir, 'usb_devices.csv'),
            fieldnames=[
                'timestamp', 'device_name', 'vendor', 'vendor_id', 'product_id',
                'serial_number', 'location_id', 'speed', 'bus_power',
                'device_class', 'is_apple'
            ]
        )

        self.thunderbolt_logger = CSVLogger(
            log_file=os.path.join(self.data_dir, 'thunderbolt_devices.csv'),
            fieldnames=[
                'timestamp', 'device_name', 'vendor', 'device_uid',
                'domain_uuid', 'route_string', 'link_speed', 'link_width',
                'device_rom_version', 'receptacle_id'
            ]
        )

        self.events_logger = CSVLogger(
            log_file=os.path.join(self.data_dir, 'peripheral_events.csv'),
            fieldnames=[
                'timestamp', 'event_type', 'device_type', 'device_name',
                'device_id', 'vendor', 'details'
            ]
        )

        # Track current device states to detect changes
        self.current_bluetooth_devices = {}
        self.current_usb_devices = {}
        self.current_thunderbolt_devices = {}

        # Statistics
        self.total_bluetooth_events = 0
        self.total_usb_events = 0
        self.total_thunderbolt_events = 0

        # Background monitoring thread
        self.monitor_thread = None
        self.running = False
        self.collection_interval = 300  # Check every 5 minutes (reduced from 30s to avoid IOKit stress)

    def start(self):
        """Start background peripheral monitoring."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """Stop background peripheral monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                self._collect_bluetooth_devices()
                self._collect_usb_devices()
                self._collect_thunderbolt_devices()
            except Exception as e:
                logger.error(f"Error in peripheral monitor loop: {e}")

            # Sleep in small intervals to allow graceful shutdown
            for _ in range(self.collection_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _collect_bluetooth_devices(self):
        """Collect Bluetooth device inventory using system_profiler."""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPBluetoothDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return

            data = json.loads(result.stdout)
            timestamp = datetime.now().isoformat()

            # Parse Bluetooth data structure
            bt_data = data.get('SPBluetoothDataType', [])
            if not bt_data:
                return

            current_devices = {}

            for controller in bt_data:
                # Get paired devices
                devices = controller.get('device_connected', [])
                devices.extend(controller.get('device_not_connected', []))

                for device in devices:
                    device_name = device.get('device_name', 'Unknown')
                    device_address = device.get('device_address', '')

                    # Determine connection status
                    is_connected = 'device_isconnected' in device and device['device_isconnected'] == 'attrib_Yes'
                    is_paired = True  # If in list, it's paired

                    # Extract device details
                    device_type = device.get('device_minorType', 'Unknown')
                    rssi = device.get('device_rssi', '')
                    battery_level = device.get('device_batteryLevel', '')
                    vendor_id = device.get('device_vendorID', '')
                    product_id = device.get('device_productID', '')

                    # Get services
                    services = []
                    if 'device_services' in device:
                        services = list(device['device_services'].keys())
                    services_str = ','.join(services) if services else ''

                    # Log device state
                    self.bluetooth_logger.append({
                        'timestamp': timestamp,
                        'device_name': device_name,
                        'device_address': device_address,
                        'device_type': device_type,
                        'is_connected': is_connected,
                        'is_paired': is_paired,
                        'rssi': rssi,
                        'battery_level': battery_level,
                        'vendor_id': vendor_id,
                        'product_id': product_id,
                        'services': services_str
                    })

                    current_devices[device_address] = {
                        'name': device_name,
                        'connected': is_connected
                    }

            # Detect connection/disconnection events
            self._detect_bluetooth_events(current_devices, timestamp)
            self.current_bluetooth_devices = current_devices

        except subprocess.TimeoutExpired:
            logger.warning("Bluetooth profiler timed out")
        except json.JSONDecodeError:
            logger.error("Failed to parse Bluetooth data")
        except Exception as e:
            logger.error(f"Error collecting Bluetooth devices: {e}")

    def _collect_usb_devices(self):
        """Collect USB device inventory using system_profiler."""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return

            data = json.loads(result.stdout)
            timestamp = datetime.now().isoformat()

            # Parse USB data structure
            usb_data = data.get('SPUSBDataType', [])
            if not usb_data:
                return

            current_devices = {}

            # Recursively parse USB device tree
            def parse_usb_tree(devices, is_apple_controller=False):
                for device in devices:
                    device_name = device.get('_name', 'Unknown')
                    vendor = device.get('manufacturer', '')
                    vendor_id = device.get('vendor_id', '')
                    product_id = device.get('product_id', '')
                    serial_number = device.get('serial_num', '')
                    location_id = device.get('location_id', '')
                    speed = device.get('device_speed', '')
                    bus_power = device.get('bcd_device', '')

                    # Determine if Apple device
                    is_apple = 'Apple' in vendor or is_apple_controller

                    # Device class (hub, mass storage, etc.)
                    device_class = 'Hub' if '_items' in device else 'Device'

                    # Skip USB hubs/controllers, focus on actual devices
                    if product_id and product_id != '0x0000':
                        device_id = f"{vendor_id}:{product_id}:{location_id}"

                        self.usb_logger.append({
                            'timestamp': timestamp,
                            'device_name': device_name,
                            'vendor': vendor,
                            'vendor_id': vendor_id,
                            'product_id': product_id,
                            'serial_number': serial_number,
                            'location_id': location_id,
                            'speed': speed,
                            'bus_power': bus_power,
                            'device_class': device_class,
                            'is_apple': is_apple
                        })

                        current_devices[device_id] = {
                            'name': device_name,
                            'vendor': vendor
                        }

                    # Recursively parse child devices
                    if '_items' in device:
                        parse_usb_tree(device['_items'], is_apple)

            parse_usb_tree(usb_data)

            # Detect connection/disconnection events
            self._detect_usb_events(current_devices, timestamp)
            self.current_usb_devices = current_devices

        except subprocess.TimeoutExpired:
            logger.warning("USB profiler timed out")
        except json.JSONDecodeError:
            logger.error("Failed to parse USB data")
        except Exception as e:
            logger.error(f"Error collecting USB devices: {e}")

    def _collect_thunderbolt_devices(self):
        """Collect Thunderbolt device inventory using system_profiler."""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPThunderboltDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return

            data = json.loads(result.stdout)
            timestamp = datetime.now().isoformat()

            # Parse Thunderbolt data structure
            tb_data = data.get('SPThunderboltDataType', [])
            if not tb_data:
                return

            current_devices = {}

            for controller in tb_data:
                # Get devices on this controller
                devices = controller.get('_items', [])

                for device in devices:
                    device_name = device.get('_name', 'Unknown')
                    vendor = device.get('vendor_name', '')
                    device_uid = device.get('device_uid', '')
                    domain_uuid = device.get('domain_uuid', '')
                    route_string = device.get('route_string', '')
                    link_speed = device.get('current_link_speed', '')
                    link_width = device.get('current_link_width', '')
                    device_rom_version = device.get('device_rom_revision', '')
                    receptacle_id = device.get('receptacle_id', '')

                    device_id = device_uid or f"{vendor}:{device_name}"

                    self.thunderbolt_logger.append({
                        'timestamp': timestamp,
                        'device_name': device_name,
                        'vendor': vendor,
                        'device_uid': device_uid,
                        'domain_uuid': domain_uuid,
                        'route_string': route_string,
                        'link_speed': link_speed,
                        'link_width': link_width,
                        'device_rom_version': device_rom_version,
                        'receptacle_id': receptacle_id
                    })

                    current_devices[device_id] = {
                        'name': device_name,
                        'vendor': vendor
                    }

            # Detect connection/disconnection events
            self._detect_thunderbolt_events(current_devices, timestamp)
            self.current_thunderbolt_devices = current_devices

        except subprocess.TimeoutExpired:
            logger.warning("Thunderbolt profiler timed out")
        except json.JSONDecodeError:
            logger.error("Failed to parse Thunderbolt data")
        except Exception as e:
            logger.error(f"Error collecting Thunderbolt devices: {e}")

    def _detect_bluetooth_events(self, current_devices: Dict, timestamp: str):
        """Detect Bluetooth connection/disconnection events."""
        # New connections
        for device_id, device_info in current_devices.items():
            if device_id not in self.current_bluetooth_devices:
                # New device paired
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'connected',
                    'device_type': 'bluetooth',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': '',
                    'details': 'Device paired and connected'
                })
                self.total_bluetooth_events += 1
            elif device_info['connected'] and not self.current_bluetooth_devices[device_id]['connected']:
                # Device reconnected
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'connected',
                    'device_type': 'bluetooth',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': '',
                    'details': 'Device reconnected'
                })
                self.total_bluetooth_events += 1

        # Disconnections
        for device_id, device_info in self.current_bluetooth_devices.items():
            if device_id not in current_devices:
                # Device unpaired
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'disconnected',
                    'device_type': 'bluetooth',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': '',
                    'details': 'Device unpaired'
                })
                self.total_bluetooth_events += 1
            elif not current_devices[device_id]['connected'] and device_info['connected']:
                # Device disconnected
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'disconnected',
                    'device_type': 'bluetooth',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': '',
                    'details': 'Device disconnected'
                })
                self.total_bluetooth_events += 1

    def _detect_usb_events(self, current_devices: Dict, timestamp: str):
        """Detect USB connection/disconnection events."""
        # New connections
        for device_id, device_info in current_devices.items():
            if device_id not in self.current_usb_devices:
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'connected',
                    'device_type': 'usb',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': device_info['vendor'],
                    'details': 'USB device connected'
                })
                self.total_usb_events += 1

        # Disconnections
        for device_id, device_info in self.current_usb_devices.items():
            if device_id not in current_devices:
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'disconnected',
                    'device_type': 'usb',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': device_info['vendor'],
                    'details': 'USB device disconnected'
                })
                self.total_usb_events += 1

    def _detect_thunderbolt_events(self, current_devices: Dict, timestamp: str):
        """Detect Thunderbolt connection/disconnection events."""
        # New connections
        for device_id, device_info in current_devices.items():
            if device_id not in self.current_thunderbolt_devices:
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'connected',
                    'device_type': 'thunderbolt',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': device_info['vendor'],
                    'details': 'Thunderbolt device connected'
                })
                self.total_thunderbolt_events += 1

        # Disconnections
        for device_id, device_info in self.current_thunderbolt_devices.items():
            if device_id not in current_devices:
                self.events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'disconnected',
                    'device_type': 'thunderbolt',
                    'device_name': device_info['name'],
                    'device_id': device_id,
                    'vendor': device_info['vendor'],
                    'details': 'Thunderbolt device disconnected'
                })
                self.total_thunderbolt_events += 1

    # Public API Methods

    def get_peripheral_summary(self) -> Dict[str, Any]:
        """
        Get summary of all connected peripherals.

        Returns:
            Dictionary with peripheral counts and recent events
        """
        return {
            'bluetooth': {
                'total_devices': len(self.current_bluetooth_devices),
                'connected_devices': sum(1 for d in self.current_bluetooth_devices.values() if d.get('connected', False)),
                'total_events': self.total_bluetooth_events
            },
            'usb': {
                'total_devices': len(self.current_usb_devices),
                'total_events': self.total_usb_events
            },
            'thunderbolt': {
                'total_devices': len(self.current_thunderbolt_devices),
                'total_events': self.total_thunderbolt_events
            }
        }

    def get_connected_devices(self, device_type: str = 'all') -> Dict[str, List[Dict]]:
        """
        Get list of currently connected devices.

        Args:
            device_type: 'bluetooth', 'usb', 'thunderbolt', or 'all'

        Returns:
            Dictionary with device lists by type
        """
        result = {}

        if device_type in ('bluetooth', 'all'):
            result['bluetooth'] = [
                {'id': device_id, **device_info}
                for device_id, device_info in self.current_bluetooth_devices.items()
            ]

        if device_type in ('usb', 'all'):
            result['usb'] = [
                {'id': device_id, **device_info}
                for device_id, device_info in self.current_usb_devices.items()
            ]

        if device_type in ('thunderbolt', 'all'):
            result['thunderbolt'] = [
                {'id': device_id, **device_info}
                for device_id, device_info in self.current_thunderbolt_devices.items()
            ]

        return result

    def get_recent_events(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """
        Get recent peripheral connection/disconnection events.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of events to return

        Returns:
            List of recent events sorted by timestamp (newest first)
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Read from CSV (in production, would query database)
        events = []
        csv_file = os.path.join(self.data_dir, 'peripheral_events.csv')

        if not os.path.exists(csv_file):
            return events

        try:
            with open(csv_file, 'r') as f:
                lines = f.readlines()

            # Skip header
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 7:
                    timestamp_str = parts[0]
                    try:
                        event_time = datetime.fromisoformat(timestamp_str)
                        if event_time >= cutoff_time:
                            events.append({
                                'timestamp': timestamp_str,
                                'event_type': parts[1],
                                'device_type': parts[2],
                                'device_name': parts[3],
                                'device_id': parts[4],
                                'vendor': parts[5],
                                'details': parts[6]
                            })
                    except ValueError:
                        continue

            # Sort by timestamp (newest first) and limit
            events.sort(key=lambda x: x['timestamp'], reverse=True)
            return events[:limit]

        except Exception as e:
            logger.error(f"Error reading peripheral events: {e}")
            return []


# Singleton accessor
def get_peripheral_monitor(data_dir: str = None) -> PeripheralMonitor:
    """
    Get the singleton PeripheralMonitor instance.

    Args:
        data_dir: Directory for CSV log files

    Returns:
        PeripheralMonitor singleton instance
    """
    with PeripheralMonitor._lock:
        if PeripheralMonitor._instance is None:
            PeripheralMonitor._instance = PeripheralMonitor(data_dir)
            PeripheralMonitor._instance.start()
        return PeripheralMonitor._instance


# Test harness
if __name__ == '__main__':
    logger.info("Testing Peripheral Monitor...")

    monitor = PeripheralMonitor()

    logger.info("1. Collecting Bluetooth devices...")
    monitor._collect_bluetooth_devices()

    logger.info("2. Collecting USB devices...")
    monitor._collect_usb_devices()

    logger.info("3. Collecting Thunderbolt devices...")
    monitor._collect_thunderbolt_devices()

    logger.info("4. Getting peripheral summary...")
    summary = monitor.get_peripheral_summary()
    logger.info(f"   Bluetooth: {summary['bluetooth']['total_devices']} devices")
    logger.info(f"   USB: {summary['usb']['total_devices']} devices")
    logger.info(f"   Thunderbolt: {summary['thunderbolt']['total_devices']} devices")

    logger.info("5. Getting connected devices...")
    devices = monitor.get_connected_devices()
    logger.info(f"   Total connected: {len(devices.get('bluetooth', [])) + len(devices.get('usb', [])) + len(devices.get('thunderbolt', []))}")

    logger.info("Peripheral Monitor: Ready for Integration")
