"""
Network Path Analysis Widget - MTR-style traceroute visualization
Shows network path with per-hop latency and packet loss statistics.
"""
import logging

logger = logging.getLogger(__name__)


def get_network_path_widget_html():
    """Generate Network Path Analysis widget HTML"""
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
    <title>Network Path Analysis - ATLAS Agent</title>
    <style>
{base_styles}
        body {{
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }}
        .widget-title {{
            font-size: 24px;
            font-weight: bold;
            color: #ffc800;
            text-align: center;
            margin-bottom: 5px;
        }}
        .widget-subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            text-align: center;
            margin-bottom: 20px;
        }}
        .target-input {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .target-input input {{
            flex: 1;
            padding: 12px 15px;
            border-radius: 8px;
            border: 1px solid #333;
            background: var(--bg-elevated);
            color: var(--text-primary);
            font-size: 14px;
        }}
        .target-input input:focus {{
            outline: none;
            border-color: #ffc800;
        }}
        .trace-btn {{
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            background: #ffc800;
            color: #000;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .trace-btn:hover {{
            background: #ffdb4d;
        }}
        .trace-btn:disabled {{
            background: #666;
            cursor: not-allowed;
        }}
        .quick-targets {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .quick-target {{
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #444;
            background: transparent;
            color: var(--text-secondary);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .quick-target:hover {{
            border-color: #ffc800;
            color: #ffc800;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: var(--bg-elevated);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }}
        .summary-value {{
            font-size: 24px;
            font-weight: bold;
            color: var(--text-primary);
        }}
        .summary-value.good {{ color: #10b981; }}
        .summary-value.warning {{ color: #ffc800; }}
        .summary-value.critical {{ color: #ff3000; }}
        .summary-label {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .hops-container {{
            background: var(--bg-elevated);
            border-radius: 12px;
            overflow: hidden;
        }}
        .hop-header {{
            display: grid;
            grid-template-columns: 40px 1fr 80px 80px 80px 80px 60px;
            padding: 12px 15px;
            background: rgba(255,255,255,0.05);
            font-size: 11px;
            font-weight: bold;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .hop-row {{
            display: grid;
            grid-template-columns: 40px 1fr 80px 80px 80px 80px 60px;
            padding: 10px 15px;
            border-top: 1px solid rgba(255,255,255,0.05);
            font-size: 13px;
            align-items: center;
        }}
        .hop-row:hover {{
            background: rgba(255,255,255,0.03);
        }}
        .hop-num {{
            color: var(--text-muted);
            font-weight: bold;
        }}
        .hop-host {{
            display: flex;
            flex-direction: column;
        }}
        .hop-hostname {{
            color: var(--text-primary);
            font-weight: 500;
        }}
        .hop-ip {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .hop-metric {{
            text-align: right;
            font-family: monospace;
        }}
        .hop-metric.good {{ color: #10b981; }}
        .hop-metric.warning {{ color: #ffc800; }}
        .hop-metric.critical {{ color: #ff3000; }}
        .loss-bar {{
            width: 100%;
            height: 4px;
            background: #333;
            border-radius: 2px;
            overflow: hidden;
            margin-top: 4px;
        }}
        .loss-fill {{
            height: 100%;
            background: #10b981;
            transition: width 0.3s;
        }}
        .loss-fill.warning {{ background: #ffc800; }}
        .loss-fill.critical {{ background: #ff3000; }}
        .problem-hops {{
            margin-top: 20px;
            padding: 15px;
            background: rgba(255, 48, 0, 0.1);
            border: 1px solid rgba(255, 48, 0, 0.3);
            border-radius: 8px;
        }}
        .problem-hops h4 {{
            color: #ff3000;
            margin: 0 0 10px 0;
            font-size: 14px;
        }}
        .problem-item {{
            font-size: 12px;
            color: var(--text-secondary);
            margin: 6px 0;
            padding-left: 15px;
            position: relative;
        }}
        .problem-item::before {{
            content: "!";
            position: absolute;
            left: 0;
            color: #ff3000;
            font-weight: bold;
        }}
        .loading {{
            text-align: center;
            padding: 60px;
            color: var(--text-muted);
        }}
        .loading-spinner {{
            width: 40px;
            height: 40px;
            border: 3px solid #333;
            border-top-color: #ffc800;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }}
        .method-badge {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            background: rgba(16, 185, 129, 0.15);
            border-radius: 4px;
            font-size: 10px;
            color: #10b981;
            margin-top: 15px;
        }}
        .refresh-time {{
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 15px;
        }}
        .no-data {{
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <h1 class="widget-title">Network Path Analysis</h1>
    <p class="widget-subtitle">MTR-style traceroute with per-hop statistics</p>

    <div class="target-input">
        <input type="text" id="targetInput" placeholder="Enter hostname or IP (e.g., google.com, 8.8.8.8)" value="8.8.8.8">
        <button class="trace-btn" id="traceBtn" onclick="runTrace()">Trace Route</button>
    </div>

    <div class="quick-targets">
        <button class="quick-target" onclick="setTarget('8.8.8.8')">Google DNS</button>
        <button class="quick-target" onclick="setTarget('1.1.1.1')">Cloudflare</button>
        <button class="quick-target" onclick="setTarget('google.com')">google.com</button>
        <button class="quick-target" onclick="setTarget('amazon.com')">amazon.com</button>
        <button class="quick-target" onclick="setTarget('microsoft.com')">microsoft.com</button>
    </div>

    <div class="summary-cards" id="summaryCards" style="display: none;">
        <div class="summary-card">
            <div class="summary-value" id="hopCount">-</div>
            <div class="summary-label">Hops</div>
        </div>
        <div class="summary-card">
            <div class="summary-value" id="avgLatency">-</div>
            <div class="summary-label">Avg Latency</div>
        </div>
        <div class="summary-card">
            <div class="summary-value" id="maxLatency">-</div>
            <div class="summary-label">Max Latency</div>
        </div>
        <div class="summary-card">
            <div class="summary-value" id="problemCount">-</div>
            <div class="summary-label">Issues</div>
        </div>
    </div>

    <div id="resultsContainer">
        <div class="no-data">Enter a target and click "Trace Route" to analyze the network path</div>
    </div>

    <div class="method-badge" id="methodBadge" style="display: none;">
        <span>Method:</span>
        <span id="traceMethod">native</span>
    </div>

    <div class="refresh-time" id="refreshTime" style="display: none;">Completed: --</div>

    <script>
{api_helpers}
{toast_script}
        let isTracing = false;

        function setTarget(target) {{
            document.getElementById('targetInput').value = target;
            runTrace();
        }}

        async function runTrace() {{
            if (isTracing) return;

            const target = document.getElementById('targetInput').value.trim();
            if (!target) {{
                showToast('Please enter a target hostname or IP');
                return;
            }}

            isTracing = true;
            const btn = document.getElementById('traceBtn');
            btn.disabled = true;
            btn.textContent = 'Tracing...';

            document.getElementById('summaryCards').style.display = 'none';
            document.getElementById('resultsContainer').innerHTML = `
                <div class="loading">
                    <div class="loading-spinner"></div>
                    <div>Tracing route to ${{target}}...</div>
                    <div style="font-size: 11px; margin-top: 5px; color: #666;">This may take 20-30 seconds</div>
                </div>
            `;

            try {{
                const result = await apiFetch('/api/traceroute?target=' + encodeURIComponent(target) + '&count=5');
                if (!result.ok) {{
                    document.getElementById('resultsContainer').innerHTML =
                        '<div class="no-data">' + (result.error || 'Trace request failed') + '</div>';
                    return;
                }}
                const data = result.data;

                if (data.error) {{
                    document.getElementById('resultsContainer').innerHTML =
                        '<div class="no-data">' + data.error + '</div>';
                    return;
                }}

                renderResults(data);

            }} catch (e) {{
                console.error('Trace failed:', e);
                document.getElementById('resultsContainer').innerHTML =
                    '<div class="no-data">Failed to trace route. Please try again.</div>';
            }} finally {{
                isTracing = false;
                btn.disabled = false;
                btn.textContent = 'Trace Route';
            }}
        }}

        function renderResults(data) {{
            const hops = data.hops || [];

            if (hops.length === 0) {{
                document.getElementById('resultsContainer').innerHTML =
                    '<div class="no-data">No hops found. The target may be unreachable.</div>';
                return;
            }}

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
            document.getElementById('summaryCards').style.display = 'grid';
            document.getElementById('hopCount').textContent = hops.length;

            const avgEl = document.getElementById('avgLatency');
            avgEl.textContent = avgLatency.toFixed(1) + 'ms';
            avgEl.className = 'summary-value ' + getLatencyClass(avgLatency);

            const maxEl = document.getElementById('maxLatency');
            maxEl.textContent = maxLatency.toFixed(1) + 'ms';
            maxEl.className = 'summary-value ' + getLatencyClass(maxLatency);

            const probEl = document.getElementById('problemCount');
            probEl.textContent = problemCount;
            probEl.className = 'summary-value ' + (problemCount > 0 ? 'warning' : 'good');

            // Render hops table
            let html = `
                <div class="hops-container">
                    <div class="hop-header">
                        <div>#</div>
                        <div>Host</div>
                        <div style="text-align: right;">Loss</div>
                        <div style="text-align: right;">Sent</div>
                        <div style="text-align: right;">Avg</div>
                        <div style="text-align: right;">Best</div>
                        <div style="text-align: right;">Worst</div>
                    </div>
            `;

            hops.forEach(hop => {{
                const lossClass = hop.loss_pct > 20 ? 'critical' : hop.loss_pct > 5 ? 'warning' : 'good';
                const latClass = getLatencyClass(hop.avg_ms);
                const hostname = hop.hostname !== hop.ip ? hop.hostname : '';

                html += `
                    <div class="hop-row">
                        <div class="hop-num">${{hop.hop}}</div>
                        <div class="hop-host">
                            <span class="hop-hostname">${{hop.ip === '*' ? '* * *' : (hostname || hop.ip)}}</span>
                            ${{hostname && hop.ip !== '*' ? '<span class="hop-ip">' + hop.ip + '</span>' : ''}}
                        </div>
                        <div class="hop-metric ${{lossClass}}">${{hop.loss_pct.toFixed(1)}}%</div>
                        <div class="hop-metric">${{hop.sent}}</div>
                        <div class="hop-metric ${{latClass}}">${{hop.avg_ms > 0 ? hop.avg_ms.toFixed(1) : '-'}}</div>
                        <div class="hop-metric">${{hop.min_ms > 0 ? hop.min_ms.toFixed(1) : '-'}}</div>
                        <div class="hop-metric">${{hop.max_ms > 0 ? hop.max_ms.toFixed(1) : '-'}}</div>
                    </div>
                `;
            }});

            html += '</div>';

            // Render problem hops if any
            if (data.problem_hops && data.problem_hops.length > 0) {{
                html += '<div class="problem-hops"><h4>Issues Detected</h4>';
                data.problem_hops.forEach(p => {{
                    html += `<div class="problem-item">Hop ${{p.hop}} (${{p.ip}}): ${{p.issues.join(', ')}}</div>`;
                }});
                html += '</div>';
            }}

            document.getElementById('resultsContainer').innerHTML = html;

            // Show method and time
            document.getElementById('methodBadge').style.display = 'inline-flex';
            document.getElementById('traceMethod').textContent = data.method || 'native';
            document.getElementById('refreshTime').style.display = 'block';
            document.getElementById('refreshTime').textContent = 'Completed: ' + new Date().toLocaleTimeString() +
                ' (' + (data.total_time_ms / 1000).toFixed(1) + 's)';
        }}

        function getLatencyClass(ms) {{
            if (ms <= 0) return '';
            if (ms < 50) return 'good';
            if (ms < 100) return 'warning';
            return 'critical';
        }}

        // Allow Enter key to trigger trace
        document.getElementById('targetInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') runTrace();
        }});
    </script>
</body>
</html>'''
