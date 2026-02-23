"""
API routes for the agent dashboard.

Handles all GET /api/* and POST /api/* routes.
"""
import json
import time
import logging

from atlas.config.defaults import safe_int_param
from atlas.system_health_widget import get_system_health
from atlas.system_monitor_widget import get_comprehensive_system_stats
from atlas.pressure_logger import get_pressure_logger
from atlas.process_widget import process_monitor
from atlas.network.monitors.wifi import get_wifi_monitor
from atlas.dashboard_preferences import (
    get_dashboard_preferences, CATEGORIES
)

# Optional Phase 4 monitors
try:
    from atlas.display_monitor import get_display_monitor
    DISPLAY_MONITOR_AVAILABLE = True
except ImportError:
    DISPLAY_MONITOR_AVAILABLE = False

try:
    from atlas.power_monitor import get_power_monitor
    POWER_MONITOR_AVAILABLE = True
except ImportError:
    POWER_MONITOR_AVAILABLE = False

try:
    from atlas.peripheral_monitor import get_peripheral_monitor
    PERIPHERAL_MONITOR_AVAILABLE = True
except ImportError:
    PERIPHERAL_MONITOR_AVAILABLE = False

try:
    from atlas.security_monitor import get_security_monitor
    SECURITY_MONITOR_AVAILABLE = True
except ImportError:
    SECURITY_MONITOR_AVAILABLE = False

try:
    from atlas.disk_health_monitor import get_disk_monitor
    DISK_MONITOR_AVAILABLE = True
except ImportError:
    DISK_MONITOR_AVAILABLE = False

try:
    from atlas.software_inventory_monitor import get_software_monitor
    SOFTWARE_MONITOR_AVAILABLE = True
except ImportError:
    SOFTWARE_MONITOR_AVAILABLE = False

try:
    from atlas.application_monitor import get_app_monitor
    APP_MONITOR_AVAILABLE = True
except ImportError:
    APP_MONITOR_AVAILABLE = False

logger = logging.getLogger(__name__)


def _get_speed_test_monitor():
    from atlas.network.monitors.speedtest import get_speed_test_monitor
    return get_speed_test_monitor()


def _get_ping_monitor():
    from atlas.network.monitors.ping import PingMonitor
    if not hasattr(_get_ping_monitor, '_instance'):
        _get_ping_monitor._instance = PingMonitor()
    return _get_ping_monitor._instance


