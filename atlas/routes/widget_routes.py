"""
Widget and page HTML routes for the agent dashboard.

Handles all GET /widget/* and page routes (/, /dashboard, /help).
"""
from atlas.speedtest_widget import get_speedtest_widget_html, get_speedtest_history_widget_html
from atlas.ping_widget import get_ping_widget_html
from atlas.wifi_widget import get_wifi_widget_html
from atlas.process_widget import get_process_widget_html
from atlas.system_monitor_widget import get_system_monitor_widget_html
from atlas.security_dashboard_widget import get_security_dashboard_widget_html
from atlas.vpn_status_widget import get_vpn_status_widget_html
from atlas.saas_health_widget import get_saas_health_widget_html
from atlas.network_quality_widget import get_network_quality_widget_html
from atlas.wifi_roaming_widget import get_wifi_roaming_widget_html
from atlas.power_widget import get_power_widget_html
from atlas.display_widget import get_display_widget_html
from atlas.peripherals_widget import get_peripherals_widget_html
from atlas.system_health_widget import get_system_health_widget_html
from atlas.disk_health_widget import get_disk_health_widget_html
from atlas.network_analysis_widget import get_network_analysis_widget_html
from atlas.voip_quality_widget import get_voip_quality_widget_html
from atlas.connection_rate_widget import get_connection_rate_widget_html
from atlas.throughput_widget import get_throughput_widget_html
from atlas.network_testing_widget import get_network_testing_widget_html
from atlas.widget_html_generators import (
    get_cpu_widget_html,
    get_gpu_widget_html,
    get_memory_widget_html,
    get_disk_widget_html,
    get_network_widget_html,
    get_wifi_analyzer_widget_html,
    get_wifi_analyzer_compact_widget_html,
    get_speed_correlation_widget_html,
    get_info_widget_html,
)
from atlas.page_generators import (
    get_homepage_html,
    get_help_html,
    get_dashboard_html,
)


def dispatch_get(handler, path):
    """Handle GET requests for widget HTML pages.

    Args:
        handler: LiveWidgetHandler instance
        path: URL path (without query string)

    Returns:
        True if the request was handled, False otherwise
    """
    # ==================== Page Routes ====================

    if path == '/':
        handler.serve_html(get_homepage_html())

    elif path == '/dashboard':
        handler.serve_html(get_dashboard_html())

    elif path == '/help':
        handler.serve_html(get_help_html())

    # ==================== Core Widget Routes ====================

    elif path == '/widget/cpu':
        handler.serve_html(get_cpu_widget_html())

    elif path == '/widget/gpu':
        handler.serve_html(get_gpu_widget_html())

    elif path == '/widget/memory':
        handler.serve_html(get_memory_widget_html())

    elif path == '/widget/disk':
        handler.serve_html(get_disk_widget_html())

    elif path == '/widget/network':
        handler.serve_html(get_network_widget_html())

    elif path == '/widget/info':
        handler.serve_html(get_info_widget_html())

    elif path == '/widget/speedtest':
        handler.serve_html(get_speedtest_widget_html())

    elif path == '/widget/speedtest-history':
        handler.serve_html(get_speedtest_history_widget_html())

    elif path == '/widget/health':
        handler.serve_html(get_system_health_widget_html())

    elif path == '/widget/ping':
        handler.serve_html(get_ping_widget_html())

    elif path == '/widget/wifi':
        handler.serve_html(get_wifi_widget_html())

    elif path == '/widget/processes':
        handler.serve_html(get_process_widget_html())

    elif path == '/widget/system-monitor':
        handler.serve_html(get_system_monitor_widget_html())

    # ==================== Dashboard Widget Routes ====================

    elif path == '/widget/security-dashboard':
        handler.serve_html(get_security_dashboard_widget_html())

    elif path == '/widget/vpn-status':
        handler.serve_html(get_vpn_status_widget_html())

    elif path == '/widget/saas-health':
        handler.serve_html(get_saas_health_widget_html())

    elif path == '/widget/network-quality':
        handler.serve_html(get_network_quality_widget_html())

    elif path == '/widget/wifi-roaming':
        handler.serve_html(get_wifi_roaming_widget_html())

    elif path == '/widget/power':
        handler.serve_html(get_power_widget_html())

    elif path == '/widget/display':
        handler.serve_html(get_display_widget_html())

    elif path == '/widget/peripherals':
        handler.serve_html(get_peripherals_widget_html())

    elif path == '/widget/security-status':
        handler.serve_html(get_security_dashboard_widget_html())

    elif path == '/widget/system-health':
        handler.serve_html(get_system_health_widget_html())

    elif path == '/widget/disk-health':
        handler.serve_html(get_disk_health_widget_html())

    # ==================== Network Testing Widgets ====================

    elif path == '/widget/network-testing':
        handler.serve_html(get_network_testing_widget_html())

    elif path == '/widget/voip-quality':
        handler.serve_html(get_voip_quality_widget_html())

    elif path == '/widget/connection-rate':
        handler.serve_html(get_connection_rate_widget_html())

    elif path == '/widget/throughput':
        handler.serve_html(get_throughput_widget_html())

    # ==================== Analysis Widgets ====================

    elif path == '/widget/wifi-analyzer':
        handler.serve_html(get_wifi_analyzer_widget_html())

    elif path == '/widget/wifi-analyzer-compact':
        handler.serve_html(get_wifi_analyzer_compact_widget_html())

    elif path == '/widget/speed-correlation':
        handler.serve_html(get_speed_correlation_widget_html())

    elif path == '/widget/network-analysis':
        handler.serve_html(get_network_analysis_widget_html())

    # ==================== Lazy-Loaded Widgets ====================

    elif path == '/widget/tools':
        from atlas.tools_widget import get_tools_widget_html
        handler.serve_html(get_tools_widget_html())

    elif path == '/widget/network-path':
        from atlas.network_path_widget import get_network_path_widget_html
        handler.serve_html(get_network_path_widget_html())

    elif path == '/widget/alert-rules':
        from atlas.alert_rules_widget import get_alert_rules_widget_html
        handler.serve_html(get_alert_rules_widget_html())

    elif path == '/widget/trends':
        from atlas.trend_visualization_widget import get_trend_visualization_widget_html
        handler.serve_html(get_trend_visualization_widget_html())

    elif path == '/widget/comparison':
        from atlas.machine_comparison_widget import get_machine_comparison_widget_html
        handler.serve_html(get_machine_comparison_widget_html())

    else:
        return False

    return True
