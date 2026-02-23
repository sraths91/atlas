"""
Enhanced Traceroute Module - MTR-style network path analysis using native macOS tools.
Provides per-hop latency and packet loss statistics without requiring mtr installation.
Falls back to mtr when available for enhanced functionality.
"""
import subprocess
import re
import time
import statistics
import logging
import socket
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from atlas.tool_availability import get_tool_monitor

logger = logging.getLogger(__name__)


@dataclass
class HopStats:
    """Statistics for a single hop in the network path"""
    hop_number: int
    ip_address: Optional[str]
    hostname: Optional[str]
    packets_sent: int = 0
    packets_received: int = 0
    packet_loss_pct: float = 0.0
    latencies_ms: List[float] = field(default_factory=list)
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    std_ms: float = 0.0
    last_ms: float = 0.0

    def add_latency(self, latency_ms: float):
        """Add a latency measurement"""
        self.latencies_ms.append(latency_ms)
        self.packets_received += 1
        self._recalculate()

    def add_timeout(self):
        """Record a timeout (packet loss)"""
        self.packets_sent += 1
        self._recalculate()

    def _recalculate(self):
        """Recalculate statistics"""
        self.packets_sent = max(self.packets_sent, len(self.latencies_ms))
        if self.latencies_ms:
            self.min_ms = min(self.latencies_ms)
            self.max_ms = max(self.latencies_ms)
            self.avg_ms = statistics.mean(self.latencies_ms)
            self.last_ms = self.latencies_ms[-1]
            if len(self.latencies_ms) > 1:
                self.std_ms = statistics.stdev(self.latencies_ms)

        if self.packets_sent > 0:
            self.packet_loss_pct = ((self.packets_sent - self.packets_received) / self.packets_sent) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hop": self.hop_number,
            "ip": self.ip_address or "*",
            "hostname": self.hostname or self.ip_address or "*",
            "sent": self.packets_sent,
            "received": self.packets_received,
            "loss_pct": round(self.packet_loss_pct, 1),
            "min_ms": round(self.min_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "std_ms": round(self.std_ms, 2),
            "last_ms": round(self.last_ms, 2)
        }


@dataclass
class TracerouteResult:
    """Complete traceroute result"""
    target: str
    target_ip: Optional[str]
    hops: List[HopStats]
    completed: bool
    total_time_ms: float
    method: str  # "mtr" or "native"
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "target_ip": self.target_ip,
            "hops": [hop.to_dict() for hop in self.hops],
            "completed": self.completed,
            "total_time_ms": round(self.total_time_ms, 2),
            "method": self.method,
            "timestamp": self.timestamp,
            "hop_count": len(self.hops),
            "problem_hops": self._get_problem_hops()
        }

    def _get_problem_hops(self) -> List[Dict[str, Any]]:
        """Identify hops with significant packet loss or high latency"""
        problems = []
        for hop in self.hops:
            issues = []
            if hop.packet_loss_pct > 5:
                issues.append(f"{hop.packet_loss_pct:.1f}% packet loss")
            if hop.avg_ms > 100:
                issues.append(f"high latency ({hop.avg_ms:.1f}ms)")
            if hop.std_ms > 20:
                issues.append(f"unstable ({hop.std_ms:.1f}ms jitter)")

            if issues:
                problems.append({
                    "hop": hop.hop_number,
                    "ip": hop.ip_address or "*",
                    "issues": issues
                })
        return problems