def dispatch_get(handler, path):
    """Handle GET requests for API data endpoints.

    Args:
        handler: LiveWidgetHandler instance
        path: URL path (without query string)

    Returns:
        True if the request was handled, False otherwise
    """
    # ==================== Dashboard Layout ====================

    if path == '/api/dashboard/layout':
        prefs = get_dashboard_preferences()
        handler.serve_json({
            'layout': prefs.get_layout(),
            'widgets': prefs.get_all_widgets_with_state(),
            'categories': CATEGORIES,
        })

    elif path == '/api/dashboard/widgets':
        prefs = get_dashboard_preferences()
        handler.serve_json({
            'widgets': prefs.get_all_widgets_with_state(),
            'categories': CATEGORIES,
        })

    # ==================== System Metrics ====================

    elif path == '/api/system/comprehensive':
        handler.serve_json(get_comprehensive_system_stats())

    elif path == '/api/metrics/aggregated':
        from atlas.database import get_database
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 24, max_val=8760)
        interval = safe_int_param(params, 'interval', 5, max_val=1440)

        db = get_database()
        data = db.get_aggregated_metrics(hours=hours, interval_minutes=interval)
        handler.serve_json(data)

    elif path == '/api/metrics/history':
        from atlas.database import get_database
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 24, max_val=8760)
        limit = safe_int_param(params, 'limit', 1000, max_val=10000)

        db = get_database()
        metrics = db.get_metrics(hours=hours, limit=limit)
        handler.serve_json({'metrics': metrics, 'count': len(metrics)})

    # ==================== Pressure ====================

    elif path == '/api/pressure/history/10m':
        handler.serve_json(get_pressure_logger().get_history('10m'))

    elif path == '/api/pressure/history/1h':
        handler.serve_json(get_pressure_logger().get_history('1h'))

    elif path == '/api/pressure/history/24h':
        handler.serve_json(get_pressure_logger().get_history('24h'))

    elif path == '/api/pressure/history/7d':
        handler.serve_json(get_pressure_logger().get_history('7d'))

    elif path == '/api/pressure/current':
        handler.serve_json(get_pressure_logger().get_current())

    # ==================== WebSocket ====================

    elif path == '/api/stream':
        handler.handle_websocket()

    # ==================== System Stats ====================

    elif path == '/api/stats':
        handler.serve_json(handler.get_current_stats())

    elif path == '/api/health':
        handler.serve_json(get_system_health())

    # ==================== Speed Test ====================

    elif path == '/api/speedtest':
        monitor = _get_speed_test_monitor()
        handler.serve_json(monitor.get_last_result())

    elif path == '/api/speedtest/history':
        monitor = _get_speed_test_monitor()
        handler.serve_json(monitor.get_history())

    elif path == '/api/speedtest/slow-status':
        monitor = _get_speed_test_monitor()
        handler.serve_json(monitor.get_slow_speed_status())

    elif path == '/api/speedtest/mode':
        monitor = _get_speed_test_monitor()
        handler.serve_json(monitor.get_mode_info())

    # ==================== Hardware Monitors ====================

    elif path == '/api/display/status':
        if DISPLAY_MONITOR_AVAILABLE:
            monitor = get_display_monitor()
            handler.serve_json(monitor.get_status())
        else:
            handler.serve_json({'error': 'Display monitor not available', 'status': 'unavailable'})

    elif path == '/api/power/status':
        if POWER_MONITOR_AVAILABLE:
            monitor = get_power_monitor()
            handler.serve_json(monitor.get_power_summary())
        else:
            handler.serve_json({'error': 'Power monitor not available', 'status': 'unavailable'})

    elif path == '/api/peripherals/devices':
        if PERIPHERAL_MONITOR_AVAILABLE:
            monitor = get_peripheral_monitor()
            handler.serve_json(monitor.get_connected_devices('all'))
        else:
            handler.serve_json({'error': 'Peripheral monitor not available', 'status': 'unavailable'})

    elif path == '/api/security/status':
        if SECURITY_MONITOR_AVAILABLE:
            monitor = get_security_monitor()
            handler.serve_json(monitor.get_current_security_status())
        else:
            handler.serve_json({'error': 'Security monitor not available', 'status': 'unavailable'})

    elif path == '/api/disk/health':
        if DISK_MONITOR_AVAILABLE:
            monitor = get_disk_monitor()
            handler.serve_json(monitor.get_disk_health_summary())
        else:
            handler.serve_json({'error': 'Disk monitor not available', 'status': 'unavailable'})

    elif path == '/api/disk/status':
        if DISK_MONITOR_AVAILABLE:
            monitor = get_disk_monitor()
            result = monitor.get_detailed_disk_status()
            handler.serve_json(result)
        else:
            handler.serve_json({'error': 'Disk monitor not available', 'status': 'unavailable'})

    elif path == '/api/software/inventory':
        if SOFTWARE_MONITOR_AVAILABLE:
            monitor = get_software_monitor()
            handler.serve_json(monitor.get_inventory_summary())
        else:
            handler.serve_json({'error': 'Software monitor not available', 'status': 'unavailable'})

    elif path == '/api/applications/status':
        if APP_MONITOR_AVAILABLE:
            monitor = get_app_monitor()
            handler.serve_json(monitor.get_crash_summary())
        else:
            handler.serve_json({'error': 'Application monitor not available', 'status': 'unavailable'})

    elif path == '/api/system-health/overview':
        _handle_system_health_overview(handler)

    # ==================== Ping ====================

    elif path == '/api/ping':
        monitor = _get_ping_monitor()
        handler.serve_json(monitor.get_last_result())

    elif path == '/api/ping/stats':
        monitor = _get_ping_monitor()
        handler.serve_json(monitor.get_stats())

    elif path == '/api/ping/history':
        monitor = _get_ping_monitor()
        handler.serve_json(monitor.get_history())

    elif path == '/api/ping/local-ip':
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except (OSError, socket.error):
            local_ip = 'localhost'
        handler.serve_json({'local_ip': local_ip})

    # ==================== Network Quality ====================

    elif path == '/api/network/udp-quality':
        try:
            from atlas.network.monitors import get_udp_quality_monitor
            monitor = get_udp_quality_monitor()
            result = monitor.get_last_result()
            if not result or result.get('status') == 'idle':
                ping_monitor = _get_ping_monitor()
                ping_data = ping_monitor.get_stats()
                result = {
                    'status': 'estimated',
                    'jitter_ms': 0,
                    'packet_loss_percent': 0,
                    'latency_ms': ping_data.get('avg_latency', 0),
                    'note': 'UDP test not yet run - using ping estimates'
                }
            handler.serve_json(result)
        except Exception as e:
            handler.serve_json({'error': str(e), 'jitter_ms': 0, 'packet_loss_percent': 0})

    elif path == '/api/network/mos':
        try:
            from atlas.network.monitors import estimate_mos_simple, get_mos_color
            ping_monitor = _get_ping_monitor()
            ping_data = ping_monitor.get_stats()
            latency = ping_data.get('avg_latency', 0)
            jitter = abs(ping_data.get('max_latency', 0) - ping_data.get('min_latency', 0)) / 2
            packet_loss = 100 - ping_data.get('success_rate', 100)

            mos, rating = estimate_mos_simple(latency, jitter, packet_loss)
            handler.serve_json({
                'mos': mos,
                'rating': rating,
                'color': get_mos_color(mos),
                'input': {
                    'latency_ms': latency,
                    'jitter_ms': jitter,
                    'packet_loss_percent': packet_loss
                }
            })
        except Exception as e:
            handler.serve_json({'error': str(e), 'mos': 1.0, 'rating': 'unknown'})

    elif path == '/api/network/quality':
        try:
            from atlas.network.monitors.network_quality_monitor import get_network_quality_monitor
            monitor = get_network_quality_monitor()
            summary = monitor.get_quality_summary()
            handler.serve_json(summary)
        except Exception as e:
            logger.error(f"Error getting network quality: {e}")
            handler.serve_json({
                'tcp': {'avg_retransmit_rate_percent': 0, 'max_retransmit_rate_percent': 0, 'sample_count': 0},
                'dns': {'availability_percent': 0, 'avg_query_time_ms': 0, 'max_query_time_ms': 0, 'sample_count': 0},
                'tls': {'success_rate_percent': 0, 'avg_handshake_time_ms': 0, 'max_handshake_time_ms': 0, 'sample_count': 0},
                'http': {'success_rate_percent': 0, 'avg_response_time_ms': 0, 'max_response_time_ms': 0, 'sample_count': 0}
            })

    elif path == '/api/saas/health':
        _handle_saas_health(handler)

    # ==================== WiFi ====================

    elif path == '/api/wifi':
        monitor = get_wifi_monitor()
        handler.serve_json(monitor.get_last_result())

    elif path == '/api/wifi/history':
        monitor = get_wifi_monitor()
        handler.serve_json(monitor.get_history())

    elif path == '/api/wifi/diagnosis':
        monitor = get_wifi_monitor()
        diagnosis = monitor.get_last_diagnosis()
        if diagnosis:
            handler.serve_json(diagnosis)
        else:
            diagnosis = monitor.run_diagnostics_now()
            handler.serve_json(diagnosis)

    elif path == '/api/wifi/diagnose':
        monitor = get_wifi_monitor()
        diagnosis = monitor.run_diagnostics_now()
        handler.serve_json(diagnosis)

    elif path == '/api/wifi/signal/history/10m':
        from atlas.wifi_analyzer import get_wifi_signal_logger
        handler.serve_json(get_wifi_signal_logger().get_history('10m'))

    elif path == '/api/wifi/signal/history/1h':
        from atlas.wifi_analyzer import get_wifi_signal_logger
        handler.serve_json(get_wifi_signal_logger().get_history('1h'))

    elif path == '/api/wifi/signal/history/24h':
        from atlas.wifi_analyzer import get_wifi_signal_logger
        handler.serve_json(get_wifi_signal_logger().get_history('24h'))

    elif path == '/api/wifi/signal/history/7d':
        from atlas.wifi_analyzer import get_wifi_signal_logger
        handler.serve_json(get_wifi_signal_logger().get_history('7d'))

    elif path == '/api/wifi/signal/current':
        from atlas.wifi_analyzer import get_wifi_signal_logger
        handler.serve_json(get_wifi_signal_logger().get_current())

    elif path == '/api/wifi/nearby':
        from atlas.wifi_analyzer import get_nearby_scanner
        networks = get_nearby_scanner().scan_networks()
        handler.serve_json({
            'networks': networks,
            'count': len(networks),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        })

    elif path == '/api/wifi/channels':
        from atlas.wifi_analyzer import get_nearby_scanner
        handler.serve_json(get_nearby_scanner().get_channel_analysis())

    elif path == '/api/wifi/spectrum':
        from atlas.wifi_analyzer import get_nearby_scanner
        handler.serve_json(get_nearby_scanner().get_spectrum_data())

    elif path == '/api/wifi/alias/current':
        from atlas.wifi_analyzer import get_network_alias_manager
        manager = get_network_alias_manager()
        fingerprint = manager.get_current_fingerprint()
        alias = manager.get_alias(fingerprint) if fingerprint else None
        handler.serve_json({
            'fingerprint': fingerprint,
            'alias': alias,
            'has_alias': alias is not None
        })

    elif path == '/api/wifi/alias/all':
        from atlas.wifi_analyzer import get_network_alias_manager
        manager = get_network_alias_manager()
        aliases = manager.get_all_aliases()
        handler.serve_json({
            'aliases': aliases,
            'count': len(aliases)
        })

    # ==================== Speed Correlation ====================

    elif path == '/api/speed-correlation/analysis':
        from urllib.parse import urlparse, parse_qs
        from atlas.speed_correlation import get_speed_correlation_analyzer
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 168, max_val=8760)
        analyzer = get_speed_correlation_analyzer()
        handler.serve_json(analyzer.get_correlation_analysis(hours))

    elif path == '/api/speed-correlation/data':
        from urllib.parse import urlparse, parse_qs
        from atlas.speed_correlation import get_speed_correlation_analyzer
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 168, max_val=8760)
        analyzer = get_speed_correlation_analyzer()
        handler.serve_json({
            'data': analyzer.get_correlated_data(hours),
            'hours': hours
        })

    elif path == '/api/speed-correlation/summary':
        from atlas.speed_correlation import get_speed_correlation_analyzer
        analyzer = get_speed_correlation_analyzer()
        handler.serve_json(analyzer.get_summary())

    # ==================== WiFi Roaming ====================

    elif path == '/api/wifi/roaming':
        _handle_wifi_roaming(handler)

    elif path == '/api/wifi/roaming/events':
        from urllib.parse import urlparse, parse_qs
        from atlas.wifi_roaming import get_wifi_roaming_tracker
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 24, max_val=8760)
        event_type = params.get('type', [None])[0]
        tracker = get_wifi_roaming_tracker()
        handler.serve_json({
            'events': tracker.get_events(hours, event_type),
            'hours': hours
        })

    elif path == '/api/wifi/roaming/sessions':
        from urllib.parse import urlparse, parse_qs
        from atlas.wifi_roaming import get_wifi_roaming_tracker
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 24, max_val=8760)
        tracker = get_wifi_roaming_tracker()
        handler.serve_json({
            'sessions': tracker.get_sessions(hours),
            'hours': hours
        })

    elif path == '/api/wifi/roaming/stats':
        from urllib.parse import urlparse, parse_qs
        from atlas.wifi_roaming import get_wifi_roaming_tracker
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 24, max_val=8760)
        tracker = get_wifi_roaming_tracker()
        handler.serve_json(tracker.get_statistics(hours))

    elif path == '/api/wifi/roaming/timeline':
        from urllib.parse import urlparse, parse_qs
        from atlas.wifi_roaming import get_wifi_roaming_tracker
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 24, max_val=8760)
        tracker = get_wifi_roaming_tracker()
        handler.serve_json({
            'timeline': tracker.get_timeline(hours),
            'hours': hours
        })

    elif path == '/api/wifi/roaming/current':
        from atlas.wifi_roaming import get_wifi_roaming_tracker
        tracker = get_wifi_roaming_tracker()
        handler.serve_json(tracker.get_current_state())

    # ==================== Processes ====================

    elif path == '/api/processes':
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        sort_by = params.get('sort', ['cpu'])[0]
        limit = safe_int_param(params, 'limit', 10, max_val=10000)
        processes = process_monitor.get_top_processes(sort_by=sort_by, limit=limit)
        running = sum(1 for p in processes if p['status'] == 'running')
        handler.serve_json({
            'processes': processes,
            'total': len(processes),
            'running': running,
            'timestamp': process_monitor.last_update
        })

    elif path.startswith('/api/processes/search'):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        query = params.get('q', [''])[0]
        processes = process_monitor.search_processes(query)
        running = sum(1 for p in processes if p['status'] == 'running')
        handler.serve_json({
            'processes': processes,
            'total': len(processes),
            'running': running,
            'timestamp': process_monitor.last_update
        })

    elif path == '/api/processes/problematic':
        problematic = process_monitor.get_problematic_processes()
        handler.serve_json(problematic)

    # ==================== Tools & Licensing ====================

    elif path == '/api/tools/status':
        from atlas.tool_availability import get_tool_monitor
        tool_monitor = get_tool_monitor()
        status = tool_monitor.get_all_tool_status()
        tools_list = []
        for name, info in status.items():
            tools_list.append({
                'name': info['name'],
                'installed': info['installed'],
                'path': info['path'],
                'description': info['description'],
                'license': info['license'],
                'license_type': 'permissive' if info['license'] in ['MIT', 'Apache-2.0', 'BSD-3-Clause'] else 'copyleft',
                'brew_package': info['brew_package'],
                'requires_sudo': info['requires_sudo'],
                'value_for_atlas': info['value_for_atlas'],
                'attribution': info['attribution']
            })
        handler.serve_json({
            'tools': tools_list,
            'installed_count': len(tool_monitor.get_installed_tools()),
            'missing_count': len(tool_monitor.get_missing_tools()),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        })

    elif path == '/api/tools/licensing':
        from atlas.licensing import get_api_licensing_info
        handler.serve_json(get_api_licensing_info())

    # ==================== Network Path ====================

    elif path == '/api/traceroute':
        from urllib.parse import urlparse, parse_qs
        from atlas.enhanced_traceroute import get_tracer
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        target = params.get('target', ['8.8.8.8'])[0]
        count = safe_int_param(params, 'count', 3, max_val=100)
        tracer = get_tracer()
        result = tracer.trace(target, count=count, max_hops=20)
        handler.serve_json(result.to_dict())

    elif path == '/api/traceroute/quick':
        from urllib.parse import urlparse, parse_qs
        from atlas.enhanced_traceroute import get_tracer
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        target = params.get('target', ['8.8.8.8'])[0]
        tracer = get_tracer()
        result = tracer.quick_trace(target)
        handler.serve_json(result)

    elif path == '/api/network/path-summary':
        _handle_network_path_summary(handler)

    # ==================== Agent Health ====================

    elif path == '/api/agent/health':
        _handle_agent_health(handler)

    # ==================== System Pressure ====================

    elif path == '/api/system/pressure':
        _handle_system_pressure(handler)

    # ==================== Data Export ====================

    elif path.startswith('/api/ping/export'):
        _handle_export(handler, 'ping')

    elif path.startswith('/api/speedtest/export'):
        _handle_export(handler, 'speedtest')

    elif path.startswith('/api/wifi/events/export'):
        _handle_export(handler, 'wifi_events')

    elif path.startswith('/api/wifi/export'):
        _handle_export(handler, 'wifi')

    # ==================== Network Analysis ====================

    elif path == '/api/network/analysis':
        from urllib.parse import urlparse, parse_qs
        from atlas.network_analyzer import get_network_analyzer
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = 24
        if 'hours' in params:
            try:
                hours = int(params['hours'][0])
            except (ValueError, IndexError):
                pass
        analyzer = get_network_analyzer()
        report = analyzer.get_analysis_report(hours=hours)
        handler.serve_json(report)

    elif path == '/api/network/analysis/latest':
        from atlas.network_analyzer import get_network_analyzer
        analyzer = get_network_analyzer()
        latest = analyzer.get_latest_analysis()
        handler.serve_json(latest)

    elif path == '/api/network/analysis/settings':
        from atlas.network_analysis_settings import get_settings
        settings = get_settings()
        handler.serve_json(settings.get_all())

    # ==================== Notifications ====================

    elif path == '/api/notifications/status':
        from atlas.notification_manager import get_notification_manager
        manager = get_notification_manager()
        handler.serve_json({
            'enabled': manager.is_enabled(),
            'min_interval_minutes': manager.min_notification_interval.total_seconds() / 60
        })

    elif path == '/api/notifications/history':
        from atlas.notification_manager import get_notification_manager
        manager = get_notification_manager()
        history = manager.get_notification_history(limit=50)
        handler.serve_json({'notifications': history})

    # ==================== Alert Rules (GET) ====================

    elif path == '/api/alerts/rules':
        from atlas.alert_rules_manager import get_alert_rules_manager
        manager = get_alert_rules_manager()
        include_disabled = handler.path.find('include_disabled=true') != -1
        rules = manager.list_rules(include_disabled=include_disabled)
        handler.serve_json({
            'rules': [r.to_dict() for r in rules],
            'count': len(rules)
        })

    elif path.startswith('/api/alerts/rules/') and not path.endswith('/events'):
        from atlas.alert_rules_manager import get_alert_rules_manager
        rule_id = path.split('/api/alerts/rules/')[-1].split('?')[0]
        manager = get_alert_rules_manager()
        rule = manager.get_rule(rule_id)
        if rule:
            handler.serve_json(rule.to_dict())
        else:
            handler.send_error(404, f"Rule not found: {rule_id}")

    elif path == '/api/alerts/events':
        from atlas.alert_rules_manager import get_alert_rules_manager
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        manager = get_alert_rules_manager()
        events = manager.get_alert_events(
            rule_id=params.get('rule_id', [None])[0],
            severity=params.get('severity', [None])[0],
            hours=safe_int_param(params, 'hours', 24, max_val=8760),
            limit=safe_int_param(params, 'limit', 100, max_val=10000)
        )
        handler.serve_json({
            'events': [e.to_dict() for e in events],
            'count': len(events)
        })

    elif path == '/api/alerts/statistics':
        from atlas.alert_rules_manager import get_alert_rules_manager
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        hours = safe_int_param(params, 'hours', 24, max_val=8760)
        manager = get_alert_rules_manager()
        stats = manager.get_alert_statistics(hours)
        handler.serve_json(stats)

    elif path == '/api/alerts/email-config':
        from atlas.alert_rules_manager import get_alert_rules_manager
        manager = get_alert_rules_manager()
        config = manager.get_email_config()
        handler.serve_json(config or {'configured': False})

    elif path == '/api/alerts/metrics':
        from atlas.alert_rules_manager import MetricType, Condition, AlertSeverity
        handler.serve_json({
            'metric_types': [m.value for m in MetricType],
            'conditions': [c.value for c in Condition],
            'severities': [s.value for s in AlertSeverity]
        })

    else:
        return False

    return True


