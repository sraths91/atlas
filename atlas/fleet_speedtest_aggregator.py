"""
Fleet Speed Test Aggregator - Collects and analyzes speed test data from all machines
"""
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class SpeedTestAggregator:
    """Aggregates and analyzes speed test data from fleet machines"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize speed test aggregator
        
        Args:
            db_path: Path to SQLite database (defaults to ~/.fleet-data/speedtest.sqlite3)
        """
        if db_path is None:
            db_path = str(Path.home() / '.fleet-data' / 'speedtest.sqlite3')
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"Speed test aggregator initialized with database: {db_path}")
    
    def _init_database(self):
        """Initialize database schema for speed test storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create speed test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS speedtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                download_mbps REAL,
                upload_mbps REAL,
                ping_ms REAL,
                jitter_ms REAL,
                packet_loss REAL,
                server_name TEXT,
                server_location TEXT,
                isp TEXT,
                external_ip TEXT,
                result_url TEXT,
                test_duration_seconds REAL,
                raw_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_machine_timestamp 
            ON speedtest_results(machine_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON speedtest_results(timestamp)
        """)
        
        # Create aggregated statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS speedtest_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                period TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                test_count INTEGER,
                avg_download_mbps REAL,
                avg_upload_mbps REAL,
                avg_ping_ms REAL,
                min_download_mbps REAL,
                max_download_mbps REAL,
                min_upload_mbps REAL,
                max_upload_mbps REAL,
                min_ping_ms REAL,
                max_ping_ms REAL,
                median_download_mbps REAL,
                median_upload_mbps REAL,
                median_ping_ms REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(machine_id, period, period_start)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Speed test database schema initialized")
    
    def store_speedtest_result(self, machine_id: str, result: Dict[str, Any]) -> bool:
        """
        Store a speed test result
        
        Args:
            machine_id: Machine identifier
            result: Speed test result dictionary
            
        Returns:
            True if stored successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract fields from result - support both flat format (from agent monitor)
            # and Ookla nested format (from speedtest-cli JSON)
            timestamp = result.get('timestamp', datetime.now().isoformat())

            dl = result.get('download', 0)
            ul = result.get('upload', 0)
            pg = result.get('ping', 0)

            if isinstance(dl, dict):
                # Ookla nested format: {'download': {'bandwidth': bits/s}, ...}
                download_mbps = dl.get('bandwidth', 0) / 125000
                upload_mbps = ul.get('bandwidth', 0) if isinstance(ul, dict) else 0
                if isinstance(ul, dict):
                    upload_mbps = ul.get('bandwidth', 0) / 125000
                ping_ms = pg.get('latency', 0) if isinstance(pg, dict) else 0
                jitter_ms = pg.get('jitter', 0) if isinstance(pg, dict) else 0
            else:
                # Flat format from agent: {'download': 501.84, 'upload': 19.04, 'ping': 5.3, ...}
                download_mbps = float(dl) if dl else 0
                upload_mbps = float(ul) if ul else 0
                ping_ms = float(pg) if pg else 0
                jitter_ms = float(result.get('jitter', 0))

            packet_loss = result.get('packetLoss', result.get('packet_loss', 0))

            server = result.get('server', '')
            if isinstance(server, dict):
                server_name = server.get('name', '')
                server_location = f"{server.get('location', '')}, {server.get('country', '')}"
            else:
                server_name = str(server)
                server_location = ''

            isp = result.get('isp', '')
            external_ip = ''
            if isinstance(result.get('interface'), dict):
                external_ip = result['interface'].get('externalIp', '')
            result_url = ''
            if isinstance(result.get('result'), dict):
                result_url = result['result'].get('url', '')

            # Calculate test duration
            test_duration = 0
            if isinstance(result.get('download'), dict) and 'elapsed' in result['download']:
                test_duration += result['download']['elapsed'] / 1000
            if isinstance(result.get('upload'), dict) and 'elapsed' in result['upload']:
                test_duration += result['upload']['elapsed'] / 1000
            
            cursor.execute("""
                INSERT INTO speedtest_results (
                    machine_id, timestamp, download_mbps, upload_mbps, ping_ms,
                    jitter_ms, packet_loss, server_name, server_location, isp,
                    external_ip, result_url, test_duration_seconds, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                machine_id, timestamp, download_mbps, upload_mbps, ping_ms,
                jitter_ms, packet_loss, server_name, server_location, isp,
                external_ip, result_url, test_duration, json.dumps(result)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored speed test result for {machine_id}: {download_mbps:.1f}/{upload_mbps:.1f} Mbps")
            return True
            
        except Exception as e:
            logger.error(f"Error storing speed test result: {e}")
            return False
    
    def get_recent_results(self, machine_id: Optional[str] = None, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent speed test results
        
        Args:
            machine_id: Optional machine filter
            hours: Number of hours to look back
            limit: Maximum number of results
            
        Returns:
            List of speed test results
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            if machine_id:
                cursor.execute("""
                    SELECT * FROM speedtest_results
                    WHERE machine_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (machine_id, cutoff_time, limit))
            else:
                cursor.execute("""
                    SELECT * FROM speedtest_results
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (cutoff_time, limit))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                results.append(result)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error getting recent results: {e}")
            return []
    
    def get_recent_20_average(self, machine_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get average of most recent 20 tests per machine
        
        Args:
            machine_id: Optional specific machine, or None for all machines
            
        Returns:
            Dictionary with averages per machine
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if machine_id:
                # Single machine
                cursor.execute("""
                    SELECT download_mbps, upload_mbps, ping_ms, jitter_ms, packet_loss
                    FROM speedtest_results
                    WHERE machine_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                """, (machine_id,))
                
                results = cursor.fetchall()
                
                if not results:
                    conn.close()
                    return {'error': f'No data for machine {machine_id}'}
                
                downloads = [r[0] for r in results if r[0] is not None]
                uploads = [r[1] for r in results if r[1] is not None]
                pings = [r[2] for r in results if r[2] is not None]
                jitters = [r[3] for r in results if r[3] is not None]
                packet_losses = [r[4] for r in results if r[4] is not None]
                
                conn.close()
                
                return {
                    'machine_id': machine_id,
                    'test_count': len(results),
                    'avg_download_mbps': round(statistics.mean(downloads), 2) if downloads else 0,
                    'avg_upload_mbps': round(statistics.mean(uploads), 2) if uploads else 0,
                    'avg_ping_ms': round(statistics.mean(pings), 2) if pings else 0,
                    'avg_jitter_ms': round(statistics.mean(jitters), 2) if jitters else 0,
                    'avg_packet_loss': round(statistics.mean(packet_losses), 2) if packet_losses else 0,
                }
            else:
                # All machines
                cursor.execute("SELECT DISTINCT machine_id FROM speedtest_results")
                machines = [row[0] for row in cursor.fetchall()]
                
                results = {}
                for mid in machines:
                    cursor.execute("""
                        SELECT download_mbps, upload_mbps, ping_ms, jitter_ms, packet_loss
                        FROM speedtest_results
                        WHERE machine_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 20
                    """, (mid,))
                    
                    tests = cursor.fetchall()
                    
                    if tests:
                        downloads = [r[0] for r in tests if r[0] is not None]
                        uploads = [r[1] for r in tests if r[1] is not None]
                        pings = [r[2] for r in tests if r[2] is not None]
                        jitters = [r[3] for r in tests if r[3] is not None]
                        packet_losses = [r[4] for r in tests if r[4] is not None]
                        
                        results[mid] = {
                            'test_count': len(tests),
                            'avg_download_mbps': round(statistics.mean(downloads), 2) if downloads else 0,
                            'avg_upload_mbps': round(statistics.mean(uploads), 2) if uploads else 0,
                            'avg_ping_ms': round(statistics.mean(pings), 2) if pings else 0,
                            'avg_jitter_ms': round(statistics.mean(jitters), 2) if jitters else 0,
                            'avg_packet_loss': round(statistics.mean(packet_losses), 2) if packet_losses else 0,
                        }
                
                conn.close()
                return results
                
        except Exception as e:
            logger.error(f"Error getting recent 20 average: {e}")
            return {}
    
    def get_subnet_analysis(self, subnet: str = None) -> Dict[str, Any]:
        """
        Analyze speed tests by IP subnet
        
        Args:
            subnet: IP subnet in CIDR notation (e.g., '192.168.1.0/24') or None for all
            
        Returns:
            Statistics grouped by subnet
        """
        try:
            import ipaddress
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all unique external IPs with their test data
            cursor.execute("""
                SELECT external_ip, machine_id, download_mbps, upload_mbps, ping_ms
                FROM speedtest_results
                WHERE external_ip IS NOT NULL AND external_ip != ''
                ORDER BY timestamp DESC
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return {'error': 'No IP data available'}
            
            # Group by subnet
            subnet_data = defaultdict(lambda: {
                'machines': set(),
                'ips': set(),
                'downloads': [],
                'uploads': [],
                'pings': [],
                'test_count': 0
            })
            
            for external_ip, machine_id, download, upload, ping in results:
                try:
                    ip = ipaddress.ip_address(external_ip)
                    
                    # If specific subnet requested, filter
                    if subnet:
                        network = ipaddress.ip_network(subnet, strict=False)
                        if ip not in network:
                            continue
                        subnet_key = subnet
                    else:
                        # Auto-detect subnet (assume /24 for IPv4, /64 for IPv6)
                        if ip.version == 4:
                            network = ipaddress.ip_network(f"{ip}/24", strict=False)
                        else:
                            network = ipaddress.ip_network(f"{ip}/64", strict=False)
                        subnet_key = str(network)
                    
                    subnet_data[subnet_key]['machines'].add(machine_id)
                    subnet_data[subnet_key]['ips'].add(external_ip)
                    if download:
                        subnet_data[subnet_key]['downloads'].append(download)
                    if upload:
                        subnet_data[subnet_key]['uploads'].append(upload)
                    if ping:
                        subnet_data[subnet_key]['pings'].append(ping)
                    subnet_data[subnet_key]['test_count'] += 1
                    
                except (ValueError, ipaddress.AddressValueError) as e:
                    logger.debug(f"Invalid IP address {external_ip}: {e}")
                    continue
            
            # Calculate statistics for each subnet
            analysis = {}
            for subnet_key, data in subnet_data.items():
                analysis[subnet_key] = {
                    'machine_count': len(data['machines']),
                    'machines': sorted(list(data['machines'])),
                    'ip_count': len(data['ips']),
                    'ips': sorted(list(data['ips'])),
                    'test_count': data['test_count'],
                    'avg_download_mbps': round(statistics.mean(data['downloads']), 2) if data['downloads'] else 0,
                    'avg_upload_mbps': round(statistics.mean(data['uploads']), 2) if data['uploads'] else 0,
                    'avg_ping_ms': round(statistics.mean(data['pings']), 2) if data['pings'] else 0,
                    'min_download_mbps': round(min(data['downloads']), 2) if data['downloads'] else 0,
                    'max_download_mbps': round(max(data['downloads']), 2) if data['downloads'] else 0,
                }
            
            return {
                'subnets': analysis,
                'total_subnets': len(analysis),
                'total_tests': sum(d['test_count'] for d in analysis.values())
            }
            
        except Exception as e:
            logger.error(f"Error analyzing subnets: {e}")
            return {'error': str(e)}
    
    def get_fleet_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get fleet-wide speed test summary
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Summary statistics for entire fleet
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Get overall statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as test_count,
                    COUNT(DISTINCT machine_id) as machine_count,
                    AVG(download_mbps) as avg_download,
                    AVG(upload_mbps) as avg_upload,
                    AVG(ping_ms) as avg_ping,
                    MIN(download_mbps) as min_download,
                    MAX(download_mbps) as max_download,
                    MIN(upload_mbps) as min_upload,
                    MAX(upload_mbps) as max_upload,
                    MIN(ping_ms) as min_ping,
                    MAX(ping_ms) as max_ping
                FROM speedtest_results
                WHERE timestamp > ?
            """, (cutoff_time,))
            
            row = cursor.fetchone()
            
            summary = {
                'period_hours': hours,
                'test_count': row[0] or 0,
                'machine_count': row[1] or 0,
                'avg_download_mbps': round(row[2], 2) if row[2] else 0,
                'avg_upload_mbps': round(row[3], 2) if row[3] else 0,
                'avg_ping_ms': round(row[4], 2) if row[4] else 0,
                'min_download_mbps': round(row[5], 2) if row[5] else 0,
                'max_download_mbps': round(row[6], 2) if row[6] else 0,
                'min_upload_mbps': round(row[7], 2) if row[7] else 0,
                'max_upload_mbps': round(row[8], 2) if row[8] else 0,
                'min_ping_ms': round(row[9], 2) if row[9] else 0,
                'max_ping_ms': round(row[10], 2) if row[10] else 0,
            }
            
            # Get per-machine statistics
            cursor.execute("""
                SELECT 
                    machine_id,
                    COUNT(*) as test_count,
                    AVG(download_mbps) as avg_download,
                    AVG(upload_mbps) as avg_upload,
                    AVG(ping_ms) as avg_ping,
                    MAX(timestamp) as last_test
                FROM speedtest_results
                WHERE timestamp > ?
                GROUP BY machine_id
                ORDER BY avg_download DESC
            """, (cutoff_time,))
            
            machines = []
            for row in cursor.fetchall():
                machines.append({
                    'machine_id': row[0],
                    'test_count': row[1],
                    'avg_download_mbps': round(row[2], 2),
                    'avg_upload_mbps': round(row[3], 2),
                    'avg_ping_ms': round(row[4], 2),
                    'last_test': row[5]
                })
            
            summary['machines'] = machines
            
            conn.close()
            return summary
            
        except Exception as e:
            logger.error(f"Error getting fleet summary: {e}")
            return {}
    
    def get_machine_stats(self, machine_id: str, hours: int = 168) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific machine
        
        Args:
            machine_id: Machine identifier
            hours: Number of hours to analyze (default 7 days)
            
        Returns:
            Detailed statistics for the machine
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Get all results for this machine
            cursor.execute("""
                SELECT download_mbps, upload_mbps, ping_ms, jitter_ms, packet_loss, timestamp
                FROM speedtest_results
                WHERE machine_id = ? AND timestamp > ?
                ORDER BY timestamp ASC
            """, (machine_id, cutoff_time))
            
            results = cursor.fetchall()
            
            if not results:
                conn.close()
                return {'error': 'No data found for this machine'}
            
            downloads = [r[0] for r in results if r[0] is not None]
            uploads = [r[1] for r in results if r[1] is not None]
            pings = [r[2] for r in results if r[2] is not None]
            jitters = [r[3] for r in results if r[3] is not None]
            packet_losses = [r[4] for r in results if r[4] is not None]
            
            stats = {
                'machine_id': machine_id,
                'period_hours': hours,
                'test_count': len(results),
                'first_test': results[0][5],
                'last_test': results[-1][5],
                'download': {
                    'avg': round(statistics.mean(downloads), 2) if downloads else 0,
                    'median': round(statistics.median(downloads), 2) if downloads else 0,
                    'min': round(min(downloads), 2) if downloads else 0,
                    'max': round(max(downloads), 2) if downloads else 0,
                    'stdev': round(statistics.stdev(downloads), 2) if len(downloads) > 1 else 0,
                },
                'upload': {
                    'avg': round(statistics.mean(uploads), 2) if uploads else 0,
                    'median': round(statistics.median(uploads), 2) if uploads else 0,
                    'min': round(min(uploads), 2) if uploads else 0,
                    'max': round(max(uploads), 2) if uploads else 0,
                    'stdev': round(statistics.stdev(uploads), 2) if len(uploads) > 1 else 0,
                },
                'ping': {
                    'avg': round(statistics.mean(pings), 2) if pings else 0,
                    'median': round(statistics.median(pings), 2) if pings else 0,
                    'min': round(min(pings), 2) if pings else 0,
                    'max': round(max(pings), 2) if pings else 0,
                    'stdev': round(statistics.stdev(pings), 2) if len(pings) > 1 else 0,
                },
                'jitter': {
                    'avg': round(statistics.mean(jitters), 2) if jitters else 0,
                    'max': round(max(jitters), 2) if jitters else 0,
                },
                'packet_loss': {
                    'avg': round(statistics.mean(packet_losses), 2) if packet_losses else 0,
                    'max': round(max(packet_losses), 2) if packet_losses else 0,
                }
            }
            
            # Get time series data for charting
            time_series = []
            for r in results:
                time_series.append({
                    'timestamp': r[5],
                    'download': round(r[0], 2) if r[0] else 0,
                    'upload': round(r[1], 2) if r[1] else 0,
                    'ping': round(r[2], 2) if r[2] else 0,
                })
            
            stats['time_series'] = time_series
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting machine stats: {e}")
            return {'error': str(e)}
    
    def get_comparison_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get comparison report across all machines
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Comparison data for all machines
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute("""
                SELECT 
                    machine_id,
                    AVG(download_mbps) as avg_download,
                    AVG(upload_mbps) as avg_upload,
                    AVG(ping_ms) as avg_ping,
                    MIN(download_mbps) as min_download,
                    MAX(download_mbps) as max_download,
                    COUNT(*) as test_count
                FROM speedtest_results
                WHERE timestamp > ?
                GROUP BY machine_id
                ORDER BY avg_download DESC
            """, (cutoff_time,))
            
            machines = []
            for row in cursor.fetchall():
                machines.append({
                    'machine_id': row[0],
                    'avg_download': round(row[1], 2),
                    'avg_upload': round(row[2], 2),
                    'avg_ping': round(row[3], 2),
                    'min_download': round(row[4], 2),
                    'max_download': round(row[5], 2),
                    'test_count': row[6],
                    'variability': round(row[5] - row[4], 2),  # Range
                })
            
            # Calculate fleet averages for comparison
            if machines:
                fleet_avg_download = statistics.mean([m['avg_download'] for m in machines])
                fleet_avg_upload = statistics.mean([m['avg_upload'] for m in machines])
                fleet_avg_ping = statistics.mean([m['avg_ping'] for m in machines])
                
                # Add performance rating
                for machine in machines:
                    machine['download_vs_fleet'] = round(
                        ((machine['avg_download'] - fleet_avg_download) / fleet_avg_download * 100), 1
                    ) if fleet_avg_download > 0 else 0
                    
                    machine['upload_vs_fleet'] = round(
                        ((machine['avg_upload'] - fleet_avg_upload) / fleet_avg_upload * 100), 1
                    ) if fleet_avg_upload > 0 else 0
            
            conn.close()
            
            return {
                'period_hours': hours,
                'machines': machines,
                'fleet_avg_download': round(fleet_avg_download, 2) if machines else 0,
                'fleet_avg_upload': round(fleet_avg_upload, 2) if machines else 0,
                'fleet_avg_ping': round(fleet_avg_ping, 2) if machines else 0,
            }
            
        except Exception as e:
            logger.error(f"Error getting comparison report: {e}")
            return {}
    
    def detect_anomalies(self, machine_id: str, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detect anomalous speed test results (outliers)
        
        Args:
            machine_id: Machine identifier
            threshold_std: Number of standard deviations to consider anomalous
            
        Returns:
            List of anomalous results
        """
        try:
            stats = self.get_machine_stats(machine_id, hours=168)  # 7 days
            
            if 'error' in stats:
                return []
            
            anomalies = []
            
            # Get recent results
            results = self.get_recent_results(machine_id, hours=168)
            
            for result in results:
                issues = []
                
                # Check download speed
                if result['download_mbps']:
                    z_score = abs(result['download_mbps'] - stats['download']['avg']) / stats['download']['stdev'] if stats['download']['stdev'] > 0 else 0
                    if z_score > threshold_std:
                        issues.append(f"Download: {result['download_mbps']:.1f} Mbps (avg: {stats['download']['avg']:.1f})")
                
                # Check upload speed
                if result['upload_mbps']:
                    z_score = abs(result['upload_mbps'] - stats['upload']['avg']) / stats['upload']['stdev'] if stats['upload']['stdev'] > 0 else 0
                    if z_score > threshold_std:
                        issues.append(f"Upload: {result['upload_mbps']:.1f} Mbps (avg: {stats['upload']['avg']:.1f})")
                
                # Check ping
                if result['ping_ms']:
                    z_score = abs(result['ping_ms'] - stats['ping']['avg']) / stats['ping']['stdev'] if stats['ping']['stdev'] > 0 else 0
                    if z_score > threshold_std:
                        issues.append(f"Ping: {result['ping_ms']:.1f} ms (avg: {stats['ping']['avg']:.1f})")
                
                if issues:
                    anomalies.append({
                        'timestamp': result['timestamp'],
                        'issues': issues,
                        'download_mbps': result['download_mbps'],
                        'upload_mbps': result['upload_mbps'],
                        'ping_ms': result['ping_ms'],
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    def generate_report(self, format: str = 'text', hours: int = 24) -> str:
        """
        Generate a formatted report
        
        Args:
            format: Report format ('text', 'json', 'html')
            hours: Number of hours to analyze
            
        Returns:
            Formatted report string
        """
        summary = self.get_fleet_summary(hours)
        
        if format == 'json':
            return json.dumps(summary, indent=2)
        
        elif format == 'text':
            report = []
            report.append("=" * 60)
            report.append(f"FLEET SPEED TEST REPORT - Last {hours} Hours")
            report.append("=" * 60)
            report.append(f"\nFleet Summary:")
            report.append(f"  Total Tests: {summary.get('test_count', 0)}")
            report.append(f"  Machines Tested: {summary.get('machine_count', 0)}")
            report.append(f"\nAverage Speeds:")
            report.append(f"  Download: {summary.get('avg_download_mbps', 0):.1f} Mbps")
            report.append(f"  Upload: {summary.get('avg_upload_mbps', 0):.1f} Mbps")
            report.append(f"  Ping: {summary.get('avg_ping_ms', 0):.1f} ms")
            report.append(f"\nSpeed Range:")
            report.append(f"  Download: {summary.get('min_download_mbps', 0):.1f} - {summary.get('max_download_mbps', 0):.1f} Mbps")
            report.append(f"  Upload: {summary.get('min_upload_mbps', 0):.1f} - {summary.get('max_upload_mbps', 0):.1f} Mbps")
            report.append(f"  Ping: {summary.get('min_ping_ms', 0):.1f} - {summary.get('max_ping_ms', 0):.1f} ms")
            
            if summary.get('machines'):
                report.append(f"\n{'-' * 60}")
                report.append("Per-Machine Results:")
                report.append(f"{'-' * 60}")
                for machine in summary['machines']:
                    report.append(f"\n{machine['machine_id']}:")
                    report.append(f"  Tests: {machine['test_count']}")
                    report.append(f"  Download: {machine['avg_download_mbps']:.1f} Mbps")
                    report.append(f"  Upload: {machine['avg_upload_mbps']:.1f} Mbps")
                    report.append(f"  Ping: {machine['avg_ping_ms']:.1f} ms")
                    report.append(f"  Last Test: {machine['last_test']}")
            
            report.append("\n" + "=" * 60)
            return "\n".join(report)
        
        return "Unsupported format"


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    aggregator = SpeedTestAggregator()
    
    # Generate and print report
    report = aggregator.generate_report(format='text', hours=24)
    print(report)