class EnhancedTraceroute:
    """
    Performs MTR-style traceroute using native macOS tools or mtr when available.
    """

    def __init__(self):
        self.tool_monitor = get_tool_monitor()

    def trace(
        self,
        target: str,
        count: int = 10,
        max_hops: int = 30,
        timeout: float = 1.0,
        resolve_hostnames: bool = True
    ) -> TracerouteResult:
        """
        Perform enhanced traceroute to target.

        Args:
            target: Hostname or IP address to trace
            count: Number of probes per hop (like mtr -c)
            max_hops: Maximum number of hops to trace
            timeout: Timeout per probe in seconds
            resolve_hostnames: Whether to resolve IP addresses to hostnames

        Returns:
            TracerouteResult with per-hop statistics
        """
        start_time = time.time()

        # Resolve target IP
        try:
            target_ip = socket.gethostbyname(target)
        except socket.gaierror:
            target_ip = None

        # Try mtr first if available
        if self.tool_monitor.is_tool_available("mtr"):
            result = self._trace_with_mtr(target, count, max_hops, resolve_hostnames)
        else:
            result = self._trace_native(target, target_ip, count, max_hops, timeout, resolve_hostnames)

        result.total_time_ms = (time.time() - start_time) * 1000
        result.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        return result

    def _trace_with_mtr(
        self,
        target: str,
        count: int,
        max_hops: int,
        resolve_hostnames: bool
    ) -> TracerouteResult:
        """Use mtr for traceroute (requires sudo/root privileges on macOS)"""
        logger.info(f"Attempting mtr for traceroute to {target}")

        mtr_path = self.tool_monitor.get_tool_path("mtr")
        args = [
            mtr_path,
            "--report",  # Report mode
            "--report-cycles", str(count),
            "--max-ttl", str(max_hops),
        ]

        if not resolve_hostnames:
            args.append("--no-dns")

        args.append(target)

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=count * max_hops + 30
            )

            # Check for permission errors in stderr
            if "Failure to open" in result.stderr or "permission" in result.stderr.lower():
                logger.info("mtr requires root privileges, falling back to native traceroute")
                return self._trace_native(target, None, count, max_hops, 1.0, resolve_hostnames)

            hops = self._parse_mtr_output(result.stdout)

            # If mtr returns no hops (likely permission issue), fall back to native
            if len(hops) == 0:
                logger.info("mtr returned no hops (needs sudo), falling back to native traceroute")
                return self._trace_native(target, None, count, max_hops, 1.0, resolve_hostnames)

            target_ip = hops[-1].ip_address if hops else None

            return TracerouteResult(
                target=target,
                target_ip=target_ip,
                hops=hops,
                completed=len(hops) > 0,
                total_time_ms=0,
                method="mtr"
            )
        except subprocess.TimeoutExpired:
            logger.warning("mtr timed out, falling back to native traceroute")
            return self._trace_native(target, None, count, max_hops, 1.0, resolve_hostnames)
        except Exception as e:
            logger.error(f"mtr failed: {e}, falling back to native traceroute")
            return self._trace_native(target, None, count, max_hops, 1.0, resolve_hostnames)

    def _parse_mtr_output(self, output: str) -> List[HopStats]:
        """Parse mtr report output"""
        hops = []
        # mtr output format:
        # HOST: hostname                             Loss%   Snt   Last   Avg  Best  Wrst StDev
        #   1.|-- gateway.local                       0.0%    10    1.2   1.3   1.1   1.5   0.1

        pattern = r'^\s*(\d+)\.\|--\s+(\S+)\s+(\d+\.?\d*)%\s+(\d+)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)'

        for line in output.split('\n'):
            match = re.match(pattern, line)
            if match:
                hop_num = int(match.group(1))
                host = match.group(2)
                loss_pct = float(match.group(3))
                sent = int(match.group(4))
                last_ms = float(match.group(5))
                avg_ms = float(match.group(6))
                best_ms = float(match.group(7))
                worst_ms = float(match.group(8))
                std_ms = float(match.group(9))

                # Determine if host is IP or hostname
                ip_address = host if re.match(r'^\d+\.\d+\.\d+\.\d+$', host) else None
                hostname = host if not ip_address else None

                hop = HopStats(
                    hop_number=hop_num,
                    ip_address=ip_address or host,
                    hostname=hostname or host,
                    packets_sent=sent,
                    packets_received=int(sent * (100 - loss_pct) / 100),
                    packet_loss_pct=loss_pct,
                    min_ms=best_ms,
                    max_ms=worst_ms,
                    avg_ms=avg_ms,
                    std_ms=std_ms,
                    last_ms=last_ms
                )
                hops.append(hop)

        return hops

    def _trace_native(
        self,
        target: str,
        target_ip: Optional[str],
        count: int,
        max_hops: int,
        timeout: float,
        resolve_hostnames: bool
    ) -> TracerouteResult:
        """
        Native MTR-style traceroute using macOS traceroute + ping.
        First discovers the path, then probes each hop multiple times.
        """
        logger.info(f"Using native traceroute to {target}")

        # Step 1: Discover the path using traceroute
        path = self._discover_path(target, max_hops, timeout)

        if not path:
            return TracerouteResult(
                target=target,
                target_ip=target_ip,
                hops=[],
                completed=False,
                total_time_ms=0,
                method="native"
            )

        # Step 2: Probe each hop multiple times to get statistics
        hops = self._probe_path(path, count, timeout, resolve_hostnames)

        return TracerouteResult(
            target=target,
            target_ip=target_ip or (hops[-1].ip_address if hops else None),
            hops=hops,
            completed=True,
            total_time_ms=0,
            method="native"
        )

    def _discover_path(self, target: str, max_hops: int, timeout: float) -> List[Optional[str]]:
        """Discover the network path using traceroute"""
        try:
            # Use -q 1 for single probe per hop (faster)
            # Timeout calculation: max_hops * wait_time * probes + buffer
            wait_time = max(1, int(timeout))
            process_timeout = max_hops * wait_time * 2 + 15  # Extra buffer for slow responses

            result = subprocess.run(
                [
                    "traceroute",
                    "-n",  # Don't resolve hostnames (faster)
                    "-m", str(max_hops),
                    "-w", str(wait_time),
                    "-q", "1",  # Single probe per hop for faster discovery
                    target
                ],
                capture_output=True,
                text=True,
                timeout=process_timeout
            )

            path = []
            current_hop = 0
            # traceroute output format:
            #  1  192.168.1.1  1.234 ms  1.123 ms  1.456 ms
            #  2  * * *
            # Some targets have multiple addresses per hop:
            #  2  10.27.41.203  10.697 ms
            #     10.27.41.202  14.199 ms  8.812 ms

            for line in result.stdout.split('\n'):
                # Skip empty lines, header lines, and warning lines
                if not line.strip():
                    continue
                if 'traceroute' in line.lower() or 'warning' in line.lower():
                    continue

                # Check if line starts with a hop number (with leading spaces)
                parts = line.split()
                if not parts:
                    continue

                # Try to get hop number from first part
                try:
                    hop_num = int(parts[0])
                    current_hop = hop_num
                    # Find the first IP address in this line
                    ip = None
                    for part in parts[1:]:
                        if part == '*':
                            continue
                        # Check if it looks like an IP address
                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', part):
                            ip = part
                            break
                    # Ensure path list is long enough
                    while len(path) < hop_num:
                        path.append(None)
                    if ip:
                        path[hop_num - 1] = ip
                except ValueError:
                    # This line doesn't start with a hop number
                    # It might be a continuation line with alternate IP
                    # If we already have an entry for this hop with None, try to fill it
                    if current_hop > 0 and current_hop <= len(path):
                        if path[current_hop - 1] is None:
                            # Try to find an IP in this line
                            for part in parts:
                                if part == '*':
                                    continue
                                if re.match(r'^\d+\.\d+\.\d+\.\d+$', part):
                                    path[current_hop - 1] = part
                                    break

            return path

        except subprocess.TimeoutExpired:
            logger.warning("traceroute timed out")
            return []
        except Exception as e:
            logger.error(f"traceroute failed: {e}")
            return []

    def _probe_path(
        self,
        path: List[Optional[str]],
        count: int,
        timeout: float,
        resolve_hostnames: bool
    ) -> List[HopStats]:
        """Probe each hop in the path multiple times to gather statistics"""
        hops = []

        for hop_num, ip in enumerate(path, start=1):
            hop = HopStats(hop_number=hop_num, ip_address=ip, hostname=None)

            if ip:
                # Probe this hop
                latencies = self._ping_host(ip, count, timeout)
                hop.packets_sent = count
                hop.packets_received = len(latencies)

                for lat in latencies:
                    hop.latencies_ms.append(lat)

                hop._recalculate()

                # Resolve hostname if requested
                if resolve_hostnames:
                    hop.hostname = self._resolve_hostname(ip)

            else:
                # Unresponsive hop
                hop.packets_sent = count
                hop.packets_received = 0
                hop.packet_loss_pct = 100.0

            hops.append(hop)

        return hops

    def _ping_host(self, ip: str, count: int, timeout: float) -> List[float]:
        """Ping a host and return list of latencies"""
        try:
            # Use verbose mode to get individual ping times
            result = subprocess.run(
                [
                    "ping",
                    "-c", str(count),
                    "-W", str(int(timeout * 1000)),  # Timeout in ms
                    ip
                ],
                capture_output=True,
                text=True,
                timeout=count * timeout + 5
            )

            latencies = []

            # Parse individual ping responses
            # Format: 64 bytes from 8.8.8.8: icmp_seq=0 ttl=117 time=12.345 ms
            for line in result.stdout.split('\n'):
                time_match = re.search(r'time[=<]([\d.]+)\s*ms', line)
                if time_match:
                    latencies.append(float(time_match.group(1)))

            return latencies

        except subprocess.TimeoutExpired:
            return []
        except Exception as e:
            logger.debug(f"ping to {ip} failed: {e}")
            return []

    def _resolve_hostname(self, ip: str) -> Optional[str]:
        """Resolve IP address to hostname"""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror):
            return None

    def quick_trace(self, target: str) -> Dict[str, Any]:
        """
        Perform a quick traceroute suitable for dashboard display.
        Uses fewer probes for faster results.
        """
        result = self.trace(target, count=3, max_hops=20, timeout=0.5, resolve_hostnames=True)
        return result.to_dict()


# Singleton instance
_tracer = None


def get_tracer() -> EnhancedTraceroute:
    """Get the singleton enhanced traceroute instance"""
    global _tracer
    if _tracer is None:
        _tracer = EnhancedTraceroute()
    return _tracer