def dispatch_post(handler, path):
    """Handle POST requests for API endpoints.

    Note: Auth POST routes (/login, /api/auth/*) are handled inline
    in LiveWidgetHandler.do_POST since they run before the auth check.

    Args:
        handler: LiveWidgetHandler instance
        path: URL path (without query string)

    Returns:
        True if the request was handled, False otherwise
    """
    # ==================== Processes ====================

    if path.startswith('/api/processes/kill/'):
        pid_str = path.split('/')[-1]
        try:
            pid = int(pid_str)
            result = process_monitor.kill_process(pid)
            handler.serve_json(result)
        except ValueError:
            handler.send_error(400, "Invalid PID")

    # ==================== Network Analysis Settings ====================

    elif path == '/api/network/analysis/settings':
        from atlas.network_analysis_settings import get_settings
        body = handler._read_body()
        if body is None:
            return True
        new_settings = json.loads(body.decode('utf-8'))
        settings = get_settings()
        valid, error = settings.validate_settings(new_settings)
        if not valid:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': error}).encode())
            return True
        success = settings.update(new_settings)
        if success:
            handler.serve_json({'status': 'success', 'settings': settings.get_all()})
        else:
            handler.send_error(500, "Failed to save settings")

    # ==================== Dashboard Layout ====================

    elif path == '/api/dashboard/layout':
        prefs = get_dashboard_preferences()
        body = handler._read_body()
        if body is None:
            return True
        new_layout = json.loads(body.decode('utf-8'))
        success = prefs.update_layout(new_layout)
        if success:
            handler.serve_json({'status': 'success', 'layout': prefs.get_layout()})
        else:
            handler.send_error(500, "Failed to save layout")

    elif path == '/api/dashboard/layout/reset':
        prefs = get_dashboard_preferences()
        success = prefs.reset_to_default()
        if success:
            handler.serve_json({'status': 'success', 'layout': prefs.get_layout()})
        else:
            handler.send_error(500, "Failed to reset layout")

    # ==================== Notifications ====================

    elif path == '/api/notifications/enable':
        from atlas.notification_manager import get_notification_manager
        manager = get_notification_manager()
        manager.enable_notifications()
        handler.serve_json({'status': 'success', 'enabled': True})

    elif path == '/api/notifications/disable':
        from atlas.notification_manager import get_notification_manager
        manager = get_notification_manager()
        manager.disable_notifications()
        handler.serve_json({'status': 'success', 'enabled': False})

    elif path == '/api/notifications/test':
        from atlas.notification_manager import get_notification_manager
        manager = get_notification_manager()
        success = manager.send_custom_notification(
            "ATLAS Test Notification",
            "This is a test notification from ATLAS Agent"
        )
        handler.serve_json({'status': 'success' if success else 'failed', 'sent': success})

    # ==================== Speed Test ====================

    elif path == '/api/speedtest/run':
        monitor = _get_speed_test_monitor()
        monitor.run_test_now()
        handler.serve_json({'status': 'started', 'message': 'Speed test started', 'mode': monitor.get_test_mode()})

    elif path == '/api/speedtest/run-full':
        monitor = _get_speed_test_monitor()
        monitor.run_full_test_now()
        handler.serve_json({'status': 'started', 'message': 'Full speed test started', 'mode': 'full'})

    elif path == '/api/speedtest/mode':
        monitor = _get_speed_test_monitor()
        handler.serve_json(monitor.get_mode_info())

    elif path == '/api/speedtest/mode/set':
        body = handler._read_body()
        if body is None:
            return True
        data = json.loads(body.decode('utf-8'))
        mode = data.get('mode', 'lite')
        monitor = _get_speed_test_monitor()
        success = monitor.set_test_mode(mode)
        if success:
            handler.serve_json({'status': 'success', 'mode': mode, 'message': f'Speed test mode set to {mode}'})
        else:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': f'Invalid mode: {mode}. Use "lite" or "full"'}).encode())

    # ==================== WiFi Aliases ====================

    elif path == '/api/wifi/alias/set':
        from atlas.wifi_analyzer import get_network_alias_manager
        body = handler._read_body()
        if body is None:
            return True
        data = json.loads(body.decode('utf-8'))
        alias = data.get('alias', '').strip()
        if not alias:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Alias is required'}).encode())
            return True
        manager = get_network_alias_manager()
        fingerprint = manager.get_current_fingerprint()
        if not fingerprint:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'No network connected'}).encode())
            return True
        manager.set_alias(fingerprint, alias)
        handler.serve_json({
            'status': 'success',
            'fingerprint': fingerprint,
            'alias': alias
        })

    elif path == '/api/wifi/alias/remove':
        from atlas.wifi_analyzer import get_network_alias_manager
        body = handler._read_body()
        if body is None:
            return True
        data = json.loads(body.decode('utf-8'))
        fingerprint = data.get('fingerprint', '')
        if not fingerprint:
            manager = get_network_alias_manager()
            fingerprint = manager.get_current_fingerprint()
        if not fingerprint:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'No fingerprint provided'}).encode())
            return True
        manager = get_network_alias_manager()
        success = manager.remove_alias(fingerprint)
        handler.serve_json({
            'status': 'success' if success else 'not_found',
            'fingerprint': fingerprint
        })

    # ==================== Network Testing ====================

    elif path == '/api/network/connection-test':
        try:
            from atlas.network.monitors import get_tcp_connection_tester
            body = handler._read_body()
            if body is None:
                return True
            body = body if body else b'{}'
            json.loads(body.decode('utf-8'))
            tester = get_tcp_connection_tester()
            result = tester.run_single_test()
            handler.serve_json(result)
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            handler.serve_json({'error': 'Test failed', 'status': 'failed'})

    elif path == '/api/network/throughput-test':
        try:
            from atlas.network.monitors import get_throughput_tester
            body = handler._read_body()
            if body is None:
                return True
            body = body if body else b'{}'
            data = json.loads(body.decode('utf-8'))
            server_host = data.get('server_host')
            server_port = data.get('server_port', 5007)
            duration = data.get('duration', 5)
            if not server_host:
                handler.serve_json({'error': 'server_host is required', 'status': 'failed'})
                return True
            tester = get_throughput_tester(server_host)
            tester.set_server(server_host, server_port)
            tester.test_duration = duration
            result = tester.run_full_test()
            handler.serve_json(result)
        except Exception as e:
            logger.error(f"Throughput test error: {e}")
            handler.serve_json({'error': 'Test failed', 'status': 'failed'})

    elif path == '/api/network/udp-test':
        try:
            from atlas.network.monitors import get_udp_quality_monitor
            body = handler._read_body()
            if body is None:
                return True
            body = body if body else b'{}'
            data = json.loads(body.decode('utf-8'))
            target_host = data.get('target_host', '8.8.8.8')
            target_port = data.get('target_port', 5005)
            monitor = get_udp_quality_monitor(target_host, target_port)
            result = monitor.run_single_test()
            handler.serve_json(result)
        except Exception as e:
            logger.error(f"UDP test error: {e}")
            handler.serve_json({'error': 'Test failed', 'status': 'failed'})

    # ==================== Alert Rules (POST) ====================

    elif path == '/api/alerts/rules':
        from atlas.alert_rules_manager import get_alert_rules_manager
        body = handler._read_body()
        if body is None:
            return True
        rule_data = json.loads(body.decode('utf-8'))
        manager = get_alert_rules_manager()
        success, message, rule = manager.create_rule(rule_data)
        if success:
            handler.serve_json({
                'status': 'success',
                'message': message,
                'rule': rule.to_dict()
            })
        else:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path.startswith('/api/alerts/rules/') and path.endswith('/update'):
        from atlas.alert_rules_manager import get_alert_rules_manager
        rule_id = path.replace('/api/alerts/rules/', '').replace('/update', '')
        body = handler._read_body()
        if body is None:
            return True
        updates = json.loads(body.decode('utf-8'))
        manager = get_alert_rules_manager()
        success, message = manager.update_rule(rule_id, updates)
        if success:
            rule = manager.get_rule(rule_id)
            handler.serve_json({
                'status': 'success',
                'message': message,
                'rule': rule.to_dict() if rule else None
            })
        else:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path.startswith('/api/alerts/rules/') and path.endswith('/delete'):
        from atlas.alert_rules_manager import get_alert_rules_manager
        rule_id = path.replace('/api/alerts/rules/', '').replace('/delete', '')
        manager = get_alert_rules_manager()
        success, message = manager.delete_rule(rule_id)
        if success:
            handler.serve_json({'status': 'success', 'message': message})
        else:
            handler.send_response(404)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path.startswith('/api/alerts/rules/') and path.endswith('/toggle'):
        from atlas.alert_rules_manager import get_alert_rules_manager
        rule_id = path.replace('/api/alerts/rules/', '').replace('/toggle', '')
        body = handler._read_body()
        if body is None:
            return True
        data = json.loads(body.decode('utf-8'))
        enabled = data.get('enabled', True)
        manager = get_alert_rules_manager()
        success, message = manager.toggle_rule(rule_id, enabled)
        if success:
            rule = manager.get_rule(rule_id)
            handler.serve_json({
                'status': 'success',
                'message': message,
                'rule': rule.to_dict() if rule else None
            })
        else:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path == '/api/alerts/rules/reset':
        from atlas.alert_rules_manager import get_alert_rules_manager
        manager = get_alert_rules_manager()
        success, message = manager.reset_to_defaults()
        if success:
            rules = manager.list_rules()
            handler.serve_json({
                'status': 'success',
                'message': message,
                'rules': [r.to_dict() for r in rules]
            })
        else:
            handler.send_response(500)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path.startswith('/api/alerts/events/') and path.endswith('/acknowledge'):
        from atlas.alert_rules_manager import get_alert_rules_manager
        event_id = path.replace('/api/alerts/events/', '').replace('/acknowledge', '')
        body = handler._read_body()
        if body is None:
            return True
        data = json.loads(body.decode('utf-8'))
        acknowledged_by = data.get('acknowledged_by', 'user')
        manager = get_alert_rules_manager()
        success, message = manager.acknowledge_event(event_id, acknowledged_by)
        if success:
            handler.serve_json({'status': 'success', 'message': message})
        else:
            handler.send_response(404)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path == '/api/alerts/email-config':
        from atlas.alert_rules_manager import get_alert_rules_manager
        body = handler._read_body()
        if body is None:
            return True
        config = json.loads(body.decode('utf-8'))
        manager = get_alert_rules_manager()
        success, message = manager.configure_email(config)
        if success:
            handler.serve_json({'status': 'success', 'message': message})
        else:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path == '/api/alerts/email-test':
        from atlas.alert_rules_manager import get_alert_rules_manager
        body = handler._read_body()
        if body is None:
            return True
        data = json.loads(body.decode('utf-8'))
        recipient = data.get('recipient')
        if not recipient:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'recipient is required'}).encode())
            return True
        manager = get_alert_rules_manager()
        success, message = manager.test_email(recipient)
        if success:
            handler.serve_json({'status': 'success', 'message': message})
        else:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': message}).encode())

    elif path == '/api/alerts/evaluate':
        from atlas.alert_rules_manager import get_alert_rules_manager
        body = handler._read_body()
        if body is None:
            return True
        metrics = json.loads(body.decode('utf-8')) if body else {}
        if not metrics:
            current = handler.get_current_stats()
            metrics = {
                'cpu': current.get('cpu', 0),
                'memory': current.get('memory', 0),
                'disk': current.get('disk', 0),
                'temperature': current.get('temperature', 0),
                'battery': current.get('battery', 0),
                'network_up': current.get('network_up', 0),
                'network_down': current.get('network_down', 0),
            }
        manager = get_alert_rules_manager()
        events = manager.evaluate_metrics(metrics)
        handler.serve_json({
            'status': 'success',
            'metrics_evaluated': metrics,
            'triggered_events': [e.to_dict() for e in events],
            'count': len(events)
        })

    elif path == '/api/alerts/cleanup':
        from atlas.alert_rules_manager import get_alert_rules_manager
        body = handler._read_body()
        if body is None:
            return True
        data = json.loads(body.decode('utf-8')) if body else {}
        days = int(data.get('days', 30))
        manager = get_alert_rules_manager()
        deleted = manager.cleanup_old_events(days)
        handler.serve_json({
            'status': 'success',
            'deleted_count': deleted,
            'message': f'Deleted {deleted} events older than {days} days'
        })

    # ==================== Encrypted Export ====================

    elif path.startswith('/api/ping/export'):
        _handle_encrypted_export(handler, 'ping')

    elif path.startswith('/api/speedtest/export'):
        _handle_encrypted_export(handler, 'speedtest')

    elif path.startswith('/api/wifi/events/export'):
        _handle_encrypted_export(handler, 'wifi_events')

    elif path.startswith('/api/wifi/export'):
        _handle_encrypted_export(handler, 'wifi')

    else:
        return False

    return True


