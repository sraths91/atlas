"""
Network Testing Widget - Tabbed container for CyPerf-inspired network testing

Combines four specialized network testing widgets into a single tabbed view:
- Network Quality: TCP retransmission, DNS, TLS, HTTP metrics
- VoIP Quality: MOS score, UDP jitter, packet loss
- Throughput: Download/upload bandwidth testing
- Connection Rate: CPS, success rate, latency distribution
"""
import logging

logger = logging.getLogger(__name__)


def get_network_testing_widget_html():
    """Generate tabbed Network Testing widget HTML."""
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
    <title>Network Testing - ATLAS Agent</title>
    <style>
{base_styles}
        body {{
            padding: 0;
            margin: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .tab-bar {{
            display: flex;
            background: var(--bg-elevated);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            flex-shrink: 0;
            overflow-x: auto;
        }}
        .tab {{
            padding: 12px 20px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            white-space: nowrap;
            transition: color 0.2s, border-color 0.2s;
            background: none;
            border-top: none;
            border-left: none;
            border-right: none;
            font-family: inherit;
        }}
        .tab:hover {{
            color: var(--text-secondary);
        }}
        .tab.active {{
            color: #22d3ee;
            border-bottom-color: #22d3ee;
        }}
        .tab-content {{
            flex: 1;
            position: relative;
            overflow: hidden;
        }}
        .tab-content iframe {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
            display: none;
        }}
        .tab-content iframe.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <nav class="tab-bar" role="tablist" aria-label="Network Testing">
        <button class="tab active" role="tab" aria-selected="true" aria-controls="frame-quality" id="tab-quality" tabindex="0" data-tab="quality">Network Quality</button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="frame-voip" id="tab-voip" tabindex="-1" data-tab="voip">VoIP Quality</button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="frame-throughput" id="tab-throughput" tabindex="-1" data-tab="throughput">Throughput</button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="frame-connection" id="tab-connection" tabindex="-1" data-tab="connection">Connection Rate</button>
    </nav>
    <div class="tab-content">
        <iframe id="frame-quality" class="active" role="tabpanel" aria-labelledby="tab-quality" src="/widget/network-quality" title="Network Quality" loading="lazy"></iframe>
        <iframe id="frame-voip" role="tabpanel" aria-labelledby="tab-voip" src="/widget/voip-quality" title="VoIP Quality" loading="lazy"></iframe>
        <iframe id="frame-throughput" role="tabpanel" aria-labelledby="tab-throughput" src="/widget/throughput" title="Throughput" loading="lazy"></iframe>
        <iframe id="frame-connection" role="tabpanel" aria-labelledby="tab-connection" src="/widget/connection-rate" title="Connection Rate" loading="lazy"></iframe>
    </div>
    <script>
{api_helpers}
{toast_script}
        const tabs = document.querySelectorAll('.tab');
        const frames = document.querySelectorAll('.tab-content iframe');

        tabs.forEach(tab => {{
            tab.addEventListener('click', () => {{
                tabs.forEach(t => {{
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                    t.setAttribute('tabindex', '-1');
                }});
                frames.forEach(f => f.classList.remove('active'));

                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                tab.setAttribute('tabindex', '0');
                const frameId = 'frame-' + tab.dataset.tab;
                document.getElementById(frameId).classList.add('active');
            }});
        }});

        // Tab keyboard navigation
        document.querySelectorAll('[role="tablist"]').forEach(tablist => {{
            tablist.addEventListener('keydown', (e) => {{
                const tabElements = [...tablist.querySelectorAll('[role="tab"]')];
                const idx = tabElements.indexOf(document.activeElement);
                if (idx < 0) return;
                let target = null;
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {{
                    target = tabElements[(idx + 1) % tabElements.length];
                }} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{
                    target = tabElements[(idx - 1 + tabElements.length) % tabElements.length];
                }} else if (e.key === 'Home') {{
                    target = tabElements[0];
                }} else if (e.key === 'End') {{
                    target = tabElements[tabElements.length - 1];
                }}
                if (target) {{
                    e.preventDefault();
                    target.click();
                    target.focus();
                }}
            }});
        }});
    </script>
</body>
</html>'''


__all__ = ['get_network_testing_widget_html']
