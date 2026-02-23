"""
Peripherals Widget - Dashboard widget for Bluetooth, USB, and Thunderbolt device monitoring
"""
import logging

logger = logging.getLogger(__name__)


def get_peripherals_widget_html():
    """Generate Peripherals widget HTML"""
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
    <title>Peripherals - ATLAS Agent</title>
    <style>
{base_styles}
        body {{
            padding: 20px;
            max-width: 700px;
            margin: 0 auto;
        }}
        .widget-title {{
            font-size: 24px;
            font-weight: bold;
            color: #f59e0b;
            text-align: center;
            margin-bottom: 20px;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .status-card {{
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
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
        .status-sub {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 5px;
        }}
        .device-section {{
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .section-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}
        .section-icon {{
            font-size: 20px;
        }}
        .section-title {{
            font-weight: 600;
            color: var(--text-primary);
        }}
        .section-count {{
            margin-left: auto;
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
        }}
        .device-list {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .device-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: var(--bg-secondary);
            border-radius: 8px;
        }}
        .device-info {{
            flex: 1;
        }}
        .device-name {{
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: 3px;
        }}
        .device-details {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .device-status {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }}
        .device-status.connected {{
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }}
        .device-status.disconnected {{
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }}
        .device-status.paired {{
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
        }}
        .battery-indicator {{
            display: flex;
            align-items: center;
            gap: 5px;
            margin-left: 10px;
        }}
        .battery-bar {{
            width: 30px;
            height: 12px;
            background: #333;
            border-radius: 3px;
            overflow: hidden;
        }}
        .battery-fill {{
            height: 100%;
            background: #10b981;
            transition: width 0.3s ease;
        }}
        .battery-fill.low {{
            background: #ef4444;
        }}
        .battery-fill.medium {{
            background: #f59e0b;
        }}
        .battery-text {{
            font-size: 11px;
            color: var(--text-muted);
            min-width: 35px;
        }}
        .empty-state {{
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-style: italic;
        }}
        .refresh-time {{
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 15px;
        }}
    </style>
</head>
<body>
    <h1 class="widget-title">Peripherals</h1>

    <div class="status-grid">
        <div class="status-card">
            <div class="status-label">Bluetooth</div>
            <div class="status-value" id="bluetoothCount">--</div>
            <div class="status-sub">devices</div>
        </div>

        <div class="status-card">
            <div class="status-label">USB</div>
            <div class="status-value" id="usbCount">--</div>
            <div class="status-sub">devices</div>
        </div>

        <div class="status-card">
            <div class="status-label">Thunderbolt</div>
            <div class="status-value" id="thunderboltCount">--</div>
            <div class="status-sub">devices</div>
        </div>
    </div>

    <div class="device-section">
        <div class="section-header">
            <span class="section-icon">Bluetooth</span>
            <span class="section-title">Bluetooth Devices</span>
            <span class="section-count" id="btSectionCount">0</span>
        </div>
        <div class="device-list" id="bluetoothList">
            <div class="empty-state">Loading...</div>
        </div>
    </div>

    <div class="device-section">
        <div class="section-header">
            <span class="section-icon">USB</span>
            <span class="section-title">USB Devices</span>
            <span class="section-count" id="usbSectionCount">0</span>
        </div>
        <div class="device-list" id="usbList">
            <div class="empty-state">Loading...</div>
        </div>
    </div>

    <div class="device-section">
        <div class="section-header">
            <span class="section-icon">TB</span>
            <span class="section-title">Thunderbolt Devices</span>
            <span class="section-count" id="tbSectionCount">0</span>
        </div>
        <div class="device-list" id="thunderboltList">
            <div class="empty-state">Loading...</div>
        </div>
    </div>

    <div class="refresh-time" id="refreshTime">Last updated: --</div>

    <script>
{api_helpers}
{toast_script}
        function escapeHtml(str) {{
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }}

        function getBatteryClass(level) {{
            if (level < 20) return 'low';
            if (level < 50) return 'medium';
            return '';
        }}

        function renderDeviceList(devices, containerId, type) {{
            const container = document.getElementById(containerId);

            if (!devices || devices.length === 0) {{
                container.innerHTML = '<div class="empty-state">No ' + escapeHtml(type) + ' devices connected</div>';
                return;
            }}

            container.innerHTML = devices.map(d => {{
                const batteryHtml = d.battery_level !== undefined && d.battery_level !== null ? `
                    <div class="battery-indicator">
                        <div class="battery-bar">
                            <div class="battery-fill ${{getBatteryClass(d.battery_level)}}" style="width: ${{d.battery_level}}%"></div>
                        </div>
                        <span class="battery-text">${{d.battery_level}}%</span>
                    </div>
                ` : '';

                const isConnected = safeBool(d.connected);
                const isPaired = safeBool(d.paired);
                const statusClass = isConnected ? 'connected' : (isPaired ? 'paired' : 'disconnected');
                const statusText = isConnected ? 'Connected' : (isPaired ? 'Paired' : 'Disconnected');

                return `
                    <div class="device-item">
                        <div class="device-info">
                            <div class="device-name">${{escapeHtml(d.name || 'Unknown Device')}}</div>
                            <div class="device-details">
                                ${{escapeHtml(d.type || type)}} ${{d.vendor ? '| ' + escapeHtml(d.vendor) : ''}} ${{d.address ? '| ' + escapeHtml(d.address) : ''}}
                            </div>
                        </div>
                        ${{batteryHtml}}
                        <span class="device-status ${{statusClass}}">${{statusText}}</span>
                    </div>
                `;
            }}).join('');
        }}

        async function update() {{
            try {{
                const result = await apiFetch('/api/peripherals/devices');

                if (!result.ok) {{
                    console.error('Peripherals fetch failed:', result.error);
                    document.getElementById('bluetoothCount').textContent = 'N/A';
                    ToastManager.error('Failed to load peripheral devices');
                    return;
                }}

                const data = result.data;

                // Bluetooth
                const bluetooth = data.bluetooth || {{}};
                const btDevices = bluetooth.devices || [];
                document.getElementById('bluetoothCount').textContent = btDevices.length;
                document.getElementById('btSectionCount').textContent = btDevices.length;
                renderDeviceList(btDevices, 'bluetoothList', 'Bluetooth');

                // USB
                const usb = data.usb || {{}};
                const usbDevices = usb.devices || [];
                document.getElementById('usbCount').textContent = usbDevices.length;
                document.getElementById('usbSectionCount').textContent = usbDevices.length;
                renderDeviceList(usbDevices, 'usbList', 'USB');

                // Thunderbolt
                const thunderbolt = data.thunderbolt || {{}};
                const tbDevices = thunderbolt.devices || [];
                document.getElementById('thunderboltCount').textContent = tbDevices.length;
                document.getElementById('tbSectionCount').textContent = tbDevices.length;
                renderDeviceList(tbDevices, 'thunderboltList', 'Thunderbolt');

                document.getElementById('refreshTime').textContent =
                    'Last updated: ' + new Date().toLocaleTimeString();

            }} catch (e) {{
                console.error('Peripherals widget update failed:', e);
                ToastManager.error('Failed to update peripherals');
            }}
        }}

        update();
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.STANDARD);
        window.addEventListener('beforeunload', () => {{ clearInterval(_ivUpdate); }});
    </script>
</body>
</html>'''