# ==================== Complex Handler Helpers ====================


def _handle_system_health_overview(handler):
    """Handle /api/system-health/overview endpoint."""
    overview = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'monitors': {}
    }

    if DISPLAY_MONITOR_AVAILABLE:
        try:
            dm = get_display_monitor()
            status = dm.get_status()
            overview['monitors']['display'] = {
                'status': status.get('status', 'unknown'),
                'display_count': status.get('display', {}).get('display_count', 0),
                'gpu': status.get('gpu', {}).get('gpu_name', 'Unknown')
            }
        except Exception as e:
            overview['monitors']['display'] = {'status': 'error', 'error': str(e)}

    if POWER_MONITOR_AVAILABLE:
        try:
            pm = get_power_monitor()
            summary = pm.get_power_summary()
            overview['monitors']['power'] = {
                'status': 'healthy' if summary.get('battery', {}).get('health_percentage', 0) > 50 else 'warning',
                'battery_health': summary.get('battery', {}).get('health_percentage', 0),
                'is_charging': summary.get('battery', {}).get('is_charging', False),
                'thermal_status': summary.get('thermal', {}).get('status', 'Unknown')
            }
        except Exception as e:
            overview['monitors']['power'] = {'status': 'error', 'error': str(e)}

    if PERIPHERAL_MONITOR_AVAILABLE:
        try:
            perm = get_peripheral_monitor()
            summary = perm.get_peripheral_summary()
            overview['monitors']['peripherals'] = {
                'status': 'healthy',
                'bluetooth_devices': summary.get('bluetooth', {}).get('total_devices', 0),
                'usb_devices': summary.get('usb', {}).get('total_devices', 0)
            }
        except Exception as e:
            overview['monitors']['peripherals'] = {'status': 'error', 'error': str(e)}

    if SECURITY_MONITOR_AVAILABLE:
        try:
            sm = get_security_monitor()
            summary = sm.get_current_security_status()
            score = summary.get('security_score', 0)
            overview['monitors']['security'] = {
                'status': 'healthy' if score >= 80 else 'warning' if score >= 50 else 'critical',
                'score': score,
                'firewall': summary.get('firewall', {}).get('enabled', False),
                'filevault': summary.get('filevault', {}).get('enabled', False)
            }
        except Exception as e:
            overview['monitors']['security'] = {'status': 'error', 'error': str(e)}

    if DISK_MONITOR_AVAILABLE:
        try:
            dm = get_disk_monitor()
            summary = dm.get_disk_health_summary()
            overview['monitors']['disk'] = {
                'status': summary.get('overall_status', 'unknown'),
                'disk_count': len(summary.get('disks', [])),
                'issues': summary.get('issues_count', 0)
            }
        except Exception as e:
            overview['monitors']['disk'] = {'status': 'error', 'error': str(e)}

    handler.serve_json(overview)


