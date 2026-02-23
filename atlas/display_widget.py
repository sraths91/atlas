"""
Display & Graphics Widget - Dashboard widget for display and GPU monitoring
"""
import logging

logger = logging.getLogger(__name__)


def get_display_widget_html():
    """Generate Display & Graphics widget HTML"""
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
    <title>Display & Graphics - ATLAS Agent</title>
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
            color: #8b5cf6;
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
            font-size: 24px;
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
        .display-list {{
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .display-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
        }}
        .display-item:last-child {{
            border-bottom: none;
        }}
        .display-info {{
            flex: 1;
        }}
        .display-name {{
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
        }}
        .display-details {{
            font-size: 12px;
            color: var(--text-muted);
        }}
        .display-badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .display-badge.primary {{
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
        }}
        .display-badge.external {{
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
        }}
        .gpu-card {{
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1));
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }}
        .gpu-name {{
            font-size: 18px;
            font-weight: bold;
            color: #a78bfa;
            margin-bottom: 15px;
        }}
        .gpu-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        .gpu-stat {{
            text-align: center;
        }}
        .gpu-stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: var(--text-primary);
        }}
        .gpu-stat-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .vram-bar {{
            width: 100%;
            height: 8px;
            background: #333;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 15px;
        }}
        .vram-fill {{
            height: 100%;
            background: linear-gradient(90deg, #8b5cf6, #3b82f6);
            transition: width 0.5s ease;
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
    <h1 class="widget-title">Display & Graphics</h1>

    <div class="status-grid">
        <div class="status-card">
            <div class="status-label">Connected Displays</div>
            <div class="status-value" id="displayCount">--</div>
        </div>

        <div class="status-card">
            <div class="status-label">Primary Resolution</div>
            <div class="status-value" id="primaryResolution" style="font-size: 18px;">--</div>
        </div>
    </div>

    <div class="display-list" id="displayList">
        <div class="status-label" style="margin-bottom: 10px;">Connected Displays</div>
        <div id="displaysContainer">
            <div class="display-item">
                <div class="display-info">
                    <div class="display-name">Loading...</div>
                    <div class="display-details">Fetching display information</div>
                </div>
            </div>
        </div>
    </div>

    <div class="gpu-card">
        <div class="gpu-name" id="gpuName">Loading GPU...</div>
        <div class="gpu-stats">
            <div class="gpu-stat">
                <div class="gpu-stat-value" id="vramTotal">--</div>
                <div class="gpu-stat-label">VRAM Total</div>
            </div>
            <div class="gpu-stat">
                <div class="gpu-stat-value" id="vramUsed">--</div>
                <div class="gpu-stat-label">VRAM Used</div>
            </div>
            <div class="gpu-stat">
                <div class="gpu-stat-value" id="gpuTemp">--</div>
                <div class="gpu-stat-label">Temperature</div>
            </div>
        </div>
        <div class="vram-bar">
            <div class="vram-fill" id="vramFill" style="width: 0%"></div>
        </div>
        <div class="status-sub" style="text-align: center; margin-top: 8px;" id="gpuType">--</div>
    </div>

    <div class="refresh-time" id="refreshTime">Last updated: --</div>

    <script>
{api_helpers}
{toast_script}
        async function update() {{
            try {{
                const result = await apiFetch('/api/display/status');
                if (!result.ok) {{
                    document.getElementById('displayCount').textContent = 'N/A';
                    document.getElementById('primaryResolution').textContent = result.error;
                    return;
                }}
                const data = result.data;

                // Display section
                const display = data.display || {{}};
                document.getElementById('displayCount').textContent = display.display_count || 0;
                document.getElementById('displayCount').className = 'status-value ' +
                    (display.display_count > 0 ? 'good' : 'warning');

                document.getElementById('primaryResolution').textContent =
                    display.primary_resolution || 'Unknown';

                // Render display list
                const displays = display.displays || [];
                const container = document.getElementById('displaysContainer');

                if (displays.length > 0) {{
                    container.innerHTML = displays.map((d, i) => `
                        <div class="display-item">
                            <div class="display-info">
                                <div class="display-name">${{d.name || 'Display ' + (i + 1)}}</div>
                                <div class="display-details">
                                    ${{d.resolution}} @ ${{d.refresh_rate || '60'}}Hz | ${{d.connection || 'Unknown'}}
                                </div>
                            </div>
                            <span class="display-badge ${{d.type === 'Built-in' ? 'primary' : 'external'}}">
                                ${{d.type || 'External'}}
                            </span>
                        </div>
                    `).join('');
                }} else {{
                    container.innerHTML = `
                        <div class="display-item">
                            <div class="display-info">
                                <div class="display-name">No displays detected</div>
                                <div class="display-details">Display information unavailable</div>
                            </div>
                        </div>
                    `;
                }}

                // GPU section
                const gpu = data.gpu || {{}};
                document.getElementById('gpuName').textContent = gpu.gpu_name || 'Unknown GPU';

                const vramTotal = gpu.vram_total_mb || 0;
                const vramUsed = gpu.vram_used_mb || 0;

                document.getElementById('vramTotal').textContent =
                    vramTotal >= 1024 ? (vramTotal / 1024).toFixed(1) + ' GB' : vramTotal + ' MB';
                document.getElementById('vramUsed').textContent =
                    vramUsed >= 1024 ? (vramUsed / 1024).toFixed(1) + ' GB' : vramUsed + ' MB';

                const gpuTemp = gpu.gpu_temp_celsius || 0;
                document.getElementById('gpuTemp').textContent =
                    gpuTemp > 0 ? gpuTemp.toFixed(0) + 'C' : 'N/A';

                // VRAM bar
                const vramPercent = vramTotal > 0 ? (vramUsed / vramTotal) * 100 : 0;
                document.getElementById('vramFill').style.width = vramPercent + '%';

                // GPU type
                document.getElementById('gpuType').textContent =
                    gpu.has_discrete_gpu ? 'Discrete GPU' : 'Integrated GPU (Unified Memory)';

                document.getElementById('refreshTime').textContent =
                    'Last updated: ' + new Date().toLocaleTimeString();

            }} catch (e) {{
                console.error('Display widget update failed:', e);
                ToastManager.error('Failed to update display info');
            }}
        }}

        update();
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.STANDARD);
        window.addEventListener('beforeunload', () => {{ clearInterval(_ivUpdate); }});
    </script>
</body>
</html>'''
