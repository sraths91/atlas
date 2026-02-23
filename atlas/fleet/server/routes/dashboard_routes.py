"""
Fleet Dashboard Routes

Route handlers for fleet dashboard API endpoints.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- Machine listing
- Fleet summary statistics
- Server resource metrics
- Storage information

Created: December 31, 2025
"""
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from atlas.fleet.server.router import send_json, send_error, send_unauthorized


def register_dashboard_routes(router, data_store, auth_manager):
    """Register all dashboard-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        data_store: FleetDataStore instance
        auth_manager: FleetAuthManager instance
    """

    # GET /api/fleet/machines - Get all machines
    def handle_get_machines(handler):
        """Get list of all machines"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        # Get all machines
        machines = data_store.get_all_machines()
        send_json(handler, {'machines': machines})


    # GET /api/fleet/summary - Get fleet summary
    def handle_get_summary(handler):
        """Get fleet summary statistics"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        # Get fleet summary
        summary = data_store.get_fleet_summary()
        send_json(handler, summary)


    # GET /api/fleet/server-resources - Get fleet server process resources
    def handle_get_server_resources(handler):
        """Get fleet server process resource usage"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            import psutil

            # Get the fleet server process
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()

            # Get process CPU (call once to initialize, then get value)
            process.cpu_percent()
            time.sleep(0.1)
            process_cpu = process.cpu_percent()

            # Get data directory size
            data_dir_size = 0
            data_dir = Path.home() / '.fleet-server'
            if data_dir.exists():
                for fp in data_dir.rglob('*'):
                    if fp.is_file():
                        try:
                            data_dir_size += fp.stat().st_size
                        except (OSError, IOError):
                            pass

            # Get log file sizes (check new persistent log directory)
            log_size = 0
            log_dir = Path.home() / 'Library' / 'Logs' / 'FleetServer'
            if log_dir.exists():
                for fp in log_dir.rglob('*'):
                    if fp.is_file():
                        try:
                            log_size += fp.stat().st_size
                        except (OSError, IOError):
                            pass

            # Get process creation time and uptime
            create_time = process.create_time()
            uptime_seconds = time.time() - create_time

            # Get open file descriptors and connections
            try:
                num_fds = process.num_fds()
            except (psutil.AccessDenied, OSError, AttributeError):
                num_fds = 0

            try:
                connections = len(process.connections())
            except (psutil.AccessDenied, OSError):
                connections = 0

            send_json(handler, {
                'process': {
                    'pid': os.getpid(),
                    'cpu_percent': process_cpu,
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'memory_percent': process.memory_percent(),
                    'threads': process.num_threads(),
                    'uptime_seconds': uptime_seconds,
                    'open_files': num_fds,
                    'connections': connections
                },
                'storage': {
                    'data_dir_size': data_dir_size,
                    'log_size': log_size,
                    'total_size': data_dir_size + log_size
                }
            })
        except Exception as e:
            logger.error(f"Error getting server resources: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/storage - Inspect storage/backend information
    def handle_get_storage(handler):
        """Get storage and backend information"""
        info = {}
        # Some data_store implementations may not support storage_info
        if hasattr(data_store, 'storage_info'):
            try:
                info = data_store.storage_info()
            except Exception as e:
                logger.error(f"Error getting storage info: {e}", exc_info=True)
                info = {'error': 'Internal server error'}
        else:
            info = {
                'backend': 'in_memory',
                'note': 'Current data store does not expose storage_info()'
            }

        send_json(handler, info)


    # GET /api/fleet/agents - Get list of registered agents with dashboard URLs
    def handle_get_agents(handler):
        """Get list of all registered agents with their dashboard URLs

        Returns a list of agents including:
        - machine_id, serial_number, computer_name
        - local_ip, dashboard_url
        - first_seen, last_seen, status
        """
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        # Get registered agents
        if hasattr(data_store, 'get_registered_agents'):
            agents = data_store.get_registered_agents()
        else:
            # Fallback for older data stores
            machines = data_store.get_all_machines()
            agents = []
            for m in machines:
                info = m.get('info', {})
                sn = info.get('serial_number', m['machine_id'])
                agents.append({
                    'machine_id': m['machine_id'],
                    'serial_number': sn,
                    'computer_name': info.get('computer_name', info.get('hostname', m['machine_id'])),
                    'local_ip': info.get('local_ip', 'unknown'),
                    'dashboard_url': f"/machine/{sn}/dashboard",
                    'first_seen': m.get('first_seen'),
                    'last_seen': m.get('last_seen'),
                    'status': m.get('status', 'unknown')
                })

        send_json(handler, {
            'agents': agents,
            'count': len(agents)
        })


    # Register routes with router
    router.get('/api/fleet/machines', handle_get_machines)
    router.get('/api/fleet/summary', handle_get_summary)
    router.get('/api/fleet/server-resources', handle_get_server_resources)
    router.get('/api/fleet/storage', handle_get_storage)
    router.get('/api/fleet/agents', handle_get_agents)


__all__ = ['register_dashboard_routes']