def _handle_saas_health(handler):
    """Handle /api/saas/health endpoint."""
    try:
        from atlas.network.monitors.saas_endpoint_monitor import get_saas_endpoint_monitor
        monitor = get_saas_endpoint_monitor()
        current_status = monitor.get_current_status()
        categories = monitor.get_category_summary()
        incidents = monitor.incidents_logger.get_history()[-20:]

        services = []
        for endpoint_name, status in current_status.items():
            services.append({
                'endpoint_name': endpoint_name,
                'host': status.get('host', ''),
                'category': status.get('category', 'Unknown'),
                'reachable': status.get('reachable') == 'True' or status.get('reachable') is True,
                'latency_ms': float(status.get('latency_ms', 0) or 0),
                'dns_time_ms': float(status.get('dns_time_ms', 0) or 0),
                'error': status.get('error', '')
            })

        services_up = sum(1 for s in services if s['reachable'])
        total_services = len(services)
        latencies = [s['latency_ms'] for s in services if s['reachable'] and s['latency_ms'] > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        avg_availability = (services_up / total_services * 100) if total_services > 0 else 0

        handler.serve_json({
            'summary': {
                'services_up': services_up,
                'total_services': total_services,
                'avg_latency': avg_latency,
                'avg_availability': avg_availability
            },
            'categories': categories,
            'services': services,
            'incidents': incidents
        })
    except Exception as e:
        logger.error(f"Error getting SaaS health: {e}")
        handler.serve_json({'error': str(e), 'services': [], 'categories': {}, 'incidents': []})


def _handle_wifi_roaming(handler):
    """Handle /api/wifi/roaming endpoint."""
    from atlas.wifi_roaming import get_wifi_roaming_tracker
    try:
        tracker = get_wifi_roaming_tracker()
        wifi_mon = get_wifi_monitor()
        current = tracker.get_current_state()
        events = tracker.get_events(hours=24)
        stats = tracker.get_statistics(hours=24)

        signal_history = []
        try:
            wifi_data = wifi_mon.last_result
            if wifi_data.get('rssi'):
                signal_history.append({
                    'timestamp': wifi_data.get('timestamp', ''),
                    'rssi': wifi_data.get('rssi'),
                    'quality': wifi_data.get('quality_score', 0)
                })
        except Exception:
            pass

        channel_utilization = []
        if current.get('channel'):
            channel_utilization.append({
                'channel': current.get('channel'),
                'band': current.get('band', ''),
                'utilization': 0
            })

        sticky_client_detected = False
        if current.get('connected') and current.get('rssi'):
            rssi = current.get('rssi')
            if rssi and rssi < -80:
                recent_ap_switches = [e for e in events if e.get('type') == 'ap_switch']
                if len(recent_ap_switches) == 0:
                    sticky_client_detected = True

        handler.serve_json({
            'current': {
                'ssid': current.get('ssid') or wifi_mon.last_result.get('ssid', '--'),
                'bssid': current.get('gateway_mac'),
                'channel': current.get('channel'),
                'band': current.get('band'),
                'rssi': current.get('rssi'),
                'snr': current.get('snr'),
                'quality_rating': current.get('quality_rating'),
                'connected': current.get('connected', False)
            },
            'sticky_client_detected': sticky_client_detected,
            'channel_utilization': channel_utilization,
            'signal_history': signal_history,
            'statistics': stats,
            'events': events[:20]
        })
    except Exception as e:
        logger.error(f"Error getting WiFi roaming data: {e}")
        handler.serve_json({
            'current': {},
            'sticky_client_detected': False,
            'channel_utilization': [],
            'signal_history': [],
            'statistics': {},
            'events': []
        })


def _handle_network_path_summary(handler):
    """Handle /api/network/path-summary endpoint."""
    from atlas.enhanced_traceroute import get_tracer
    tracer = get_tracer()
    results = {}
    for target in ['8.8.8.8', '1.1.1.1']:
        try:
            trace = tracer.quick_trace(target)
            results[target] = {
                'hop_count': trace.get('hop_count', 0),
                'completed': trace.get('completed', False),
                'problem_count': len(trace.get('problem_hops', [])),
                'method': trace.get('method', 'native')
            }
        except Exception as e:
            results[target] = {'error': str(e)}
    handler.serve_json({
        'targets': results,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
    })


def _handle_agent_health(handler):
    """Handle /api/agent/health endpoint."""
    import socket
    import psutil

    # Access class-level attributes via handler's class
    handler_class = handler.__class__

    uptime = time.time() - handler.agent_start_time

    monitors_status = {
        'speedtest': _get_speed_test_monitor().is_running() if hasattr(_get_speed_test_monitor(), 'is_running') else True,
        'ping': _get_ping_monitor().is_running() if hasattr(_get_ping_monitor(), 'is_running') else True,
        'wifi': get_wifi_monitor().is_running() if hasattr(get_wifi_monitor(), 'is_running') else True,
    }

    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    health_data = {
        'status': 'healthy',
        'agent_version': handler.agent_version,
        'uptime_seconds': int(uptime),
        'hostname': socket.gethostname(),
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'fleet_server': handler.fleet_server_url,
        'last_fleet_report': handler.last_fleet_report,
        'monitors': monitors_status,
        'system': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': round(memory.available / (1024**3), 2)
        },
        'responsive': True,
        'e2ee': {
            'enabled': handler_class.e2ee_enabled,
            'server_verified': handler_class.e2ee_server_verified,
            'last_verification': handler_class.last_e2ee_verification,
            'status': 'encrypted' if handler_class.e2ee_enabled and handler_class.e2ee_server_verified else ('enabled_unverified' if handler_class.e2ee_enabled else 'disabled')
        }
    }

    handler.serve_json(health_data)


