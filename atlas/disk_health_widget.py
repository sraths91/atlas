"""
Disk Health Widget - Compact dashboard widget for SMART disk monitoring
"""
import logging

logger = logging.getLogger(__name__)


def get_disk_health_widget_html():
    """Generate Disk Health widget HTML"""
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
    <title>Disk Health - ATLAS Agent</title>
    <style>
{base_styles}
        body {{
            padding: 16px;
            margin: 0;
            overflow-y: auto;
        }}
        .widget-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }}
        .widget-title {{
            font-size: 15px;
            font-weight: 700;
            color: #ffc800;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .smartctl-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .smartctl-indicator.active {{
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
        }}
        .smartctl-indicator.unavailable {{
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
        }}
        .disk-card {{
            background: rgba(255,255,255,0.04);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
        }}
        .disk-card:last-of-type {{
            margin-bottom: 0;
        }}
        .disk-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }}
        .disk-name {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.2;
        }}
        .disk-model {{
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 2px;
        }}
        .health-badge {{
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 700;
            white-space: nowrap;
            flex-shrink: 0;
            margin-left: 8px;
        }}
        .health-excellent {{ background: #10b981; color: #000; }}
        .health-good {{ background: #8bc34a; color: #000; }}
        .health-fair {{ background: #f59e0b; color: #000; }}
        .health-poor {{ background: #ef4444; color: #fff; }}
        .health-critical {{ background: #dc2626; color: #fff; animation: pulse 1s infinite; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.6; }}
        }}
        .health-bar {{
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 10px;
        }}
        .health-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #34d399);
            transition: width 0.5s ease;
            border-radius: 2px;
        }}
        .health-fill.warning {{
            background: linear-gradient(90deg, #f59e0b, #fbbf24);
        }}
        .health-fill.critical {{
            background: linear-gradient(90deg, #ef4444, #f87171);
        }}
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            margin-bottom: 8px;
        }}
        .metric {{
            text-align: center;
            padding: 6px 4px;
            background: rgba(255,255,255,0.03);
            border-radius: 6px;
        }}
        .metric-value {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }}
        .metric-value.good {{ color: #10b981; }}
        .metric-value.warning {{ color: #f59e0b; }}
        .metric-value.critical {{ color: #ef4444; }}
        .metric-label {{
            font-size: 8px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0;
        }}
        .detail-item {{
            display: flex;
            justify-content: space-between;
            padding: 4px 6px;
            font-size: 11px;
        }}
        .detail-item:nth-child(odd) {{
            border-right: 1px solid rgba(255,255,255,0.05);
            padding-right: 10px;
        }}
        .detail-item:nth-child(even) {{
            padding-left: 10px;
        }}
        .detail-label {{
            color: var(--text-muted);
        }}
        .detail-value {{
            font-weight: 500;
            color: var(--text-primary);
        }}
        .no-disks {{
            text-align: center;
            padding: 30px 10px;
            color: var(--text-muted);
            font-size: 12px;
        }}
        .refresh-time {{
            text-align: center;
            font-size: 9px;
            color: var(--text-muted);
            margin-top: 8px;
            opacity: 0.7;
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
    <div class="widget-header">
        <div class="widget-title">
            <span>Disk Health</span>
        </div>
        <div class="smartctl-indicator" id="smartctlBadge" style="display: none;">
            <span id="smartctlStatus">SMART</span>
        </div>
    </div>

    <div id="diskContainer">
        <div class="no-disks">Loading disk information...</div>
    </div>

    <div class="refresh-time" id="refreshTime">Updated: --</div>

    <script>
{api_helpers}
{toast_script}
        function escapeHtml(str) {{
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }}

        function fmtBytes(gb) {{
            return gb >= 1000 ? (gb / 1000).toFixed(1) + ' TB' : gb.toFixed(0) + ' GB';
        }}

        function fmtHours(h) {{
            if (h >= 8760) return (h / 8760).toFixed(1) + 'y';
            if (h >= 720) return (h / 720).toFixed(0) + 'mo';
            if (h >= 24) return (h / 24).toFixed(0) + 'd';
            return h + 'h';
        }}

        function healthClass(p) {{
            if (p >= 90) return 'excellent';
            if (p >= 80) return 'good';
            if (p >= 60) return 'fair';
            if (p >= 40) return 'poor';
            return 'critical';
        }}

        function valClass(v, good, warn) {{
            if (v <= good) return 'good';
            if (v <= warn) return 'warning';
            return 'critical';
        }}

        async function update() {{
            try {{
                const result = await apiFetch('/api/disk/status');
                if (!result.ok) {{
                    document.getElementById('diskContainer').innerHTML =
                        '<div class="no-disks">' + escapeHtml(result.error) + '</div>';
                    return;
                }}
                const data = result.data;

                if (data.error) {{
                    document.getElementById('diskContainer').innerHTML =
                        '<div class="no-disks">' + escapeHtml(data.error) + '</div>';
                    return;
                }}

                const disks = data.disks || [];

                if (disks.length === 0) {{
                    document.getElementById('diskContainer').innerHTML =
                        '<div class="no-disks">No disks detected</div>';
                    return;
                }}

                let html = '';

                disks.forEach(disk => {{
                    // Validate disk object has required fields with safe defaults
                    const healthPct = Number(disk.health_percentage) || 0;
                    const temperature = Number(disk.temperature_c) || 0;
                    const wearLevel = Number(disk.wear_leveling) || 0;
                    const powerOnHours = Number(disk.power_on_hours) || 0;
                    const bytesWritten = Number(disk.total_bytes_written_gb) || 0;

                    const hc = healthClass(healthPct);
                    const barClass = healthPct < 60 ? 'critical' :
                                     healthPct < 80 ? 'warning' : '';

                    const tempVal = temperature > 0 ? temperature + '°' : '--';
                    const tempClass = temperature > 50 ? 'critical' : temperature > 40 ? 'warning' : 'good';
                    const healthValClass = hc === 'critical' || hc === 'poor' ? 'critical' : hc === 'fair' ? 'warning' : 'good';
                    const wearClass = wearLevel < 50 ? 'critical' : wearLevel < 80 ? 'warning' : 'good';

                    html += `
                        <div class="disk-card">
                            <div class="disk-top">
                                <div>
                                    <div class="disk-name">${{escapeHtml(disk.disk_identifier || 'Unknown')}}</div>
                                    <div class="disk-model">${{escapeHtml(disk.model || 'Unknown Model')}}</div>
                                </div>
                                <span class="health-badge health-${{hc}}">${{escapeHtml(disk.health_label || 'Unknown')}}</span>
                            </div>

                            <div class="health-bar">
                                <div class="health-fill ${{barClass}}" style="width: ${{healthPct}}%"></div>
                            </div>

                            <div class="metrics-row">
                                <div class="metric">
                                    <div class="metric-value ${{healthValClass}}">${{healthPct}}%</div>
                                    <div class="metric-label">Health</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value ${{tempClass}}">${{tempVal}}</div>
                                    <div class="metric-label">Temp</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value">${{powerOnHours > 0 ? fmtHours(powerOnHours) : '--'}}</div>
                                    <div class="metric-label">Power On</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value ${{wearClass}}">${{wearLevel}}%</div>
                                    <div class="metric-label">Wear</div>
                                </div>
                            </div>

                            <div class="detail-grid">
                                <div class="detail-item">
                                    <span class="detail-label">SMART</span>
                                    <span class="detail-value" style="color: ${{disk.smart_status === 'PASSED' ? '#10b981' : '#ef4444'}}">${{escapeHtml(disk.smart_status || 'N/A')}}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Written</span>
                                    <span class="detail-value">${{bytesWritten > 0 ? fmtBytes(bytesWritten) : '--'}}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Cycles</span>
                                    <span class="detail-value">${{disk.power_cycle_count || '--'}}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Errors</span>
                                    <span class="detail-value" style="color: ${{(disk.media_errors || 0) > 0 ? '#ef4444' : '#10b981'}}">${{disk.media_errors || 0}}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }});

                document.getElementById('diskContainer').innerHTML = html;

                // Show smartctl status
                const badge = document.getElementById('smartctlBadge');
                badge.style.display = 'inline-flex';
                if (data.smartctl_available) {{
                    badge.className = 'smartctl-indicator active';
                    document.getElementById('smartctlStatus').textContent = 'SMART';
                }} else {{
                    badge.className = 'smartctl-indicator unavailable';
                    document.getElementById('smartctlStatus').textContent = 'NO SMART';
                }}

                document.getElementById('refreshTime').textContent =
                    'Updated: ' + new Date().toLocaleTimeString();

            }} catch (e) {{
                console.error('Disk health widget update failed:', e);
                document.getElementById('diskContainer').innerHTML =
                    '<div class="no-disks">Failed to load disk data</div>';
            }}
        }}

        update();
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.STANDARD);
        window.addEventListener('beforeunload', () => {{ clearInterval(_ivUpdate); }});
    </script>
</body>
</html>'''
