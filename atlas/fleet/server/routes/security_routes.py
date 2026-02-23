"""
Fleet Security Routes

Route handlers for security monitoring endpoints.
Part of Phase 3 - Visualization Widgets implementation.

This module handles:
- Security status dashboard data
- Security event retrieval
- Security score reporting

Created: January 10, 2026
"""
import json
import logging
from typing import TYPE_CHECKING

from atlas.fleet.server.router import send_json, send_error
from atlas.config.defaults import safe_int_param

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

# Try to import security monitor with availability flag
try:
    from atlas.security_monitor import get_security_monitor
    SECURITY_MONITOR_AVAILABLE = True
except ImportError:
    SECURITY_MONITOR_AVAILABLE = False
    logger.warning("Security monitor not available")

# Try to import VPN monitor with availability flag
try:
    from atlas.network.monitors.vpn_monitor import get_vpn_monitor
    VPN_MONITOR_AVAILABLE = True
except ImportError:
    VPN_MONITOR_AVAILABLE = False
    logger.warning("VPN monitor not available")

# Try to import SaaS endpoint monitor with availability flag
try:
    from atlas.network.monitors.saas_endpoint_monitor import get_saas_endpoint_monitor
    SAAS_MONITOR_AVAILABLE = True
except ImportError:
    SAAS_MONITOR_AVAILABLE = False
    logger.warning("SaaS endpoint monitor not available")

# Try to import network quality monitor with availability flag
try:
    from atlas.network.monitors.network_quality_monitor import get_network_quality_monitor
    NETWORK_QUALITY_MONITOR_AVAILABLE = True
except ImportError:
    NETWORK_QUALITY_MONITOR_AVAILABLE = False
    logger.warning("Network quality monitor not available")

# Try to import WiFi roaming monitor with availability flag
try:
    from atlas.network.monitors.wifi_roaming_monitor import get_wifi_roaming_monitor
    WIFI_ROAMING_MONITOR_AVAILABLE = True
except ImportError:
    WIFI_ROAMING_MONITOR_AVAILABLE = False
    logger.warning("WiFi roaming monitor not available")

# Try to import application monitor with availability flag
try:
    from atlas.application_monitor import get_app_monitor
    APP_MONITOR_AVAILABLE = True
except ImportError:
    APP_MONITOR_AVAILABLE = False
    logger.warning("Application monitor not available")

# Try to import disk health monitor with availability flag
try:
    from atlas.disk_health_monitor import get_disk_monitor
    DISK_MONITOR_AVAILABLE = True
except ImportError:
    DISK_MONITOR_AVAILABLE = False
    logger.warning("Disk health monitor not available")

# Try to import software inventory monitor with availability flag
try:
    from atlas.software_inventory_monitor import get_software_monitor
    SOFTWARE_MONITOR_AVAILABLE = True
except ImportError:
    SOFTWARE_MONITOR_AVAILABLE = False
    logger.warning("Software inventory monitor not available")

# Try to import peripheral monitor with availability flag
try:
    from atlas.peripheral_monitor import get_peripheral_monitor
    PERIPHERAL_MONITOR_AVAILABLE = True
except ImportError:
    PERIPHERAL_MONITOR_AVAILABLE = False
    logger.warning("Peripheral monitor not available")

# Try to import power monitor with availability flag
try:
    from atlas.power_monitor import get_power_monitor
    POWER_MONITOR_AVAILABLE = True
except ImportError:
    POWER_MONITOR_AVAILABLE = False
    logger.warning("Power monitor not available")

# Try to import display monitor with availability flag
try:
    from atlas.display_monitor import get_display_monitor
    DISPLAY_MONITOR_AVAILABLE = True
except ImportError:
    DISPLAY_MONITOR_AVAILABLE = False
    logger.warning("Display monitor not available")