def _handle_system_pressure(handler):
    """Handle /api/system/pressure endpoint."""
    import psutil

    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    try:
        load_avg = psutil.getloadavg()
        load_1m, load_5m, load_15m = load_avg
        normalized_load = load_1m / cpu_count if cpu_count > 0 else 0
    except (AttributeError, OSError):
        load_1m = load_5m = load_15m = 0
        normalized_load = 0

    pressure_score = 0
    if cpu_percent > 90:
        pressure_score += 40
    elif cpu_percent > 75:
        pressure_score += 30
    elif cpu_percent > 50:
        pressure_score += 15
    elif cpu_percent > 25:
        pressure_score += 5

    if memory.percent > 90:
        pressure_score += 40
    elif memory.percent > 80:
        pressure_score += 30
    elif memory.percent > 65:
        pressure_score += 15
    elif memory.percent > 50:
        pressure_score += 5

    if normalized_load > 2.0:
        pressure_score += 20
    elif normalized_load > 1.5:
        pressure_score += 15
    elif normalized_load > 1.0:
        pressure_score += 10
    elif normalized_load > 0.7:
        pressure_score += 5

    if pressure_score >= 60:
        pressure_level = 'Critical'
        pressure_color = '#ff3000'
    elif pressure_score >= 40:
        pressure_level = 'High'
        pressure_color = '#ff6400'
    elif pressure_score >= 20:
        pressure_level = 'Moderate'
        pressure_color = '#ffc800'
    else:
        pressure_level = 'Normal'
        pressure_color = '#00ff64'

    handler.serve_json({
        'cpu': {
            'percent': round(cpu_percent, 1),
            'cores': cpu_count
        },
        'memory': {
            'percent': round(memory.percent, 1),
            'used_gb': round(memory.used / (1024**3), 2),
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2)
        },
        'swap': {
            'percent': round(swap.percent, 1),
            'used_gb': round(swap.used / (1024**3), 2),
            'total_gb': round(swap.total / (1024**3), 2)
        },
        'load': {
            '1m': round(load_1m, 2),
            '5m': round(load_5m, 2),
            '15m': round(load_15m, 2),
            'normalized': round(normalized_load, 2)
        },
        'pressure': {
            'score': pressure_score,
            'level': pressure_level,
            'color': pressure_color
        },
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
    })


