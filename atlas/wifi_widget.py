"""
WiFi Connection Quality Widget - DEPRECATED: Use network.monitors.wifi instead

This file provides backward compatibility by re-exporting the refactored WiFiMonitor.
For new code, import directly from: atlas.network.monitors.wifi

Migration completed: December 31, 2025 (Phase 2)
"""
import warnings
import logging

# Re-export refactored monitor
from atlas.network.monitors.wifi import (
    WiFiMonitor,
    get_wifi_monitor,
    NetworkDiagnostics,
    WIFI_LOG_FILE,
    WIFI_EVENTS_FILE,
    NETWORK_DIAG_FILE,
    EXTERNAL_PING_TARGETS,
    DNS_TEST_DOMAINS
)

logger = logging.getLogger(__name__)

# Deprecation warning when importing from old location
warnings.warn(
    "Importing from atlas.wifi_widget is deprecated. "
    "Use atlas.network.monitors.wifi instead.",
    DeprecationWarning,
    stacklevel=2
)

logger.info("WiFi widget loaded (using refactored monitor)")


def get_wifi_widget_html():
    """Generate WiFi widget HTML with modern UX/UI

    Returns HTML widget for WiFi quality monitoring with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Responsive design
    - Semantic HTML structure

    Returns HTML widget for WiFi quality monitoring
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
    <title>WiFi Monitor - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* WiFi Widget Specific Styles */
        body {
            padding: 15px;
            overflow-y: auto;
        }

        .widget {
            max-width: 100%;
        }

        .widget-bordered.wifi {
            border-color: var(--color-wifi);
        }

        .widget-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-md);
            padding-bottom: var(--space-sm);
            border-bottom: 2px solid var(--border-subtle);
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: var(--color-wifi);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .status-badge {
            font-size: var(--font-size-sm);
            padding: var(--space-xs) var(--space-sm);
            border-radius: var(--radius-full);
            font-weight: bold;
        }

        .status-badge.connected {
            background: var(--color-wifi);
            color: var(--text-on-primary);
        }

        .status-badge.disconnected {
            background: var(--color-error);
            color: var(--text-primary);
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--space-sm);
            margin-bottom: var(--space-md);
        }

        .info-item {
            background: var(--bg-elevated);
            padding: var(--space-sm);
            border-radius: var(--radius-md);
            border-left: 3px solid var(--color-wifi);
        }

        .info-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: var(--space-xs);
        }

        .info-value {
            font-size: var(--font-size-lg);
            font-weight: bold;
            color: var(--color-wifi);
        }

        .quality-bar {
            width: 100%;
            height: 25px;
            background: var(--border-subtle);
            border-radius: var(--radius-full);
            overflow: hidden;
            position: relative;
            margin: var(--space-sm) 0;
        }

        .quality-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--color-wifi), #00cc50);
            transition: width var(--transition-slow), background var(--transition-normal);
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-on-primary);
            font-weight: bold;
            font-size: var(--font-size-sm);
        }

        .quality-fill.good {
            background: linear-gradient(90deg, var(--color-wifi), #00cc50);
        }

        .quality-fill.warning {
            background: linear-gradient(90deg, var(--color-warning), #ff8800);
        }

        .quality-fill.error {
            background: linear-gradient(90deg, #ff6400, var(--color-error));
        }

        .diagnosis-panel {
            background: var(--bg-elevated);
            padding: var(--space-md);
            border-radius: var(--radius-md);
            margin-top: var(--space-sm);
            border-left: 3px solid var(--color-warning);
        }

        .diagnosis-title {
            font-size: var(--font-size-sm);
            color: var(--color-warning);
            font-weight: bold;
            margin-bottom: var(--space-xs);
        }

        .diagnosis-text {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            line-height: 1.4;
        }

        .chart-container {
            margin-top: var(--space-md);
            height: 120px;
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-sm);
        }

        .chart-container canvas {
            width: 100%;
            height: 100%;
        }

        .loading {
            text-align: center;
            color: var(--text-secondary);
            padding: var(--space-lg);
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
            .info-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered wifi" role="main" aria-label="WiFi Quality Monitor">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">WiFi Quality</h1>
            <div class="status-badge" id="status" role="status" aria-live="polite">...</div>
        </header>

        <section class="info-grid" aria-label="WiFi Information">
            <div class="info-item">
                <div class="info-label" id="ssid-label">Network</div>
                <div class="info-value" id="ssid" aria-labelledby="ssid-label">--</div>
            </div>
            <div class="info-item">
                <div class="info-label" id="rssi-label">Signal</div>
                <div class="info-value" id="rssi" aria-labelledby="rssi-label">-- dBm</div>
            </div>
            <div class="info-item">
                <div class="info-label" id="quality-label">Quality</div>
                <div class="info-value" id="quality" aria-labelledby="quality-label">--%</div>
            </div>
            <div class="info-item">
                <div class="info-label" id="channel-label">Channel</div>
                <div class="info-value" id="channel" aria-labelledby="channel-label">--</div>
            </div>
        </section>

        <div class="quality-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" aria-label="WiFi quality percentage">
            <div class="quality-fill" id="quality-bar" style="width: 0%">0%</div>
        </div>

        <aside class="diagnosis-panel" id="diagnosis" style="display: none;" role="alert" aria-live="polite">
            <div class="diagnosis-title">Network Diagnosis</div>
            <div class="diagnosis-text" id="diagnosis-text">--</div>
        </aside>

        <section class="chart-container" aria-label="WiFi quality history chart">
            <canvas id="chart" aria-hidden="true"></canvas>
        </section>
    </main>

    <script>
'''

    widget_script = '''
        const canvas = document.getElementById('chart');
        const ctx = canvas.getContext('2d');
        let history = [];

        async function update() {
            try {
                // Fetch WiFi data with validation
                const result = await apiFetch('/api/wifi');

                if (!result.ok) {
                    console.error('WiFi data fetch failed:', result.error);
                    document.getElementById('status').textContent = 'Error';
                    document.getElementById('status').className = 'status-badge error';
                    return;
                }

                const data = result.data;

                // Update status
                const statusEl = document.getElementById('status');
                if (data.status === 'connected') {
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'status-badge connected';
                } else {
                    statusEl.textContent = 'Disconnected';
                    statusEl.className = 'status-badge disconnected';
                }

                // Update info with safe defaults
                document.getElementById('ssid').textContent = data.ssid || '--';
                document.getElementById('rssi').textContent = data.rssi ? `${data.rssi} dBm` : '-- dBm';
                document.getElementById('quality').textContent = data.quality_score ? `${data.quality_score}%` : '--%';
                document.getElementById('channel').textContent = data.channel || '--';

                // Update quality bar
                const qualityScore = Number(data.quality_score) || 0;
                const qualityBar = document.getElementById('quality-bar');
                const qualityBarContainer = qualityBar.parentElement;
                qualityBar.style.width = qualityScore + '%';
                qualityBar.textContent = qualityScore + '%';

                // Update ARIA attributes
                qualityBarContainer.setAttribute('aria-valuenow', qualityScore);

                // Color based on quality with appropriate class
                if (qualityScore >= 70) {
                    qualityBar.className = 'quality-fill good';
                } else if (qualityScore >= 40) {
                    qualityBar.className = 'quality-fill warning';
                } else {
                    qualityBar.className = 'quality-fill error';
                }

                // Fetch diagnosis with validation
                const diagResult = await apiFetch('/api/wifi/diagnosis');

                if (diagResult.ok) {
                    const diagData = diagResult.data;
                    if (diagData.issue_type && diagData.issue_type !== 'none') {
                        document.getElementById('diagnosis').style.display = 'block';
                        document.getElementById('diagnosis-text').textContent = diagData.description || 'Running diagnostics...';
                    } else {
                        document.getElementById('diagnosis').style.display = 'none';
                    }
                }

                // Fetch history for chart with validation
                const histResult = await apiFetch('/api/wifi/history');

                if (histResult.ok && Array.isArray(histResult.data)) {
                    history = histResult.data.slice(-30);
                }

                drawChart();

            } catch (e) {
                console.error('WiFi widget update failed:', e);
                ToastManager.error('Failed to update WiFi data');
            }
        }

        function drawChart() {
            if (history.length === 0) return;

            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw quality line
            ctx.strokeStyle = '#00ff64';
            ctx.lineWidth = 2;
            ctx.beginPath();

            const maxQuality = 100;
            const step = canvas.width / (history.length - 1 || 1);

            history.forEach((point, i) => {
                const x = i * step;
                const y = canvas.height - (point.quality_score / maxQuality) * canvas.height;
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.stroke();

            // Draw baseline at 70% (good quality threshold)
            ctx.strokeStyle = '#666';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            const baselineY = canvas.height - (70 / 100) * canvas.height;
            ctx.moveTo(0, baselineY);
            ctx.lineTo(canvas.width, baselineY);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Initial update
        update();

        // Update every 5 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.FREQUENT);
'''

    html_end = '''
        window.addEventListener('beforeunload', () => { clearInterval(_ivUpdate); });
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


# Export all for backward compatibility
__all__ = [
    'WiFiMonitor',
    'get_wifi_monitor',
    'get_wifi_widget_html',
    'NetworkDiagnostics',
    'WIFI_LOG_FILE',
    'WIFI_EVENTS_FILE',
    'NETWORK_DIAG_FILE',
    'EXTERNAL_PING_TARGETS',
    'DNS_TEST_DOMAINS'
]
