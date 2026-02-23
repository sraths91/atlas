"""
Fleet Admin Routes

Route handlers for administrative endpoints including user management,
certificates, API keys, E2EE encryption, and package building.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- User management (create, delete, change password)
- Certificate management
- API key management
- E2EE encryption key management
- Package building (agent, cluster, load balancer)

Created: December 31, 2025
"""
import json
import logging
import base64
from pathlib import Path

from atlas.fleet.server.router import read_request_body, send_json, send_error, send_unauthorized

logger = logging.getLogger(__name__)


def register_admin_routes(router, auth_manager, encryption=None):
    """Register all admin-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        auth_manager: FleetAuthManager instance
        encryption: FleetConfigEncryption instance (optional)
    """

    # ========== USER MANAGEMENT ROUTES ==========

    # POST /api/fleet/users/create - Create new user
    def handle_users_create(handler):
        """Create new user account"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body.decode())

            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.create_user(
                username=data.get('username'),
                password=data.get('password'),
                role=data.get('role', 'admin'),
                created_by=handler.headers.get('Authorization', 'unknown')
            )

            send_json(handler, {'success': success, 'message': message})
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/users/change-password - Change current user's password
    def handle_users_change_password(handler):
        """Change current user's password"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body.decode())

            # Get username from session token
            session_token = auth_manager.get_session_token(handler)
            if session_token:
                from atlas.fleet_user_manager import FleetUserManager
                user_manager = FleetUserManager()
                _, username = user_manager.validate_session(session_token)
            else:
                send_json(handler, {'success': False, 'message': 'Unable to identify user'}, status=400)
                return

            success, message = user_manager.change_password(
                username=username,
                old_password=data.get('current_password'),
                new_password=data.get('new_password')
            )

            send_json(handler, {'success': success, 'message': message})
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/users/delete - Delete user
    def handle_users_delete(handler):
        """Delete user account"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body.decode())

            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.delete_user(
                username=data.get('username'),
                deleted_by=handler.headers.get('Authorization', 'unknown')
            )

            send_json(handler, {'success': success, 'message': message})
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/users/force-update-password - Force update password (legacy migration)
    def handle_users_force_update_password(handler):
        """Force update current user's password for legacy migration"""
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

            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.force_password_update(
                username=username,
                new_password=data.get('new_password'),
                updated_by=username
            )

            send_json(handler, {'success': success, 'message': message})
        except Exception as e:
            logger.error(f"Error forcing password update: {e}")
            send_error(handler, 'Internal server error')


    # ========== CERTIFICATE MANAGEMENT ROUTES ==========

    # GET /api/fleet/cert-status - Get certificate expiration warning
    def handle_cert_status(handler):
        """Get certificate expiration warning"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_cert_auto import get_certificate_status
            status = get_certificate_status()

            send_json(handler, status)
        except Exception as e:
            logger.error(f"Error getting cert status: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/cert-info - Get certificate information
    def handle_cert_info(handler):
        """Get certificate information"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_cert_auto import get_certificate_info
            info = get_certificate_info()

            send_json(handler, info)
        except Exception as e:
            logger.error(f"Error getting cert info: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/update-certificate - Update SSL certificate
    def handle_update_certificate(handler):
        """Update SSL certificate via file upload"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            # This route handles multipart form data for certificate upload
            # Implementation would need multipart parsing
            send_json(handler, {
                'success': False,
                'message': 'Certificate upload not yet implemented in router module'
            }, status=501)
        except Exception as e:
            logger.error(f"Error updating certificate: {e}")
            send_error(handler, 'Internal server error')


    # ========== API KEY MANAGEMENT ROUTES ==========

    # POST /api/fleet/verify-and-get-key - Verify password and get API key
    def handle_verify_and_get_key(handler):
        """Verify password and return API key"""
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

            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            # Verify password
            if not user_manager.verify_password(username, data.get('password')):
                send_json(handler, {'success': False, 'message': 'Invalid password'})
                return

            # Get API key from config
            config_path = Path.home() / ".fleet-config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                api_key = config.get('server', {}).get('api_key')

                send_json(handler, {'success': True, 'api_key': api_key})
            else:
                send_json(handler, {'success': False, 'message': 'Configuration not found'})
        except Exception as e:
            logger.error(f"Error verifying and getting key: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/regenerate-key - Regenerate API key
    def handle_regenerate_key(handler):
        """Regenerate API key after password verification"""
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

            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            # Verify password
            if not user_manager.verify_password(username, data.get('password')):
                send_json(handler, {'success': False, 'message': 'Invalid password'})
                return

            # Generate new API key
            import secrets
            new_api_key = secrets.token_urlsafe(32)

            # Update config
            config_path = Path.home() / ".fleet-config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)

                config.setdefault('server', {})['api_key'] = new_api_key

                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)

                send_json(handler, {
                    'success': True,
                    'api_key': new_api_key,
                    'message': 'API key regenerated successfully'
                })
            else:
                send_json(handler, {'success': False, 'message': 'Configuration not found'})
        except Exception as e:
            logger.error(f"Error regenerating key: {e}")
            send_error(handler, 'Internal server error')


    # ========== E2EE ENCRYPTION ROUTES ==========

    # GET /api/fleet/e2ee-status - Check E2EE encryption key status
    def handle_e2ee_status_get(handler):
        """Check if E2EE encryption key is configured"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        has_key = encryption is not None and encryption.enabled

        send_json(handler, {
            'success': True,
            'has_key': has_key,
            'status': 'enabled' if has_key else 'disabled'
        })


    # Register routes with router
    router.post('/api/fleet/users/create', handle_users_create)
    router.post('/api/fleet/users/change-password', handle_users_change_password)
    router.post('/api/fleet/users/delete', handle_users_delete)
    router.post('/api/fleet/users/force-update-password', handle_users_force_update_password)
    router.get('/api/fleet/cert-status', handle_cert_status)
    router.get('/api/fleet/cert-info', handle_cert_info)
    router.post('/api/fleet/update-certificate', handle_update_certificate)
    router.post('/api/fleet/verify-and-get-key', handle_verify_and_get_key)
    router.post('/api/fleet/regenerate-key', handle_regenerate_key)
    router.get('/api/fleet/e2ee-status', handle_e2ee_status_get)


__all__ = ['register_admin_routes']
