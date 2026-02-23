"""
Tool Availability Monitor - Detects which system monitoring tools are available
Tracks installation status and licensing requirements for third-party tools.
"""
import subprocess
import shutil
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class License(Enum):
    """Software license types with compliance requirements"""
    MIT = "MIT"  # Permissive - no restrictions
    APACHE_2 = "Apache-2.0"  # Permissive - patent grant, attribution required
    BSD_3 = "BSD-3-Clause"  # Permissive - attribution required
    GPL_2 = "GPL-2.0"  # Copyleft - must distribute unmodified, include license
    GPL_3 = "GPL-3.0"  # Copyleft - must distribute unmodified, include license
    LGPL_3 = "LGPL-3.0"  # Copyleft (weak) - dynamic linking OK, modifications GPL
    PROPRIETARY = "Proprietary"  # Check individual terms


@dataclass
class ToolInfo:
    """Information about a monitoring tool"""
    name: str
    brew_package: str
    binary_name: str
    license: License
    description: str
    value_for_atlas: str
    requires_sudo: bool = False
    attribution: Optional[str] = None


# Registry of recommended tools with licensing information
TOOL_REGISTRY = {
    "smartmontools": ToolInfo(
        name="smartmontools",
        brew_package="smartmontools",
        binary_name="smartctl",
        license=License.GPL_2,
        description="SMART disk health monitoring",
        value_for_atlas="Disk health scores, wear leveling, temperature monitoring",
        requires_sudo=True,
        attribution="smartmontools - GPL-2.0 - https://www.smartmontools.org/"
    ),
    "mtr": ToolInfo(
        name="mtr",
        brew_package="mtr",
        binary_name="mtr",
        license=License.GPL_2,
        description="Network path analysis with ping + traceroute",
        value_for_atlas="Enhanced traceroute with packet loss and latency per hop",
        requires_sudo=True,
        attribution="mtr - GPL-2.0 - https://www.bitwizard.nl/mtr/"
    ),
    "iperf3": ToolInfo(
        name="iperf3",
        brew_package="iperf3",
        binary_name="iperf3",
        license=License.BSD_3,
        description="LAN bandwidth testing tool",
        value_for_atlas="Server-to-server bandwidth testing, jitter measurement",
        requires_sudo=False,
        attribution="iperf3 - BSD-3-Clause - https://software.es.net/iperf/"
    ),
    "bandwhich": ToolInfo(
        name="bandwhich",
        brew_package="bandwhich",
        binary_name="bandwhich",
        license=License.MIT,
        description="Terminal bandwidth utilization tool",
        value_for_atlas="Per-process network usage, real-time bandwidth monitoring",
        requires_sudo=True,
        attribution="bandwhich - MIT - https://github.com/imsnif/bandwhich"
    ),
    "btop": ToolInfo(
        name="btop",
        brew_package="btop",
        binary_name="btop",
        license=License.APACHE_2,
        description="Resource monitor with beautiful interface",
        value_for_atlas="Enhanced CPU/memory/process monitoring data",
        requires_sudo=False,
        attribution="btop - Apache-2.0 - https://github.com/aristocratos/btop"
    ),
    "glances": ToolInfo(
        name="glances",
        brew_package="glances",
        binary_name="glances",
        license=License.LGPL_3,
        description="Cross-platform system monitor",
        value_for_atlas="JSON API for comprehensive system stats",
        requires_sudo=False,
        attribution="glances - LGPL-3.0 - https://nicolargo.github.io/glances/"
    ),
    "vnstat": ToolInfo(
        name="vnstat",
        brew_package="vnstat",
        binary_name="vnstat",
        license=License.GPL_2,
        description="Network traffic monitor with history",
        value_for_atlas="Historical bandwidth tracking, daily/monthly traffic stats",
        requires_sudo=False,
        attribution="vnstat - GPL-2.0 - https://humdi.net/vnstat/"
    ),
    "osquery": ToolInfo(
        name="osquery",
        brew_package="osquery",
        binary_name="osqueryi",
        license=License.APACHE_2,
        description="SQL-powered OS instrumentation",
        value_for_atlas="Endpoint visibility, compliance queries, security monitoring",
        requires_sudo=True,
        attribution="osquery - Apache-2.0 - https://osquery.io/"
    ),
    "trivy": ToolInfo(
        name="trivy",
        brew_package="trivy",
        binary_name="trivy",
        license=License.APACHE_2,
        description="Container and filesystem security scanner",
        value_for_atlas="Vulnerability scanning, security audit automation",
        requires_sudo=False,
        attribution="trivy - Apache-2.0 - https://aquasecurity.github.io/trivy/"
    ),
    "lynis": ToolInfo(
        name="lynis",
        brew_package="lynis",
        binary_name="lynis",
        license=License.GPL_3,
        description="Security auditing tool for Unix systems",
        value_for_atlas="Security hardening score, compliance checks",
        requires_sudo=True,
        attribution="lynis - GPL-3.0 - https://cisofy.com/lynis/"
    ),
}


