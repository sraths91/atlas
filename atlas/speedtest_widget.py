"""
Speed Test Widget - HTML widgets for speed test monitoring

Monitor classes re-exported from atlas.network.monitors.speedtest for
backward compatibility. New code should import from there directly.
"""
import logging

# Re-export refactored monitor for backward compatibility
from atlas.network.monitors.speedtest import (
    SpeedTestMonitor,
    get_speed_test_monitor,
    SPEEDTEST_LOG_FILE
)

logger = logging.getLogger(__name__)


def get_speedtest_widget_html():
    """Generate SpeedTest widget HTML with modern UX/UI

    Returns HTML widget for speed test monitoring with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - Toast notifications instead of alerts
    - WCAG AA compliant color contrast
    - Responsive design
    - Semantic HTML structure

    Returns HTML widget for speed test monitoring with "Run Test" button
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
    <title>Speed Test - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* Speed Test Widget Specific Styles */
        body {
            padding: 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .widget {
            width: 100%;
            max-width: 400px;
        }

        .widget-bordered.speedtest {
            border-color: var(--color-speedtest);
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: var(--color-speedtest);
            text-align: center;
            margin-bottom: var(--space-lg);
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .speed-display {
            display: flex;
            justify-content: space-around;
            margin: var(--space-lg) 0;
        }

        .speed-item {
            text-align: center;
        }

        .speed-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: var(--space-xs);
        }

        .speed-value {
            font-size: var(--font-size-2xl);
            font-weight: bold;
            color: var(--color-speedtest);
        }

        .speed-unit {
            font-size: var(--font-size-md);
            color: var(--text-muted);
        }

        .ping-jitter-display {
            display: flex;
            justify-content: space-around;
            margin: var(--space-md) 0;
            padding: var(--space-md);
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
        }

        .ping-item, .jitter-item {
            text-align: center;
            flex: 1;
        }

        .ping-value {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: var(--color-ping);
        }

        .jitter-value {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #ff6b6b;
        }

        .jitter-value.excellent { color: var(--color-success); }
        .jitter-value.good { color: #84cc16; }
        .jitter-value.fair { color: #eab308; }
        .jitter-value.poor { color: var(--color-error); }

        .quality-indicator {
            font-size: var(--font-size-xs);
            color: var(--text-muted);
            margin-top: var(--space-xs);
        }

        .status {
            text-align: center;
            padding: var(--space-sm);
            margin: var(--space-md) 0;
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            font-size: var(--font-size-md);
            color: var(--text-secondary);
        }

        .status.testing {
            color: var(--color-speedtest);
            border-left: 3px solid var(--color-speedtest);
        }

        .status.idle {
            color: var(--text-muted);
        }

        .status.error {
            color: var(--color-error);
            border-left: 3px solid var(--color-error);
        }

        .run-button {
            width: 100%;
            padding: var(--space-md);
            background: linear-gradient(135deg, var(--color-speedtest), #0080ff);
            border: none;
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-size: var(--font-size-lg);
            font-weight: bold;
            cursor: pointer;
            transition: all var(--transition-normal);
        }

        .run-button:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 4px 16px rgba(0, 200, 255, 0.5);
        }

        .run-button:active:not(:disabled) {
            transform: scale(0.95);
        }

        .run-button:disabled {
            background: #333;
            cursor: not-allowed;
            transform: none;
        }

        .run-button:focus-visible {
            outline: 2px solid var(--color-speedtest);
            outline-offset: 2px;
        }

        .countdown {
            text-align: center;
            font-size: var(--font-size-sm);
            color: var(--text-muted);
            margin-top: var(--space-sm);
        }

        /* Mode Toggle Styles */
        .mode-toggle-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            margin: var(--space-md) 0;
            padding: var(--space-sm) var(--space-md);
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
        }

        .mode-toggle-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
        }

        .mode-toggle {
            position: relative;
            width: 50px;
            height: 26px;
        }

        .mode-toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .mode-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #444;
            border-radius: 26px;
            transition: all var(--transition-normal);
        }

        .mode-slider:before {
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 3px;
            bottom: 3px;
            background: white;
            border-radius: 50%;
            transition: all var(--transition-normal);
        }

        .mode-toggle input:checked + .mode-slider {
            background: linear-gradient(135deg, var(--color-speedtest), #0080ff);
        }

        .mode-toggle input:checked + .mode-slider:before {
            transform: translateX(24px);
        }

        .mode-toggle input:focus-visible + .mode-slider {
            outline: 2px solid var(--color-speedtest);
            outline-offset: 2px;
        }

        .mode-indicator {
            font-size: var(--font-size-xs);
            color: var(--text-muted);
            min-width: 80px;
        }

        .mode-indicator.full {
            color: var(--color-speedtest);
            font-weight: bold;
        }

        .mode-info {
            font-size: var(--font-size-xs);
            color: var(--text-muted);
            text-align: center;
            margin-top: var(--space-xs);
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
            .speed-value {
                font-size: var(--font-size-xl);
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered speedtest" role="main" aria-label="Speed Test Monitor">
        <h1 class="widget-title" id="widget-title">Speed Test</h1>

        <section class="speed-display" aria-label="Speed Results">
            <div class="speed-item">
                <div class="speed-label" id="download-label">&#8595; Download</div>
                <div class="speed-value" id="download" aria-labelledby="download-label" aria-live="polite">--</div>
                <div class="speed-unit">Mbps</div>
            </div>
            <div class="speed-item">
                <div class="speed-label" id="upload-label">&#8593; Upload</div>
                <div class="speed-value" id="upload" aria-labelledby="upload-label" aria-live="polite">--</div>
                <div class="speed-unit">Mbps</div>
            </div>
        </section>

        <section class="ping-jitter-display" aria-label="Latency Metrics">
            <div class="ping-item">
                <div class="speed-label" id="ping-label">Ping</div>
                <div class="ping-value" id="ping" aria-labelledby="ping-label" aria-live="polite">-- ms</div>
            </div>
            <div class="jitter-item">
                <div class="speed-label" id="jitter-label">Jitter</div>
                <div class="jitter-value" id="jitter" aria-labelledby="jitter-label" aria-live="polite">-- ms</div>
                <div class="quality-indicator" id="jitterQuality" aria-live="polite"></div>
            </div>
        </section>

        <div class="status" id="status" role="status" aria-live="polite">Idle</div>

        <!-- Mode Toggle -->
        <div class="mode-toggle-container">
            <span class="mode-toggle-label">Lite</span>
            <label class="mode-toggle" title="Toggle between Lite (low data) and Full (accurate) speed test modes">
                <input type="checkbox" id="modeToggle" onchange="toggleMode(this.checked)" aria-label="Full accuracy mode">
                <span class="mode-slider"></span>
            </label>
            <span class="mode-toggle-label">Full</span>
            <span class="mode-indicator" id="modeIndicator">Lite mode</span>
        </div>
        <div class="mode-info" id="modeInfo">Lite mode uses less data (~60-70% reduction)</div>

        <button class="run-button" id="runBtn" onclick="runTest()" aria-describedby="status">
            Run Speed Test
        </button>

        <div class="countdown" id="countdown" aria-live="polite"></div>
    </main>

    <script>
'''

    widget_script = '''
        let isRunning = false;
        let currentMode = 'lite';

        // Fetch and apply current mode on load
        async function loadMode() {
            try {
                const result = await apiFetch('/api/speedtest/mode');
                if (!result.ok) {
                    console.error('Failed to load mode:', result.error);
                    return;
                }
                const data = result.data;
                currentMode = data.current_mode || 'lite';
                updateModeUI(currentMode === 'full');
            } catch (e) {
                console.error('Failed to load mode:', e);
            }
        }

        function updateModeUI(isFull) {
            const toggle = document.getElementById('modeToggle');
            const indicator = document.getElementById('modeIndicator');
            const info = document.getElementById('modeInfo');

            toggle.checked = isFull;

            if (isFull) {
                indicator.textContent = 'Full mode';
                indicator.className = 'mode-indicator full';
                info.textContent = 'Full mode: Maximum accuracy, higher data usage';
            } else {
                indicator.textContent = 'Lite mode';
                indicator.className = 'mode-indicator';
                info.textContent = 'Lite mode uses less data (~60-70% reduction)';
            }
        }

        async function toggleMode(isFull) {
            const mode = isFull ? 'full' : 'lite';
            try {
                const result = await apiFetch('/api/speedtest/mode/set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode: mode })
                });
                if (!result.ok) {
                    ToastManager.error(result.error || 'Failed to change mode');
                    // Revert toggle
                    document.getElementById('modeToggle').checked = !isFull;
                    return;
                }
                const data = result.data;

                if (data.status === 'success') {
                    currentMode = mode;
                    updateModeUI(isFull);
                    ToastManager.success(`Speed test mode: ${mode}`);
                } else {
                    ToastManager.error(data.error || 'Failed to change mode');
                    // Revert toggle
                    document.getElementById('modeToggle').checked = !isFull;
                }
            } catch (e) {
                console.error('Failed to set mode:', e);
                ToastManager.error('Failed to change mode');
                // Revert toggle
                document.getElementById('modeToggle').checked = !isFull;
            }
        }

        async function update() {
            try {
                const result = await apiFetch('/api/speedtest');
                if (!result.ok) {
                    console.error('Update failed:', result.error);
                    return;
                }
                const data = result.data;

                // Update values
                document.getElementById('download').textContent = data.download ? data.download.toFixed(1) : '--';
                document.getElementById('upload').textContent = data.upload ? data.upload.toFixed(1) : '--';
                document.getElementById('ping').textContent = data.ping ? data.ping.toFixed(0) + ' ms' : '-- ms';

                // Update jitter with quality indicator
                const jitterEl = document.getElementById('jitter');
                const jitterQualityEl = document.getElementById('jitterQuality');
                if (data.jitter !== undefined && data.jitter !== null) {
                    jitterEl.textContent = data.jitter.toFixed(1) + ' ms';

                    // Determine jitter quality and apply class
                    let quality, qualityText;
                    if (data.jitter < 5) {
                        quality = 'excellent';
                        qualityText = 'Excellent';
                    } else if (data.jitter < 10) {
                        quality = 'good';
                        qualityText = 'Good';
                    } else if (data.jitter < 30) {
                        quality = 'fair';
                        qualityText = 'Fair';
                    } else {
                        quality = 'poor';
                        qualityText = 'Poor';
                    }

                    jitterEl.className = 'jitter-value ' + quality;
                    jitterQualityEl.textContent = qualityText;
                } else {
                    jitterEl.textContent = '-- ms';
                    jitterEl.className = 'jitter-value';
                    jitterQualityEl.textContent = '';
                }

                // Update status
                const statusEl = document.getElementById('status');
                const runBtn = document.getElementById('runBtn');

                if (data.status === 'testing') {
                    statusEl.textContent = 'Testing... Please wait';
                    statusEl.className = 'status testing';
                    runBtn.disabled = true;
                    runBtn.setAttribute('aria-busy', 'true');
                    isRunning = true;
                } else if (data.status === 'complete' || data.status === 'idle') {
                    // Both 'complete' and 'idle' mean test finished successfully
                    statusEl.textContent = data.timestamp ? `Last test: ${new Date(data.timestamp).toLocaleTimeString()}` : 'Ready';
                    statusEl.className = 'status idle';
                    runBtn.disabled = false;
                    runBtn.setAttribute('aria-busy', 'false');
                    isRunning = false;
                } else if (data.status === 'error') {
                    // Only show error if we don't have valid results
                    if (data.download > 0 || data.upload > 0) {
                        // We have results, so show last test time instead of error
                        statusEl.textContent = data.timestamp ? `Last test: ${new Date(data.timestamp).toLocaleTimeString()}` : 'Ready';
                        statusEl.className = 'status idle';
                    } else {
                        statusEl.textContent = `Error: ${data.error || 'Unknown error'}`;
                        statusEl.className = 'status error';
                    }
                    runBtn.disabled = false;
                    runBtn.setAttribute('aria-busy', 'false');
                    isRunning = false;
                }

                // Update countdown
                if (data.next_test_in) {
                    const minutes = Math.floor(data.next_test_in / 60);
                    const seconds = data.next_test_in % 60;
                    document.getElementById('countdown').textContent = `Next automatic test in ${minutes}:${seconds.toString().padStart(2, '0')}`;
                } else {
                    document.getElementById('countdown').textContent = '';
                }

            } catch (e) {
                console.error('Update failed:', e);
            }
        }

        async function runTest() {
            if (isRunning) return;

            try {
                const result = await apiFetch('/api/speedtest/run', { method: 'POST' });
                if (!result.ok) {
                    console.error('Failed to start test:', result.error);
                    ToastManager.error('Failed to start speed test');
                    return;
                }
                const data = result.data;

                if (data.status === 'started') {
                    isRunning = true;
                    document.getElementById('status').textContent = 'Test starting...';
                    document.getElementById('status').className = 'status testing';
                    document.getElementById('runBtn').disabled = true;
                    document.getElementById('runBtn').setAttribute('aria-busy', 'true');
                    ToastManager.info('Speed test started');
                }
            } catch (e) {
                console.error('Failed to start test:', e);
                ToastManager.error('Failed to start speed test');
            }
        }

        // Initial load
        loadMode();  // Load saved mode setting
        update();    // Get current speed test data

        // Update every 2 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.REALTIME);
'''

    html_end = '''
        window.addEventListener('beforeunload', () => { clearInterval(_ivUpdate); });
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


def get_speedtest_history_widget_html():
    """Generate SpeedTest history widget HTML - Shows historical data

    Returns HTML widget for speed test history with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Responsive design
    - Semantic HTML structure
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
    <title>Speed Test History - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* Speed History Widget Specific Styles */
        body {
            padding: 15px;
            overflow: hidden;
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

        .widget-bordered.history {
            border-color: var(--color-speedtest);
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: var(--color-speedtest);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .chart-container {
            flex: 1;
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-sm);
            margin-bottom: var(--space-md);
            position: relative;
            min-height: 0;
        }

        .chart-container canvas {
            width: 100%;
            height: 100%;
            display: block;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: var(--space-sm);
            flex-shrink: 0;
        }

        .stat-item {
            background: var(--bg-elevated);
            padding: var(--space-sm);
            border-radius: var(--radius-md);
            text-align: center;
            border-left: 3px solid var(--color-speedtest);
        }

        .stat-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: var(--space-xs);
        }

        .stat-value {
            font-size: var(--font-size-lg);
            font-weight: bold;
            color: var(--color-speedtest);
        }

        .stat-value.jitter {
            color: #ff6b6b;
        }

        .stat-value.jitter.excellent {
            color: #22c55e;
        }

        .stat-value.jitter.good {
            color: #84cc16;
        }

        .stat-value.jitter.fair {
            color: #eab308;
        }

        .stat-value.jitter.poor {
            color: #ef4444;
        }

        .chart-legend {
            display: flex;
            justify-content: center;
            gap: var(--space-lg);
            margin-top: var(--space-sm);
            font-size: var(--font-size-sm);
            flex-shrink: 0;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: var(--space-xs);
        }

        .legend-color {
            width: 16px;
            height: 3px;
            border-radius: 2px;
        }

        .legend-color.download {
            background: var(--color-speedtest);
        }

        .legend-color.upload {
            background: #00C8FF;  /* Secondary color for visual differentiation from download */
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .chart-container {
                height: 200px;
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered history" role="main" aria-label="Speed Test History">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">Speed History</h1>
        </header>

        <section class="chart-container" aria-label="Speed test history chart">
            <svg id="chart" aria-hidden="true" style="width: 100%; height: 100%;"></svg>
        </section>

        <div class="chart-legend" aria-hidden="true">
            <div class="legend-item">
                <span class="legend-color download"></span>
                <span>Download</span>
            </div>
            <div class="legend-item">
                <span class="legend-color upload"></span>
                <span>Upload</span>
            </div>
        </div>

        <section class="stats-grid" aria-label="Speed Test Statistics">
            <div class="stat-item">
                <div class="stat-label" id="avg-download-label">Avg Download</div>
                <div class="stat-value" id="avgDownload" aria-labelledby="avg-download-label" aria-live="polite">-- Mbps</div>
            </div>
            <div class="stat-item">
                <div class="stat-label" id="avg-upload-label">Avg Upload</div>
                <div class="stat-value" id="avgUpload" aria-labelledby="avg-upload-label" aria-live="polite">-- Mbps</div>
            </div>
            <div class="stat-item">
                <div class="stat-label" id="avg-jitter-label">Avg Jitter</div>
                <div class="stat-value jitter" id="avgJitter" aria-labelledby="avg-jitter-label" aria-live="polite">-- ms</div>
            </div>
            <div class="stat-item">
                <div class="stat-label" id="total-tests-label">Total Tests</div>
                <div class="stat-value" id="totalTests" aria-labelledby="total-tests-label" aria-live="polite">--</div>
            </div>
        </section>
    </main>

    <script>
'''

    widget_script = '''
        const svg = document.getElementById('chart');
        let history = [];

        async function update() {
            try {
                const result = await apiFetch('/api/speedtest/history');
                if (!result.ok) {
                    console.error('Update failed:', result.error);
                    return;
                }
                const data = result.data;
                history = data.slice(-20); // Last 20 tests

                // Calculate averages
                if (history.length > 0) {
                    const avgDown = history.reduce((sum, t) => sum + (t.download || 0), 0) / history.length;
                    const avgUp = history.reduce((sum, t) => sum + (t.upload || 0), 0) / history.length;

                    // Calculate average jitter (only from tests that have jitter data)
                    const jitterTests = history.filter(t => t.jitter !== undefined && t.jitter !== null);
                    const avgJitter = jitterTests.length > 0
                        ? jitterTests.reduce((sum, t) => sum + t.jitter, 0) / jitterTests.length
                        : null;

                    document.getElementById('avgDownload').textContent = avgDown.toFixed(1) + ' Mbps';
                    document.getElementById('avgUpload').textContent = avgUp.toFixed(1) + ' Mbps';
                    document.getElementById('totalTests').textContent = history.length;

                    // Update average jitter with quality color
                    const avgJitterEl = document.getElementById('avgJitter');
                    if (avgJitter !== null) {
                        avgJitterEl.textContent = avgJitter.toFixed(1) + ' ms';
                        // Determine quality class
                        let quality;
                        if (avgJitter < 5) quality = 'excellent';
                        else if (avgJitter < 10) quality = 'good';
                        else if (avgJitter < 30) quality = 'fair';
                        else quality = 'poor';
                        avgJitterEl.className = 'stat-value jitter ' + quality;
                    } else {
                        avgJitterEl.textContent = '-- ms';
                        avgJitterEl.className = 'stat-value jitter';
                    }
                } else {
                    document.getElementById('avgDownload').textContent = '-- Mbps';
                    document.getElementById('avgUpload').textContent = '-- Mbps';
                    document.getElementById('avgJitter').textContent = '-- ms';
                    document.getElementById('totalTests').textContent = '0';
                }

                drawChart();
            } catch (e) {
                console.error('Update failed:', e);
            }
        }

        function drawChart() {
            if (history.length === 0) return;

            const rect = svg.getBoundingClientRect();
            const width = rect.width;
            const height = rect.height;

            // Clear SVG
            svg.innerHTML = '';

            if (history.length < 2) return;

            const maxSpeed = Math.max(...history.map(t => Math.max(t.download || 0, t.upload || 0)), 100);
            const paddingLeft = 45;  // Extra space for Y-axis labels
            const paddingRight = 20;
            const paddingTop = 20;
            const paddingBottom = 25;  // Extra space for X-axis label
            const chartWidth = width - paddingLeft - paddingRight;
            const chartHeight = height - paddingTop - paddingBottom;
            const step = chartWidth / (history.length - 1);

            // Create defs for gradients and filters
            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');

            // Glow filter for download line
            const downloadGlow = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
            downloadGlow.setAttribute('id', 'downloadGlow');
            downloadGlow.innerHTML = '<feGaussianBlur stdDeviation="2" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>';
            defs.appendChild(downloadGlow);

            // Glow filter for upload line
            const uploadGlow = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
            uploadGlow.setAttribute('id', 'uploadGlow');
            uploadGlow.innerHTML = '<feGaussianBlur stdDeviation="2" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>';
            defs.appendChild(uploadGlow);

            svg.appendChild(defs);

            // Draw grid lines and Y-axis labels
            for (let i = 0; i <= 4; i++) {
                const y = paddingTop + (chartHeight / 4) * i;
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', paddingLeft);
                line.setAttribute('y1', y);
                line.setAttribute('x2', width - paddingRight);
                line.setAttribute('y2', y);
                line.setAttribute('stroke', 'rgba(255, 255, 255, 0.05)');
                line.setAttribute('stroke-width', '1');
                svg.appendChild(line);

                // Y-axis labels (speed values)
                const speedValue = maxSpeed * (1 - (i / 4));
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', paddingLeft - 8);
                text.setAttribute('y', y + 4);
                text.setAttribute('text-anchor', 'end');
                text.setAttribute('font-size', '10');
                text.setAttribute('fill', 'rgba(255, 255, 255, 0.5)');
                text.textContent = speedValue.toFixed(0);
                svg.appendChild(text);
            }

            // Y-axis label (Mbps)
            const yAxisLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            yAxisLabel.setAttribute('x', 5);
            yAxisLabel.setAttribute('y', paddingTop - 5);
            yAxisLabel.setAttribute('font-size', '11');
            yAxisLabel.setAttribute('font-weight', 'bold');
            yAxisLabel.setAttribute('fill', 'rgba(255, 255, 255, 0.7)');
            yAxisLabel.textContent = 'Mbps';
            svg.appendChild(yAxisLabel);

            // X-axis label (Test #)
            const xAxisLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            xAxisLabel.setAttribute('x', width - paddingRight);
            xAxisLabel.setAttribute('y', height - 5);
            xAxisLabel.setAttribute('text-anchor', 'end');
            xAxisLabel.setAttribute('font-size', '11');
            xAxisLabel.setAttribute('font-weight', 'bold');
            xAxisLabel.setAttribute('fill', 'rgba(255, 255, 255, 0.7)');
            xAxisLabel.textContent = 'Tests';
            svg.appendChild(xAxisLabel);

            // Build download path
            let downloadPath = '';
            history.forEach((test, i) => {
                const x = paddingLeft + (i * step);
                const y = paddingTop + chartHeight - ((test.download || 0) / maxSpeed * chartHeight);
                downloadPath += (i === 0 ? 'M' : 'L') + x + ',' + y;
            });

            // Draw download line
            const downloadLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            downloadLine.setAttribute('d', downloadPath);
            downloadLine.setAttribute('stroke', '#00E5A0');
            downloadLine.setAttribute('stroke-width', '2');
            downloadLine.setAttribute('stroke-linecap', 'round');
            downloadLine.setAttribute('stroke-linejoin', 'round');
            downloadLine.setAttribute('fill', 'none');
            downloadLine.setAttribute('filter', 'url(#downloadGlow)');
            svg.appendChild(downloadLine);

            // Draw download points
            history.forEach((test, i) => {
                const x = paddingLeft + (i * step);
                const y = paddingTop + chartHeight - ((test.download || 0) / maxSpeed * chartHeight);
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', x);
                circle.setAttribute('cy', y);
                circle.setAttribute('r', '3');
                circle.setAttribute('fill', '#00E5A0');
                svg.appendChild(circle);
            });

            // Build upload path
            let uploadPath = '';
            history.forEach((test, i) => {
                const x = paddingLeft + (i * step);
                const y = paddingTop + chartHeight - ((test.upload || 0) / maxSpeed * chartHeight);
                uploadPath += (i === 0 ? 'M' : 'L') + x + ',' + y;
            });

            // Draw upload line
            const uploadLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            uploadLine.setAttribute('d', uploadPath);
            uploadLine.setAttribute('stroke', '#00C8FF');
            uploadLine.setAttribute('stroke-width', '2');
            uploadLine.setAttribute('stroke-linecap', 'round');
            uploadLine.setAttribute('stroke-linejoin', 'round');
            uploadLine.setAttribute('fill', 'none');
            uploadLine.setAttribute('filter', 'url(#uploadGlow)');
            svg.appendChild(uploadLine);

            // Draw upload points
            history.forEach((test, i) => {
                const x = paddingLeft + (i * step);
                const y = paddingTop + chartHeight - ((test.upload || 0) / maxSpeed * chartHeight);
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', x);
                circle.setAttribute('cy', y);
                circle.setAttribute('r', '3');
                circle.setAttribute('fill', '#00C8FF');
                svg.appendChild(circle);
            });
        }

        // Initial setup
        update();

        // Handle window resize with debounce
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(drawChart, 100);
        });

        // Update every 10 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.STANDARD);
'''

    html_end = '''
        window.addEventListener('beforeunload', () => { clearInterval(_ivUpdate); });
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


# Export all for backward compatibility
__all__ = [
    'SpeedTestMonitor',
    'get_speed_test_monitor',
    'get_speedtest_widget_html',
    'get_speedtest_history_widget_html',
    'SPEEDTEST_LOG_FILE'
]
