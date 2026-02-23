"""
Throughput Test Widget - Enterprise bandwidth testing

Displays:
- Download/Upload throughput to private servers
- Bidirectional bandwidth testing
- Real-time speed gauges
- Test history and trends

Inspired by Keysight CyPerf throughput testing.
"""

import logging

logger = logging.getLogger(__name__)


def get_throughput_widget_html():
    """Generate Throughput Test widget HTML

    Returns HTML widget for enterprise throughput testing with:
    - Download/Upload speed gauges
    - Private server configuration
    - Test controls and history
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
    <title>Throughput Test - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* Throughput Widget Styles */
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

        .widget-bordered.throughput {
            border-color: #10b981;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #10b981;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .widget-subtitle {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* Speed Gauges */
        .speed-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .speed-gauge {
            background: var(--bg-elevated);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            text-align: center;
        }

        .gauge-icon {
            font-size: 32px;
            margin-bottom: 10px;
        }

        .gauge-value {
            font-size: 42px;
            font-weight: bold;
        }

        .gauge-value.download {
            color: #10b981;
        }

        .gauge-value.upload {
            color: #3b82f6;
        }

        .gauge-unit {
            font-size: var(--font-size-md);
            color: var(--text-secondary);
        }

        .gauge-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Progress Bar (during test) */
        .progress-container {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .progress-label {
            display: flex;
            justify-content: space-between;
            font-size: var(--font-size-sm);
            margin-bottom: 8px;
        }

        .progress-bar {
            height: 8px;
            background: var(--bg-card);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .progress-fill.download {
            background: linear-gradient(90deg, #10b981, #34d399);
        }

        .progress-fill.upload {
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
        }

        /* Server Config */
        .server-config {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .config-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .config-row:last-child {
            margin-bottom: 0;
        }

        .config-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            width: 100px;
        }

        .config-input {
            flex: 1;
            padding: 10px;
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-size: var(--font-size-sm);
        }

        .config-input:focus {
            outline: none;
            border-color: #10b981;
        }

        .config-badge {
            padding: 4px 10px;
            background: var(--bg-card);
            border-radius: 4px;
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        .config-badge.connected {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
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
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
        }

        .test-btn.primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
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

        .test-btn .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
        }

        /* Quality Rating */
        .quality-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .quality-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border-subtle);
        }

        .quality-row:last-child {
            border-bottom: none;
        }

        .quality-label {
            color: var(--text-secondary);
            font-size: var(--font-size-sm);
        }

        .quality-value {
            font-weight: 600;
        }

        .quality-value.excellent { color: #22c55e; }
        .quality-value.good { color: #3b82f6; }
        .quality-value.acceptable { color: #eab308; }
        .quality-value.poor { color: #ef4444; }

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

        .section-title {
            font-size: var(--font-size-md);
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
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

        .history-speeds {
            display: flex;
            gap: 15px;
        }

        .history-speed {
            font-size: var(--font-size-sm);
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .history-speed.download { color: #10b981; }
        .history-speed.upload { color: #3b82f6; }

        /* Status Bar */
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

        .no-server {
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
        }

        .no-server-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
'''

    html_body = '''
    </style>
</head>
<body>
    <div class="widget widget-bordered throughput">
        <div class="widget-header">
            <div class="widget-title">📊 Throughput Test</div>
            <div class="widget-subtitle">Enterprise bandwidth measurement</div>
        </div>

        <div id="content">
            <!-- Initial state -->
            <div class="server-config">
                <div class="config-row">
                    <span class="config-label">Server</span>
                    <input type="text" class="config-input" id="serverHost" placeholder="Fleet server IP or hostname" value="">
                    <span class="config-badge" id="serverStatus">Not configured</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Port</span>
                    <input type="text" class="config-input" id="serverPort" placeholder="5007" value="5007" style="width: 80px; flex: none;">
                    <span class="config-badge">TCP</span>
                </div>
            </div>

            <div class="test-controls">
                <button class="test-btn primary" onclick="runThroughputTest()" id="runBtn">
                    <span>▶</span>
                    <span>Run Throughput Test</span>
                </button>
            </div>

            <div class="speed-container">
                <div class="speed-gauge">
                    <div class="gauge-icon">⬇️</div>
                    <div class="gauge-value download" id="downloadSpeed">--</div>
                    <div class="gauge-unit">Mbps</div>
                    <div class="gauge-label">Download</div>
                </div>
                <div class="speed-gauge">
                    <div class="gauge-icon">⬆️</div>
                    <div class="gauge-value upload" id="uploadSpeed">--</div>
                    <div class="gauge-unit">Mbps</div>
                    <div class="gauge-label">Upload</div>
                </div>
            </div>

            <div id="qualitySection" style="display: none;">
                <div class="quality-section">
                    <div class="quality-row">
                        <span class="quality-label">Network Quality</span>
                        <span class="quality-value" id="qualityRating">--</span>
                    </div>
                    <div class="quality-row">
                        <span class="quality-label">Streaming (4K)</span>
                        <span id="streamingQuality">--</span>
                    </div>
                    <div class="quality-row">
                        <span class="quality-label">Video Conferencing</span>
                        <span id="videoQuality">--</span>
                    </div>
                </div>
            </div>

            <div id="historySection" style="display: none;">
                <div class="history-section">
                    <div class="section-title">Test History</div>
                    <div class="history-list" id="historyList">
                    </div>
                </div>
            </div>

            <div class="status-bar">
                <span id="statusText">Configure server to begin testing</span>
                <span id="lastUpdate">--</span>
            </div>
        </div>
    </div>

    <script>
        let testHistory = [];
        let isRunning = false;

        // Fleet reporting variables
        let machineId = null;
        let fleetServerUrl = null;

        // Report metrics to fleet server
        async function reportToFleet(metrics) {
            if (!fleetServerUrl || !machineId) {
                return;
            }

            try {
                const result = await apiFetch(`${fleetServerUrl}/api/fleet/network-test/metrics`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        machine_id: machineId,
                        test_type: 'throughput',
                        metrics: metrics
                    })
                });

                if (result.ok) {
                    console.log('Throughput metrics reported to fleet server');
                } else {
                    console.log('Failed to report throughput metrics:', result.error);
                }
            } catch (e) {
                console.log('Error reporting to fleet:', e);
            }
        }

        // Try to auto-discover fleet server
        async function discoverFleetServer() {
            try {
                const result = await apiFetch('/api/agent/health');
                if (!result.ok) {
                    console.log('Could not auto-discover fleet server');
                    return;
                }
                const data = result.data;

                // Store machine ID and fleet URL for reporting
                machineId = data.machine_id || data.serial_number || 'unknown';
                fleetServerUrl = data.fleet_server_url;

                if (data.fleet_server) {
                    const url = new URL(data.fleet_server);
                    document.getElementById('serverHost').value = url.hostname;
                    document.getElementById('serverStatus').textContent = 'Fleet Server';
                    document.getElementById('serverStatus').classList.add('connected');
                }
            } catch (e) {
                console.log('Could not auto-discover fleet server');
            }
        }

        function getQualityRating(downloadMbps, uploadMbps) {
            const minSpeed = Math.min(downloadMbps, uploadMbps);
            if (minSpeed >= 100) return { rating: 'excellent', text: 'EXCELLENT' };
            if (minSpeed >= 50) return { rating: 'good', text: 'GOOD' };
            if (minSpeed >= 25) return { rating: 'acceptable', text: 'ACCEPTABLE' };
            return { rating: 'poor', text: 'POOR' };
        }

        function getStreamingQuality(downloadMbps) {
            if (downloadMbps >= 25) return { text: '4K Ultra HD', class: 'excellent' };
            if (downloadMbps >= 10) return { text: '1080p HD', class: 'good' };
            if (downloadMbps >= 5) return { text: '720p', class: 'acceptable' };
            return { text: 'SD Only', class: 'poor' };
        }

        function getVideoConfQuality(downloadMbps, uploadMbps) {
            const minSpeed = Math.min(downloadMbps, uploadMbps);
            if (minSpeed >= 10) return { text: 'Group HD Calls', class: 'excellent' };
            if (minSpeed >= 3) return { text: '1:1 HD Calls', class: 'good' };
            if (minSpeed >= 1.5) return { text: 'Standard Quality', class: 'acceptable' };
            return { text: 'Audio Only', class: 'poor' };
        }

        async function runThroughputTest() {
            if (isRunning) return;

            const serverHost = document.getElementById('serverHost').value;
            const serverPort = document.getElementById('serverPort').value || '5007';

            if (!serverHost) {
                alert('Please enter a server address');
                return;
            }

            isRunning = true;
            const runBtn = document.getElementById('runBtn');
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner"></span><span>Testing...</span>';

            document.getElementById('downloadSpeed').textContent = '...';
            document.getElementById('uploadSpeed').textContent = '...';
            document.getElementById('statusText').textContent = 'Running throughput test...';

            try {
                const result = await apiFetch('/api/network/throughput-test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        server_host: serverHost,
                        server_port: parseInt(serverPort),
                        duration: 5
                    })
                });

                if (result.ok) {
                    const data = result.data;
                    updateResults(data);

                    // Add to history
                    testHistory.unshift({
                        time: new Date().toLocaleTimeString(),
                        download: data.download_mbps || 0,
                        upload: data.upload_mbps || 0
                    });
                    if (testHistory.length > 5) testHistory.pop();
                    updateHistory();

                    // Report to fleet server
                    const quality = getQualityRating(data.download_mbps || 0, data.upload_mbps || 0);
                    reportToFleet({
                        download_mbps: data.download_mbps || 0,
                        upload_mbps: data.upload_mbps || 0,
                        server_host: serverHost,
                        server_port: parseInt(serverPort),
                        jitter_ms: data.jitter_ms || 0,
                        test_duration_seconds: data.test_duration_seconds || 0,
                        rating: quality.text,
                        bytes_transferred: data.bytes_transferred || 0
                    });
                } else {
                    throw new Error('Test failed');
                }
            } catch (error) {
                console.error('Throughput test error:', error);
                document.getElementById('downloadSpeed').textContent = 'ERR';
                document.getElementById('uploadSpeed').textContent = 'ERR';
                document.getElementById('statusText').textContent = 'Test failed - check server address';
            }

            isRunning = false;
            runBtn.disabled = false;
            runBtn.innerHTML = '<span>🔄</span><span>Run Again</span>';
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }

        function updateResults(data) {
            const download = data.download_mbps || 0;
            const upload = data.upload_mbps || 0;

            document.getElementById('downloadSpeed').textContent = download.toFixed(1);
            document.getElementById('uploadSpeed').textContent = upload.toFixed(1);

            // Show quality section
            document.getElementById('qualitySection').style.display = 'block';

            // Update quality rating
            const quality = getQualityRating(download, upload);
            const qualityEl = document.getElementById('qualityRating');
            qualityEl.textContent = quality.text;
            qualityEl.className = 'quality-value ' + quality.rating;

            // Update streaming quality
            const streaming = getStreamingQuality(download);
            document.getElementById('streamingQuality').innerHTML =
                `<span class="quality-value ${streaming.class}">${streaming.text}</span>`;

            // Update video conf quality
            const videoConf = getVideoConfQuality(download, upload);
            document.getElementById('videoQuality').innerHTML =
                `<span class="quality-value ${videoConf.class}">${videoConf.text}</span>`;

            document.getElementById('statusText').textContent =
                `Server: ${data.server || document.getElementById('serverHost').value}`;
        }

        function updateHistory() {
            if (testHistory.length === 0) {
                document.getElementById('historySection').style.display = 'none';
                return;
            }

            document.getElementById('historySection').style.display = 'block';
            const historyList = document.getElementById('historyList');
            historyList.innerHTML = testHistory.map(h => `
                <div class="history-item">
                    <span class="history-time">${h.time}</span>
                    <div class="history-speeds">
                        <span class="history-speed download">⬇️ ${h.download.toFixed(1)} Mbps</span>
                        <span class="history-speed upload">⬆️ ${h.upload.toFixed(1)} Mbps</span>
                    </div>
                </div>
            `).join('');
        }

        // Initialize
        discoverFleetServer();
    </script>
'''

    return html_start + base_styles + widget_styles + html_body + '\n<script>\n' + api_helpers + '\n' + toast_script + '\n</script>\n</body>\n</html>'
