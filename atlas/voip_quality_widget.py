"""
VoIP/Video Quality Widget - Real-time communication quality monitoring

Displays:
- MOS (Mean Opinion Score) for voice quality
- UDP packet loss and jitter metrics
- Quality recommendations
- Historical quality trends
- Codec comparison

Inspired by Keysight CyPerf quality metrics.
"""

import logging

logger = logging.getLogger(__name__)


def get_voip_quality_widget_html():
    """Generate VoIP/Video Quality widget HTML

    Returns HTML widget for VoIP/video quality monitoring with:
    - MOS score gauge
    - UDP metrics (packet loss, jitter, latency)
    - Quality ratings and recommendations
    - Real-time updates
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
    <title>VoIP/Video Quality - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* VoIP Quality Widget Styles */
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

        .widget-bordered.voip {
            border-color: #8b5cf6;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #8b5cf6;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .widget-subtitle {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* MOS Score Gauge */
        .mos-container {
            background: var(--bg-elevated);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            margin-bottom: var(--space-md);
            text-align: center;
        }

        .mos-gauge {
            position: relative;
            width: 180px;
            height: 100px;
            margin: 0 auto 15px;
        }

        .mos-gauge svg {
            width: 100%;
            height: 100%;
        }

        .mos-arc-bg {
            fill: none;
            stroke: var(--bg-card);
            stroke-width: 20;
        }

        .mos-arc-fill {
            fill: none;
            stroke-width: 20;
            stroke-linecap: round;
            transition: stroke-dashoffset 0.5s ease, stroke 0.3s ease;
        }

        .mos-value {
            font-size: 48px;
            font-weight: bold;
            color: var(--text-primary);
        }

        .mos-rating {
            font-size: var(--font-size-lg);
            font-weight: 600;
            margin-top: 5px;
            text-transform: uppercase;
        }

        .mos-rating.excellent { color: #22c55e; }
        .mos-rating.good { color: #3b82f6; }
        .mos-rating.fair { color: #eab308; }
        .mos-rating.poor { color: #f97316; }
        .mos-rating.bad { color: #ef4444; }

        .mos-scale {
            display: flex;
            justify-content: space-between;
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            margin-top: 10px;
        }

        /* UDP Metrics Grid */
        .udp-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: var(--space-sm);
            margin-bottom: var(--space-md);
        }

        .metric-card {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            text-align: center;
            border-left: 3px solid transparent;
        }

        .metric-card.excellent { border-left-color: #22c55e; }
        .metric-card.good { border-left-color: #3b82f6; }
        .metric-card.fair { border-left-color: #eab308; }
        .metric-card.poor { border-left-color: #ef4444; }

        .metric-value {
            font-size: var(--font-size-2xl);
            font-weight: bold;
            color: var(--text-primary);
        }

        .metric-unit {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
        }

        .metric-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: 5px;
        }

        /* Quality Indicators */
        .quality-indicators {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .indicator-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-subtle);
        }

        .indicator-row:last-child {
            border-bottom: none;
        }

        .indicator-label {
            color: var(--text-secondary);
            font-size: var(--font-size-sm);
        }

        .indicator-value {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .indicator-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        .indicator-dot.excellent { background: #22c55e; }
        .indicator-dot.good { background: #3b82f6; }
        .indicator-dot.fair { background: #eab308; }
        .indicator-dot.poor { background: #ef4444; }

        /* Recommendations */
        .recommendations {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
        }

        .recommendations-title {
            font-size: var(--font-size-md);
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
        }

        .recommendation-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 8px 0;
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
        }

        .recommendation-icon {
            font-size: 16px;
        }

        /* Test Controls */
        .test-controls {
            display: flex;
            gap: var(--space-sm);
            margin-bottom: var(--space-md);
        }

        .test-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: var(--radius-md);
            font-size: var(--font-size-sm);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .test-btn.primary {
            background: linear-gradient(135deg, #8b5cf6, #6366f1);
            color: white;
        }

        .test-btn.primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        }

        .test-btn.secondary {
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border-subtle);
        }

        .test-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }

        /* Status indicator */
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            padding-top: var(--space-sm);
            border-top: 1px solid var(--border-subtle);
            margin-top: auto;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
'''

    html_body = '''
    </style>
</head>
<body>
    <div class="widget widget-bordered voip">
        <div class="widget-header">
            <div class="widget-title">🎙️ VoIP/Video Quality</div>
            <div class="widget-subtitle">Real-time communication quality assessment</div>
        </div>

        <div id="content">
            <div class="loading">
                <div class="spinner"></div>
                <div>Measuring network quality...</div>
            </div>
        </div>
    </div>

    <script>
        // MOS color mapping
        function getMOSColor(mos) {
            if (mos >= 4.3) return '#22c55e';
            if (mos >= 4.0) return '#3b82f6';
            if (mos >= 3.6) return '#eab308';
            if (mos >= 3.1) return '#f97316';
            return '#ef4444';
        }

        function getMOSRating(mos) {
            if (mos >= 4.3) return 'excellent';
            if (mos >= 4.0) return 'good';
            if (mos >= 3.6) return 'fair';
            if (mos >= 3.1) return 'poor';
            return 'bad';
        }

        function getMetricRating(metric, value) {
            if (metric === 'jitter') {
                if (value < 10) return 'excellent';
                if (value < 20) return 'good';
                if (value < 50) return 'fair';
                return 'poor';
            }
            if (metric === 'packet_loss') {
                if (value < 0.1) return 'excellent';
                if (value < 1) return 'good';
                if (value < 3) return 'fair';
                return 'poor';
            }
            if (metric === 'latency') {
                if (value < 50) return 'excellent';
                if (value < 100) return 'good';
                if (value < 200) return 'fair';
                return 'poor';
            }
            return 'good';
        }

        // Create MOS gauge SVG
        function createMOSGauge(mos) {
            const maxMOS = 5.0;
            const minMOS = 1.0;
            const normalizedMOS = (mos - minMOS) / (maxMOS - minMOS);
            const arcLength = 251.2; // Circumference of half circle (r=80)
            const offset = arcLength * (1 - normalizedMOS);
            const color = getMOSColor(mos);

            return `
                <svg viewBox="0 0 200 110">
                    <path class="mos-arc-bg" d="M 20 100 A 80 80 0 0 1 180 100" />
                    <path class="mos-arc-fill" d="M 20 100 A 80 80 0 0 1 180 100"
                        stroke="${color}"
                        stroke-dasharray="${arcLength}"
                        stroke-dashoffset="${offset}" />
                </svg>
            `;
        }

        // Get machine ID for fleet reporting
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
        async function reportToFleet(metrics, testType) {
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
                        test_type: testType,
                        metrics: metrics
                    })
                });

                if (result.ok) {
                    console.log(`${testType} metrics reported to fleet server`);
                } else {
                    console.log(`Failed to report ${testType} metrics:`, result.error);
                }
            } catch (e) {
                console.log('Error reporting to fleet:', e);
            }
        }

        async function fetchQualityData() {
            try {
                // Fetch ping data for latency
                const pingResult = await apiFetch('/api/ping');
                if (!pingResult.ok) {
                    throw new Error(pingResult.error || 'Failed to fetch ping data');
                }
                const pingData = pingResult.data;

                // Fetch UDP quality if available
                let udpData = { jitter_ms: 0, packet_loss_percent: 0 };
                try {
                    const udpResult = await apiFetch('/api/network/udp-quality');
                    if (udpResult.ok) {
                        udpData = udpResult.data;
                    }
                } catch (e) {
                    console.log('UDP quality endpoint not available');
                }

                // Calculate MOS based on available metrics
                const latency = pingData.latency || 0;
                const jitter = udpData.jitter_ms || (pingData.jitter || 0);
                const packetLoss = udpData.packet_loss_percent || 0;

                // Simple MOS estimation (E-model simplified)
                let r = 93.2;
                r -= latency * 0.024;
                r -= jitter * 0.25;
                r -= packetLoss * 4.5;
                r = Math.max(0, Math.min(100, r));

                // Convert R to MOS
                let mos;
                if (r <= 0) mos = 1.0;
                else if (r >= 100) mos = 4.5;
                else mos = 1 + 0.035 * r + r * (r - 60) * (100 - r) * 7e-6;
                mos = Math.max(1.0, Math.min(5.0, mos));

                const result = {
                    mos: mos.toFixed(2),
                    latency: latency.toFixed(1),
                    jitter: jitter.toFixed(1),
                    packetLoss: packetLoss.toFixed(2),
                    lastUpdate: new Date().toLocaleTimeString()
                };

                // Report MOS metrics to fleet server
                reportToFleet({
                    mos_score: parseFloat(result.mos),
                    latency_ms: parseFloat(result.latency),
                    jitter_ms: parseFloat(result.jitter),
                    packet_loss_percent: parseFloat(result.packetLoss),
                    rating: getMOSRating(parseFloat(result.mos))
                }, 'mos');

                // Report UDP quality metrics separately
                if (udpData.jitter_ms > 0 || udpData.packet_loss_percent > 0) {
                    reportToFleet({
                        jitter_ms: udpData.jitter_ms || 0,
                        packet_loss_percent: udpData.packet_loss_percent || 0,
                        latency_ms: latency,
                        quality_score: Math.max(0, 100 - (packetLoss * 10) - (jitter * 2))
                    }, 'udp_quality');
                }

                return result;
            } catch (error) {
                console.error('Error fetching quality data:', error);
                return null;
            }
        }

        // Initialize machine info on load
        getMachineInfo();

        function generateRecommendations(data) {
            const recommendations = [];
            const mos = parseFloat(data.mos);
            const latency = parseFloat(data.latency);
            const jitter = parseFloat(data.jitter);
            const packetLoss = parseFloat(data.packetLoss);

            if (mos >= 4.0) {
                recommendations.push({ icon: '✅', text: 'Network quality is excellent for voice/video calls' });
            }

            if (latency > 150) {
                recommendations.push({ icon: '🔴', text: `High latency (${latency}ms) - Consider closer servers or better routing` });
            } else if (latency > 100) {
                recommendations.push({ icon: '🟡', text: `Moderate latency (${latency}ms) - Acceptable but could be improved` });
            }

            if (jitter > 30) {
                recommendations.push({ icon: '🔴', text: `High jitter (${jitter}ms) - Network congestion or QoS issues likely` });
            } else if (jitter > 15) {
                recommendations.push({ icon: '🟡', text: `Moderate jitter (${jitter}ms) - Consider traffic prioritization` });
            }

            if (packetLoss > 3) {
                recommendations.push({ icon: '🔴', text: `High packet loss (${packetLoss}%) - Check network for errors` });
            } else if (packetLoss > 1) {
                recommendations.push({ icon: '🟡', text: `Some packet loss (${packetLoss}%) - May affect call quality` });
            }

            if (recommendations.length === 0) {
                recommendations.push({ icon: '✅', text: 'All metrics are within acceptable ranges' });
            }

            return recommendations;
        }

        function renderContent(data) {
            if (!data) {
                document.getElementById('content').innerHTML = `
                    <div class="loading">
                        <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                        <div>Unable to fetch quality data</div>
                    </div>
                `;
                return;
            }

            const rating = getMOSRating(parseFloat(data.mos));
            const recommendations = generateRecommendations(data);

            document.getElementById('content').innerHTML = `
                <!-- MOS Score -->
                <div class="mos-container">
                    <div class="mos-gauge">
                        ${createMOSGauge(parseFloat(data.mos))}
                    </div>
                    <div class="mos-value">${data.mos}</div>
                    <div class="mos-rating ${rating}">${rating}</div>
                    <div class="mos-scale">
                        <span>1.0 Bad</span>
                        <span>2.6 Poor</span>
                        <span>3.6 Fair</span>
                        <span>4.3 Excellent</span>
                    </div>
                </div>

                <!-- UDP Metrics -->
                <div class="udp-metrics">
                    <div class="metric-card ${getMetricRating('latency', parseFloat(data.latency))}">
                        <div class="metric-value">${data.latency}<span class="metric-unit">ms</span></div>
                        <div class="metric-label">Latency</div>
                    </div>
                    <div class="metric-card ${getMetricRating('jitter', parseFloat(data.jitter))}">
                        <div class="metric-value">${data.jitter}<span class="metric-unit">ms</span></div>
                        <div class="metric-label">Jitter</div>
                    </div>
                    <div class="metric-card ${getMetricRating('packet_loss', parseFloat(data.packetLoss))}">
                        <div class="metric-value">${data.packetLoss}<span class="metric-unit">%</span></div>
                        <div class="metric-label">Packet Loss</div>
                    </div>
                </div>

                <!-- Quality Indicators -->
                <div class="quality-indicators">
                    <div class="indicator-row">
                        <span class="indicator-label">Voice Calls</span>
                        <div class="indicator-value">
                            <span class="indicator-dot ${parseFloat(data.mos) >= 3.6 ? 'excellent' : parseFloat(data.mos) >= 3.1 ? 'fair' : 'poor'}"></span>
                            <span>${parseFloat(data.mos) >= 3.6 ? 'Supported' : parseFloat(data.mos) >= 3.1 ? 'May have issues' : 'Not recommended'}</span>
                        </div>
                    </div>
                    <div class="indicator-row">
                        <span class="indicator-label">Video Conferencing</span>
                        <div class="indicator-value">
                            <span class="indicator-dot ${parseFloat(data.mos) >= 4.0 ? 'excellent' : parseFloat(data.mos) >= 3.6 ? 'fair' : 'poor'}"></span>
                            <span>${parseFloat(data.mos) >= 4.0 ? 'HD Quality' : parseFloat(data.mos) >= 3.6 ? 'SD Quality' : 'Degraded'}</span>
                        </div>
                    </div>
                    <div class="indicator-row">
                        <span class="indicator-label">Screen Sharing</span>
                        <div class="indicator-value">
                            <span class="indicator-dot ${parseFloat(data.latency) < 100 ? 'excellent' : parseFloat(data.latency) < 200 ? 'fair' : 'poor'}"></span>
                            <span>${parseFloat(data.latency) < 100 ? 'Smooth' : parseFloat(data.latency) < 200 ? 'Acceptable' : 'Laggy'}</span>
                        </div>
                    </div>
                </div>

                <!-- Recommendations -->
                <div class="recommendations">
                    <div class="recommendations-title">Recommendations</div>
                    ${recommendations.map(r => `
                        <div class="recommendation-item">
                            <span class="recommendation-icon">${r.icon}</span>
                            <span>${r.text}</span>
                        </div>
                    `).join('')}
                </div>

                <!-- Status Bar -->
                <div class="status-bar">
                    <div class="status-indicator">
                        <span class="status-dot"></span>
                        <span>Monitoring Active</span>
                    </div>
                    <span>Last update: ${data.lastUpdate}</span>
                </div>
            `;
        }

        // Initial load
        fetchQualityData().then(renderContent);

        // Refresh every 10 seconds
        const _ivUpdate = setInterval(() => {
            fetchQualityData().then(renderContent);
        }, UPDATE_INTERVAL.STANDARD);

        // Cleanup intervals on page unload
        window.addEventListener('beforeunload', () => {
            clearInterval(_ivUpdate);
        });
    </script>
'''

    return html_start + base_styles + widget_styles + html_body + '\n<script>\n' + api_helpers + '\n' + toast_script + '\n</script>\n</body>\n</html>'
