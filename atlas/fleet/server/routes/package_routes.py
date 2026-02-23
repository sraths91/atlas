"""
Fleet Package Building Routes

Route handlers for package generation and distribution endpoints.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- Download agent installer (GET /api/fleet/download-installer)
- Build standalone agent package (POST /api/fleet/build-standalone-package)
- Build fleet-linked agent package (POST /api/fleet/build-agent-package)
- Build cluster node package (POST /api/fleet/build-cluster-package)
- Generate load balancer package (POST /api/fleet/generate-loadbalancer)
- Storage info page (GET /api/fleet/storage-info)
- ACME HTTP-01 challenge (GET /.well-known/acme-challenge/*)

Created: December 31, 2025
"""
import json
import logging
import tempfile
from pathlib import Path

from atlas.fleet.server.router import read_request_body

logger = logging.getLogger(__name__)


def register_package_routes(router, data_store, auth_manager, cluster_manager=None):
    """Register all package building and misc routes with the FleetRouter

    Args:
        router: FleetRouter instance
        data_store: FleetDataStore instance
        auth_manager: FleetAuthManager instance
        cluster_manager: FleetClusterManager instance (optional)
    """

    # Import page generators for storage-info
    from atlas.fleet_server import get_settings_info_html


    # GET /api/fleet/download-installer - Download agent installer package
    def handle_download_installer(handler):
        """Download agent installer package"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(401)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
            return

        try:
            # Import the builder
            from atlas.fleet_agent_builder import AgentPackageBuilder

            # Load config
            config_path = Path.home() / ".fleet-config.json"
            if not config_path.exists():
                handler.send_response(500)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({'error': 'Server not configured. Run setup wizard first.'}).encode())
                return

            # Build installer package
            builder = AgentPackageBuilder(config_path)
            package_path = builder.build_package()

            # Send the file
            with open(package_path, 'rb') as f:
                content = f.read()

            handler.send_response(200)
            handler.send_header('Content-Type', 'application/zip')
            handler.send_header('Content-Disposition', f'attachment; filename="{package_path.name}"')
            handler.send_header('Content-Length', len(content))
            handler.end_headers()
            handler.wfile.write(content)

            # Clean up temp file
            package_path.unlink()

        except Exception as e:
            logger.error(f"Error generating installer: {e}", exc_info=True)
            handler.send_response(500)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Failed to generate installer'}).encode())


    # POST /api/fleet/build-standalone-package or /api/fleet/build-agent-package
    def handle_build_agent_package(handler):
        """Build customized agent package (fleet-linked or standalone)"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(401)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
            return

        try:
            # Read configuration
            body = read_request_body(handler)
            if body is None:
                return
            request_data = json.loads(body.decode())

            is_standalone = request_data.get('standalone', True)
            package_name = request_data.get('package_name', 'Atlas.pkg')

            # Extract widget/tool configuration and ordering from request
            widget_config = request_data.get('widgets', None)
            tool_config = request_data.get('tools', None)
            widget_order = request_data.get('widget_order', None)
            tool_order = request_data.get('tool_order', None)
            standalone_options = request_data.get('standalone_options', None)

            # Import package builder class
            from atlas.fleet_agent_builder import AgentPackageBuilder

            # Build package in temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix='agent_pkg_'))

            if not is_standalone:
                # Fleet-linked: use default config path (handles encryption)
                config_path = Path.home() / ".fleet-config.json"
                if not config_path.exists() and not Path(str(config_path) + ".encrypted").exists():
                    handler.send_response(400)
                    handler.send_header('Content-type', 'application/json')
                    handler.end_headers()
                    handler.wfile.write(json.dumps({'error': 'Server configuration not found'}).encode())
                    return

                builder = AgentPackageBuilder(str(config_path))
                result_path = builder.build_package(
                    output_dir=str(temp_dir),
                    widget_config=widget_config,
                    tool_config=tool_config,
                    widget_order=widget_order,
                    tool_order=tool_order
                )
            else:
                # Standalone package - uses default config path
                builder = AgentPackageBuilder()
                result_path = builder.build_standalone_package(
                    output_dir=str(temp_dir),
                    widget_config=widget_config,
                    tool_config=tool_config,
                    widget_order=widget_order,
                    tool_order=tool_order,
                    standalone_options=standalone_options
                )

            # Builder returns a Path on success, None on failure
            result_path = Path(result_path) if result_path else None

            if result_path and result_path.exists():
                # Send the file
                with open(result_path, 'rb') as f:
                    content = f.read()

                # Determine content type from actual output file
                filename = result_path.name
                if filename.endswith('.pkg'):
                    content_type = 'application/vnd.apple.installer+xml'
                elif filename.endswith('.zip'):
                    content_type = 'application/zip'
                else:
                    content_type = 'application/octet-stream'

                handler.send_response(200)
                handler.send_header('Content-Type', content_type)
                handler.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                handler.send_header('Content-Length', len(content))
                handler.end_headers()
                handler.wfile.write(content)

                # Clean up temp file
                result_path.unlink(missing_ok=True)

            else:
                handler.send_response(500)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({'error': 'Failed to build package'}).encode())

        except Exception as e:
            logger.error(f"Error building agent package: {e}", exc_info=True)
            handler.send_response(500)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Failed to build package'}).encode())


    # POST /api/fleet/build-cluster-package - Build cluster node package
    def handle_build_cluster_package(handler):
        """Build cluster node installer package (and optionally load balancer)"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(401)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
            return

        try:
            # Check if cluster mode is enabled
            if not cluster_manager or not cluster_manager.enabled:
                handler.send_response(400)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({'error': 'Cluster mode not enabled'}).encode())
                return

            # Read configuration
            body = read_request_body(handler)
            if body is None:
                return
            request_data = json.loads(body.decode())

            node_name = request_data.get('node_name')
            package_name = request_data.get('package_name', 'FleetServerClusterNode.pkg')
            include_loadbalancer = request_data.get('include_loadbalancer', False)
            lb_port = request_data.get('lb_port', 8778)

            # Load current server configuration
            config_path = Path.home() / ".fleet-config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    server_config = json.load(f)
            else:
                server_config = {}

            # Import cluster package builder
            from atlas.cluster_pkg_builder import build_cluster_node_package

            # Build package in temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix='cluster_pkg_'))
            output_path = temp_dir / package_name

            success, message = build_cluster_node_package(
                server_config=server_config,
                output_path=str(output_path),
                node_name=node_name
            )

            if not success or not output_path.exists():
                handler.send_response(500)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({'error': message or 'Failed to build node package'}).encode())
                return

            # Build load balancer package if requested
            lb_output_path = None
            if include_loadbalancer:
                from atlas.loadbalancer_builder import build_loadbalancer_package

                # Get all cluster nodes
                nodes = cluster_manager.get_active_nodes()
                node_list = []
                for node in nodes:
                    node_list.append({
                        'id': node.node_id,
                        'host': node.host,
                        'port': 8778
                    })

                lb_package_name = 'FleetLoadBalancer.tar.gz'
                lb_output_path = temp_dir / lb_package_name

                lb_success, lb_message = build_loadbalancer_package(
                    output_path=str(lb_output_path),
                    nodes=node_list,
                    port=lb_port,
                    name='fleet-lb'
                )

                if not lb_success:
                    logger.warning(f"Load balancer package build failed: {lb_message}")
                    lb_output_path = None

            # If both packages built, create ZIP
            if lb_output_path and lb_output_path.exists():
                import zipfile

                zip_name = 'FleetClusterPackages.zip'
                zip_path = temp_dir / zip_name

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(output_path, arcname=package_name)
                    zipf.write(lb_output_path, arcname=lb_package_name)

                    # Add README
                    readme = f"""Fleet Server Cluster Packages

