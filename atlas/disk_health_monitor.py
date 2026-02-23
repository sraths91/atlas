"""
Disk Health Monitor - SMART data and storage health tracking

Monitors:
- SMART disk health indicators
- Disk I/O latency (read/write performance)
- Filesystem errors and corruption
- SSD wear level (TBW - Total Bytes Written)
- Storage capacity and usage trends
- External drive connections

Enterprise Value:
- Predict disk failures before they occur
- Identify performance degradation
- Proactive disk replacement planning
- Track SSD lifespan and warranty status
"""

import os
import logging
import threading
import time
import subprocess
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import plistlib

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)


class DiskHealthMonitor:
    """Monitor disk health via SMART data and I/O performance"""

    def __init__(self, data_dir: str = None):
        """Initialize disk health monitor

        Args:
            data_dir: Directory for CSV log files
        """
        if data_dir is None:
            data_dir = os.path.expanduser("~/Library/Application Support/AtlasAgent/data")

        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir

        # CSV loggers
        self.smart_logger = CSVLogger(
            os.path.join(data_dir, "disk_smart.csv"),
            fieldnames=[
                'timestamp', 'disk_name', 'disk_model', 'disk_serial',
                'smart_status', 'temperature_c', 'power_on_hours',
                'power_cycle_count', 'reallocated_sectors', 'pending_sectors',
                'uncorrectable_errors', 'wear_leveling_count', 'total_bytes_written_gb',
                'health_percentage'
            ],
            max_history=10000
        )

        self.io_latency_logger = CSVLogger(
            os.path.join(data_dir, "disk_io_latency.csv"),
            fieldnames=[
                'timestamp', 'disk_name', 'read_latency_ms', 'write_latency_ms',
                'read_ops_per_sec', 'write_ops_per_sec', 'queue_depth',
                'read_throughput_mbps', 'write_throughput_mbps'
            ],
            max_history=50000
        )

        self.storage_logger = CSVLogger(
            os.path.join(data_dir, "disk_storage.csv"),
            fieldnames=[
                'timestamp', 'volume_name', 'mount_point', 'filesystem',
                'total_gb', 'used_gb', 'available_gb', 'usage_percent',
                'inode_used', 'inode_total', 'external_drive'
            ],
            max_history=50000
        )

        # Monitoring state
        self._lock = threading.RLock()
        self._running = False
        self._monitor_thread = None

        # Disk tracking
        self._known_disks = set()

        logger.info("Disk Health Monitor initialized")

    def start(self, collection_interval: int = 300):
        """Start background monitoring

        Args:
            collection_interval: Seconds between collections (default: 300 = 5 min)
        """
        with self._lock:
            if self._running:
                logger.warning("Disk health monitor already running")
                return

            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(collection_interval,),
                daemon=True,
                name="DiskHealthMonitor"
            )
            self._monitor_thread.start()
            logger.info(f"Disk health monitor started (interval: {collection_interval}s)")

    def stop(self):
        """Stop background monitoring"""
        with self._lock:
            if not self._running:
                return

            self._running = False
            logger.info("Disk health monitor stopped")

    def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self._running:
            try:
                # Collect SMART data (less frequent)
                self._collect_smart_data()

                # Monitor I/O latency
                self._monitor_io_latency()

                # Track storage usage
                self._monitor_storage()

            except Exception as e:
                logger.error(f"Error in disk health monitor loop: {e}")

            # Sleep until next collection
            time.sleep(interval)

    def _collect_smart_data(self):
        """Collect SMART disk health data"""
        try:
            # Use diskutil to list all disks
            result = subprocess.run(
                ['diskutil', 'list', '-plist'],
                capture_output=True,
                timeout=10
            )

            if result.returncode != 0:
                return

            # Parse plist output
            disk_list = plistlib.loads(result.stdout)
            all_disks = disk_list.get('AllDisksAndPartitions', [])

            current_time = datetime.now().isoformat()

            for disk_info in all_disks:
                disk_identifier = disk_info.get('DeviceIdentifier', '')

                # Only check physical disks (disk0, disk1, etc - not partitions)
                if not re.match(r'^disk\d+$', disk_identifier):
                    continue

                # Get SMART status for this disk
                smart_data = self._get_smart_data(disk_identifier)

                if smart_data:
                    self.smart_logger.append({
                        'timestamp': current_time,
                        'disk_name': disk_identifier,
                        'disk_model': smart_data.get('model', ''),
                        'disk_serial': smart_data.get('serial', ''),
                        'smart_status': smart_data.get('smart_status', 'Unknown'),
                        'temperature_c': smart_data.get('temperature', 0),
                        'power_on_hours': smart_data.get('power_on_hours', 0),
                        'power_cycle_count': smart_data.get('power_cycle_count', 0),
                        'reallocated_sectors': smart_data.get('reallocated_sectors', 0),
                        'pending_sectors': smart_data.get('pending_sectors', 0),
                        'uncorrectable_errors': smart_data.get('uncorrectable_errors', 0),
                        'wear_leveling_count': smart_data.get('wear_leveling', 0),
                        'total_bytes_written_gb': smart_data.get('total_bytes_written_gb', 0),
                        'health_percentage': smart_data.get('health_percentage', 100)
                    })

                    # Log warning if disk health is concerning
                    if smart_data.get('health_percentage', 100) < 80:
                        logger.warning(f"Disk health warning: {disk_identifier} at {smart_data['health_percentage']}%")

        except Exception as e:
            logger.error(f"Error collecting SMART data: {e}")

    def _get_smart_data(self, disk_identifier: str) -> Optional[Dict]:
        """Get SMART data for a specific disk

        Args:
            disk_identifier: Disk identifier (e.g., 'disk0')

        Returns:
            Dict with SMART data, or None if unavailable
        """
        try:
            # Use diskutil info to get disk information
            result = subprocess.run(
                ['diskutil', 'info', '-plist', disk_identifier],
                capture_output=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            disk_info = plistlib.loads(result.stdout)

            # Get SMART status
            smart_status = disk_info.get('SMARTStatus', 'Not Supported')

            # Basic disk info
            smart_data = {
                'model': disk_info.get('MediaName', ''),
                'serial': disk_info.get('VolumeUUID', '')[:16],  # Shortened
                'smart_status': smart_status,
                'temperature': 0,
                'power_on_hours': 0,
                'power_cycle_count': 0,
                'reallocated_sectors': 0,
                'pending_sectors': 0,
                'uncorrectable_errors': 0,
                'wear_leveling': 0,
                'total_bytes_written_gb': 0,
                'health_percentage': 100 if smart_status == 'Verified' else 50
            }

            # Try to get more detailed SMART data using smartctl (if available)
            # Note: smartctl requires smartmontools package: brew install smartmontools
            try:
                smartctl_result = subprocess.run(
                    ['smartctl', '-a', f'/dev/{disk_identifier}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if smartctl_result.returncode in [0, 4]:  # 0 = OK, 4 = SMART OK but some attributes failed
                    output = smartctl_result.stdout

                    # Detect if this is an NVMe drive (Apple Silicon Macs use NVMe)
                    is_nvme = 'NVMe' in output or 'APPLE SSD' in output

                    if is_nvme:
                        # Parse NVMe SMART data format
                        smart_data = self._parse_nvme_smart(output, smart_data)
                    else:
                        # Parse traditional SATA SMART attributes
                        smart_data = self._parse_sata_smart(output, smart_data)

            except FileNotFoundError:
                # smartctl not installed, use basic data only
                logger.debug("smartctl not installed - install with: brew install smartmontools")
            except Exception as e:
                logger.debug(f"Error getting detailed SMART data: {e}")

            return smart_data

        except Exception as e:
            logger.error(f"Error getting SMART data for {disk_identifier}: {e}")
            return None

    def _parse_nvme_smart(self, output: str, smart_data: Dict) -> Dict:
        """Parse NVMe SMART data from smartctl output

        NVMe drives (including Apple Silicon SSDs) use a different format:
        - Temperature: X Celsius
        - Available Spare: X%
        - Percentage Used: X%
        - Data Units Written: X,XXX,XXX [X TB]
        - Power On Hours: XXX
        - Power Cycles: XXX
        - Media and Data Integrity Errors: X

        Args:
            output: Raw smartctl output
            smart_data: Existing smart_data dict to update

        Returns:
            Updated smart_data dict
        """
        # Parse model and serial from NVMe info section
        model_match = re.search(r'Model Number:\s+(.+)', output)
        if model_match:
            smart_data['model'] = model_match.group(1).strip()

        serial_match = re.search(r'Serial Number:\s+(.+)', output)
        if serial_match:
            smart_data['serial'] = serial_match.group(1).strip()[:16]

        # Parse SMART health status
        health_match = re.search(r'SMART overall-health.*?:\s*(\w+)', output, re.IGNORECASE)
        if health_match:
            smart_data['smart_status'] = health_match.group(1)

        # Parse temperature
        temp_match = re.search(r'Temperature:\s+(\d+)\s*Celsius', output)
        if temp_match:
            smart_data['temperature'] = int(temp_match.group(1))

        # Parse power-on hours
        poh_match = re.search(r'Power On Hours:\s+([\d,]+)', output)
        if poh_match:
            smart_data['power_on_hours'] = int(poh_match.group(1).replace(',', ''))

        # Parse power cycles
        pcc_match = re.search(r'Power Cycles:\s+([\d,]+)', output)
        if pcc_match:
            smart_data['power_cycle_count'] = int(pcc_match.group(1).replace(',', ''))

        # Parse unsafe shutdowns (similar to reallocated sectors in concern level)
        unsafe_match = re.search(r'Unsafe Shutdowns:\s+([\d,]+)', output)
        if unsafe_match:
            smart_data['reallocated_sectors'] = int(unsafe_match.group(1).replace(',', ''))

        # Parse media and data integrity errors
        errors_match = re.search(r'Media and Data Integrity Errors:\s+([\d,]+)', output)
        if errors_match:
            smart_data['uncorrectable_errors'] = int(errors_match.group(1).replace(',', ''))

        # Parse percentage used (NVMe wear indicator - 100% = worn out)
        percentage_used_match = re.search(r'Percentage Used:\s+(\d+)%', output)
        if percentage_used_match:
            percentage_used = int(percentage_used_match.group(1))
            # Convert to wear leveling count (100 = new, 0 = worn out)
            smart_data['wear_leveling'] = max(0, 100 - percentage_used)

        # Parse available spare (NVMe health indicator)
        spare_match = re.search(r'Available Spare:\s+(\d+)%', output)
        available_spare = 100
        if spare_match:
            available_spare = int(spare_match.group(1))

        # Parse data units written and convert to GB
        # Format: "Data Units Written: 52,154,236 [26.7 TB]"
        tbw_match = re.search(r'Data Units Written:\s+([\d,]+)(?:\s*\[([\d.]+)\s*(TB|GB|PB)\])?', output)
        if tbw_match:
            data_units = int(tbw_match.group(1).replace(',', ''))
            # Each data unit is 512KB (1000 * 512 bytes per NVMe spec)
            smart_data['total_bytes_written_gb'] = round((data_units * 512 * 1000) / (1024**3), 2)

        # Calculate health percentage for NVMe
        health_score = 100

        # Deduct for percentage used (primary wear indicator)
        if smart_data.get('wear_leveling', 100) < 100:
            # wear_leveling is already 100 - percentage_used
            health_score = min(health_score, smart_data['wear_leveling'])

        # Deduct for low available spare
        if available_spare < 100:
            if available_spare < 10:
                health_score -= 30
            elif available_spare < 50:
                health_score -= 15

        # Deduct for media errors (critical)
        if smart_data.get('uncorrectable_errors', 0) > 0:
            health_score -= min(50, smart_data['uncorrectable_errors'] * 20)

        # Deduct for excessive unsafe shutdowns
        unsafe_shutdowns = smart_data.get('reallocated_sectors', 0)
        if unsafe_shutdowns > 50:
            health_score -= min(10, (unsafe_shutdowns - 50) // 10)

        smart_data['health_percentage'] = max(0, health_score)

        return smart_data

    def _parse_sata_smart(self, output: str, smart_data: Dict) -> Dict:
        """Parse traditional SATA SMART attributes from smartctl output

        SATA drives use attribute tables like:
        - 194 Temperature_Celsius
        - 9 Power_On_Hours
        - 12 Power_Cycle_Count
        - 5 Reallocated_Sector_Ct
        - 197 Current_Pending_Sector
        - 198 Offline_Uncorrectable

        Args:
            output: Raw smartctl output
            smart_data: Existing smart_data dict to update

        Returns:
            Updated smart_data dict
        """
        # Parse temperature
        temp_match = re.search(r'(?:194|Temperature).*?(\d+)\s*(?:Celsius|\(.*C.*\))', output, re.IGNORECASE)
        if temp_match:
            smart_data['temperature'] = int(temp_match.group(1))

        # Parse power-on hours
        poh_match = re.search(r'(?:9\s+)?Power_On_Hours.*?(\d+)', output)
        if poh_match:
            smart_data['power_on_hours'] = int(poh_match.group(1))

        # Parse power cycle count
        pcc_match = re.search(r'(?:12\s+)?Power_Cycle_Count.*?(\d+)', output)
        if pcc_match:
            smart_data['power_cycle_count'] = int(pcc_match.group(1))

        # Parse reallocated sectors
        reallocated_match = re.search(r'(?:5\s+)?Reallocated_Sector_Ct.*?(\d+)\s*$', output, re.MULTILINE)
        if reallocated_match:
            smart_data['reallocated_sectors'] = int(reallocated_match.group(1))

        # Parse pending sectors
        pending_match = re.search(r'(?:197\s+)?Current_Pending_Sector.*?(\d+)\s*$', output, re.MULTILINE)
        if pending_match:
            smart_data['pending_sectors'] = int(pending_match.group(1))

        # Parse uncorrectable errors
        uncorrectable_match = re.search(r'(?:198\s+)?(?:Offline_Uncorrectable|Reported_Uncorrect).*?(\d+)\s*$', output, re.MULTILINE)
        if uncorrectable_match:
            smart_data['uncorrectable_errors'] = int(uncorrectable_match.group(1))

        # SSD-specific: Wear leveling
        wear_match = re.search(r'(?:177\s+)?Wear_Leveling_Count.*?(\d+)\s*$', output, re.MULTILINE)
        if wear_match:
            smart_data['wear_leveling'] = int(wear_match.group(1))

        # SSD-specific: Total bytes written (LBAs)
        tbw_match = re.search(r'(?:241\s+)?Total_LBAs_Written.*?(\d+)', output)
        if tbw_match:
            # Convert LBAs to GB (assuming 512 bytes per LBA)
            lbas = int(tbw_match.group(1))
            smart_data['total_bytes_written_gb'] = round((lbas * 512) / (1024**3), 2)

        # Calculate health percentage for SATA
        health_score = 100

        # Deduct for reallocated sectors
        if smart_data.get('reallocated_sectors', 0) > 0:
            health_score -= min(20, smart_data['reallocated_sectors'] * 2)

        # Deduct for pending sectors
        if smart_data.get('pending_sectors', 0) > 0:
            health_score -= min(30, smart_data['pending_sectors'] * 5)

        # Deduct for uncorrectable errors
        if smart_data.get('uncorrectable_errors', 0) > 0:
            health_score -= min(50, smart_data['uncorrectable_errors'] * 10)

        # SSD wear (100 = new, 0 = worn out)
        if smart_data.get('wear_leveling', 0) > 0:
            health_score = min(health_score, smart_data['wear_leveling'])

        smart_data['health_percentage'] = max(0, health_score)

        return smart_data

    def _monitor_io_latency(self):
        """Monitor disk I/O latency and throughput"""
        try:
            # Use iostat to get I/O statistics
            result = subprocess.run(
                ['iostat', '-d', '-c', '2', '-w', '1'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return

            current_time = datetime.now().isoformat()
            lines = result.stdout.strip().split('\n')

            # Parse iostat output
            # Format varies, but typically: disk KB/t  tps  MB/s
            for line in lines:
                if line.startswith('disk'):
                    try:
                        parts = line.split()
                        if len(parts) < 4:
                            continue

                        disk_name = parts[0]
                        kb_per_transfer = float(parts[1])
                        transfers_per_sec = float(parts[2])
                        mb_per_sec = float(parts[3])

                        # Estimate latency (very rough approximation)
                        # Average latency ≈ 1 / transfers_per_sec (in seconds)
                        avg_latency_ms = (1000 / transfers_per_sec) if transfers_per_sec > 0 else 0

                        # Split read/write (iostat doesn't separate, so estimate 50/50)
                        read_latency = write_latency = avg_latency_ms / 2
                        read_ops = write_ops = transfers_per_sec / 2
                        read_throughput = write_throughput = mb_per_sec / 2

                        self.io_latency_logger.append({
                            'timestamp': current_time,
                            'disk_name': disk_name,
                            'read_latency_ms': round(read_latency, 2),
                            'write_latency_ms': round(write_latency, 2),
                            'read_ops_per_sec': round(read_ops, 2),
                            'write_ops_per_sec': round(write_ops, 2),
                            'queue_depth': 0,  # Not available from iostat
                            'read_throughput_mbps': round(read_throughput, 2),
                            'write_throughput_mbps': round(write_throughput, 2)
                        })

                    except (ValueError, IndexError):
                        continue

        except Exception as e:
            logger.error(f"Error monitoring I/O latency: {e}")

    def _monitor_storage(self):
        """Monitor storage capacity and usage"""
        try:
            # Use df to get filesystem usage
            result = subprocess.run(
                ['df', '-H'],  # -H for human-readable in GB
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return

            current_time = datetime.now().isoformat()
            lines = result.stdout.strip().split('\n')[1:]  # Skip header

            for line in lines:
                try:
                    parts = line.split()
                    if len(parts) < 9:
                        continue

                    filesystem = parts[0]
                    total_size = parts[1]
                    used = parts[2]
                    available = parts[3]
                    usage_percent = parts[4].replace('%', '')
                    mount_point = parts[8]

                    # Skip special filesystems
                    if filesystem.startswith('/dev/null') or filesystem.startswith('map'):
                        continue

                    # Determine if external drive
                    is_external = '/Volumes/' in mount_point and mount_point != '/Volumes'

                    # Extract volume name
                    if mount_point == '/':
                        volume_name = 'Macintosh HD'
                    elif mount_point.startswith('/Volumes/'):
                        volume_name = mount_point.replace('/Volumes/', '')
                    else:
                        volume_name = os.path.basename(mount_point)

                    # Convert sizes to GB (remove unit suffix)
                    def size_to_gb(size_str):
                        size_str = size_str.upper()
                        if 'T' in size_str:
                            return float(size_str.replace('T', '')) * 1024
                        elif 'G' in size_str:
                            return float(size_str.replace('G', ''))
                        elif 'M' in size_str:
                            return float(size_str.replace('M', '')) / 1024
                        else:
                            return float(size_str.replace('K', '')) / (1024 * 1024)

                    total_gb = size_to_gb(total_size)
                    used_gb = size_to_gb(used)
                    available_gb = size_to_gb(available)

                    self.storage_logger.append({
                        'timestamp': current_time,
                        'volume_name': volume_name,
                        'mount_point': mount_point,
                        'filesystem': filesystem,
                        'total_gb': round(total_gb, 2),
                        'used_gb': round(used_gb, 2),
                        'available_gb': round(available_gb, 2),
                        'usage_percent': float(usage_percent),
                        'inode_used': 0,  # Would need separate df -i call
                        'inode_total': 0,
                        'external_drive': is_external
                    })

                    # Warn if usage > 90%
                    if float(usage_percent) > 90:
                        logger.warning(f"Disk space warning: {volume_name} at {usage_percent}% capacity")

                except (ValueError, IndexError):
                    continue

        except Exception as e:
            logger.error(f"Error monitoring storage: {e}")

    def get_disk_health_summary(self) -> Dict:
        """Get summary of disk health status

        Returns:
            Dict with disk health summary
        """
        try:
            recent_smart = self.smart_logger.get_history()[-10:]  # Last 10 samples

            if not recent_smart:
                return {
                    'disks_monitored': 0,
                    'healthy_disks': 0,
                    'warning_disks': 0,
                    'failing_disks': 0,
                    'avg_health_percentage': 0,
                    'disks': []
                }

            # Aggregate by disk
            disk_health = {}
            for entry in recent_smart:
                disk_name = entry.get('disk_name', '')
                health = float(entry.get('health_percentage', 100))

                if disk_name not in disk_health:
                    disk_health[disk_name] = []
                disk_health[disk_name].append(health)

            # Calculate averages
            disks = []
            healthy = 0
            warning = 0
            failing = 0

            for disk_name, health_values in disk_health.items():
                avg_health = sum(health_values) / len(health_values)

                status = 'Healthy'
                if avg_health < 50:
                    status = 'Failing'
                    failing += 1
                elif avg_health < 80:
                    status = 'Warning'
                    warning += 1
                else:
                    healthy += 1

                disks.append({
                    'disk_name': disk_name,
                    'health_percentage': round(avg_health, 1),
                    'status': status
                })

            overall_health = sum(d['health_percentage'] for d in disks) / len(disks) if disks else 0

            return {
                'disks_monitored': len(disks),
                'healthy_disks': healthy,
                'warning_disks': warning,
                'failing_disks': failing,
                'avg_health_percentage': round(overall_health, 1),
                'disks': disks
            }

        except Exception as e:
            logger.error(f"Error getting disk health summary: {e}")
            return {
                'disks_monitored': 0,
                'healthy_disks': 0,
                'warning_disks': 0,
                'failing_disks': 0,
                'avg_health_percentage': 0,
                'disks': []
            }

    def get_storage_summary(self) -> Dict:
        """Get summary of storage usage

        Returns:
            Dict with storage summary
        """
        try:
            recent_storage = self.storage_logger.get_history()[-20:]  # Last 20 samples

            if not recent_storage:
                return {
                    'volumes': 0,
                    'total_capacity_gb': 0,
                    'total_used_gb': 0,
                    'total_available_gb': 0,
                    'avg_usage_percent': 0,
                    'external_drives': 0
                }

            # Aggregate by volume (latest entry per volume)
            volumes = {}
            for entry in recent_storage:
                volume_name = entry.get('volume_name', '')
                volumes[volume_name] = entry

            total_capacity = sum(float(v.get('total_gb', 0)) for v in volumes.values())
            total_used = sum(float(v.get('used_gb', 0)) for v in volumes.values())
            total_available = sum(float(v.get('available_gb', 0)) for v in volumes.values())

            avg_usage = (total_used / total_capacity * 100) if total_capacity > 0 else 0

            external_count = sum(1 for v in volumes.values() if v.get('external_drive'))

            return {
                'volumes': len(volumes),
                'total_capacity_gb': round(total_capacity, 2),
                'total_used_gb': round(total_used, 2),
                'total_available_gb': round(total_available, 2),
                'avg_usage_percent': round(avg_usage, 1),
                'external_drives': external_count
            }

        except Exception as e:
            logger.error(f"Error getting storage summary: {e}")
            return {
                'volumes': 0,
                'total_capacity_gb': 0,
                'total_used_gb': 0,
                'total_available_gb': 0,
                'avg_usage_percent': 0,
                'external_drives': 0
            }

    def get_detailed_disk_status(self) -> Dict:
        """Get detailed SMART status for all disks (live data)

        This method fetches fresh SMART data directly for API responses,
        bypassing the CSV history for real-time accuracy.

        Returns:
            Dict with detailed disk status including SMART attributes
        """
        try:
            logger.info("get_detailed_disk_status called")
            # Use diskutil to list all disks
            result = subprocess.run(
                ['diskutil', 'list', '-plist'],
                capture_output=True,
                timeout=10
            )
            logger.info(f"diskutil returned code {result.returncode}")

            if result.returncode != 0:
                return {'error': 'Failed to list disks', 'disks': []}

            disk_list = plistlib.loads(result.stdout)
            all_disks = disk_list.get('AllDisksAndPartitions', [])

            disks = []
            smartctl_available = True
            seen_serials = set()  # Track seen serials to avoid duplicate physical disks

            for disk_info in all_disks:
                disk_identifier = disk_info.get('DeviceIdentifier', '')

                # Only check physical disks (disk0, disk1, etc - not partitions)
                if not re.match(r'^disk\d+$', disk_identifier):
                    continue

                # Check if this is a physical disk vs synthesized (APFS container)
                # Synthesized disks point to the same physical storage
                disk_content = disk_info.get('Content', '')
                is_physical = disk_content in ['GUID_partition_scheme', 'FDisk_partition_scheme', 'Apple_partition_scheme', '']

                # Skip synthesized disks (APFS containers, etc) - they share the same physical drive
                if not is_physical and 'synthesized' in str(disk_info).lower():
                    continue

                # Get SMART status for this disk
                smart_data = self._get_smart_data(disk_identifier)

                if not smart_data:
                    logger.debug(f"Disk {disk_identifier}: No SMART data returned")
                    continue

                # Skip disks without valid SMART data (likely synthesized containers)
                # Physical disks should have temperature or power_on_hours from smartctl
                temp = smart_data.get('temperature', 0)
                poh = smart_data.get('power_on_hours', 0)
                serial = smart_data.get('serial', '')
                has_valid_smart = temp > 0 or poh > 0 or bool(serial)

                logger.debug(f"Disk {disk_identifier}: temp={temp}, poh={poh}, serial={serial}, valid={has_valid_smart}")

                if not has_valid_smart:
                    continue

                # Skip if we've already seen this serial (duplicate physical disk entry)
                serial = smart_data.get('serial', '')
                if serial:
                    if serial in seen_serials:
                        continue
                    seen_serials.add(serial)

                if smart_data:
                    # Check if smartctl is available based on temperature data
                    if smart_data.get('temperature', 0) == 0 and smartctl_available:
                        # Check if smartctl is actually installed
                        try:
                            subprocess.run(['which', 'smartctl'], capture_output=True, timeout=2)
                        except (subprocess.SubprocessError, OSError):
                            smartctl_available = False

                    disk_status = {
                        'disk_identifier': disk_identifier,
                        'model': smart_data.get('model', 'Unknown'),
                        'serial': smart_data.get('serial', ''),
                        'smart_status': smart_data.get('smart_status', 'Unknown'),
                        'health_percentage': smart_data.get('health_percentage', 100),
                        'temperature_c': smart_data.get('temperature', 0),
                        'power_on_hours': smart_data.get('power_on_hours', 0),
                        'power_cycle_count': smart_data.get('power_cycle_count', 0),
                        'total_bytes_written_gb': smart_data.get('total_bytes_written_gb', 0),
                        'wear_leveling': smart_data.get('wear_leveling', 100),
                        'unsafe_shutdowns': smart_data.get('reallocated_sectors', 0),
                        'media_errors': smart_data.get('uncorrectable_errors', 0),
                    }

                    # Determine health status label
                    health = disk_status['health_percentage']
                    if health >= 90:
                        disk_status['health_label'] = 'Excellent'
                    elif health >= 80:
                        disk_status['health_label'] = 'Good'
                    elif health >= 60:
                        disk_status['health_label'] = 'Fair'
                    elif health >= 40:
                        disk_status['health_label'] = 'Poor'
                    else:
                        disk_status['health_label'] = 'Critical'

                    disks.append(disk_status)

            return {
                'disks': disks,
                'smartctl_available': smartctl_available,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting detailed disk status: {e}")
            return {'error': str(e), 'disks': []}


# Singleton instance
_disk_monitor_instance = None
_disk_monitor_lock = threading.Lock()


def get_disk_monitor() -> DiskHealthMonitor:
    """Get singleton disk health monitor instance

    Returns:
        DiskHealthMonitor instance
    """
    global _disk_monitor_instance

    if _disk_monitor_instance is None:
        with _disk_monitor_lock:
            if _disk_monitor_instance is None:
                _disk_monitor_instance = DiskHealthMonitor()
                _disk_monitor_instance.start(collection_interval=300)  # 5 minutes

    return _disk_monitor_instance


# Export
__all__ = ['DiskHealthMonitor', 'get_disk_monitor']
