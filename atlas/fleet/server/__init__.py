"""
Fleet Server Module

Modular fleet server implementation with separated concerns.
Refactored from monolithic fleet_server.py (Phase 4).

Created: December 31, 2025
"""

from .data_store import FleetDataStore
from .auth import FleetAuthManager, require_web_auth, require_api_key
from .router import FleetRouter

__version__ = "2.0.0"
__all__ = [
    'FleetDataStore',
    'FleetAuthManager',
    'require_web_auth',
    'require_api_key',
    'FleetRouter'
]