This ZIP contains:
1. {package_name} - Cluster node installer (install on Mac servers)
2. {lb_package_name} - Load balancer config (deploy on Linux/Docker)

Quick Start:
1. Install node package on each Mac server
2. Extract and deploy load balancer package
3. Access via load balancer at http://<lb-ip>:{lb_port}

See README.md in load balancer package for details.
"""
                    zipf.writestr('README.txt', readme)

                # Send ZIP
                with open(zip_path, 'rb') as f:
                    content = f.read()

                handler.send_response(200)
                handler.send_header('Content-Type', 'application/zip')
                handler.send_header('Content-Disposition', f'attachment; filename="{zip_name}"')
                handler.send_header('Content-Length', len(content))
                handler.end_headers()
                handler.wfile.write(content)

                logger.info(f"Cluster packages built: node + load balancer")
            else:
                # Just send node package
                with open(output_path, 'rb') as f:
                    content = f.read()

                # Use appropriate content type for .pkg files
                content_type = 'application/vnd.apple.installer+xml' if package_name.endswith('.pkg') else 'application/octet-stream'

                handler.send_response(200)
                handler.send_header('Content-Type', content_type)
                handler.send_header('Content-Disposition', f'attachment; filename="{package_name}"')
                handler.send_header('Content-Length', len(content))
                handler.end_headers()
                handler.wfile.write(content)

                logger.info(f"Cluster node package built: {package_name}")

            # Clean up
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except (OSError, IOError, PermissionError):
                pass

        except Exception as e:
            logger.error(f"Error building cluster package: {e}", exc_info=True)
            handler.send_response(500)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Failed to build cluster package'}).encode())


    # POST /api/fleet/generate-loadbalancer - Generate load balancer package
    def handle_generate_loadbalancer(handler):
        """Generate load balancer package (standalone feature)"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(401)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
            return

        try:
            # Read configuration
            body = read_request_body(handler)
            if body is None:
                return
            request_data = json.loads(body.decode())

            port = request_data.get('port', 8778)
            package_name = request_data.get('package_name', 'FleetLoadBalancer.tar.gz')

            from atlas.loadbalancer_builder import build_loadbalancer_package

            # Get cluster nodes if available
            node_list = []

            if cluster_manager and cluster_manager.enabled:
                # Get active cluster nodes
                nodes = cluster_manager.get_active_nodes()
                for node in nodes:
                    node_list.append({
                        'id': node.node_id,
                        'host': node.host,
                        'port': 8778
                    })
                logger.info(f"Generating load balancer for {len(node_list)} cluster nodes")
            else:
                # Standalone mode - generate template for future use
                # Use current server as example node
                import socket
                hostname = socket.gethostname()
                try:
                    local_ip = socket.gethostbyname(hostname)
                except (socket.gaierror, socket.herror, OSError):
                    local_ip = '127.0.0.1'

                node_list.append({
                    'id': 'server-01',
                    'host': local_ip,
                    'port': 8778
                })
                logger.info("Generating load balancer template for standalone server (future clustering)")

            # Build load balancer package
            temp_dir = Path(tempfile.mkdtemp(prefix='lb_pkg_'))
            output_path = temp_dir / package_name

            success, message = build_loadbalancer_package(
                output_path=str(output_path),
                nodes=node_list,
                port=port,
                name='fleet-lb'
            )

            if success and output_path.exists():
                # Send the file
                with open(output_path, 'rb') as f:
                    content = f.read()

                handler.send_response(200)
                handler.send_header('Content-Type', 'application/gzip')
                handler.send_header('Content-Disposition', f'attachment; filename="{package_name}"')
                handler.send_header('Content-Length', len(content))
                handler.end_headers()
                handler.wfile.write(content)

                logger.info(f"Load balancer package generated: {package_name}")

                # Clean up
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except (OSError, IOError, PermissionError):
                    pass
            else:
                handler.send_response(500)
                handler.send_header('Content-type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({'error': message or 'Failed to build load balancer package'}).encode())

        except Exception as e:
            logger.error(f"Error generating load balancer package: {e}", exc_info=True)
            handler.send_response(500)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Failed to generate load balancer package'}).encode())


    # GET /api/fleet/storage-info - Storage info page for settings
    def handle_storage_info(handler):
        """Get storage info page for settings"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            handler.send_response(302)
            handler.send_header('Location', '/login')
            handler.end_headers()
            return

        # Serve settings info HTML
        handler.send_response(200)
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        handler.wfile.write(get_settings_info_html(data_store).encode())


    # GET /.well-known/acme-challenge/* - ACME HTTP-01 challenge for Let's Encrypt
    def handle_acme_challenge(handler, challenge_token):
        """Handle ACME HTTP-01 challenge for Let's Encrypt"""
        try:
            # Check if we have a pending challenge for this token
            acme_challenge_dir = Path.home() / ".acme-challenges"
            challenge_file = acme_challenge_dir / challenge_token

            if challenge_file.exists():
                with open(challenge_file, 'r') as f:
                    challenge_response = f.read().strip()

                handler.send_response(200)
                handler.send_header('Content-Type', 'text/plain')
                handler.send_header('Content-Length', len(challenge_response))
                handler.end_headers()
                handler.wfile.write(challenge_response.encode())

                logger.info(f"Served ACME challenge: {challenge_token}")
            else:
                handler.send_error(404, "Challenge not found")
                logger.warning(f"ACME challenge not found: {challenge_token}")

        except Exception as e:
            logger.error(f"Error handling ACME challenge: {e}")
            handler.send_error(500, "Internal server error")


    # Register routes with router
    router.get('/api/fleet/download-installer', handle_download_installer)
    router.post('/api/fleet/build-standalone-package', handle_build_agent_package)
    router.post('/api/fleet/build-agent-package', handle_build_agent_package)
    router.post('/api/fleet/build-cluster-package', handle_build_cluster_package)
    router.post('/api/fleet/generate-loadbalancer', handle_generate_loadbalancer)
    router.get('/api/fleet/storage-info', handle_storage_info)
    router.get('/.well-known/acme-challenge/{token}', handle_acme_challenge)


__all__ = ['register_package_routes']
