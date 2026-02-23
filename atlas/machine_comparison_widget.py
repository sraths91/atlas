"""
Multi-Machine Comparison Widget

Provides side-by-side comparison of metrics across multiple machines in a fleet.
Features:
- Compare CPU, memory, disk, network metrics across machines
- Ranking by different metrics
- Identify outliers and anomalies
- Historical comparison charts

Note: This widget is designed for fleet mode but can work standalone
by comparing historical snapshots of the current machine.
"""

from typing import Dict, Any, List


def get_machine_comparison_widget_html() -> str:
    """Generate the Multi-Machine Comparison widget HTML"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATLAS - Machine Comparison</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
            max-width: 1600px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        h1 {
            font-size: 24px;
            font-weight: 600;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        h1::before {
            content: "\\1F4BB";
            font-size: 28px;
        }

        .controls {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .btn {
            padding: 8px 16px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #e4e4e4;
        }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.15);
        }

        .metric-selector {
            display: flex;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 4px;
        }

        .metric-btn {
            padding: 8px 16px;
            border: none;
            background: transparent;
            color: #888;
            cursor: pointer;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .metric-btn.active {
            background: rgba(102, 126, 234, 0.3);
            color: #fff;
        }

        .metric-btn:hover:not(.active) {
            color: #ccc;
        }

        .fleet-mode-notice {
            background: rgba(52, 152, 219, 0.2);
            border: 1px solid rgba(52, 152, 219, 0.3);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .fleet-mode-notice.standalone {
            background: rgba(243, 156, 18, 0.2);
            border-color: rgba(243, 156, 18, 0.3);
        }

        .fleet-mode-notice span {
            font-size: 24px;
        }

        .fleet-mode-notice p {
            font-size: 14px;
            color: #ccc;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .stat-card h3 {
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }

        .stat-value-large {
            font-size: 32px;
            font-weight: 700;
            color: #fff;
        }

        .stat-subtitle {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }

        .comparison-section {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #fff;
        }

        .chart-container {
            height: 300px;
            position: relative;
        }

        .machine-table {
            width: 100%;
            border-collapse: collapse;
        }

        .machine-table th,
        .machine-table td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }

        .machine-table th {
            font-size: 12px;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .machine-table tr:hover {
            background: rgba(255,255,255,0.02);
        }

        .machine-name {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .machine-status {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        .machine-status.online { background: #2ecc71; }
        .machine-status.offline { background: #e74c3c; }
        .machine-status.warning { background: #f39c12; }

        .metric-bar {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .metric-bar-bg {
            flex: 1;
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }

        .metric-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .metric-bar-fill.low { background: #2ecc71; }
        .metric-bar-fill.medium { background: #f39c12; }
        .metric-bar-fill.high { background: #e74c3c; }

        .metric-value {
            min-width: 50px;
            text-align: right;
            font-weight: 600;
            font-size: 14px;
        }

        .rank-badge {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
        }

        .rank-badge.gold { background: linear-gradient(135deg, #f39c12, #e67e22); color: #fff; }
        .rank-badge.silver { background: linear-gradient(135deg, #95a5a6, #7f8c8d); color: #fff; }
        .rank-badge.bronze { background: linear-gradient(135deg, #cd6133, #a04000); color: #fff; }
        .rank-badge.normal { background: rgba(255,255,255,0.1); color: #888; }

        .anomaly-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .anomaly-indicator.high {
            background: rgba(231, 76, 60, 0.2);
            color: #e74c3c;
        }

        .anomaly-indicator.normal {
            background: rgba(46, 204, 113, 0.2);
            color: #2ecc71;
        }

        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 60px;
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

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr 1fr;
            }

            .machine-table {
                font-size: 13px;
            }

            .controls {
                flex-wrap: wrap;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Machine Comparison</h1>
                <p style="color: #666; font-size: 13px; margin-top: 4px;">Compare metrics across your fleet</p>
            </div>
            <div class="controls">
                <div class="metric-selector">
                    <button class="metric-btn active" data-metric="cpu">CPU</button>
                    <button class="metric-btn" data-metric="memory">Memory</button>
                    <button class="metric-btn" data-metric="disk">Disk</button>
                    <button class="metric-btn" data-metric="network">Network</button>
                </div>
                <button class="btn btn-secondary" onclick="refreshData()">Refresh</button>
            </div>
        </header>

        <div class="fleet-mode-notice" id="fleet-notice">
            <span>\\u2139\\uFE0F</span>
            <div>
                <strong>Checking fleet status...</strong>
                <p>Connecting to fleet server to retrieve machine data.</p>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Machines</h3>
                <div class="stat-value-large" id="total-machines">--</div>
                <div class="stat-subtitle">in fleet</div>
            </div>
            <div class="stat-card">
                <h3>Online</h3>
                <div class="stat-value-large" id="online-machines">--</div>
                <div class="stat-subtitle" id="online-pct">--%</div>
            </div>
            <div class="stat-card">
                <h3>Fleet Average</h3>
                <div class="stat-value-large" id="fleet-avg">--%</div>
                <div class="stat-subtitle" id="selected-metric">CPU usage</div>
            </div>
            <div class="stat-card">
                <h3>Anomalies Detected</h3>
                <div class="stat-value-large" id="anomaly-count">--</div>
                <div class="stat-subtitle">machines above threshold</div>
            </div>
        </div>

        <div class="comparison-section">
            <div class="section-header">
                <span class="section-title">Metric Distribution</span>
            </div>
            <div class="chart-container">
                <canvas id="distribution-chart" role="img" aria-label="Machine metric distribution chart"></canvas>
                <div class="sr-only" id="distributionChartDesc">Distribution chart comparing machine metrics across the fleet.</div>
            </div>
        </div>

        <div class="comparison-section">
            <div class="section-header">
                <span class="section-title">Machine Rankings</span>
            </div>
            <table class="machine-table" id="machine-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Machine</th>
                        <th>CPU</th>
                        <th>Memory</th>
                        <th>Disk</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="machine-tbody">
                    <tr>
                        <td colspan="6" class="loading">Loading machines...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let distributionChart;
        let currentMetric = 'cpu';
        let machines = [];
        let isFleetMode = false;

        function createChart() {
            const ctx = document.getElementById('distribution-chart').getContext('2d');
            distributionChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU %',
                        data: [],
                        backgroundColor: [],
                        borderRadius: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false,
                        },
                        tooltip: {
                            backgroundColor: 'rgba(26, 26, 46, 0.95)',
                            titleColor: '#fff',
                            bodyColor: '#ccc',
                            padding: 12,
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: {
                                color: 'rgba(255,255,255,0.05)',
                            },
                            ticks: {
                                color: '#666',
                                callback: v => v + '%',
                            },
                        },
                        x: {
                            grid: {
                                display: false,
                            },
                            ticks: {
                                color: '#888',
                                maxRotation: 45,
                            },
                        },
                    },
                },
            });
        }

        async function loadData() {
            try {
                // First check if we're in fleet mode
                const healthRes = await fetch('/api/agent/health');
                const health = await healthRes.json();

                if (health.fleet_server_url) {
                    isFleetMode = true;
                    await loadFleetData(health.fleet_server_url);
                } else {
                    isFleetMode = false;
                    loadStandaloneData();
                }
            } catch (err) {
                console.error('Failed to load data:', err);
                loadStandaloneData();
            }
        }

        async function loadFleetData(fleetUrl) {
            document.getElementById('fleet-notice').innerHTML = `
                <span>\\u2705</span>
                <div>
                    <strong>Fleet Mode Active</strong>
                    <p>Connected to ${fleetUrl}. Comparing machines in your fleet.</p>
                </div>
            `;
            document.getElementById('fleet-notice').classList.remove('standalone');

            try {
                // Fetch machines from fleet server
                const res = await fetch(`${fleetUrl}/api/machines`);
                if (!res.ok) throw new Error('Failed to fetch fleet machines');

                const data = await res.json();
                machines = data.machines || [];

                updateStats();
                updateChart();
                updateTable();
            } catch (err) {
                console.error('Fleet data error:', err);
                // Fall back to current machine
                loadStandaloneData();
            }
        }

        async function loadStandaloneData() {
            document.getElementById('fleet-notice').innerHTML = `
                <span>\\u2139\\uFE0F</span>
                <div>
                    <strong>Standalone Mode</strong>
                    <p>Not connected to a fleet server. Showing current machine stats only. <a href="/help#fleet" style="color: #3498db;">Learn about Fleet Mode</a></p>
                </div>
            `;
            document.getElementById('fleet-notice').classList.add('standalone');

            try {
                // Get current machine stats
                const res = await fetch('/api/stats');
                const stats = await res.json();

                // Get hostname
                let hostname = 'This Machine';
                try {
                    const healthRes = await fetch('/api/agent/health');
                    const health = await healthRes.json();
                    hostname = health.hostname || 'This Machine';
                } catch (e) {}

                machines = [{
                    machine_id: 'current',
                    hostname: hostname,
                    status: 'online',
                    metrics: {
                        cpu: stats.cpu || 0,
                        memory: stats.memory || 0,
                        disk: stats.disk || 0,
                        network_up: stats.network_up || 0,
                        network_down: stats.network_down || 0,
                    },
                    last_seen: new Date().toISOString(),
                }];

                updateStats();
                updateChart();
                updateTable();
            } catch (err) {
                console.error('Failed to load standalone data:', err);
            }
        }

        function updateStats() {
            const total = machines.length;
            const online = machines.filter(m => m.status === 'online').length;

            document.getElementById('total-machines').textContent = total;
            document.getElementById('online-machines').textContent = online;
            document.getElementById('online-pct').textContent = total > 0 ? Math.round(online / total * 100) + '%' : '0%';

            // Calculate average for selected metric
            const values = machines
                .filter(m => m.status === 'online' && m.metrics)
                .map(m => m.metrics[currentMetric] || 0);

            const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
            document.getElementById('fleet-avg').textContent = avg.toFixed(1) + '%';

            // Update metric label
            const metricLabels = {
                cpu: 'CPU usage',
                memory: 'Memory usage',
                disk: 'Disk usage',
                network: 'Network activity',
            };
            document.getElementById('selected-metric').textContent = metricLabels[currentMetric];

            // Count anomalies (above 80%)
            const threshold = 80;
            const anomalies = values.filter(v => v > threshold).length;
            document.getElementById('anomaly-count').textContent = anomalies;
        }

        function updateChart() {
            const onlineMachines = machines.filter(m => m.status === 'online' && m.metrics);

            // Sort by current metric (descending)
            onlineMachines.sort((a, b) => (b.metrics[currentMetric] || 0) - (a.metrics[currentMetric] || 0));

            const labels = onlineMachines.map(m => m.hostname || m.machine_id?.substring(0, 8) || 'Unknown');
            const values = onlineMachines.map(m => m.metrics[currentMetric] || 0);
            const colors = values.map(v => {
                if (v > 80) return 'rgba(231, 76, 60, 0.8)';
                if (v > 60) return 'rgba(243, 156, 18, 0.8)';
                return 'rgba(102, 126, 234, 0.8)';
            });

            distributionChart.data.labels = labels;
            distributionChart.data.datasets[0].data = values;
            distributionChart.data.datasets[0].backgroundColor = colors;
            distributionChart.data.datasets[0].label = currentMetric.toUpperCase() + ' %';
            distributionChart.update();
        }

        function updateTable() {
            const tbody = document.getElementById('machine-tbody');

            if (machines.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><h3>No Machines Found</h3><p>Connect to a fleet server to compare machines.</p></td></tr>';
                return;
            }

            // Sort by current metric
            const sorted = [...machines]
                .filter(m => m.metrics)
                .sort((a, b) => (b.metrics[currentMetric] || 0) - (a.metrics[currentMetric] || 0));

            tbody.innerHTML = sorted.map((machine, idx) => {
                const rank = idx + 1;
                const rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : 'normal';

                const cpu = machine.metrics?.cpu || 0;
                const memory = machine.metrics?.memory || 0;
                const disk = machine.metrics?.disk || 0;

                return `
                    <tr>
                        <td><div class="rank-badge ${rankClass}">${rank}</div></td>
                        <td>
                            <div class="machine-name">
                                <div class="machine-status ${machine.status || 'offline'}"></div>
                                <span>${machine.hostname || machine.machine_id?.substring(0, 8) || 'Unknown'}</span>
                            </div>
                        </td>
                        <td>${renderMetricBar(cpu)}</td>
                        <td>${renderMetricBar(memory)}</td>
                        <td>${renderMetricBar(disk)}</td>
                        <td>${renderStatus(machine)}</td>
                    </tr>
                `;
            }).join('');
        }

        function renderMetricBar(value) {
            const level = value > 80 ? 'high' : value > 60 ? 'medium' : 'low';
            return `
                <div class="metric-bar">
                    <div class="metric-bar-bg">
                        <div class="metric-bar-fill ${level}" style="width: ${Math.min(value, 100)}%"></div>
                    </div>
                    <span class="metric-value">${value.toFixed(0)}%</span>
                </div>
            `;
        }

        function renderStatus(machine) {
            // Check for anomalies
            const cpu = machine.metrics?.cpu || 0;
            const memory = machine.metrics?.memory || 0;

            if (cpu > 90 || memory > 90) {
                return '<span class="anomaly-indicator high">High Load</span>';
            }
            if (machine.status === 'offline') {
                return '<span class="anomaly-indicator high">Offline</span>';
            }
            return '<span class="anomaly-indicator normal">Normal</span>';
        }

        function refreshData() {
            loadData();
        }

        // Metric selector
        document.querySelectorAll('.metric-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.metric-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMetric = btn.dataset.metric;
                updateStats();
                updateChart();
                updateTable();
            });
        });

        // Initialize
        createChart();
        loadData();

        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
'''
