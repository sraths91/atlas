"""
Fleet Network Analysis Dashboard Page
Displays network analysis results across all machines in the fleet.
"""


def get_fleet_network_analysis_page() -> str:
    """Generate the fleet network analysis dashboard HTML"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fleet Network Analysis</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .header h1 {
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .nav-links {
            display: flex;
            gap: 15px;
        }
        
        .nav-links a {
            color: #4fc3f7;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 6px;
            transition: background 0.2s;
        }
        
        .nav-links a:hover {
            background: rgba(79, 195, 247, 0.2);
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .controls select, .controls button {
            padding: 10px 16px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.1);
            color: #fff;
            cursor: pointer;
            font-size: 14px;
        }
        
        .controls button:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .summary-card {
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        
        .summary-card .value {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .summary-card .label {
            color: #aaa;
            font-size: 13px;
        }
        
        .summary-card.healthy .value { color: #00c853; }
        .summary-card.warning .value { color: #ffd93d; }
        .summary-card.critical .value { color: #ff5252; }
        
        .health-score {
            font-size: 48px !important;
        }
        
        .machines-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .machine-card {
            background: rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: transform 0.2s, background 0.2s;
        }
        
        .machine-card:hover {
            transform: translateY(-2px);
            background: rgba(255,255,255,0.1);
        }
        
        .machine-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .machine-name {
            font-size: 18px;
            font-weight: 600;
        }
        
        .status-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-healthy { background: #00c853; color: #000; }
        .status-degraded { background: #ff5252; color: #fff; }
        .status-slowdowns { background: #4fc3f7; color: #000; }
        .status-poor { background: #ff9800; color: #000; }
        .status-unknown { background: #666; color: #fff; }
        
        .machine-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat .value {
            font-size: 20px;
            font-weight: 600;
        }
        
        .stat .label {
            font-size: 11px;
            color: #888;
        }
        
        .machine-message {
            font-size: 13px;
            color: #aaa;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .incidents-section {
            background: rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 20px;
            margin-top: 25px;
        }
        
        .incidents-section h2 {
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .incident-item {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #ff5252;
        }
        
        .incident-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .incident-machine {
            font-weight: 600;
            color: #4fc3f7;
        }
        
        .incident-time {
            font-size: 12px;
            color: #888;
        }
        
        .incident-summary {
            font-size: 14px;
            color: #ccc;
            margin-bottom: 10px;
        }
        
        .incident-factors {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .factor-tag {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            background: rgba(255,255,255,0.1);
        }
        
        .factor-tag.warning { background: rgba(255, 217, 61, 0.2); color: #ffd93d; }
        .factor-tag.critical { background: rgba(255, 82, 82, 0.2); color: #ff5252; }
        .factor-tag.info { background: rgba(79, 195, 247, 0.2); color: #4fc3f7; }
        
        .access-point-info {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: rgba(79, 195, 247, 0.1);
            border-radius: 6px;
            margin-bottom: 10px;
            font-size: 13px;
        }
        
        .ap-icon {
            font-size: 16px;
        }
        
        .ap-ssid {
            font-weight: 600;
            color: #4fc3f7;
        }
        
        .ap-bssid {
            color: #888;
            font-family: monospace;
            font-size: 11px;
        }
        
        .ap-details {
            margin-left: auto;
            color: #aaa;
            font-size: 12px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        
        .loading-spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255,255,255,0.1);
            border-radius: 50%;
            border-top-color: #4fc3f7;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .recommendations-list {
            margin-top: 10px;
            padding-left: 20px;
        }
        
        .recommendations-list li {
            font-size: 13px;
            color: #aaa;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Fleet Network Analysis</h1>
            <div class="nav-links">
                <a href="/dashboard">← Dashboard</a>
                <a href="/settings">Settings</a>
            </div>
        </div>
        
        <div class="controls">
            <select id="timeRange" onchange="loadAnalysis()">
                <option value="6">Last 6 Hours</option>
                <option value="24" selected>Last 24 Hours</option>
                <option value="48">Last 48 Hours</option>
                <option value="168">Last 7 Days</option>
            </select>
            <button onclick="loadAnalysis()">Refresh Analysis</button>
            <span id="lastUpdate" style="color: #666; font-size: 12px; margin-left: auto;"></span>
        </div>
        
        <div class="summary-cards" id="summaryCards">
            <div class="summary-card">
                <div class="value health-score" id="healthScore">-</div>
                <div class="label">Fleet Health Score</div>
            </div>
            <div class="summary-card">
                <div class="value" id="machinesAnalyzed">-</div>
                <div class="label">Machines Analyzed</div>
            </div>
            <div class="summary-card">
                <div class="value" id="machinesWithIssues">-</div>
                <div class="label">Machines with Issues</div>
            </div>
            <div class="summary-card">
                <div class="value" id="totalIncidents">-</div>
                <div class="label">Total Incidents</div>
            </div>
            <div class="summary-card">
                <div class="value" id="avgDownload">-</div>
                <div class="label">Avg Download (Mbps)</div>
            </div>
            <div class="summary-card">
                <div class="value" id="avgUpload">-</div>
                <div class="label">Avg Upload (Mbps)</div>
            </div>
        </div>
        
        <h2 style="margin-bottom: 15px;">Machine Status</h2>
        <div class="machines-grid" id="machinesGrid">
            <div class="loading">
                <div class="loading-spinner"></div>
                <p style="margin-top: 15px;">Loading network analysis...</p>
            </div>
        </div>
        
        <div class="incidents-section" id="incidentsSection" style="display: none;">
            <h2>🚨 Recent Incidents</h2>
            <div id="incidentsList"></div>
        </div>
    </div>
    
    <script>
        let analysisData = null;
        
        async function loadAnalysis() {
            const hours = document.getElementById('timeRange').value;
            const machinesGrid = document.getElementById('machinesGrid');
            
            machinesGrid.innerHTML = `
                <div class="loading" style="grid-column: 1/-1;">
                    <div class="loading-spinner"></div>
                    <p style="margin-top: 15px;">Analyzing network logs...</p>
                </div>
            `;
            
            try {
                const response = await fetch(`/api/fleet/network-analysis?hours=${hours}`, {
                    credentials: 'include'
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to load analysis');
                }
                
                analysisData = data;
                renderAnalysis(analysisData);
                
                document.getElementById('lastUpdate').textContent = 
                    'Last updated: ' + new Date().toLocaleTimeString();
                    
            } catch (error) {
                console.error('Error loading analysis:', error);
                machinesGrid.innerHTML = `
                    <div class="no-data" style="grid-column: 1/-1;">
                        <p>Error loading analysis</p>
                        <p style="font-size: 13px; margin-top: 10px;">${error.message}</p>
                    </div>
                `;
            }
        }
        
        function renderAnalysis(data) {
            // Update summary cards
            const healthScore = data.fleet_summary?.health_score || 0;
            const healthEl = document.getElementById('healthScore');
            healthEl.textContent = healthScore;
            healthEl.parentElement.className = 'summary-card ' + 
                (healthScore >= 80 ? 'healthy' : healthScore >= 50 ? 'warning' : 'critical');
            
            document.getElementById('machinesAnalyzed').textContent = data.machines_analyzed || 0;
            
            const issuesEl = document.getElementById('machinesWithIssues');
            issuesEl.textContent = data.machines_with_issues || 0;
            issuesEl.parentElement.className = 'summary-card ' + 
                (data.machines_with_issues === 0 ? 'healthy' : 'warning');
            
            const incidentsEl = document.getElementById('totalIncidents');
            incidentsEl.textContent = data.total_incidents || 0;
            incidentsEl.parentElement.className = 'summary-card ' + 
                (data.total_incidents === 0 ? 'healthy' : 'critical');
            
            document.getElementById('avgDownload').textContent = 
                (data.fleet_summary?.avg_download || 0).toFixed(1);
            document.getElementById('avgUpload').textContent = 
                (data.fleet_summary?.avg_upload || 0).toFixed(1);
            
            // Render machine cards
            const machinesGrid = document.getElementById('machinesGrid');
            
            if (!data.machine_reports || data.machine_reports.length === 0) {
                machinesGrid.innerHTML = `
                    <div class="no-data" style="grid-column: 1/-1;">
                        <p>No machines with network data</p>
                        <p style="font-size: 13px; margin-top: 10px;">
                            Machines need to send widget logs for analysis
                        </p>
                    </div>
                `;
                return;
            }
            
            machinesGrid.innerHTML = data.machine_reports.map(machine => `
                <div class="machine-card" onclick="showMachineDetail('${machine.machine_id}')">
                    <div class="machine-header">
                        <span class="machine-name">${machine.machine_id}</span>
                        <span class="status-badge status-${machine.overall_status || 'unknown'}">
                            ${machine.overall_status === 'slowdowns' ? 
                                `Slowdowns: ${machine.incidents_detected}` : 
                                machine.overall_status || 'Unknown'}
                        </span>
                    </div>
                    <div class="machine-stats">
                        <div class="stat">
                            <div class="value">${(machine.avg_download || 0).toFixed(1)}</div>
                            <div class="label">Download Mbps</div>
                        </div>
                        <div class="stat">
                            <div class="value">${(machine.avg_upload || 0).toFixed(1)}</div>
                            <div class="label">Upload Mbps</div>
                        </div>
                        <div class="stat">
                            <div class="value">${machine.incidents_detected || 0}</div>
                            <div class="label">Incidents</div>
                        </div>
                    </div>
                    <div class="machine-message">${machine.overall_message || 'No data'}</div>
                </div>
            `).join('');
            
            // Render incidents
            renderIncidents(data);
        }
        
        function renderIncidents(data) {
            const incidentsSection = document.getElementById('incidentsSection');
            const incidentsList = document.getElementById('incidentsList');
            
            // Collect all incidents from all machines
            const allIncidents = [];
            for (const machine of (data.machine_reports || [])) {
                for (const incident of (machine.incidents || [])) {
                    allIncidents.push({
                        ...incident,
                        machine_id: machine.machine_id
                    });
                }
            }
            
            if (allIncidents.length === 0) {
                incidentsSection.style.display = 'none';
                return;
            }
            
            // Sort by start time, most recent first
            allIncidents.sort((a, b) => 
                new Date(b.start_time) - new Date(a.start_time)
            );
            
            incidentsSection.style.display = 'block';
            incidentsList.innerHTML = allIncidents.slice(0, 10).map(incident => `
                <div class="incident-item">
                    <div class="incident-header">
                        <span class="incident-machine">${incident.machine_id}</span>
                        <span class="incident-time">
                            ${new Date(incident.start_time).toLocaleString()} 
                            (${incident.duration_minutes?.toFixed(0) || 0} min)
                        </span>
                    </div>
                    ${incident.access_point ? `
                        <div class="access-point-info">
                            <span class="ap-icon"></span>
                            <span class="ap-ssid">${incident.access_point.ssid || 'Unknown'}</span>
                            ${incident.access_point.bssid ? `
                                <span class="ap-bssid">(${incident.access_point.bssid})</span>
                            ` : ''}
                            <span class="ap-details">
                                Ch ${incident.access_point.channel || '?'} | 
                                ${incident.access_point.avg_rssi || '?'} dBm |
                                ${incident.access_point.tx_rate || '?'} Mbps
                            </span>
                        </div>
                    ` : ''}
                    <div class="incident-summary">${incident.summary || 'Network slowdown detected'}</div>
                    <div class="incident-factors">
                        ${(incident.factors || []).map(f => `
                            <span class="factor-tag ${f.severity}">${f.description}</span>
                        `).join('')}
                    </div>
                    ${incident.recommendations?.length > 0 ? `
                        <ul class="recommendations-list">
                            ${incident.recommendations.slice(0, 2).map(r => 
                                `<li>${r}</li>`
                            ).join('')}
                        </ul>
                    ` : ''}
                </div>
            `).join('');
        }
        
        function showMachineDetail(machineId) {
            window.location.href = `/machine/${machineId}`;
        }
        
        // Load on page load
        document.addEventListener('DOMContentLoaded', loadAnalysis);
        
        // Auto-refresh every 2 minutes
        setInterval(loadAnalysis, 120000);
    </script>
</body>
</html>'''
