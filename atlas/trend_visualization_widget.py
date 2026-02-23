"""
Trend Visualization Widget

Provides interactive 7-day trend charts for system metrics including:
- CPU usage over time
- Memory usage trends
- Network throughput
- Temperature patterns
- Disk usage changes

Uses Chart.js for visualization with zoom and pan capabilities.
"""

from typing import Dict, Any


def get_trend_visualization_widget_html() -> str:
    """Generate the Trend Visualization widget HTML"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATLAS - Trend Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
    <style>
        :root {
            --color-primary: #00E5A0;
            --color-secondary: #00c8ff;
            --color-success: #22c55e;
            --color-warning: #f59e0b;
            --color-error: #ff4444;
            --text-primary: #ffffff;
            --text-secondary: #b0b0b0;
            --text-muted: #888888;
            --bg-primary: #1a1a1a;
            --bg-elevated: #2a2a2a;
            --border-subtle: #333;
        }

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
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        h1::before {
            content: "\\1F4C8";
            font-size: 28px;
        }

        .controls {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .time-selector {
            display: flex;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 4px;
        }

        .time-btn {
            padding: 8px 16px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            cursor: pointer;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .time-btn.active {
            background: rgba(102, 126, 234, 0.3);
            color: var(--text-primary);
        }

        .time-btn:hover:not(.active) {
            color: #ccc;
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

        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #e4e4e4;
        }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.15);
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .stat-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .stat-change {
            font-size: 12px;
            margin-top: 4px;
        }

        .stat-change.up { color: #e74c3c; }
        .stat-change.down { color: #2ecc71; }
        .stat-change.neutral { color: var(--text-muted); }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 20px;
        }

        .chart-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .chart-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .chart-subtitle {
            font-size: 12px;
            color: #666;
            margin-top: 2px;
        }

        .chart-container {
            position: relative;
            height: 250px;
        }

        .legend-inline {
            display: flex;
            gap: 16px;
            font-size: 12px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-muted);
        }

        .legend-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            color: var(--text-muted);
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

        .no-data {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }

        .zoom-hint {
            text-align: center;
            font-size: 11px;
            color: #555;
            margin-top: 8px;
        }

        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }

            .chart-card {
                min-width: 0;
            }

            header {
                flex-direction: column;
                gap: 16px;
                align-items: flex-start;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Trend Visualization</h1>
                <p style="color: #666; font-size: 13px; margin-top: 4px;">Historical metrics analysis with interactive charts</p>
            </div>
            <div class="controls">
                <div class="time-selector">
                    <button class="time-btn" data-hours="1">1H</button>
                    <button class="time-btn" data-hours="6">6H</button>
                    <button class="time-btn" data-hours="24">24H</button>
                    <button class="time-btn active" data-hours="168">7D</button>
                </div>
                <button class="btn btn-secondary" onclick="refreshData()">Refresh</button>
            </div>
        </header>

        <div class="stats-row" id="stats-summary">
            <div class="stat-card">
                <div class="stat-label">Avg CPU</div>
                <div class="stat-value" id="stat-cpu">--%</div>
                <div class="stat-change neutral" id="stat-cpu-change">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Memory</div>
                <div class="stat-value" id="stat-memory">--%</div>
                <div class="stat-change neutral" id="stat-memory-change">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Temperature</div>
                <div class="stat-value" id="stat-temp">--°C</div>
                <div class="stat-change neutral" id="stat-temp-change">Loading...</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Peak CPU</div>
                <div class="stat-value" id="stat-peak-cpu">--%</div>
                <div class="stat-change neutral" id="stat-peak-time">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Data Points</div>
                <div class="stat-value" id="stat-points">--</div>
                <div class="stat-change neutral" id="stat-interval">--</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">CPU & GPU Usage</div>
                        <div class="chart-subtitle">Processing utilization over time</div>
                    </div>
                    <div class="legend-inline">
                        <div class="legend-item"><div class="legend-dot" style="background: #667eea;"></div> CPU</div>
                        <div class="legend-item"><div class="legend-dot" style="background: #f093fb;"></div> GPU</div>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="cpu-chart" role="img" aria-label="CPU usage trend chart"></canvas>
                </div>
                <div class="zoom-hint">Scroll to zoom, drag to pan</div>
            </div>

            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">Memory Usage</div>
                        <div class="chart-subtitle">RAM utilization percentage</div>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="memory-chart" role="img" aria-label="Memory usage trend chart"></canvas>
                </div>
                <div class="zoom-hint">Scroll to zoom, drag to pan</div>
            </div>

            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">Network Throughput</div>
                        <div class="chart-subtitle">Upload and download speeds</div>
                    </div>
                    <div class="legend-inline">
                        <div class="legend-item"><div class="legend-dot" style="background: #2ecc71;"></div> Download</div>
                        <div class="legend-item"><div class="legend-dot" style="background: #3498db;"></div> Upload</div>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="network-chart" role="img" aria-label="Network throughput trend chart"></canvas>
                </div>
                <div class="zoom-hint">Scroll to zoom, drag to pan</div>
            </div>

            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">Temperature</div>
                        <div class="chart-subtitle">CPU temperature readings</div>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="temp-chart" role="img" aria-label="Temperature trend chart"></canvas>
                </div>
                <div class="zoom-hint">Scroll to zoom, drag to pan</div>
            </div>
        </div>
    </div>

    <script>
        function cssVar(name) {
            return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        }

        let cpuChart, memoryChart, networkChart, tempChart;
        let currentHours = 168; // Default to 7 days
        let aggregatedData = null;

        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    titleColor: cssVar('--text-primary'),
                    bodyColor: '#ccc',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        title: function(items) {
                            if (!items.length) return '';
                            const date = new Date(items[0].parsed.x);
                            return date.toLocaleString();
                        }
                    }
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true,
                        },
                        mode: 'x',
                    },
                    pan: {
                        enabled: true,
                        mode: 'x',
                    },
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        displayFormats: {
                            hour: 'MMM d, HH:mm',
                            day: 'MMM d',
                        },
                    },
                    grid: {
                        color: 'rgba(255,255,255,0.05)',
                    },
                    ticks: {
                        color: '#666',
                        maxRotation: 0,
                    },
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255,255,255,0.05)',
                    },
                    ticks: {
                        color: '#666',
                    },
                },
            },
        };

        function createCharts() {
            const cpuCtx = document.getElementById('cpu-chart').getContext('2d');
            cpuChart = new Chart(cpuCtx, {
                type: 'line',
                data: {
                    datasets: [
                        {
                            label: 'CPU %',
                            data: [],
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                        },
                        {
                            label: 'GPU %',
                            data: [],
                            borderColor: '#f093fb',
                            backgroundColor: 'rgba(240, 147, 251, 0.1)',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                        },
                    ],
                },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            max: 100,
                            ticks: {
                                ...chartOptions.scales.y.ticks,
                                callback: v => v + '%',
                            },
                        },
                    },
                },
            });

            const memCtx = document.getElementById('memory-chart').getContext('2d');
            memoryChart = new Chart(memCtx, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Memory %',
                        data: [],
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.2)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                    }],
                },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            max: 100,
                            ticks: {
                                ...chartOptions.scales.y.ticks,
                                callback: v => v + '%',
                            },
                        },
                    },
                },
            });

            const netCtx = document.getElementById('network-chart').getContext('2d');
            networkChart = new Chart(netCtx, {
                type: 'line',
                data: {
                    datasets: [
                        {
                            label: 'Download KB/s',
                            data: [],
                            borderColor: '#2ecc71',
                            backgroundColor: 'rgba(46, 204, 113, 0.1)',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                        },
                        {
                            label: 'Upload KB/s',
                            data: [],
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                        },
                    ],
                },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            ticks: {
                                ...chartOptions.scales.y.ticks,
                                callback: v => formatBytes(v * 1024) + '/s',
                            },
                        },
                    },
                },
            });

            const tempCtx = document.getElementById('temp-chart').getContext('2d');
            tempChart = new Chart(tempCtx, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Temperature',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                    }],
                },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            suggestedMin: 20,
                            suggestedMax: 100,
                            ticks: {
                                ...chartOptions.scales.y.ticks,
                                callback: v => v + '°C',
                            },
                        },
                    },
                },
            });
        }

        async function loadData() {
            try {
                // Calculate interval based on time range
                let interval = 5; // minutes
                if (currentHours <= 1) interval = 1;
                else if (currentHours <= 6) interval = 2;
                else if (currentHours <= 24) interval = 5;
                else interval = 30; // 7 days

                const res = await fetch(`/api/metrics/aggregated?hours=${currentHours}&interval=${interval}`);
                if (!res.ok) throw new Error('Failed to fetch data');

                aggregatedData = await res.json();
                updateCharts();
                updateStats();
            } catch (err) {
                console.error('Failed to load data:', err);
                // Try falling back to raw metrics
                try {
                    const res = await fetch(`/api/metrics/history?hours=${currentHours}`);
                    if (res.ok) {
                        const data = await res.json();
                        processRawMetrics(data.metrics || []);
                    }
                } catch (e) {
                    console.error('Fallback also failed:', e);
                }
            }
        }

        function processRawMetrics(metrics) {
            // Convert raw metrics to chart format
            aggregatedData = {
                cpu: metrics.map(m => [m.timestamp * 1000, m.cpu_usage || 0]),
                gpu: metrics.map(m => [m.timestamp * 1000, m.gpu_usage || 0]),
                memory: metrics.map(m => [m.timestamp * 1000, m.memory_usage || 0]),
                temperature: metrics.map(m => [m.timestamp * 1000, m.temperature || 0]),
                network_up: metrics.map(m => [m.timestamp * 1000, (m.network_up || 0) / 1024]),
                network_down: metrics.map(m => [m.timestamp * 1000, (m.network_down || 0) / 1024]),
            };
            updateCharts();
            updateStats();
        }

        function updateCharts() {
            if (!aggregatedData) return;

            // Update CPU chart
            cpuChart.data.datasets[0].data = aggregatedData.cpu.map(d => ({x: d[0], y: d[1]}));
            cpuChart.data.datasets[1].data = aggregatedData.gpu.map(d => ({x: d[0], y: d[1]}));
            cpuChart.update('none');

            // Update Memory chart
            memoryChart.data.datasets[0].data = aggregatedData.memory.map(d => ({x: d[0], y: d[1]}));
            memoryChart.update('none');

            // Update Network chart
            networkChart.data.datasets[0].data = aggregatedData.network_down.map(d => ({x: d[0], y: d[1]}));
            networkChart.data.datasets[1].data = aggregatedData.network_up.map(d => ({x: d[0], y: d[1]}));
            networkChart.update('none');

            // Update Temperature chart
            tempChart.data.datasets[0].data = aggregatedData.temperature.map(d => ({x: d[0], y: d[1]}));
            tempChart.update('none');
        }

        function updateStats() {
            if (!aggregatedData) return;

            const cpuData = aggregatedData.cpu.map(d => d[1]).filter(v => v > 0);
            const memData = aggregatedData.memory.map(d => d[1]).filter(v => v > 0);
            const tempData = aggregatedData.temperature.map(d => d[1]).filter(v => v > 0);

            // Averages
            const avgCpu = cpuData.length ? (cpuData.reduce((a, b) => a + b, 0) / cpuData.length) : 0;
            const avgMem = memData.length ? (memData.reduce((a, b) => a + b, 0) / memData.length) : 0;
            const avgTemp = tempData.length ? (tempData.reduce((a, b) => a + b, 0) / tempData.length) : 0;

            document.getElementById('stat-cpu').textContent = avgCpu.toFixed(1) + '%';
            document.getElementById('stat-memory').textContent = avgMem.toFixed(1) + '%';
            document.getElementById('stat-temp').textContent = avgTemp.toFixed(0) + '°C';

            // Peak CPU
            const peakCpu = Math.max(...cpuData, 0);
            document.getElementById('stat-peak-cpu').textContent = peakCpu.toFixed(1) + '%';

            // Find peak time
            const peakIdx = cpuData.indexOf(peakCpu);
            if (peakIdx >= 0 && aggregatedData.cpu[peakIdx]) {
                const peakTime = new Date(aggregatedData.cpu[peakIdx][0]);
                document.getElementById('stat-peak-time').textContent = peakTime.toLocaleString();
            }

            // Data points
            document.getElementById('stat-points').textContent = cpuData.length.toLocaleString();

            // Interval
            let intervalStr = currentHours <= 1 ? '1 min' : currentHours <= 6 ? '2 min' : currentHours <= 24 ? '5 min' : '30 min';
            document.getElementById('stat-interval').textContent = intervalStr + ' intervals';

            // Calculate changes (compare first half to second half)
            if (cpuData.length > 10) {
                const midpoint = Math.floor(cpuData.length / 2);
                const firstHalf = cpuData.slice(0, midpoint);
                const secondHalf = cpuData.slice(midpoint);

                const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
                const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
                const cpuChange = secondAvg - firstAvg;

                const changeEl = document.getElementById('stat-cpu-change');
                changeEl.textContent = (cpuChange >= 0 ? '+' : '') + cpuChange.toFixed(1) + '% vs earlier';
                changeEl.className = 'stat-change ' + (cpuChange > 5 ? 'up' : cpuChange < -5 ? 'down' : 'neutral');
            }
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        function refreshData() {
            loadData();
        }

        // Time selector
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentHours = parseInt(btn.dataset.hours);
                loadData();
            });
        });

        // Initialize
        createCharts();
        loadData();

        // Auto-refresh every 5 minutes
        setInterval(loadData, 5 * 60 * 1000);
    </script>
</body>
</html>
'''
