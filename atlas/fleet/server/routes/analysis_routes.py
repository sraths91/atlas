"""
Fleet Analysis Routes

Route handlers for network analysis and speedtest analytics endpoints.
Extracted from fleet_server.py (Phase 4 Stage 4).

This module handles:
- SpeedTest aggregation and analytics (7 routes)
- Network analysis (fleet-wide and per-machine) (2 routes)
- Widget logs retrieval (1 route)

Created: December 31, 2025
"""
import json
import logging
from urllib.parse import parse_qs, urlparse

from atlas.fleet.server.router import read_request_body, send_json, send_error, send_unauthorized
from atlas.config.defaults import safe_int_param

logger = logging.getLogger(__name__)


def register_analysis_routes(router, data_store, auth_manager):
    """Register all analysis-related routes with the FleetRouter

    Args:
        router: FleetRouter instance
        data_store: FleetDataStore instance
        auth_manager: FleetAuthManager instance
    """

    # Helper to parse query parameters
    def get_query_params(handler):
        """Extract query parameters from request"""
        parsed = urlparse(handler.path)
        return parse_qs(parsed.query)


    # GET /api/fleet/speedtest/summary - Fleet-wide speedtest summary
    def handle_speedtest_summary(handler):
        """Get fleet-wide speedtest summary"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

            params = get_query_params(handler)
            hours = safe_int_param(params, 'hours', 24, max_val=8760)

            aggregator = SpeedTestAggregator()
            summary = aggregator.get_fleet_summary(hours)

            send_json(handler, summary)
        except Exception as e:
            logger.error(f"Error getting speedtest summary: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/speedtest/machine - Machine-specific speedtest stats
    def handle_speedtest_machine(handler):
        """Get machine-specific speedtest statistics"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

            params = get_query_params(handler)
            machine_id = params.get('machine_id', [None])[0]
            hours = safe_int_param(params, 'hours', 168, max_val=8760)

            if not machine_id:
                send_error(handler, 'Missing machine_id', status=400)
                return

            aggregator = SpeedTestAggregator()
            stats = aggregator.get_machine_stats(machine_id, hours)

            send_json(handler, stats)
        except Exception as e:
            logger.error(f"Error getting machine speedtest stats: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/speedtest/comparison - Speedtest comparison report
    def handle_speedtest_comparison(handler):
        """Get speedtest comparison report"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

            params = get_query_params(handler)
            hours = safe_int_param(params, 'hours', 24, max_val=8760)

            aggregator = SpeedTestAggregator()
            report = aggregator.get_comparison_report(hours)

            send_json(handler, report)
        except Exception as e:
            logger.error(f"Error getting speedtest comparison: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/speedtest/anomalies - Speedtest anomaly detection
    def handle_speedtest_anomalies(handler):
        """Detect speedtest anomalies for a machine"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

            params = get_query_params(handler)
            machine_id = params.get('machine_id', [None])[0]

            if not machine_id:
                send_error(handler, 'Missing machine_id', status=400)
                return

            aggregator = SpeedTestAggregator()
            anomalies = aggregator.detect_anomalies(machine_id)

            send_json(handler, {'anomalies': anomalies, 'count': len(anomalies)})
        except Exception as e:
            logger.error(f"Error detecting speedtest anomalies: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/speedtest/recent - Recent speedtest results
    def handle_speedtest_recent(handler):
        """Get recent speedtest results"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

            params = get_query_params(handler)
            machine_id = params.get('machine_id', [None])[0]
            hours = safe_int_param(params, 'hours', 24, max_val=8760)
            limit = safe_int_param(params, 'limit', 100, max_val=10000)

            aggregator = SpeedTestAggregator()
            results = aggregator.get_recent_results(machine_id, hours, limit)

            send_json(handler, {'results': results, 'count': len(results)})
        except Exception as e:
            logger.error(f"Error getting recent speedtest results: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/speedtest/recent20 - Average of recent 20 tests per machine
    def handle_speedtest_recent20(handler):
        """Get average of recent 20 speedtests per machine"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

            params = get_query_params(handler)
            machine_id = params.get('machine_id', [None])[0]

            aggregator = SpeedTestAggregator()
            results = aggregator.get_recent_20_average(machine_id)

            send_json(handler, results)
        except Exception as e:
            logger.error(f"Error getting recent 20 average: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/speedtest/subnet - Subnet analysis
    def handle_speedtest_subnet(handler):
        """Get speedtest analysis by subnet"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            from atlas.fleet_speedtest_aggregator import SpeedTestAggregator

            params = get_query_params(handler)
            subnet = params.get('subnet', [None])[0]

            aggregator = SpeedTestAggregator()
            analysis = aggregator.get_subnet_analysis(subnet)

            send_json(handler, analysis)
        except Exception as e:
            logger.error(f"Error getting subnet analysis: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/network-analysis - Fleet-wide network analysis
    def handle_network_analysis_fleet(handler):
        """Get fleet-wide network analysis"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            import urllib.parse
            from atlas.fleet_network_analyzer import FleetNetworkAnalyzer

            # Parse query parameters
            query_string = handler.path.split('?')[1] if '?' in handler.path else ''
            params = urllib.parse.parse_qs(query_string)
            hours = safe_int_param(params, 'hours', 24, max_val=8760)

            analyzer = FleetNetworkAnalyzer(data_store)
            report = analyzer.analyze_fleet(hours=hours)

            send_json(handler, report)
        except Exception as e:
            logger.error(f"Error analyzing fleet network: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/network-analysis/{machine_id} - Machine-specific network analysis
    def handle_network_analysis_machine(handler, machine_id):
        """Get machine-specific network analysis"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            import urllib.parse
            from atlas.fleet_network_analyzer import FleetNetworkAnalyzer

            # Parse query parameters
            query_string = handler.path.split('?')[1] if '?' in handler.path else ''
            params = urllib.parse.parse_qs(query_string)
            hours = safe_int_param(params, 'hours', 24, max_val=8760)

            analyzer = FleetNetworkAnalyzer(data_store)
            report = analyzer.analyze_machine(machine_id, hours=hours)

            send_json(handler, report)
        except Exception as e:
            logger.error(f"Error analyzing machine network: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/widget-logs - Get widget logs with filtering
    def handle_widget_logs_get(handler):
        """Get widget logs with optional filtering"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            params = get_query_params(handler)
            machine_id = params.get('machine_id', [None])[0]
            widget_type = params.get('widget_type', [None])[0]
            limit = safe_int_param(params, 'limit', 100, max_val=10000)

            if hasattr(data_store, 'get_widget_logs'):
                logs = data_store.get_widget_logs(machine_id, limit, widget_type)
                send_json(handler, {'logs': logs, 'count': len(logs)})
            else:
                send_json(handler, {'logs': [], 'count': 0})
        except Exception as e:
            logger.error(f"Error getting widget logs: {e}")
            send_error(handler, 'Internal server error')


    # ==================== Network Quality Testing Endpoints (CyPerf-inspired) ====================

    # GET /api/fleet/network-test/servers - Get network test server info
    def handle_network_test_servers(handler):
        """Get information about available network test servers"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            # Get fleet server IP for agent configuration
            import socket
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            local_ips = [ip for ip in local_ips if not ip.startswith("127.")]
            server_ip = local_ips[0] if local_ips else 'localhost'

            servers = {
                'udp_echo': {
                    'host': server_ip,
                    'port': 5005,
                    'description': 'UDP Echo Server for VoIP/video quality testing (jitter, packet loss)',
                    'protocol': 'UDP'
                },
                'tcp_connection': {
                    'host': server_ip,
                    'port': 5006,
                    'description': 'TCP Connection Server for CPS (connections per second) testing',
                    'protocol': 'TCP'
                },
                'throughput': {
                    'host': server_ip,
                    'port': 5007,
                    'description': 'Throughput Server for enterprise bandwidth testing',
                    'protocol': 'TCP'
                }
            }

            send_json(handler, {
                'servers': servers,
                'fleet_server_ip': server_ip,
                'info': 'Use these servers for enterprise-grade network testing instead of public servers'
            })

        except Exception as e:
            logger.error(f"Error getting network test servers: {e}")
            send_error(handler, 'Internal server error')


    # POST /api/fleet/network-test/calculate-mos - Calculate MOS score from metrics
    def handle_calculate_mos(handler):
        """Calculate MOS (Mean Opinion Score) from network metrics"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body) if body else {}

            # Get metrics from request
            latency_ms = float(data.get('latency_ms', 0))
            jitter_ms = float(data.get('jitter_ms', 0))
            packet_loss_percent = float(data.get('packet_loss_percent', 0))
            codec = data.get('codec', 'G.711')

            from atlas.network.monitors import calculate_network_mos, CodecType

            # Map codec name to CodecType
            codec_map = {
                'G.711': CodecType.G711,
                'G.729': CodecType.G729,
                'Opus': CodecType.OPUS,
                'SILK': CodecType.SILK,
                'Speex': CodecType.SPEEX,
            }
            codec_type = codec_map.get(codec, CodecType.G711)

            result = calculate_network_mos(
                ping_latency_ms=latency_ms,
                jitter_ms=jitter_ms,
                packet_loss_percent=packet_loss_percent,
                codec=codec_type
            )

            send_json(handler, result)

        except Exception as e:
            logger.error(f"Error calculating MOS: {e}")
            send_error(handler, 'Internal server error')


    # GET /api/fleet/network-test/mos-simple - Quick MOS estimation
    def handle_mos_simple(handler):
        """Quick MOS estimation from query parameters"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            params = get_query_params(handler)
            latency_ms = float(params.get('latency_ms', ['0'])[0])
            jitter_ms = float(params.get('jitter_ms', ['0'])[0])
            packet_loss_percent = float(params.get('packet_loss', ['0'])[0])

            from atlas.network.monitors import estimate_mos_simple, get_mos_color

            mos, rating = estimate_mos_simple(latency_ms, jitter_ms, packet_loss_percent)

            send_json(handler, {
                'mos': mos,
                'rating': rating,
                'color': get_mos_color(mos),
                'input': {
                    'latency_ms': latency_ms,
                    'jitter_ms': jitter_ms,
                    'packet_loss_percent': packet_loss_percent
                }
            })

        except Exception as e:
            logger.error(f"Error in simple MOS calculation: {e}")
            send_error(handler, 'Internal server error')


    # ==================== Network Test Metrics Submission (Agent -> Server) ====================

    # POST /api/fleet/network-test/metrics - Submit network test metrics from agent
    def handle_network_test_metrics_submit(handler):
        """Receive network test metrics from agent"""
        try:
            body = read_request_body(handler)
            if body is None:
                return
            data = json.loads(body) if body else {}

            machine_id = data.get('machine_id')
            test_type = data.get('test_type')
            metrics = data.get('metrics', {})

            if not machine_id or not test_type:
                send_error(handler, 'Missing required fields: machine_id and test_type', status=400)
                return

            # Store metrics in data store
            data_store.store_network_test_metrics(machine_id, test_type, metrics)

            send_json(handler, {
                'success': True,
                'message': f'Stored {test_type} metrics for {machine_id}'
            })

        except Exception as e:
            logger.error(f"Error storing network test metrics: {e}")
            send_error(handler, 'Internal server error')

    # GET /api/fleet/network-test/metrics - Get network test metrics for a machine
    def handle_network_test_metrics_get(handler):
        """Get network test metrics for a machine"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            params = get_query_params(handler)
            machine_id = params.get('machine_id', [None])[0]
            test_type = params.get('test_type', [None])[0]
            limit = safe_int_param(params, 'limit', 50, max_val=10000)

            if not machine_id:
                send_error(handler, 'Missing machine_id', status=400)
                return

            metrics = data_store.get_network_test_metrics(machine_id, test_type, limit)

            send_json(handler, metrics)

        except Exception as e:
            logger.error(f"Error getting network test metrics: {e}")
            send_error(handler, 'Internal server error')

    # GET /api/fleet/network-test/summary - Fleet-wide network test summary
    def handle_network_test_summary(handler):
        """Get fleet-wide network test summary"""
        # Check web authentication
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            params = get_query_params(handler)
            test_type = params.get('test_type', [None])[0]
            hours = safe_int_param(params, 'hours', 24, max_val=8760)

            summary = data_store.get_fleet_network_test_summary(test_type, hours)

            send_json(handler, summary)

        except Exception as e:
            logger.error(f"Error getting network test summary: {e}")
            send_error(handler, 'Internal server error')

    # GET /api/fleet/export-logs - Get permanent export logs
    def handle_export_logs_get(handler):
        """Get export logs (permanent storage, not subject to widget_logs cleanup)"""
        is_authenticated, _ = auth_manager.check_web_auth(handler)
        if not is_authenticated:
            send_unauthorized(handler)
            return

        try:
            params = get_query_params(handler)
            machine_id = params.get('machine_id', [None])[0]
            limit = safe_int_param(params, 'limit', 200, max_val=10000)

            if hasattr(data_store, 'get_export_logs'):
                logs = data_store.get_export_logs(machine_id, limit)
                send_json(handler, {'logs': logs, 'count': len(logs)})
            else:
                send_json(handler, {'logs': [], 'count': 0})
        except Exception as e:
            logger.error(f"Error getting export logs: {e}")
            send_error(handler, 'Internal server error')


    # Register routes with router
    router.get('/api/fleet/export-logs', handle_export_logs_get)
    router.get('/api/fleet/speedtest/summary', handle_speedtest_summary)
    router.get('/api/fleet/speedtest/machine', handle_speedtest_machine)
    router.get('/api/fleet/speedtest/comparison', handle_speedtest_comparison)
    router.get('/api/fleet/speedtest/anomalies', handle_speedtest_anomalies)
    router.get('/api/fleet/speedtest/recent', handle_speedtest_recent)
    router.get('/api/fleet/speedtest/recent20', handle_speedtest_recent20)
    router.get('/api/fleet/speedtest/subnet', handle_speedtest_subnet)
    router.get('/api/fleet/network-analysis', handle_network_analysis_fleet)
    router.get('/api/fleet/network-analysis/{machine_id}', handle_network_analysis_machine)
    router.get('/api/fleet/widget-logs', handle_widget_logs_get)

    # Network test endpoints (CyPerf-inspired)
    router.get('/api/fleet/network-test/servers', handle_network_test_servers)
    router.post('/api/fleet/network-test/calculate-mos', handle_calculate_mos)
    router.get('/api/fleet/network-test/mos-simple', handle_mos_simple)

    # Network test metrics submission and retrieval
    router.post('/api/fleet/network-test/metrics', handle_network_test_metrics_submit)
    router.get('/api/fleet/network-test/metrics', handle_network_test_metrics_get)
    router.get('/api/fleet/network-test/summary', handle_network_test_summary)


__all__ = ['register_analysis_routes']
