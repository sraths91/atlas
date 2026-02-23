"""
Widget HTML Generators - Extracted from live_widgets.py

Standalone functions that generate HTML/CSS/JavaScript widget content.
These are pure functions returning HTML strings with no external dependencies.
"""


def get_base_widget_style():
    """Common CSS for all widgets"""
    return '''
    <style>
        :root {
            --color-primary: #00E5A0;
            --color-primary-hover: #00C890;
            --color-secondary: #00c8ff;
            --color-success: #22c55e;
            --color-warning: #f59e0b;
            --color-error: #ff4444;
            --text-primary: #ffffff;
            --text-secondary: #b0b0b0;
            --text-muted: #888888;
            --bg-primary: #1a1a1a;
            --bg-elevated: #2a2a2a;
            --border-subtle: #333;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .widget {
            text-align: center;
        }
        .widget {
            background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-primary) 100%);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            position: relative;
            overflow: hidden;
        }
        .widget::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(45deg, var(--color-primary), var(--color-secondary));
            border-radius: 20px;
            z-index: -1;
            opacity: 0.5;
        }
        .gauge {
            position: relative;
            width: 140px;
            height: 140px;
        }
        .gauge-circle {
            transform: rotate(-90deg);
        }
        .gauge-bg {
            fill: none;
            stroke: var(--border-subtle);
            stroke-width: 12;
        }
        .gauge-fill {
            fill: none;
            stroke: var(--color-primary);
            stroke-width: 8;
            stroke-linecap: round;
            transform: rotate(-90deg);
            transform-origin: center;
            transition: stroke-dashoffset 0.5s ease-out;
        }
        .value {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 36px;
            font-weight: bold;
            color: var(--color-primary);
            transition: color 0.3s ease;
        }
        .label {
            margin-top: 10px;
            font-size: 16px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        .bar {
            width: 100%;
            height: 30px;
            background: var(--border-subtle);
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }
        .bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
            transition: width 0.5s ease;
            border-radius: 15px;
        }
        .info-panel {
            width: 100%;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-subtle);
        }
        .info-item:last-child {
            border-bottom: none;
        }
        .info-label {
            color: var(--text-muted);
        }
        .info-value {
            color: var(--color-primary);
            font-weight: bold;
            transition: color 0.3s ease;
        }
    </style>
    '''

def get_cpu_widget_html():
    """CPU gauge widget"""
    return f'''<!DOCTYPE html>
<html>
<head>
<title>CPU Monitor</title>
{get_base_widget_style()}
<style>
    :root {{
        --color-primary: #00c8ff;
        --color-secondary: #0080ff;
    }}
</style>
</head>
<body>
<div class="widget">
    <div class="gauge">
        <svg class="gauge-circle" viewBox="0 0 140 140">
            <circle class="gauge-bg" cx="70" cy="70" r="60"/>
            <circle class="gauge-fill" cx="70" cy="70" r="60" 
                    stroke-dasharray="377" stroke-dashoffset="377" id="gauge"/>
        </svg>
        <div class="value" id="value">--</div>
    </div>
    <div class="label">CPU</div>
</div>

<script>
    const gauge = document.getElementById('gauge');
    const value = document.getElementById('value');
    const circumference = 377;
    
    async function update() {{
        try {{
            const response = await fetch('/api/stats');
            const data = await response.json();
            const percent = data.cpu;
            
            value.textContent = Math.round(percent) + '%';
            const offset = circumference - (percent / 100) * circumference;
            gauge.style.strokeDashoffset = offset;
        }} catch (e) {{
            console.error('Update failed:', e);
        }}
    }}
    
    update();
    setInterval(update, 1000);
</script>
</body>
</html>'''

def get_gpu_widget_html():
    """GPU gauge widget"""
    return get_cpu_widget_html().replace('CPU', 'GPU').replace('data.cpu', 'data.gpu').replace('#00c8ff', '#ff6400').replace('#0080ff', '#ff3000')

def get_memory_widget_html():
    """Memory gauge widget"""
    return get_cpu_widget_html().replace('CPU', 'RAM').replace('data.cpu', 'data.memory').replace('#00c8ff', '#00ff64').replace('#0080ff', '#00cc50')

def get_disk_widget_html():
    """Disk bar widget"""
    return f'''<!DOCTYPE html>
<html>
<head>
<title>Disk Monitor</title>
{get_base_widget_style()}
<style>
    :root {{
        --color-primary: #ffc800;
        --color-secondary: #ff8800;
    }}
</style>
</head>
<body>
<div class="widget">
    <div class="label" style="margin-bottom: 20px;">DISK</div>
    <div class="value" id="value" style="position: static; transform: none; margin-bottom: 20px;">--</div>
    <div class="bar">
        <div class="bar-fill" id="bar" style="width: 0%"></div>
    </div>
</div>

<script>
    async function update() {{
        try {{
            const response = await fetch('/api/stats');
            const data = await response.json();
            const percent = data.disk;
            
            document.getElementById('value').textContent = Math.round(percent) + '%';
            document.getElementById('bar').style.width = percent + '%';
            
            document.querySelector('.widget').classList.add('updating');
            setTimeout(() => document.querySelector('.widget').classList.remove('updating'), 300);
        }} catch (e) {{
            console.error('Update failed:', e);
        }}
    }}
    
    update();
    setInterval(update, 1000);
</script>
</body>
</html>'''

def get_network_widget_html():
    """Network graph widget"""
    return f'''<!DOCTYPE html>
<html>
<head>
<title>Network Monitor</title>
{get_base_widget_style()}
<style>
    :root {{
        --color-primary: #64ff00;
        --color-secondary: #00ff64;
    }}
    canvas {{
        width: 100%;
        height: 100px;
        border-radius: 10px;
    }}
</style>
</head>
<body>
<div class="widget" style="height: 250px;">
    <div class="label" style="margin-bottom: 10px;">NETWORK</div>
    <canvas id="graph" width="180" height="100" role="img" aria-label="Network throughput graph"></canvas>
    <div style="margin-top: 10px; font-size: 12px; width: 100%;">
        <div style="display: flex; justify-content: space-between;">
            <span style="color: var(--color-primary);">↑ <span id="up">--</span></span>
            <span style="color: var(--color-secondary);">↓ <span id="down">--</span></span>
        </div>
    </div>
</div>

<script>
    function cssVar(name) {{
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }}
    const canvas = document.getElementById('graph');
    const ctx = canvas.getContext('2d');
    const dataPoints = Array(50).fill(0);
    
    async function update() {{
        try {{
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            document.getElementById('up').textContent = data.network_up.toFixed(1) + ' KB/s';
            document.getElementById('down').textContent = data.network_down.toFixed(1) + ' KB/s';
            
            // Add new data point (total traffic)
            dataPoints.push(data.network_up + data.network_down);
            dataPoints.shift();
            
            // Draw graph
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = cssVar('--color-primary');
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            const max = Math.max(...dataPoints, 10);
            const step = canvas.width / (dataPoints.length - 1);
            
            dataPoints.forEach((point, i) => {{
                const x = i * step;
                const y = canvas.height - (point / max) * canvas.height;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }});
            
            ctx.stroke();
        }} catch (e) {{
            console.error('Update failed:', e);
        }}
    }}

    update();
    setInterval(update, 1000);
</script>
</body>
</html>'''

