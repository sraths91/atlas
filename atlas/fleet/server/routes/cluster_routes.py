"""
Fleet Cluster Routes

Route handlers for cluster management and high availability endpoints.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- Cluster status and configuration
- Health check endpoint (no auth for load balancers)
- Active nodes listing
- Comprehensive health monitoring

Created: December 31, 2025
"""
import json
import logging
from atlas.fleet.server.router import send_json, send_error, send_unauthorized
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def register_cluster_routes(router, cluster_manager, auth_manager):
    """Register all cluster-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        cluster_manager: ClusterManager instance (optional, can be None)
        auth_manager: FleetAuthManager instance
    """

    # GET /api/fleet/cluster/status - Get cluster status
    def handle_cluster_status(handler):
        """Get cluster status (health check and node information)"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        if cluster_manager and cluster_manager.enabled:
            status = cluster_manager.get_cluster_status()
            send_json(handler, status)
        else:
            send_json(handler, {
                'enabled': False,
                'mode': 'standalone',
                'message': 'Cluster mode not enabled'
            })


    # GET /api/fleet/cluster/health - Health check for load balancers
    def handle_cluster_health(handler):
        """Health check endpoint (no authentication required for load balancers)"""
        if cluster_manager:
            is_healthy = cluster_manager.is_healthy()
            if is_healthy:
                send_json(handler, {
                    'status': 'healthy',
                    'node_id': cluster_manager.node_id
                })
            else:
                send_json(handler, {
                    'status': 'unhealthy',
                    'node_id': cluster_manager.node_id
                }, status=503)
        else:
            # Standalone mode is always healthy
            send_json(handler, {
                'status': 'healthy',
                'mode': 'standalone'
            })


    # GET /api/fleet/cluster/nodes - Get active cluster nodes
    def handle_cluster_nodes(handler):
        """Get list of active cluster nodes"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        if cluster_manager and cluster_manager.enabled:
            nodes = cluster_manager.get_active_nodes()
            send_json(handler, {
                'nodes': [node.to_dict() for node in nodes],
                'count': len(nodes)
            })
        else:
            send_json(handler, {
                'nodes': [],
                'count': 0,
                'message': 'Cluster mode not enabled'
            })


    # GET /api/fleet/cluster/health-check - Comprehensive health check
    def handle_cluster_health_check(handler):
        """Comprehensive health check for cluster monitoring"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        if not cluster_manager or not cluster_manager.enabled:
            send_error(handler, 'Cluster mode not enabled', status=400)
            return

        try:
            health_data = {}

            # Check backend connection
            backend_healthy = False
            backend_latency = 0
            backend_type = cluster_manager.config.get('backend', 'unknown')
            backend_host = None
            backend_error = None

            try:
                start_time = time.time()
                # Test backend connectivity
                if hasattr(cluster_manager.storage, 'ping'):
                    cluster_manager.storage.ping()
                backend_healthy = True
                backend_latency = int((time.time() - start_time) * 1000)

                # Get backend host if available
                if backend_type == 'redis':
                    redis_config = cluster_manager.config.get('redis', {})
                    backend_host = f"{redis_config.get('host', 'unknown')}:{redis_config.get('port', 6379)}"
            except Exception as e:
                backend_error = 'Internal server error'

            health_data['backend'] = {
                'connected': backend_healthy,
                'type': backend_type,
                'latency_ms': backend_latency if backend_healthy else None,
                'host': backend_host,
                'error': backend_error
            }

            # Check node status
            nodes = cluster_manager.get_active_nodes()
            current_node_id = cluster_manager.node_id

            node_list = []
            healthy_nodes = 0
            degraded_nodes = 0

            for node in nodes:
                # Calculate time since last heartbeat
                heartbeat_age = (datetime.now() - node.last_heartbeat).total_seconds()

                # Determine node status
                if heartbeat_age < 15:  # Fresh heartbeat
                    node_status = 'healthy'
                    healthy_nodes += 1
                elif heartbeat_age < 30:  # Aging heartbeat
                    node_status = 'degraded'
                    degraded_nodes += 1
                else:  # Stale heartbeat
                    node_status = 'offline'

                # Calculate uptime
                uptime_seconds = (datetime.now() - node.last_heartbeat).total_seconds()
                if uptime_seconds < 60:
                    uptime = f"{int(uptime_seconds)}s"
                elif uptime_seconds < 3600:
                    uptime = f"{int(uptime_seconds / 60)}m"
                elif uptime_seconds < 86400:
                    uptime = f"{int(uptime_seconds / 3600)}h"
                else:
                    uptime = f"{int(uptime_seconds / 86400)}d"

                node_list.append({
                    'node_id': node.node_id,
                    'status': node_status,
                    'last_heartbeat': node.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S'),
                    'host': node.host,
                    'uptime': uptime,
                    'is_current': node.node_id == current_node_id
                })

            health_data['nodes'] = node_list

            # Check data synchronization
            sync_healthy = backend_healthy  # If backend is healthy, sync should be working
            session_count = 0

            try:
                # Count active sessions (if session storage is available)
                if hasattr(handler, 'session_store') and handler.session_store:
                    # Try to count sessions
                    session_count = len(getattr(handler.session_store, '_sessions', {}))
            except (AttributeError, TypeError):
                pass

            health_data['sync'] = {
                'synced': sync_healthy,
                'session_count': session_count,
                'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'details': 'All nodes sharing data via backend' if sync_healthy else None,
                'error': 'Backend connection issue' if not sync_healthy else None
            }

            # Check failover readiness
            failover_ready = healthy_nodes >= 2

            health_data['failover'] = {
                'ready': failover_ready,
                'healthy_nodes': healthy_nodes,
                'details': f"Cluster can survive {healthy_nodes - 1} node failure(s)" if failover_ready else None
            }

            # Overall health status
            if healthy_nodes >= 2 and backend_healthy:
                overall = 'healthy'
            elif healthy_nodes >= 1 and backend_healthy:
                overall = 'degraded'
            else:
                overall = 'critical'

            health_data['overall'] = overall

            send_json(handler, health_data)

        except Exception as e:
            logger.error(f"Error performing health check: {e}", exc_info=True)
            send_error(handler, 'Internal server error')


    # Register routes with router
    router.get('/api/fleet/cluster/status', handle_cluster_status)
    router.get('/api/fleet/cluster/health', handle_cluster_health)
    router.get('/api/fleet/cluster/nodes', handle_cluster_nodes)
    router.get('/api/fleet/cluster/health-check', handle_cluster_health_check)


__all__ = ['register_cluster_routes']