def _handle_export(handler, export_type):
    """Handle data export endpoints for ping, speedtest, wifi, wifi_events."""
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)

    hours = None
    if 'hours' in params:
        try:
            hours = int(params['hours'][0])
        except (ValueError, IndexError):
            pass

    export_format = params.get('format', ['csv'])[0].lower()

    if export_type == 'ping':
        monitor = _get_ping_monitor()
        label = 'ping'
    elif export_type == 'speedtest':
        monitor = _get_speed_test_monitor()
        label = 'speedtest'
    elif export_type == 'wifi':
        monitor = get_wifi_monitor()
        label = 'wifi_quality'
    elif export_type == 'wifi_events':
        monitor = get_wifi_monitor()
        label = 'wifi_events'
    else:
        handler.send_error(400, f"Unknown export type: {export_type}")
        return

    if export_format == 'json':
        if export_type == 'wifi_events':
            history = monitor.get_events_history()
        else:
            history = monitor.get_history()

        if hours:
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(hours=hours)
            history = [h for h in history if datetime.fromisoformat(h['timestamp']) >= cutoff]

        if history:
            filename = f"{label}_last_{hours}h.json" if hours else f"{label}_all.json"
            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            handler.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            handler.send_header('Cache-Control', 'no-cache')
            cors_origin = handler._get_cors_origin()
            if cors_origin:
                handler.send_header('Access-Control-Allow-Origin', cors_origin)
            handler.end_headers()
            handler.wfile.write(json.dumps(history, indent=2).encode())
            _log_export_event(export_type, 'json', filename, False)
        else:
            handler.send_error(404, "No data to export")
    else:
        if export_type == 'wifi_events':
            csv_data = monitor.export_events_to_csv(hours=hours)
        else:
            csv_data = monitor.export_to_csv(hours=hours)

        if csv_data:
            filename = f"{label}_last_{hours}h.csv" if hours else f"{label}_all.csv"
            handler.send_response(200)
            handler.send_header('Content-type', 'text/csv')
            handler.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            handler.send_header('Cache-Control', 'no-cache')
            cors_origin = handler._get_cors_origin()
            if cors_origin:
                handler.send_header('Access-Control-Allow-Origin', cors_origin)
            handler.end_headers()
            handler.wfile.write(csv_data.encode())
            _log_export_event(export_type, 'csv', filename, False)
        else:
            handler.send_error(404, "No data to export")


