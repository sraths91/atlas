"""
VPN Status Widget - Real-time VPN connection monitoring

Displays:
- VPN connection status (connected/disconnected)
- VPN client detection (Cisco, GlobalProtect, etc.)
- Active VPN interfaces
- Connection duration
- Split tunnel detection
- Recent VPN events
"""

import logging

logger = logging.getLogger(__name__)


def get_vpn_status_widget_html():
    """Generate VPN Status widget HTML

    Returns HTML widget for VPN monitoring with:
    - Connection status indicator
    - VPN client identification
    - Active interfaces list
    - Connection duration timer
    - Split tunnel warning
    - Recent VPN events timeline
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
    <title>VPN Status - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* VPN Status Widget Specific Styles */
        body {
            padding: 15px;
            overflow-y: auto;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .widget {
            max-width: 100%;
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }

        .widget-bordered.vpn {
            border-color: #3b82f6;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #3b82f6;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Connection Status */
        .status-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: var(--space-lg) 0;
            padding: var(--space-lg);
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            flex-shrink: 0;
        }

        .status-indicator {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: var(--space-md);
            position: relative;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .status-indicator.connected {
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
            animation: pulse 2s ease-in-out infinite;
        }

        .status-indicator.disconnected {
            background: linear-gradient(135deg, #64748b 0%, #475569 100%);
        }

        @keyframes pulse {
            0%, 100% {
                box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
            }
            50% {
                box-shadow: 0 4px 20px rgba(34, 197, 94, 0.6);
            }
        }

        .status-icon {
            font-size: 48px;
            color: white;
        }

        .status-label {
            font-size: var(--font-size-lg);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }

        .status-label.connected {
            color: #22c55e;
        }

        .vpn-client {
            font-size: var(--font-size-md);
            color: var(--text-secondary);
        }

        /* Connection Details */
        .details-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .details-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .detail-item {
            display: flex;
            justify-content: space-between;
            padding: var(--space-xs) 0;
            font-size: var(--font-size-sm);
        }

        .detail-label {
            color: var(--text-secondary);
        }

        .detail-value {
            color: var(--text-primary);
            font-weight: 500;
        }

        /* Interfaces List */
        .interfaces-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .interfaces-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .interface-item {
            padding: var(--space-sm);
            margin-bottom: var(--space-xs);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
            border-left: 3px solid #3b82f6;
        }

        .interface-name {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }

        .interface-details {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        .no-interfaces {
            text-align: center;
            color: var(--text-muted);
            padding: var(--space-md);
        }

        /* Split Tunnel Warning */
        .warning-banner {
            background: rgba(234, 179, 8, 0.1);
            border: 1px solid #eab308;
            border-radius: var(--radius-sm);
            padding: var(--space-sm);
            margin-bottom: var(--space-md);
            display: none;
        }

        .warning-banner.show {
            display: block;
        }

        .warning-icon {
            color: #eab308;
            margin-right: var(--space-xs);
        }

        .warning-text {
            color: #eab308;
            font-size: var(--font-size-sm);
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

        .event-item.connect {
            border-left-color: #22c55e;
        }

        .event-item.disconnect {
            border-left-color: #ef4444;
        }

        .event-item.split_tunnel_detected {
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
            .status-indicator {
                width: 100px;
                height: 100px;
            }

            .status-icon {
                font-size: 36px;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered vpn" role="main" aria-label="VPN Status">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">VPN Status</h1>
        </header>

        <!-- Connection Status -->
        <section class="status-container" aria-label="VPN Connection Status">
            <div id="statusIndicator" class="status-indicator disconnected">
                <div class="status-icon">🔒</div>
            </div>
            <div id="statusLabel" class="status-label">Disconnected</div>
            <div id="vpnClient" class="vpn-client">No VPN detected</div>
        </section>

        <!-- Split Tunnel Warning -->
        <div id="splitTunnelWarning" class="warning-banner">
            <span class="warning-icon">⚠️</span>
            <span class="warning-text">Split tunnel detected - Some traffic may bypass VPN</span>
        </div>

        <!-- Connection Details -->
        <section id="detailsSection" class="details-section" style="display: none;" aria-label="Connection Details">
            <h2 class="details-title">Connection Details</h2>
            <div class="detail-item">
                <span class="detail-label">Duration:</span>
                <span id="duration" class="detail-value">--</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Interfaces:</span>
                <span id="interfaceCount" class="detail-value">0</span>
            </div>
        </section>

        <!-- Active Interfaces -->
        <section class="interfaces-section" aria-label="VPN Interfaces">
            <h2 class="interfaces-title">Active Interfaces</h2>
            <div id="interfacesList"></div>
        </section>

        <!-- Recent VPN Events -->
        <section class="events-section" aria-label="VPN Events">
            <h2 class="events-title">Recent Events</h2>
            <div id="eventsList"></div>
        </section>
    </main>

    <script>
'''

    widget_script = '''
        let connectionStartTime = null;
        let durationInterval = null;

        async function update() {
            try {
                const result = await apiFetch('/api/vpn/status');

                if (!result.ok) {
                    console.error('VPN status fetch failed:', result.error);
                    document.getElementById('statusLabel').textContent = 'Unavailable';
                    return;
                }

                const data = result.data;

                // Update connection status (use safeBool for type-safe boolean)
                updateStatus(safeBool(data.connected), data.vpn_client);

                // Update details
                updateDetails(data);

                // Update interfaces
                updateInterfaces(data.interfaces || []);

                // Update split tunnel warning (use safeBool for type-safe boolean)
                updateSplitTunnel(safeBool(data.split_tunnel));

                // Update events
                updateEvents(data.recent_events || []);

            } catch (e) {
                console.error('VPN status widget update failed:', e);
                ToastManager.error('Failed to update VPN status');
            }
        }

        function updateStatus(connected, client) {
            const indicator = document.getElementById('statusIndicator');
            const label = document.getElementById('statusLabel');
            const clientEl = document.getElementById('vpnClient');
            const detailsSection = document.getElementById('detailsSection');

            if (connected) {
                indicator.className = 'status-indicator connected';
                label.className = 'status-label connected';
                label.textContent = 'Connected';
                clientEl.textContent = client || 'VPN Active';
                detailsSection.style.display = 'block';

                if (!connectionStartTime) {
                    connectionStartTime = new Date();
                    startDurationCounter();
                }
            } else {
                indicator.className = 'status-indicator disconnected';
                label.className = 'status-label';
                label.textContent = 'Disconnected';
                clientEl.textContent = 'No VPN detected';
                detailsSection.style.display = 'none';

                if (connectionStartTime) {
                    connectionStartTime = null;
                    stopDurationCounter();
                }
            }
        }

        function updateDetails(data) {
            const interfaceCount = document.getElementById('interfaceCount');
            interfaceCount.textContent = data.connection_count || 0;
        }

        function updateInterfaces(interfaces) {
            const interfacesList = document.getElementById('interfacesList');

            if (interfaces.length === 0) {
                interfacesList.innerHTML = '<div class="no-interfaces">No active VPN interfaces</div>';
                return;
            }

            interfacesList.innerHTML = interfaces.map(iface => {
                const name = typeof iface === 'string' ? iface : iface.interface || iface;
                const details = typeof iface === 'object' ?
                    `${iface.local_ip || ''} ${iface.remote_ip ? '→ ' + iface.remote_ip : ''}`.trim() : '';

                return `
                    <div class="interface-item">
                        <div class="interface-name">${name}</div>
                        ${details ? `<div class="interface-details">${details}</div>` : ''}
                    </div>
                `;
            }).join('');
        }

        function updateSplitTunnel(detected) {
            const warning = document.getElementById('splitTunnelWarning');
            if (detected) {
                warning.classList.add('show');
            } else {
                warning.classList.remove('show');
            }
        }

        function updateEvents(events) {
            const eventsList = document.getElementById('eventsList');

            if (events.length === 0) {
                eventsList.innerHTML = '<div class="no-events">No recent VPN events</div>';
                return;
            }

            eventsList.innerHTML = events.slice(0, 10).map(event => {
                const time = new Date(event.timestamp);
                const timeAgo = getTimeAgo(time);

                return `
                    <div class="event-item ${event.event_type || 'connect'}">
                        <div class="event-time">${timeAgo}</div>
                        <div class="event-message">${event.details || event.message || 'VPN event'}</div>
                    </div>
                `;
            }).join('');
        }

        function startDurationCounter() {
            stopDurationCounter();
            updateDuration();
            durationInterval = setInterval(updateDuration, 1000);
        }

        function stopDurationCounter() {
            if (durationInterval) {
                clearInterval(durationInterval);
                durationInterval = null;
            }
            document.getElementById('duration').textContent = '--';
        }

        function updateDuration() {
            if (!connectionStartTime) return;

            const now = new Date();
            const diff = Math.floor((now - connectionStartTime) / 1000);

            const hours = Math.floor(diff / 3600);
            const minutes = Math.floor((diff % 3600) / 60);
            const seconds = diff % 60;

            const duration = document.getElementById('duration');
            duration.textContent = `${hours}h ${minutes}m ${seconds}s`;
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

        // Update every 5 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.FREQUENT);

        // Cleanup intervals on page unload
        window.addEventListener('beforeunload', () => {
            if (durationInterval) clearInterval(durationInterval);
            clearInterval(_ivUpdate);
        });
'''

    html_end = '''
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


# Export
__all__ = ['get_vpn_status_widget_html']
