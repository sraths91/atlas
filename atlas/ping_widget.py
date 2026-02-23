"""
Ping Monitor Widget - HTML widgets for ping monitoring

Monitor classes re-exported from atlas.network.monitors.ping for
backward compatibility. New code should import from there directly.
"""
import logging

# Re-export refactored monitor for backward compatibility
from atlas.network.monitors.ping import (
    PingMonitor,
    get_ping_monitor,
    PING_LOG_FILE
)

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get local IP address

    Returns:
        Local IP address or 'localhost' if unable to determine
    """
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except (OSError, socket.error):
        return 'localhost'


def get_ping_widget_html():
    """Generate Ping widget HTML with modern UX/UI

    Returns HTML widget for ping monitoring with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Responsive design
    - Semantic HTML structure

    Returns HTML widget for ping monitoring with statistics
    """
    # Import shared styles
    from atlas.agent_widget_styles import (
        get_widget_base_styles,
        get_widget_toast_script,
        get_widget_api_helpers_script,
        get_css_var_reader_script
    )

    base_styles = get_widget_base_styles()
    toast_script = get_widget_toast_script()
    api_helpers = get_widget_api_helpers_script()
    css_var_reader = get_css_var_reader_script()

    html_start = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ping Monitor - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* Ping Widget Specific Styles */
        body {
            padding: 15px;
            overflow-y: auto;
        }

        .widget {
            max-width: 100%;
        }

        .widget-bordered.ping {
            border-color: var(--color-ping);
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
            color: var(--color-ping);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .status-badge {
            font-size: var(--font-size-sm);
            padding: var(--space-xs) var(--space-sm);
            border-radius: var(--radius-full);
            font-weight: bold;
        }

        .status-badge.success {
            background: var(--color-success);
            color: var(--text-on-primary);
        }

        .status-badge.timeout {
            background: var(--color-error);
            color: var(--text-primary);
        }

        .status-badge.network-lost {
            background: #ff0080;
            color: var(--text-primary);
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .latency-display {
            text-align: center;
            margin: var(--space-lg) 0;
        }

        .latency-value {
            font-size: 48px;
            font-weight: bold;
            color: var(--color-ping);
        }

        .latency-unit {
            font-size: var(--font-size-xl);
            color: var(--text-muted);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--space-sm);
            margin: var(--space-md) 0;
        }

        .stat-item {
            background: var(--bg-elevated);
            padding: var(--space-sm);
            border-radius: var(--radius-md);
            border-left: 3px solid var(--color-ping);
        }

        .stat-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: var(--space-xs);
        }

        .stat-value {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--color-ping);
        }

        .chart-container {
            height: 120px;
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-sm);
            margin-top: var(--space-md);
        }

        .chart-container canvas {
            width: 100%;
            height: 100%;
        }

        .target-info {
            text-align: center;
            font-size: var(--font-size-xs);
            color: var(--text-muted);
            margin-top: var(--space-sm);
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
            .latency-value {
                font-size: 36px;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered ping" role="main" aria-label="Ping Monitor">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">Ping Monitor</h1>
            <div class="status-badge" id="status" role="status" aria-live="polite">...</div>
        </header>

        <section class="latency-display" aria-label="Current Latency">
            <div class="latency-value" id="latency" aria-live="polite">--</div>
            <div class="latency-unit">ms</div>
        </section>

        <section class="stats-grid" aria-label="Ping Statistics">
            <div class="stat-item">
                <div class="stat-label" id="avg-label">Average</div>
                <div class="stat-value" id="avg" aria-labelledby="avg-label">-- ms</div>
            </div>
            <div class="stat-item">
                <div class="stat-label" id="minmax-label">Min / Max</div>
                <div class="stat-value" id="minmax" aria-labelledby="minmax-label">-- / -- ms</div>
            </div>
            <div class="stat-item">
                <div class="stat-label" id="success-label">Success Rate</div>
                <div class="stat-value" id="success" aria-labelledby="success-label">--%</div>
            </div>
            <div class="stat-item">
                <div class="stat-label" id="total-label">Total Pings</div>
                <div class="stat-value" id="total" aria-labelledby="total-label">--</div>
            </div>
        </section>

        <section class="chart-container" aria-label="Ping latency history chart">
            <canvas id="chart" aria-hidden="true"></canvas>
        </section>

        <footer class="target-info">Target: <span id="target">8.8.8.8</span></footer>
    </main>

    <script>
'''

    widget_script = '''
        const canvas = document.getElementById('chart');
        const ctx = canvas.getContext('2d');
        let history = [];

        async function update() {
            try {
                // Fetch ping data
                const result = await apiFetch('/api/ping');
                if (!result.ok) {
                    console.error('Ping fetch failed:', result.error);
                    ToastManager.error('Failed to fetch ping data');
                    return;
                }
                const data = result.data;

                // Update status
                const statusEl = document.getElementById('status');
                if (data.network_lost) {
                    statusEl.textContent = 'Network Lost';
                    statusEl.className = 'status-badge network-lost';
                } else if (data.status === 'success') {
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'status-badge success';
                } else if (data.status === 'timeout') {
                    statusEl.textContent = 'Timeout';
                    statusEl.className = 'status-badge timeout';
                } else {
                    statusEl.textContent = 'Unknown';
                    statusEl.className = 'status-badge';
                }

                // Update latency
                document.getElementById('latency').textContent = data.latency ? data.latency.toFixed(1) : '--';

                // Fetch stats
                const statsResult = await apiFetch('/api/ping/stats');
                if (statsResult.ok) {
                    const stats = statsResult.data;
                    document.getElementById('avg').textContent = stats.avg_latency ? stats.avg_latency.toFixed(1) + ' ms' : '-- ms';
                    document.getElementById('minmax').textContent =
                        (stats.min_latency && stats.max_latency)
                        ? `${stats.min_latency.toFixed(1)} / ${stats.max_latency.toFixed(1)} ms`
                        : '-- / -- ms';
                    document.getElementById('success').textContent = stats.success_rate ? stats.success_rate.toFixed(1) + '%' : '--%';
                    document.getElementById('total').textContent = stats.total_pings || '--';
                }

                // Fetch history
                const histResult = await apiFetch('/api/ping/history');
                if (histResult.ok) {
                    const histData = histResult.data;
                    history = histData.slice(-30); // Last 30 pings
                }

                drawChart();

            } catch (e) {
                console.error('Ping widget update failed:', e);
                ToastManager.error('Failed to update ping data');
            }
        }

        function drawChart() {
            if (history.length === 0) return;

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Calculate max latency for scaling (exclude timeouts)
            const validLatencies = history.filter(p => p.status === 'success').map(p => p.latency);
            const maxLatency = Math.max(...validLatencies, 100);
            const step = canvas.width / (history.length - 1 || 1);

            // Draw latency line
            ctx.strokeStyle = cssVar('--color-primary');
            ctx.lineWidth = 2;
            ctx.beginPath();

            let firstPoint = true;
            history.forEach((ping, i) => {
                const x = i * step;

                if (ping.status === 'success') {
                    const y = canvas.height - (ping.latency / maxLatency) * canvas.height;
                    if (firstPoint) {
                        ctx.moveTo(x, y);
                        firstPoint = false;
                    } else {
                        ctx.lineTo(x, y);
                    }
                } else {
                    // Draw timeout markers
                    ctx.save();
                    ctx.fillStyle = '#ff3000';
                    ctx.fillRect(x - 2, 0, 4, canvas.height);
                    ctx.restore();
                    firstPoint = true;
                }
            });

            ctx.stroke();

            // Draw baseline (average)
            if (validLatencies.length > 0) {
                const avgLatency = validLatencies.reduce((a, b) => a + b, 0) / validLatencies.length;
                const avgY = canvas.height - (avgLatency / maxLatency) * canvas.height;

                ctx.strokeStyle = '#666';
                ctx.lineWidth = 1;
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.moveTo(0, avgY);
                ctx.lineTo(canvas.width, avgY);
                ctx.stroke();
                ctx.setLineDash([]);
            }
        }

        // Get local IP
        fetch('/api/ping/local-ip')
            .then(r => r.json())
            .then(data => {
                if (data.local_ip) {
                    document.getElementById('target').textContent += ` (Local: ${data.local_ip})`;
                }
            });

        // Initial update
        update();

        // Update every 2 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.REALTIME);
'''

    html_end = '''
        window.addEventListener('beforeunload', () => { clearInterval(_ivUpdate); });
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + css_var_reader + widget_script + html_end


# Export all for backward compatibility
__all__ = [
    'PingMonitor',
    'get_ping_monitor',
    'get_ping_widget_html',
    'get_local_ip',
    'PING_LOG_FILE'
]
