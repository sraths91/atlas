"""
Network Quality Widget - Advanced network performance monitoring

Displays:
- Overall network quality score
- TCP retransmission rate chart
- DNS query latency by resolver
- TLS handshake performance
- HTTP response time trends
- Quality indicators by protocol
"""

import logging

logger = logging.getLogger(__name__)


def get_network_quality_widget_html():
    """Generate Network Quality widget HTML

    Returns HTML widget for network quality monitoring with:
    - Overall quality score
    - TCP statistics
    - DNS resolver performance
    - TLS handshake metrics
    - HTTP response times
    - Protocol-level health indicators
    """
    # Import shared styles
    from atlas.agent_widget_styles import (
        get_widget_base_styles,
        get_widget_toast_script,
        get_widget_api_helpers_script
    )

    base_styles = get_widget_base_styles()
    toast_script = get_widget_toast_script()
    api_helpers = get_widget_api_helpers_script()

    html_start = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Quality - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* Network Quality Widget Specific Styles */
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
        }

        body {
            padding: 15px;
            overflow-y: auto;
            overflow-x: hidden;
            box-sizing: border-box;
        }

        .widget {
            max-width: 100%;
            min-height: min-content;
        }

        .widget-bordered.network {
            border-color: #06b6d4;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #06b6d4;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Quality Score Overview */
        .quality-overview {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            display: flex;
            justify-content: space-around;
            align-items: center;
            flex-shrink: 0;
        }

        .quality-metric {
            text-align: center;
        }

        .quality-score {
            font-size: var(--font-size-2xl);
            font-weight: bold;
        }

        .quality-score.excellent {
            color: #22c55e;
        }

        .quality-score.good {
            color: #3b82f6;
        }

        .quality-score.fair {
            color: #eab308;
        }

        .quality-score.poor {
            color: #ef4444;
        }

        .quality-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: var(--space-xs);
        }

        /* Protocol Metrics Grid */
        .protocols-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: var(--space-sm);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .protocol-card {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            border-left: 3px solid transparent;
        }

        .protocol-card.excellent {
            border-left-color: #22c55e;
        }

        .protocol-card.good {
            border-left-color: #3b82f6;
        }

        .protocol-card.fair {
            border-left-color: #eab308;
        }

        .protocol-card.poor {
            border-left-color: #ef4444;
        }

        .protocol-name {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }

        .protocol-metric {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }

        .metric-label-small {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        .metric-value-small {
            font-size: var(--font-size-xs);
            font-weight: bold;
            color: var(--text-primary);
        }

        /* DNS Resolvers */
        .dns-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .section-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .resolver-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--space-sm);
            margin-bottom: var(--space-xs);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
        }

        .resolver-name {
            font-size: var(--font-size-sm);
            color: var(--text-primary);
        }

        .resolver-stats {
            display: flex;
            gap: var(--space-md);
        }

        .stat {
            text-align: right;
        }

        .stat-value {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
        }

        .stat-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        /* TCP Statistics */
        .tcp-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .tcp-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: var(--space-sm);
        }

        .tcp-metric {
            text-align: center;
            padding: var(--space-sm);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
        }

        .tcp-value {
            font-size: var(--font-size-lg);
            font-weight: bold;
            color: var(--text-primary);
        }

        .tcp-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            margin-top: var(--space-xs);
        }

        /* Performance Trends */
        .trends-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex: 1;
            min-height: 0;
            overflow-y: auto;
        }

        .trend-item {
            padding: var(--space-sm);
            margin-bottom: var(--space-xs);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
        }

        .trend-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: var(--space-xs);
        }

        .trend-name {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
        }

        .trend-value {
            font-size: var(--font-size-sm);
            font-weight: bold;
        }

        .trend-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }

        .trend-fill {
            height: 100%;
            transition: width 0.3s ease;
        }

        .trend-fill.excellent {
            background: #22c55e;
        }

        .trend-fill.good {
            background: #3b82f6;
        }

        .trend-fill.fair {
            background: #eab308;
        }

        .trend-fill.poor {
            background: #ef4444;
        }

        .no-data {
            text-align: center;
            color: var(--text-muted);
            padding: var(--space-lg);
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .protocols-grid {
                grid-template-columns: 1fr;
            }

            .quality-overview {
                flex-direction: column;
                gap: var(--space-md);
            }

            .resolver-stats {
                flex-direction: column;
                gap: var(--space-xs);
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered network" role="main" aria-label="Network Quality">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">Network Quality</h1>
        </header>

        <!-- Quality Score Overview -->
        <section class="quality-overview" aria-label="Quality Overview">
            <div class="quality-metric">
                <div id="overallScore" class="quality-score excellent">--</div>
                <div class="quality-label">Overall Quality</div>
            </div>
            <div class="quality-metric">
                <div id="tcpHealth" class="quality-score">--</div>
                <div class="quality-label">TCP Health</div>
            </div>
            <div class="quality-metric">
                <div id="dnsHealth" class="quality-score">--</div>
                <div class="quality-label">DNS Health</div>
            </div>
        </section>

        <!-- Protocol Metrics -->
        <section aria-label="Protocol Metrics">
            <div id="protocolsGrid" class="protocols-grid"></div>
        </section>

        <!-- DNS Resolvers -->
        <section class="dns-section" aria-label="DNS Resolvers">
            <h2 class="section-title">DNS Resolver Performance</h2>
            <div id="resolversList"></div>
        </section>

        <!-- TCP Statistics -->
        <section class="tcp-section" aria-label="TCP Statistics">
            <h2 class="section-title">TCP Statistics</h2>
            <div id="tcpMetrics" class="tcp-metrics"></div>
        </section>

        <!-- Performance Trends -->
        <section class="trends-section" aria-label="Performance Trends">
            <h2 class="section-title">Recent Performance</h2>
            <div id="trendsList"></div>
        </section>
    </main>

    <script>
'''

    widget_script = '''
        async function update() {
            try {
                const result = await apiFetch('/api/network/quality');
                if (!result.ok) {
                    console.error('Network quality fetch failed:', result.error);
                    ToastManager.error('Failed to update network quality data');
                    return;
                }
                const data = result.data;

                // Update overall scores
                updateOverallScores(data);

                // Update protocol metrics
                updateProtocols(data);

                // Update DNS resolvers
                updateDNSResolvers(data.dns || {});

                // Update TCP statistics
                updateTCPStats(data.tcp || {});

                // Update trends
                updateTrends(data);

            } catch (e) {
                console.error('Network quality widget update failed:', e);
                ToastManager.error('Failed to update network quality data');
            }
        }

        function updateOverallScores(data) {
            // Overall quality score (0-100)
            const overallEl = document.getElementById('overallScore');
            const score = calculateOverallScore(data);
            overallEl.textContent = score + '%';
            overallEl.className = 'quality-score ' + getQualityClass(score);

            // TCP health
            const tcpEl = document.getElementById('tcpHealth');
            const tcpScore = data.tcp?.avg_retransmit_rate_percent || 0;
            const tcpHealth = Math.max(0, 100 - (tcpScore * 100));
            tcpEl.textContent = Math.round(tcpHealth) + '%';
            tcpEl.className = 'quality-score ' + getQualityClass(tcpHealth);

            // DNS health
            const dnsEl = document.getElementById('dnsHealth');
            const dnsAvail = data.dns?.availability_percent || 0;
            dnsEl.textContent = dnsAvail.toFixed(1) + '%';
            dnsEl.className = 'quality-score ' + getQualityClass(dnsAvail);
        }

        function updateProtocols(data) {
            const grid = document.getElementById('protocolsGrid');

            const protocols = [
                {
                    name: 'DNS',
                    metrics: {
                        'Availability': (data.dns?.availability_percent || 0).toFixed(1) + '%',
                        'Avg Latency': Math.round(data.dns?.avg_query_time_ms || 0) + 'ms',
                        'Max Latency': Math.round(data.dns?.max_query_time_ms || 0) + 'ms'
                    },
                    quality: getQualityClass(data.dns?.availability_percent || 0)
                },
                {
                    name: 'TLS',
                    metrics: {
                        'Success Rate': (data.tls?.success_rate_percent || 0).toFixed(1) + '%',
                        'Avg Handshake': Math.round(data.tls?.avg_handshake_time_ms || 0) + 'ms',
                        'Max Handshake': Math.round(data.tls?.max_handshake_time_ms || 0) + 'ms'
                    },
                    quality: getQualityClass(data.tls?.success_rate_percent || 0)
                },
                {
                    name: 'HTTP',
                    metrics: {
                        'Success Rate': (data.http?.success_rate_percent || 0).toFixed(1) + '%',
                        'Avg Response': Math.round(data.http?.avg_response_time_ms || 0) + 'ms',
                        'Max Response': Math.round(data.http?.max_response_time_ms || 0) + 'ms'
                    },
                    quality: getQualityClass(data.http?.success_rate_percent || 0)
                },
                {
                    name: 'TCP',
                    metrics: {
                        'Retransmit Rate': (data.tcp?.avg_retransmit_rate_percent || 0).toFixed(2) + '%',
                        'Max Rate': (data.tcp?.max_retransmit_rate_percent || 0).toFixed(2) + '%',
                        'Samples': data.tcp?.sample_count || 0
                    },
                    quality: getQualityClass(100 - (data.tcp?.avg_retransmit_rate_percent || 0) * 100)
                }
            ];

            grid.innerHTML = protocols.map(proto => `
                <div class="protocol-card ${proto.quality}">
                    <div class="protocol-name">${proto.name}</div>
                    ${Object.entries(proto.metrics).map(([label, value]) => `
                        <div class="protocol-metric">
                            <span class="metric-label-small">${label}:</span>
                            <span class="metric-value-small">${value}</span>
                        </div>
                    `).join('')}
                </div>
            `).join('');
        }

        function updateDNSResolvers(dnsData) {
            const list = document.getElementById('resolversList');
            const resolvers = dnsData.resolvers || [];

            if (resolvers.length === 0) {
                list.innerHTML = '<div class="no-data">No DNS resolver data available yet</div>';
                return;
            }

            list.innerHTML = resolvers.map(resolver => `
                <div class="resolver-item">
                    <span class="resolver-name">${resolver.name}</span>
                    <div class="resolver-stats">
                        <div class="stat">
                            <div class="stat-value">${resolver.latency}ms</div>
                            <div class="stat-label">Latency</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">${resolver.availability}%</div>
                            <div class="stat-label">Uptime</div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function updateTCPStats(tcpData) {
            const metricsDiv = document.getElementById('tcpMetrics');

            const metrics = [
                { label: 'Retransmit Rate', value: (tcpData.avg_retransmit_rate_percent || 0).toFixed(4) + '%' },
                { label: 'Max Retransmit', value: (tcpData.max_retransmit_rate_percent || 0).toFixed(4) + '%' },
                { label: 'Samples', value: tcpData.sample_count || 0 }
            ];

            metricsDiv.innerHTML = metrics.map(metric => `
                <div class="tcp-metric">
                    <div class="tcp-value">${metric.value}</div>
                    <div class="tcp-label">${metric.label}</div>
                </div>
            `).join('');
        }

        function updateTrends(data) {
            const list = document.getElementById('trendsList');

            const trends = [
                {
                    name: 'DNS Query Time',
                    value: Math.round(data.dns?.avg_query_time_ms || 0) + 'ms',
                    percentage: Math.min(100, ((data.dns?.avg_query_time_ms || 0) / THRESHOLDS.TREND_MAX.DNS) * 100),
                    quality: getLatencyQuality(data.dns?.avg_query_time_ms || 0)
                },
                {
                    name: 'TLS Handshake',
                    value: Math.round(data.tls?.avg_handshake_time_ms || 0) + 'ms',
                    percentage: Math.min(100, ((data.tls?.avg_handshake_time_ms || 0) / THRESHOLDS.TREND_MAX.TLS) * 100),
                    quality: getLatencyQuality(data.tls?.avg_handshake_time_ms || 0)
                },
                {
                    name: 'HTTP Response',
                    value: Math.round(data.http?.avg_response_time_ms || 0) + 'ms',
                    percentage: Math.min(100, ((data.http?.avg_response_time_ms || 0) / THRESHOLDS.TREND_MAX.HTTP) * 100),
                    quality: getLatencyQuality(data.http?.avg_response_time_ms || 0)
                }
            ];

            list.innerHTML = trends.map(trend => `
                <div class="trend-item">
                    <div class="trend-header">
                        <span class="trend-name">${trend.name}</span>
                        <span class="trend-value ${trend.quality}">${trend.value}</span>
                    </div>
                    <div class="trend-bar">
                        <div class="trend-fill ${trend.quality}" style="width: ${trend.percentage}%"></div>
                    </div>
                </div>
            `).join('');
        }

        function calculateOverallScore(data) {
            const dnsScore = data.dns?.availability_percent || 0;
            const tlsScore = data.tls?.success_rate_percent || 0;
            const httpScore = data.http?.success_rate_percent || 0;
            const tcpScore = Math.max(0, 100 - (data.tcp?.avg_retransmit_rate_percent || 0) * 100);

            return Math.round((dnsScore + tlsScore + httpScore + tcpScore) / 4);
        }

        function getQualityClass(score) {
            if (score >= THRESHOLDS.QUALITY.EXCELLENT) return 'excellent';
            if (score >= THRESHOLDS.QUALITY.GOOD) return 'good';
            if (score >= THRESHOLDS.QUALITY.FAIR) return 'fair';
            return 'poor';
        }

        function getLatencyQuality(latency) {
            if (latency < THRESHOLDS.LATENCY.EXCELLENT) return 'excellent';
            if (latency < THRESHOLDS.LATENCY.GOOD) return 'good';
            if (latency < THRESHOLDS.LATENCY.FAIR) return 'fair';
            return 'poor';
        }

        // Initial update
        update();

        // Update every 10 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.STANDARD);
'''

    html_end = '''
        window.addEventListener('beforeunload', () => { clearInterval(_ivUpdate); });
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


# Export
__all__ = ['get_network_quality_widget_html']