class ToolAvailabilityMonitor:
    """Monitors availability of system monitoring tools"""

    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 300  # 5 minute cache

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a specific tool is available"""
        if tool_name not in TOOL_REGISTRY:
            return False

        tool = TOOL_REGISTRY[tool_name]
        return shutil.which(tool.binary_name) is not None

    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """Get the full path to a tool's binary"""
        if tool_name not in TOOL_REGISTRY:
            return None

        tool = TOOL_REGISTRY[tool_name]
        return shutil.which(tool.binary_name)

    def get_all_tool_status(self) -> dict:
        """Get availability status for all registered tools"""
        import time

        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        status = {}
        for name, tool in TOOL_REGISTRY.items():
            path = shutil.which(tool.binary_name)
            status[name] = {
                "installed": path is not None,
                "path": path,
                "name": tool.name,
                "description": tool.description,
                "license": tool.license.value,
                "brew_package": tool.brew_package,
                "requires_sudo": tool.requires_sudo,
                "value_for_atlas": tool.value_for_atlas,
                "attribution": tool.attribution
            }

        self._cache = status
        self._cache_time = now
        return status

    def get_installed_tools(self) -> list:
        """Get list of installed tools"""
        status = self.get_all_tool_status()
        return [name for name, info in status.items() if info["installed"]]

    def get_missing_tools(self) -> list:
        """Get list of tools that are not installed"""
        status = self.get_all_tool_status()
        return [name for name, info in status.items() if not info["installed"]]

    def get_install_command(self, tool_name: str) -> Optional[str]:
        """Get the Homebrew install command for a tool"""
        if tool_name not in TOOL_REGISTRY:
            return None
        return f"brew install {TOOL_REGISTRY[tool_name].brew_package}"

    def get_permissive_licensed_tools(self) -> list:
        """Get tools with permissive licenses (MIT, Apache, BSD)"""
        permissive = {License.MIT, License.APACHE_2, License.BSD_3}
        return [
            name for name, tool in TOOL_REGISTRY.items()
            if tool.license in permissive
        ]

    def get_copyleft_licensed_tools(self) -> list:
        """Get tools with copyleft licenses (GPL, LGPL)"""
        copyleft = {License.GPL_2, License.GPL_3, License.LGPL_3}
        return [
            name for name, tool in TOOL_REGISTRY.items()
            if tool.license in copyleft
        ]

    def get_licensing_summary(self) -> dict:
        """Get a summary of licensing requirements for all tools"""
        return {
            "safe_to_bundle": {
                name: TOOL_REGISTRY[name].attribution
                for name in self.get_permissive_licensed_tools()
            },
            "requires_gpl_compliance": {
                name: TOOL_REGISTRY[name].attribution
                for name in self.get_copyleft_licensed_tools()
            },
            "gpl_compliance_notes": [
                "GPL tools can be bundled but must be distributed unmodified",
                "Include full license text with distribution",
                "Provide source code or written offer for source",
                "Include copyright notices and attribution",
                "LGPL allows dynamic linking without copyleft effect"
            ]
        }

    def run_tool(self, tool_name: str, args: list, timeout: int = 30) -> Optional[str]:
        """
        Run a tool and return its output.
        Returns None if tool is not available.
        """
        path = self.get_tool_path(tool_name)
        if not path:
            return None

        try:
            result = subprocess.run(
                [path] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning(f"Tool {tool_name} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error running {tool_name}: {e}")
            return None

    def get_tool_version(self, tool_name: str) -> Optional[str]:
        """Get version string for an installed tool"""
        path = self.get_tool_path(tool_name)
        if not path:
            return None

        version_args = {
            "smartmontools": ["--version"],
            "mtr": ["--version"],
            "iperf3": ["--version"],
            "bandwhich": ["--version"],
            "btop": ["--version"],
            "glances": ["--version"],
            "vnstat": ["--version"],
            "osquery": ["--version"],
            "trivy": ["--version"],
            "lynis": ["--version"],
        }

        args = version_args.get(tool_name, ["--version"])

        try:
            result = subprocess.run(
                [path] + args,
                capture_output=True,
                text=True,
                timeout=5
            )
            # Return first line of output
            output = result.stdout.strip() or result.stderr.strip()
            return output.split('\n')[0] if output else None
        except Exception:
            return None


# Singleton instance
_monitor = None


def get_tool_monitor() -> ToolAvailabilityMonitor:
    """Get the singleton tool availability monitor"""
    global _monitor
    if _monitor is None:
        _monitor = ToolAvailabilityMonitor()
    return _monitor
