"""
WiFi Roaming Widget - Advanced WiFi roaming and AP analysis

Displays:
- AP roaming event timeline
- Sticky client detection alerts
- Channel utilization heatmap
- Signal strength trends
- Roaming latency statistics
"""

import logging

logger = logging.getLogger(__name__)


def get_wifi_roaming_widget_html():
    """Generate WiFi Roaming widget HTML

    Returns HTML widget for WiFi roaming monitoring with:
    - AP roaming event timeline
    - Sticky client detection
    - Channel utilization
    - Signal strength trends
    - Roaming latency statistics
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
    <title>WiFi Roaming - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* WiFi Roaming Widget Specific Styles */
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

        .widget-bordered.wifi {
            border-color: #a855f7;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #a855f7;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Current AP Info */
        .current-ap-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .ap-info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: var(--space-sm);
            margin-top: var(--space-sm);
        }

        .ap-metric {
            text-align: center;
            padding: var(--space-sm);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
        }

        .ap-value {
            font-size: var(--font-size-lg);
            font-weight: bold;
            color: var(--text-primary);
        }

        .ap-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            margin-top: var(--space-xs);
        }

        /* Sticky Client Warning */
        .sticky-warning {
            background: rgba(234, 179, 8, 0.1);
            border: 1px solid #eab308;
            border-radius: var(--radius-sm);
            padding: var(--space-sm);
            margin-bottom: var(--space-md);
            display: none;
            flex-shrink: 0;
        }

        .sticky-warning.show {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
        }

        .warning-icon {
            font-size: var(--font-size-lg);
        }

        .warning-content {
            flex: 1;
        }

        .warning-title {
            color: #eab308;
            font-weight: bold;
            font-size: var(--font-size-sm);
        }

        .warning-message {
            color: var(--text-secondary);
            font-size: var(--font-size-xs);
            margin-top: 2px;
        }

        /* Channel Utilization */
        .channel-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .section-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .channel-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
            gap: var(--space-xs);
        }

        .channel-item {
            text-align: center;
            padding: var(--space-sm);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
            border-top: 3px solid transparent;
        }

        .channel-item.low {
            border-top-color: #22c55e;
        }

        .channel-item.medium {
            border-top-color: #eab308;
        }

        .channel-item.high {
            border-top-color: #ef4444;
        }

        .channel-number {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
        }

        .channel-util {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Signal Strength Trend */
        .signal-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .signal-trend {
            display: flex;
            align-items: flex-end;
            height: 100px;
            gap: 4px;
            margin-top: var(--space-sm);
        }

        .signal-bar {
            flex: 1;
            background: linear-gradient(to top, #a855f7, #c084fc);
            border-radius: 2px 2px 0 0;
            min-height: 10px;
            transition: height 0.3s ease;
        }

        .signal-stats {
            display: flex;
            justify-content: space-around;
            margin-top: var(--space-sm);
        }

        .signal-stat {
            text-align: center;
        }

        .signal-value {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
        }

        .signal-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Roaming Events */
        .events-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex: 1;
            min-height: 0;
            overflow-y: auto;
        }

        .event-item {
            padding: var(--space-sm);
            margin-bottom: var(--space-xs);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
            border-left: 3px solid transparent;
        }

        .event-item.roam {
            border-left-color: #3b82f6;
        }

        .event-item.sticky {
            border-left-color: #eab308;
        }

        .event-item.disconnect {
            border-left-color: #ef4444;
        }

        .event-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: var(--space-xs);
        }

        .event-type {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
        }

        .event-time {
            font-size: var(--font-size-xs);
            color: var(--text-muted);
        }

        .event-details {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        .event-ap-change {
            display: flex;
            align-items: center;
            gap: var(--space-xs);
            margin-top: var(--space-xs);
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        .event-latency {
            display: inline-block;
            padding: 2px 6px;
            background: rgba(168, 85, 247, 0.2);
            border-radius: 3px;
            margin-left: var(--space-xs);
            font-weight: bold;
        }

        .no-events {
            text-align: center;
            color: var(--text-muted);
            padding: var(--space-lg);
        }

        /* Roaming Statistics */
        .stats-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            flex-shrink: 0;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: var(--space-sm);
        }

        .stat-item {
            text-align: center;
            padding: var(--space-sm);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
        }

        .stat-value-large {
            font-size: var(--font-size-lg);
            font-weight: bold;
            color: #a855f7;
        }

        .stat-label-small {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            margin-top: var(--space-xs);
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .ap-info-grid {
                grid-template-columns: 1fr 1fr;
            }

            .channel-grid {
                grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
            }

            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered wifi" role="main" aria-label="WiFi Roaming">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">WiFi Roaming Monitor</h1>
        </header>

        <!-- Current AP Info -->
        <section class="current-ap-section" aria-label="Current Access Point">
            <h2 class="section-title">Current Access Point</h2>
            <div class="ap-info-grid">
                <div class="ap-metric">
                    <div id="currentSSID" class="ap-value">--</div>
                    <div class="ap-label">SSID</div>
                </div>
                <div class="ap-metric">
                    <div id="currentBSSID" class="ap-value">--</div>
                    <div class="ap-label">BSSID</div>
                </div>
                <div class="ap-metric">
                    <div id="currentChannel" class="ap-value">--</div>
                    <div class="ap-label">Channel</div>
                </div>
                <div class="ap-metric">
                    <div id="currentSignal" class="ap-value">--</div>
                    <div class="ap-label">Signal (dBm)</div>
                </div>
            </div>
        </section>

        <!-- Sticky Client Warning -->
        <div id="stickyWarning" class="sticky-warning">
            <div class="warning-icon">⚠️</div>
            <div class="warning-content">
                <div class="warning-title">Sticky Client Detected</div>
                <div class="warning-message">Device may be holding onto weak AP when better option available</div>
            </div>
        </div>

        <!-- Channel Utilization -->
        <section class="channel-section" aria-label="Channel Utilization">
            <h2 class="section-title">Channel Utilization</h2>
            <div id="channelGrid" class="channel-grid"></div>
        </section>

        <!-- Signal Strength Trend -->
        <section class="signal-section" aria-label="Signal Strength">
            <h2 class="section-title">Signal Strength Trend (Last Hour)</h2>
            <div id="signalTrend" class="signal-trend"></div>
            <div class="signal-stats">
                <div class="signal-stat">
                    <div id="signalAvg" class="signal-value">--</div>
                    <div class="signal-label">Average</div>
                </div>
                <div class="signal-stat">
                    <div id="signalMin" class="signal-value">--</div>
                    <div class="signal-label">Minimum</div>
                </div>
                <div class="signal-stat">
                    <div id="signalMax" class="signal-value">--</div>
                    <div class="signal-label">Maximum</div>
                </div>
            </div>
        </section>

        <!-- Roaming Statistics -->
        <section class="stats-section" aria-label="Roaming Statistics">
            <h2 class="section-title">Roaming Statistics (24h)</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div id="roamCount" class="stat-value-large">--</div>
                    <div class="stat-label-small">Roam Events</div>
                </div>
                <div class="stat-item">
                    <div id="avgLatency" class="stat-value-large">--</div>
                    <div class="stat-label-small">Avg Latency</div>
                </div>
                <div class="stat-item">
                    <div id="stickyCount" class="stat-value-large">--</div>
                    <div class="stat-label-small">Sticky Events</div>
                </div>
                <div class="stat-item">
                    <div id="uniqueAPs" class="stat-value-large">--</div>
                    <div class="stat-label-small">Unique APs</div>
                </div>
            </div>
        </section>

        <!-- Roaming Events -->
        <section class="events-section" aria-label="Roaming Events">
            <h2 class="section-title">Recent Roaming Events</h2>
            <div id="eventsList"></div>
        </section>
    </main>

    <script>
'''

    widget_script = '''
        async function update() {
            try {
                const result = await apiFetch('/api/wifi/roaming');
                if (!result.ok) {
                    console.error('WiFi roaming fetch failed:', result.error);
                    ToastManager.error('Failed to update WiFi roaming data');
                    return;
                }
                const data = result.data;

                // Update current AP info
                updateCurrentAP(data.current || {});

                // Update sticky client warning
                updateStickyWarning(safeBool(data.sticky_client_detected));

                // Update channel utilization
                updateChannels(data.channel_utilization || []);

                // Update signal strength trend
                updateSignalTrend(data.signal_history || []);

                // Update statistics
                updateStats(data.statistics || {});

                // Update events
                updateEvents(data.events || []);

            } catch (e) {
                console.error('WiFi roaming widget update failed:', e);
                ToastManager.error('Failed to update WiFi roaming data');
            }
        }

        function updateCurrentAP(current) {
            document.getElementById('currentSSID').textContent = current.ssid || '--';
            document.getElementById('currentBSSID').textContent = current.bssid ? formatBSSID(current.bssid) : '--';
            document.getElementById('currentChannel').textContent = current.channel || '--';
            document.getElementById('currentSignal').textContent = current.rssi ? current.rssi + ' dBm' : '--';
        }

        function updateStickyWarning(detected) {
            const warning = document.getElementById('stickyWarning');
            if (detected) {
                warning.classList.add('show');
            } else {
                warning.classList.remove('show');
            }
        }

        function updateChannels(channels) {
            const grid = document.getElementById('channelGrid');

            if (channels.length === 0) {
                // Show common 2.4GHz and 5GHz channels with no data
                channels = [1, 6, 11, 36, 40, 44, 48].map(ch => ({
                    channel: ch,
                    utilization_percent: 0
                }));
            }

            grid.innerHTML = channels.map(ch => {
                const util = ch.utilization_percent || 0;
                const level = util < 30 ? 'low' : util < 70 ? 'medium' : 'high';

                return `
                    <div class="channel-item ${level}">
                        <div class="channel-number">${ch.channel}</div>
                        <div class="channel-util">${util.toFixed(0)}%</div>
                    </div>
                `;
            }).join('');
        }

        function updateSignalTrend(history) {
            const trend = document.getElementById('signalTrend');

            if (history.length === 0) {
                trend.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No signal history available</div>';
                document.getElementById('signalAvg').textContent = '--';
                document.getElementById('signalMin').textContent = '--';
                document.getElementById('signalMax').textContent = '--';
                return;
            }

            // Create signal bars (last 20 samples)
            const samples = history.slice(-20);
            const minSignal = -90;
            const maxSignal = -30;

            trend.innerHTML = samples.map(sample => {
                const rssi = sample.rssi || -70;
                const normalized = ((rssi - minSignal) / (maxSignal - minSignal)) * 100;
                const height = Math.max(10, Math.min(100, normalized));

                return `<div class="signal-bar" style="height: ${height}%" title="${rssi} dBm"></div>`;
            }).join('');

            // Calculate statistics
            const rssiValues = history.map(s => s.rssi || -70);
            const avg = rssiValues.reduce((a, b) => a + b, 0) / rssiValues.length;
            const min = Math.min(...rssiValues);
            const max = Math.max(...rssiValues);

            document.getElementById('signalAvg').textContent = avg.toFixed(0) + ' dBm';
            document.getElementById('signalMin').textContent = min + ' dBm';
            document.getElementById('signalMax').textContent = max + ' dBm';
        }

        function updateStats(stats) {
            document.getElementById('roamCount').textContent = stats.roam_count || 0;
            document.getElementById('avgLatency').textContent = stats.avg_roam_latency_ms
                ? Math.round(stats.avg_roam_latency_ms) + 'ms'
                : '--';
            document.getElementById('stickyCount').textContent = stats.sticky_client_count || 0;
            document.getElementById('uniqueAPs').textContent = stats.unique_aps || 0;
        }

        function updateEvents(events) {
            const list = document.getElementById('eventsList');

            if (events.length === 0) {
                list.innerHTML = '<div class="no-events">No recent roaming events</div>';
                return;
            }

            list.innerHTML = events.slice(0, 20).map(event => {
                const time = new Date(event.timestamp);
                const timeAgo = getTimeAgo(time);
                const eventType = event.event_type || 'roam';
                const eventClass = eventType.includes('sticky') ? 'sticky' :
                                 eventType.includes('disconnect') ? 'disconnect' : 'roam';

                let eventTypeLabel = 'AP Roaming';
                if (eventType.includes('sticky')) eventTypeLabel = 'Sticky Client';
                else if (eventType.includes('disconnect')) eventTypeLabel = 'Disconnected';

                return `
                    <div class="event-item ${eventClass}">
                        <div class="event-header">
                            <span class="event-type">${eventTypeLabel}</span>
                            <span class="event-time">${timeAgo}</span>
                        </div>
                        <div class="event-details">${event.details || ''}</div>
                        ${event.from_bssid && event.to_bssid ? `
                            <div class="event-ap-change">
                                ${formatBSSID(event.from_bssid)} → ${formatBSSID(event.to_bssid)}
                                ${event.roam_latency_ms ? `<span class="event-latency">${Math.round(event.roam_latency_ms)}ms</span>` : ''}
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
        }

        function formatBSSID(bssid) {
            // Shorten BSSID for display (show last 4 octets)
            const parts = bssid.split(':');
            if (parts.length === 6) {
                return '...' + parts.slice(-2).join(':');
            }
            return bssid;
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
'''

    html_end = '''
        window.addEventListener('beforeunload', () => { clearInterval(_ivUpdate); });
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


# Export
__all__ = ['get_wifi_roaming_widget_html']