def get_wifi_analyzer_widget_html():
    """Enhanced WiFi Analyzer Widget - WiFi Explorer inspired features"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WiFi Analyzer - ATLAS Agent</title>
<style>
    :root {
        --color-primary: #00E5A0;
        --color-primary-hover: #00C890;
        --color-secondary: #00c8ff;
        --color-success: #22c55e;
        --color-warning: #f59e0b;
        --color-error: #ff4444;
        --text-primary: #ffffff;
        --text-secondary: #b0b0b0;
        --text-muted: #888888;
        --bg-primary: #1a1a1a;
        --bg-elevated: #2a2a2a;
        --border-subtle: #333;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        background: #0d0d0d;
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        padding: 15px;
        min-height: 100vh;
    }
    .container { max-width: 100%; }

    /* Tabs */
    .tabs {
        display: flex;
        gap: 5px;
        margin-bottom: 15px;
        flex-wrap: wrap;
    }
    .tab {
        padding: 8px 16px;
        background: var(--bg-primary);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 12px;
        font-family: inherit;
        transition: all 0.2s;
    }
    .tab:hover { background: var(--bg-elevated); color: var(--text-primary); }
    .tab.active {
        background: var(--color-secondary);
        color: #000;
        border-color: var(--color-secondary);
        font-weight: bold;
    }
    .panel { display: none; }
    .panel.active { display: block; }

    /* Status Header */
    .status-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        padding: 15px;
        background: var(--bg-primary);
        border-radius: 10px;
        border-left: 4px solid var(--color-secondary);
    }
    .ssid-name {
        font-size: 20px;
        font-weight: bold;
        color: var(--color-secondary);
    }
    .quality-badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
        text-transform: uppercase;
    }
    .quality-excellent { background: var(--color-success); color: #000; }
    .quality-good { background: #8bc34a; color: #000; }
    .quality-fair { background: var(--color-warning); color: #000; }
    .quality-poor { background: var(--color-error); color: var(--text-primary); }

    /* Metric Cards */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 10px;
        margin-bottom: 15px;
    }
    .metric-card {
        background: var(--bg-primary);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .metric-label {
        font-size: 10px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: var(--color-secondary);
        margin-top: 5px;
    }
    .metric-unit {
        font-size: 12px;
        color: var(--text-muted);
    }

    /* Signal Meter */
    .signal-meter {
        background: var(--bg-primary);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .signal-bar {
        height: 25px;
        background: var(--bg-elevated);
        border-radius: 4px;
        overflow: hidden;
        position: relative;
    }
    .signal-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 10px;
        color: #000;
        font-weight: bold;
        font-size: 12px;
    }
    .signal-fill.excellent { background: linear-gradient(90deg, #00ff64, #00cc50); }
    .signal-fill.good { background: linear-gradient(90deg, #8bc34a, #689f38); }
    .signal-fill.fair { background: linear-gradient(90deg, #ffc800, #ff9800); }
    .signal-fill.poor { background: linear-gradient(90deg, #ff6400, #ff3000); }

    /* Chart Container */
    .chart-container {
        background: var(--bg-primary);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .chart-title {
        font-size: 12px;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    canvas { width: 100%; }

    /* Period Tabs */
    .period-tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 15px;
    }
    .period-btn {
        padding: 6px 12px;
        background: var(--bg-primary);
        border: 1px solid var(--border-subtle);
        border-radius: 4px;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 11px;
    }
    .period-btn:hover { background: var(--bg-elevated); }
    .period-btn.active {
        background: var(--color-secondary);
        color: #000;
        border-color: var(--color-secondary);
    }

    /* Network List */
    .network-list {
        background: var(--bg-primary);
        border-radius: 8px;
        overflow: hidden;
    }
    .network-item {
        display: flex;
        align-items: center;
        padding: 12px 15px;
        border-bottom: 1px solid var(--bg-elevated);
        gap: 15px;
    }
    .network-item:last-child { border-bottom: none; }
    .network-item.current { background: rgba(0, 200, 255, 0.1); }
    .network-ssid {
        flex: 1;
        font-weight: 500;
    }
    .network-ssid.current { color: var(--color-secondary); }
    .network-channel {
        font-size: 12px;
        color: var(--text-muted);
        min-width: 60px;
    }
    .network-signal {
        min-width: 60px;
        text-align: right;
        font-weight: bold;
    }
    .network-bars {
        display: flex;
        gap: 2px;
        align-items: flex-end;
    }
    .bar {
        width: 4px;
        background: var(--border-subtle);
        border-radius: 1px;
    }
    .bar.active { background: var(--color-success); }

    /* Spectrum Visualization */
    .spectrum-container {
        background: var(--bg-primary);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .spectrum-title {
        font-size: 12px;
        color: var(--color-secondary);
        font-weight: bold;
        margin-bottom: 10px;
    }
    .channel-bar {
        display: inline-block;
        margin: 2px;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 10px;
        cursor: pointer;
    }
    .channel-bar.empty { background: var(--bg-elevated); color: var(--text-muted); }
    .channel-bar.low { background: var(--color-success); color: #000; }
    .channel-bar.medium { background: var(--color-warning); color: #000; }
    .channel-bar.high { background: var(--color-error); color: var(--text-primary); }
    .channel-bar.current { border: 2px solid var(--color-secondary); }

    /* Congestion Info */
    .congestion-panel {
        background: var(--bg-primary);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .congestion-level {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .congestion-none { background: var(--color-success); color: #000; }
    .congestion-low { background: #8bc34a; color: #000; }
    .congestion-moderate { background: var(--color-warning); color: #000; }
    .congestion-high { background: var(--color-error); color: var(--text-primary); }

    /* Section Title */
    .section-title {
        font-size: 12px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 15px 0 10px 0;
        padding-bottom: 5px;
        border-bottom: 1px solid var(--border-subtle);
    }

    /* Events List */
    .event-item {
        display: flex;
        justify-content: space-between;
        padding: 8px 12px;
        background: var(--bg-primary);
        border-radius: 4px;
        margin-bottom: 5px;
        font-size: 12px;
    }
    .event-type {
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: bold;
    }
    .event-type.info { background: var(--color-secondary); color: #000; }
    .event-type.warning { background: var(--color-warning); color: #000; }
    .event-type.error { background: var(--color-error); color: var(--text-primary); }

    /* Loading State */
    .loading {
        text-align: center;
        padding: 40px;
        color: var(--text-muted);
    }
</style>
</head>
<body>
<div class="container">
    <div class="tabs" role="tablist" aria-label="WiFi analyzer sections">
        <button class="tab active" role="tab" aria-selected="true" aria-controls="panel-overview" id="tab-overview" tabindex="0" onclick="showPanel('overview')">Overview</button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="panel-history" id="tab-history" tabindex="-1" onclick="showPanel('history')">Signal History</button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="panel-networks" id="tab-networks" tabindex="-1" onclick="showPanel('networks')">Nearby Networks</button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="panel-spectrum" id="tab-spectrum" tabindex="-1" onclick="showPanel('spectrum')">Channel Spectrum</button>
    </div>

    <!-- Overview Panel -->
    <div class="panel active" id="panel-overview" role="tabpanel" aria-labelledby="tab-overview">
        <div class="status-header">
            <div>
                <div class="ssid-name" id="ssidName">--</div>
                <div style="color: var(--text-muted); font-size: 12px; margin-top: 5px;">
                    <span id="wifiStandard">--</span> &bull; Channel <span id="channelInfo">--</span>
                </div>
            </div>
            <div class="quality-badge quality-good" id="qualityBadge">--</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Signal Strength</div>
                <div class="metric-value" id="rssiValue">--</div>
                <div class="metric-unit">dBm</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Noise Floor</div>
                <div class="metric-value" id="noiseValue">--</div>
                <div class="metric-unit">dBm</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">SNR</div>
                <div class="metric-value" id="snrValue">--</div>
                <div class="metric-unit">dB</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">TX Rate</div>
                <div class="metric-value" id="txRateValue">--</div>
                <div class="metric-unit">Mbps</div>
            </div>
        </div>

        <div class="signal-meter">
            <div class="chart-title">Signal Quality</div>
            <div class="signal-bar">
                <div class="signal-fill good" id="signalFill" style="width: 0%">0%</div>
            </div>
        </div>

        <div class="congestion-panel" id="congestionPanel">
            <div class="chart-title">Channel Congestion</div>
            <div style="margin-top: 10px;">
                <span class="congestion-level congestion-low" id="congestionLevel">--</span>
                <span style="color: var(--text-muted); font-size: 12px; margin-left: 10px;">
                    <span id="overlapCount">0</span> overlapping networks
                </span>
            </div>
            <div style="margin-top: 10px; font-size: 12px; color: var(--text-muted);" id="recommendedChannel"></div>
        </div>
    </div>

    <!-- History Panel -->
    <div class="panel" id="panel-history" role="tabpanel" aria-labelledby="tab-history">
        <div class="period-tabs">
            <button class="period-btn active" onclick="loadHistory('10m')">10 Min</button>
            <button class="period-btn" onclick="loadHistory('1h')">1 Hour</button>
            <button class="period-btn" onclick="loadHistory('24h')">24 Hours</button>
            <button class="period-btn" onclick="loadHistory('7d')">7 Days</button>
        </div>

        <div class="chart-container">
            <div class="chart-title">Signal Strength (RSSI) Over Time</div>
            <canvas id="rssiChart" height="150" role="img" aria-label="WiFi signal strength chart"></canvas>
        </div>

        <div class="chart-container">
            <div class="chart-title">Signal-to-Noise Ratio (SNR) Over Time</div>
            <canvas id="snrChart" height="150" role="img" aria-label="WiFi signal-to-noise ratio chart"></canvas>
        </div>

        <div class="section-title">Recent Events</div>
        <div id="eventsList">
            <div class="loading">Loading events...</div>
        </div>
    </div>

    <!-- Networks Panel -->
    <div class="panel" id="panel-networks" role="tabpanel" aria-labelledby="tab-networks">
        <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--text-muted); font-size: 12px;"><span id="networkCount">0</span> networks found</span>
            <button onclick="scanNetworks()" style="padding: 6px 12px; background: var(--color-secondary); border: none; border-radius: 4px; color: #000; font-weight: bold; cursor: pointer; font-size: 12px;">
                Scan Now
            </button>
        </div>

        <div class="network-list" id="networkList">
            <div class="loading">Scanning for networks...</div>
        </div>
    </div>

    <!-- Spectrum Panel -->
    <div class="panel" id="panel-spectrum" role="tabpanel" aria-labelledby="tab-spectrum">
        <div class="spectrum-container">
            <div class="spectrum-title">2.4 GHz Band (Channels 1-11)</div>
            <div id="spectrum24" style="margin-top: 10px;"></div>
        </div>

        <div class="spectrum-container">
            <div class="spectrum-title">5 GHz Band</div>
            <div id="spectrum5" style="margin-top: 10px;"></div>
        </div>

        <div class="congestion-panel">
            <div class="chart-title">Channel Recommendations</div>
            <div style="margin-top: 10px; font-size: 14px;">
                <div style="margin-bottom: 8px;">
                    <span style="color: var(--text-muted);">Best 2.4 GHz channel:</span>
                    <span style="color: var(--color-success); font-weight: bold; margin-left: 10px;" id="best24Channel">--</span>
                </div>
                <div>
                    <span style="color: var(--text-muted);">Best 5 GHz channel:</span>
                    <span style="color: var(--color-success); font-weight: bold; margin-left: 10px;" id="best5Channel">--</span>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }
    let currentPeriod = '10m';

    function showPanel(name) {
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.tab[role="tab"]').forEach(t => {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
            t.setAttribute('tabindex', '-1');
        });
        document.getElementById('panel-' + name).classList.add('active');
        const activeTab = document.getElementById('tab-' + name);
        if (activeTab) {
            activeTab.classList.add('active');
            activeTab.setAttribute('aria-selected', 'true');
            activeTab.setAttribute('tabindex', '0');
        }

        // Load panel-specific data
        if (name === 'networks') scanNetworks();
        if (name === 'spectrum') loadSpectrum();
        if (name === 'history') loadHistory(currentPeriod);
    }

    function getSignalBars(rssi) {
        const bars = [
            { height: 6, threshold: -90 },
            { height: 10, threshold: -75 },
            { height: 14, threshold: -65 },
            { height: 18, threshold: -55 },
            { height: 22, threshold: -45 }
        ];
        return bars.map(b => `<div class="bar${rssi >= b.threshold ? ' active' : ''}" style="height: ${b.height}px;"></div>`).join('');
    }

    async function updateOverview() {
        try {
            // Get current signal data
            const response = await fetch('/api/wifi/signal/current');
            const data = await response.json();

            if (data.status === 'connected') {
                document.getElementById('ssidName').textContent = data.ssid || 'Unknown';
                document.getElementById('wifiStandard').textContent = data.wifi_standard || data.phy_mode || '--';
                document.getElementById('channelInfo').textContent = `${data.channel || '--'} (${data.band || '--'}, ${data.channel_width || 20}MHz)`;
                document.getElementById('rssiValue').textContent = data.rssi || '--';
                document.getElementById('noiseValue').textContent = data.noise || '--';
                document.getElementById('snrValue').textContent = data.snr || '--';
                document.getElementById('txRateValue').textContent = data.tx_rate || '--';

                // Quality badge
                const badge = document.getElementById('qualityBadge');
                const rating = data.quality_rating || 'unknown';
                badge.textContent = rating.toUpperCase();
                badge.className = 'quality-badge quality-' + rating;

                // Signal bar
                const score = data.quality_score || 0;
                const fill = document.getElementById('signalFill');
                fill.style.width = score + '%';
                fill.textContent = score + '%';
                fill.className = 'signal-fill ' + rating;
            } else {
                document.getElementById('ssidName').textContent = 'Not Connected';
                document.getElementById('qualityBadge').textContent = 'OFFLINE';
                document.getElementById('qualityBadge').className = 'quality-badge quality-poor';
            }

            // Get channel analysis
            const channelResponse = await fetch('/api/wifi/channels');
            const channelData = await channelResponse.json();

            const congestionLevel = document.getElementById('congestionLevel');
            congestionLevel.textContent = (channelData.congestion_level || 'unknown').toUpperCase();
            congestionLevel.className = 'congestion-level congestion-' + (channelData.congestion_level || 'unknown');

            document.getElementById('overlapCount').textContent = channelData.overlap_count || 0;

            if (channelData.recommended_channel_5ghz || channelData.recommended_channel_2_4ghz) {
                const rec = channelData.current_network?.band === '5GHz'
                    ? channelData.recommended_channel_5ghz
                    : channelData.recommended_channel_2_4ghz;
                document.getElementById('recommendedChannel').textContent = `Recommended: Channel ${rec}`;
            }

        } catch (e) {
            console.error('Failed to update overview:', e);
        }
    }

    async function loadHistory(period) {
        currentPeriod = period;

        // Update active button
        document.querySelectorAll('.period-btn').forEach(btn => btn.classList.remove('active'));
        event?.target?.classList.add('active');

        try {
            const response = await fetch('/api/wifi/signal/history/' + period);
            const data = await response.json();

            drawChart('rssiChart', data.samples, 'rssi', cssVar('--color-secondary'), -30, -100);
            drawChart('snrChart', data.samples, 'snr', cssVar('--color-success'), 60, 0);

            // Update events
            const eventsList = document.getElementById('eventsList');
            if (data.events && data.events.length > 0) {
                eventsList.innerHTML = data.events.slice(0, 10).map(e => `
                    <div class="event-item">
                        <span class="event-type ${e.severity}">${e.type}</span>
                        <span style="flex: 1; margin-left: 10px;">${e.description}</span>
                        <span style="color: var(--text-muted);">${new Date(e.timestamp).toLocaleTimeString()}</span>
                    </div>
                `).join('');
            } else {
                eventsList.innerHTML = '<div style="color: var(--color-success); text-align: center; padding: 20px;">No events recorded</div>';
            }

        } catch (e) {
            console.error('Failed to load history:', e);
        }
    }

    function drawChart(canvasId, samples, field, color, maxVal, minVal) {
        const canvas = document.getElementById(canvasId);
        const ctx = canvas.getContext('2d');

        canvas.width = canvas.parentElement.clientWidth - 30;
        canvas.height = 150;

        ctx.fillStyle = cssVar('--bg-primary');
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        if (!samples || samples.length < 2) {
            ctx.fillStyle = cssVar('--text-muted');
            ctx.font = '12px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Collecting data...', canvas.width / 2, canvas.height / 2);
            return;
        }

        const padding = { top: 10, right: 10, bottom: 25, left: 40 };
        const chartWidth = canvas.width - padding.left - padding.right;
        const chartHeight = canvas.height - padding.top - padding.bottom;

        // Grid lines
        ctx.strokeStyle = cssVar('--border-subtle');
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartHeight / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(canvas.width - padding.right, y);
            ctx.stroke();

            // Y-axis labels
            ctx.fillStyle = cssVar('--text-muted');
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'right';
            const val = maxVal - ((maxVal - minVal) / 4) * i;
            ctx.fillText(Math.round(val), padding.left - 5, y + 3);
        }

        // Draw line
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();

        samples.forEach((s, i) => {
            const x = padding.left + (i / (samples.length - 1)) * chartWidth;
            const val = s[field] || 0;
            const y = padding.top + ((maxVal - val) / (maxVal - minVal)) * chartHeight;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }

    async function scanNetworks() {
        const list = document.getElementById('networkList');
        list.innerHTML = '<div class="loading">Scanning...</div>';

        try {
            const response = await fetch('/api/wifi/nearby');
            const data = await response.json();

            document.getElementById('networkCount').textContent = data.count || 0;

            if (data.networks && data.networks.length > 0) {
                list.innerHTML = data.networks.map(n => `
                    <div class="network-item${n.is_current ? ' current' : ''}">
                        <div class="network-bars">${getSignalBars(n.rssi)}</div>
                        <div class="network-ssid${n.is_current ? ' current' : ''}">${n.ssid || 'Hidden Network'}</div>
                        <div class="network-channel">${n.band || '--'} Ch ${n.channel || '--'}</div>
                        <div class="network-signal" style="color: ${n.rssi >= -60 ? 'var(--color-success)' : n.rssi >= -75 ? 'var(--color-warning)' : 'var(--color-error)'};">
                            ${n.rssi} dBm
                        </div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div class="loading">No networks found</div>';
            }

        } catch (e) {
            console.error('Failed to scan networks:', e);
            list.innerHTML = '<div class="loading">Scan failed</div>';
        }
    }

    async function loadSpectrum() {
        try {
            const response = await fetch('/api/wifi/spectrum');
            const data = await response.json();

            // 2.4 GHz spectrum
            const spectrum24 = document.getElementById('spectrum24');
            const channels24 = data.channels_2_4ghz || [1,2,3,4,5,6,7,8,9,10,11];
            const networks24 = data.spectrum_2_4ghz || [];

            spectrum24.innerHTML = channels24.map(ch => {
                const networksOnChannel = networks24.filter(n => n.channel === ch);
                const count = networksOnChannel.length;
                const isCurrent = networksOnChannel.some(n => n.is_current);
                let cls = 'empty';
                if (count >= 3) cls = 'high';
                else if (count >= 2) cls = 'medium';
                else if (count >= 1) cls = 'low';
                return `<span class="channel-bar ${cls}${isCurrent ? ' current' : ''}" title="${count} networks">${ch}</span>`;
            }).join('');

            // 5 GHz spectrum
            const spectrum5 = document.getElementById('spectrum5');
            const channels5 = data.channels_5ghz || [];
            const networks5 = data.spectrum_5ghz || [];

            spectrum5.innerHTML = channels5.map(ch => {
                const networksOnChannel = networks5.filter(n => n.channel === ch);
                const count = networksOnChannel.length;
                const isCurrent = networksOnChannel.some(n => n.is_current);
                let cls = 'empty';
                if (count >= 3) cls = 'high';
                else if (count >= 2) cls = 'medium';
                else if (count >= 1) cls = 'low';
                return `<span class="channel-bar ${cls}${isCurrent ? ' current' : ''}" title="${count} networks">${ch}</span>`;
            }).join('');

            // Channel recommendations
            const channelResponse = await fetch('/api/wifi/channels');
            const channelData = await channelResponse.json();

            document.getElementById('best24Channel').textContent = channelData.recommended_channel_2_4ghz || '--';
            document.getElementById('best5Channel').textContent = channelData.recommended_channel_5ghz || '--';

        } catch (e) {
            console.error('Failed to load spectrum:', e);
        }
    }

    // Tab keyboard navigation
    document.querySelectorAll('[role="tablist"]').forEach(tablist => {
        tablist.addEventListener('keydown', (e) => {
            const tabs = [...tablist.querySelectorAll('[role="tab"]')];
            const idx = tabs.indexOf(document.activeElement);
            if (idx < 0) return;
            let target = null;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                target = tabs[(idx + 1) % tabs.length];
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                target = tabs[(idx - 1 + tabs.length) % tabs.length];
            } else if (e.key === 'Home') {
                target = tabs[0];
            } else if (e.key === 'End') {
                target = tabs[tabs.length - 1];
            }
            if (target) {
                e.preventDefault();
                target.click();
                target.focus();
            }
        });
    });

    // Initial load
    updateOverview();
    setInterval(updateOverview, 5000);

    // Load history on panel switch
    setTimeout(() => loadHistory('10m'), 500);
</script>
</body>
</html>'''

def get_wifi_analyzer_compact_widget_html():
    """Compact WiFi Analyzer Widget for Dashboard - Shows key metrics at a glance"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WiFi Analyzer - ATLAS Agent</title>
