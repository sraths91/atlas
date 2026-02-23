"""
Fleet UI Routes

Route handlers for web UI pages and authentication flows.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- Login page (GET /login, POST /login) with TouchID support
- Logout (GET /logout, POST /api/fleet/logout)
- Dashboard page (GET /dashboard)
- Settings page (GET /settings)
- Password reset page (GET /password-reset, POST /reset-password)
- Machine detail page (GET /machine/{identifier})
- Current user info endpoint (GET /api/fleet/current-user)
- User list endpoint (GET /api/fleet/users)
- Password update check (GET /api/fleet/users/check-password-update)

Created: December 31, 2025
"""
import json
import logging
import urllib.parse
import base64

from atlas.fleet.server.router import read_request_body, send_json, send_error, send_unauthorized

logger = logging.getLogger(__name__)

# Import TouchID functions
try:
    from atlas.dashboard_auth import check_touchid_available, authenticate_with_touchid
    TOUCHID_SUPPORT = True
except ImportError:
    TOUCHID_SUPPORT = False
    def check_touchid_available():
        return False
    def authenticate_with_touchid(reason=""):
        return False, "TouchID not available"


def register_ui_routes(router, auth_manager, data_store=None):
    """Register all UI-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        auth_manager: FleetAuthManager instance
        data_store: FleetDataStore instance (optional, needed for agent dashboard redirect)
    """

    # Import page generators (will remain in fleet_server.py for now)
    # These functions generate HTML for pages
    from atlas.fleet_server import (
        generate_login_page,
        generate_password_reset_page,
        get_fleet_dashboard_html
    )
    from atlas.fleet_settings_page import get_settings_html
    from atlas.fleet_machine_detail import get_machine_detail_html
    from atlas.fleet_machine_dashboard import get_machine_dashboard_html


    # ========== PAGE ROUTES (GET) ==========

    # GET / or /login - Login page
    def handle_login_page(handler):
        """Serve login page with optional TouchID support"""
        # Check if TouchID is available on this system
        touchid_available = check_touchid_available()

        handler.send_response(200)
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        handler.wfile.write(generate_login_page(touchid_available=touchid_available).encode())


    # GET /logout - Logout and redirect
    def handle_logout_get(handler):
        """Handle logout (destroy session and redirect)"""
        # Get session token from cookie
        session_token = auth_manager.get_session_token(handler)

        if session_token:
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()
            user_manager.destroy_session(session_token)

        # Clear cookie and redirect to login
        handler.send_response(302)
        handler.send_header('Location', '/login')
        handler.send_header('Set-Cookie', 'fleet_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict; Secure')
        handler.end_headers()


    # GET /dashboard - Dashboard page
    def handle_dashboard_page(handler):
        """Serve fleet dashboard page"""
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(302)
            handler.send_header('Location', '/login')
            handler.end_headers()
            return

        # Check if user needs password update
        from atlas.fleet_user_manager import FleetUserManager
        user_manager = FleetUserManager()

        needs_update, reason = user_manager.check_password_needs_update(username)
        if needs_update:
            # Redirect to password reset page
            handler.send_response(302)
            handler.send_header('Location', '/password-reset')
            handler.end_headers()
            return

        # Serve fleet dashboard
        handler.send_response(200)
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        handler.wfile.write(get_fleet_dashboard_html().encode())


    # GET /settings - Settings page
    def handle_settings_page(handler):
        """Serve settings page"""
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(302)
            handler.send_header('Location', '/login')
            handler.end_headers()
            return

        # Serve settings page
        handler.send_response(200)
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        handler.wfile.write(get_settings_html().encode())


    # GET /password-reset - Password reset page
    def handle_password_reset_page(handler):
        """Serve password reset page"""
        # Check if user is authenticated but needs password update
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(302)
            handler.send_header('Location', '/login')
            handler.end_headers()
            return

        # Serve password reset page
        handler.send_response(200)
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        handler.wfile.write(generate_password_reset_page(username).encode())


    # GET /machine/{identifier} - Machine detail page
    def handle_machine_detail_page(handler, identifier):
        """Serve machine detail page"""
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(302)
            handler.send_header('Location', '/login')
            handler.end_headers()
            return

        # Serve machine detail page
        handler.send_response(200)
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        handler.wfile.write(get_machine_detail_html(identifier).encode())


    # GET /machine/{identifier}/dashboard - Server-hosted machine dashboard
    def handle_machine_dashboard_redirect(handler, identifier):
        """Serve a server-hosted dashboard for the machine.

        This route looks up the machine by serial number (or machine_id) and
        displays a full dashboard using synced data from the fleet server.
        The dashboard shows the same information as the agent's local dashboard
        but pulls data from the server's data store.

        This approach ensures the dashboard is always accessible, even when
        the agent is offline - it will show the last known data.
        """
        # Check web authentication
        is_authenticated, username = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(302)
            handler.send_header('Location', '/login')
            handler.end_headers()
            return

        if data_store is None:
            # Fallback to old machine detail page if no data_store
            handler.send_response(302)
            handler.send_header('Location', f'/machine/{identifier}')
            handler.end_headers()
            return

        # Look up machine by identifier (serial number or machine_id)
        machine = data_store.get_machine(identifier)
        machine_id = identifier

        # If not found by machine_id, try serial number
        if not machine:
            all_machines = data_store.get_all_machines()
            for m in all_machines:
                if m.get('info', {}).get('serial_number') == identifier:
                    machine = m
                    machine_id = m.get('machine_id', identifier)
                    break

        # Get history if available
        history = None
        if machine and hasattr(data_store, 'get_machine_history'):
            history = data_store.get_machine_history(machine_id)

        # Serve the dashboard HTML (works for both online and offline machines)
        handler.send_response(200)
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        dashboard_html = get_machine_dashboard_html(machine, identifier, history)
        handler.wfile.write(dashboard_html.encode())


    # ========== AUTHENTICATION ROUTES (POST) ==========

    # POST /login - Handle login form submission
    def handle_login_post(handler):
        """Handle login form submission with optional TouchID support"""
        touchid_available = check_touchid_available()

        try:
            body = read_request_body(handler)
            if body is None:
                return
            body = body.decode('utf-8')

            # Parse form data
            params = urllib.parse.parse_qs(body)
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            use_touchid = params.get('use_touchid', [''])[0] == 'true'

            # Handle TouchID authentication
            if use_touchid:
                if not touchid_available:
                    handler.send_response(200)
                    handler.send_header('Content-type', 'text/html')
                    handler.end_headers()
                    handler.wfile.write(generate_login_page(
                        "TouchID is not available on this system",
                        touchid_available=False
                    ).encode())
                    return

                # Perform TouchID authentication
                success, message = authenticate_with_touchid("authenticate to ATLAS Fleet Dashboard")

                if not success:
                    logger.warning(f"TouchID authentication failed: {message}")
                    handler.send_response(200)
                    handler.send_header('Content-type', 'text/html')
                    handler.end_headers()
                    handler.wfile.write(generate_login_page(
                        message or "TouchID authentication failed",
                        touchid_available=touchid_available
                    ).encode())
                    return

                # TouchID successful - create session for touchid_user
                from atlas.fleet_user_manager import FleetUserManager
                user_manager = FleetUserManager()

                # Create a session for the TouchID user
                # Use a special touchid_user account (TouchID bypasses regular user lookup)
                session_token = user_manager.create_session('touchid_user')

                logger.info("TouchID authentication successful")

                # Redirect to dashboard
                handler.send_response(302)
                handler.send_header('Location', '/dashboard')
                handler.send_header('Set-Cookie', f'fleet_session={session_token}; Path=/; Max-Age=28800; HttpOnly; SameSite=Strict; Secure')
                handler.end_headers()
                return

            # Standard username/password authentication
            if not username or not password:
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write(generate_login_page(
                    "Username and password are required",
                    touchid_available=touchid_available
                ).encode())
                return

            # Authenticate user
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            client_ip = handler.client_address[0]
            success, message = user_manager.authenticate(username, password, client_ip)

            if not success:
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write(generate_login_page(
                    message,
                    touchid_available=touchid_available
                ).encode())
                return

            # Check if password needs update
            needs_update, reason = user_manager.check_password_needs_update(username)

            # Create session
            session_token = user_manager.create_session(username)

            # Set cookie and redirect
            if needs_update:
                redirect_url = '/password-reset'
            else:
                redirect_url = '/dashboard'

            handler.send_response(302)
            handler.send_header('Location', redirect_url)
            handler.send_header('Set-Cookie', f'fleet_session={session_token}; Path=/; Max-Age=28800; HttpOnly; SameSite=Strict; Secure')
            handler.end_headers()
        except Exception as e:
            logger.error(f"Error handling login: {e}")
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(generate_login_page(
                "Login error occurred",
                touchid_available=touchid_available
            ).encode())


    # POST /reset-password - Handle password reset form submission
    def handle_password_reset_post(handler):
        """Handle password reset form submission"""
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

            new_password = data.get('new_password')

            if not new_password:
                send_json(handler, {'success': False, 'message': 'New password is required'})
                return

            # Update password
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            success, message = user_manager.force_password_update(
                username=username,
                new_password=new_password,
                updated_by=username
            )

            send_json(handler, {'success': success, 'message': message})
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/logout - API logout endpoint
    def handle_logout_api(handler):
        """API logout endpoint - returns 401 to clear credentials"""
        handler.send_response(401)
        handler.send_header('WWW-Authenticate', 'Basic realm="Fleet Dashboard"')
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'message': 'Logged out'}).encode())


    # ========== USER INFO ROUTES (GET) ==========

    # GET /api/fleet/current-user - Get current logged-in user info
    def handle_current_user(handler):
        """Get current logged-in user info"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            # Get session token from cookie
            session_token = auth_manager.get_session_token(handler)

            if session_token:
                from atlas.fleet_user_manager import FleetUserManager
                user_manager = FleetUserManager()

                # Decode session to get username and role
                try:
                    session_data = base64.b64decode(session_token).decode('utf-8')
                    username, role, _ = session_data.split(':')

                    send_json(handler, {'username': username, 'role': role})
                except (ValueError, KeyError, IndexError):
                    send_json(handler, {'username': 'unknown', 'role': 'unknown'})
            else:
                send_json(handler, {'username': 'guest', 'role': 'viewer'})
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/users/check-password-update - Check if password needs update
    def handle_check_password_update(handler):
        """Check if current user's password needs update"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            # Get session token from cookie
            session_token = auth_manager.get_session_token(handler)

            if session_token:
                from atlas.fleet_user_manager import FleetUserManager
                user_manager = FleetUserManager()

                # Decode session to get username
                try:
                    session_data = base64.b64decode(session_token).decode('utf-8')
                    username, _, _ = session_data.split(':')

                    # Check if password needs update
                    needs_update, reason = user_manager.check_password_needs_update(username)

                    send_json(handler, {'needs_update': needs_update, 'reason': reason})
                except (ValueError, KeyError, IndexError, UnicodeDecodeError):
                    send_json(handler, {'needs_update': False})
            else:
                send_json(handler, {'needs_update': False})
        except Exception as e:
            logger.error(f"Error checking password update: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/users - Get list of users
    def handle_users_list(handler):
        """Get list of all users"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            # Get all users
            users = user_manager.get_all_users()

            send_json(handler, {'users': users})
        except Exception as e:
            logger.error(f"Error getting users list: {e}")
            send_error(handler, 'Internal server error')


    # Register routes with router
    # Page routes
    router.get('/', handle_login_page)
    router.get('/login', handle_login_page)
    router.get('/logout', handle_logout_get)
    router.get('/dashboard', handle_dashboard_page)
    router.get('/settings', handle_settings_page)
    router.get('/password-reset', handle_password_reset_page)
    router.get('/machine/{identifier}', handle_machine_detail_page)
    router.get('/machine/{identifier}/dashboard', handle_machine_dashboard_redirect)

    # Authentication routes
    router.post('/login', handle_login_post)
    router.post('/reset-password', handle_password_reset_post)
    router.post('/api/fleet/logout', handle_logout_api)

    # User info routes
    router.get('/api/fleet/current-user', handle_current_user)
    router.get('/api/fleet/users/check-password-update', handle_check_password_update)
    router.get('/api/fleet/users', handle_users_list)


__all__ = ['register_ui_routes']
