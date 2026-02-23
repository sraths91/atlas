"""
Fleet E2EE (End-to-End Encryption) Routes

Route handlers for encryption key management endpoints.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- Verify password and get encryption key (POST /api/fleet/verify-and-get-encryption-key)
- Generate new encryption key (POST /api/fleet/generate-encryption-key)
- Regenerate encryption key (POST /api/fleet/regenerate-encryption-key)
- Rotate encryption key to agents (POST /api/fleet/rotate-encryption-key)
- Get key rotation status (GET /api/fleet/key-rotation-status)

Created: December 31, 2025
"""
import json
import logging
import uuid
from datetime import datetime

from atlas.fleet.server.router import read_request_body, send_json, send_error, send_unauthorized

logger = logging.getLogger(__name__)


def register_e2ee_routes(router, data_store, auth_manager, encryption=None):
    """Register all E2EE-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        data_store: FleetDataStore instance
        auth_manager: FleetAuthManager instance
        encryption: FleetConfigEncryption instance (optional)
    """

    # Helper methods for encryption key management
    def get_encryption_key_from_config():
        """Get encryption key from config file"""
        try:
            import os
            import json
            from pathlib import Path

            config_path = Path.home() / ".fleet-config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                return config.get('encryption', {}).get('e2ee_key')
        except Exception as e:
            logger.error(f"Error reading encryption key from config: {e}")
        return None

    def save_encryption_key_to_config(encryption_key):
        """Save encryption key to config file"""
        try:
            import os
            import json
            from pathlib import Path

            config_path = Path.home() / ".fleet-config.json"

            # Load existing config
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}

            # Update encryption section
            if 'encryption' not in config:
                config['encryption'] = {}
            config['encryption']['e2ee_key'] = encryption_key

            # Save back
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info("E2EE encryption key saved to config")
        except Exception as e:
            logger.error(f"Error saving encryption key to config: {e}")
            raise


    # POST /api/fleet/verify-and-get-encryption-key - Verify password and return encryption key
    def handle_verify_and_get_encryption_key(handler):
        """Verify password and return E2EE encryption key"""
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body.decode())

            password = data.get('password')

            if not password:
                send_json(handler, {'success': False, 'message': 'Password is required'})
                return

            # Verify password
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.authenticate(username, password)

            if success:
                # Get encryption key from config
                encryption_key = get_encryption_key_from_config()
                if encryption_key:
                    send_json(handler, {'success': True, 'encryption_key': encryption_key})
                else:
                    send_json(handler, {'success': False, 'message': 'No encryption key configured'})
            else:
                send_json(handler, {'success': False, 'message': 'Incorrect password'})
        except Exception as e:
            logger.error(f"Error verifying and getting encryption key: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/generate-encryption-key - Generate new encryption key
    def handle_generate_encryption_key(handler):
        """Generate new E2EE encryption key"""
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body.decode())

            password = data.get('password')

            if not password:
                send_json(handler, {'success': False, 'message': 'Password is required'})
                return

            # Verify password
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.authenticate(username, password)

            if not success:
                send_json(handler, {'success': False, 'message': 'Incorrect password'})
                return

            # Generate new encryption key
            from atlas.encryption import DataEncryption
            new_key = DataEncryption.generate_key()

            # Save to config
            save_encryption_key_to_config(new_key)

            # Update server's encryption handler (if accessible)
            # Note: This would need to be passed in or accessed via a global reference
            # For now, just save to config - server restart will pick it up

            logger.info(f"E2EE encryption key generated by user: {username}")

            send_json(handler, {
                'success': True,
                'encryption_key': new_key,
                'message': 'Encryption key generated successfully'
            })
        except Exception as e:
            logger.error(f"Error generating encryption key: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/regenerate-encryption-key - Regenerate encryption key
    def handle_regenerate_encryption_key(handler):
        """Regenerate E2EE encryption key (same as generate but for existing keys)"""
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body.decode())

            password = data.get('password')

            if not password:
                send_json(handler, {'success': False, 'message': 'Password is required'})
                return

            # Verify password
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.authenticate(username, password)

            if not success:
                send_json(handler, {'success': False, 'message': 'Incorrect password'})
                return

            # Generate new encryption key
            from atlas.encryption import DataEncryption
            new_key = DataEncryption.generate_key()

            # Save to config
            save_encryption_key_to_config(new_key)

            logger.info(f"E2EE encryption key regenerated by user: {username}")

            send_json(handler, {
                'success': True,
                'encryption_key': new_key,
                'message': 'Encryption key regenerated successfully'
            })
        except Exception as e:
            logger.error(f"Error regenerating encryption key: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/rotate-encryption-key - Rotate encryption key to all agents
    def handle_rotate_encryption_key(handler):
        """Rotate encryption key to all connected agents (remote update)"""
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body.decode())

            password = data.get('password')

            if not password:
                send_json(handler, {'success': False, 'message': 'Password is required'})
                return

            # Verify password
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.authenticate(username, password)

            if not success:
                send_json(handler, {'success': False, 'message': 'Incorrect password'})
                return

            # Check if E2EE is currently enabled
            if not encryption or not encryption.enabled:
                send_json(handler, {'success': False, 'message': 'E2EE is not currently enabled. Generate a key first.'})
                return

            from atlas.encryption import DataEncryption

            # Generate new key
            new_key = DataEncryption.generate_key()

            # Encrypt new key with OLD key for secure transmission
            encrypted_new_key = encryption.encrypt_payload({'new_key': new_key})

            # Queue rotate command for all connected machines
            machines = data_store.get_all_machines()
            queued_count = 0

            for machine in machines:
                machine_id = machine.get('machine_id')
                command = {
                    'id': str(uuid.uuid4()),
                    'action': 'rotate_encryption_key',
                    'params': {'encrypted_new_key': encrypted_new_key},
                    'timestamp': datetime.now().isoformat()
                }
                data_store.add_pending_command(machine_id, command)
                queued_count += 1
                logger.info(f"Queued key rotation command for {machine_id}")

            # Save new key to server config
            save_encryption_key_to_config(new_key)

            logger.info(f"E2EE key rotation initiated by {username} - {queued_count} agents queued")

            send_json(handler, {
                'success': True,
                'encryption_key': new_key,
                'agents_queued': queued_count,
                'message': f'Key rotation queued for {queued_count} agent(s). Agents will update on next poll.'
            })

        except Exception as e:
            logger.error(f"Error rotating encryption key: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/key-rotation-status - Get key rotation command status
    def handle_key_rotation_status(handler):
        """Get key rotation command status for all machines"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            rotation_status = []
            if hasattr(data_store, 'get_recent_commands'):
                machines = data_store.get_all_machines()
                for machine in machines:
                    machine_id = machine.get('machine_id')
                    hostname = machine.get('info', {}).get('hostname', machine_id[:8])

                    # Get recent key rotation commands
                    commands = data_store.get_recent_commands(machine_id, limit=5)
                    for cmd in commands:
                        if cmd.get('action') == 'rotate_encryption_key':
                            rotation_status.append({
                                'machine_id': machine_id,
                                'hostname': hostname,
                                'status': cmd.get('status', 'pending'),
                                'created_at': cmd.get('created_at'),
                                'executed_at': cmd.get('executed_at'),
                                'result': cmd.get('result', {})
                            })
                            break  # Only get most recent rotation command per machine

            send_json(handler, {'success': True, 'rotations': rotation_status})
        except Exception as e:
            logger.error(f"Error getting key rotation status: {e}")
            send_error(handler, 'Internal server error')


    # Register routes with router
    router.post('/api/fleet/verify-and-get-encryption-key', handle_verify_and_get_encryption_key)
    router.post('/api/fleet/generate-encryption-key', handle_generate_encryption_key)
    router.post('/api/fleet/regenerate-encryption-key', handle_regenerate_encryption_key)
    router.post('/api/fleet/rotate-encryption-key', handle_rotate_encryption_key)
    router.get('/api/fleet/key-rotation-status', handle_key_rotation_status)


__all__ = ['register_e2ee_routes']
