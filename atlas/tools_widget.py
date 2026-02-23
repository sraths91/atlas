"""
Tools Status Widget - Shows available monitoring tools and installation recommendations
"""
import logging

logger = logging.getLogger(__name__)


def get_tools_widget_html():
    """Generate Tools Status widget HTML"""
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
    <title>Monitoring Tools - ATLAS Agent</title>
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
            color: #ffc800;
            text-align: center;
            margin-bottom: 10px;
        }}
        .widget-subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            text-align: center;
            margin-bottom: 20px;
        }}
        .section-header {{
            font-size: 14px;
            font-weight: bold;
            color: var(--text-secondary);
            margin: 20px 0 10px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .tool-card {{
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .tool-info {{
            flex: 1;
        }}
        .tool-name {{
            font-size: 16px;
            font-weight: bold;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .tool-description {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .tool-value {{
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 6px;
            padding: 4px 8px;
            background: rgba(255,200,0,0.1);
            border-radius: 6px;
            display: inline-block;
        }}
        .tool-license {{
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 6px;
        }}
        .license-permissive {{
            color: #10b981;
        }}
        .license-copyleft {{
            color: #f59e0b;
        }}
        .status-badge {{
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: bold;
            white-space: nowrap;
        }}
        .status-installed {{
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }}
        .status-not-installed {{
            background: rgba(107, 114, 128, 0.2);
            color: #9ca3af;
        }}
        .install-btn {{
            background: #ffc800;
            color: #000;
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .install-btn:hover {{
            background: #ffdb4d;
        }}
        .copy-icon {{
            width: 14px;
            height: 14px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: var(--bg-elevated);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }}
        .summary-value {{
            font-size: 28px;
            font-weight: bold;
            color: var(--text-primary);
        }}
        .summary-value.installed {{ color: #10b981; }}
        .summary-value.available {{ color: #f59e0b; }}
        .summary-value.total {{ color: #ffc800; }}
        .summary-label {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .compliance-notice {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin-top: 20px;
            font-size: 11px;
            color: var(--text-secondary);
        }}
        .compliance-notice h4 {{
            color: #f59e0b;
            margin: 0 0 8px 0;
            font-size: 12px;
        }}
        .compliance-notice ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .compliance-notice li {{
            margin: 4px 0;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
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
    <h1 class="widget-title">Monitoring Tools</h1>
    <p class="widget-subtitle">Third-party tools that enhance ATLAS capabilities</p>

    <div class="summary-cards">
        <div class="summary-card">
            <div class="summary-value installed" id="installedCount">-</div>
            <div class="summary-label">Installed</div>
        </div>
        <div class="summary-card">
            <div class="summary-value available" id="availableCount">-</div>
            <div class="summary-label">Available</div>
        </div>
        <div class="summary-card">
            <div class="summary-value total" id="totalCount">-</div>
            <div class="summary-label">Total Tools</div>
        </div>
    </div>

    <div id="toolsContainer">
        <div class="loading">Loading tool information...</div>
    </div>

    <div class="compliance-notice" id="complianceNotice" style="display: none;">
        <h4>GPL Compliance Notice</h4>
        <p>Some tools use copyleft licenses (GPL/LGPL). When bundling for distribution:</p>
        <ul>
            <li>Distribute binaries unmodified</li>
            <li>Include full license text</li>
            <li>Provide source code access</li>
        </ul>
    </div>

    <div class="refresh-time" id="refreshTime">Last updated: --</div>

    <script>
{api_helpers}
{toast_script}
        function escapeHtml(str) {{
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }}

        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                showToast('Copied to clipboard!');
            }}).catch(() => {{
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showToast('Copied to clipboard!');
            }});
        }}

        async function loadTools() {{
            try {{
                const result = await apiFetch('/api/tools/status');
                if (!result.ok) {{
                    document.getElementById('toolsContainer').innerHTML =
                        '<div class="loading">' + escapeHtml(result.error || 'Failed to load tools') + '</div>';
                    return;
                }}
                const data = result.data;

                if (data.error) {{
                    document.getElementById('toolsContainer').innerHTML =
                        '<div class="loading">' + escapeHtml(data.error) + '</div>';
                    return;
                }}

                const tools = data.tools || [];
                const installed = tools.filter(t => t.installed).length;
                const available = tools.filter(t => !t.installed).length;

                document.getElementById('installedCount').textContent = installed;
                document.getElementById('availableCount').textContent = available;
                document.getElementById('totalCount').textContent = tools.length;

                // Separate installed and available tools
                const installedTools = tools.filter(t => t.installed);
                const availableTools = tools.filter(t => !t.installed);

                let html = '';

                if (installedTools.length > 0) {{
                    html += '<div class="section-header">Installed Tools</div>';
                    installedTools.forEach(tool => {{
                        html += renderToolCard(tool);
                    }});
                }}

                if (availableTools.length > 0) {{
                    html += '<div class="section-header">Available to Install</div>';
                    availableTools.forEach(tool => {{
                        html += renderToolCard(tool);
                    }});
                }}

                document.getElementById('toolsContainer').innerHTML = html;

                // Show compliance notice if any GPL tools
                const hasGPL = tools.some(t => t.license_type === 'copyleft');
                document.getElementById('complianceNotice').style.display = hasGPL ? 'block' : 'none';

                document.getElementById('refreshTime').textContent =
                    'Last updated: ' + new Date().toLocaleTimeString();

            }} catch (e) {{
                console.error('Failed to load tools:', e);
                document.getElementById('toolsContainer').innerHTML =
                    '<div class="loading">Failed to load tool information</div>';
            }}
        }}

        function renderToolCard(tool) {{
            const licenseClass = tool.license_type === 'permissive' ? 'license-permissive' : 'license-copyleft';
            const statusClass = tool.installed ? 'status-installed' : 'status-not-installed';
            const statusText = tool.installed ? 'Installed' : 'Not Installed';

            let installBtn = '';
            if (!tool.installed) {{
                installBtn = `
                    <button class="install-btn" onclick="copyToClipboard('brew install ${{escapeHtml(tool.brew_package || tool.name)}}')">
                        <svg class="copy-icon" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                        </svg>
                        Copy Install Command
                    </button>
                `;
            }}

            return `
                <div class="tool-card">
                    <div class="tool-info">
                        <div class="tool-name">
                            ${{escapeHtml(tool.name)}}
                            <span class="tool-license ${{licenseClass}}">(${{escapeHtml(tool.license)}})</span>
                        </div>
                        <div class="tool-description">${{escapeHtml(tool.description)}}</div>
                        <div class="tool-value">${{escapeHtml(tool.value_for_atlas || 'Enhanced monitoring capabilities')}}</div>
                        ${{installBtn}}
                    </div>
                    <span class="status-badge ${{statusClass}}">${{statusText}}</span>
                </div>
            `;
        }}

        loadTools();
        // Refresh every 60 seconds
        const _ivUpdate = setInterval(loadTools, UPDATE_INTERVAL.RARE);

        // Cleanup intervals on page unload
        window.addEventListener('beforeunload', () => {{
            clearInterval(_ivUpdate);
        }});
    </script>
</body>
</html>'''
