"""
SaaS Endpoint Health Widget - Monitor critical business service availability

Displays:
- Service category health grid (Office365, Google, AWS, etc.)
- Availability percentage by service
- Response time trends
- Incident alerts
- Recent outages timeline
"""

import logging

logger = logging.getLogger(__name__)


def get_saas_health_widget_html():
    """Generate SaaS Endpoint Health widget HTML

    Returns HTML widget for SaaS monitoring with:
    - Service category health grid
    - Availability metrics
    - Response time indicators
    - Incident timeline
    - Overall health score
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
    <title>SaaS Health - ATLAS Agent</title>
    <style>
'''

    widget_styles = '''
        /* SaaS Health Widget Specific Styles */
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

        .widget-bordered.saas {
            border-color: #8b5cf6;
        }

        .widget-header {
            text-align: center;
            margin-bottom: var(--space-md);
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            color: #8b5cf6;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Overall Health Score */
        .health-overview {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
            display: flex;
            justify-content: space-around;
            align-items: center;
        }

        .health-metric {
            text-align: center;
        }

        .metric-value {
            font-size: var(--font-size-2xl);
            font-weight: bold;
            color: var(--text-primary);
        }

        .metric-value.excellent {
            color: #22c55e;
        }

        .metric-value.good {
            color: #3b82f6;
        }

        .metric-value.degraded {
            color: #eab308;
        }

        .metric-value.down {
            color: #ef4444;
        }

        .metric-label {
            font-size: var(--font-size-sm);
            color: var(--text-secondary);
            margin-top: var(--space-xs);
        }

        /* Service Categories Grid */
        .categories-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: var(--space-sm);
            margin-bottom: var(--space-md);
        }

        .category-card {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            border: 2px solid transparent;
        }

        .category-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .category-card.healthy {
            border-color: #22c55e;
        }

        .category-card.degraded {
            border-color: #eab308;
        }

        .category-card.down {
            border-color: #ef4444;
        }

        .category-icon {
            font-size: 32px;
            margin-bottom: var(--space-xs);
        }

        .category-name {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }

        .category-status {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        .availability-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: var(--radius-sm);
            font-size: var(--font-size-xs);
            font-weight: bold;
            margin-top: var(--space-xs);
        }

        .availability-badge.excellent {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
        }

        .availability-badge.good {
            background: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
        }

        .availability-badge.degraded {
            background: rgba(234, 179, 8, 0.2);
            color: #eab308;
        }

        .availability-badge.down {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }

        /* Service Details */
        .services-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .services-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .service-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--space-sm);
            margin-bottom: var(--space-xs);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
            border-left: 3px solid transparent;
        }

        .service-item.healthy {
            border-left-color: #22c55e;
        }

        .service-item.degraded {
            border-left-color: #eab308;
        }

        .service-item.down {
            border-left-color: #ef4444;
        }

        .service-info {
            flex: 1;
        }

        .service-name {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .service-endpoint {
            font-size: var(--font-size-xs);
            color: var(--text-muted);
        }

        .service-metrics {
            display: flex;
            gap: var(--space-md);
            align-items: center;
        }

        .metric-item {
            text-align: right;
        }

        .metric-item-value {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
        }

        .metric-item-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        /* Incidents Section */
        .incidents-section {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .incidents-title {
            font-size: var(--font-size-md);
            font-weight: bold;
            color: var(--text-primary);
            margin-bottom: var(--space-sm);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: var(--space-xs);
        }

        .incident-item {
            padding: var(--space-sm);
            margin-bottom: var(--space-xs);
            background: rgba(0, 0, 0, 0.3);
            border-radius: var(--radius-sm);
            border-left: 3px solid #ef4444;
        }

        .incident-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: var(--space-xs);
        }

        .incident-service {
            font-size: var(--font-size-sm);
            font-weight: bold;
            color: var(--text-primary);
        }

        .incident-time {
            font-size: var(--font-size-xs);
            color: var(--text-muted);
        }

        .incident-details {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
        }

        .no-incidents {
            text-align: center;
            color: var(--text-muted);
            padding: var(--space-lg);
        }

        /* Loading State */
        .loading {
            text-align: center;
            padding: var(--space-lg);
            color: var(--text-secondary);
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .categories-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .service-metrics {
                flex-direction: column;
                gap: var(--space-xs);
            }
        }

        @media (max-width: 480px) {
            .health-overview {
                flex-direction: column;
                gap: var(--space-md);
            }
        }
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="widget widget-bordered saas" role="main" aria-label="SaaS Health Monitor">
        <header class="widget-header">
            <h1 class="widget-title" id="widget-title">SaaS Health</h1>
        </header>

        <!-- Overall Health Overview -->
        <section class="health-overview" aria-label="Health Overview">
            <div class="health-metric">
                <div id="overallHealth" class="metric-value excellent">--</div>
                <div class="metric-label">Overall Health</div>
            </div>
            <div class="health-metric">
                <div id="avgLatency" class="metric-value">--ms</div>
                <div class="metric-label">Avg Response Time</div>
            </div>
            <div class="health-metric">
                <div id="servicesUp" class="metric-value excellent">--</div>
                <div class="metric-label">Services Up</div>
            </div>
        </section>

        <!-- Service Categories -->
        <section aria-label="Service Categories">
            <div id="categoriesGrid" class="categories-grid"></div>
        </section>

        <!-- Recent Incidents -->
        <section class="incidents-section" aria-label="Recent Incidents">
            <h2 class="incidents-title">Recent Incidents</h2>
            <div id="incidentsList"></div>
        </section>

        <!-- Service Details -->
        <section class="services-section" aria-label="Service Details">
            <h2 class="services-title">Service Details</h2>
            <div id="servicesList"></div>
        </section>
    </main>

    <script>
'''

    widget_script = '''
        function escapeHtml(str) {
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }

        async function update() {
            try {
                const result = await apiFetch('/api/saas/health');
                if (!result.ok) {
                    console.error('SaaS health fetch failed:', result.error);
                    document.getElementById('servicesList').innerHTML =
                        '<div class="loading">Failed to load SaaS health data</div>';
                    return;
                }
                const data = result.data;

                // Update overall health
                updateOverallHealth(data);

                // Update categories grid
                updateCategories(data.categories || {});

                // Update service details
                updateServices(data.services || []);

                // Update incidents
                updateIncidents(data.incidents || []);

            } catch (e) {
                console.error('SaaS health widget update failed:', e);
                document.getElementById('servicesList').innerHTML =
                    '<div class="loading">Failed to load SaaS health data</div>';
            }
        }

        function updateOverallHealth(data) {
            const summary = data.summary || {};

            // Overall health percentage
            const healthEl = document.getElementById('overallHealth');
            const availability = summary.avg_availability || 0;
            healthEl.textContent = availability.toFixed(1) + '%';
            healthEl.className = 'metric-value ' + getHealthClass(availability);

            // Average latency
            const latencyEl = document.getElementById('avgLatency');
            const latency = summary.avg_latency || 0;
            latencyEl.textContent = Math.round(latency) + 'ms';
            latencyEl.className = 'metric-value ' + getLatencyClass(latency);

            // Services up count
            const servicesUpEl = document.getElementById('servicesUp');
            const upCount = summary.services_up || 0;
            const totalCount = summary.total_services || 0;
            servicesUpEl.textContent = `${upCount}/${totalCount}`;
            servicesUpEl.className = 'metric-value ' +
                (upCount === totalCount ? 'excellent' : upCount > totalCount * 0.8 ? 'good' : 'degraded');
        }

        function updateCategories(categories) {
            const grid = document.getElementById('categoriesGrid');

            const categoryIcons = {
                'Office365': '📊',
                'GoogleWorkspace': '📧',
                'Zoom': '📹',
                'AWS': '☁️',
                'Slack': '💬',
                'Salesforce': '📈',
                'CDN': '🌐',
                'Teams': '👥',
                'GoogleMeet': '🎥'
            };

            const html = Object.entries(categories).map(([name, data]) => {
                const availability = data.availability_percent || 0;
                const healthClass = getHealthClass(availability);
                const icon = categoryIcons[name] || '🔧';

                return `
                    <div class="category-card ${healthClass}">
                        <div class="category-icon">${icon}</div>
                        <div class="category-name">${escapeHtml(name)}</div>
                        <div class="availability-badge ${healthClass}">
                            ${availability.toFixed(1)}%
                        </div>
                        <div class="category-status">
                            ${Math.round(data.avg_latency || 0)}ms avg
                        </div>
                    </div>
                `;
            }).join('');

            grid.innerHTML = html || '<div class="loading">No categories available</div>';
        }

        function updateServices(services) {
            const list = document.getElementById('servicesList');

            if (services.length === 0) {
                list.innerHTML = '<div class="loading">No service data available</div>';
                return;
            }

            const html = services.map(service => {
                const reachable = service.reachable;
                const healthClass = reachable ? 'healthy' : 'down';
                const latency = service.latency_ms || 0;

                return `
                    <div class="service-item ${healthClass}">
                        <div class="service-info">
                            <div class="service-name">${escapeHtml(service.endpoint_name || 'Unknown')}</div>
                            <div class="service-endpoint">${escapeHtml(service.host || '')}</div>
                        </div>
                        <div class="service-metrics">
                            <div class="metric-item">
                                <div class="metric-item-value">${reachable ? '✓' : '✗'}</div>
                                <div class="metric-item-label">Status</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-item-value">${Math.round(latency)}ms</div>
                                <div class="metric-item-label">Latency</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            list.innerHTML = html;
        }

        function updateIncidents(incidents) {
            const list = document.getElementById('incidentsList');

            if (incidents.length === 0) {
                list.innerHTML = '<div class="no-incidents">✓ No recent incidents</div>';
                return;
            }

            const html = incidents.slice(0, 10).map(incident => {
                const time = new Date(incident.timestamp);
                const timeAgo = getTimeAgo(time);

                return `
                    <div class="incident-item">
                        <div class="incident-header">
                            <span class="incident-service">${escapeHtml(incident.endpoint_name || 'Unknown')}</span>
                            <span class="incident-time">${escapeHtml(timeAgo)}</span>
                        </div>
                        <div class="incident-details">
                            ${escapeHtml(incident.details || incident.incident_type || 'Service outage')}
                            ${incident.duration_seconds ? ` (${formatDuration(incident.duration_seconds)})` : ''}
                        </div>
                    </div>
                `;
            }).join('');

            list.innerHTML = html;
        }

        function getHealthClass(availability) {
            if (availability >= 99.5) return 'excellent';
            if (availability >= 95) return 'good';
            if (availability >= 80) return 'degraded';
            return 'down';
        }

        function getLatencyClass(latency) {
            if (latency < 100) return 'excellent';
            if (latency < 300) return 'good';
            if (latency < 1000) return 'degraded';
            return 'down';
        }

        function getTimeAgo(date) {
            const seconds = Math.floor((new Date() - date) / 1000);

            if (seconds < 60) return 'Just now';
            if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
            if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
            return Math.floor(seconds / 86400) + 'd ago';
        }

        function formatDuration(seconds) {
            if (seconds < 60) return `${Math.round(seconds)}s`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
            return `${Math.floor(seconds / 3600)}h`;
        }

        // Initial update
        update();

        // Update every 15 seconds
        const _ivUpdate = setInterval(update, UPDATE_INTERVAL.RELAXED);
'''

    html_end = '''
        window.addEventListener('beforeunload', () => { clearInterval(_ivUpdate); });
    </script>
</body>
</html>'''

    return html_start + base_styles + widget_styles + api_helpers + toast_script + widget_script + html_end


# Export
__all__ = ['get_saas_health_widget_html']
