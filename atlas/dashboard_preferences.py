"""
Dashboard Preferences Manager
Manages user-customizable widget layout, visibility, and ordering for the dashboard.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WidgetConfig:
    """Standardized widget configuration.

    All widgets registered in the dashboard must specify these fields.
    Use WIDGET_REGISTRY for the canonical dict-based registry.
    """
    name: str
    route: str
    default_size: str     # CSS class: widget-span-1, widget-span-2, widget-full-width
    default_height: str   # CSS height value, e.g. "450px"
    category: str         # system, network, enterprise, security, hardware
    description: str


# Widget Registry - single source of truth for all available dashboard widgets
WIDGET_REGISTRY = {
    "system-monitor": {
        "name": "System Monitor",
        "route": "/widget/system-monitor",
        "default_size": "widget-span-2",
        "default_height": "550px",
        "category": "system",
        "description": "CPU, RAM, GPU, disk, and network monitoring",
    },
    "wifi": {
        "name": "WiFi Status",
        "route": "/widget/wifi",
        "default_size": "widget-span-1",
        "default_height": "550px",
        "category": "network",
        "description": "Current WiFi connection details",
    },
    "wifi-analyzer-compact": {
        "name": "WiFi Analyzer",
        "route": "/widget/wifi-analyzer-compact",
        "default_size": "widget-full-width",
        "default_height": "480px",
        "category": "network",
        "description": "WiFi signal analysis and nearby networks",
    },
    "speedtest": {
        "name": "Speed Test",
        "route": "/widget/speedtest",
        "default_size": "widget-span-1",
        "default_height": "500px",
        "category": "network",
        "description": "Run and view internet speed tests",
    },
    "speedtest-history": {
        "name": "Speed Test History",
        "route": "/widget/speedtest-history",
        "default_size": "widget-span-2",
        "default_height": "500px",
        "category": "network",
        "description": "Historical speed test results and trends",
    },
    "network-testing": {
        "name": "Network Testing",
        "route": "/widget/network-testing",
        "default_size": "widget-full-width",
        "default_height": "600px",
        "category": "network",
        "description": "VoIP quality, throughput, and connection rate testing",
    },
    "vpn-status": {
        "name": "VPN Status",
        "route": "/widget/vpn-status",
        "default_size": "widget-span-1",
        "default_height": "450px",
        "category": "enterprise",
        "description": "VPN connection status and health",
    },
    "saas-health": {
        "name": "SaaS Health",
        "route": "/widget/saas-health",
        "default_size": "widget-span-1",
        "default_height": "450px",
        "category": "enterprise",
        "description": "Cloud service availability monitoring",
    },
    "network-quality": {
        "name": "Network Quality",
        "route": "/widget/network-quality",
        "default_size": "widget-span-1",
        "default_height": "450px",
        "category": "network",
        "description": "Network quality metrics and scoring",
    },
    "security-dashboard": {
        "name": "Security Dashboard",
        "route": "/widget/security-dashboard",
        "default_size": "widget-span-2",
        "default_height": "500px",
        "category": "security",
        "description": "Security overview and compliance status",
    },
    "system-health": {
        "name": "System Health",
        "route": "/widget/system-health",
        "default_size": "widget-span-1",
        "default_height": "500px",
        "category": "system",
        "description": "Overall system health scoring",
    },
    "power": {
        "name": "Power & Battery",
        "route": "/widget/power",
        "default_size": "widget-span-1",
        "default_height": "400px",
        "category": "hardware",
        "description": "Battery status and power information",
    },
    "display": {
        "name": "Display",
        "route": "/widget/display",
        "default_size": "widget-span-1",
        "default_height": "400px",
        "category": "hardware",
        "description": "Connected display information",
    },
    "peripherals": {
        "name": "Peripherals",
        "route": "/widget/peripherals",
        "default_size": "widget-span-1",
        "default_height": "400px",
        "category": "hardware",
        "description": "Connected peripherals and USB devices",
    },
    "disk-health": {
        "name": "Disk Health",
        "route": "/widget/disk-health",
        "default_size": "widget-span-1",
        "default_height": "400px",
        "category": "hardware",
        "description": "SMART disk health monitoring",
    },
    "wifi-roaming": {
        "name": "WiFi Roaming",
        "route": "/widget/wifi-roaming",
        "default_size": "widget-span-2",
        "default_height": "500px",
        "category": "network",
        "description": "WiFi roaming events and analysis",
    },
    "network-analysis": {
        "name": "Network Analysis",
        "route": "/widget/network-analysis",
        "default_size": "widget-span-1",
        "default_height": "500px",
        "category": "network",
        "description": "Deep network performance analysis",
    },
    "processes": {
        "name": "Processes",
        "route": "/widget/processes",
        "default_size": "widget-full-width",
        "default_height": "650px",
        "category": "system",
        "description": "Running processes and resource usage",
    },
}

# Default widget order (matches the original hardcoded layout)
DEFAULT_ORDER = [
    "system-monitor", "wifi",
    "wifi-analyzer-compact",
    "speedtest", "speedtest-history",
    "network-testing",
    "vpn-status", "saas-health", "network-quality",
    "security-dashboard", "system-health",
    "power", "display", "peripherals", "disk-health",
    "wifi-roaming", "network-analysis",
    "processes",
]

# Category display names and order
CATEGORIES = {
    "system": "System",
    "network": "Network",
    "enterprise": "Enterprise",
    "security": "Security",
    "hardware": "Hardware",
}


class DashboardPreferences:
    """Manages dashboard layout preferences persisted to JSON"""

    def __init__(self, settings_file: Optional[str] = None):
        if settings_file is None:
            config_dir = Path.home() / ".config" / "atlas-agent"
            config_dir.mkdir(parents=True, exist_ok=True)
            settings_file = config_dir / "dashboard_layout.json"

        self.settings_file = Path(settings_file)
        self.layout = self._load()

    def _default_layout(self) -> Dict[str, Any]:
        """Return the default layout configuration"""
        return {
            "order": list(DEFAULT_ORDER),
            "hidden": [],
            "sizes": {},
            "heights": {},
        }

    def _load(self) -> Dict[str, Any]:
        """Load layout from file, merging with defaults for new widgets"""
        defaults = self._default_layout()
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    saved = json.load(f)
                layout = {
                    "order": saved.get("order", defaults["order"]),
                    "hidden": saved.get("hidden", []),
                    "sizes": saved.get("sizes", {}),
                    "heights": saved.get("heights", {}),
                }
                # Merge in any new widgets not in saved order
                for widget_id in DEFAULT_ORDER:
                    if widget_id in WIDGET_REGISTRY and widget_id not in layout["order"]:
                        layout["order"].append(widget_id)
                # Remove widgets that no longer exist in registry
                layout["order"] = [w for w in layout["order"] if w in WIDGET_REGISTRY]
                layout["hidden"] = [w for w in layout["hidden"] if w in WIDGET_REGISTRY]
                logger.info(f"Loaded dashboard layout from {self.settings_file}")
                return layout
            except (json.JSONDecodeError, IOError, KeyError) as e:
                logger.warning(f"Failed to load dashboard layout: {e}")
                return defaults
        return defaults

    def _save(self) -> bool:
        """Save current layout to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.layout, f, indent=2)
            logger.info(f"Saved dashboard layout to {self.settings_file}")
            return True
        except IOError as e:
            logger.error(f"Failed to save dashboard layout: {e}")
            return False

    def get_layout(self) -> Dict[str, Any]:
        """Get current layout configuration"""
        return {
            "order": list(self.layout["order"]),
            "hidden": list(self.layout["hidden"]),
            "sizes": dict(self.layout["sizes"]),
            "heights": dict(self.layout["heights"]),
        }

    def update_layout(self, new_layout: Dict[str, Any]) -> bool:
        """Update layout from client-submitted data"""
        if "order" in new_layout:
            order = new_layout["order"]
            if isinstance(order, list) and all(isinstance(w, str) for w in order):
                # Only keep valid widget IDs
                self.layout["order"] = [w for w in order if w in WIDGET_REGISTRY]
                # Append any missing widgets
                for widget_id in DEFAULT_ORDER:
                    if widget_id in WIDGET_REGISTRY and widget_id not in self.layout["order"]:
                        self.layout["order"].append(widget_id)

        if "hidden" in new_layout:
            hidden = new_layout["hidden"]
            if isinstance(hidden, list) and all(isinstance(w, str) for w in hidden):
                self.layout["hidden"] = [w for w in hidden if w in WIDGET_REGISTRY]

        if "sizes" in new_layout:
            sizes = new_layout["sizes"]
            valid_sizes = {"widget-span-1", "widget-span-2", "widget-full-width"}
            if isinstance(sizes, dict):
                self.layout["sizes"] = {
                    k: v for k, v in sizes.items()
                    if k in WIDGET_REGISTRY and v in valid_sizes
                }

        if "heights" in new_layout:
            heights = new_layout["heights"]
            if isinstance(heights, dict):
                self.layout["heights"] = {
                    k: v for k, v in heights.items()
                    if k in WIDGET_REGISTRY and isinstance(v, str) and v.endswith("px")
                }

        return self._save()

    def reset_to_default(self) -> bool:
        """Reset layout to defaults"""
        self.layout = self._default_layout()
        return self._save()

    def get_visible_widgets(self) -> List[Dict[str, Any]]:
        """Get ordered list of visible widgets with resolved sizes/heights"""
        widgets = []
        for widget_id in self.layout["order"]:
            if widget_id in self.layout["hidden"]:
                continue
            if widget_id not in WIDGET_REGISTRY:
                continue
            meta = WIDGET_REGISTRY[widget_id]
            widgets.append({
                "id": widget_id,
                "route": meta["route"],
                "size": self.layout["sizes"].get(widget_id, meta["default_size"]),
                "height": self.layout["heights"].get(widget_id, meta["default_height"]),
            })
        return widgets

    def get_all_widgets_with_state(self) -> List[Dict[str, Any]]:
        """Get all widgets with their visibility state for the settings UI"""
        result = []
        # First add widgets in the user's order
        seen = set()
        for widget_id in self.layout["order"]:
            if widget_id not in WIDGET_REGISTRY:
                continue
            seen.add(widget_id)
            meta = WIDGET_REGISTRY[widget_id]
            result.append({
                "id": widget_id,
                "name": meta["name"],
                "category": meta["category"],
                "description": meta["description"],
                "visible": widget_id not in self.layout["hidden"],
                "size": self.layout["sizes"].get(widget_id, meta["default_size"]),
                "height": self.layout["heights"].get(widget_id, meta["default_height"]),
                "default_size": meta["default_size"],
                "default_height": meta["default_height"],
            })
        # Add any widgets not yet in the order (newly added)
        for widget_id, meta in WIDGET_REGISTRY.items():
            if widget_id not in seen:
                result.append({
                    "id": widget_id,
                    "name": meta["name"],
                    "category": meta["category"],
                    "description": meta["description"],
                    "visible": widget_id not in self.layout["hidden"],
                    "size": meta["default_size"],
                    "height": meta["default_height"],
                    "default_size": meta["default_size"],
                    "default_height": meta["default_height"],
                })
        return result


# Singleton instance
_preferences_instance = None


def get_dashboard_preferences() -> DashboardPreferences:
    """Get or create the singleton DashboardPreferences instance"""
    global _preferences_instance
    if _preferences_instance is None:
        _preferences_instance = DashboardPreferences()
    return _preferences_instance