def _encrypt_export_data(data: bytes, password: str) -> bytes:
    """Encrypt export data with AES-256-GCM using a password.

    Output format: salt(16) + nonce(12) + ciphertext+tag
    Decrypt with PBKDF2(password, salt) -> AESGCM(key).decrypt(nonce, ct, None)
    """
    import os
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise RuntimeError("cryptography package required for encrypted export")

    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode('utf-8'))
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return salt + nonce + ciphertext


def _encrypt_export_fernet(data: bytes, password: str) -> bytes:
    """Encrypt export data with AES-256-GCM (password) then Fernet wrap (fleet key).

    Dual-layer encryption: inner AES-256-GCM with user password,
    outer Fernet wrap with the agent's key so the fleet server can
    peel the Fernet layer and still require the password for the inner layer.
    """
    # Inner layer: AES-256-GCM with password
    aes_encrypted = _encrypt_export_data(data, password)
    # Outer layer: Fernet wrap with agent key
    from atlas.database import get_database
    db = get_database()
    key = db.encryption_key_b64
    if not key:
        raise RuntimeError("Agent encryption key not available")
    from cryptography.fernet import Fernet
    f = Fernet(key.encode('ascii'))
    return f.encrypt(aes_encrypted)


def _log_export_event(export_type: str, export_format: str, filename: str, encrypted: bool, mode: str = 'none'):
    """Log an export event to the widget log collector for fleet tracking."""
    try:
        import getpass
        local_user = getpass.getuser()
    except Exception:
        local_user = 'unknown'
    try:
        from atlas.widget_log_collector import log_widget_event
        log_widget_event('INFO', 'export', f'{export_type} data exported', {
            'export_type': export_type,
            'format': export_format,
            'filename': filename,
            'encrypted': encrypted,
            'mode': mode,
            'local_user': local_user
        })
    except Exception:
        pass  # Don't fail exports if logging fails


def _handle_encrypted_export(handler, export_type):
    """Handle POST export requests with encryption (password or fleet key)."""
    from urllib.parse import urlparse, parse_qs

    body = handler._read_body()
    if body is None:
        return

    try:
        data = json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        handler.send_error(400, "Invalid JSON body")
        return

    mode = data.get('mode', 'password')
    password = None

    if mode == 'fleet_key':
        password = data.get('password', '')
        if not password or len(password) < 16:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Password must be at least 16 characters'}).encode())
            return
    elif mode == 'password':
        password = data.get('password', '')
        if not password or len(password) < 4:
            handler.send_response(400)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({'error': 'Password must be at least 4 characters'}).encode())
            return
    else:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': f'Unknown encryption mode: {mode}'}).encode())
        return

    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)

    hours = None
    if 'hours' in params:
        try:
            hours = int(params['hours'][0])
        except (ValueError, IndexError):
            pass

    export_format = params.get('format', ['csv'])[0].lower()

    if export_type == 'ping':
        monitor = _get_ping_monitor()
        label = 'ping'
    elif export_type == 'speedtest':
        monitor = _get_speed_test_monitor()
        label = 'speedtest'
    elif export_type == 'wifi':
        monitor = get_wifi_monitor()
        label = 'wifi_quality'
    elif export_type == 'wifi_events':
        monitor = get_wifi_monitor()
        label = 'wifi_events'
    else:
        handler.send_error(400, f"Unknown export type: {export_type}")
        return

    # Generate export content
    if export_format == 'json':
        if export_type == 'wifi_events':
            history = monitor.get_events_history()
        else:
            history = monitor.get_history()

        if hours:
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(hours=hours)
            history = [h for h in history if datetime.fromisoformat(h['timestamp']) >= cutoff]

        if not history:
            handler.send_error(404, "No data to export")
            return

        content_bytes = json.dumps(history, indent=2).encode('utf-8')
        base_filename = f"{label}_last_{hours}h.json" if hours else f"{label}_all.json"
    else:
        if export_type == 'wifi_events':
            csv_data = monitor.export_events_to_csv(hours=hours)
        else:
            csv_data = monitor.export_to_csv(hours=hours)

        if not csv_data:
            handler.send_error(404, "No data to export")
            return

        content_bytes = csv_data.encode('utf-8')
        base_filename = f"{label}_last_{hours}h.csv" if hours else f"{label}_all.csv"

    # Encrypt the content
    try:
        if mode == 'fleet_key':
            encrypted_bytes = _encrypt_export_fernet(content_bytes, password)
        else:
            encrypted_bytes = _encrypt_export_data(content_bytes, password)
    except RuntimeError as e:
        handler.send_response(500)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': str(e)}).encode())
        return

    filename = base_filename + ('.fernet.enc' if mode == 'fleet_key' else '.enc')
    handler.send_response(200)
    handler.send_header('Content-type', 'application/octet-stream')
    handler.send_header('Content-Disposition', f'attachment; filename="{filename}"')
    handler.send_header('Content-Length', str(len(encrypted_bytes)))
    handler.send_header('Cache-Control', 'no-cache')
    cors_origin = handler._get_cors_origin()
    if cors_origin:
        handler.send_header('Access-Control-Allow-Origin', cors_origin)
    handler.end_headers()
    handler.wfile.write(encrypted_bytes)
    _log_export_event(export_type, export_format, filename, True, mode)
