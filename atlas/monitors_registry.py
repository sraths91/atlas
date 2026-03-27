"""
Centralized registry for optional monitors.

Provides lazy-loading with ImportError handling, eliminating duplicate
try/except blocks across live_widgets.py and api_routes.py.

Usage:
    from atlas.monitors_registry import get_monitor, is_available

    monitor = get_monitor('power')  # Returns monitor instance or None
    if is_available('power'):
        monitor.start()
"""
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Lazy-loaded monitor cache: name -> instance or None
_MONITORS: dict[str, Optional[Any]] = {}

# Import functions for each optional monitor.
# Each returns the singleton getter, so get_monitor() calls it once and caches.
_IMPORTERS: dict[str, Callable[[], Any]] = {
    'display': lambda: __import__(
        'atlas.display_monitor', fromlist=['get_display_monitor']
    ).get_display_monitor(),
    'power': lambda: __import__(
        'atlas.power_monitor', fromlist=['get_power_monitor']
    ).get_power_monitor(),
    'peripheral': lambda: __import__(
        'atlas.peripheral_monitor', fromlist=['get_peripheral_monitor']
    ).get_peripheral_monitor(),
    'security': lambda: __import__(
        'atlas.security_monitor', fromlist=['get_security_monitor']
    ).get_security_monitor(),
    'disk': lambda: __import__(
        'atlas.disk_health_monitor', fromlist=['get_disk_monitor']
    ).get_disk_monitor(),
    'software': lambda: __import__(
        'atlas.software_inventory_monitor', fromlist=['get_software_monitor']
    ).get_software_monitor(),
    'application': lambda: __import__(
        'atlas.application_monitor', fromlist=['get_app_monitor']
    ).get_app_monitor(),
}

# Sentinel to distinguish "not yet loaded" from "loaded but unavailable (None)"
_NOT_LOADED = object()


def get_monitor(name: str) -> Optional[Any]:
    """Get an optional monitor by name. Returns the monitor instance or None.

    Lazy-loads the module on first access and caches the result. If the module
    is not installed, returns None without raising.

    Args:
        name: Monitor name (display, power, peripheral, security, disk, software, application)

    Returns:
        Monitor instance or None if unavailable
    """
    cached = _MONITORS.get(name, _NOT_LOADED)
    if cached is not _NOT_LOADED:
        return cached

    importer = _IMPORTERS.get(name)
    if importer is None:
        logger.warning(f"Unknown monitor name: {name}")
        _MONITORS[name] = None
        return None

    try:
        instance = importer()
        _MONITORS[name] = instance
        logger.debug(f"Monitor '{name}' loaded successfully")
        return instance
    except ImportError:
        _MONITORS[name] = None
        logger.debug(f"Monitor '{name}' not available (ImportError)")
        return None
    except Exception as e:
        _MONITORS[name] = None
        logger.warning(f"Monitor '{name}' failed to initialize: {e}")
        return None


def is_available(name: str) -> bool:
    """Check if a monitor is available (importable and initialized).

    Args:
        name: Monitor name

    Returns:
        True if get_monitor(name) would return a non-None value
    """
    return get_monitor(name) is not None
