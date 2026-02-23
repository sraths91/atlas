"""
Fleet Agent Routes

Route handlers for fleet agent communication endpoints.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- Agent reporting (machine info, metrics)
- Command distribution and acknowledgment
- Widget logs collection
- E2EE payload decryption

Created: December 31, 2025
"""
import json
import logging
from typing import TYPE_CHECKING

from atlas.fleet.server.router import read_request_body, send_json, send_error, send_unauthorized

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


def register_agent_routes(router, data_store, encryption=None, auth_manager=None):
    """Register all agent-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        data_store: FleetDataStore instance
        encryption: FleetConfigEncryption instance (optional)
        auth_manager: FleetAuthManager instance (optional)
    """

    # POST /api/fleet/report - Agent reporting endpoint
    def handle_agent_report(handler):
        """Handle agent report submission with E2EE support"""
        # Check API key authentication
        if auth_manager and not auth_manager.check_api_key(handler):
            send_unauthorized(handler)
            return

        # Read and parse body
        body = read_request_body(handler)
        if body is None:
            return
        data = json.loads(body.decode())

        # Decrypt payload if it's encrypted
        e2ee_verified = False
        if data.get('encrypted') and encryption:
            try:
                data = encryption.decrypt_payload(data)
                e2ee_verified = True  # Successfully decrypted - keys match!
                logger.debug("Successfully decrypted agent payload")
            except Exception as e:
                logger.error(f"Failed to decrypt payload: {e}")
                send_error(handler, 'Decryption failed', status=400, extra={'e2ee_verified': False})
                return
        elif data.get('encrypted') and not encryption:
            logger.error("Received encrypted payload but no encryption key configured!")
            send_error(handler, 'Server not configured for encryption', extra={'e2ee_verified': False})
            return

        # Extract data
        machine_id = data.get('machine_id')
        machine_info = data.get('machine_info', {})
        metrics = data.get('metrics', {})
        agent_db_key = data.get('agent_db_key')  # Agent's local DB Fernet key

        if not machine_id:
            send_error(handler, 'Missing machine_id', status=400)
            return

        # Store data with E2EE status
        machine_info['e2ee_enabled'] = e2ee_verified
        data_store.update_machine(machine_id, machine_info, metrics)

        # Store agent DB encryption key if provided and E2EE verified
        db_key_stored = False
        if agent_db_key and e2ee_verified:
            try:
                if hasattr(data_store, 'store_agent_db_key'):
                    data_store.store_agent_db_key(machine_id, agent_db_key)
                    db_key_stored = True
                    logger.info(f"Stored agent DB key for {machine_id}")
            except Exception as e:
                logger.error(f"Failed to store agent DB key: {e}")

        # Return response with E2EE verification status
        send_json(handler, {'status': 'ok', 'e2ee_verified': e2ee_verified, 'db_key_stored': db_key_stored})


    # GET /api/fleet/commands/{machine_id} - Get pending commands for agent
    def handle_get_commands(handler, machine_id):
        """Get pending commands for agent polling"""
        if hasattr(data_store, 'get_pending_commands'):
            commands = data_store.get_pending_commands(machine_id)
            send_json(handler, {'commands': commands})
        else:
            send_json(handler, {'commands': []})


    # POST /api/fleet/command/{machine_id}/ack - Agent acknowledging command
    def handle_command_ack(handler, machine_id):
        """Handle agent command acknowledgment"""
        # Check API key authentication
        if auth_manager and not auth_manager.check_api_key(handler):
            send_unauthorized(handler)
            return

        # Read and parse body
        body = read_request_body(handler)
        if body is None:
            return
        data = json.loads(body.decode())

        command_id = data.get('id')
        status = data.get('status', 'completed')
        result = data.get('result', {})

        if not command_id:
            send_error(handler, 'Missing command id', status=400)
            return

        if hasattr(data_store, 'acknowledge_command'):
            data_store.acknowledge_command(command_id, status, result)

        send_json(handler, {'status': 'ok'})


    # POST /api/fleet/widget-logs - Store widget logs from machines
    def handle_widget_logs(handler):
        """Handle widget logs submission with E2EE support"""
        # Check API key authentication
        if auth_manager and not auth_manager.check_api_key(handler):
            send_unauthorized(handler)
            return

        # Read and parse body
        body = read_request_body(handler)
        if body is None:
            return
        data = json.loads(body.decode())

        # Decrypt payload if it's encrypted
        if data.get('encrypted') and encryption:
            try:
                data = encryption.decrypt_payload(data)
                logger.debug("Successfully decrypted widget logs payload")
            except Exception as e:
                logger.error(f"Failed to decrypt widget logs: {e}")
                send_error(handler, 'Decryption failed', status=400)
                return
        elif data.get('encrypted') and not encryption:
            logger.error("Received encrypted widget logs but no encryption key configured!")
            send_error(handler, 'Server not configured for encryption')
            return

        machine_id = data.get('machine_id')
        logs = data.get('logs', [])

        if not machine_id:
            send_error(handler, 'Missing machine_id', status=400)
            return

        if not logs:
            send_error(handler, 'No logs provided', status=400)
            return

        # Store logs
        if hasattr(data_store, 'store_widget_logs'):
            data_store.store_widget_logs(machine_id, logs)

            # Also aggregate speed test results
            try:
                from atlas.fleet_speedtest_aggregator import SpeedTestAggregator
                aggregator = SpeedTestAggregator()

                speedtest_count = 0
                for log in logs:
                    if log.get('widget_type') == 'speedtest' and log.get('data'):
                        aggregator.store_speedtest_result(machine_id, log['data'])
                        speedtest_count += 1

                if speedtest_count > 0:
                    logger.info(f"Aggregated {speedtest_count} speed test results from {machine_id}")
            except Exception as e:
                logger.error(f"Error aggregating speed tests: {e}")

            # Store export logs permanently (not subject to widget_logs cleanup)
            try:
                if hasattr(data_store, 'store_export_log'):
                    export_count = 0
                    for log in logs:
                        if log.get('widget_type') == 'export' and log.get('data'):
                            log_data = log['data']
                            log_data['timestamp'] = log.get('timestamp', '')
                            data_store.store_export_log(machine_id, log_data)
                            export_count += 1
                    if export_count > 0:
                        logger.info(f"Stored {export_count} export log(s) permanently from {machine_id}")
            except Exception as e:
                logger.error(f"Error storing export logs: {e}")

            send_json(handler, {'status': 'ok', 'logs_stored': len(logs)})
        else:
            send_error(handler, 'Widget logs not supported', status=501)


    # Register routes with router
    router.post('/api/fleet/report', handle_agent_report)
    router.get('/api/fleet/commands/{machine_id}', handle_get_commands)
    router.post('/api/fleet/command/{machine_id}/ack', handle_command_ack)
    router.post('/api/fleet/widget-logs', handle_widget_logs)


__all__ = ['register_agent_routes']
