"""
Machine detail page HTML for fleet server

Enhanced with modern UX/UI best practices:
- Accessibility (ARIA labels, focus states, screen reader support)
- Toast notifications instead of alerts
- Responsive design with mobile breakpoints
- CSS custom properties design system
- Improved color contrast (WCAG AA compliant)
"""

from atlas.fleet_login_page import get_base_styles, get_toast_script


def get_machine_detail_html(machine_id: str) -> str:
    """Generate machine detail/history page HTML"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Machine detail and monitoring for {machine_id}">
    <meta name="theme-color" content="#0a0a0a">
    <title>Machine Detail - {machine_id}</title>
    <style>
        {get_base_styles()}

        /* ========================================
           Machine Detail Page Specific Styles
           ======================================== */
        .page-container {{
            padding: var(--space-lg);
            max-width: 1600px;
            margin: 0 auto;
        }}

        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-xl);
            padding-bottom: var(--space-lg);
            border-bottom: 2px solid var(--color-primary);
            flex-wrap: wrap;
            gap: var(--space-md);
        }}

        .header-left {{
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
        }}

        h1 {{
            color: var(--color-primary);
            font-size: var(--font-size-2xl);
            margin: 0;
        }}

        .header-actions {{
            display: flex;
            gap: var(--space-md);
            align-items: center;
            flex-wrap: wrap;
        }}

        .back-link {{
            color: var(--color-primary);
            text-decoration: none;
            font-size: var(--font-size-lg);
            display: inline-flex;
            align-items: center;
            gap: var(--space-xs);
            transition: color var(--transition-fast);
        }}

        .back-link:hover {{
            text-decoration: underline;
        }}

        .back-link:focus-visible {{
            outline: 2px solid var(--color-primary);
            outline-offset: 2px;
        }}

        .export-btn {{
            background: var(--color-primary);
            color: var(--text-on-primary);
            border: none;
            padding: 10px 20px;
            border-radius: var(--radius-md);
            font-size: var(--font-size-sm);
            font-weight: bold;
            cursor: pointer;
            transition: all var(--transition-normal);
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            text-decoration: none;
        }}

        .export-btn:hover {{
            background: var(--color-primary-hover);
            transform: translateY(-2px);
            box-shadow: var(--shadow-glow);
        }}

        .export-btn:focus-visible {{
            outline: 2px solid var(--text-primary);
            outline-offset: 2px;
        }}

        .status-badge {{
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-full);
            font-size: var(--font-size-sm);
            font-weight: bold;
            text-transform: uppercase;
        }}

        .status-online {{
            background: var(--color-primary);
            color: var(--bg-primary);
        }}

        .status-warning {{
            background: var(--color-warning);
            color: var(--bg-primary);
        }}

        .status-offline {{
            background: var(--color-error);
            color: var(--text-primary);
        }}

        /* Info Grid */
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: var(--space-lg);
            margin-bottom: var(--space-xl);
        }}

        .info-card {{
            background: var(--bg-secondary);
            border: 2px solid #333;
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
        }}

        .info-card h3 {{
            color: var(--color-primary);
            margin-bottom: var(--space-md);
            font-size: var(--font-size-lg);
        }}

        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: var(--space-sm) 0;
            border-bottom: 1px solid #333;
        }}

        .info-row:last-child {{
            border-bottom: none;
        }}

        .info-label {{
            color: var(--text-secondary);
        }}

        .info-value {{
            color: var(--text-primary);
            font-weight: bold;
        }}

        /* Metrics Section */
        .section {{
            margin-bottom: var(--space-xl);
        }}

        .section h2 {{
            color: var(--color-primary);
            margin-bottom: var(--space-lg);
            font-size: var(--font-size-xl);
        }}

        .metric-card {{
            background: var(--bg-secondary);
            border: 2px solid #333;
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            margin-bottom: var(--space-lg);
        }}

        .metric-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-sm);
        }}

        .metric-name {{
            font-size: var(--font-size-lg);
            font-weight: bold;
        }}

        .metric-value {{
            font-size: var(--font-size-xl);
            color: var(--color-primary);
        }}

        .metric-bar {{
            width: 100%;
            height: 12px;
            background: #333;
            border-radius: 6px;
            overflow: hidden;
        }}

        .metric-fill {{
            height: 100%;
            transition: width 0.5s ease;
            border-radius: 6px;
        }}

        .metric-fill.cpu {{
            background: linear-gradient(90deg, var(--color-primary), var(--color-primary-hover));
        }}

        .metric-fill.memory {{
            background: linear-gradient(90deg, #00ffff, #0099ff);
        }}

        .metric-fill.disk {{
            background: linear-gradient(90deg, #ff00ff, #cc00cc);
        }}

        .metric-fill.high {{
            background: linear-gradient(90deg, var(--color-error), #cc0000) !important;
        }}

        /* Actions Section */
        .actions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: var(--space-md);
        }}

        .action-button {{
            background: var(--bg-secondary);
            border: 2px solid var(--color-primary);
            color: var(--color-primary);
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-md);
            font-size: var(--font-size-md);
            font-weight: bold;
            cursor: pointer;
            transition: all var(--transition-normal);
        }}

        .action-button:hover {{
            background: var(--color-primary);
            color: var(--bg-primary);
        }}

        .action-button:focus-visible {{
            outline: 2px solid var(--color-primary);
            outline-offset: 2px;
        }}

        .action-button.danger {{
            border-color: var(--color-error);
            color: var(--color-error);
        }}

        .action-button.danger:hover {{
            background: var(--color-error);
            color: var(--text-primary);
        }}

        /* Processes Table */
        .processes-table {{
            background: var(--bg-secondary);
            border: 2px solid #333;
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            margin-bottom: var(--space-lg);
            overflow-x: auto;
        }}

        .processes-table h3 {{
            color: var(--color-primary);
            margin-bottom: var(--space-md);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 600px;
        }}

        th {{
            text-align: left;
            padding: var(--space-sm);
            border-bottom: 2px solid #333;
            color: var(--text-secondary);
        }}

        td {{
            padding: var(--space-sm);
            border-bottom: 1px solid #333;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .kill-btn {{
            background: var(--color-error);
            color: var(--text-primary);
            border: none;
            padding: 5px 10px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: var(--font-size-xs);
            transition: background var(--transition-fast);
        }}

        .kill-btn:hover {{
            background: #cc0000;
        }}

        .kill-btn:focus-visible {{
            outline: 2px solid var(--text-primary);
            outline-offset: 2px;
        }}

        /* Commands Section */
        .command-item {{
            background: var(--bg-secondary);
            border: 2px solid #333;
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-sm);
        }}

        .command-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-sm);
        }}

        .command-action {{
            font-weight: bold;
            color: var(--color-primary);
        }}

        .command-status {{
            padding: 4px 8px;
            border-radius: var(--radius-md);
            font-size: var(--font-size-xs);
            font-weight: bold;
        }}

        .command-status.pending {{
            background: var(--color-warning);
            color: var(--bg-primary);
        }}

        .command-status.completed {{
            background: var(--color-primary);
            color: var(--bg-primary);
        }}

        .command-status.failed {{
            background: var(--color-error);
            color: var(--text-primary);
        }}

        .command-time {{
            color: var(--text-secondary);
            font-size: var(--font-size-xs);
        }}

        /* Loading State */
        .loading {{
            text-align: center;
            padding: var(--space-xl);
            color: var(--text-secondary);
        }}

        /* Atlas Section */
        .widgets-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: var(--space-md);
            margin-bottom: var(--space-lg);
        }}

        .widget-container {{
            background: var(--bg-secondary);
            border: 2px solid #333;
            border-radius: var(--radius-md);
            padding: var(--space-sm);
            text-align: center;
        }}

        .widget-container img {{
            width: 100%;
            height: auto;
            border-radius: var(--radius-sm);
        }}

        .widget-error {{
            color: var(--color-error);
            padding: var(--space-lg);
            text-align: center;
            background: var(--bg-secondary);
            border: 2px solid var(--color-error);
            border-radius: var(--radius-md);
        }}

        .atlas-link {{
            display: inline-block;
            background: var(--color-primary);
            color: var(--bg-primary);
            padding: var(--space-sm) var(--space-lg);
            border-radius: var(--radius-md);
            text-decoration: none;
            font-weight: bold;
            margin-top: var(--space-sm);
            transition: all var(--transition-normal);
        }}

        .atlas-link:hover {{
            background: var(--color-primary-hover);
        }}

        .atlas-link:focus-visible {{
            outline: 2px solid var(--text-primary);
            outline-offset: 2px;
        }}

        /* Confirmation Dialog */
        .confirm-dialog {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg-overlay);
            z-index: var(--z-modal);
            align-items: center;
            justify-content: center;
        }}

        .confirm-dialog.active {{
            display: flex;
        }}

        .confirm-content {{
            background: var(--bg-secondary);
            border: 2px solid var(--color-primary);
            border-radius: var(--radius-lg);
            padding: var(--space-xl);
            max-width: 400px;
            width: 90%;
            text-align: center;
        }}

        .confirm-title {{
            color: var(--color-primary);
            font-size: var(--font-size-xl);
            margin-bottom: var(--space-md);
        }}

        .confirm-message {{
            color: var(--text-secondary);
            margin-bottom: var(--space-lg);
        }}

        .confirm-actions {{
            display: flex;
            gap: var(--space-md);
            justify-content: center;
        }}

        /* Responsive Breakpoints */
        @media (max-width: 768px) {{
            .header {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .header-actions {{
                width: 100%;
                justify-content: flex-start;
            }}

            h1 {{
                font-size: var(--font-size-xl);
            }}

            .info-grid {{
                grid-template-columns: 1fr;
            }}

            .actions-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 480px) {{
            .page-container {{
                padding: var(--space-md);
            }}

            .export-btn {{
                padding: var(--space-sm) var(--space-md);
                font-size: var(--font-size-xs);
            }}
        }}
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <!-- Confirmation Dialog -->
    <div id="confirmDialog" class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirmTitle">
        <div class="confirm-content">
            <h2 id="confirmTitle" class="confirm-title">Confirm Action</h2>
            <p id="confirmMessage" class="confirm-message"></p>
            <div class="confirm-actions">
                <button id="confirmCancel" class="action-button">Cancel</button>
                <button id="confirmOk" class="action-button danger">Confirm</button>
            </div>
        </div>
    </div>

    <main id="main-content" class="page-container" role="main">
        <header class="header">
            <div class="header-left">
                <a href="/dashboard" class="back-link" aria-label="Back to Fleet Dashboard">
                    <span aria-hidden="true">&larr;</span> Back to Fleet
                </a>
                <h1 id="machineName">Loading...</h1>
            </div>
            <nav class="header-actions" aria-label="Machine actions">
                <a id="networkAnalysisLink" href="#" class="export-btn" target="_blank" rel="noopener" aria-label="Open network analysis in new tab">
                    Network Analysis
                </a>
                <button class="export-btn" onclick="exportDeviceLogs()" aria-label="Export device logs to CSV">
                    Export Device Logs
                </button>
                <div id="statusBadge" role="status" aria-live="polite"></div>
            </nav>
        </header>

        <section class="info-grid" id="infoGrid" aria-label="Machine information">
            <div class="loading" role="status" aria-live="polite">
                <div class="spinner" aria-hidden="true"></div>
                <span>Loading machine information...</span>
            </div>
        </section>

        <section class="section" aria-labelledby="atlas-heading">
            <h2 id="atlas-heading">Atlas Widgets</h2>
            <div id="atlasWidgets" role="region" aria-label="Atlas widget previews">
                <div class="loading" role="status" aria-live="polite">
                    <div class="spinner" aria-hidden="true"></div>
                    <span>Loading Atlas widgets...</span>
                </div>
            </div>
        </section>

        <section class="section" aria-labelledby="metrics-heading">
            <h2 id="metrics-heading">Current Metrics</h2>
            <div id="metricsCards" role="region" aria-label="System metrics"></div>
        </section>

        <section class="section" aria-labelledby="actions-heading">
            <h2 id="actions-heading">Remote Actions</h2>
            <div class="actions-grid" role="group" aria-label="Remote action buttons">
                <button class="action-button" onclick="restartAgent()" aria-describedby="restart-desc">
                    Restart Agent
                </button>
                <span id="restart-desc" class="sr-only">Restart the fleet agent service on this machine</span>
                <button class="action-button" onclick="clearDNS()" aria-describedby="dns-desc">
                    Clear DNS Cache
                </button>
                <span id="dns-desc" class="sr-only">Clear the DNS cache on this machine</span>
            </div>
        </section>

        <section class="processes-table" id="processesSection" aria-labelledby="processes-heading">
            <h3 id="processes-heading">Top Processes</h3>
            <div id="processesContent" role="region" aria-label="Process list"></div>
        </section>

        <section class="section" aria-labelledby="commands-heading">
            <h2 id="commands-heading">Recent Commands</h2>
            <div id="commandsList" role="log" aria-label="Command history"></div>
        </section>
    </main>

    <script>
        {get_toast_script()}

        const machineId = '{machine_id}';

        // Confirmation dialog helper
        function showConfirm(title, message) {{
            return new Promise((resolve) => {{
                const dialog = document.getElementById('confirmDialog');
                const titleEl = document.getElementById('confirmTitle');
                const messageEl = document.getElementById('confirmMessage');
                const cancelBtn = document.getElementById('confirmCancel');
                const okBtn = document.getElementById('confirmOk');

                titleEl.textContent = title;
                messageEl.textContent = message;
                dialog.classList.add('active');

                // Focus trap
                okBtn.focus();

                const cleanup = () => {{
                    dialog.classList.remove('active');
                    cancelBtn.removeEventListener('click', onCancel);
                    okBtn.removeEventListener('click', onOk);
                }};

                const onCancel = () => {{
                    cleanup();
                    resolve(false);
                }};

                const onOk = () => {{
                    cleanup();
                    resolve(true);
                }};

                cancelBtn.addEventListener('click', onCancel);
                okBtn.addEventListener('click', onOk);

                // Close on escape
                dialog.addEventListener('keydown', (e) => {{
                    if (e.key === 'Escape') {{
                        cleanup();
                        resolve(false);
                    }}
                }});
            }});
        }}

        async function loadMachineData() {{
            try {{
                const machineResponse = await fetch(`/api/fleet/machine/${{machineId}}`);
                const machine = await machineResponse.json();

                // Update header
                document.getElementById('machineName').textContent = machine.info?.hostname || machineId;
                document.getElementById('statusBadge').innerHTML = `
                    <span class="status-badge status-${{machine.status}}" role="status">${{machine.status}}</span>
                `;

                // Update info cards with ARIA
                const infoGrid = document.getElementById('infoGrid');
                infoGrid.innerHTML = `
                    <article class="info-card" aria-label="System Information">
                        <h3>System Information</h3>
                        <div class="info-row">
                            <span class="info-label">Computer Name</span>
                            <span class="info-value">${{machine.info?.computer_name || machine.info?.hostname || 'Unknown'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Serial Number</span>
                            <span class="info-value">${{machine.info?.serial_number || 'Unknown'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">OS</span>
                            <span class="info-value">${{machine.info?.os || 'Unknown'}} ${{machine.info?.os_version || ''}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Architecture</span>
                            <span class="info-value">${{machine.info?.architecture || 'Unknown'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Processor</span>
                            <span class="info-value">${{machine.info?.processor || 'Unknown'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">CPU Cores</span>
                            <span class="info-value">${{machine.info?.cpu_count || '?'}} (${{machine.info?.cpu_threads || '?'}} threads)</span>
                        </div>
                    </article>
                    <article class="info-card" aria-label="Status">
                        <h3>Status</h3>
                        <div class="info-row">
                            <span class="info-label">First Seen</span>
                            <span class="info-value">${{new Date(machine.first_seen).toLocaleString()}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Last Seen</span>
                            <span class="info-value">${{new Date(machine.last_seen).toLocaleString()}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Uptime</span>
                            <span class="info-value">${{formatUptime(machine.latest_metrics?.uptime_seconds || 0)}}</span>
                        </div>
                    </article>
                    <article class="info-card" aria-label="Security Status">
                        <h3>Security</h3>
                        <div class="info-row">
                            <span class="info-label">Firewall</span>
                            <span class="info-value">${{machine.latest_metrics?.security?.firewall_enabled ? 'Enabled' : 'Disabled'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">FileVault</span>
                            <span class="info-value">${{machine.latest_metrics?.security?.filevault_enabled ? 'Enabled' : 'Disabled'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Gatekeeper</span>
                            <span class="info-value">${{machine.latest_metrics?.security?.gatekeeper_enabled ? 'Enabled' : 'Disabled'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">SIP</span>
                            <span class="info-value">${{machine.latest_metrics?.security?.sip_enabled ? 'Enabled' : 'Disabled'}}</span>
                        </div>
                    </article>
                `;

                // Update metrics with accessible progress bars
                const metrics = machine.latest_metrics || {{}};
                const cpu = metrics.cpu?.percent || 0;
                const memory = metrics.memory?.percent || 0;
                const disk = metrics.disk?.percent || 0;

                document.getElementById('metricsCards').innerHTML = `
                    <div class="metric-card" role="group" aria-label="CPU Usage">
                        <div class="metric-header">
                            <span class="metric-name">CPU Usage</span>
                            <span class="metric-value" aria-label="${{cpu.toFixed(1)}} percent">${{cpu.toFixed(1)}}%</span>
                        </div>
                        <div class="metric-bar" role="progressbar" aria-valuenow="${{cpu}}" aria-valuemin="0" aria-valuemax="100" aria-label="CPU usage progress">
                            <div class="metric-fill cpu ${{cpu > 90 ? 'high' : ''}}" style="width: ${{cpu}}%"></div>
                        </div>
                    </div>
                    <div class="metric-card" role="group" aria-label="Memory Usage">
                        <div class="metric-header">
                            <span class="metric-name">Memory Usage</span>
                            <span class="metric-value" aria-label="${{memory.toFixed(1)}} percent">${{memory.toFixed(1)}}%</span>
                        </div>
                        <div class="metric-bar" role="progressbar" aria-valuenow="${{memory}}" aria-valuemin="0" aria-valuemax="100" aria-label="Memory usage progress">
                            <div class="metric-fill memory ${{memory > 90 ? 'high' : ''}}" style="width: ${{memory}}%"></div>
                        </div>
                    </div>
                    <div class="metric-card" role="group" aria-label="Disk Usage">
                        <div class="metric-header">
                            <span class="metric-name">Disk Usage</span>
                            <span class="metric-value" aria-label="${{disk.toFixed(1)}} percent">${{disk.toFixed(1)}}%</span>
                        </div>
                        <div class="metric-bar" role="progressbar" aria-valuenow="${{disk}}" aria-valuemin="0" aria-valuemax="100" aria-label="Disk usage progress">
                            <div class="metric-fill disk ${{disk > 90 ? 'high' : ''}}" style="width: ${{disk}}%"></div>
                        </div>
                    </div>
                `;

                // Update processes table with accessibility
                const topCPU = metrics.processes?.top_cpu || [];
                if (topCPU.length > 0) {{
                    document.getElementById('processesContent').innerHTML = `
                        <table role="grid" aria-label="Top processes by CPU usage">
                            <thead>
                                <tr>
                                    <th scope="col">Process</th>
                                    <th scope="col">PID</th>
                                    <th scope="col">User</th>
                                    <th scope="col">CPU</th>
                                    <th scope="col">Memory</th>
                                    <th scope="col">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${{topCPU.map(proc => `
                                    <tr>
                                        <td>${{proc.name}}</td>
                                        <td>${{proc.pid}}</td>
                                        <td>${{proc.user}}</td>
                                        <td>${{proc.cpu.toFixed(1)}}%</td>
                                        <td>${{proc.memory.toFixed(1)}}%</td>
                                        <td>
                                            <button class="kill-btn" onclick="killProcess(${{proc.pid}}, '${{proc.name}}')"
                                                    aria-label="Kill process ${{proc.name}} with PID ${{proc.pid}}">
                                                Kill
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}}
                            </tbody>
                        </table>
                    `;
                }} else {{
                    document.getElementById('processesContent').innerHTML = '<p style="color: var(--text-secondary);">No process data available</p>';
                }}

            }} catch (e) {{
                console.error('Error loading machine data:', e);
                ToastManager.error('Failed to load machine data');
            }}
        }}

        async function loadCommands() {{
            try {{
                const response = await fetch(`/api/fleet/recent-commands/${{machineId}}`);
                const data = await response.json();
                const commands = data.commands || [];

                if (commands.length > 0) {{
                    document.getElementById('commandsList').innerHTML = commands.map(cmd => `
                        <article class="command-item" aria-label="Command: ${{cmd.action}}">
                            <div class="command-header">
                                <span class="command-action">${{cmd.action}}</span>
                                <span class="command-status ${{cmd.status}}" role="status">${{cmd.status}}</span>
                            </div>
                            <div class="command-time">
                                <time datetime="${{cmd.created_at}}">Created: ${{new Date(cmd.created_at).toLocaleString()}}</time>
                                ${{cmd.executed_at ? `<time datetime="${{cmd.executed_at}}"> - Executed: ${{new Date(cmd.executed_at).toLocaleString()}}</time>` : ''}}
                            </div>
                            ${{cmd.result?.message ? `<div style="color: var(--text-secondary); margin-top: var(--space-xs);">${{cmd.result.message}}</div>` : ''}}
                        </article>
                    `).join('');
                }} else {{
                    document.getElementById('commandsList').innerHTML = '<p style="color: var(--text-secondary);">No recent commands</p>';
                }}
            }} catch (e) {{
                console.error('Error loading commands:', e);
            }}
        }}

        async function sendCommand(action, params = {{}}) {{
            try {{
                const response = await fetch(`/api/fleet/command/${{machineId}}`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ action, params }})
                }});

                const result = await response.json();
                if (result.command_id) {{
                    ToastManager.success('Command sent successfully!');
                    loadCommands();
                }} else {{
                    ToastManager.error('Error sending command');
                }}
            }} catch (e) {{
                console.error('Error sending command:', e);
                ToastManager.error('Error sending command');
            }}
        }}

        async function restartAgent() {{
            const confirmed = await showConfirm('Restart Agent', 'Restart the fleet agent on this machine?');
            if (confirmed) {{
                sendCommand('restart_agent');
            }}
        }}

        async function clearDNS() {{
            const confirmed = await showConfirm('Clear DNS Cache', 'Clear DNS cache on this machine?');
            if (confirmed) {{
                sendCommand('clear_dns_cache');
            }}
        }}

        async function killProcess(pid, name) {{
            const confirmed = await showConfirm('Kill Process', `Kill process "${{name}}" (PID: ${{pid}})?`);
            if (confirmed) {{
                sendCommand('kill_process', {{ pid }});
            }}
        }}

        function formatUptime(seconds) {{
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);

            if (days > 0) return `${{days}}d ${{hours}}h`;
            if (hours > 0) return `${{hours}}h ${{minutes}}m`;
            return `${{minutes}}m`;
        }}

        async function loadAtlasWidgets() {{
            try {{
                const machineResponse = await fetch(`/api/fleet/machine/${{machineId}}`);
                const machine = await machineResponse.json();

                const machineHost = machine.info?.local_ip || machine.info?.hostname || machineId;
                const atlasPort = 8767;
                const atlasUrl = `http://${{machineHost}}:${{atlasPort}}`;

                const networkAnalysisLink = document.getElementById('networkAnalysisLink');
                if (networkAnalysisLink) {{
                    networkAnalysisLink.href = `${{atlasUrl}}/widget/network-analysis`;
                }}

                const statsResponse = await fetch(`${{atlasUrl}}/api/stats`, {{
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-cache'
                }});

                if (statsResponse.ok) {{
                    const timestamp = Date.now();
                    document.getElementById('atlasWidgets').innerHTML = `
                        <h3 style="color: var(--color-primary); margin-bottom: var(--space-md);">System Widgets</h3>
                        <div class="widgets-grid">
                            <div class="widget-container">
                                <iframe src="${{atlasUrl}}/widget/cpu" frameborder="0" style="width: 100%; height: 200px;" title="CPU Widget"></iframe>
                            </div>
                            <div class="widget-container">
                                <iframe src="${{atlasUrl}}/widget/gpu" frameborder="0" style="width: 100%; height: 200px;" title="GPU Widget"></iframe>
                            </div>
                            <div class="widget-container">
                                <iframe src="${{atlasUrl}}/widget/memory" frameborder="0" style="width: 100%; height: 200px;" title="Memory Widget"></iframe>
                            </div>
                            <div class="widget-container">
                                <iframe src="${{atlasUrl}}/widget/disk" frameborder="0" style="width: 100%; height: 200px;" title="Disk Widget"></iframe>
                            </div>
                            <div class="widget-container">
                                <iframe src="${{atlasUrl}}/widget/network" frameborder="0" style="width: 100%; height: 200px;" title="Network Widget"></iframe>
                            </div>
                            <div class="widget-container">
                                <iframe src="${{atlasUrl}}/widget/info" frameborder="0" style="width: 100%; height: 200px;" title="System Info Widget"></iframe>
                            </div>
                        </div>

                        <h3 style="color: var(--color-primary); margin: var(--space-xl) 0 var(--space-md) 0;">Network & Performance Widgets</h3>
                        <div class="widgets-grid">
                            <div class="widget-container" style="grid-column: span 2;">
                                <iframe src="${{atlasUrl}}/widget/wifi" frameborder="0" style="width: 100%; height: 600px;" title="WiFi Widget"></iframe>
                            </div>
                            <div class="widget-container" style="grid-column: span 2;">
                                <iframe src="${{atlasUrl}}/widget/ping" frameborder="0" style="width: 100%; height: 600px;" title="Ping Widget"></iframe>
                            </div>
                            <div class="widget-container" style="grid-column: span 2;">
                                <iframe src="${{atlasUrl}}/widget/speedtest" frameborder="0" style="width: 100%; height: 600px;" title="Speed Test Widget"></iframe>
                            </div>
                            <div class="widget-container" style="grid-column: span 2;">
                                <iframe src="${{atlasUrl}}/widget/health" frameborder="0" style="width: 100%; height: 600px;" title="Health Widget"></iframe>
                            </div>
                            <div class="widget-container" style="grid-column: span 3;">
                                <iframe src="${{atlasUrl}}/widget/processes" frameborder="0" style="width: 100%; height: 700px;" title="Processes Widget"></iframe>
                            </div>
                        </div>

                        <a href="${{atlasUrl}}" target="_blank" rel="noopener" class="atlas-link">
                            Open Full Atlas Dashboard
                        </a>
                    `;
                }} else {{
                    throw new Error('Atlas not responding');
                }}
            }} catch (e) {{
                console.error('Error loading Atlas widgets:', e);
                document.getElementById('atlasWidgets').innerHTML = `
                    <div class="widget-error" role="alert">
                        <p>Atlas not available on this machine</p>
                        <p style="font-size: var(--font-size-sm); margin-top: var(--space-sm); color: var(--text-secondary);">
                            Make sure the Atlas app is running on port 8767
                        </p>
                        <p style="font-size: var(--font-size-xs); margin-top: var(--space-xs); color: var(--text-muted);">
                            Run: python3 -m atlas.live_widgets
                        </p>
                    </div>
                `;
            }}
        }}

        function logsToCSV(logs) {{
            if (logs.length === 0) {{
                return 'No logs to export';
            }}

            const headers = ['ID', 'Serial Number', 'Timestamp', 'Level', 'Widget Type', 'Message', 'Data'];

            const rows = logs.map(log => {{
                const dataStr = JSON.stringify(log.data || {{}}).replace(/"/g, '""');
                return [
                    log.id,
                    log.machine_id,
                    log.timestamp,
                    log.level,
                    log.widget_type,
                    `"${{log.message.replace(/"/g, '""')}}"`,
                    `"${{dataStr}}"`
                ].join(',');
            }});

            return [headers.join(','), ...rows].join('\\n');
        }}

        async function exportDeviceLogs() {{
            try {{
                ToastManager.info('Preparing log export...');

                const response = await fetch(`/api/fleet/widget-logs?machine_id=${{machineId}}&limit=10000`);
                const data = await response.json();

                const machine = await (await fetch(`/api/fleet/machine/${{machineId}}`)).json();
                const machineName = machine.info?.computer_name || machine.info?.hostname || machineId;
                const serialNumber = machine.info?.serial_number || machineId;
                const date = new Date().toISOString().split('T')[0];
                const filename = `${{machineName.replace(/[^a-z0-9]/gi, '_')}}_logs_${{date}}.csv`;

                data.logs.forEach(log => {{
                    log.machine_id = serialNumber;
                }});

                const csv = logsToCSV(data.logs);

                const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                ToastManager.success(`Exported ${{data.logs.length}} log entries for ${{machineName}}`);
            }} catch (e) {{
                ToastManager.error('Error exporting logs: ' + e.message);
            }}
        }}

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {{
            loadMachineData();
            loadCommands();
            loadAtlasWidgets();

            // Refresh every 5 seconds
            setInterval(() => {{
                loadMachineData();
                loadCommands();
                loadAtlasWidgets();
            }}, 5000);
        }});
    </script>
</body>
</html>'''
