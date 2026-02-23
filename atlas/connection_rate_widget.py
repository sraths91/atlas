"""
TCP Connection Rate Widget - Network capacity testing

Displays:
- Connections per second (CPS)
- Connection success rate
- Connection latency distribution
- P95 latency metrics
- Historical CPS trends

Inspired by Keysight CyPerf connection rate testing.
"""

import logging

logger = logging.getLogger(__name__)


def get_connection_rate_widget_html():
    """Generate TCP Connection Rate widget HTML

    Returns HTML widget for connection rate testing with:
    - CPS (connections per second) gauge
    - Success rate metrics
    - Latency distribution
    - Test controls
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
    <title>Connection Rate Test - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* Connection Rate Widget Styles */
        body {
            padding: 15px;
            overflow-y: auto;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .widget {
            max-width: 100%;
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }

        .widget-bordered.connection {
            border-color: #f59e0b;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #f59e0b;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .widget-subtitle {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* CPS Display */
        .cps-container {
            background: var(--bg-elevated);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            margin-bottom: var(--space-md);
            text-align: center;
        }

        .cps-value {
            font-size: 64px;
            font-weight: bold;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .cps-unit {
            font-size: var(--font-size-lg);
            color: var(--text-secondary);
            margin-top: 5px;
        }

        .cps-rating {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: var(--font-size-sm);
            font-weight: 600;
            margin-top: 10px;
        }

        .cps-rating.excellent { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
        .cps-rating.good { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
        .cps-rating.acceptable { background: rgba(234, 179, 8, 0.2); color: #eab308; }
        .cps-rating.poor { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--space-sm);
            margin-bottom: var(--space-md);
        }

        .metric-card {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            text-align: center;
        }

        .metric-value {
            font-size: var(--font-size-2xl);
            font-weight: bold;
            color: var(--text-primary);
        }

        .metric-value.success { color: #22c55e; }
        .metric-value.warning { color: #eab308; }
        .metric-value.error { color: #ef4444; }

        .metric-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: 5px;
        }

        /* Latency Distribution */
        .latency-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .section-title {
            font-size: var(--font-size-md);
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
        }

        .latency-bars {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .latency-row {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .latency-label {
            width: 60px;
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
        }

        .latency-bar {
            flex: 1;
            height: 24px;
            background: var(--bg-card);
            border-radius: 4px;
            overflow: hidden;
        }

        .latency-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }

        .latency-fill.avg { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
        .latency-fill.min { background: linear-gradient(90deg, #22c55e, #4ade80); }
        .latency-fill.max { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .latency-fill.p95 { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }

        .latency-value {
            width: 70px;
            font-size: var(--font-size-sm);
            color: var(--text-primary);
            text-align: right;
        }

        /* Test Controls */
        .test-controls {
            display: flex;
            gap: var(--space-sm);
            margin-bottom: var(--space-md);
        }

        .test-btn {
            flex: 1;
            padding: 14px;
            border: none;
            border-radius: var(--radius-md);
            font-size: var(--font-size-sm);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .test-btn.primary {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
        }

        .test-btn.primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
        }

        .test-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }

        .test-btn .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
        }

        /* Test History */
        .history-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            flex: 1;
            min-height: 0;
            display: flex;
            flex-direction: column;
        }

        .history-list {
            flex: 1;
            overflow-y: auto;
        }

        .history-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border-subtle);
        }

        .history-item:last-child {
            border-bottom: none;
        }

        .history-time {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
        }

        .history-cps {
            font-size: var(--font-size-md);
            font-weight: 600;
            color: #f59e0b;
        }

        .history-success {
            font-size: var(--font-size-sm);
            padding: 4px 8px;
            border-radius: 4px;
            background: var(--bg-card);
        }

        /* Status */
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            padding-top: var(--space-sm);
            border-top: 1px solid var(--border-subtle);
            margin-top: var(--space-sm);
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }

        .loading .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--border-subtle);
            border-top-color: #f59e0b;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
'''

    html_body = '''
    </style>
</head>
<body>
    <div class="widget widget-bordered connection">
        <div class="widget-header">
            <div class="widget-title">🔌 Connection Rate Test</div>
            <div class="widget-subtitle">TCP connection establishment capacity</div>
        </div>

        <div id="content">
            <div class="loading">
                <div class="spinner"></div>
                <div>Ready to test connection rate</div>
            </div>
        </div>
    </div>

    <script>
        let testHistory = [];
        let isRunning = false;
        let lastResult = null;

        // Fleet reporting variables
        let machineId = null;
        let fleetServerUrl = null;

        async function getMachineInfo() {
            try {
                const result = await apiFetch('/api/agent/health');
                if (!result.ok) {
                    console.log('Could not get machine info:', result.error);
                    return { machineId: 'unknown', fleetServerUrl: null };
                }
                const data = result.data;
                machineId = data.machine_id || data.serial_number || 'unknown';
                fleetServerUrl = data.fleet_server_url;
                return { machineId, fleetServerUrl };
            } catch (e) {
                console.log('Could not get machine info:', e);
                return { machineId: 'unknown', fleetServerUrl: null };
            }
        }

        // Report metrics to fleet server
        async function reportToFleet(metrics) {
            if (!fleetServerUrl || !machineId) {
                await getMachineInfo();
            }

            if (!fleetServerUrl) {
                console.log('No fleet server configured, skipping metric report');
                return;
            }

            try {
                const result = await apiFetch(`${fleetServerUrl}/api/fleet/network-test/metrics`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        machine_id: machineId,
                        test_type: 'connection_rate',
                        metrics: metrics
                    })
                });

                if (result.ok) {
                    console.log('Connection rate metrics reported to fleet server');
                } else {
                    console.log('Failed to report connection rate metrics:', result.error);
                }
            } catch (e) {
                console.log('Error reporting to fleet:', e);
            }
        }

        // Initialize machine info on load
        getMachineInfo();

        function getCPSRating(cps) {
            if (cps >= 10) return 'excellent';
            if (cps >= 5) return 'good';
            if (cps >= 2) return 'acceptable';
            return 'poor';
        }

        function getSuccessClass(rate) {
            if (rate >= 95) return 'success';
            if (rate >= 80) return 'warning';
            return 'error';
        }

        async function runConnectionTest() {
            if (isRunning) return;

            isRunning = true;
            renderContent();

            try {
                const result = await apiFetch('/api/network/connection-test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ connections: 20, timeout: 5 })
                });

                if (result.ok) {
                    lastResult = result.data;
                    testHistory.unshift({
                        time: new Date().toLocaleTimeString(),
                        cps: lastResult.connections_per_second,
                        success: lastResult.success_rate_percent
                    });
                    if (testHistory.length > 5) testHistory.pop();

                    // Report to fleet server
                    reportToFleet({
                        cps: lastResult.connections_per_second,
                        success_rate_percent: lastResult.success_rate_percent,
                        total_connections: lastResult.total_connections,
                        successful_connections: lastResult.successful_connections,
                        avg_connect_time_ms: lastResult.avg_connect_time_ms,
                        min_connect_time_ms: lastResult.min_connect_time_ms,
                        max_connect_time_ms: lastResult.max_connect_time_ms,
                        p95_connect_time_ms: lastResult.p95_connect_time_ms,
                        test_duration_seconds: lastResult.test_duration_seconds,
                        rating: getCPSRating(lastResult.connections_per_second)
                    });
                }
            } catch (error) {
                console.error('Connection test error:', error);
            }

            isRunning = false;
            renderContent();
        }

        function renderContent() {
            const content = document.getElementById('content');

            if (!lastResult && !isRunning) {
                content.innerHTML = `
                    <div class="test-controls">
                        <button class="test-btn primary" onclick="runConnectionTest()">
                            <span>▶</span>
                            <span>Run Connection Test</span>
                        </button>
                    </div>

                    <div class="cps-container">
                        <div class="cps-value">--</div>
                        <div class="cps-unit">connections per second</div>
                    </div>

                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">--</div>
                            <div class="metric-label">Success Rate</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">--</div>
                            <div class="metric-label">Avg Latency</div>
                        </div>
                    </div>

                    <div class="status-bar">
                        <span>Click "Run Connection Test" to begin</span>
                    </div>
                `;
                return;
            }

            if (isRunning) {
                content.innerHTML = `
                    <div class="test-controls">
                        <button class="test-btn primary" disabled>
                            <span class="spinner"></span>
                            <span>Testing...</span>
                        </button>
                    </div>

                    <div class="cps-container">
                        <div class="cps-value">...</div>
                        <div class="cps-unit">measuring connection rate</div>
                    </div>

                    <div class="loading">
                        <div>Establishing connections to test endpoints...</div>
                    </div>
                `;
                return;
            }

            const data = lastResult;
            const rating = getCPSRating(data.connections_per_second);
            const successClass = getSuccessClass(data.success_rate_percent);
            const maxLatency = Math.max(data.max_connect_time_ms || 100, 100);

            content.innerHTML = `
                <div class="test-controls">
                    <button class="test-btn primary" onclick="runConnectionTest()">
                        <span>🔄</span>
                        <span>Run Again</span>
                    </button>
                </div>

                <!-- CPS Display -->
                <div class="cps-container">
                    <div class="cps-value">${data.connections_per_second.toFixed(1)}</div>
                    <div class="cps-unit">connections per second</div>
                    <span class="cps-rating ${rating}">${rating.toUpperCase()}</span>
                </div>

                <!-- Metrics Grid -->
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value ${successClass}">${data.success_rate_percent.toFixed(1)}%</div>
                        <div class="metric-label">Success Rate (${data.successful_connections}/${data.total_connections})</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${data.avg_connect_time_ms.toFixed(0)}ms</div>
                        <div class="metric-label">Avg Connect Time</div>
                    </div>
                </div>

                <!-- Latency Distribution -->
                <div class="latency-section">
                    <div class="section-title">Latency Distribution</div>
                    <div class="latency-bars">
                        <div class="latency-row">
                            <span class="latency-label">Min</span>
                            <div class="latency-bar">
                                <div class="latency-fill min" style="width: ${(data.min_connect_time_ms / maxLatency) * 100}%"></div>
                            </div>
                            <span class="latency-value">${data.min_connect_time_ms.toFixed(0)} ms</span>
                        </div>
                        <div class="latency-row">
                            <span class="latency-label">Avg</span>
                            <div class="latency-bar">
                                <div class="latency-fill avg" style="width: ${(data.avg_connect_time_ms / maxLatency) * 100}%"></div>
                            </div>
                            <span class="latency-value">${data.avg_connect_time_ms.toFixed(0)} ms</span>
                        </div>
                        <div class="latency-row">
                            <span class="latency-label">P95</span>
                            <div class="latency-bar">
                                <div class="latency-fill p95" style="width: ${(data.p95_connect_time_ms / maxLatency) * 100}%"></div>
                            </div>
                            <span class="latency-value">${data.p95_connect_time_ms.toFixed(0)} ms</span>
                        </div>
                        <div class="latency-row">
                            <span class="latency-label">Max</span>
                            <div class="latency-bar">
                                <div class="latency-fill max" style="width: ${(data.max_connect_time_ms / maxLatency) * 100}%"></div>
                            </div>
                            <span class="latency-value">${data.max_connect_time_ms.toFixed(0)} ms</span>
                        </div>
                    </div>
                </div>

                ${testHistory.length > 1 ? `
                <!-- Test History -->
                <div class="history-section">
                    <div class="section-title">Recent Tests</div>
                    <div class="history-list">
                        ${testHistory.map(h => `
                            <div class="history-item">
                                <span class="history-time">${h.time}</span>
                                <span class="history-cps">${h.cps.toFixed(1)} CPS</span>
                                <span class="history-success">${h.success.toFixed(0)}%</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}

                <div class="status-bar">
                    <span>Test Duration: ${data.test_duration_seconds?.toFixed(1) || '--'}s</span>
                    <span>Last: ${new Date().toLocaleTimeString()}</span>
                </div>
            `;
        }

        // Initial render
        renderContent();
    </script>
'''

    return html_start + base_styles + widget_styles + html_body + '\n<script>\n' + api_helpers + '\n' + toast_script + '\n</script>\n</body>\n</html>'