<style>
    :root {
        --color-primary: #00E5A0;
        --color-primary-hover: #00C890;
        --color-secondary: #00c8ff;
        --color-success: #22c55e;
        --color-warning: #f59e0b;
        --color-error: #ff4444;
        --text-primary: #ffffff;
        --text-secondary: #b0b0b0;
        --text-muted: #888888;
        --bg-primary: #1a1a1a;
        --bg-elevated: #2a2a2a;
        --border-subtle: #333;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        background: #0d0d0d;
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        padding: 12px;
        height: 100vh;
        overflow: hidden;
    }

    .widget-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--color-secondary);
    }
    .widget-title {
        font-size: 11px;
        font-weight: bold;
        color: var(--color-secondary);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .expand-btn {
        font-size: 10px;
        padding: 4px 8px;
        background: var(--bg-primary);
        border: 1px solid var(--color-secondary);
        border-radius: 4px;
        color: var(--color-secondary);
        cursor: pointer;
        text-decoration: none;
    }
    .expand-btn:hover {
        background: var(--color-secondary);
        color: #000;
    }

    .ssid-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .ssid-name {
        font-size: 16px;
        font-weight: bold;
        color: var(--text-primary);
        max-width: 180px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .quality-badge {
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 10px;
        text-transform: uppercase;
    }
    .quality-excellent { background: var(--color-success); color: #000; }
    .quality-good { background: #8bc34a; color: #000; }
    .quality-fair { background: var(--color-warning); color: #000; }
    .quality-poor { background: var(--color-error); color: var(--text-primary); }

    .metrics-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-bottom: 10px;
    }
    .metric {
        background: var(--bg-primary);
        border-radius: 6px;
        padding: 8px 6px;
        text-align: center;
    }
    .metric-value {
        font-size: 16px;
        font-weight: bold;
        color: var(--color-secondary);
    }
    .metric-label {
        font-size: 8px;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-top: 2px;
    }

    .signal-bar-container {
        margin-bottom: 10px;
    }
    .signal-bar-label {
        display: flex;
        justify-content: space-between;
        font-size: 9px;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    .signal-bar {
        height: 8px;
        background: var(--bg-elevated);
        border-radius: 4px;
        overflow: hidden;
    }
    .signal-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    .signal-fill.excellent { background: linear-gradient(90deg, #00ff64, #00cc50); }
    .signal-fill.good { background: linear-gradient(90deg, #8bc34a, #689f38); }
    .signal-fill.fair { background: linear-gradient(90deg, #ffc800, #ff9800); }
    .signal-fill.poor { background: linear-gradient(90deg, #ff6400, #ff3000); }

    .mini-chart {
        background: var(--bg-primary);
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 10px;
        height: 70px;
    }
    .mini-chart canvas {
        width: 100%;
        height: 100%;
    }

    .info-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-top: 1px solid #222;
        font-size: 11px;
    }
    .info-row:first-child { border-top: none; }
    .info-label { color: var(--text-muted); }
    .info-value { color: var(--text-primary); font-weight: 500; }
    .info-value.warning { color: var(--color-warning); }
    .info-value.good { color: var(--color-success); }

    .channel-mini {
        display: flex;
        gap: 3px;
        flex-wrap: wrap;
        margin-top: 8px;
    }
    .ch-dot {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        font-size: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
    }
    .ch-dot.empty { background: var(--bg-elevated); color: #444; }
    .ch-dot.low { background: var(--color-success); color: #000; }
    .ch-dot.medium { background: var(--color-warning); color: #000; }
    .ch-dot.high { background: var(--color-error); color: var(--text-primary); }
    .ch-dot.current { border: 2px solid var(--color-secondary); }

    .networks-preview {
        font-size: 10px;
        color: var(--text-muted);
        margin-top: 6px;
    }
    .networks-preview span { color: var(--color-secondary); font-weight: bold; }

    .disconnected {
        text-align: center;
        padding: 40px 20px;
        color: var(--text-muted);
    }
    .disconnected .icon { font-size: 40px; margin-bottom: 10px; }

    /* Network Alias Styles */
    .ssid-container {
        display: flex;
        align-items: center;
        gap: 8px;
        max-width: 220px;
    }
    .edit-alias-btn {
        background: none;
        border: 1px solid #444;
        border-radius: 4px;
        color: var(--text-muted);
        cursor: pointer;
        padding: 2px 6px;
        font-size: 10px;
        transition: all 0.2s;
    }
    .edit-alias-btn:hover {
        border-color: var(--color-secondary);
        color: var(--color-secondary);
    }
    .alias-modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        z-index: 1000;
        justify-content: center;
        align-items: center;
    }
    .alias-modal.active { display: flex; }
    .alias-dialog {
        background: var(--bg-primary);
        border: 1px solid var(--color-secondary);
        border-radius: 10px;
        padding: 20px;
        width: 280px;
    }
    .alias-dialog h3 {
        color: var(--color-secondary);
        font-size: 14px;
        margin-bottom: 15px;
    }
    .alias-input {
        width: 100%;
        padding: 10px;
        background: #0d0d0d;
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        color: var(--text-primary);
        font-size: 14px;
        margin-bottom: 15px;
    }
    .alias-input:focus {
        outline: none;
        border-color: var(--color-secondary);
    }
    .alias-buttons {
        display: flex;
        gap: 10px;
    }
    .alias-btn {
        flex: 1;
        padding: 8px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 12px;
        font-weight: bold;
    }
    .alias-btn.save {
        background: var(--color-secondary);
        color: #000;
    }
    .alias-btn.cancel {
        background: var(--border-subtle);
        color: var(--text-primary);
    }
    .alias-btn:hover { opacity: 0.8; }
    .alias-indicator {
        font-size: 8px;
        color: var(--color-secondary);
        margin-left: 4px;
    }
</style>
</head>
<body>
<div class="widget-header">
    <span class="widget-title">WiFi Analyzer</span>
    <a href="/widget/wifi-analyzer" target="_blank" class="expand-btn">Full View →</a>
</div>

<div id="content">
    <div class="ssid-row">
        <div class="ssid-container">
            <div class="ssid-name" id="ssidName">--</div>
            <button class="edit-alias-btn" onclick="openAliasModal()" title="Set network name">Edit</button>
        </div>
        <div class="quality-badge quality-good" id="qualityBadge">--</div>
    </div>

    <div class="metrics-row">
        <div class="metric">
            <div class="metric-value" id="rssiValue">--</div>
            <div class="metric-label">RSSI</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="snrValue">--</div>
            <div class="metric-label">SNR</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="channelValue">--</div>
            <div class="metric-label">Channel</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="txRateValue">--</div>
            <div class="metric-label">TX Mbps</div>
        </div>
    </div>

    <div class="signal-bar-container">
        <div class="signal-bar-label">
            <span>Signal Quality</span>
            <span id="qualityPercent">0%</span>
        </div>
        <div class="signal-bar">
            <div class="signal-fill good" id="signalFill" style="width: 0%"></div>
        </div>
    </div>

    <div class="mini-chart">
        <canvas id="miniChart" role="img" aria-label="WiFi signal strength mini chart"></canvas>
    </div>

    <div class="info-row">
        <span class="info-label">WiFi Standard</span>
        <span class="info-value" id="wifiStandard">--</span>
    </div>
    <div class="info-row">
        <span class="info-label">Band / Width</span>
        <span class="info-value" id="bandWidth">--</span>
    </div>
    <div class="info-row">
        <span class="info-label">Congestion</span>
        <span class="info-value" id="congestion">--</span>
    </div>

    <div class="channel-mini" id="channelMini"></div>
    <div class="networks-preview" id="networksPreview"></div>
</div>

<div id="disconnected" class="disconnected" style="display: none;">
    <div class="icon">📶</div>
    <div>WiFi Disconnected</div>
</div>

<!-- Network Alias Modal -->
<div id="aliasModal" class="alias-modal">
    <div class="alias-dialog">
        <h3>Set Network Name</h3>
        <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
            Since macOS hides the SSID, you can set a custom name for this network.
            It will be remembered for future connections.
        </p>
        <input type="text" id="aliasInput" class="alias-input" placeholder="Enter network name (e.g., Home WiFi)">
        <div class="alias-buttons">
            <button class="alias-btn cancel" onclick="closeAliasModal()">Cancel</button>
            <button class="alias-btn save" onclick="saveAlias()">Save</button>
        </div>
    </div>
</div>

<script>
    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }
    const rssiHistory = [];
    const MAX_HISTORY = 30;
    let currentAlias = null;
    let currentFingerprint = null;

    function openAliasModal() {
        const modal = document.getElementById('aliasModal');
        const input = document.getElementById('aliasInput');
        input.value = currentAlias || '';
        modal.classList.add('active');
        input.focus();
    }

    function closeAliasModal() {
        document.getElementById('aliasModal').classList.remove('active');
    }

    async function saveAlias() {
        const input = document.getElementById('aliasInput');
        const alias = input.value.trim();
        if (!alias) return;

        try {
            const response = await fetch('/api/wifi/alias/set', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ alias: alias })
            });
            const result = await response.json();
            if (result.status === 'success') {
                currentAlias = alias;
                document.getElementById('ssidName').textContent = alias;
                closeAliasModal();
            }
        } catch (e) {
            console.error('Failed to save alias:', e);
        }
    }

    async function loadAlias() {
        try {
            const response = await fetch('/api/wifi/alias/current');
            const data = await response.json();
            currentFingerprint = data.fingerprint;
            currentAlias = data.alias;
            return data.alias;
        } catch (e) {
            return null;
        }
    }

    async function update() {
        try {
            const response = await fetch('/api/wifi/signal/current');
            const data = await response.json();

            if (data.status === 'connected') {
                document.getElementById('content').style.display = 'block';
                document.getElementById('disconnected').style.display = 'none';

                // Load alias first time or when network changes
                const alias = await loadAlias();

                // SSID and quality - prefer alias over system SSID
                const displayName = alias || data.ssid || 'Unknown';
                document.getElementById('ssidName').textContent = displayName;
                const badge = document.getElementById('qualityBadge');
                const rating = data.quality_rating || 'unknown';
                badge.textContent = rating.toUpperCase();
                badge.className = 'quality-badge quality-' + rating;

                // Metrics
                document.getElementById('rssiValue').textContent = data.rssi || '--';
                document.getElementById('snrValue').textContent = data.snr || '--';
                document.getElementById('channelValue').textContent = data.channel || '--';
                document.getElementById('txRateValue').textContent = data.tx_rate || '--';

                // Signal bar
                const score = data.quality_score || 0;
                document.getElementById('qualityPercent').textContent = score + '%';
                const fill = document.getElementById('signalFill');
                fill.style.width = score + '%';
                fill.className = 'signal-fill ' + rating;

                // Info
                document.getElementById('wifiStandard').textContent = data.wifi_standard || data.phy_mode || '--';
                document.getElementById('bandWidth').textContent = `${data.band || '--'} / ${data.channel_width || 20}MHz`;

                // Update history for mini chart
                rssiHistory.push(data.rssi || -100);
                if (rssiHistory.length > MAX_HISTORY) rssiHistory.shift();
                drawMiniChart();

                // Get channel data
                const channelResponse = await fetch('/api/wifi/channels');
                const channelData = await channelResponse.json();

                const congestionEl = document.getElementById('congestion');
                const level = channelData.congestion_level || 'unknown';
                congestionEl.textContent = level.charAt(0).toUpperCase() + level.slice(1) +
                    (channelData.overlap_count ? ` (${channelData.overlap_count} overlap)` : '');
                congestionEl.className = 'info-value ' + (level === 'high' ? 'warning' : level === 'none' || level === 'low' ? 'good' : '');

                // Mini channel spectrum
                const spectrum = await fetch('/api/wifi/spectrum').then(r => r.json());
                drawChannelMini(spectrum, data.channel, data.band);

                // Networks preview
                document.getElementById('networksPreview').innerHTML =
                    `<span>${channelData.total_networks || 0}</span> nearby networks detected`;

            } else {
                document.getElementById('content').style.display = 'none';
                document.getElementById('disconnected').style.display = 'block';
            }
        } catch (e) {
            console.error('Update failed:', e);
        }
    }

    function drawMiniChart() {
        const canvas = document.getElementById('miniChart');
        const ctx = canvas.getContext('2d');

        canvas.width = canvas.parentElement.clientWidth - 16;
        canvas.height = 54;

        ctx.fillStyle = cssVar('--bg-primary');
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        if (rssiHistory.length < 2) return;

        const minRssi = -100;
        const maxRssi = -30;
        const padding = 2;

        ctx.strokeStyle = cssVar('--color-secondary');
        ctx.lineWidth = 1.5;
        ctx.beginPath();

        rssiHistory.forEach((rssi, i) => {
            const x = padding + (i / (MAX_HISTORY - 1)) * (canvas.width - padding * 2);
            const y = padding + ((maxRssi - rssi) / (maxRssi - minRssi)) * (canvas.height - padding * 2);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Warning line at -70 dBm
        ctx.strokeStyle = cssVar('--color-warning');
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        const warnY = padding + ((maxRssi - (-70)) / (maxRssi - minRssi)) * (canvas.height - padding * 2);
        ctx.moveTo(0, warnY);
        ctx.lineTo(canvas.width, warnY);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    function drawChannelMini(spectrum, currentChannel, currentBand) {
        const container = document.getElementById('channelMini');
        const channels = currentBand === '5GHz' ? [36,40,44,48,149,153,157,161,165] : [1,6,11];
        const networks = currentBand === '5GHz' ? spectrum.spectrum_5ghz : spectrum.spectrum_2_4ghz;

        container.innerHTML = channels.map(ch => {
            const count = (networks || []).filter(n => n.channel === ch).length;
            let cls = 'empty';
            if (count >= 3) cls = 'high';
            else if (count >= 2) cls = 'medium';
            else if (count >= 1) cls = 'low';
            const isCurrent = ch === currentChannel;
            return `<div class="ch-dot ${cls}${isCurrent ? ' current' : ''}" title="Ch ${ch}: ${count} networks">${ch}</div>`;
        }).join('');
    }

    update();
    setInterval(update, 5000);
</script>
</body>
</html>'''

def get_speed_correlation_widget_html():
    """Speed Correlation Widget - Shows relationship between WiFi signal and speed"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Speed Correlation - ATLAS Agent</title>
<style>
    :root {
        --color-primary: #00E5A0;
        --color-primary-hover: #00C890;
        --color-secondary: #00c8ff;
        --color-success: #22c55e;
        --color-warning: #f59e0b;
        --color-error: #ff4444;
        --text-primary: #ffffff;
        --text-secondary: #b0b0b0;
        --text-muted: #888888;
        --bg-primary: #1a1a1a;
        --bg-elevated: #2a2a2a;
        --border-subtle: #333;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        padding: 20px;
        min-height: 100vh;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 2px solid var(--color-secondary);
    }
    .title {
        font-size: 18px;
        font-weight: bold;
        color: var(--color-secondary);
    }
    .subtitle {
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 4px;
    }
    .time-selector {
        display: flex;
        gap: 8px;
    }
    .time-btn {
        padding: 6px 12px;
        background: var(--bg-primary);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 11px;
        transition: all 0.2s;
    }
    .time-btn:hover { border-color: var(--color-secondary); color: var(--color-secondary); }
    .time-btn.active { background: var(--color-secondary); color: #000; border-color: var(--color-secondary); }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }
    .stat-card {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid var(--bg-elevated);
    }
    .stat-card h3 {
        font-size: 11px;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: var(--color-secondary);
    }
    .stat-label {
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 4px;
    }

    .charts-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 20px;
    }
    @media (max-width: 768px) {
        .charts-row { grid-template-columns: 1fr; }
    }

    .chart-container {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid var(--bg-elevated);
    }
    .chart-title {
        font-size: 12px;
        color: var(--color-secondary);
        margin-bottom: 10px;
        text-transform: uppercase;
    }
    .chart-canvas {
        width: 100%;
        height: 250px;
    }

    .insights-section {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid var(--bg-elevated);
        margin-bottom: 20px;
    }
    .insights-title {
        font-size: 12px;
        color: var(--color-secondary);
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .insight {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid var(--bg-elevated);
    }
    .insight:last-child { border-bottom: none; }
    .insight-icon {
        font-size: 16px;
        min-width: 24px;
    }
    .insight-text {
        font-size: 13px;
        color: #ccc;
        line-height: 1.5;
    }

    .rssi-breakdown {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid var(--bg-elevated);
    }
    .breakdown-title {
        font-size: 12px;
        color: var(--color-secondary);
        text-transform: uppercase;
        margin-bottom: 15px;
    }
    .breakdown-row {
        display: grid;
        grid-template-columns: 100px 1fr 80px 80px 80px;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid var(--bg-elevated);
        align-items: center;
        font-size: 12px;
    }
    .breakdown-row.header {
        color: var(--text-muted);
        font-weight: bold;
        border-bottom: 2px solid var(--border-subtle);
    }
    .breakdown-label {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .signal-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .signal-dot.excellent { background: var(--color-success); }
    .signal-dot.good { background: #8bc34a; }
    .signal-dot.fair { background: var(--color-warning); }
    .signal-dot.poor { background: #ff6400; }
    .signal-dot.unusable { background: var(--color-error); }
    .bar-container {
        height: 8px;
        background: var(--bg-elevated);
        border-radius: 4px;
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    .bar-fill.excellent { background: var(--color-success); }
    .bar-fill.good { background: #8bc34a; }
    .bar-fill.fair { background: var(--color-warning); }
    .bar-fill.poor { background: #ff6400; }

    .no-data {
        text-align: center;
        padding: 60px 20px;
        color: var(--text-muted);
    }
    .no-data .icon { font-size: 48px; margin-bottom: 15px; }

    .loading {
        text-align: center;
        padding: 40px;
        color: var(--text-muted);
    }
</style>
</head>
<body>
<div class="header">
    <div>
        <div class="title">Speed & Signal Correlation</div>
        <div class="subtitle">Analyze how WiFi signal strength affects your internet speed</div>
    </div>
    <div class="time-selector">
        <button class="time-btn" onclick="loadData(24)">24h</button>
        <button class="time-btn" onclick="loadData(72)">3d</button>
        <button class="time-btn active" onclick="loadData(168)">7d</button>
        <button class="time-btn" onclick="loadData(720)">30d</button>
    </div>
</div>

<div id="loading" class="loading">Loading correlation data...</div>
<div id="content" style="display: none;">
    <div class="stats-grid" id="statsGrid"></div>
    <div class="charts-row">
        <div class="chart-container">
            <div class="chart-title">Signal vs Download Speed</div>
            <canvas id="scatterChart" class="chart-canvas" role="img" aria-label="Speed test scatter plot"></canvas>
        </div>
        <div class="chart-container">
            <div class="chart-title">Speed by Signal Quality</div>
            <canvas id="barChart" class="chart-canvas" role="img" aria-label="Speed test bar chart"></canvas>
        </div>
    </div>
    <div class="insights-section">
        <div class="insights-title">Insights</div>
        <div id="insights"></div>
    </div>
    <div class="rssi-breakdown">
        <div class="breakdown-title">Performance by Signal Strength</div>
        <div id="breakdown"></div>
    </div>
</div>
<div id="noData" class="no-data" style="display: none;">
    <div class="icon">📊</div>
    <div>Not enough correlated data yet</div>
    <div style="margin-top: 10px; font-size: 12px;">
        Run some speed tests while connected to WiFi to see correlations
    </div>
</div>

<script>
    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }
    let currentData = null;
    let scatterChart = null;
    let barChart = null;

    async function loadData(hours) {
        // Update active button
        document.querySelectorAll('.time-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        document.getElementById('loading').style.display = 'block';
        document.getElementById('content').style.display = 'none';
        document.getElementById('noData').style.display = 'none';

        try {
            const response = await fetch(`/api/speed-correlation/analysis?hours=${hours}`);
            currentData = await response.json();

            if (currentData.status !== 'success' || currentData.sample_count < 3) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('noData').style.display = 'block';
                return;
            }

            document.getElementById('loading').style.display = 'none';
            document.getElementById('content').style.display = 'block';

            renderStats();
            renderScatterChart();
            renderBarChart();
            renderInsights();
            renderBreakdown();
        } catch (e) {
            console.error('Failed to load data:', e);
            document.getElementById('loading').style.display = 'none';
            document.getElementById('noData').style.display = 'block';
        }
    }

    function renderStats() {
        const stats = currentData;
        const correlation = stats.correlation?.rssi_vs_download;

        let correlationColor = cssVar('--text-muted');
        if (correlation !== null) {
            correlationColor = Math.abs(correlation) > 0.5 ? cssVar('--color-success') :
                              Math.abs(correlation) > 0.3 ? cssVar('--color-warning') : cssVar('--text-muted');
        }

        document.getElementById('statsGrid').innerHTML = `
            <div class="stat-card">
                <h3>Tests Analyzed</h3>
                <div class="stat-value">${stats.sample_count}</div>
                <div class="stat-label">of ${stats.total_tests} total tests</div>
            </div>
            <div class="stat-card">
                <h3>Correlation</h3>
                <div class="stat-value" style="color: ${correlationColor}">
                    ${correlation !== null ? (correlation > 0 ? '+' : '') + correlation.toFixed(2) : 'N/A'}
                </div>
                <div class="stat-label">${stats.correlation?.interpretation || ''}</div>
            </div>
            <div class="stat-card">
                <h3>Time Period</h3>
                <div class="stat-value">${stats.hours_analyzed}h</div>
                <div class="stat-label">${Math.round(stats.hours_analyzed / 24)} days of data</div>
            </div>
        `;
    }

    function renderScatterChart() {
        const canvas = document.getElementById('scatterChart');
        const ctx = canvas.getContext('2d');
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width - 30;
        canvas.height = 250;

        ctx.fillStyle = cssVar('--bg-primary');
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const data = currentData.scatter_data;
        if (!data || data.length === 0) return;

        const padding = { top: 20, right: 20, bottom: 40, left: 50 };
        const chartWidth = canvas.width - padding.left - padding.right;
        const chartHeight = canvas.height - padding.top - padding.bottom;

        // Find ranges
        const rssiValues = data.map(d => d.rssi);
        const downloadValues = data.map(d => d.download);
        const minRssi = Math.min(...rssiValues) - 5;
        const maxRssi = Math.max(...rssiValues) + 5;
        const maxDownload = Math.max(...downloadValues) * 1.1;

        // Draw grid
        ctx.strokeStyle = cssVar('--bg-elevated');
        ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i++) {
            const y = padding.top + (chartHeight / 5) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(canvas.width - padding.right, y);
            ctx.stroke();
        }

        // Draw axes labels
        ctx.fillStyle = cssVar('--text-muted');
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('RSSI (dBm)', canvas.width / 2, canvas.height - 5);
        ctx.save();
        ctx.translate(12, canvas.height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Download (Mbps)', 0, 0);
        ctx.restore();

        // X-axis labels
        for (let i = 0; i <= 4; i++) {
            const rssi = minRssi + ((maxRssi - minRssi) / 4) * i;
            const x = padding.left + (chartWidth / 4) * i;
            ctx.fillText(Math.round(rssi).toString(), x, canvas.height - padding.bottom + 15);
        }

        // Y-axis labels
        ctx.textAlign = 'right';
        for (let i = 0; i <= 5; i++) {
            const speed = (maxDownload / 5) * (5 - i);
            const y = padding.top + (chartHeight / 5) * i;
            ctx.fillText(Math.round(speed).toString(), padding.left - 5, y + 3);
        }

        // Draw points
        data.forEach(point => {
            const x = padding.left + ((point.rssi - minRssi) / (maxRssi - minRssi)) * chartWidth;
            const y = padding.top + (1 - point.download / maxDownload) * chartHeight;

            // Color based on SNR
            let color = cssVar('--color-secondary');
            if (point.snr >= 40) color = cssVar('--color-success');
            else if (point.snr >= 25) color = '#8bc34a';
            else if (point.snr >= 15) color = cssVar('--color-warning');
            else color = '#ff6400';

            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = cssVar('--text-primary');
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        // Draw trend line if enough points
        if (data.length >= 5) {
            const n = data.length;
            const sumX = data.reduce((s, d) => s + d.rssi, 0);
            const sumY = data.reduce((s, d) => s + d.download, 0);
            const sumXY = data.reduce((s, d) => s + d.rssi * d.download, 0);
            const sumX2 = data.reduce((s, d) => s + d.rssi * d.rssi, 0);

            const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
            const intercept = (sumY - slope * sumX) / n;

            ctx.strokeStyle = cssVar('--color-secondary');
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            const x1 = padding.left;
            const y1 = padding.top + (1 - (slope * minRssi + intercept) / maxDownload) * chartHeight;
            const x2 = canvas.width - padding.right;
            const y2 = padding.top + (1 - (slope * maxRssi + intercept) / maxDownload) * chartHeight;
            ctx.moveTo(x1, Math.max(padding.top, Math.min(y1, canvas.height - padding.bottom)));
            ctx.lineTo(x2, Math.max(padding.top, Math.min(y2, canvas.height - padding.bottom)));
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }

    function renderBarChart() {
        const canvas = document.getElementById('barChart');
        const ctx = canvas.getContext('2d');
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width - 30;
        canvas.height = 250;

        ctx.fillStyle = cssVar('--bg-primary');
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const rssiStats = currentData.rssi_stats;
        const categories = ['excellent', 'good', 'fair', 'poor'];
        const colors = { excellent: cssVar('--color-success'), good: '#8bc34a', fair: cssVar('--color-warning'), poor: '#ff6400' };

        const validCats = categories.filter(c => rssiStats[c]?.sample_count > 0);
        if (validCats.length === 0) return;

        const padding = { top: 20, right: 20, bottom: 50, left: 50 };
        const chartWidth = canvas.width - padding.left - padding.right;
        const chartHeight = canvas.height - padding.top - padding.bottom;

        const maxSpeed = Math.max(...validCats.map(c => rssiStats[c].avg_download)) * 1.2;
        const barWidth = (chartWidth / validCats.length) * 0.6;
        const gap = (chartWidth / validCats.length) * 0.4;

        // Y-axis
        ctx.fillStyle = cssVar('--text-muted');
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 5; i++) {
            const speed = (maxSpeed / 5) * (5 - i);
            const y = padding.top + (chartHeight / 5) * i;
            ctx.fillText(Math.round(speed).toString(), padding.left - 5, y + 3);

            ctx.strokeStyle = cssVar('--bg-elevated');
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(canvas.width - padding.right, y);
            ctx.stroke();
        }

        // Draw bars
        validCats.forEach((cat, i) => {
            const stats = rssiStats[cat];
            const x = padding.left + (chartWidth / validCats.length) * i + gap / 2;
            const height = (stats.avg_download / maxSpeed) * chartHeight;
            const y = padding.top + chartHeight - height;

            // Bar
            ctx.fillStyle = colors[cat];
            ctx.beginPath();
            ctx.roundRect(x, y, barWidth, height, [4, 4, 0, 0]);
            ctx.fill();

            // Label
            ctx.fillStyle = cssVar('--text-primary');
            ctx.font = 'bold 11px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(Math.round(stats.avg_download) + ' Mbps', x + barWidth / 2, y - 8);

            // Category name
            ctx.fillStyle = cssVar('--text-muted');
            ctx.font = '10px sans-serif';
            ctx.fillText(cat.charAt(0).toUpperCase() + cat.slice(1), x + barWidth / 2, canvas.height - padding.bottom + 15);
            ctx.fillText(`(${stats.sample_count})`, x + barWidth / 2, canvas.height - padding.bottom + 28);
        });
    }

    function renderInsights() {
        const insights = currentData.insights || [];
        const container = document.getElementById('insights');

        if (insights.length === 0) {
            container.innerHTML = '<div class="insight"><div class="insight-text">No significant patterns detected yet.</div></div>';
            return;
        }

        container.innerHTML = insights.map(insight => `
            <div class="insight">
                <div class="insight-icon">💡</div>
                <div class="insight-text">${insight}</div>
            </div>
        `).join('');
    }

    function renderBreakdown() {
        const rssiStats = currentData.rssi_stats;
        const categories = ['excellent', 'good', 'fair', 'poor', 'unusable'];
        const container = document.getElementById('breakdown');

        const maxDownload = Math.max(...Object.values(rssiStats)
            .filter(s => s.avg_download)
            .map(s => s.avg_download)) || 100;

        let html = `
            <div class="breakdown-row header">
                <div>Signal</div>
                <div>Avg Speed</div>
                <div>Download</div>
                <div>Upload</div>
                <div>Ping</div>
            </div>
        `;

        categories.forEach(cat => {
            const stats = rssiStats[cat];
            if (!stats) return;

            const pct = stats.avg_download ? (stats.avg_download / maxDownload) * 100 : 0;

            html += `
                <div class="breakdown-row">
                    <div class="breakdown-label">
                        <span class="signal-dot ${cat}"></span>
                        <span>${cat.charAt(0).toUpperCase() + cat.slice(1)}</span>
                    </div>
                    <div class="bar-container">
                        <div class="bar-fill ${cat}" style="width: ${pct}%"></div>
                    </div>
                    <div>${stats.avg_download ? stats.avg_download + ' Mbps' : '-'}</div>
                    <div>${stats.avg_upload ? stats.avg_upload + ' Mbps' : '-'}</div>
                    <div>${stats.avg_ping ? stats.avg_ping + ' ms' : '-'}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    // Initial load
    loadData(168);

    // Handle resize
    window.addEventListener('resize', () => {
        if (currentData) {
            renderScatterChart();
            renderBarChart();
        }
    });
</script>
</body>
</html>'''

def get_wifi_roaming_widget_html():
    """WiFi Roaming History Widget - Shows AP switches, band changes, and connection events"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WiFi Roaming History - ATLAS Agent</title>
<style>
    :root {
        --color-primary: #00E5A0;
        --color-primary-hover: #00C890;
        --color-secondary: #00c8ff;
        --color-success: #22c55e;
        --color-warning: #f59e0b;
        --color-error: #ff4444;
        --text-primary: #ffffff;
        --text-secondary: #b0b0b0;
        --text-muted: #888888;
        --bg-primary: #1a1a1a;
        --bg-elevated: #2a2a2a;
        --border-subtle: #333;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        padding: 20px;
        min-height: 100vh;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 2px solid var(--color-secondary);
    }
    .title { font-size: 18px; font-weight: bold; color: var(--color-secondary); }
    .subtitle { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
    .time-selector { display: flex; gap: 8px; }
    .time-btn {
        padding: 6px 12px;
        background: var(--bg-primary);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 11px;
        transition: all 0.2s;
    }
    .time-btn:hover { border-color: var(--color-secondary); color: var(--color-secondary); }
    .time-btn.active { background: var(--color-secondary); color: #000; border-color: var(--color-secondary); }

    .current-state {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid var(--bg-elevated);
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 15px;
    }
    .state-item { text-align: center; }
    .state-value { font-size: 20px; font-weight: bold; color: var(--color-secondary); }
    .state-label { font-size: 10px; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; }
    .state-value.connected { color: var(--color-success); }
    .state-value.disconnected { color: #ff6400; }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }
    .stat-card {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid var(--bg-elevated);
        text-align: center;
    }
    .stat-value { font-size: 28px; font-weight: bold; color: var(--color-secondary); }
    .stat-label { font-size: 10px; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; }

    .band-usage {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid var(--bg-elevated);
    }
    .band-title { font-size: 12px; color: var(--color-secondary); text-transform: uppercase; margin-bottom: 12px; }
    .band-bar { display: flex; height: 30px; border-radius: 6px; overflow: hidden; margin-bottom: 10px; }
    .band-segment { display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; }
    .band-2g { background: var(--color-warning); color: #000; }
    .band-5g { background: var(--color-secondary); color: #000; }
    .band-6g { background: #8b5cf6; color: #fff; }
    .band-legend { display: flex; gap: 20px; justify-content: center; }
    .legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-muted); }
    .legend-dot { width: 10px; height: 10px; border-radius: 50%; }

    .timeline-section {
        background: var(--bg-primary);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid var(--bg-elevated);
    }
    .timeline-title { font-size: 12px; color: var(--color-secondary); text-transform: uppercase; margin-bottom: 15px; }
    .timeline { max-height: 400px; overflow-y: auto; }
    .timeline-event {
        display: flex;
        gap: 15px;
        padding: 12px 0;
        border-bottom: 1px solid var(--bg-elevated);
    }
    .timeline-event:last-child { border-bottom: none; }
    .event-icon {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        flex-shrink: 0;
    }
    .event-icon.ap_switch { background: #8b5cf6; }
    .event-icon.band_switch { background: var(--color-secondary); }
    .event-icon.channel_change { background: var(--color-warning); }
    .event-icon.quality_change { background: #ff6400; }
    .event-icon.connect { background: var(--color-success); }
    .event-icon.disconnect { background: var(--color-error); }
    .event-content { flex: 1; }
    .event-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; }
    .event-details { font-size: 11px; color: var(--text-muted); }
    .event-time { font-size: 10px; color: var(--text-muted); margin-top: 4px; }

    .no-events {
        text-align: center;
        padding: 40px;
        color: var(--text-muted);
    }
    .no-events .icon { font-size: 40px; margin-bottom: 10px; }

    .loading { text-align: center; padding: 40px; color: var(--text-muted); }

    /* Scrollbar styling */
    .timeline::-webkit-scrollbar { width: 6px; }
    .timeline::-webkit-scrollbar-track { background: var(--bg-primary); }
    .timeline::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 3px; }
</style>
</head>
<body>
<div class="header">
    <div>
        <div class="title">WiFi Roaming History</div>
        <div class="subtitle">Track AP switches, band changes, and connection events</div>
    </div>
    <div class="time-selector">
        <button class="time-btn" onclick="loadData(1)">1h</button>
        <button class="time-btn" onclick="loadData(6)">6h</button>
        <button class="time-btn active" onclick="loadData(24)">24h</button>
        <button class="time-btn" onclick="loadData(168)">7d</button>
    </div>
</div>

<div id="loading" class="loading">Loading roaming data...</div>

<div id="content" style="display: none;">
    <div class="current-state" id="currentState"></div>

    <div class="stats-grid" id="statsGrid"></div>

    <div class="band-usage" id="bandUsage"></div>

    <div class="timeline-section">
        <div class="timeline-title">Event Timeline</div>
        <div class="timeline" id="timeline"></div>
    </div>
</div>

<script>
    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }
    let currentHours = 24;

    async function loadData(hours) {
        currentHours = hours;

        // Update button states
        document.querySelectorAll('.time-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        document.getElementById('loading').style.display = 'block';
        document.getElementById('content').style.display = 'none';

        try {
            const [statsRes, timelineRes, currentRes] = await Promise.all([
                fetch(`/api/wifi/roaming/stats?hours=${hours}`),
                fetch(`/api/wifi/roaming/timeline?hours=${hours}`),
                fetch('/api/wifi/roaming/current')
            ]);

            const stats = await statsRes.json();
            const timeline = await timelineRes.json();
            const current = await currentRes.json();

            document.getElementById('loading').style.display = 'none';
            document.getElementById('content').style.display = 'block';

            renderCurrentState(current);
            renderStats(stats);
            renderBandUsage(stats.band_usage);
            renderTimeline(timeline.timeline);
        } catch (e) {
            console.error('Error loading data:', e);
            document.getElementById('loading').textContent = 'Error loading data';
        }
    }

    function renderCurrentState(state) {
        const connected = state.connected;
        document.getElementById('currentState').innerHTML = `
            <div class="state-item">
                <div class="state-value ${connected ? 'connected' : 'disconnected'}">
                    ${connected ? 'Connected' : 'Disconnected'}
                </div>
                <div class="state-label">Status</div>
            </div>
            <div class="state-item">
                <div class="state-value">${state.band || '--'}</div>
                <div class="state-label">Band</div>
            </div>
            <div class="state-item">
                <div class="state-value">${state.channel || '--'}</div>
                <div class="state-label">Channel</div>
            </div>
            <div class="state-item">
                <div class="state-value">${state.channel_width ? state.channel_width + 'MHz' : '--'}</div>
                <div class="state-label">Width</div>
            </div>
            <div class="state-item">
                <div class="state-value">${state.rssi ? state.rssi + ' dBm' : '--'}</div>
                <div class="state-label">Signal</div>
            </div>
            <div class="state-item">
                <div class="state-value" style="text-transform: capitalize; color: ${getQualityColor(state.quality_rating)}">
                    ${state.quality_rating || '--'}
                </div>
                <div class="state-label">Quality</div>
            </div>
        `;
    }

    function getQualityColor(quality) {
        const colors = {
            excellent: cssVar('--color-success'),
            good: '#8bc34a',
            fair: cssVar('--color-warning'),
            poor: '#ff6400'
        };
        return colors[quality] || cssVar('--text-muted');
    }

    function renderStats(stats) {
        const counts = stats.event_counts || {};
        document.getElementById('statsGrid').innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${stats.total_events}</div>
                <div class="stat-label">Total Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${counts.ap_switch || 0}</div>
                <div class="stat-label">AP Switches</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${counts.band_switch || 0}</div>
                <div class="stat-label">Band Switches</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${counts.channel_change || 0}</div>
                <div class="stat-label">Channel Changes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.unique_access_points}</div>
                <div class="stat-label">Unique APs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${formatDuration(stats.session_stats?.avg_duration_seconds || 0)}</div>
                <div class="stat-label">Avg Session</div>
            </div>
        `;
    }

    function renderBandUsage(bandUsage) {
        const total = (bandUsage['2.4GHz'] || 0) + (bandUsage['5GHz'] || 0) + (bandUsage['6GHz'] || 0);

        if (total === 0) {
            document.getElementById('bandUsage').innerHTML = `
                <div class="band-title">Band Usage</div>
                <div style="text-align: center; color: var(--text-muted); padding: 20px;">No band usage data yet</div>
            `;
            return;
        }

        const pct2g = ((bandUsage['2.4GHz'] || 0) / total * 100).toFixed(1);
        const pct5g = ((bandUsage['5GHz'] || 0) / total * 100).toFixed(1);
        const pct6g = ((bandUsage['6GHz'] || 0) / total * 100).toFixed(1);

        document.getElementById('bandUsage').innerHTML = `
            <div class="band-title">Band Usage</div>
            <div class="band-bar">
                ${pct2g > 0 ? `<div class="band-segment band-2g" style="width: ${pct2g}%">${pct2g}%</div>` : ''}
                ${pct5g > 0 ? `<div class="band-segment band-5g" style="width: ${pct5g}%">${pct5g}%</div>` : ''}
                ${pct6g > 0 ? `<div class="band-segment band-6g" style="width: ${pct6g}%">${pct6g}%</div>` : ''}
            </div>
            <div class="band-legend">
                <div class="legend-item"><div class="legend-dot" style="background: var(--color-warning)"></div> 2.4GHz</div>
                <div class="legend-item"><div class="legend-dot" style="background: var(--color-secondary)"></div> 5GHz</div>
                <div class="legend-item"><div class="legend-dot" style="background: #8b5cf6"></div> 6GHz</div>
            </div>
        `;
    }

    function renderTimeline(events) {
        const container = document.getElementById('timeline');

        if (!events || events.length === 0) {
            container.innerHTML = `
                <div class="no-events">
                    <div class="icon">📡</div>
                    <div>No roaming events in this time period</div>
                </div>
            `;
            return;
        }

        container.innerHTML = events.map(item => {
            if (item.type === 'event') {
                return renderEvent(item.details);
            }
            return '';
        }).filter(Boolean).join('');
    }

    function renderEvent(event) {
        const type = event.type;
        let icon, title, details;

        switch (type) {
            case 'ap_switch':
                icon = '🔄';
                title = 'Access Point Switch';
                details = `From ${formatMAC(event.from_gateway)} to ${formatMAC(event.to_gateway)}`;
                if (event.from_band !== event.to_band) {
                    details += ` (${event.from_band} → ${event.to_band})`;
                }
                break;
            case 'band_switch':
                icon = '📶';
                title = `Band Switch: ${event.from_band} → ${event.to_band}`;
                details = `Channel ${event.from_channel} → ${event.to_channel}`;
                if (event.rssi_before && event.rssi_after) {
                    details += ` | Signal: ${event.rssi_before} → ${event.rssi_after} dBm`;
                }
                break;
            case 'channel_change':
                icon = '📻';
                title = `Channel Change: ${event.from_channel} → ${event.to_channel}`;
                details = `Band: ${event.band} | Signal: ${event.rssi} dBm`;
                break;
            case 'quality_change':
                icon = event.to_quality === 'excellent' || event.to_quality === 'good' ? '📈' : '📉';
                title = `Quality: ${event.from_quality} → ${event.to_quality}`;
                details = `Signal: ${event.from_rssi} → ${event.to_rssi} dBm | Ch ${event.channel} (${event.band})`;
                break;
            case 'connect':
                icon = '✅';
                title = 'Connected to WiFi';
                details = `Channel ${event.channel} (${event.band}) | Signal: ${event.rssi} dBm (${event.quality_rating})`;
                break;
            case 'disconnect':
                icon = '❌';
                title = 'Disconnected from WiFi';
                details = `Was on channel ${event.previous_channel} (${event.previous_band})`;
                break;
            default:
                icon = '📡';
                title = type;
                details = JSON.stringify(event);
        }

        return `
            <div class="timeline-event">
                <div class="event-icon ${type}">${icon}</div>
                <div class="event-content">
                    <div class="event-title">${title}</div>
                    <div class="event-details">${details}</div>
                    <div class="event-time">${formatTime(event.timestamp)}</div>
                </div>
            </div>
        `;
    }

    function formatMAC(mac) {
        if (!mac) return 'Unknown';
        return mac.substring(0, 8) + '...';
    }

    function formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;

        return date.toLocaleString();
    }

    function formatDuration(seconds) {
        if (!seconds || seconds < 60) return '< 1m';
        if (seconds < 3600) return Math.floor(seconds / 60) + 'm';
        return Math.floor(seconds / 3600) + 'h ' + Math.floor((seconds % 3600) / 60) + 'm';
    }

    // Initial load
    loadData(24);

    // Auto-refresh every 30 seconds
    setInterval(() => loadData(currentHours), 30000);
</script>
</body>
</html>'''

def get_info_widget_html():
    """System info panel widget"""
    return f'''<!DOCTYPE html>
<html>
<head>
<title>System Info</title>
{get_base_widget_style()}
<style>
    :root {{
        --color-primary: #00ffff;
        --color-secondary: #0080ff;
    }}
    .widget {{
        height: auto;
        min-height: 200px;
    }}
</style>
</head>
<body>
<div class="widget">
    <div class="label" style="margin-bottom: 15px;">SYSTEM INFO</div>
    <div class="info-panel">
        <div class="info-item">
            <span class="info-label">Upload</span>
            <span class="info-value" id="up">--</span>
        </div>
        <div class="info-item">
            <span class="info-label">Download</span>
            <span class="info-value" id="down">--</span>
        </div>
        <div class="info-item">
            <span class="info-label">Battery</span>
            <span class="info-value" id="battery">--</span>
        </div>
        <div class="info-item">
            <span class="info-label">Temp</span>
            <span class="info-value" id="temp">--</span>
        </div>
    </div>
</div>

<script>
    async function update() {{
        try {{
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            // Network with proper formatting
            const upSpeed = data.network_up || 0;
            const downSpeed = data.network_down || 0;
            document.getElementById('up').textContent = upSpeed.toFixed(1) + ' KB/s';
            document.getElementById('down').textContent = downSpeed.toFixed(1) + ' KB/s';
            
            // Battery with fallback
            const battery = data.battery || 0;
            if (battery > 0) {{
                document.getElementById('battery').textContent = battery + '%';
            }} else {{
                document.getElementById('battery').textContent = 'N/A';
            }}
            
            // Temperature with fallback
            const temp = data.temperature || 0;
            if (temp > 0) {{
                document.getElementById('temp').textContent = temp + '°C';
            }} else {{
                document.getElementById('temp').textContent = 'N/A';
            }}
            
            document.querySelector('.widget').classList.add('updating');
            setTimeout(() => document.querySelector('.widget').classList.remove('updating'), 300);
        }} catch (e) {{
            console.error('Update failed:', e);
        }}
    }}
    
    update();
    setInterval(update, 1000);
</script>
</body>
</html>'''
