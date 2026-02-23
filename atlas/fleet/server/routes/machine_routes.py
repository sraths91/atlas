"""
Fleet Machine Routes

Route handlers for individual machine data endpoints.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- Machine detail retrieval (by machine_id or serial number)
- Machine history retrieval
- Recent commands retrieval

Created: December 31, 2025
"""
import json
import logging
from atlas.fleet.server.router import send_json, send_error, send_unauthorized, read_request_body
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


def register_machine_routes(router, data_store, auth_manager):
    """Register all machine-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        data_store: FleetDataStore instance
        auth_manager: FleetAuthManager instance
    """

    # Helper function to resolve identifier (machine_id or serial number)
    def resolve_identifier(identifier):
        """Resolve identifier to machine_id, checking both machine_id and serial number

        Args:
            identifier: Machine ID or serial number

        Returns:
            tuple: (machine, machine_id) where machine is the machine dict or None,
                   and machine_id is the resolved ID or original identifier
        """
        # First try as machine_id
        machine = data_store.get_machine(identifier)
        if machine:
            return machine, identifier

        # Try to find by serial number
        all_machines = data_store.get_all_machines()
        for m in all_machines:
            if m.get("info", {}).get("serial_number") == identifier:
                return m, m["machine_id"]

        return None, identifier


    # GET /api/fleet/machine/{identifier} - Get specific machine
    def handle_get_machine(handler, identifier):
        """Get specific machine by machine_id or serial number"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        # Resolve identifier to machine
        machine, _ = resolve_identifier(identifier)

        if machine:
            send_json(handler, machine)
        else:
            send_error(handler, "Machine not found", status=404)


    # GET /api/fleet/history/{identifier} - Get machine history
    def handle_get_history(handler, identifier):
        """Get machine history by machine_id or serial number"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        # Resolve identifier to machine_id
        _, machine_id = resolve_identifier(identifier)

        # Get history
        history = data_store.get_machine_history(machine_id)

        send_json(handler, {"history": history})


    # GET /api/fleet/recent-commands/{identifier} - Get recent commands for machine
    def handle_get_recent_commands(handler, identifier):
        """Get recent commands for UI display (by machine_id or serial number)"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        # Resolve identifier to machine_id
        _, machine_id = resolve_identifier(identifier)

        # Get recent commands if supported
        if hasattr(data_store, "get_recent_commands"):
            commands = data_store.get_recent_commands(machine_id)
            send_json(handler, {"commands": commands})
        else:
            send_json(handler, {"commands": []})


    # POST /api/fleet/machine/{identifier}/decrypt-db-data - Decrypt agent DB data
    def handle_decrypt_agent_data(handler, identifier):
        """Decrypt data from an agent's local encrypted DB."""
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        _, machine_id = resolve_identifier(identifier)

        body = read_request_body(handler)
        if body is None:
            return

        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError:
            send_error(handler, 'Invalid JSON', status=400)
            return

        encrypted_data = data.get('encrypted_data')
        if not encrypted_data:
            send_error(handler, 'Missing encrypted_data field', status=400)
            return

        if hasattr(data_store, 'decrypt_agent_data'):
            try:
                decrypted = data_store.decrypt_agent_data(machine_id, encrypted_data)
                if decrypted is None:
                    send_error(handler, f'No DB key stored for {machine_id}', status=404)
                    return
                send_json(handler, {'success': True, 'decrypted_data': decrypted})
            except Exception as e:
                send_error(handler, f'Decryption failed: {str(e)}', status=400)
        elif hasattr(data_store, 'get_agent_db_key'):
            key_b64 = data_store.get_agent_db_key(machine_id)
            if not key_b64:
                send_error(handler, f'No DB key stored for {machine_id}', status=404)
                return
            try:
                from cryptography.fernet import Fernet
                decrypted = Fernet(key_b64.encode('ascii')).decrypt(encrypted_data.encode()).decode('utf-8')
                send_json(handler, {'success': True, 'decrypted_data': decrypted})
            except Exception as e:
                send_error(handler, f'Decryption failed: {str(e)}', status=400)
        else:
            send_error(handler, 'Agent DB key storage not available', status=501)


    # POST /api/fleet/machine/{identifier}/decrypt-export - Decrypt agent export file
    def handle_decrypt_export(handler, identifier):
        """Decrypt a dual-layer encrypted export file from an agent.

        Dual-layer: outer Fernet wrap (agent key) + inner AES-256-GCM (password).
        Requires both the stored agent key and the user-provided password.
        """
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        _, machine_id = resolve_identifier(identifier)

        body = read_request_body(handler)
        if body is None:
            return

        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError:
            send_error(handler, 'Invalid JSON', status=400)
            return

        encrypted_data = data.get('encrypted_data')
        password = data.get('password', '')
        original_filename = data.get('filename', 'export.csv')
        if not encrypted_data:
            send_error(handler, 'Missing encrypted_data field', status=400)
            return
        if not password or len(password) < 16:
            send_error(handler, 'Password is required (16+ characters)', status=400)
            return

        if not hasattr(data_store, 'get_agent_db_key'):
            send_error(handler, 'Agent DB key storage not available', status=501)
            return

        key_b64 = data_store.get_agent_db_key(machine_id)
        if not key_b64:
            send_error(handler, f'No DB key stored for {machine_id}', status=404)
            return

        try:
            # Layer 1: Fernet unwrap with agent key
            from cryptography.fernet import Fernet
            f = Fernet(key_b64.encode('ascii'))
            aes_encrypted = f.decrypt(encrypted_data.encode('ascii'))

            # Layer 2: AES-256-GCM decrypt with password
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            salt = aes_encrypted[:16]
            nonce = aes_encrypted[16:28]
            ciphertext = aes_encrypted[28:]

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            aes_key = kdf.derive(password.encode('utf-8'))
            aesgcm = AESGCM(aes_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)

            send_json(handler, {
                'success': True,
                'decrypted_data': decrypted.decode('utf-8'),
                'filename': original_filename
            })
        except Exception as e:
            send_error(handler, f'Decryption failed: {str(e)}', status=400)


    # Register routes with router
    router.get("/api/fleet/machine/{identifier}", handle_get_machine)
    router.get("/api/fleet/history/{identifier}", handle_get_history)
    router.get("/api/fleet/recent-commands/{identifier}", handle_get_recent_commands)
    router.post("/api/fleet/machine/{identifier}/decrypt-db-data", handle_decrypt_agent_data)
    router.post("/api/fleet/machine/{identifier}/decrypt-export", handle_decrypt_export)


__all__ = ["register_machine_routes"]
