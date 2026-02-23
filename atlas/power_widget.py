"""
Power & Battery Widget - Dashboard widget for power and thermal monitoring
"""
import logging

logger = logging.getLogger(__name__)


def get_power_widget_html():
    """Generate Power & Battery widget HTML"""
    from atlas.agent_widget_styles import (
        get_widget_base_styles,
        get_widget_toast_script,
        get_widget_api_helpers_script
    )

    base_styles = get_widget_base_styles()
    toast_script = get_widget_toast_script()
    api_helpers = get_widget_api_helpers_script()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Power & Battery - ATLAS Agent</title>
    <style>
{base_styles}
        body {{
            padding: 20px;
            max-width: 600px;
            margin: 0 auto;
        }}
        .widget-title {{
            font-size: 24px;
            font-weight: bold;
            color: #10b981;
            text-align: center;
            margin-bottom: 20px;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .status-card {{
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }}
        .status-card.full-width {{
            grid-column: span 2;
        }}
        .status-label {{
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .status-value {{
            font-size: 28px;
            font-weight: bold;
            color: var(--text-primary);
        }}
        .status-value.good {{ color: #10b981; }}
        .status-value.warning {{ color: #f59e0b; }}
        .status-value.critical {{ color: #ef4444; }}
        .status-sub {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 5px;
        }}
        .battery-bar {{
            width: 100%;
            height: 20px;
            background: #333;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .battery-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #34d399);
            transition: width 0.5s ease;
        }}
        .battery-fill.charging {{
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
            animation: pulse 2s infinite;
        }}
        .battery-fill.low {{
            background: linear-gradient(90deg, #ef4444, #f87171);
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        .thermal-indicator {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
        }}
        .thermal-indicator.normal {{ background: rgba(16, 185, 129, 0.2); }}
        .thermal-indicator.elevated {{ background: rgba(245, 158, 11, 0.2); }}
        .thermal-indicator.throttled {{ background: rgba(239, 68, 68, 0.2); }}
        .refresh-time {{
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 15px;
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }}
        }}
    </style>
</head>
<body>
    <h1 class="widget-title">Power & Battery</h1>

    <div class="status-grid">
        <div class="status-card">
            <div class="status-label">Current Charge</div>
            <div class="status-value good" id="currentCharge">--</div>
            <div class="battery-bar">
                <div class="battery-fill" id="batteryFill" style="width: 0%"></div>
            </div>
            <div class="status-sub" id="chargeStatus">Loading...</div>
        </div>

        <div class="status-card">
            <div class="status-label">Battery Health</div>
            <div class="status-value" id="batteryHealth">--</div>
            <div class="status-sub" id="batteryStatus">--</div>
        </div>

        <div class="status-card">
            <div class="status-label">Cycle Count</div>
            <div class="status-value" id="cycleCount">--</div>
            <div class="status-sub" id="cycleStatus">cycles</div>
        </div>

        <div class="status-card">
            <div class="status-label">Power Source</div>
            <div class="status-value" id="powerSource">--</div>
            <div class="status-sub" id="timeRemaining">--</div>
        </div>

        <div class="status-card full-width">
            <div class="status-label">Thermal Status</div>
            <div class="thermal-indicator" id="thermalIndicator">
                <span class="status-value" id="thermalStatus">--</span>
            </div>
            <div class="status-sub" id="thermalDetail">CPU temperature and throttling status</div>
        </div>

        <div class="status-card" id="cpuTempCard" style="display: none;">
            <div class="status-label">CPU Temperature</div>
            <div class="status-value good" id="cpuTemp">--</div>
            <div class="status-sub" id="cpuTempSource">--</div>
        </div>

        <div class="status-card">
            <div class="status-label">Thermal Pressure</div>
            <div class="status-value good" id="thermalPressure">--</div>
            <div class="status-sub">System thermal state</div>
        </div>

        <div class="status-card">
            <div class="status-label">Throttle Events (24h)</div>
            <div class="status-value" id="throttleEvents">--</div>
        </div>
    </div>

    <div class="refresh-time" id="refreshTime">Last updated: --</div>

    <script>
{api_helpers}
{toast_script}
        async function update() {{
            try {{
                const result = await apiFetch('/api/power/status');

                if (!result.ok) {{
                    console.error('Power status fetch failed:', result.error);
                    document.getElementById('batteryHealth').textContent = 'N/A';
                    document.getElementById('batteryStatus').textContent = result.error || 'Unavailable';
                    return;
                }}

                const data = result.data;

                // Battery section - with robust null checks
                const battery = data.battery || {{}};
                const health = Number(battery.health_percentage) || 0;
                const currentCharge = Number(battery.current_charge) || 0;

                // Handle boolean conversion - API may return boolean, string, or number
                const isCharging = safeBool(battery.is_charging);
                const powerSource = battery.power_source || (isCharging ? 'AC Power' : 'Battery');

                // Current charge display
                document.getElementById('currentCharge').textContent = currentCharge + '%';
                document.getElementById('currentCharge').className = 'status-value ' +
                    (currentCharge >= 50 ? 'good' : currentCharge >= 20 ? 'warning' : 'critical');

                const batteryFill = document.getElementById('batteryFill');
                batteryFill.style.width = currentCharge + '%';
                batteryFill.className = 'battery-fill' +
                    (isCharging ? ' charging' : '') +
                    (currentCharge < 20 ? ' low' : '');

                document.getElementById('chargeStatus').textContent = isCharging ? 'Charging' : 'On Battery';

                // Battery health display
                document.getElementById('batteryHealth').textContent = health + '%';
                document.getElementById('batteryHealth').className = 'status-value ' +
                    (health >= 80 ? 'good' : health >= 50 ? 'warning' : 'critical');
                document.getElementById('batteryStatus').textContent = battery.status || 'Unknown';

                // Cycle count
                document.getElementById('cycleCount').textContent = battery.cycle_count || '0';

                // Power source
                document.getElementById('powerSource').textContent = powerSource;
                document.getElementById('powerSource').className = 'status-value ' + (isCharging ? 'good' : '');
                document.getElementById('timeRemaining').textContent = battery.time_remaining || 'N/A';

                // Thermal section - with robust null checks
                const thermal = data.thermal || {{}};
                const thermalStatus = thermal.status || 'Unknown';
                const isThrottled = safeBool(thermal.is_throttled);

                document.getElementById('thermalStatus').textContent = thermalStatus;

                const thermalIndicator = document.getElementById('thermalIndicator');
                thermalIndicator.className = 'thermal-indicator ' +
                    (isThrottled ? 'throttled' : thermalStatus === 'Normal' ? 'normal' : 'elevated');

                document.getElementById('thermalDetail').textContent =
                    isThrottled ? 'System is throttling' : 'System running normally';

                // CPU Temperature display (shown if macmon or osx-cpu-temp is available)
                const cpuTemp = Number(thermal.cpu_temperature) || 0;
                const cpuTempSource = thermal.cpu_temp_source || null;
                const cpuTempCard = document.getElementById('cpuTempCard');

                if (cpuTemp > 0 && cpuTempSource) {{
                    cpuTempCard.style.display = 'block';
                    // Validate cpuTemp is a valid number before calling toFixed
                    const tempDisplay = isNaN(cpuTemp) ? '0.0' : cpuTemp.toFixed(1);
                    document.getElementById('cpuTemp').textContent = tempDisplay + '°C';
                    document.getElementById('cpuTemp').className = 'status-value ' +
                        (cpuTemp < 70 ? 'good' : cpuTemp < 85 ? 'warning' : 'critical');
                    document.getElementById('cpuTempSource').textContent = 'via ' + cpuTempSource;
                }} else {{
                    cpuTempCard.style.display = 'none';
                }}

                // Thermal pressure display - validate string before charAt
                const pressure = String(thermal.thermal_pressure || 'nominal').toLowerCase();
                const pressureDisplay = pressure.length > 0 ?
                    pressure.charAt(0).toUpperCase() + pressure.slice(1) : 'Nominal';

                document.getElementById('thermalPressure').textContent = pressureDisplay;
                document.getElementById('thermalPressure').className = 'status-value ' +
                    (pressure === 'nominal' ? 'good' : pressure === 'moderate' ? 'warning' : 'critical');

                document.getElementById('throttleEvents').textContent = thermal.throttle_events_24h || '0';
                document.getElementById('throttleEvents').className = 'status-value ' +
                    (thermal.throttle_events_24h > 0 ? 'warning' : 'good');

                document.getElementById('refreshTime').textContent =
                    'Last updated: ' + new Date().toLocaleTimeString();

            }} catch (e) {{
                console.error('Power widget update failed:', e);
                ToastManager.error('Failed to update power status');
            }}
        }}

        update();
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.FREQUENT);
        window.addEventListener('beforeunload', () => {{ clearInterval(_ivUpdate); }});
    </script>
</body>
</html>'''
