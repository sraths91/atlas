"""
Security Dashboard Widget - Comprehensive security posture visualization

Displays:
- Security score gauge (0-100)
- Security posture checklist
- Pending updates counter
- Recent security events
- Failed login attempts chart
"""

import logging

logger = logging.getLogger(__name__)


def get_security_dashboard_widget_html():
    """Generate Security Dashboard widget HTML

    Returns HTML widget for security monitoring with:
    - Security score visualization
    - Compliance status indicators
    - Real-time event monitoring
    - Accessibility features (ARIA labels, focus states)
    """
    # Import shared styles
    from atlas.agent_widget_styles import (
        get_widget_base_styles,
        get_widget_toast_script,
        get_widget_api_helpers_script
    )

    base_styles = get_widget_base_styles()
    toast_script = get_widget_toast_script()
    api_helpers = get_widget_api_helpers_script()

    html_start = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Dashboard - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* Security Dashboard Widget Specific Styles */
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
        }

        body {
            padding: 15px;
            overflow-y: auto;
            overflow-x: hidden;
            box-sizing: border-box;
        }

        .widget {
            max-width: 100%;
            min-height: min-content;
        }

        .widget-bordered.security {
            border-color: #00E5A0;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #00E5A0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Security Score Gauge */
        .score-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: var(--space-lg) 0;
            flex-shrink: 0;
        }

        .score-gauge {
            position: relative;
            width: 200px;
            height: 200px;
        }

        .score-circle {
            transform: rotate(-90deg);
        }

        .score-bg {
            fill: none;
            stroke: rgba(255, 255, 255, 0.1);
            stroke-width: 20;
        }

        .score-progress {
            fill: none;
            stroke: #00E5A0;
            stroke-width: 20;
            stroke-linecap: round;
            transition: stroke-dashoffset 1s ease;
        }

        .score-progress.warning {
            stroke: #eab308;
        }

        .score-progress.danger {
            stroke: #ef4444;
        }

        .score-value {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 48px;
            font-weight: bold;
            color: #00E5A0;
        }

        .score-value.warning {
            color: #eab308;
        }

        .score-value.danger {
            color: #ef4444;
        }

        .score-label {
            position: absolute;
            bottom: 55px;
            left: 50%;
            transform: translateX(-50%);
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        /* Security Checklist */
        .security-checklist {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .checklist-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .checklist-item {
            display: flex;
            align-items: center;
            padding: var(--space-xs) 0;
            font-size: var(--font-size-sm);
        }

        .check-icon {
            width: 20px;
            height: 20px;
            margin-right: var(--space-sm);
            flex-shrink: 0;
        }

        .check-icon.enabled {
            color: #22c55e;
        }

        .check-icon.disabled {
            color: #ef4444;
        }

        .check-label {
            color: var(--text-secondary);
        }

        /* Updates Section */
        .updates-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .updates-section.warning {
            border-left: 3px solid #eab308;
        }

        .updates-section.danger {
            border-left: 3px solid #ef4444;
        }

        .updates-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            margin-bottom: var(--space-xs);
        }

        .updates-count {
            font-size: var(--font-size-2xl);
            font-weight: bold;
            color: #eab308;
        }

        .updates-count.danger {
            color: #ef4444;
        }

        /* Events Section */
        .events-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex: 1;
            min-height: 0;
            overflow-y: auto;
        }

        .events-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .event-item {
            padding: var(--space-sm);
            margin-bottom: var(--space-xs);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
            border-left: 3px solid transparent;
        }

        .event-item.critical {
            border-left-color: #ef4444;
        }

        .event-item.high {
            border-left-color: #f97316;
        }

        .event-item.medium {
            border-left-color: #eab308;
        }

        .event-time {
            font-size: var(--font-size-xs);
            color: var(--text-muted);
            margin-bottom: var(--space-xs);
        }

        .event-message {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
        }

        .no-events {
            text-align: center;
            color: var(--text-muted);
            padding: var(--space-lg);
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
            .score-gauge {
                width: 150px;
                height: 150px;
            }

            .score-value {
                font-size: 36px;
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered security" role="main" aria-label="Security Dashboard">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">Security Dashboard</h1>
        </header>

        <!-- Security Score Gauge -->
        <section class="score-container" aria-label="Security Score">
            <div class="score-gauge">
                <svg class="score-circle" width="200" height="200" viewBox="0 0 200 200">
                    <circle class="score-bg" cx="100" cy="100" r="85"></circle>
                    <circle id="scoreProgress" class="score-progress" cx="100" cy="100" r="85"
                            stroke-dasharray="534.07" stroke-dashoffset="534.07"></circle>
                </svg>
                <div id="scoreValue" class="score-value" aria-live="polite">--</div>
                <div class="score-label">Security Score</div>
            </div>
        </section>

        <!-- Security Checklist -->
        <section class="security-checklist" aria-label="Security Status">
            <h2 class="checklist-title">Security Posture</h2>
            <div id="checklistItems"></div>
        </section>

        <!-- Pending Updates -->
        <section id="updatesSection" class="updates-section" aria-label="System Updates">
            <div class="updates-title">Pending Security Updates</div>
            <div id="updatesCount" class="updates-count" aria-live="polite">--</div>
        </section>

        <!-- Recent Security Events -->
        <section class="events-section" aria-label="Security Events">
            <h2 class="events-title">Recent Security Events</h2>
            <div id="eventsList"></div>
        </section>
    </main>

    <script>
'''

    widget_script = '''
        function escapeHtml(str) {
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }

        let currentScore = 0;

        async function update() {
            try {
                const result = await apiFetch('/api/security/status');
                if (!result.ok) {
                    console.error('Update failed:', result.error);
                    return;
                }
                const data = result.data;

                // Update security score
                updateScore(data.security_score || 0);

                // Flatten nested structure for checklist
                const flatData = {
                    firewall_enabled: data.firewall?.enabled || false,
                    filevault_enabled: data.filevault?.enabled || false,
                    gatekeeper_enabled: data.gatekeeper?.enabled || false,
                    sip_enabled: data.sip?.enabled || false,
                    screen_lock_enabled: data.screen_lock?.enabled || false,
                    auto_updates_enabled: data.updates?.auto_updates_enabled || false
                };

                // Update checklist
                updateChecklist(flatData);

                // Update pending updates
                updatePendingUpdates(data.updates?.pending_count || 0);

                // Update events
                updateEvents(data.recent_events || []);

            } catch (e) {
                console.error('Update failed:', e);
            }
        }

        function updateScore(score) {
            currentScore = score;
            const scoreValue = document.getElementById('scoreValue');
            const scoreProgress = document.getElementById('scoreProgress');

            // Update score display
            scoreValue.textContent = score;

            // Calculate circle progress
            const circumference = 534.07;
            const offset = circumference - (score / 100 * circumference);
            scoreProgress.style.strokeDashoffset = offset;

            // Color based on score
            scoreValue.className = 'score-value';
            scoreProgress.className = 'score-progress';

            if (score >= 80) {
                // Good
            } else if (score >= 60) {
                scoreValue.classList.add('warning');
                scoreProgress.classList.add('warning');
            } else {
                scoreValue.classList.add('danger');
                scoreProgress.classList.add('danger');
            }
        }

        function updateChecklist(data) {
            const checklistItems = document.getElementById('checklistItems');

            const items = [
                { label: 'Firewall Enabled', enabled: data.firewall_enabled, key: 'firewall' },
                { label: 'FileVault Encryption', enabled: data.filevault_enabled, key: 'filevault' },
                { label: 'Gatekeeper Enabled', enabled: data.gatekeeper_enabled, key: 'gatekeeper' },
                { label: 'System Integrity Protection', enabled: data.sip_enabled, key: 'sip' },
                { label: 'Screen Lock Configured', enabled: data.screen_lock_enabled, key: 'screen_lock' },
                { label: 'Automatic Updates', enabled: data.auto_updates_enabled, key: 'auto_updates' }
            ];

            checklistItems.innerHTML = items.map(item => `
                <div class="checklist-item">
                    <svg class="check-icon ${item.enabled ? 'enabled' : 'disabled'}" fill="currentColor" viewBox="0 0 20 20">
                        ${item.enabled ?
                            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>' :
                            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>'
                        }
                    </svg>
                    <span class="check-label">${item.label}</span>
                </div>
            `).join('');
        }

        function updatePendingUpdates(count) {
            const updatesCount = document.getElementById('updatesCount');
            const updatesSection = document.getElementById('updatesSection');

            updatesCount.textContent = count;
            updatesCount.className = 'updates-count';
            updatesSection.className = 'updates-section';

            if (count === 0) {
                updatesCount.textContent = 'Up to date ✓';
                updatesCount.classList.add('success');
            } else if (count > 5) {
                updatesCount.classList.add('danger');
                updatesSection.classList.add('danger');
            } else if (count > 0) {
                updatesSection.classList.add('warning');
            }
        }

        function updateEvents(events) {
            const eventsList = document.getElementById('eventsList');

            if (events.length === 0) {
                eventsList.innerHTML = '<div class="no-events">No recent security events</div>';
                return;
            }

            eventsList.innerHTML = events.slice(0, 10).map(event => {
                const time = new Date(event.timestamp);
                const timeAgo = getTimeAgo(time);

                return `
                    <div class="event-item ${escapeHtml(event.severity || 'medium')}">
                        <div class="event-time">${timeAgo}</div>
                        <div class="event-message">${escapeHtml(event.details || event.message)}</div>
                    </div>
                `;
            }).join('');
        }

        function getTimeAgo(date) {
            const seconds = Math.floor((new Date() - date) / 1000);

            if (seconds < 60) return 'Just now';
            if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
            if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
            return Math.floor(seconds / 86400) + 'd ago';
        }

        // Initial update
        update();

        // Update every 10 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.STANDARD);

        // Cleanup intervals on page unload
        window.addEventListener('beforeunload', () => {
            clearInterval(_ivUpdate);
        });
'''

    html_end = '''
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


# Export
__all__ = ['get_security_dashboard_widget_html']