def register_security_routes(router):
    """Register all security-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
    """

    # GET /api/security/status - Get security status for dashboard widget
    def handle_security_status(handler):
        """Get current security status and events for Security Dashboard widget"""
        if not SECURITY_MONITOR_AVAILABLE:
            send_error(handler, 'Security monitor not available', status=503)
            return

        try:
            # Get security monitor instance
            monitor = get_security_monitor()

            # Get current security status
            status = monitor.get_current_security_status()

            # Get recent security events
            events = monitor.get_security_events()

            # Format response for widget
            response = {
                'security_score': status.get('security_score', 0),
                'firewall_enabled': status.get('firewall', {}).get('enabled', False),
                'filevault_enabled': status.get('filevault', {}).get('enabled', False),
                'gatekeeper_enabled': status.get('gatekeeper', {}).get('enabled', False),
                'sip_enabled': status.get('sip', {}).get('enabled', False),
                'screen_lock_enabled': status.get('screen_lock', {}).get('enabled', False),
                'auto_updates_enabled': status.get('updates', {}).get('auto_updates_enabled', False),
                'pending_updates': status.get('updates', {}).get('security_updates_count', 0),
                'recent_events': []
            }

            # Format recent events for widget (limit to 10)
            for event in events[:10]:
                response['recent_events'].append({
                    'timestamp': event.get('timestamp', ''),
                    'severity': event.get('severity', 'medium'),
                    'message': event.get('message', ''),
                    'details': event.get('details', '')
                })

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting security status: {e}")
            send_error(handler, 'Internal server error')

    # GET /api/security/events - Get recent security events with filtering
    def handle_security_events(handler):
        """Get security events with optional filtering"""
        if not SECURITY_MONITOR_AVAILABLE:
            send_error(handler, 'Security monitor not available', status=503)
            return

        try:
            # Parse query parameters
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(handler.path)
            params = parse_qs(parsed.query)

            limit = safe_int_param(params, 'limit', 100, max_val=10000)
            severity = params.get('severity', [None])[0]

            # Get security monitor instance
            monitor = get_security_monitor()

            # Get security events
            events = monitor.get_security_events()

            # Filter by severity if specified
            if severity:
                events = [e for e in events if e.get('severity') == severity]

            # Limit results
            events = events[:limit]

            # Send response
            send_json(handler, {
                'events': events,
                'count': len(events)
            })

        except Exception as e:
            logger.error(f"Error getting security events: {e}")
            send_error(handler, 'Internal server error')

    # GET /api/security/score - Get current security score
    def handle_security_score(handler):
        """Get current security score only"""
        if not SECURITY_MONITOR_AVAILABLE:
            send_error(handler, 'Security monitor not available', status=503)
            return

        try:
            # Get security monitor instance
            monitor = get_security_monitor()

            # Get current security status
            status = monitor.get_current_security_status()

            # Send response
            send_json(handler, {
                'security_score': status.get('security_score', 0)
            })

        except Exception as e:
            logger.error(f"Error getting security score: {e}")
            send_error(handler, 'Internal server error')

    # GET /api/vpn/status - Get VPN connection status
    def handle_vpn_status(handler):
        """Get current VPN status for VPN Status widget"""
        if not VPN_MONITOR_AVAILABLE:
            send_error(handler, 'VPN monitor not available', status=503, extra={'connected': False, 'vpn_client': None})
            return

        try:
            # Get VPN monitor instance
            monitor = get_vpn_monitor()

            # Get current status
            status = monitor.get_current_status()

            # Get recent events
            events = monitor.get_events(hours=24)

            # Detect split tunnel (simplified check based on available data)
            split_tunnel = False
            for event in events:
                if event.get('event_type') == 'split_tunnel_detected':
                    split_tunnel = True
                    break

            # Format response for widget
            response = {
                'connected': status.get('connected', False),
                'vpn_client': status.get('vpn_client'),
                'connection_count': status.get('connection_count', 0),
                'interfaces': list(status.get('interfaces', {}).keys()),
                'split_tunnel': split_tunnel,
                'recent_events': []
            }

            # Format recent events for widget (limit to 20)
            for event in events[:20]:
                response['recent_events'].append({
                    'timestamp': event.get('timestamp', ''),
                    'event_type': event.get('event_type', 'unknown'),
                    'details': event.get('details', ''),
                    'interface': event.get('interface', '')
                })

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting VPN status: {e}")
            send_error(handler, 'Internal server error', extra={'connected': False})

    # GET /api/saas/health - Get SaaS endpoint health status
    def handle_saas_health(handler):
        """Get SaaS endpoint health for SaaS Health widget"""
        if not SAAS_MONITOR_AVAILABLE:
            send_error(handler, 'SaaS endpoint monitor not available', status=503, extra={'summary': {'avg_availability': 0, 'services_up': 0, 'total_services': 0}})
            return

        try:
            # Get SaaS monitor instance
            monitor = get_saas_endpoint_monitor()

            # Get current status of all endpoints
            current_status = monitor.get_current_status()

            # Get category summary
            category_summary = monitor.get_category_summary()

            # Get recent incidents
            incidents_data = monitor.incidents_logger.get_history()

            # Calculate overall summary
            total_services = len(current_status)
            services_up = sum(1 for s in current_status.values() if s.get('reachable'))

            # Calculate average availability and latency
            avg_availability = 0
            avg_latency = 0
            if total_services > 0:
                avg_availability = (services_up / total_services) * 100
                latencies = [float(s.get('latency_ms', 0)) for s in current_status.values()
                           if s.get('reachable') and s.get('latency_ms')]
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)

            # Format response for widget
            response = {
                'summary': {
                    'avg_availability': round(avg_availability, 2),
                    'avg_latency': round(avg_latency, 2),
                    'services_up': services_up,
                    'total_services': total_services
                },
                'categories': category_summary,
                'services': [
                    {
                        'endpoint_name': name,
                        'host': status.get('host', ''),
                        'category': status.get('category', 'Unknown'),
                        'reachable': status.get('reachable', False),
                        'latency_ms': status.get('latency_ms', 0),
                        'error': status.get('error', '')
                    }
                    for name, status in current_status.items()
                ],
                'incidents': []
            }

            # Format recent incidents (limit to 20)
            for incident in incidents_data[:20]:
                response['incidents'].append({
                    'timestamp': incident.get('timestamp', ''),
                    'endpoint_name': incident.get('endpoint_name', ''),
                    'category': incident.get('category', ''),
                    'incident_type': incident.get('incident_type', ''),
                    'duration_seconds': incident.get('duration_seconds', 0),
                    'details': incident.get('details', '')
                })

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting SaaS health: {e}")
            send_error(handler, 'Internal server error', extra={'summary': {'avg_availability': 0, 'services_up': 0, 'total_services': 0}})

    # GET /api/network/quality - Get network quality metrics
    def handle_network_quality(handler):
        """Get network quality metrics for Network Quality widget"""
        if not NETWORK_QUALITY_MONITOR_AVAILABLE:
            send_error(handler, 'Network quality monitor not available', status=503, extra={'tcp': {}, 'dns': {}, 'tls': {}, 'http': {}})
            return

        try:
            # Get network quality monitor instance
            monitor = get_network_quality_monitor()

            # Get current quality summary
            summary = monitor.get_quality_summary()

            # Format response for widget
            response = {
                'tcp': {
                    'avg_retransmit_rate_percent': summary.get('tcp', {}).get('avg_retransmit_rate_percent', 0),
                    'max_retransmit_rate_percent': summary.get('tcp', {}).get('max_retransmit_rate_percent', 0),
                    'sample_count': summary.get('tcp', {}).get('sample_count', 0)
                },
                'dns': {
                    'availability_percent': summary.get('dns', {}).get('availability_percent', 0),
                    'avg_query_time_ms': summary.get('dns', {}).get('avg_query_time_ms', 0),
                    'max_query_time_ms': summary.get('dns', {}).get('max_query_time_ms', 0)
                },
                'tls': {
                    'success_rate_percent': summary.get('tls', {}).get('success_rate_percent', 0),
                    'avg_handshake_time_ms': summary.get('tls', {}).get('avg_handshake_time_ms', 0),
                    'max_handshake_time_ms': summary.get('tls', {}).get('max_handshake_time_ms', 0)
                },
                'http': {
                    'success_rate_percent': summary.get('http', {}).get('success_rate_percent', 0),
                    'avg_response_time_ms': summary.get('http', {}).get('avg_response_time_ms', 0),
                    'max_response_time_ms': summary.get('http', {}).get('max_response_time_ms', 0)
                }
            }

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting network quality: {e}")
            send_error(handler, 'Internal server error', extra={'tcp': {}, 'dns': {}, 'tls': {}, 'http': {}})

    # GET /api/wifi/roaming - Get WiFi roaming metrics
    def handle_wifi_roaming(handler):
        """Get WiFi roaming metrics for WiFi Roaming widget"""
        if not WIFI_ROAMING_MONITOR_AVAILABLE:
            send_error(handler, 'WiFi roaming monitor not available', status=503, extra={'current': {}, 'statistics': {}, 'events': []})
            return

        try:
            # Get WiFi roaming monitor instance
            monitor = get_wifi_roaming_monitor()

            # Get current WiFi status
            current_status = monitor.get_current_status()

            # Get roaming events
            events = monitor.get_roaming_events(hours=24)

            # Get roaming statistics
            stats = monitor.get_roaming_statistics(hours=24)

            # Get signal history
            signal_history = monitor.get_signal_history(hours=1)

            # Get channel utilization
            channel_util = monitor.get_channel_utilization()

            # Check for sticky client
            sticky_detected = any(e.get('event_type') == 'sticky_client_detected' for e in events[:5])

            # Format response for widget
            response = {
                'current': {
                    'ssid': current_status.get('ssid', ''),
                    'bssid': current_status.get('bssid', ''),
                    'channel': current_status.get('channel', 0),
                    'rssi': current_status.get('rssi', 0)
                },
                'statistics': {
                    'roam_count': stats.get('total_roams', 0),
                    'avg_roam_latency_ms': stats.get('avg_roam_latency_ms', 0),
                    'sticky_client_count': stats.get('sticky_client_count', 0),
                    'unique_aps': stats.get('unique_aps', 0)
                },
                'sticky_client_detected': sticky_detected,
                'channel_utilization': channel_util,
                'signal_history': signal_history,
                'events': []
            }

            # Format events (limit to 20)
            for event in events[:20]:
                response['events'].append({
                    'timestamp': event.get('timestamp', ''),
                    'event_type': event.get('event_type', ''),
                    'from_bssid': event.get('from_bssid', ''),
                    'to_bssid': event.get('to_bssid', ''),
                    'roam_latency_ms': event.get('roam_latency_ms', 0),
                    'details': event.get('details', '')
                })

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting WiFi roaming data: {e}")
            send_error(handler, 'Internal server error', extra={'current': {}, 'statistics': {}, 'events': []})

    # GET /api/applications/crashes - Get application crash data
    def handle_app_crashes(handler):
        """Get application crash data for APM widget"""
        if not APP_MONITOR_AVAILABLE:
            send_error(handler, 'Application monitor not available', status=503, extra={'summary': {}, 'recent_crashes': []})
            return

        try:
            # Get application monitor instance
            monitor = get_app_monitor()

            # Get crash summary
            summary = monitor.get_crash_summary(hours=24)

            # Get recent crashes
            recent_crashes = monitor.get_recent_crashes(hours=24)

            # Get top resource consumers
            top_cpu = monitor.get_top_resource_consumers(metric='cpu', limit=10)
            top_memory = monitor.get_top_resource_consumers(metric='memory', limit=10)

            # Format response for widget
            response = {
                'summary': summary,
                'recent_crashes': recent_crashes[:20],  # Limit to 20
                'top_cpu_consumers': top_cpu,
                'top_memory_consumers': top_memory
            }

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting application crash data: {e}")
            send_error(handler, 'Internal server error', extra={'summary': {}, 'recent_crashes': []})

    # GET /api/disk/health - Get disk health data
    def handle_disk_health(handler):
        """Get disk health data for Disk Health widget"""
        if not DISK_MONITOR_AVAILABLE:
            send_error(handler, 'Disk health monitor not available', status=503, extra={'health_summary': {}, 'storage_summary': {}})
            return

        try:
            # Get disk health monitor instance
            monitor = get_disk_monitor()

            # Get disk health summary
            health_summary = monitor.get_disk_health_summary()

            # Get storage summary
            storage_summary = monitor.get_storage_summary()

            # Format response for widget
            response = {
                'health_summary': health_summary,
                'storage_summary': storage_summary
            }

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting disk health data: {e}")
            send_error(handler, 'Internal server error', extra={'health_summary': {}, 'storage_summary': {}})

    # GET /api/software/inventory - Get software inventory
    def handle_software_inventory(handler):
        """Get software inventory for Software Inventory widget"""
        if not SOFTWARE_MONITOR_AVAILABLE:
            send_error(handler, 'Software inventory monitor not available', status=503, extra={'summary': {}, 'outdated_software': []})
            return

        try:
            # Get software monitor instance
            monitor = get_software_monitor()

            # Get inventory summary
            summary = monitor.get_inventory_summary()

            # Get outdated software
            outdated = monitor.check_outdated_software()

            # Get application list (top 50 by size)
            inventory = monitor.get_application_inventory()
            app_list = sorted(
                inventory.values(),
                key=lambda x: x.get('size_mb', 0),
                reverse=True
            )[:50]

            # Format response for widget
            response = {
                'summary': summary,
                'outdated_software': outdated,
                'top_applications': [
                    {
                        'name': app['name'],
                        'version': app['version'],
                        'size_mb': app['size_mb'],
                        'is_system': app.get('is_system', False)
                    }
                    for app in app_list
                ]
            }

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting software inventory: {e}")
            send_error(handler, 'Internal server error', extra={'summary': {}, 'outdated_software': []})

    # GET /api/peripherals/devices - Get peripheral device inventory
    def handle_peripheral_devices(handler):
        """Get peripheral device inventory for Peripheral Devices widget"""
        if not PERIPHERAL_MONITOR_AVAILABLE:
            send_error(handler, 'Peripheral monitor not available', status=503, extra={'summary': {}, 'devices': {}, 'recent_events': []})
            return

        try:
            # Get peripheral monitor instance
            monitor = get_peripheral_monitor()

            # Get peripheral summary
            summary = monitor.get_peripheral_summary()

            # Get connected devices
            devices = monitor.get_connected_devices()

            # Get recent events (last 24 hours)
            recent_events = monitor.get_recent_events(hours=24, limit=20)

            # Format response for widget
            response = {
                'summary': summary,
                'devices': {
                    'bluetooth': devices.get('bluetooth', []),
                    'usb': devices.get('usb', []),
                    'thunderbolt': devices.get('thunderbolt', [])
                },
                'recent_events': recent_events
            }

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting peripheral devices: {e}")
            send_error(handler, 'Internal server error', extra={'summary': {}, 'devices': {}, 'recent_events': []})

    # GET /api/power/status - Get power and battery status
    def handle_power_status(handler):
        """Get power metrics for Power/Battery Health widget"""
        if not POWER_MONITOR_AVAILABLE:
            send_error(handler, 'Power monitor not available', status=503, extra={'battery': {}, 'thermal': {}, 'recent_events': []})
            return

        try:
            # Get power monitor instance
            monitor = get_power_monitor()

            # Get power summary
            summary = monitor.get_power_summary()

            # Format response for widget
            response = {
                'battery': summary.get('battery', {}),
                'thermal': summary.get('thermal', {}),
                'recent_events': summary.get('recent_events', []),
                'total_power_events': summary.get('total_power_events', 0)
            }

            # Send response
            send_json(handler, response)

        except Exception as e:
            logger.error(f"Error getting power status: {e}")
            send_error(handler, 'Internal server error', extra={'battery': {}, 'thermal': {}, 'recent_events': []})

    def handle_display_status(handler: 'BaseHTTPRequestHandler'):
        """Get display and GPU status for Display/Graphics widget"""
        if not DISPLAY_MONITOR_AVAILABLE:
            send_error(handler, 'Display monitor not available', status=503, extra={'display': {}, 'gpu': {}, 'status': 'unavailable'})
            return

        try:
            # Get display monitor instance
            monitor = get_display_monitor()

            # Get combined status
            status = monitor.get_status()

            # Send response
            send_json(handler, status)

        except Exception as e:
            logger.error(f"Error getting display status: {e}")
            send_error(handler, 'Internal server error', extra={'display': {}, 'gpu': {}, 'status': 'error'})

    # Register routes
    router.get('/api/security/status', handle_security_status)
    router.get('/api/security/events', handle_security_events)
    router.get('/api/security/score', handle_security_score)
    router.get('/api/vpn/status', handle_vpn_status)  # VPN status endpoint
    router.get('/api/saas/health', handle_saas_health)  # SaaS health endpoint
    router.get('/api/network/quality', handle_network_quality)  # Network quality endpoint
    router.get('/api/wifi/roaming', handle_wifi_roaming)  # WiFi roaming endpoint
    router.get('/api/applications/crashes', handle_app_crashes)  # Application monitoring endpoint
    router.get('/api/disk/health', handle_disk_health)  # Disk health endpoint
    router.get('/api/software/inventory', handle_software_inventory)  # Software inventory endpoint
    router.get('/api/peripherals/devices', handle_peripheral_devices)  # Peripheral devices endpoint
    router.get('/api/power/status', handle_power_status)  # Power and battery status endpoint
    router.get('/api/display/status', handle_display_status)  # Display and GPU status endpoint


# Export
__all__ = ['register_security_routes']
