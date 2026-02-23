"""
Network Analysis Widget
Displays automated network log analysis with slowdown explanations
"""
from atlas.agent_widget_styles import get_widget_api_helpers_script, get_widget_toast_script


def get_network_analysis_widget_html() -> str:
    """Generate HTML for the network analysis widget"""
    api_helpers = get_widget_api_helpers_script()
    toast_script = get_widget_toast_script()
    return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Analysis</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .header h1 {
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-badge {
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-healthy { background: #00c853; color: #000; }
        .status-degraded { background: #ff5252; color: #fff; }
        .status-slowdowns { background: #00E5A0; color: #000; }
        .status-poor { background: #ff5252; color: #fff; }
        
        .security-badge {
            background: rgba(0, 200, 83, 0.15);
            color: #69f0ae;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 5px;
            border: 1px solid rgba(0, 200, 83, 0.3);
        }
        .security-badge::before {
            content: "";
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .controls select, .controls button {
            padding: 10px 16px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
            cursor: pointer;
        }
        
        .controls select {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        
        .controls button {
            background: #00E5A0;
            color: #000;
            font-weight: 600;
            transition: all 0.2s;
        }

        .controls button:hover {
            background: #00C890;
            transform: translateY(-1px);
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .summary-card {
            background: rgba(26, 26, 26, 0.7);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        }

        .summary-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #00E5A0;
        }
        
        .summary-card .label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            margin-top: 5px;
        }
        
        .incidents-section {
            margin-top: 25px;
        }
        
        .section-title {
            font-size: 18px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .incident-card {
            background: rgba(26, 26, 26, 0.7);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        }
        
        .incident-header {
            background: rgba(255,82,82,0.2);
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }
        
        .incident-header:hover {
            background: rgba(255,82,82,0.3);
        }
        
        .incident-time {
            font-weight: 600;
        }
        
        .incident-stats {
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: #ccc;
        }
        
        .incident-body {
            padding: 20px;
            display: none;
        }
        
        .incident-body.expanded {
            display: block;
        }
        
        .incident-summary {
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-line;
        }
        
        .factors-grid {
            display: grid;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .factor-card {
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #888;
        }
        
        .factor-card.critical { border-left-color: #ff5252; }
        .factor-card.warning { border-left-color: #ffc107; }
        .factor-card.info { border-left-color: #00E5A0; }
        
        .factor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .factor-category {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 4px;
            background: rgba(255,255,255,0.1);
        }
        
        .factor-severity {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
        }
        
        .factor-severity.critical { background: #ff5252; color: #fff; }
        .factor-severity.warning { background: #ffc107; color: #000; }
        .factor-severity.info { background: #00E5A0; color: #000; }
        
        .factor-description {
            font-size: 14px;
            line-height: 1.5;
            color: #ddd;
        }
        
        .factor-metrics {
            margin-top: 10px;
            font-size: 12px;
            color: #888;
        }
        
        .recommendations {
            background: rgba(0, 229, 160, 0.1);
            border-radius: 8px;
            padding: 15px;
        }

        .recommendations h4 {
            margin-bottom: 10px;
            color: #00E5A0;
        }
        
        .recommendations ul {
            list-style: none;
            padding: 0;
        }
        
        .recommendations li {
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
            font-size: 14px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .recommendations li:last-child {
            border-bottom: none;
        }
        
        .recommendations li::before {
            content: "";
            position: absolute;
            left: 0;
        }
        
        .no-incidents {
            text-align: center;
            padding: 60px 20px;
            background: rgba(0,200,83,0.1);
            border-radius: 12px;
        }
        
        .no-incidents .icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .no-incidents h3 {
            color: #00c853;
            margin-bottom: 10px;
        }
        
        .loading {
            text-align: center;
            padding: 60px 20px;
        }
        
        .loading .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #00E5A0;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .last-updated {
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 20px;
        }

        /* Network Path Analysis Section */
        .path-section {
            margin-top: 25px;
            padding-top: 25px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        .path-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .path-header h3 {
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .trace-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .trace-controls input {
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 13px;
            width: 200px;
        }

        .trace-controls input:focus {
            outline: none;
            border-color: #00E5A0;
        }

        .trace-controls button {
            padding: 8px 16px;
            border-radius: 6px;
            border: none;
            background: #00E5A0;
            color: #000;
            font-weight: 600;
            cursor: pointer;
            font-size: 13px;
        }

        .trace-controls button:hover {
            background: #00C890;
        }

        .trace-controls button:disabled {
            background: #666;
            cursor: not-allowed;
        }

        .quick-targets {
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }

        .quick-target {
            padding: 5px 12px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.2);
            background: transparent;
            color: #aaa;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .quick-target:hover {
            border-color: #00E5A0;
            color: #00E5A0;
        }

        .path-summary-cards {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }

        .path-summary-card {
            background: rgba(26, 26, 26, 0.7);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }

        .path-summary-card .value {
            font-size: 24px;
            font-weight: bold;
            color: #00E5A0;
        }

        .path-summary-card .value.warning { color: #ffc107; }
        .path-summary-card .value.critical { color: #ff5252; }
        .path-summary-card .value.good { color: #00E5A0; }

        .path-summary-card .label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            margin-top: 4px;
        }

        .hops-table {
            background: rgba(26, 26, 26, 0.7);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            overflow: hidden;
        }

        .hops-header {
            display: grid;
            grid-template-columns: 50px 1fr 80px 80px 80px 80px;
            padding: 12px 15px;
            background: rgba(255,255,255,0.05);
            font-size: 11px;
            font-weight: bold;
            color: #888;
            text-transform: uppercase;
        }

        .hop-row {
            display: grid;
            grid-template-columns: 50px 1fr 80px 80px 80px 80px;
            padding: 10px 15px;
            border-top: 1px solid rgba(255,255,255,0.05);
            font-size: 13px;
            align-items: center;
        }

        .hop-row:hover {
            background: rgba(255,255,255,0.03);
        }

        .hop-num {
            color: #888;
            font-weight: bold;
        }

        .hop-host {
            display: flex;
            flex-direction: column;
        }

        .hop-hostname {
            color: #fff;
            font-weight: 500;
        }

        .hop-ip {
            font-size: 11px;
            color: #666;
        }

        .hop-metric {
            text-align: right;
            font-family: monospace;
        }

        .hop-metric.good { color: #00E5A0; }
        .hop-metric.warning { color: #ffc107; }
        .hop-metric.critical { color: #ff5252; }

        .problem-hops {
            margin-top: 15px;
            padding: 15px;
            background: rgba(255, 82, 82, 0.1);
            border: 1px solid rgba(255, 82, 82, 0.3);
            border-radius: 8px;
        }

        .problem-hops h4 {
            color: #ff8a80;
            margin: 0 0 10px 0;
            font-size: 14px;
        }

        .problem-item {
            font-size: 12px;
            color: #ccc;
            margin: 6px 0;
            padding-left: 15px;
            position: relative;
        }

        .problem-item::before {
            content: "!";
            position: absolute;
            left: 0;
            color: #ff5252;
            font-weight: bold;
        }

        .trace-loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }

        .trace-spinner {
            width: 30px;
            height: 30px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #00E5A0;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }

        .method-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            background: rgba(0, 229, 160, 0.15);
            border-radius: 4px;
            font-size: 10px;
            color: #00E5A0;
            margin-top: 10px;
        }

        .no-trace-data {
            text-align: center;
            padding: 30px;
            color: #888;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        
        .expand-icon {
            transition: transform 0.3s;
        }

        .expanded .expand-icon {
            transform: rotate(180deg);
        }

        /* Modal Styles */
        .modal {
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0, 0, 0, 0.7);
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            background: rgba(26, 26, 26, 0.95);
            backdrop-filter: blur(40px) saturate(180%);
            margin: 5% auto;
            padding: 0;
            border: 1px solid rgba(0, 229, 160, 0.3);
            border-radius: 16px;
            width: 90%;
            max-width: 600px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
            animation: slideDown 0.3s;
        }

        @keyframes slideDown {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .modal-header {
            padding: 20px 25px;
            background: linear-gradient(135deg, #2a2a2a 0%, #1e1e1e 100%);
            border-bottom: 1px solid #444;
            border-radius: 12px 12px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-header h2 {
            margin: 0;
            color: #fff;
            font-size: 20px;
        }

        .close {
            color: #999;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            transition: color 0.2s;
        }

        .close:hover,
        .close:focus {
            color: #fff;
        }

        .modal-body {
            padding: 25px;
            max-height: 60vh;
            overflow-y: auto;
        }

        .setting-group {
            margin-bottom: 25px;
        }

        .setting-group label {
            display: block;
            color: #fff;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }

        .setting-group input[type="number"] {
            width: 100%;
            padding: 10px 12px;
            background: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            color: #fff;
            font-size: 14px;
            transition: border-color 0.2s;
        }

        .setting-group input[type="number"]:focus {
            outline: none;
            border-color: #00E5A0;
            box-shadow: 0 0 20px rgba(0, 229, 160, 0.2);
        }

        .setting-group small {
            display: block;
            color: #999;
            font-size: 12px;
            margin-top: 5px;
        }

        .setting-example {
            background: rgba(0, 229, 160, 0.1);
            border-left: 3px solid #00E5A0;
            padding: 15px;
            border-radius: 6px;
            color: #ddd;
            font-size: 13px;
            line-height: 1.6;
            margin-top: 20px;
        }

        .modal-footer {
            padding: 20px 25px;
            background: #1a1a1a;
            border-top: 1px solid #444;
            border-radius: 0 0 12px 12px;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }

        .btn-primary, .btn-secondary {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #00E5A0;
            color: #0a0a0a;
            font-weight: 600;
        }

        .btn-primary:hover {
            background: #00C890;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 229, 160, 0.4);
        }

        .btn-secondary {
            background: #333;
            color: #fff;
            border: 1px solid #555;
        }

        .btn-secondary:hover {
            background: #444;
            border-color: #666;
        }

        .tooltip {
            color: #00E5A0;
            cursor: help;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Network Analysis</h1>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="security-badge">Data Encrypted</span>
                <span id="statusBadge" class="status-badge status-healthy">Loading...</span>
            </div>
        </div>
        
        <div class="controls">
            <select id="timeRange" onchange="loadAnalysis()">
                <option value="6">Last 6 Hours</option>
                <option value="24" selected>Last 24 Hours</option>
                <option value="48">Last 48 Hours</option>
                <option value="168">Last 7 Days</option>
            </select>
            <button onclick="loadAnalysis()">Refresh Analysis</button>
            <button onclick="openSettings()">Thresholds</button>
        </div>

        <!-- Settings Modal -->
        <div id="settingsModal" class="modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Analysis Thresholds</h2>
                    <span class="close" onclick="closeSettings()">&times;</span>
                </div>
                <div class="modal-body">
                    <p style="color: #999; margin-bottom: 20px;">
                        Customize when the analyzer considers your internet "slow". Adjust based on your typical speeds.
                    </p>

                    <div class="setting-group">
                        <label for="downloadThreshold">
                            Slow Download Speed (Mbps)
                            <span class="tooltip">⓵</span>
                        </label>
                        <input type="number" id="downloadThreshold" min="1" max="10000" step="0.1" />
                        <small>Speed tests below this are considered slow (default: 20 Mbps)</small>
                    </div>

                    <div class="setting-group">
                        <label for="uploadThreshold">
                            Slow Upload Speed (Mbps)
                            <span class="tooltip">⓵</span>
                        </label>
                        <input type="number" id="uploadThreshold" min="1" max="10000" step="0.1" />
                        <small>Upload speeds below this are flagged (default: 5 Mbps)</small>
                    </div>

                    <div class="setting-group">
                        <label for="pingThreshold">
                            High Ping Latency (ms)
                            <span class="tooltip">⓵</span>
                        </label>
                        <input type="number" id="pingThreshold" min="1" max="10000" step="1" />
                        <small>Ping times above this are considered high (default: 100 ms)</small>
                    </div>

                    <div class="setting-group">
                        <label for="consecutiveCount">
                            Consecutive Slow Tests Required
                            <span class="tooltip">⓵</span>
                        </label>
                        <input type="number" id="consecutiveCount" min="1" max="20" step="1" />
                        <small>How many consecutive slow tests trigger an incident (default: 3)</small>
                    </div>

                    <div class="setting-example">
                        <strong>Examples:</strong><br>
                        • Gigabit: Set 100 Mbps as slow<br>
                        • DSL/Slow: Set 5 Mbps as slow<br>
                        • Sensitive: Set consecutive to 2 for faster detection
                    </div>

                    <hr style="border: none; border-top: 1px solid #444; margin: 25px 0;">

                    <h3 style="color: #fff; font-size: 16px; margin-bottom: 15px;">🔔 Notifications</h3>

                    <div class="setting-group">
                        <label style="display: flex; align-items: center; gap: 10px;">
                            <input type="checkbox" id="notificationsEnabled" style="width: auto;">
                            <span>Enable macOS notifications for slowdowns</span>
                        </label>
                        <small>Get notified when network slowdowns are detected (max 1 per 15 min)</small>
                    </div>

                    <div class="setting-group">
                        <button onclick="testNotification()" class="btn-secondary" style="width: 100%;">
                            📬 Send Test Notification
                        </button>
                    </div>
                </div>
                <div class="modal-footer">
                    <button onclick="resetSettings()" class="btn-secondary">Reset to Defaults</button>
                    <button onclick="saveSettings()" class="btn-primary">Save Changes</button>
                </div>
            </div>
        </div>
        
        <div id="summaryCards" class="summary-cards">
            <div class="summary-card">
                <div class="value" id="incidentCount">-</div>
                <div class="label">Slowdown Incidents</div>
            </div>
            <div class="summary-card">
                <div class="value" id="speedTestCount">-</div>
                <div class="label">Speed Tests Analyzed</div>
            </div>
            <div class="summary-card">
                <div class="value" id="wifiSamples">-</div>
                <div class="label">WiFi Samples</div>
            </div>
            <div class="summary-card">
                <div class="value" id="diagCount">-</div>
                <div class="label">Diagnostics</div>
            </div>
        </div>
        
        <div id="content" class="incidents-section">
            <div class="loading">
                <div class="spinner"></div>
                <div>Analyzing network logs...</div>
            </div>
        </div>

        <!-- Network Path Analysis Section -->
        <div class="path-section">
            <div class="path-header">
                <h3>🛤️ Network Path Analysis</h3>
                <div class="trace-controls">
                    <input type="text" id="traceTarget" placeholder="Hostname or IP" value="8.8.8.8">
                    <button id="traceBtn" onclick="runTraceroute()">Trace Route</button>
                </div>
            </div>

            <div class="quick-targets">
                <button class="quick-target" onclick="setTraceTarget('8.8.8.8')">Google DNS</button>
                <button class="quick-target" onclick="setTraceTarget('1.1.1.1')">Cloudflare</button>
                <button class="quick-target" onclick="setTraceTarget('google.com')">google.com</button>
                <button class="quick-target" onclick="setTraceTarget('amazon.com')">amazon.com</button>
                <button class="quick-target" onclick="setTraceTarget('microsoft.com')">microsoft.com</button>
            </div>

            <div class="path-summary-cards" id="pathSummaryCards" style="display: none;">
                <div class="path-summary-card">
                    <div class="value" id="hopCount">-</div>
                    <div class="label">Hops</div>
                </div>
                <div class="path-summary-card">
                    <div class="value" id="avgLatency">-</div>
                    <div class="label">Avg Latency</div>
                </div>
                <div class="path-summary-card">
                    <div class="value" id="maxLatency">-</div>
                    <div class="label">Max Latency</div>
                </div>
                <div class="path-summary-card">
                    <div class="value" id="problemHops">-</div>
                    <div class="label">Issues</div>
                </div>
            </div>

            <div id="traceResults">
                <div class="no-trace-data">
                    Enter a target and click "Trace Route" to analyze the network path
                </div>
            </div>
        </div>

        <div id="lastUpdated" class="last-updated"></div>
    </div>
    
    <script>
''' + api_helpers + '''
''' + toast_script + '''
        let analysisData = null;
        
        async function loadAnalysis() {
            const hours = document.getElementById('timeRange').value;
            const content = document.getElementById('content');
            
            content.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <div>Analyzing network logs for the last ${hours} hours...</div>
                </div>
            `;
            
            try {
                const result = await apiFetch(`/api/network/analysis?hours=${hours}`);
                if (!result.ok) {
                    content.innerHTML = `
                        <div class="no-incidents">
                            <div class="icon"></div>
                            <h3>Error Loading Analysis</h3>
                            <p>${result.error}</p>
                        </div>
                    `;
                    return;
                }
                analysisData = result.data;
                renderAnalysis(analysisData);
            } catch (error) {
                content.innerHTML = `
                    <div class="no-incidents">
                        <div class="icon"></div>
                        <h3>Error Loading Analysis</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }
        
        function renderAnalysis(data) {
            // Update status badge
            const badge = document.getElementById('statusBadge');
            
            // Handle different status types
            if (data.overall_status === 'slowdowns') {
                // Show "Slowdowns: X" for past incidents
                badge.textContent = `SLOWDOWNS: ${data.slowdown_count || data.incidents_detected}`;
                badge.className = 'status-badge status-slowdowns';
            } else if (data.overall_status === 'degraded') {
                // Active issue
                badge.textContent = 'ACTIVE ISSUE';
                badge.className = 'status-badge status-degraded';
            } else {
                badge.textContent = data.overall_status.toUpperCase();
                badge.className = `status-badge status-${data.overall_status}`;
            }
            
            // Update summary cards
            document.getElementById('incidentCount').textContent = data.incidents_detected;
            document.getElementById('speedTestCount').textContent = data.data_summary.speed_tests_analyzed;
            document.getElementById('wifiSamples').textContent = data.data_summary.wifi_samples_analyzed;
            document.getElementById('diagCount').textContent = data.data_summary.network_diagnostics_analyzed;
            
            // Update last updated
            document.getElementById('lastUpdated').textContent = 
                `Analysis generated: ${new Date(data.generated_at).toLocaleString()}`;
            
            const content = document.getElementById('content');
            
            if (data.incidents.length === 0) {
                content.innerHTML = `
                    <div class="no-incidents">
                        <div class="icon"></div>
                        <h3>No Slowdowns Detected</h3>
                        <p>${data.overall_message}</p>
                        <p style="margin-top: 15px; color: #888;">
                            Thresholds: Download < ${data.thresholds.slow_download_mbps} Mbps, 
                            ${data.thresholds.consecutive_tests_required}+ consecutive slow tests
                        </p>
                    </div>
                `;
                return;
            }
            
            let html = `<h3 class="section-title">Detected Slowdown Incidents</h3>`;
            
            data.incidents.forEach((incident, index) => {
                const startTime = new Date(incident.start_time);
                const endTime = new Date(incident.end_time);
                
                html += `
                    <div class="incident-card">
                        <div class="incident-header" onclick="toggleIncident(${index})">
                            <div class="incident-time">
                                📅 ${startTime.toLocaleDateString()} ${startTime.toLocaleTimeString()} - ${endTime.toLocaleTimeString()}
                                <span style="color: #888; font-weight: normal; margin-left: 10px;">
                                    (${incident.duration_minutes.toFixed(0)} min)
                                </span>
                            </div>
                            <div class="incident-stats">
                                <span>⬇️ ${incident.avg_download_mbps} Mbps</span>
                                <span>⬆️ ${incident.avg_upload_mbps} Mbps</span>
                                <span>📶 ${incident.avg_ping_ms} ms</span>
                                <span class="expand-icon">▼</span>
                            </div>
                        </div>
                        <div class="incident-body" id="incident-${index}">
                            <div class="incident-summary">${incident.summary}</div>
                            
                            ${incident.trigger_factors && incident.trigger_factors.length > 0 ? `
                                <div style="background: rgba(255,82,82,0.15); border-radius: 8px; padding: 15px; margin-bottom: 20px; border-left: 4px solid #ff5252;">
                                    <h4 style="margin-bottom: 10px; color: #ff8a80;">Likely Trigger(s) - What Changed Right Before</h4>
                                    <ul style="list-style: none; padding: 0; margin: 0;">
                                        ${incident.trigger_factors.map(t => `<li style="padding: 5px 0; font-size: 14px;">${t}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                            
                            ${incident.metric_changes && incident.metric_changes.length > 0 ? `
                                <h4 style="margin-bottom: 15px;">Before vs During Comparison</h4>
                                <div style="background: rgba(0,0,0,0.2); border-radius: 8px; overflow: hidden; margin-bottom: 20px;">
                                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                                        <thead>
                                            <tr style="background: rgba(255,255,255,0.05);">
                                                <th style="padding: 10px; text-align: left;">Metric</th>
                                                <th style="padding: 10px; text-align: center;">Before</th>
                                                <th style="padding: 10px; text-align: center;">During</th>
                                                <th style="padding: 10px; text-align: center;">Change</th>
                                                <th style="padding: 10px; text-align: left;">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${incident.metric_changes.map(mc => `
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); ${mc.is_significant ? 'background: rgba(255,82,82,0.1);' : ''}">
                                                    <td style="padding: 10px;">
                                                        ${getCategoryIcon(mc.category)} ${mc.metric_name}
                                                    </td>
                                                    <td style="padding: 10px; text-align: center; color: #00E5A0;">${mc.before_value}</td>
                                                    <td style="padding: 10px; text-align: center; color: ${mc.is_significant ? '#ff8a80' : '#fff'};">${mc.during_value}</td>
                                                    <td style="padding: 10px; text-align: center;">
                                                        <span style="color: ${mc.direction === 'increased' ? '#ff8a80' : (mc.direction === 'decreased' ? '#81c784' : '#888')};">
                                                            ${mc.change_amount > 0 ? '+' : ''}${mc.change_amount}
                                                            ${mc.change_percent !== 0 ? ` (${mc.change_percent > 0 ? '+' : ''}${mc.change_percent.toFixed(0)}%)` : ''}
                                                        </span>
                                                    </td>
                                                    <td style="padding: 10px;">
                                                        ${mc.is_significant ? 
                                                            '<span style="background: #ff5252; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px;">SIGNIFICANT</span>' : 
                                                            '<span style="color: #888; font-size: 11px;">stable</span>'}
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : ''}
                            
                            ${incident.factors.length > 0 ? `
                                <h4 style="margin-bottom: 15px;">🔎 Contributing Factors</h4>
                                <div class="factors-grid">
                                    ${incident.factors.map(factor => `
                                        <div class="factor-card ${factor.severity}">
                                            <div class="factor-header">
                                                <span class="factor-category">${getCategoryIcon(factor.category)} ${factor.category}</span>
                                                <span class="factor-severity ${factor.severity}">${factor.severity.toUpperCase()}</span>
                                            </div>
                                            <div class="factor-description">${factor.description}</div>
                                            ${Object.keys(factor.metrics).length > 0 ? `
                                                <div class="factor-metrics">
                                                    ${Object.entries(factor.metrics).map(([k, v]) => 
                                                        `<span>${k}: ${typeof v === 'number' ? v.toFixed(1) : v}</span>`
                                                    ).join(' | ')}
                                                </div>
                                            ` : ''}
                                        </div>
                                    `).join('')}
                                </div>
                            ` : '<p style="color: #888;">No local factors identified - issue may be ISP-related.</p>'}
                            
                            ${incident.recommendations.length > 0 ? `
                                <div class="recommendations">
                                    <h4>Recommendations</h4>
                                    <ul>
                                        ${incident.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}

                            ${incident.traceroute_snapshots && incident.traceroute_snapshots.length > 0 ? `
                                <div class="traceroute-snapshots" style="margin-top: 20px;">
                                    <h4 style="margin-bottom: 15px;">🌐 Network Path Analysis (Captured During Incident)</h4>
                                    ${incident.traceroute_snapshots.map(snapshot => `
                                        <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 4px solid #ffc800;">
                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                                <div>
                                                    <strong style="color: #ffc800;">Target: ${snapshot.target}</strong>
                                                    <span style="color: #888; font-size: 12px; margin-left: 10px;">(${snapshot.method})</span>
                                                </div>
                                                <div style="font-size: 12px; color: #888;">${snapshot.timestamp}</div>
                                            </div>
                                            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px;">
                                                <div style="text-align: center; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px;">
                                                    <div style="font-size: 18px; font-weight: bold;">${snapshot.hop_count}</div>
                                                    <div style="font-size: 11px; color: #888;">Hops</div>
                                                </div>
                                                <div style="text-align: center; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px;">
                                                    <div style="font-size: 18px; font-weight: bold; color: ${snapshot.avg_latency_ms < 50 ? '#10b981' : snapshot.avg_latency_ms < 100 ? '#ffc800' : '#ff3000'};">${snapshot.avg_latency_ms.toFixed(1)}ms</div>
                                                    <div style="font-size: 11px; color: #888;">Avg Latency</div>
                                                </div>
                                                <div style="text-align: center; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px;">
                                                    <div style="font-size: 18px; font-weight: bold; color: ${snapshot.max_latency_ms < 100 ? '#10b981' : snapshot.max_latency_ms < 200 ? '#ffc800' : '#ff3000'};">${snapshot.max_latency_ms.toFixed(1)}ms</div>
                                                    <div style="font-size: 11px; color: #888;">Max Latency</div>
                                                </div>
                                                <div style="text-align: center; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px;">
                                                    <div style="font-size: 18px; font-weight: bold; color: ${snapshot.problem_hops.length === 0 ? '#10b981' : '#ff3000'};">${snapshot.problem_hops.length}</div>
                                                    <div style="font-size: 11px; color: #888;">Issues</div>
                                                </div>
                                            </div>
                                            ${snapshot.problem_hops && snapshot.problem_hops.length > 0 ? `
                                                <div style="background: rgba(255,48,0,0.1); border-radius: 6px; padding: 10px; margin-bottom: 10px;">
                                                    <div style="font-size: 12px; font-weight: bold; color: #ff8a80; margin-bottom: 8px;">⚠️ Problem Hops Detected:</div>
                                                    ${snapshot.problem_hops.map(ph => `
                                                        <div style="font-size: 12px; color: #ccc; padding: 4px 0;">
                                                            <span style="color: #ff8a80;">Hop ${ph.hop}</span> (${ph.ip}): ${ph.issues.join(', ')}
                                                        </div>
                                                    `).join('')}
                                                </div>
                                            ` : ''}
                                            <details style="cursor: pointer;">
                                                <summary style="font-size: 12px; color: #888; padding: 5px 0;">Show all ${snapshot.hops.length} hops</summary>
                                                <div style="margin-top: 10px; font-size: 12px; font-family: monospace; max-height: 200px; overflow-y: auto;">
                                                    <table style="width: 100%; border-collapse: collapse;">
                                                        <thead>
                                                            <tr style="color: #888; text-align: left;">
                                                                <th style="padding: 4px 8px;">#</th>
                                                                <th style="padding: 4px 8px;">Host</th>
                                                                <th style="padding: 4px 8px; text-align: right;">Loss</th>
                                                                <th style="padding: 4px 8px; text-align: right;">Avg</th>
                                                                <th style="padding: 4px 8px; text-align: right;">Max</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            ${snapshot.hops.map(hop => `
                                                                <tr style="border-top: 1px solid rgba(255,255,255,0.05);">
                                                                    <td style="padding: 4px 8px; color: #888;">${hop.hop}</td>
                                                                    <td style="padding: 4px 8px;">${hop.hostname !== hop.ip ? hop.hostname + ' <span style="color:#666">(' + hop.ip + ')</span>' : hop.ip}</td>
                                                                    <td style="padding: 4px 8px; text-align: right; color: ${hop.loss_pct > 20 ? '#ff3000' : hop.loss_pct > 5 ? '#ffc800' : '#10b981'};">${hop.loss_pct}%</td>
                                                                    <td style="padding: 4px 8px; text-align: right; color: ${hop.avg_ms < 50 ? '#10b981' : hop.avg_ms < 100 ? '#ffc800' : '#ff3000'};">${hop.avg_ms > 0 ? hop.avg_ms.toFixed(1) : '-'}</td>
                                                                    <td style="padding: 4px 8px; text-align: right;">${hop.max_ms > 0 ? hop.max_ms.toFixed(1) : '-'}</td>
                                                                </tr>
                                                            `).join('')}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </details>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            
            content.innerHTML = html;
        }
        
        function getCategoryIcon(category) {
            const icons = {
                'wifi_signal': '📶',
                'interference': '',
                'gateway': '',
                'internet': '',
                'event': '',
                'congestion': ''
            };
            return icons[category] || '';
        }
        
        function toggleIncident(index) {
            const body = document.getElementById(`incident-${index}`);
            body.classList.toggle('expanded');
        }

        // Settings Modal Functions
        async function openSettings() {
            const modal = document.getElementById('settingsModal');
            modal.style.display = 'block';
            await loadCurrentSettings();
        }

        function closeSettings() {
            const modal = document.getElementById('settingsModal');
            modal.style.display = 'none';
        }

        async function loadCurrentSettings() {
            try {
                const settingsResult = await apiFetch('/api/network/analysis/settings');
                if (!settingsResult.ok) {
                    console.error('Failed to load settings:', settingsResult.error);
                    return;
                }
                const settings = settingsResult.data;

                document.getElementById('downloadThreshold').value = settings.slow_download_threshold;
                document.getElementById('uploadThreshold').value = settings.slow_upload_threshold;
                document.getElementById('pingThreshold').value = settings.high_ping_threshold;
                document.getElementById('consecutiveCount').value = settings.consecutive_slow_count;

                // Load notification status
                const notifResult = await apiFetch('/api/notifications/status');
                if (!notifResult.ok) {
                    console.error('Failed to load notification status:', notifResult.error);
                    return;
                }
                document.getElementById('notificationsEnabled').checked = notifResult.data.enabled;
            } catch (error) {
                console.error('Failed to load settings:', error);
                showToast(error.message || 'Failed to load', 'error');
            }
        }

        async function saveSettings() {
            const settings = {
                slow_download_threshold: parseFloat(document.getElementById('downloadThreshold').value),
                slow_upload_threshold: parseFloat(document.getElementById('uploadThreshold').value),
                high_ping_threshold: parseFloat(document.getElementById('pingThreshold').value),
                consecutive_slow_count: parseInt(document.getElementById('consecutiveCount').value)
            };

            try {
                // Save threshold settings
                const result = await apiFetch('/api/network/analysis/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(settings)
                });

                if (!result.ok) {
                    alert(`Failed to save settings: ${result.error || 'Unknown error'}`);
                    return;
                }

                // Save notification preferences
                const notifEnabled = document.getElementById('notificationsEnabled').checked;
                const notifEndpoint = notifEnabled ? '/api/notifications/enable' : '/api/notifications/disable';
                await apiFetch(notifEndpoint, { method: 'POST' });

                closeSettings();
                // Refresh analysis with new settings
                loadAnalysis();
                alert('Settings saved successfully! Analysis will use new thresholds.');
            } catch (error) {
                alert(`Failed to save settings: ${error.message}`);
            }
        }

        async function resetSettings() {
            if (!confirm('Reset all thresholds to defaults?')) {
                return;
            }

            const defaultSettings = {
                slow_download_threshold: 20.0,
                slow_upload_threshold: 5.0,
                high_ping_threshold: 100.0,
                consecutive_slow_count: 3
            };

            try {
                const result = await apiFetch('/api/network/analysis/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(defaultSettings)
                });

                if (result.ok) {
                    await loadCurrentSettings();
                    alert('Settings reset to defaults!');
                } else {
                    alert('Failed to reset settings');
                }
            } catch (error) {
                alert(`Failed to reset settings: ${error.message}`);
            }
        }

        async function testNotification() {
            try {
                const result = await apiFetch('/api/notifications/test', { method: 'POST' });

                if (!result.ok) {
                    alert(`Failed to send test notification: ${result.error}`);
                    return;
                }

                if (result.data.sent) {
                    alert('Test notification sent! Check your macOS notification center.');
                } else {
                    alert('Failed to send notification. Make sure notifications are enabled.');
                }
            } catch (error) {
                alert(`Failed to send test notification: ${error.message}`);
            }
        }

        // Close modal when clicking outside of it
        window.onclick = function(event) {
            const modal = document.getElementById('settingsModal');
            if (event.target === modal) {
                closeSettings();
            }
        }

        // ===== Network Path Analysis Functions =====
        let isTracing = false;

        function setTraceTarget(target) {
            document.getElementById('traceTarget').value = target;
            runTraceroute();
        }

        async function runTraceroute() {
            if (isTracing) return;

            const target = document.getElementById('traceTarget').value.trim();
            if (!target) {
                alert('Please enter a target hostname or IP');
                return;
            }

            isTracing = true;
            const btn = document.getElementById('traceBtn');
            btn.disabled = true;
            btn.textContent = 'Tracing...';

            document.getElementById('pathSummaryCards').style.display = 'none';
            document.getElementById('traceResults').innerHTML = `
                <div class="trace-loading">
                    <div class="trace-spinner"></div>
                    <div>Tracing route to ${target}...</div>
                    <div style="font-size: 11px; margin-top: 5px; color: #666;">This may take 15-30 seconds</div>
                </div>
            `;

            try {
                const result = await apiFetch('/api/traceroute?target=' + encodeURIComponent(target) + '&count=3');
                if (!result.ok) {
                    document.getElementById('traceResults').innerHTML =
                        '<div class="no-trace-data">' + (result.error || 'Failed to trace route') + '</div>';
                    return;
                }
                const data = result.data;

                if (data.error) {
                    document.getElementById('traceResults').innerHTML =
                        '<div class="no-trace-data">' + data.error + '</div>';
                    return;
                }

                renderTraceResults(data);

            } catch (e) {
                console.error('Trace failed:', e);
                showToast(e.message || 'Failed to load', 'error');
                document.getElementById('traceResults').innerHTML =
                    '<div class="no-trace-data">Failed to trace route. Please try again.</div>';
            } finally {
                isTracing = false;
                btn.disabled = false;
                btn.textContent = 'Trace Route';
            }
        }

        function renderTraceResults(data) {
            const hops = data.hops || [];

            if (hops.length === 0) {
                document.getElementById('traceResults').innerHTML =
                    '<div class="no-trace-data">No hops found. The target may be unreachable.</div>';
                return;
            }

            // Calculate summary stats
            const validHops = hops.filter(h => h.avg_ms > 0);
            const avgLatency = validHops.length > 0
                ? validHops.reduce((sum, h) => sum + h.avg_ms, 0) / validHops.length
                : 0;
            const maxLatency = validHops.length > 0
                ? Math.max(...validHops.map(h => h.max_ms))
                : 0;
            const problemCount = (data.problem_hops || []).length;

            // Update summary cards
            document.getElementById('pathSummaryCards').style.display = 'grid';
            document.getElementById('hopCount').textContent = hops.length;

            const avgEl = document.getElementById('avgLatency');
            avgEl.textContent = avgLatency.toFixed(1) + 'ms';
            avgEl.className = 'value ' + getLatencyClass(avgLatency);

            const maxEl = document.getElementById('maxLatency');
            maxEl.textContent = maxLatency.toFixed(1) + 'ms';
            maxEl.className = 'value ' + getLatencyClass(maxLatency);

            const probEl = document.getElementById('problemHops');
            probEl.textContent = problemCount;
            probEl.className = 'value ' + (problemCount > 0 ? 'warning' : 'good');

            // Render hops table
            let html = `
                <div class="hops-table">
                    <div class="hops-header">
                        <div>#</div>
                        <div>Host</div>
                        <div style="text-align: right;">Loss</div>
                        <div style="text-align: right;">Avg</div>
                        <div style="text-align: right;">Best</div>
                        <div style="text-align: right;">Worst</div>
                    </div>
            `;

            hops.forEach(hop => {
                const lossClass = hop.loss_pct > 20 ? 'critical' : hop.loss_pct > 5 ? 'warning' : 'good';
                const latClass = getLatencyClass(hop.avg_ms);
                const hostname = hop.hostname !== hop.ip ? hop.hostname : '';

                html += `
                    <div class="hop-row">
                        <div class="hop-num">${hop.hop}</div>
                        <div class="hop-host">
                            <span class="hop-hostname">${hop.ip === '*' ? '* * *' : (hostname || hop.ip)}</span>
                            ${hostname && hop.ip !== '*' ? '<span class="hop-ip">' + hop.ip + '</span>' : ''}
                        </div>
                        <div class="hop-metric ${lossClass}">${hop.loss_pct.toFixed(1)}%</div>
                        <div class="hop-metric ${latClass}">${hop.avg_ms > 0 ? hop.avg_ms.toFixed(1) : '-'}</div>
                        <div class="hop-metric">${hop.min_ms > 0 ? hop.min_ms.toFixed(1) : '-'}</div>
                        <div class="hop-metric">${hop.max_ms > 0 ? hop.max_ms.toFixed(1) : '-'}</div>
                    </div>
                `;
            });

            html += '</div>';

            // Render problem hops if any
            if (data.problem_hops && data.problem_hops.length > 0) {
                html += '<div class="problem-hops"><h4>⚠️ Issues Detected</h4>';
                data.problem_hops.forEach(p => {
                    html += `<div class="problem-item">Hop ${p.hop} (${p.ip}): ${p.issues.join(', ')}</div>`;
                });
                html += '</div>';
            }

            // Method badge
            html += `<div class="method-badge">
                <span>Method:</span>
                <span>${data.method || 'native'}</span>
                <span style="margin-left: 10px;">Time: ${(data.total_time_ms / 1000).toFixed(1)}s</span>
            </div>`;

            document.getElementById('traceResults').innerHTML = html;
        }

        function getLatencyClass(ms) {
            if (ms <= 0) return '';
            if (ms < 50) return 'good';
            if (ms < 100) return 'warning';
            return 'critical';
        }

        // Allow Enter key to trigger trace
        document.getElementById('traceTarget').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') runTraceroute();
        });

        // Initial load
        loadAnalysis();

        // Auto-refresh every 5 minutes
        const _ivUpdate = setInterval(loadAnalysis, 5 * UPDATE_INTERVAL.RARE);

        // Cleanup intervals on page unload
        window.addEventListener('beforeunload', () => {
            clearInterval(_ivUpdate);
        });
    </script>
</body>
</html>'''
