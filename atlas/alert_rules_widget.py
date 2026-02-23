"""
Alert Rules Management Widget

Provides a comprehensive UI for managing custom alert rules including:
- View, create, edit, delete alert rules
- Configure notification channels (system, webhook, email)
- View alert history and statistics
- Test and validate rules
"""

from typing import Dict, Any


def get_alert_rules_widget_html() -> str:
    """Generate the Alert Rules Management widget HTML"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATLAS - Alert Rules Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e4;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        h1 {
            font-size: 28px;
            font-weight: 600;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        h1::before {
            content: "\\1F514";
            font-size: 32px;
        }

        .header-actions {
            display: flex;
            gap: 12px;
        }

        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #e4e4e4;
            border: 1px solid rgba(255,255,255,0.2);
        }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.15);
        }

        .btn-danger {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
        }

        .btn-success {
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            color: white;
        }

        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
            background: rgba(0,0,0,0.2);
            padding: 5px;
            border-radius: 12px;
            width: fit-content;
        }

        .tab {
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            font-family: inherit;
            background: transparent;
            color: #888;
            transition: all 0.2s;
        }

        .tab.active {
            background: rgba(102, 126, 234, 0.3);
            color: #fff;
        }

        .tab:hover:not(.active) {
            color: #ccc;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .stat-value {
            font-size: 36px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 14px;
            color: #888;
        }

        .stat-card.critical .stat-value { color: #e74c3c; }
        .stat-card.warning .stat-value { color: #f39c12; }
        .stat-card.info .stat-value { color: #3498db; }

        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
            color: #fff;
        }

        .rules-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .rule-item {
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 16px 20px;
            display: grid;
            grid-template-columns: auto 1fr auto auto;
            gap: 20px;
            align-items: center;
            transition: all 0.2s;
            border: 1px solid transparent;
        }

        .rule-item:hover {
            border-color: rgba(102, 126, 234, 0.3);
        }

        .rule-status {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }

        .rule-status.enabled { background: #2ecc71; }
        .rule-status.disabled { background: #7f8c8d; }

        .rule-info h4 {
            font-size: 15px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }

        .rule-info p {
            font-size: 13px;
            color: #888;
        }

        .rule-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        }

        .rule-badge.critical { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
        .rule-badge.warning { background: rgba(243, 156, 18, 0.2); color: #f39c12; }
        .rule-badge.info { background: rgba(52, 152, 219, 0.2); color: #3498db; }

        .rule-actions {
            display: flex;
            gap: 8px;
        }

        .rule-actions .btn {
            padding: 8px 12px;
            font-size: 12px;
        }

        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }

        .modal-overlay.active {
            display: flex;
        }

        .modal {
            background: #1a1a2e;
            border-radius: 16px;
            padding: 30px;
            width: 90%;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }

        .modal-title {
            font-size: 20px;
            font-weight: 600;
            color: #fff;
        }

        .modal-close {
            background: none;
            border: none;
            color: #888;
            font-size: 24px;
            cursor: pointer;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #ccc;
            margin-bottom: 8px;
        }

        .form-input,
        .form-select,
        .form-textarea {
            width: 100%;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 14px;
            transition: border-color 0.2s;
        }

        .form-input:focus,
        .form-select:focus,
        .form-textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        .checkbox-group {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }

        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(0,0,0,0.2);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
        }

        .checkbox-item input {
            width: 18px;
            height: 18px;
            accent-color: #667eea;
        }

        .events-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .event-item {
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 16px;
            display: grid;
            grid-template-columns: auto 1fr auto;
            gap: 16px;
            align-items: center;
        }

        .event-severity {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .event-severity.critical { background: rgba(231, 76, 60, 0.2); }
        .event-severity.warning { background: rgba(243, 156, 18, 0.2); }
        .event-severity.info { background: rgba(52, 152, 219, 0.2); }

        .event-info h4 {
            font-size: 14px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }

        .event-info p {
            font-size: 13px;
            color: #888;
        }

        .event-time {
            font-size: 12px;
            color: #666;
            text-align: right;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }

        .empty-state h3 {
            font-size: 18px;
            margin-bottom: 10px;
            color: #888;
        }

        .toggle-switch {
            position: relative;
            width: 50px;
            height: 26px;
            cursor: pointer;
        }

        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .toggle-slider {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.2);
            border-radius: 26px;
            transition: 0.3s;
        }

        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 3px;
            bottom: 3px;
            background: white;
            border-radius: 50%;
            transition: 0.3s;
        }

        input:checked + .toggle-slider {
            background: #667eea;
        }

        input:checked + .toggle-slider:before {
            transform: translateX(24px);
        }

        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
            color: #888;
        }

        .loading::after {
            content: "";
            width: 24px;
            height: 24px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 12px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #2ecc71;
            color: white;
            padding: 16px 24px;
            border-radius: 10px;
            font-weight: 500;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 2000;
        }

        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        .toast.error {
            background: #e74c3c;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Alert Rules Manager</h1>
            <div class="header-actions">
                <button class="btn btn-secondary" onclick="refreshData()">Refresh</button>
                <button class="btn btn-primary" onclick="openCreateModal()">+ Create Rule</button>
            </div>
        </header>

        <div class="tabs" role="tablist" aria-label="Alert rules sections">
            <button class="tab active" role="tab" aria-selected="true" aria-controls="tab-rules" id="tab-btn-rules" tabindex="0" data-tab="rules">Rules</button>
            <button class="tab" role="tab" aria-selected="false" aria-controls="tab-events" id="tab-btn-events" tabindex="-1" data-tab="events">Alert History</button>
            <button class="tab" role="tab" aria-selected="false" aria-controls="tab-settings" id="tab-btn-settings" tabindex="-1" data-tab="settings">Settings</button>
        </div>

        <!-- Rules Tab -->
        <div id="tab-rules" class="tab-content active" role="tabpanel" aria-labelledby="tab-btn-rules">
            <div class="stats-row" id="stats-row">
                <div class="stat-card">
                    <div class="stat-value" id="stat-total">-</div>
                    <div class="stat-label">Total Rules</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="stat-active">-</div>
                    <div class="stat-label">Active Rules</div>
                </div>
                <div class="stat-card critical">
                    <div class="stat-value" id="stat-critical">-</div>
                    <div class="stat-label">Critical Alerts (24h)</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-value" id="stat-warning">-</div>
                    <div class="stat-label">Warning Alerts (24h)</div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Alert Rules</span>
                    <button class="btn btn-secondary" onclick="resetToDefaults()">Reset to Defaults</button>
                </div>
                <div class="rules-list" id="rules-list">
                    <div class="loading">Loading rules...</div>
                </div>
            </div>
        </div>

        <!-- Events Tab -->
        <div id="tab-events" class="tab-content" role="tabpanel" aria-labelledby="tab-btn-events">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Alert History (Last 24 Hours)</span>
                    <select class="form-select" style="width: auto;" id="event-filter" onchange="loadEvents()">
                        <option value="">All Severities</option>
                        <option value="critical">Critical</option>
                        <option value="warning">Warning</option>
                        <option value="info">Info</option>
                    </select>
                </div>
                <div class="events-list" id="events-list">
                    <div class="loading">Loading events...</div>
                </div>
            </div>
        </div>

        <!-- Settings Tab -->
        <div id="tab-settings" class="tab-content" role="tabpanel" aria-labelledby="tab-btn-settings">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Email Notifications</span>
                </div>
                <form id="email-config-form">
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">SMTP Host</label>
                            <input type="text" class="form-input" id="smtp-host" value="smtp.gmail.com">
                        </div>
                        <div class="form-group">
                            <label class="form-label">SMTP Port</label>
                            <input type="number" class="form-input" id="smtp-port" value="587">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">Username</label>
                            <input type="text" class="form-input" id="email-username" placeholder="your@email.com">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-input" id="email-password" placeholder="App password">
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">From Address</label>
                        <input type="email" class="form-input" id="email-from" placeholder="alerts@yourdomain.com">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Enable Email Notifications</label>
                        <label class="toggle-switch">
                            <input type="checkbox" id="email-enabled">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <button type="submit" class="btn btn-primary">Save Email Config</button>
                        <button type="button" class="btn btn-secondary" onclick="testEmail()">Send Test Email</button>
                    </div>
                </form>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Maintenance</span>
                </div>
                <p style="color: #888; margin-bottom: 16px;">Clean up old alert events to free up database space.</p>
                <div style="display: flex; gap: 12px; align-items: center;">
                    <span style="color: #ccc;">Delete events older than</span>
                    <input type="number" class="form-input" style="width: 80px;" id="cleanup-days" value="30">
                    <span style="color: #ccc;">days</span>
                    <button class="btn btn-danger" onclick="cleanupEvents()">Cleanup</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Create/Edit Rule Modal -->
    <div class="modal-overlay" id="rule-modal">
        <div class="modal">
            <div class="modal-header">
                <h2 class="modal-title" id="modal-title">Create Alert Rule</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <form id="rule-form">
                <input type="hidden" id="rule-id">

                <div class="form-group">
                    <label class="form-label">Rule Name *</label>
                    <input type="text" class="form-input" id="rule-name" placeholder="High CPU Usage" required>
                </div>

                <div class="form-group">
                    <label class="form-label">Description</label>
                    <textarea class="form-textarea" id="rule-description" rows="2" placeholder="Alert when CPU usage exceeds threshold"></textarea>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Metric Type *</label>
                        <select class="form-select" id="rule-metric" required>
                            <option value="cpu">CPU Usage (%)</option>
                            <option value="memory">Memory Usage (%)</option>
                            <option value="disk">Disk Usage (%)</option>
                            <option value="temperature">Temperature (°C)</option>
                            <option value="battery">Battery (%)</option>
                            <option value="network_up">Network Upload (KB/s)</option>
                            <option value="network_down">Network Download (KB/s)</option>
                            <option value="download_speed">Download Speed (Mbps)</option>
                            <option value="upload_speed">Upload Speed (Mbps)</option>
                            <option value="ping">Ping (ms)</option>
                            <option value="packet_loss">Packet Loss (%)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Severity *</label>
                        <select class="form-select" id="rule-severity" required>
                            <option value="info">Info</option>
                            <option value="warning" selected>Warning</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Condition *</label>
                        <select class="form-select" id="rule-condition" required>
                            <option value=">">Greater than (>)</option>
                            <option value="<">Less than (<)</option>
                            <option value=">=">Greater or equal (>=)</option>
                            <option value="<=">Less or equal (<=)</option>
                            <option value="==">Equals (==)</option>
                            <option value="!=">Not equals (!=)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Threshold *</label>
                        <input type="number" class="form-input" id="rule-threshold" step="0.1" placeholder="90" required>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">Cooldown (seconds)</label>
                    <input type="number" class="form-input" id="rule-cooldown" value="300" min="60">
                    <small style="color: #666;">Minimum time between repeated alerts for this rule</small>
                </div>

                <div class="form-group">
                    <label class="form-label">Message Template</label>
                    <input type="text" class="form-input" id="rule-message" placeholder="High CPU usage: {value:.1f}%">
                    <small style="color: #666;">Use {value} or {value:.1f} for the metric value</small>
                </div>

                <div class="form-group">
                    <label class="form-label">Notification Channels</label>
                    <div class="checkbox-group">
                        <label class="checkbox-item">
                            <input type="checkbox" id="notify-system" checked>
                            <span>System Notification</span>
                        </label>
                        <label class="checkbox-item">
                            <input type="checkbox" id="notify-webhook">
                            <span>Webhook</span>
                        </label>
                        <label class="checkbox-item">
                            <input type="checkbox" id="notify-email">
                            <span>Email</span>
                        </label>
                    </div>
                </div>

                <div class="form-group" id="webhook-url-group" style="display: none;">
                    <label class="form-label">Webhook URL</label>
                    <input type="url" class="form-input" id="rule-webhook" placeholder="https://hooks.slack.com/...">
                </div>

                <div class="form-group" id="email-recipients-group" style="display: none;">
                    <label class="form-label">Email Recipients (comma-separated)</label>
                    <input type="text" class="form-input" id="rule-recipients" placeholder="admin@example.com, ops@example.com">
                </div>

                <div class="form-group">
                    <label class="form-label">Enabled</label>
                    <label class="toggle-switch">
                        <input type="checkbox" id="rule-enabled" checked>
                        <span class="toggle-slider"></span>
                    </label>
                </div>

                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Rule</button>
                </div>
            </form>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        // Tab switching
        document.querySelectorAll('.tab[role="tab"]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab[role="tab"]').forEach(t => {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                    t.setAttribute('tabindex', '-1');
                });
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                tab.setAttribute('tabindex', '0');
                document.getElementById('tab-' + tab.dataset.tab).classList.add('active');

                if (tab.dataset.tab === 'events') loadEvents();
                if (tab.dataset.tab === 'settings') loadEmailConfig();
            });
        });

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

        // Toggle webhook/email fields
        document.getElementById('notify-webhook').addEventListener('change', e => {
            document.getElementById('webhook-url-group').style.display = e.target.checked ? 'block' : 'none';
        });
        document.getElementById('notify-email').addEventListener('change', e => {
            document.getElementById('email-recipients-group').style.display = e.target.checked ? 'block' : 'none';
        });

        // Load rules on page load
        async function loadRules() {
            try {
                const [rulesRes, statsRes] = await Promise.all([
                    fetch('/api/alerts/rules?include_disabled=true'),
                    fetch('/api/alerts/statistics?hours=24')
                ]);

                const rulesData = await rulesRes.json();
                const statsData = await statsRes.json();

                // Update stats
                document.getElementById('stat-total').textContent = rulesData.count;
                document.getElementById('stat-active').textContent = rulesData.rules.filter(r => r.enabled).length;
                document.getElementById('stat-critical').textContent = statsData.by_severity?.critical || 0;
                document.getElementById('stat-warning').textContent = statsData.by_severity?.warning || 0;

                // Render rules
                const container = document.getElementById('rules-list');
                if (rulesData.rules.length === 0) {
                    container.innerHTML = '<div class="empty-state"><h3>No Alert Rules</h3><p>Create your first alert rule to get started.</p></div>';
                    return;
                }

                container.innerHTML = rulesData.rules.map(rule => `
                    <div class="rule-item">
                        <div class="rule-status ${rule.enabled ? 'enabled' : 'disabled'}"></div>
                        <div class="rule-info">
                            <h4>${escapeHtml(rule.name)}</h4>
                            <p>${rule.metric_type} ${rule.condition} ${rule.threshold} | Cooldown: ${rule.cooldown_seconds}s | Triggered: ${rule.trigger_count}x</p>
                        </div>
                        <span class="rule-badge ${rule.severity}">${rule.severity}</span>
                        <div class="rule-actions">
                            <button class="btn btn-secondary" onclick="editRule('${rule.id}')">Edit</button>
                            <button class="btn btn-secondary" onclick="toggleRule('${rule.id}', ${!rule.enabled})">${rule.enabled ? 'Disable' : 'Enable'}</button>
                            <button class="btn btn-danger" onclick="deleteRule('${rule.id}')">Delete</button>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                console.error('Failed to load rules:', err);
                showToast('Failed to load rules', true);
            }
        }

        async function loadEvents() {
            const severity = document.getElementById('event-filter').value;
            try {
                const res = await fetch(`/api/alerts/events?hours=24&limit=50${severity ? '&severity=' + severity : ''}`);
                const data = await res.json();

                const container = document.getElementById('events-list');
                if (data.events.length === 0) {
                    container.innerHTML = '<div class="empty-state"><h3>No Alert Events</h3><p>No alerts have been triggered in the last 24 hours.</p></div>';
                    return;
                }

                container.innerHTML = data.events.map(event => `
                    <div class="event-item">
                        <div class="event-severity ${event.severity}">${getSeverityIcon(event.severity)}</div>
                        <div class="event-info">
                            <h4>${escapeHtml(event.rule_name)}</h4>
                            <p>${escapeHtml(event.message)}</p>
                        </div>
                        <div class="event-time">
                            ${formatTime(event.triggered_at)}
                            ${event.acknowledged ? '<br><span style="color: #2ecc71;">\\u2713 Acknowledged</span>' : ''}
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                console.error('Failed to load events:', err);
            }
        }

        async function loadEmailConfig() {
            try {
                const res = await fetch('/api/alerts/email-config');
                const data = await res.json();

                if (data.configured !== false) {
                    document.getElementById('smtp-host').value = data.smtp_host || 'smtp.gmail.com';
                    document.getElementById('smtp-port').value = data.smtp_port || 587;
                    document.getElementById('email-username').value = data.username || '';
                    document.getElementById('email-from').value = data.from_address || '';
                    document.getElementById('email-enabled').checked = data.enabled || false;
                }
            } catch (err) {
                console.error('Failed to load email config:', err);
            }
        }

        function openCreateModal() {
            document.getElementById('modal-title').textContent = 'Create Alert Rule';
            document.getElementById('rule-form').reset();
            document.getElementById('rule-id').value = '';
            document.getElementById('rule-enabled').checked = true;
            document.getElementById('notify-system').checked = true;
            document.getElementById('webhook-url-group').style.display = 'none';
            document.getElementById('email-recipients-group').style.display = 'none';
            document.getElementById('rule-modal').classList.add('active');
        }

        async function editRule(ruleId) {
            try {
                const res = await fetch(`/api/alerts/rules/${ruleId}`);
                const rule = await res.json();

                document.getElementById('modal-title').textContent = 'Edit Alert Rule';
                document.getElementById('rule-id').value = rule.id;
                document.getElementById('rule-name').value = rule.name;
                document.getElementById('rule-description').value = rule.description || '';
                document.getElementById('rule-metric').value = rule.metric_type;
                document.getElementById('rule-severity').value = rule.severity;
                document.getElementById('rule-condition').value = rule.condition;
                document.getElementById('rule-threshold').value = rule.threshold;
                document.getElementById('rule-cooldown').value = rule.cooldown_seconds;
                document.getElementById('rule-message').value = rule.message_template || '';
                document.getElementById('rule-enabled').checked = rule.enabled;

                // Notification channels
                const types = rule.notification_types || ['system'];
                document.getElementById('notify-system').checked = types.includes('system');
                document.getElementById('notify-webhook').checked = types.includes('webhook');
                document.getElementById('notify-email').checked = types.includes('email');

                document.getElementById('webhook-url-group').style.display = types.includes('webhook') ? 'block' : 'none';
                document.getElementById('email-recipients-group').style.display = types.includes('email') ? 'block' : 'none';

                document.getElementById('rule-webhook').value = rule.webhook_url || '';
                document.getElementById('rule-recipients').value = (rule.email_recipients || []).join(', ');

                document.getElementById('rule-modal').classList.add('active');
            } catch (err) {
                console.error('Failed to load rule:', err);
                showToast('Failed to load rule', true);
            }
        }

        function closeModal() {
            document.getElementById('rule-modal').classList.remove('active');
        }

        document.getElementById('rule-form').addEventListener('submit', async e => {
            e.preventDefault();

            const ruleId = document.getElementById('rule-id').value;
            const notificationTypes = [];
            if (document.getElementById('notify-system').checked) notificationTypes.push('system');
            if (document.getElementById('notify-webhook').checked) notificationTypes.push('webhook');
            if (document.getElementById('notify-email').checked) notificationTypes.push('email');

            const ruleData = {
                name: document.getElementById('rule-name').value,
                description: document.getElementById('rule-description').value,
                metric_type: document.getElementById('rule-metric').value,
                severity: document.getElementById('rule-severity').value,
                condition: document.getElementById('rule-condition').value,
                threshold: parseFloat(document.getElementById('rule-threshold').value),
                cooldown_seconds: parseInt(document.getElementById('rule-cooldown').value),
                message_template: document.getElementById('rule-message').value,
                enabled: document.getElementById('rule-enabled').checked,
                notification_types: notificationTypes,
                webhook_url: document.getElementById('rule-webhook').value || null,
                email_recipients: document.getElementById('rule-recipients').value
                    ? document.getElementById('rule-recipients').value.split(',').map(e => e.trim())
                    : []
            };

            try {
                const url = ruleId ? `/api/alerts/rules/${ruleId}/update` : '/api/alerts/rules';
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(ruleData)
                });

                const data = await res.json();
                if (res.ok) {
                    showToast(ruleId ? 'Rule updated successfully' : 'Rule created successfully');
                    closeModal();
                    loadRules();
                } else {
                    showToast(data.error || 'Failed to save rule', true);
                }
            } catch (err) {
                console.error('Failed to save rule:', err);
                showToast('Failed to save rule', true);
            }
        });

        async function toggleRule(ruleId, enabled) {
            try {
                const res = await fetch(`/api/alerts/rules/${ruleId}/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });

                if (res.ok) {
                    showToast(enabled ? 'Rule enabled' : 'Rule disabled');
                    loadRules();
                } else {
                    showToast('Failed to toggle rule', true);
                }
            } catch (err) {
                console.error('Failed to toggle rule:', err);
                showToast('Failed to toggle rule', true);
            }
        }

        async function deleteRule(ruleId) {
            if (!confirm('Are you sure you want to delete this rule?')) return;

            try {
                const res = await fetch(`/api/alerts/rules/${ruleId}/delete`, { method: 'POST' });

                if (res.ok) {
                    showToast('Rule deleted');
                    loadRules();
                } else {
                    showToast('Failed to delete rule', true);
                }
            } catch (err) {
                console.error('Failed to delete rule:', err);
                showToast('Failed to delete rule', true);
            }
        }

        async function resetToDefaults() {
            if (!confirm('This will delete all custom rules and restore defaults. Continue?')) return;

            try {
                const res = await fetch('/api/alerts/rules/reset', { method: 'POST' });

                if (res.ok) {
                    showToast('Rules reset to defaults');
                    loadRules();
                } else {
                    showToast('Failed to reset rules', true);
                }
            } catch (err) {
                console.error('Failed to reset rules:', err);
                showToast('Failed to reset rules', true);
            }
        }

        document.getElementById('email-config-form').addEventListener('submit', async e => {
            e.preventDefault();

            const config = {
                smtp_host: document.getElementById('smtp-host').value,
                smtp_port: parseInt(document.getElementById('smtp-port').value),
                use_tls: true,
                username: document.getElementById('email-username').value,
                password: document.getElementById('email-password').value,
                from_address: document.getElementById('email-from').value,
                enabled: document.getElementById('email-enabled').checked
            };

            try {
                const res = await fetch('/api/alerts/email-config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                if (res.ok) {
                    showToast('Email configuration saved');
                } else {
                    showToast('Failed to save email config', true);
                }
            } catch (err) {
                console.error('Failed to save email config:', err);
                showToast('Failed to save email config', true);
            }
        });

        async function testEmail() {
            const recipient = prompt('Enter email address for test:');
            if (!recipient) return;

            try {
                const res = await fetch('/api/alerts/email-test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recipient })
                });

                const data = await res.json();
                if (res.ok) {
                    showToast('Test email sent');
                } else {
                    showToast(data.error || 'Failed to send test email', true);
                }
            } catch (err) {
                console.error('Failed to send test email:', err);
                showToast('Failed to send test email', true);
            }
        }

        async function cleanupEvents() {
            const days = parseInt(document.getElementById('cleanup-days').value);
            if (!confirm(`Delete all events older than ${days} days?`)) return;

            try {
                const res = await fetch('/api/alerts/cleanup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ days })
                });

                const data = await res.json();
                if (res.ok) {
                    showToast(`Deleted ${data.deleted_count} old events`);
                } else {
                    showToast('Failed to cleanup events', true);
                }
            } catch (err) {
                console.error('Failed to cleanup events:', err);
                showToast('Failed to cleanup events', true);
            }
        }

        function refreshData() {
            loadRules();
            showToast('Data refreshed');
        }

        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast' + (isError ? ' error' : '');
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function getSeverityIcon(severity) {
            const icons = {
                critical: '\\u26A0',
                warning: '\\u26A0',
                info: '\\u2139'
            };
            return icons[severity] || '\\u2139';
        }

        function formatTime(isoString) {
            const date = new Date(isoString);
            return date.toLocaleString();
        }

        // Initial load
        loadRules();
    </script>
</body>
</html>
'''
