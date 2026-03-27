"""API routes for the agent dashboard.

Handles all GET /api/* and POST /api/* routes via AgentRouter.
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

from atlas.monitors_registry import get_monitor, is_available
from atlas.routes.agent_router import agent_router

logger = logging.getLogger(__name__)


def _get_speed_test_monitor():
    from atlas.network.monitors.speedtest import get_speed_test_monitor
    return get_speed_test_monitor()


def _get_ping_monitor():
    from atlas.network.monitors.ping import PingMonitor
    if not hasattr(_get_ping_monitor, '_instance'):
        _get_ping_monitor._instance = PingMonitor()
    return _get_ping_monitor._instance


# ==================== Dashboard Routes ====================

@agent_router.route('GET', '/api/dashboard/layout')
def handle_dashboard_layout_get(handler):
    prefs = get_dashboard_preferences()
    handler.serve_json({
        'layout': prefs.get_layout(),
        'widgets': prefs.get_all_widgets_with_state(),
        'categories': CATEGORIES,
    })


@agent_router.route('GET', '/api/dashboard/widgets')
def handle_dashboard_widgets(handler):
    prefs = get_dashboard_preferences()
    handler.serve_json({
        'widgets': prefs.get_all_widgets_with_state(),
        'categories': CATEGORIES,
    })


# ==================== System Metrics ====================

@agent_router.route('GET', '/api/system/comprehensive')
def handle_system_comprehensive(handler):
    handler.serve_json(get_comprehensive_system_stats())


@agent_router.route('GET', '/api/metrics/aggregated')
def handle_metrics_aggregated(handler):
    from atlas.database import get_database
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    hours = safe_int_param(params, 'hours', 24, max_val=8760)
    interval = safe_int_param(params, 'interval', 5, max_val=1440)

    db = get_database()
    data = db.get_aggregated_metrics(hours=hours, interval_minutes=interval)
    handler.serve_json(data)


@agent_router.route('GET', '/api/metrics/history')
def handle_metrics_history(handler):
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

@agent_router.route('GET', '/api/pressure/history/10m')
def handle_pressure_history_10m(handler):
    handler.serve_json(get_pressure_logger().get_history('10m'))


@agent_router.route('GET', '/api/pressure/history/1h')
def handle_pressure_history_1h(handler):
    handler.serve_json(get_pressure_logger().get_history('1h'))


@agent_router.route('GET', '/api/pressure/history/24h')
def handle_pressure_history_24h(handler):
    handler.serve_json(get_pressure_logger().get_history('24h'))


@agent_router.route('GET', '/api/pressure/history/7d')
def handle_pressure_history_7d(handler):
    handler.serve_json(get_pressure_logger().get_history('7d'))


@agent_router.route('GET', '/api/pressure/current')
def handle_pressure_current(handler):
    handler.serve_json(get_pressure_logger().get_current())


# ==================== WebSocket ====================

@agent_router.route('GET', '/api/stream')
def handle_stream(handler):
    handler.handle_websocket()


# ==================== System Stats ====================

@agent_router.route('GET', '/api/stats')
def handle_stats(handler):
    handler.serve_json(handler.get_current_stats())


@agent_router.route('GET', '/api/health/full')
def handle_health_full(handler):
    """Aggregated health of all monitors — one endpoint to check everything."""
    import time as _time
    result = {
        'timestamp': _time.strftime('%Y-%m-%dT%H:%M:%S'),
        'monitors': {}
    }

    # Core monitors (always available)
    monitor_checks = {
        'wifi': lambda: get_wifi_monitor().get_last_result() is not None,
        'ping': lambda: _get_ping_monitor().get_last_result() is not None,
        'speedtest': lambda: _get_speed_test_monitor().get_last_result() is not None,
    }

    for name, check_fn in monitor_checks.items():
        try:
            running = check_fn()
            result['monitors'][name] = {'status': 'running' if running else 'idle'}
        except Exception as e:
            result['monitors'][name] = {'status': 'error', 'error': str(e)}

    # Optional monitors via registry
    optional = ['display', 'power', 'peripheral', 'security', 'disk', 'software', 'application']
    for name in optional:
        mon = get_monitor(name)
        if mon is None:
            result['monitors'][name] = {'status': 'unavailable'}
        else:
            try:
                running = hasattr(mon, 'is_running') and mon.is_running()
                result['monitors'][name] = {'status': 'running' if running else 'available'}
            except Exception as e:
                result['monitors'][name] = {'status': 'error', 'error': str(e)}

    # Overall status
    statuses = [m['status'] for m in result['monitors'].values()]
    if any(s == 'error' for s in statuses):
        result['overall'] = 'degraded'
    elif all(s in ('running', 'available', 'idle') for s in statuses):
        result['overall'] = 'healthy'
    else:
        result['overall'] = 'partial'

    result['monitor_count'] = len(result['monitors'])
    result['running_count'] = sum(1 for s in statuses if s == 'running')

    handler.serve_json(result)


@agent_router.route('GET', '/api/health')
def handle_health(handler):
    handler.serve_json(get_system_health())


# ==================== Speed Test ====================

@agent_router.route('GET', '/api/speedtest')
def handle_speedtest(handler):
    monitor = _get_speed_test_monitor()
    handler.serve_json(monitor.get_last_result())


@agent_router.route('GET', '/api/speedtest/history')
def handle_speedtest_history(handler):
    monitor = _get_speed_test_monitor()
    handler.serve_json(monitor.get_history())


@agent_router.route('GET', '/api/speedtest/slow-status')
def handle_speedtest_slow_status(handler):
    monitor = _get_speed_test_monitor()
    handler.serve_json(monitor.get_slow_speed_status())


@agent_router.route('GET', '/api/speedtest/mode')
def handle_speedtest_mode_get(handler):
    monitor = _get_speed_test_monitor()
    handler.serve_json(monitor.get_mode_info())


# ==================== Hardware Monitors ====================

@agent_router.route('GET', '/api/display/status')
def handle_display_status(handler):
    monitor = get_monitor('display')
    if monitor:
        handler.serve_json(monitor.get_status())
    else:
        handler.serve_json({'error': 'Display monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/power/status')
def handle_power_status(handler):
    monitor = get_monitor('power')
    if monitor:
        handler.serve_json(monitor.get_power_summary())
    else:
        handler.serve_json({'error': 'Power monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/peripherals/devices')
def handle_peripherals_devices(handler):
    monitor = get_monitor('peripheral')
    if monitor:
        handler.serve_json(monitor.get_connected_devices('all'))
    else:
        handler.serve_json({'error': 'Peripheral monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/security/status')
def handle_security_status(handler):
    monitor = get_monitor('security')
    if monitor:
        handler.serve_json(monitor.get_current_security_status())
    else:
        handler.serve_json({'error': 'Security monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/disk/health')
def handle_disk_health(handler):
    monitor = get_monitor('disk')
    if monitor:
        handler.serve_json(monitor.get_disk_health_summary())
    else:
        handler.serve_json({'error': 'Disk monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/disk/status')
def handle_disk_status(handler):
    monitor = get_monitor('disk')
    if monitor:
        result = monitor.get_detailed_disk_status()
        handler.serve_json(result)
    else:
        handler.serve_json({'error': 'Disk monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/software/inventory')
def handle_software_inventory(handler):
    monitor = get_monitor('software')
    if monitor:
        handler.serve_json(monitor.get_inventory_summary())
    else:
        handler.serve_json({'error': 'Software monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/applications/status')
def handle_applications_status(handler):
    monitor = get_monitor('application')
    if monitor:
        handler.serve_json(monitor.get_crash_summary())
    else:
        handler.serve_json({'error': 'Application monitor not available', 'status': 'unavailable'})


@agent_router.route('GET', '/api/system-health/overview')
def handle_system_health_overview_route(handler):
    _handle_system_health_overview(handler)


# ==================== Ping ====================

@agent_router.route('GET', '/api/ping')
def handle_ping(handler):
    monitor = _get_ping_monitor()
    handler.serve_json(monitor.get_last_result())


@agent_router.route('GET', '/api/ping/stats')
def handle_ping_stats(handler):
    monitor = _get_ping_monitor()
    handler.serve_json(monitor.get_stats())


@agent_router.route('GET', '/api/ping/history')
def handle_ping_history(handler):
    monitor = _get_ping_monitor()
    handler.serve_json(monitor.get_history())


@agent_router.route('GET', '/api/ping/local-ip')
def handle_ping_local_ip(handler):
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

@agent_router.route('GET', '/api/network/udp-quality')
def handle_network_udp_quality(handler):
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


@agent_router.route('GET', '/api/network/mos')
def handle_network_mos(handler):
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


@agent_router.route('GET', '/api/network/quality')
def handle_network_quality_get(handler):
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


@agent_router.route('GET', '/api/saas/health')
def handle_saas_health_route(handler):
    _handle_saas_health(handler)


# ==================== WiFi ====================

@agent_router.route('GET', '/api/wifi')
def handle_wifi_status(handler):
    monitor = get_wifi_monitor()
    handler.serve_json(monitor.get_last_result())


@agent_router.route('GET', '/api/wifi/history')
def handle_wifi_history(handler):
    monitor = get_wifi_monitor()
    handler.serve_json(monitor.get_history())


@agent_router.route('GET', '/api/wifi/diagnosis')
def handle_wifi_diagnosis(handler):
    monitor = get_wifi_monitor()
    diagnosis = monitor.get_last_diagnosis()
    if diagnosis:
        handler.serve_json(diagnosis)
    else:
        diagnosis = monitor.run_diagnostics_now()
        handler.serve_json(diagnosis)


@agent_router.route('GET', '/api/wifi/diagnose')
def handle_wifi_diagnose(handler):
    monitor = get_wifi_monitor()
    diagnosis = monitor.run_diagnostics_now()
    handler.serve_json(diagnosis)


@agent_router.route('GET', '/api/wifi/signal/history/10m')
def handle_wifi_signal_history_10m(handler):
    from atlas.wifi_analyzer import get_wifi_signal_logger
    handler.serve_json(get_wifi_signal_logger().get_history('10m'))


@agent_router.route('GET', '/api/wifi/signal/history/1h')
def handle_wifi_signal_history_1h(handler):
    from atlas.wifi_analyzer import get_wifi_signal_logger
    handler.serve_json(get_wifi_signal_logger().get_history('1h'))


@agent_router.route('GET', '/api/wifi/signal/history/24h')
def handle_wifi_signal_history_24h(handler):
    from atlas.wifi_analyzer import get_wifi_signal_logger
    handler.serve_json(get_wifi_signal_logger().get_history('24h'))


@agent_router.route('GET', '/api/wifi/signal/history/7d')
def handle_wifi_signal_history_7d(handler):
    from atlas.wifi_analyzer import get_wifi_signal_logger
    handler.serve_json(get_wifi_signal_logger().get_history('7d'))


@agent_router.route('GET', '/api/wifi/signal/current')
def handle_wifi_signal_current(handler):
    from atlas.wifi_analyzer import get_wifi_signal_logger
    handler.serve_json(get_wifi_signal_logger().get_current())


@agent_router.route('GET', '/api/wifi/nearby')
def handle_wifi_nearby(handler):
    from atlas.wifi_analyzer import get_nearby_scanner
    networks = get_nearby_scanner().scan_networks()
    handler.serve_json({
        'networks': networks,
        'count': len(networks),
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
    })


@agent_router.route('GET', '/api/wifi/channels')
def handle_wifi_channels(handler):
    from atlas.wifi_analyzer import get_nearby_scanner
    handler.serve_json(get_nearby_scanner().get_channel_analysis())


@agent_router.route('GET', '/api/wifi/spectrum')
def handle_wifi_spectrum(handler):
    from atlas.wifi_analyzer import get_nearby_scanner
    handler.serve_json(get_nearby_scanner().get_spectrum_data())


@agent_router.route('GET', '/api/wifi/alias/current')
def handle_wifi_alias_current(handler):
    from atlas.wifi_analyzer import get_network_alias_manager
    manager = get_network_alias_manager()
    fingerprint = manager.get_current_fingerprint()
    alias = manager.get_alias(fingerprint) if fingerprint else None
    handler.serve_json({
        'fingerprint': fingerprint,
        'alias': alias,
        'has_alias': alias is not None
    })


@agent_router.route('GET', '/api/wifi/alias/all')
def handle_wifi_alias_all(handler):
    from atlas.wifi_analyzer import get_network_alias_manager
    manager = get_network_alias_manager()
    aliases = manager.get_all_aliases()
    handler.serve_json({
        'aliases': aliases,
        'count': len(aliases)
    })


# ==================== Speed Correlation ====================

@agent_router.route('GET', '/api/speed-correlation/analysis')
def handle_speed_correlation_analysis(handler):
    from urllib.parse import urlparse, parse_qs
    from atlas.speed_correlation import get_speed_correlation_analyzer
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    hours = safe_int_param(params, 'hours', 168, max_val=8760)
    analyzer = get_speed_correlation_analyzer()
    handler.serve_json(analyzer.get_correlation_analysis(hours))


@agent_router.route('GET', '/api/speed-correlation/data')
def handle_speed_correlation_data(handler):
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


@agent_router.route('GET', '/api/speed-correlation/summary')
def handle_speed_correlation_summary(handler):
    from atlas.speed_correlation import get_speed_correlation_analyzer
    analyzer = get_speed_correlation_analyzer()
    handler.serve_json(analyzer.get_summary())


# ==================== WiFi Roaming ====================

@agent_router.route('GET', '/api/wifi/roaming')
def handle_wifi_roaming_route(handler):
    _handle_wifi_roaming(handler)


@agent_router.route('GET', '/api/wifi/roaming/events')
def handle_wifi_roaming_events(handler):
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


@agent_router.route('GET', '/api/wifi/roaming/sessions')
def handle_wifi_roaming_sessions(handler):
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


@agent_router.route('GET', '/api/wifi/roaming/stats')
def handle_wifi_roaming_stats(handler):
    from urllib.parse import urlparse, parse_qs
    from atlas.wifi_roaming import get_wifi_roaming_tracker
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    hours = safe_int_param(params, 'hours', 24, max_val=8760)
    tracker = get_wifi_roaming_tracker()
    handler.serve_json(tracker.get_statistics(hours))


@agent_router.route('GET', '/api/wifi/roaming/timeline')
def handle_wifi_roaming_timeline(handler):
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


@agent_router.route('GET', '/api/wifi/roaming/current')
def handle_wifi_roaming_current(handler):
    from atlas.wifi_roaming import get_wifi_roaming_tracker
    tracker = get_wifi_roaming_tracker()
    handler.serve_json(tracker.get_current_state())


# ==================== Processes (GET) ====================
# NOTE: Specific routes registered before the generic /api/processes

@agent_router.route('GET', '/api/processes/search')
def handle_processes_search(handler):
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


@agent_router.route('GET', '/api/processes/problematic')
def handle_processes_problematic(handler):
    problematic = process_monitor.get_problematic_processes()
    handler.serve_json(problematic)


@agent_router.route('GET', '/api/processes')
def handle_processes(handler):
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


# ==================== Tools & Licensing ====================

@agent_router.route('GET', '/api/tools/status')
def handle_tools_status(handler):
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


@agent_router.route('GET', '/api/tools/licensing')
def handle_tools_licensing(handler):
    from atlas.licensing import get_api_licensing_info
    handler.serve_json(get_api_licensing_info())


# ==================== Network Path ====================

@agent_router.route('GET', '/api/traceroute')
def handle_traceroute(handler):
    from urllib.parse import urlparse, parse_qs
    from atlas.enhanced_traceroute import get_tracer
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    target = params.get('target', ['8.8.8.8'])[0]
    count = safe_int_param(params, 'count', 3, max_val=100)
    tracer = get_tracer()
    result = tracer.trace(target, count=count, max_hops=20)
    handler.serve_json(result.to_dict())


@agent_router.route('GET', '/api/traceroute/quick')
def handle_traceroute_quick(handler):
    from urllib.parse import urlparse, parse_qs
    from atlas.enhanced_traceroute import get_tracer
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    target = params.get('target', ['8.8.8.8'])[0]
    tracer = get_tracer()
    result = tracer.quick_trace(target)
    handler.serve_json(result)


@agent_router.route('GET', '/api/network/path-summary')
def handle_network_path_summary_route(handler):
    _handle_network_path_summary(handler)


# ==================== Agent Health ====================

@agent_router.route('GET', '/api/agent/health')
def handle_agent_health_route(handler):
    _handle_agent_health(handler)


# ==================== System Pressure ====================

@agent_router.route('GET', '/api/system/pressure')
def handle_system_pressure_route(handler):
    _handle_system_pressure(handler)


# ==================== Data Export (GET) ====================
# NOTE: /api/wifi/events/export registered before /api/wifi/export

@agent_router.route('GET', '/api/ping/export')
def handle_ping_export_get(handler):
    _handle_export(handler, 'ping')


@agent_router.route('GET', '/api/speedtest/export')
def handle_speedtest_export_get(handler):
    _handle_export(handler, 'speedtest')


@agent_router.route('GET', '/api/wifi/events/export')
def handle_wifi_events_export_get(handler):
    _handle_export(handler, 'wifi_events')


@agent_router.route('GET', '/api/wifi/export')
def handle_wifi_export_get(handler):
    _handle_export(handler, 'wifi')


# ==================== Network Analysis ====================

@agent_router.route('GET', '/api/network/analysis')
def handle_network_analysis(handler):
    from urllib.parse import urlparse, parse_qs
    from atlas.network_analyzer import get_network_analyzer
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    hours = safe_int_param(params, 'hours', 24, max_val=8760)
    analyzer = get_network_analyzer()
    report = analyzer.get_analysis_report(hours=hours)
    handler.serve_json(report)


@agent_router.route('GET', '/api/network/analysis/latest')
def handle_network_analysis_latest(handler):
    from atlas.network_analyzer import get_network_analyzer
    analyzer = get_network_analyzer()
    latest = analyzer.get_latest_analysis()
    handler.serve_json(latest)


@agent_router.route('GET', '/api/network/analysis/settings')
def handle_network_analysis_settings_get(handler):
    from atlas.network_analysis_settings import get_settings
    settings = get_settings()
    handler.serve_json(settings.get_all())


# ==================== Notifications ====================

@agent_router.route('GET', '/api/notifications/status')
def handle_notifications_status(handler):
    from atlas.notification_manager import get_notification_manager
    manager = get_notification_manager()
    handler.serve_json({
        'enabled': manager.is_enabled(),
        'min_interval_minutes': manager.min_notification_interval.total_seconds() / 60
    })


@agent_router.route('GET', '/api/notifications/history')
def handle_notifications_history(handler):
    from atlas.notification_manager import get_notification_manager
    manager = get_notification_manager()
    history = manager.get_notification_history(limit=50)
    handler.serve_json({'notifications': history})


# ==================== Alert Rules (GET) ====================
# NOTE: Specific routes registered before parameterized /api/alerts/rules/{rule_id}

@agent_router.route('GET', '/api/alerts/rules')
def handle_alerts_rules_list(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    manager = get_alert_rules_manager()
    include_disabled = handler.path.find('include_disabled=true') != -1
    rules = manager.list_rules(include_disabled=include_disabled)
    handler.serve_json({
        'rules': [r.to_dict() for r in rules],
        'count': len(rules)
    })


@agent_router.route('GET', '/api/alerts/events')
def handle_alerts_events(handler):
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


@agent_router.route('GET', '/api/alerts/statistics')
def handle_alerts_statistics(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    hours = safe_int_param(params, 'hours', 24, max_val=8760)
    manager = get_alert_rules_manager()
    stats = manager.get_alert_statistics(hours)
    handler.serve_json(stats)


@agent_router.route('GET', '/api/alerts/email-config')
def handle_alerts_email_config_get(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    manager = get_alert_rules_manager()
    config = manager.get_email_config()
    handler.serve_json(config or {'configured': False})


@agent_router.route('GET', '/api/alerts/metrics')
def handle_alerts_metrics(handler):
    from atlas.alert_rules_manager import MetricType, Condition, AlertSeverity
    handler.serve_json({
        'metric_types': [m.value for m in MetricType],
        'conditions': [c.value for c in Condition],
        'severities': [s.value for s in AlertSeverity]
    })


@agent_router.route('GET', '/api/alerts/rules/{rule_id}')
def handle_alerts_rule_detail(handler, rule_id):
    from atlas.alert_rules_manager import get_alert_rules_manager
    manager = get_alert_rules_manager()
    rule = manager.get_rule(rule_id)
    if rule:
        handler.serve_json(rule.to_dict())
    else:
        handler.send_error(404, f"Rule not found: {rule_id}")


# ==================== OSI Layers Diagnostic (GET) ====================

@agent_router.route('GET', '/api/osi-layers')
def handle_osi_layers(handler):
    from atlas.network.monitors.osi_diagnostic_monitor import get_osi_diagnostic_monitor
    monitor = get_osi_diagnostic_monitor()
    handler.serve_json(monitor.get_last_result())


# ==================== POST Routes ====================

# ==================== Processes (POST) ====================

@agent_router.route('POST', '/api/processes/kill/{pid}')
def handle_process_kill(handler, pid):
    try:
        pid_int = int(pid)
        result = process_monitor.kill_process(pid_int)
        handler.serve_json(result)
    except ValueError:
        handler.send_error(400, "Invalid PID")


# ==================== Network Analysis Settings (POST) ====================

@agent_router.route('POST', '/api/network/analysis/settings')
def handle_network_analysis_settings_post(handler):
    from atlas.network_analysis_settings import get_settings
    body = handler._read_body()
    if body is None:
        return
    new_settings = json.loads(body.decode('utf-8'))
    settings = get_settings()
    valid, error = settings.validate_settings(new_settings)
    if not valid:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': error}).encode())
        return
    success = settings.update(new_settings)
    if success:
        handler.serve_json({'status': 'success', 'settings': settings.get_all()})
    else:
        handler.send_error(500, "Failed to save settings")


# ==================== Dashboard Layout (POST) ====================

@agent_router.route('POST', '/api/dashboard/layout')
def handle_dashboard_layout_post(handler):
    prefs = get_dashboard_preferences()
    body = handler._read_body()
    if body is None:
        return
    new_layout = json.loads(body.decode('utf-8'))
    success = prefs.update_layout(new_layout)
    if success:
        handler.serve_json({'status': 'success', 'layout': prefs.get_layout()})
    else:
        handler.send_error(500, "Failed to save layout")


@agent_router.route('POST', '/api/dashboard/layout/reset')
def handle_dashboard_layout_reset(handler):
    prefs = get_dashboard_preferences()
    success = prefs.reset_to_default()
    if success:
        handler.serve_json({'status': 'success', 'layout': prefs.get_layout()})
    else:
        handler.send_error(500, "Failed to reset layout")


# ==================== Notifications (POST) ====================

@agent_router.route('POST', '/api/notifications/enable')
def handle_notifications_enable(handler):
    from atlas.notification_manager import get_notification_manager
    manager = get_notification_manager()
    manager.enable_notifications()
    handler.serve_json({'status': 'success', 'enabled': True})


@agent_router.route('POST', '/api/notifications/disable')
def handle_notifications_disable(handler):
    from atlas.notification_manager import get_notification_manager
    manager = get_notification_manager()
    manager.disable_notifications()
    handler.serve_json({'status': 'success', 'enabled': False})


@agent_router.route('POST', '/api/notifications/test')
def handle_notifications_test(handler):
    from atlas.notification_manager import get_notification_manager
    manager = get_notification_manager()
    success = manager.send_custom_notification(
        "ATLAS Test Notification",
        "This is a test notification from ATLAS Agent"
    )
    handler.serve_json({'status': 'success' if success else 'failed', 'sent': success})


# ==================== Speed Test (POST) ====================

@agent_router.route('POST', '/api/speedtest/run')
def handle_speedtest_run(handler):
    monitor = _get_speed_test_monitor()
    monitor.run_test_now()
    handler.serve_json({'status': 'started', 'message': 'Speed test started', 'mode': monitor.get_test_mode()})


@agent_router.route('POST', '/api/speedtest/run-full')
def handle_speedtest_run_full(handler):
    monitor = _get_speed_test_monitor()
    monitor.run_full_test_now()
    handler.serve_json({'status': 'started', 'message': 'Full speed test started', 'mode': 'full'})


@agent_router.route('POST', '/api/speedtest/mode')
def handle_speedtest_mode_post(handler):
    monitor = _get_speed_test_monitor()
    handler.serve_json(monitor.get_mode_info())


@agent_router.route('POST', '/api/speedtest/mode/set')
def handle_speedtest_mode_set(handler):
    body = handler._read_body()
    if body is None:
        return
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


# ==================== WiFi Aliases (POST) ====================

@agent_router.route('POST', '/api/wifi/alias/set')
def handle_wifi_alias_set(handler):
    from atlas.wifi_analyzer import get_network_alias_manager
    body = handler._read_body()
    if body is None:
        return
    data = json.loads(body.decode('utf-8'))
    alias = data.get('alias', '').strip()
    if not alias:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': 'Alias is required'}).encode())
        return
    manager = get_network_alias_manager()
    fingerprint = manager.get_current_fingerprint()
    if not fingerprint:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': 'No network connected'}).encode())
        return
    manager.set_alias(fingerprint, alias)
    handler.serve_json({
        'status': 'success',
        'fingerprint': fingerprint,
        'alias': alias
    })


@agent_router.route('POST', '/api/wifi/alias/remove')
def handle_wifi_alias_remove(handler):
    from atlas.wifi_analyzer import get_network_alias_manager
    body = handler._read_body()
    if body is None:
        return
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
        return
    manager = get_network_alias_manager()
    success = manager.remove_alias(fingerprint)
    handler.serve_json({
        'status': 'success' if success else 'not_found',
        'fingerprint': fingerprint
    })


# ==================== Network Testing (POST) ====================

@agent_router.route('POST', '/api/network/connection-test')
def handle_network_connection_test(handler):
    try:
        from atlas.network.monitors import get_tcp_connection_tester
        body = handler._read_body()
        if body is None:
            return
        body = body if body else b'{}'
        json.loads(body.decode('utf-8'))
        tester = get_tcp_connection_tester()
        result = tester.run_single_test()
        handler.serve_json(result)
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        handler.serve_json({'error': 'Test failed', 'status': 'failed'})


@agent_router.route('POST', '/api/network/throughput-test')
def handle_network_throughput_test(handler):
    try:
        from atlas.network.monitors import get_throughput_tester
        body = handler._read_body()
        if body is None:
            return
        body = body if body else b'{}'
        data = json.loads(body.decode('utf-8'))
        server_host = data.get('server_host')
        server_port = data.get('server_port', 5007)
        duration = data.get('duration', 5)
        if not server_host:
            handler.serve_json({'error': 'server_host is required', 'status': 'failed'})
            return
        tester = get_throughput_tester(server_host)
        tester.set_server(server_host, server_port)
        tester.test_duration = duration
        result = tester.run_full_test()
        handler.serve_json(result)
    except Exception as e:
        logger.error(f"Throughput test error: {e}")
        handler.serve_json({'error': 'Test failed', 'status': 'failed'})


@agent_router.route('POST', '/api/network/udp-test')
def handle_network_udp_test(handler):
    try:
        from atlas.network.monitors import get_udp_quality_monitor
        body = handler._read_body()
        if body is None:
            return
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
# NOTE: /api/alerts/rules/reset registered before /api/alerts/rules/{rule_id}/...

@agent_router.route('POST', '/api/alerts/rules')
def handle_alerts_rules_create(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
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


@agent_router.route('POST', '/api/alerts/rules/reset')
def handle_alerts_rules_reset(handler):
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


@agent_router.route('POST', '/api/alerts/rules/{rule_id}/update')
def handle_alerts_rule_update(handler, rule_id):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
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


@agent_router.route('POST', '/api/alerts/rules/{rule_id}/delete')
def handle_alerts_rule_delete(handler, rule_id):
    from atlas.alert_rules_manager import get_alert_rules_manager
    manager = get_alert_rules_manager()
    success, message = manager.delete_rule(rule_id)
    if success:
        handler.serve_json({'status': 'success', 'message': message})
    else:
        handler.send_response(404)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': message}).encode())


@agent_router.route('POST', '/api/alerts/rules/{rule_id}/toggle')
def handle_alerts_rule_toggle(handler, rule_id):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
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


@agent_router.route('POST', '/api/alerts/events/{event_id}/acknowledge')
def handle_alerts_event_acknowledge(handler, event_id):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
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


@agent_router.route('POST', '/api/alerts/email-config')
def handle_alerts_email_config_post(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
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


@agent_router.route('POST', '/api/alerts/email-test')
def handle_alerts_email_test(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
    data = json.loads(body.decode('utf-8'))
    recipient = data.get('recipient')
    if not recipient:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': 'recipient is required'}).encode())
        return
    manager = get_alert_rules_manager()
    success, message = manager.test_email(recipient)
    if success:
        handler.serve_json({'status': 'success', 'message': message})
    else:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': message}).encode())


@agent_router.route('POST', '/api/alerts/evaluate')
def handle_alerts_evaluate(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
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


@agent_router.route('POST', '/api/alerts/cleanup')
def handle_alerts_cleanup(handler):
    from atlas.alert_rules_manager import get_alert_rules_manager
    body = handler._read_body()
    if body is None:
        return
    data = json.loads(body.decode('utf-8')) if body else {}
    days = safe_int_param(data, 'days', 30, max_val=365) if isinstance(data.get('days'), list) else min(int(data.get('days', 30)), 365)
    manager = get_alert_rules_manager()
    deleted = manager.cleanup_old_events(days)
    handler.serve_json({
        'status': 'success',
        'deleted_count': deleted,
        'message': f'Deleted {deleted} events older than {days} days'
    })


# ==================== Encrypted Export (POST) ====================
# NOTE: /api/wifi/events/export registered before /api/wifi/export

@agent_router.route('POST', '/api/ping/export')
def handle_ping_export_post(handler):
    _handle_encrypted_export(handler, 'ping')


@agent_router.route('POST', '/api/speedtest/export')
def handle_speedtest_export_post(handler):
    _handle_encrypted_export(handler, 'speedtest')


@agent_router.route('POST', '/api/wifi/events/export')
def handle_wifi_events_export_post(handler):
    _handle_encrypted_export(handler, 'wifi_events')


@agent_router.route('POST', '/api/wifi/export')
def handle_wifi_export_post(handler):
    _handle_encrypted_export(handler, 'wifi')


# ==================== OSI Layers Diagnostic (POST) ====================

@agent_router.route('POST', '/api/osi-layers/test')
def handle_osi_layers_test(handler):
    from atlas.network.monitors.osi_diagnostic_monitor import get_osi_diagnostic_monitor
    from dataclasses import asdict
    monitor = get_osi_diagnostic_monitor()
    result = monitor.run_diagnostic()
    result_dict = asdict(result)
    monitor.update_last_result(result_dict)
    handler.serve_json({'status': 'success', 'result': result_dict})


@agent_router.route('POST', '/api/osi-layers/network-quality')
def handle_osi_layers_network_quality(handler):
    _handle_network_quality(handler)


@agent_router.route('POST', '/api/osi-layers/custom-scan')
def handle_osi_layers_custom_scan(handler):
    _handle_custom_scan(handler)


# ==================== Complex Handler Helpers ====================


def _handle_system_health_overview(handler):
    """Handle /api/system-health/overview endpoint."""
    overview = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'monitors': {}
    }

    dm = get_monitor('display')
    if dm:
        try:
            status = dm.get_status()
            overview['monitors']['display'] = {
                'status': status.get('status', 'unknown'),
                'display_count': status.get('display', {}).get('display_count', 0),
                'gpu': status.get('gpu', {}).get('gpu_name', 'Unknown')
            }
        except Exception as e:
            overview['monitors']['display'] = {'status': 'error', 'error': str(e)}

    pm = get_monitor('power')
    if pm:
        try:
            summary = pm.get_power_summary()
            overview['monitors']['power'] = {
                'status': 'healthy' if summary.get('battery', {}).get('health_percentage', 0) > 50 else 'warning',
                'battery_health': summary.get('battery', {}).get('health_percentage', 0),
                'is_charging': summary.get('battery', {}).get('is_charging', False),
                'thermal_status': summary.get('thermal', {}).get('status', 'Unknown')
            }
        except Exception as e:
            overview['monitors']['power'] = {'status': 'error', 'error': str(e)}

    perm = get_monitor('peripheral')
    if perm:
        try:
            summary = perm.get_peripheral_summary()
            overview['monitors']['peripherals'] = {
                'status': 'healthy',
                'bluetooth_devices': summary.get('bluetooth', {}).get('total_devices', 0),
                'usb_devices': summary.get('usb', {}).get('total_devices', 0)
            }
        except Exception as e:
            overview['monitors']['peripherals'] = {'status': 'error', 'error': str(e)}

    sm = get_monitor('security')
    if sm:
        try:
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

    disk_mon = get_monitor('disk')
    if disk_mon:
        try:
            summary = disk_mon.get_disk_health_summary()
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


def _grade_bufferbloat(idle_ms: float, loaded_ms: float) -> str:
    """Grade bufferbloat severity from idle vs loaded latency ratio.

    Returns letter grade A-F based on how much latency increases under load.
    """
    if idle_ms <= 0:
        return 'N/A'
    ratio = loaded_ms / idle_ms
    if ratio < 1.5:
        return 'A'
    elif ratio < 3.0:
        return 'B'
    elif ratio < 5.0:
        return 'C'
    elif ratio < 10.0:
        return 'D'
    return 'F'


def _handle_network_quality(handler):
    """Handle POST /api/osi-layers/network-quality endpoint.

    Runs macOS `networkQuality -c -s` command and parses JSON output.
    Returns throughput (Mbps), responsiveness (RPM), latency, and bufferbloat grade.
    """
    import subprocess

    try:
        proc = subprocess.run(
            ['networkQuality', '-c', '-s'],
            capture_output=True, text=True, timeout=45
        )
        if proc.returncode != 0:
            handler.serve_json({
                'error': f'networkQuality exited with code {proc.returncode}',
                'stderr': proc.stderr[:500] if proc.stderr else ''
            })
            return

        data = json.loads(proc.stdout)

        dl_throughput = data.get('dl_throughput', 0) / 1_000_000  # bps -> Mbps
        ul_throughput = data.get('ul_throughput', 0) / 1_000_000
        dl_responsiveness = data.get('dl_responsiveness', 0)  # RPM
        ul_responsiveness = data.get('ul_responsiveness', 0)
        idle_latency = data.get('idle_latency_ms', 0) or data.get('base_rtt', 0)
        dl_loaded_latency = data.get('dl_latency_ms', 0) or data.get('dl_loaded_latency_ms', 0)
        ul_loaded_latency = data.get('ul_latency_ms', 0) or data.get('ul_loaded_latency_ms', 0)

        # Use the worse loaded latency for grading
        loaded_latency = max(dl_loaded_latency, ul_loaded_latency)
        grade = _grade_bufferbloat(idle_latency, loaded_latency) if idle_latency > 0 else 'N/A'

        handler.serve_json({
            'status': 'success',
            'download_mbps': round(dl_throughput, 1),
            'upload_mbps': round(ul_throughput, 1),
            'dl_responsiveness_rpm': dl_responsiveness,
            'ul_responsiveness_rpm': ul_responsiveness,
            'idle_latency_ms': round(idle_latency, 1),
            'dl_loaded_latency_ms': round(dl_loaded_latency, 1),
            'ul_loaded_latency_ms': round(ul_loaded_latency, 1),
            'bufferbloat_grade': grade,
            'raw': data
        })

    except FileNotFoundError:
        handler.serve_json({
            'error': 'networkQuality command not found (requires macOS 12+)',
            'status': 'unavailable'
        })
    except subprocess.TimeoutExpired:
        handler.serve_json({
            'error': 'networkQuality timed out after 45 seconds',
            'status': 'timeout'
        })
    except (json.JSONDecodeError, KeyError) as e:
        handler.serve_json({
            'error': f'Failed to parse networkQuality output: {e}',
            'status': 'parse_error'
        })
    except Exception as e:
        logger.error(f"networkQuality error: {e}")
        handler.serve_json({
            'error': str(e),
            'status': 'error'
        })


def _handle_custom_scan(handler):
    """Handle POST /api/osi-layers/custom-scan endpoint.

    Accepts custom targets and runs a one-time scan.
    Body JSON keys: ports, ping_targets, dns_hostnames, http_urls, tls_targets
    """
    body = handler._read_body()
    if body is None:
        return

    try:
        options = json.loads(body.decode('utf-8')) if body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': 'Invalid JSON body'}).encode())
        return

    # Validate: at least one scan target must be provided
    has_targets = any(
        options.get(k) for k in ('ports', 'ping_targets', 'dns_hostnames', 'http_urls', 'tls_targets')
    )
    if not has_targets:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': 'No scan targets provided'}).encode())
        return

    # Cap total targets to prevent abuse
    total_targets = sum(
        len(options.get(k, [])) for k in ('ports', 'ping_targets', 'dns_hostnames', 'http_urls', 'tls_targets')
    )
    if total_targets > 50:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'error': 'Too many targets (max 50)'}).encode())
        return

    try:
        from atlas.network.monitors.osi_diagnostic_monitor import get_osi_diagnostic_monitor
        monitor = get_osi_diagnostic_monitor()
        result = monitor.run_custom_scan(options)
        handler.serve_json({'status': 'success', 'result': result})
    except Exception as e:
        logger.error(f"Custom scan error: {e}")
        handler.serve_json({'error': str(e), 'status': 'error'})


# ==================== Backward-compatible dispatch ====================

def dispatch_get(handler, path):
    """Handle GET requests for API data endpoints.

    Args:
        handler: LiveWidgetHandler instance
        path: URL path (without query string)

    Returns:
        True if the request was handled, False otherwise
    """
    return agent_router.dispatch_get(handler, path)


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
    return agent_router.dispatch_post(handler, path)
