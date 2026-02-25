"""
Page HTML Generators - Extracted from live_widgets.py

Standalone functions that generate full-page HTML content (homepage, help, dashboard).
"""
from atlas.dashboard_preferences import get_dashboard_preferences


def get_homepage_html():
    """Enhanced homepage showcasing all ATLAS features

    Returns HTML homepage with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Semantic HTML structure
    - Responsive design
    """
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATLAS Agent - System Monitor</title>
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
        color: #fff;
        min-height: 100vh;
        padding: 20px;
    }

    .container {
        max-width: 1400px;
        margin: 0 auto;
    }

    /* Header */
    header {
        text-align: center;
        margin-bottom: 50px;
        padding: 30px 0;
    }

    header h1 {
        font-size: 48px;
        background: linear-gradient(135deg, #00E5A0, #00C890);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 10px;
    }

    header p {
        font-size: 18px;
        color: #888;
    }

    .status-bar {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-top: 20px;
        flex-wrap: wrap;
    }

    .status-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(255,255,255,0.05);
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
    }

    .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #00E5A0;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* Category Sections */
    .category-section {
        margin-bottom: 50px;
    }

    .category-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 25px;
        padding-bottom: 15px;
        border-bottom: 2px solid rgba(0,255,0,0.3);
    }

    .category-icon {
        font-size: 32px;
    }

    .category-header h2 {
        font-size: 28px;
        color: #00E5A0;
    }

    .category-description {
        color: #999;
        font-size: 14px;
        margin-top: 5px;
    }

    /* Feature Cards Grid */
    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 20px;
    }

    .feature-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 15px;
        padding: 25px;
        transition: all 0.3s;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }

    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00E5A0, #00C890);
        transform: scaleX(0);
        transition: transform 0.3s;
    }

    .feature-card:hover {
        background: rgba(0,255,0,0.05);
        border-color: rgba(0,255,0,0.5);
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,255,0,0.2);
    }

    .feature-card:hover::before {
        transform: scaleX(1);
    }

    .feature-icon {
        font-size: 48px;
        margin-bottom: 15px;
    }

    .feature-title {
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 10px;
        color: #fff;
    }

    .feature-description {
        color: #aaa;
        font-size: 14px;
        line-height: 1.6;
        margin-bottom: 15px;
    }

    .feature-tags {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }

    .feature-tag {
        padding: 4px 10px;
        background: rgba(0,255,0,0.1);
        border: 1px solid rgba(0,255,0,0.3);
        border-radius: 12px;
        font-size: 11px;
        color: #00E5A0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .feature-tag.advanced {
        background: rgba(255,0,255,0.1);
        border-color: rgba(255,0,255,0.3);
        color: #ff00ff;
    }

    /* Tooltips */
    .info-icon {
        display: inline-block;
        width: 18px;
        height: 18px;
        line-height: 18px;
        text-align: center;
        background: rgba(79, 195, 247, 0.2);
        border: 1px solid rgba(79, 195, 247, 0.5);
        border-radius: 50%;
        font-size: 12px;
        color: #4fc3f7;
        cursor: help;
        margin-left: 6px;
        position: relative;
        vertical-align: middle;
    }

    .info-icon:hover {
        background: rgba(79, 195, 247, 0.3);
        border-color: #4fc3f7;
    }

    .tooltip-container {
        position: relative;
        display: inline-block;
    }

    .tooltip-text {
        visibility: hidden;
        width: 250px;
        background-color: #1a1a1a;
        color: #fff;
        text-align: left;
        border-radius: 8px;
        padding: 12px;
        position: absolute;
        z-index: 1000;
        bottom: 125%;
        left: 50%;
        margin-left: -125px;
        opacity: 0;
        transition: opacity 0.3s, visibility 0.3s;
        border: 1px solid #4fc3f7;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        font-size: 13px;
        line-height: 1.5;
    }

    .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #4fc3f7 transparent transparent transparent;
    }

    .info-icon:hover .tooltip-text,
    .tooltip-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }

    /* Quick Actions */
    .quick-actions {
        background: rgba(0,255,0,0.05);
        border: 2px solid rgba(0,255,0,0.2);
        border-radius: 15px;
        padding: 30px;
        margin-top: 50px;
        text-align: center;
    }

    .quick-actions h3 {
        color: #00E5A0;
        margin-bottom: 20px;
        font-size: 24px;
    }

    .action-buttons {
        display: flex;
        justify-content: center;
        gap: 15px;
        flex-wrap: wrap;
    }

    .action-button {
        padding: 12px 28px;
        background: linear-gradient(135deg, #00E5A0, #00C890);
        color: #0a0a0a;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
        text-decoration: none;
        display: inline-block;
    }

    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,255,0,0.4);
    }

    .action-button.secondary {
        background: rgba(255,255,255,0.1);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.3);
    }

    /* Footer */
    footer {
        margin-top: 60px;
        padding-top: 30px;
        border-top: 1px solid rgba(255,255,255,0.1);
        text-align: center;
        color: #666;
        font-size: 14px;
    }

    footer a {
        color: #00E5A0;
        text-decoration: none;
    }

    footer a:hover {
        text-decoration: underline;
    }

    /* Skip Link for Accessibility */
    .skip-link {
        position: absolute;
        top: -100%;
        left: 50%;
        transform: translateX(-50%);
        background: #00E5A0;
        color: #111;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
        z-index: 10000;
        transition: top 0.15s ease;
        text-decoration: none;
    }

    .skip-link:focus {
        top: 16px;
        outline: none;
    }

    /* Focus States */
    :focus {
        outline: none;
    }

    :focus-visible {
        outline: 2px solid #00E5A0;
        outline-offset: 2px;
    }

    /* Feature Card Focus State */
    .feature-card:focus-visible {
        outline: 2px solid #00E5A0;
        outline-offset: 4px;
    }

    /* Action Button Focus State */
    .action-button:focus-visible {
        outline: 2px solid #00E5A0;
        outline-offset: 2px;
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

<div class="container">
    <header role="banner">
        <h1>ATLAS Agent</h1>
        <p>Advanced Telemetry & Live Analysis System</p>
        <div class="status-bar">
            <div class="status-item tooltip-container">
                <div class="status-indicator"></div>
                <span>Agent Active</span>
                <span class="info-icon">ⓘ
                    <span class="tooltip-text">ATLAS agent is running and monitoring your system in real-time.</span>
                </span>
            </div>
            <div class="status-item tooltip-container">
                <span></span>
                <span>Local Processing</span>
                <span class="info-icon">ⓘ
                    <span class="tooltip-text">All data is processed and stored locally on your Mac. Nothing is sent to any cloud service.</span>
                </span>
            </div>
            <div class="status-item tooltip-container">
                <span></span>
                <span>7-Day Retention</span>
                <span class="info-icon">ⓘ
                    <span class="tooltip-text">Historical data is kept for 7 days, then automatically cleaned up to save disk space (~50-100MB).</span>
                </span>
            </div>
        </div>
    </header>

    <main id="main-content" role="main">
    <!-- Real-Time Monitoring Section -->
    <section class="category-section" aria-labelledby="monitoring-title">
        <div class="category-header">
            <div class="category-icon"></div>
            <div>
                <h2 id="monitoring-title">Real-Time Monitoring
                    <span class="info-icon" role="tooltip" aria-label="Information">ⓘ
                        <span class="tooltip-text">Monitor your Mac's system resources (CPU, memory, disk, network) and processes in real-time with live updates every few seconds.</span>
                    </span>
                </h2>
                <div class="category-description">Live system metrics and performance tracking</div>
            </div>
        </div>
        <div class="features-grid" role="list">
            <a class="feature-card" href="/dashboard" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">System Monitor</div>
                <div class="feature-description">
                    Real-time CPU, memory, disk, and network monitoring with beautiful visualizations. See exactly what your system is doing at any moment.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">Live</span>
                    <span class="feature-tag">Dashboard</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/processes" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">Process Monitor</div>
                <div class="feature-description">
                    Track running processes, resource usage, and kill misbehaving apps. Complete control over your system's processes.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">Management</span>
                    <span class="feature-tag">Control</span>
                </div>
            </a>
        </div>
    </section>

    <!-- Network Analysis Section -->
    <section class="category-section" aria-labelledby="network-title">
        <div class="category-header">
            <div class="category-icon" aria-hidden="true"></div>
            <div>
                <h2 id="network-title">Network Analysis
                    <span class="info-icon" role="tooltip" aria-label="Information">ⓘ
                        <span class="tooltip-text">Unique to ATLAS! Automatically identifies network slowdowns and correlates multiple data sources to explain WHY your internet is slow - not just that it is slow.</span>
                    </span>
                </h2>
                <div class="category-description">Advanced connectivity monitoring and diagnostics</div>
            </div>
        </div>
        <div class="features-grid" role="list">
            <a class="feature-card" href="/widget/wifi" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true">📶</div>
                <div class="feature-title">WiFi Quality Monitor</div>
                <div class="feature-description">
                    Track WiFi signal strength, SNR, quality scores, and connection events. Know when your WiFi is degrading before it affects your work.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">Real-Time</span>
                    <span class="feature-tag">Alerts</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/speedtest" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">Speed Test Monitor</div>
                <div class="feature-description">
                    Automated internet speed testing with historical tracking. Identify patterns and slowdowns over time.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">Automated</span>
                    <span class="feature-tag">History</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/network-analysis" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">Network Analysis</div>
                <div class="feature-description">
                    <strong>Unique to ATLAS:</strong> Automatic root cause analysis of network slowdowns. Correlates 5 data sources to explain WHY your internet is slow.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag advanced">Advanced</span>
                    <span class="feature-tag advanced">AI-Powered</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/osi-layers" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">OSI Layer Diagnostic</div>
                <div class="feature-description">
                    Test all 7 OSI layers from Physical to Application. Instantly pinpoint which network layer is causing issues with waterfall failure detection.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag advanced">Diagnostic</span>
                    <span class="feature-tag">7 Layers</span>
                </div>
            </a>
        </div>
    </section>

    <!-- Hardware & System Health Section -->
    <section class="category-section" aria-labelledby="hardware-title">
        <div class="category-header">
            <div class="category-icon" aria-hidden="true"></div>
            <div>
                <h2 id="hardware-title">Hardware & System Health
                    <span class="info-icon" role="tooltip" aria-label="Information">i
                        <span class="tooltip-text">Monitor hardware health, peripherals, security posture, and overall system status. Enterprise-grade monitoring for Mac fleets.</span>
                    </span>
                </h2>
                <div class="category-description">Comprehensive hardware and security monitoring</div>
            </div>
        </div>
        <div class="features-grid" role="list">
            <a class="feature-card" href="/widget/system-health" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">System Health Overview</div>
                <div class="feature-description">
                    Unified view of all system monitors. See the health status of every component at a glance with quick access to detailed views.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag advanced">Overview</span>
                    <span class="feature-tag">All Monitors</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/power" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">Power & Battery</div>
                <div class="feature-description">
                    Battery health, cycle count, thermal status, and power source monitoring. Track battery degradation over time.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">Battery</span>
                    <span class="feature-tag">Thermal</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/display" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">Display & Graphics</div>
                <div class="feature-description">
                    Connected displays, resolutions, GPU status, and VRAM usage. Perfect for troubleshooting multi-monitor setups.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">GPU</span>
                    <span class="feature-tag">Displays</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/peripherals" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">Peripherals</div>
                <div class="feature-description">
                    Bluetooth, USB, and Thunderbolt device monitoring. Track connected devices and battery levels.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">Bluetooth</span>
                    <span class="feature-tag">USB</span>
                </div>
            </a>

            <a class="feature-card" href="/widget/security-dashboard" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">Security Dashboard</div>
                <div class="feature-description">
                    Firewall, FileVault, SIP, Gatekeeper, and XProtect status. Ensure compliance with security policies.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag advanced">Compliance</span>
                    <span class="feature-tag">Security</span>
                </div>
            </a>
        </div>
    </section>

    <!-- Data Management Section -->
    <section class="category-section" aria-labelledby="data-title">
        <div class="category-header">
            <div class="category-icon" aria-hidden="true"></div>
            <div>
                <h2 id="data-title">Data Management
                    <span class="info-icon" role="tooltip" aria-label="Information">ⓘ
                        <span class="tooltip-text">Export your monitoring data in CSV or JSON format for analysis in Excel, Python, or other tools. Access via API or download files.</span>
                    </span>
                </h2>
                <div class="category-description">Export, analyze, and control your monitoring data</div>
            </div>
        </div>
        <div class="features-grid" role="list">
            <a class="feature-card" href="/dashboard" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true">⬇️</div>
                <div class="feature-title">CSV Exports</div>
                <div class="feature-description">
                    Export your data in CSV format for Excel, Google Sheets, or custom analysis. 4 data types (Speed Tests, Ping, WiFi, Events) with 3 time ranges each.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">12 Options</span>
                    <span class="feature-tag">Compatible</span>
                </div>
            </a>

            <a class="feature-card" href="/api/system/comprehensive" target="_blank" rel="noopener" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true"></div>
                <div class="feature-title">JSON API</div>
                <div class="feature-description">
                    Programmatic access to all metrics via RESTful API. Build custom integrations and automations.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">API</span>
                    <span class="feature-tag">Automation</span>
                </div>
            </a>

            <div class="feature-card" role="listitem" tabindex="0">
                <div class="feature-icon" aria-hidden="true">🗄️</div>
                <div class="feature-title">7-Day Retention</div>
                <div class="feature-description">
                    All data is stored locally for 7 days with automatic cleanup. Perfect balance of history and disk space.
                </div>
                <div class="feature-tags" aria-label="Tags">
                    <span class="feature-tag">Local</span>
                    <span class="feature-tag">Private</span>
                </div>
            </div>
        </div>
    </section>

    <!-- Quick Actions -->
    <section class="quick-actions" aria-label="Quick actions">
        <h3>Get Started</h3>
        <nav class="action-buttons" aria-label="Main navigation">
            <a href="/dashboard" class="action-button">Open Dashboard</a>
            <a href="/widget/network-analysis" class="action-button secondary">Network Analysis</a>
            <a href="/help" class="action-button secondary">Feature Guide</a>
        </nav>
    </section>
    </main>

    <!-- Footer -->
    <footer role="contentinfo">
        <p><strong>ATLAS Agent v1.0.0</strong> | Enterprise-grade monitoring for everyone</p>
        <nav style="margin-top: 10px;" aria-label="Footer navigation">
            <a href="/api/system/comprehensive">API Docs</a> ·
            <a href="/help">Help</a> ·
            <a href="/about">About</a>
        </nav>
        <p style="margin-top: 15px; color: #444;">
            All data processed locally • No cloud dependencies • Open source
        </p>
    </footer>
</div>
</body>
</html>'''

def get_help_html():
    """Help and feature discovery page

    Returns HTML help page with:
    - Comprehensive widget directory
    - API reference
    - Power user tips
    - Troubleshooting guide
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Semantic HTML structure
    - Responsive design
    """
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATLAS Help & Feature Guide</title>
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
        color: #fff;
        min-height: 100vh;
        padding: 20px;
        line-height: 1.6;
    }

    .container {
        max-width: 1400px;
        margin: 0 auto;
    }

    /* Header */
    header {
        text-align: center;
        margin-bottom: 40px;
        padding: 30px 0;
    }

    header h1 {
        font-size: 42px;
        background: linear-gradient(135deg, #00E5A0, #00C890);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 10px;
    }

    header p {
        font-size: 18px;
        color: #888;
    }

    .back-link {
        display: inline-block;
        margin-bottom: 20px;
        color: #00E5A0;
        text-decoration: none;
        padding: 8px 16px;
        border: 1px solid rgba(0,255,0,0.3);
        border-radius: 8px;
        transition: all 0.3s;
    }

    .back-link:hover {
        background: rgba(0,255,0,0.1);
        border-color: rgba(0,255,0,0.6);
    }

    /* Table of Contents */
    .toc {
        background: rgba(0,255,0,0.05);
        border: 1px solid rgba(0,255,0,0.2);
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 40px;
    }

    .toc h2 {
        color: #00E5A0;
        margin-bottom: 15px;
        font-size: 20px;
    }

    .toc-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 10px;
    }

    .toc a {
        color: #ccc;
        text-decoration: none;
        padding: 8px 12px;
        border-radius: 6px;
        transition: all 0.2s;
        display: block;
    }

    .toc a:hover {
        background: rgba(0,255,0,0.1);
        color: #00E5A0;
    }

    /* Section Styles */
    .section {
        margin-bottom: 50px;
    }

    .section-title {
        font-size: 28px;
        color: #00E5A0;
        margin-bottom: 25px;
        padding-bottom: 10px;
        border-bottom: 2px solid rgba(0,255,0,0.3);
    }

    .subsection-title {
        font-size: 22px;
        color: #00C890;
        margin: 30px 0 20px 0;
    }

    /* Widget Grid */
    .widget-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }

    .widget-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 20px;
        transition: all 0.3s;
        text-decoration: none;
        color: inherit;
        display: block;
    }

    .widget-card:hover {
        border-color: rgba(0,255,0,0.5);
        background: rgba(0,255,0,0.05);
        transform: translateY(-2px);
    }

    .widget-card h4 {
        color: #00E5A0;
        margin-bottom: 8px;
        font-size: 18px;
    }

    .widget-card p {
        color: #999;
        font-size: 14px;
        margin-bottom: 10px;
    }

    .widget-card code {
        background: rgba(0,0,0,0.4);
        padding: 2px 8px;
        border-radius: 4px;
        color: #00ffff;
        font-size: 12px;
    }

    .widget-category {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .cat-system { background: rgba(0,200,255,0.2); color: #00c8ff; }
    .cat-network { background: rgba(0,255,100,0.2); color: #00ff64; }
    .cat-diagnostic { background: rgba(255,180,0,0.2); color: #ffb400; }
    .cat-security { background: rgba(255,100,100,0.2); color: #ff6464; }
    .cat-hardware { background: rgba(200,100,255,0.2); color: #c864ff; }

    /* Feature Highlight */
    .feature-highlight {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(0,255,0,0.3);
        border-left: 4px solid #00E5A0;
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 20px;
    }

    .feature-highlight h3 {
        color: #00E5A0;
        font-size: 22px;
        margin-bottom: 15px;
    }

    .feature-highlight p {
        color: #bbb;
        margin-bottom: 12px;
    }

    .feature-highlight ul {
        list-style: none;
        padding: 0;
        margin: 15px 0;
    }

    .feature-highlight li {
        padding: 8px 0 8px 25px;
        position: relative;
        color: #ccc;
    }

    .feature-highlight li::before {
        content: "✓";
        position: absolute;
        left: 0;
        color: #00E5A0;
        font-weight: bold;
    }

    /* Action Buttons */
    .action-button {
        display: inline-block;
        margin-top: 10px;
        margin-right: 10px;
        padding: 10px 20px;
        background: linear-gradient(135deg, #00E5A0, #00C890);
        color: #0a0a0a;
        text-decoration: none;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.3s;
    }

    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,255,0,0.4);
    }

    .action-button.secondary {
        background: transparent;
        border: 1px solid rgba(0,255,0,0.5);
        color: #00E5A0;
    }

    .action-button.secondary:hover {
        background: rgba(0,255,0,0.1);
    }

    /* Quick Start Guide */
    .quickstart {
        background: rgba(0,255,0,0.05);
        border: 2px solid rgba(0,255,0,0.2);
        border-radius: 12px;
        padding: 30px;
        margin-bottom: 40px;
    }

    .quickstart h2 {
        color: #00E5A0;
        margin-bottom: 20px;
    }

    .quickstart ol {
        padding-left: 25px;
        color: #ccc;
    }

    .quickstart li {
        margin: 12px 0;
    }

    .quickstart strong {
        color: #fff;
    }

    .quickstart code {
        background: rgba(0,0,0,0.4);
        padding: 2px 8px;
        border-radius: 4px;
        color: #00ffff;
        font-size: 13px;
    }

    /* API Reference */
    .api-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 15px;
    }

    .api-item {
        background: rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        padding: 15px;
        font-family: 'SF Mono', Monaco, monospace;
    }

    .api-item .method {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 10px;
    }

    .api-item .method.get { background: rgba(0,200,100,0.3); color: #00ff64; }
    .api-item .method.post { background: rgba(0,150,255,0.3); color: #00c8ff; }

    .api-item .endpoint {
        color: #00ffff;
        font-size: 13px;
    }

    .api-item .desc {
        color: #888;
        font-size: 12px;
        margin-top: 8px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Tips Section */
    .tips-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
    }

    .tip-card {
        background: rgba(255,180,0,0.05);
        border: 1px solid rgba(255,180,0,0.2);
        border-radius: 12px;
        padding: 20px;
    }

    .tip-card h4 {
        color: #ffb400;
        margin-bottom: 10px;
    }

    .tip-card p {
        color: #bbb;
        font-size: 14px;
    }

    .tip-card code {
        background: rgba(0,0,0,0.4);
        padding: 2px 6px;
        border-radius: 4px;
        color: #00ffff;
        font-size: 12px;
    }

    /* Troubleshooting */
    .troubleshoot-item {
        background: rgba(255,100,100,0.05);
        border: 1px solid rgba(255,100,100,0.2);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }

    .troubleshoot-item h4 {
        color: #ff6464;
        margin-bottom: 10px;
    }

    .troubleshoot-item .solution {
        color: #00E5A0;
        margin-top: 10px;
    }

    .troubleshoot-item p {
        color: #bbb;
    }

    /* FAQ Section */
    details {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        margin-bottom: 12px;
        padding: 15px;
        cursor: pointer;
    }

    details summary {
        font-size: 17px;
        font-weight: 600;
        color: #fff;
        list-style: none;
        position: relative;
        padding-right: 30px;
    }

    details summary::after {
        content: "+";
        position: absolute;
        right: 10px;
        font-size: 24px;
        color: #00E5A0;
        transition: transform 0.3s;
    }

    details[open] summary::after {
        transform: rotate(45deg);
    }

    details p, details ul {
        margin-top: 15px;
        color: #bbb;
    }

    details ul {
        padding-left: 20px;
    }

    details li {
        margin: 8px 0;
    }

    details:hover {
        border-color: rgba(0,255,0,0.4);
    }

    /* Footer */
    footer {
        margin-top: 60px;
        padding-top: 30px;
        border-top: 1px solid rgba(255,255,255,0.1);
        text-align: center;
        color: #666;
    }

    footer a {
        color: #00E5A0;
        text-decoration: none;
    }

    footer a:hover {
        text-decoration: underline;
    }

    /* Skip Link for Accessibility */
    .skip-link {
        position: absolute;
        top: -100%;
        left: 50%;
        transform: translateX(-50%);
        background: #00E5A0;
        color: #111;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
        z-index: 10000;
        transition: top 0.15s ease;
        text-decoration: none;
    }

    .skip-link:focus {
        top: 16px;
        outline: none;
    }

    /* Focus States */
    :focus {
        outline: none;
    }

    :focus-visible {
        outline: 2px solid #00E5A0;
        outline-offset: 2px;
    }

    details:focus-visible {
        outline: 2px solid #00E5A0;
        outline-offset: 4px;
    }

    .action-button:focus-visible,
    .back-link:focus-visible,
    .widget-card:focus-visible {
        outline: 2px solid #00E5A0;
        outline-offset: 2px;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .widget-grid, .api-grid, .tips-grid {
            grid-template-columns: 1fr;
        }
        header h1 {
            font-size: 32px;
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
<a href="#main-content" class="skip-link">Skip to main content</a>

<div class="container">
    <nav aria-label="Breadcrumb">
        <a href="/" class="back-link">← Back to Home</a>
    </nav>

    <header role="banner">
        <h1>ATLAS Help & Feature Guide</h1>
        <p>Complete documentation for the Advanced Telemetry & Live Analysis System</p>
    </header>

    <main id="main-content" role="main">

    <!-- Table of Contents -->
    <nav class="toc" aria-labelledby="toc-title">
        <h2 id="toc-title">Quick Navigation</h2>
        <div class="toc-grid">
            <a href="#quickstart">Quick Start Guide</a>
            <a href="#widgets">All Widgets (25+)</a>
            <a href="#network-analysis">Network Analysis</a>
            <a href="#api-reference">API Reference</a>
            <a href="#power-tips">Power User Tips</a>
            <a href="#troubleshooting">Troubleshooting</a>
            <a href="#faq">FAQ</a>
            <a href="#keyboard">Keyboard Shortcuts</a>
        </div>
    </nav>

    <!-- Quick Start Guide -->
    <section id="quickstart" class="quickstart" aria-labelledby="quickstart-title">
        <h2 id="quickstart-title">Quick Start Guide</h2>
        <ol>
            <li>
                <strong>Dashboard:</strong> Open <code>http://localhost:8767</code> for the main dashboard with real-time widgets.
            </li>
            <li>
                <strong>Menu Bar:</strong> Click the ATLAS icon in your macOS menu bar for quick stats and actions.
            </li>
            <li>
                <strong>Network Issues?</strong> Go to <a href="/widget/network-analysis" style="color: #00E5A0;">Network Analysis</a> for automatic root cause analysis.
            </li>
            <li>
                <strong>Export Data:</strong> Dashboard menu → Export Data → Choose type and time range.
            </li>
            <li>
                <strong>Customize Layout:</strong> Dashboard menu → Customize Dashboard to show/hide widgets.
            </li>
            <li>
                <strong>API Access:</strong> Visit <code>/api/system/comprehensive</code> for JSON metrics.
            </li>
        </ol>
    </section>

    <!-- All Widgets Section -->
    <section id="widgets" class="section" aria-labelledby="widgets-title">
        <h2 class="section-title" id="widgets-title">All Widgets</h2>
        <p style="color: #888; margin-bottom: 25px;">Click any widget to open it. Each widget can be opened in its own window for multi-monitor setups.</p>

        <h3 class="subsection-title">System Monitoring</h3>
        <div class="widget-grid">
            <a href="/widget/cpu" class="widget-card">
                <span class="widget-category cat-system">System</span>
                <h4>CPU Monitor</h4>
                <p>Real-time CPU usage with per-core breakdown and load averages.</p>
                <code>/widget/cpu</code>
            </a>
            <a href="/widget/gpu" class="widget-card">
                <span class="widget-category cat-system">System</span>
                <h4>GPU Monitor</h4>
                <p>GPU utilization, memory usage, and temperature monitoring.</p>
                <code>/widget/gpu</code>
            </a>
            <a href="/widget/memory" class="widget-card">
                <span class="widget-category cat-system">System</span>
                <h4>Memory Monitor</h4>
                <p>RAM usage, swap usage, and memory pressure indicators.</p>
                <code>/widget/memory</code>
            </a>
            <a href="/widget/disk" class="widget-card">
                <span class="widget-category cat-system">System</span>
                <h4>Disk Monitor</h4>
                <p>Disk space usage, I/O rates, and mount point details.</p>
                <code>/widget/disk</code>
            </a>
            <a href="/widget/processes" class="widget-card">
                <span class="widget-category cat-system">System</span>
                <h4>Process Manager</h4>
                <p>Top processes by CPU/memory with search and kill capability.</p>
                <code>/widget/processes</code>
            </a>
            <a href="/widget/system-health" class="widget-card">
                <span class="widget-category cat-system">System</span>
                <h4>System Health</h4>
                <p>Overall system health score with component status.</p>
                <code>/widget/system-health</code>
            </a>
            <a href="/widget/system-monitor" class="widget-card">
                <span class="widget-category cat-system">System</span>
                <h4>System Monitor</h4>
                <p>Combined CPU, memory, disk, and network in one view.</p>
                <code>/widget/system-monitor</code>
            </a>
        </div>

        <h3 class="subsection-title">Network Monitoring</h3>
        <div class="widget-grid">
            <a href="/widget/network" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>Network I/O</h4>
                <p>Real-time bandwidth usage, bytes sent/received.</p>
                <code>/widget/network</code>
            </a>
            <a href="/widget/wifi" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>WiFi Status</h4>
                <p>Signal strength, quality, SSID, channel, and connection details.</p>
                <code>/widget/wifi</code>
            </a>
            <a href="/widget/wifi-analyzer" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>WiFi Analyzer</h4>
                <p>Channel analysis, nearby networks, interference detection.</p>
                <code>/widget/wifi-analyzer</code>
            </a>
            <a href="/widget/wifi-roaming" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>WiFi Roaming</h4>
                <p>Access point handoff tracking and roaming event history.</p>
                <code>/widget/wifi-roaming</code>
            </a>
            <a href="/widget/speedtest" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>Speed Test</h4>
                <p>Download/upload speeds with history and trend analysis.</p>
                <code>/widget/speedtest</code>
            </a>
            <a href="/widget/ping" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>Ping Monitor</h4>
                <p>Latency monitoring to gateway, DNS, and internet.</p>
                <code>/widget/ping</code>
            </a>
            <a href="/widget/vpn-status" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>VPN Status</h4>
                <p>VPN connection status and configuration details.</p>
                <code>/widget/vpn-status</code>
            </a>
            <a href="/widget/network-quality" class="widget-card">
                <span class="widget-category cat-network">Network</span>
                <h4>Network Quality</h4>
                <p>Overall network quality score and metrics.</p>
                <code>/widget/network-quality</code>
            </a>
        </div>

        <h3 class="subsection-title">Diagnostic Tools</h3>
        <div class="widget-grid">
            <a href="/widget/network-analysis" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Network Analysis</h4>
                <p>Automatic root cause analysis for network slowdowns. THE power feature.</p>
                <code>/widget/network-analysis</code>
            </a>
            <a href="/widget/speed-correlation" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Speed Correlation</h4>
                <p>Correlates speed test results with WiFi signal quality.</p>
                <code>/widget/speed-correlation</code>
            </a>
            <a href="/widget/network-path" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Network Path</h4>
                <p>Visual traceroute showing hops to destination.</p>
                <code>/widget/network-path</code>
            </a>
            <a href="/widget/network-testing" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Network Testing</h4>
                <p>VoIP quality, throughput, and connection rate testing in one tabbed view.</p>
                <code>/widget/network-testing</code>
            </a>
            <a href="/widget/osi-layers" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>OSI Layers</h4>
                <p>7-layer network diagnostic showing pass/fail per OSI layer with waterfall blocking.</p>
                <code>/widget/osi-layers</code>
            </a>
            <a href="/widget/alert-rules" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Alert Rules</h4>
                <p>Create custom alert rules with webhook and email notifications.</p>
                <code>/widget/alert-rules</code>
            </a>
            <a href="/widget/trends" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Trend Visualization</h4>
                <p>Interactive 7-day charts for CPU, memory, network, and temperature.</p>
                <code>/widget/trends</code>
            </a>
            <a href="/widget/comparison" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Machine Comparison</h4>
                <p>Compare metrics across multiple machines in your fleet.</p>
                <code>/widget/comparison</code>
            </a>
            <a href="/widget/tools" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>Network Tools</h4>
                <p>Collection of network diagnostic utilities.</p>
                <code>/widget/tools</code>
            </a>
            <a href="/widget/saas-health" class="widget-card">
                <span class="widget-category cat-diagnostic">Diagnostic</span>
                <h4>SaaS Health</h4>
                <p>Cloud service availability and response times.</p>
                <code>/widget/saas-health</code>
            </a>
        </div>

        <h3 class="subsection-title">Hardware & Security</h3>
        <div class="widget-grid">
            <a href="/widget/power" class="widget-card">
                <span class="widget-category cat-hardware">Hardware</span>
                <h4>Power & Battery</h4>
                <p>Battery level, charging status, power adapter info.</p>
                <code>/widget/power</code>
            </a>
            <a href="/widget/display" class="widget-card">
                <span class="widget-category cat-hardware">Hardware</span>
                <h4>Display Info</h4>
                <p>Connected displays, resolutions, and refresh rates.</p>
                <code>/widget/display</code>
            </a>
            <a href="/widget/peripherals" class="widget-card">
                <span class="widget-category cat-hardware">Hardware</span>
                <h4>Peripherals</h4>
                <p>Connected USB devices and peripherals.</p>
                <code>/widget/peripherals</code>
            </a>
            <a href="/widget/disk-health" class="widget-card">
                <span class="widget-category cat-hardware">Hardware</span>
                <h4>Disk Health</h4>
                <p>SMART data, disk health status, and predictions.</p>
                <code>/widget/disk-health</code>
            </a>
            <a href="/widget/security-dashboard" class="widget-card">
                <span class="widget-category cat-security">Security</span>
                <h4>Security Dashboard</h4>
                <p>Comprehensive security overview and recommendations.</p>
                <code>/widget/security-dashboard</code>
            </a>
            <a href="/widget/info" class="widget-card">
                <span class="widget-category cat-hardware">Hardware</span>
                <h4>System Info</h4>
                <p>macOS version, hardware specs, uptime.</p>
                <code>/widget/info</code>
            </a>
            <a href="/widget/health" class="widget-card">
                <span class="widget-category cat-hardware">Hardware</span>
                <h4>Health Overview</h4>
                <p>Combined health metrics across all components.</p>
                <code>/widget/health</code>
            </a>
        </div>
    </section>

    <!-- Network Analysis Deep Dive -->
    <section id="network-analysis" class="section" aria-labelledby="analysis-title">
        <h2 class="section-title" id="analysis-title">Network Analysis - Deep Dive</h2>

        <article class="feature-highlight">
            <h3>The Most Powerful Feature in ATLAS</h3>
            <p>
                While other monitors just show you that your internet is slow, ATLAS tells you <strong>WHY</strong>.
                The Network Analysis tool automatically correlates 5 data sources to identify the root cause of slowdowns.
            </p>

            <h4 style="color: #00C890; margin: 20px 0 10px;">How It Works</h4>
            <ul>
                <li><strong>Slowdown Detection:</strong> Identifies periods with 3+ consecutive slow speed tests (below 20 Mbps)</li>
                <li><strong>Data Correlation:</strong> Analyzes speed tests, WiFi quality, ping tests, network diagnostics, and WiFi events</li>
                <li><strong>Before/During Comparison:</strong> Compares 15 minutes before vs during the slowdown</li>
                <li><strong>Trigger Identification:</strong> Highlights events in the 2 minutes before issues started</li>
                <li><strong>Actionable Recommendations:</strong> Provides specific fixes, not generic advice</li>
            </ul>

            <h4 style="color: #00C890; margin: 20px 0 10px;">Example Output</h4>
            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; font-family: monospace; color: #ccc; margin: 15px 0;">
                <strong style="color: #ff6464;">Slowdown detected: 8:15 AM - 8:42 AM (27 minutes)</strong><br><br>
                <strong style="color: #ffb400;">Likely Triggers:</strong><br>
                &nbsp;&nbsp;• WiFi signal dropped from -55 dBm to -72 dBm<br>
                &nbsp;&nbsp;• SNR decreased from 45 dB to 23 dB<br>
                &nbsp;&nbsp;• Disconnect event at 8:14:32<br><br>
                <strong style="color: #00E5A0;">Recommendations:</strong><br>
                &nbsp;&nbsp;• Move closer to your WiFi router<br>
                &nbsp;&nbsp;• Switch to 5GHz band if available<br>
                &nbsp;&nbsp;• Check for interference sources near router
            </div>

            <a href="/widget/network-analysis" class="action-button">Open Network Analysis</a>
            <a href="/api/network/analysis" class="action-button secondary">View via API</a>
        </article>
    </section>

    <!-- API Reference -->
    <section id="api-reference" class="section" aria-labelledby="api-title">
        <h2 class="section-title" id="api-title">API Reference</h2>
        <p style="color: #888; margin-bottom: 25px;">All endpoints return JSON. Base URL: <code>http://localhost:8767</code></p>

        <h3 class="subsection-title">System Metrics</h3>
        <div class="api-grid">
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/system/comprehensive</span>
                <p class="desc">All system metrics in one call (CPU, memory, disk, network, processes)</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/stats</span>
                <p class="desc">Quick system stats summary</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/system/pressure</span>
                <p class="desc">Current system pressure (CPU, memory, I/O)</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/pressure/history/{period}</span>
                <p class="desc">Pressure history (10m, 1h, 24h, 7d)</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/processes</span>
                <p class="desc">List all processes with CPU/memory usage</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/processes/kill/{pid}</span>
                <p class="desc">Kill a process by PID</p>
            </div>
        </div>

        <h3 class="subsection-title">Network & WiFi</h3>
        <div class="api-grid">
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/wifi</span>
                <p class="desc">Current WiFi connection details</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/wifi/history</span>
                <p class="desc">WiFi quality history</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/wifi/nearby</span>
                <p class="desc">Nearby WiFi networks scan</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/wifi/channels</span>
                <p class="desc">WiFi channel utilization</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/wifi/roaming/events</span>
                <p class="desc">Access point roaming events</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/ping/stats</span>
                <p class="desc">Ping statistics (gateway, DNS, internet)</p>
            </div>
        </div>

        <h3 class="subsection-title">Speed Tests & Analysis</h3>
        <div class="api-grid">
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/speedtest</span>
                <p class="desc">Latest speed test result</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/speedtest/history</span>
                <p class="desc">Speed test history (7 days)</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/speedtest/run</span>
                <p class="desc">Trigger a new speed test</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/network/analysis</span>
                <p class="desc">Network slowdown analysis results</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/speed-correlation/analysis</span>
                <p class="desc">Speed vs WiFi signal correlation</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/traceroute</span>
                <p class="desc">Network path trace results</p>
            </div>
        </div>

        <h3 class="subsection-title">Data Export</h3>
        <div class="api-grid">
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/speedtest/export/{range}</span>
                <p class="desc">Export speed tests (1h, 24h, all) as CSV</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/ping/export/{range}</span>
                <p class="desc">Export ping data (1h, 24h, all) as CSV</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/wifi/export/{range}</span>
                <p class="desc">Export WiFi quality (1h, 24h, all) as CSV</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/wifi/events/export/{range}</span>
                <p class="desc">Export WiFi events (1h, 24h, all) as CSV</p>
            </div>
        </div>

        <h3 class="subsection-title">Dashboard & Settings</h3>
        <div class="api-grid">
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/dashboard/layout</span>
                <p class="desc">Get current dashboard layout</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/dashboard/layout</span>
                <p class="desc">Save dashboard layout preferences</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/notifications/enable</span>
                <p class="desc">Enable system notifications</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/wifi/alias/set</span>
                <p class="desc">Set custom name for a WiFi network</p>
            </div>
        </div>

        <h3 class="subsection-title">Alert Rules</h3>
        <div class="api-grid">
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/alerts/rules</span>
                <p class="desc">List all alert rules</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/alerts/rules</span>
                <p class="desc">Create a new alert rule</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/alerts/rules/{id}/update</span>
                <p class="desc">Update an existing rule</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/alerts/rules/{id}/delete</span>
                <p class="desc">Delete an alert rule</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/alerts/events</span>
                <p class="desc">Get alert event history</p>
            </div>
            <div class="api-item">
                <span class="method get">GET</span>
                <span class="endpoint">/api/alerts/statistics</span>
                <p class="desc">Get alert statistics (24h)</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/alerts/email-config</span>
                <p class="desc">Configure email notifications</p>
            </div>
            <div class="api-item">
                <span class="method post">POST</span>
                <span class="endpoint">/api/alerts/evaluate</span>
                <p class="desc">Manually evaluate rules against metrics</p>
            </div>
        </div>
    </section>

    <!-- Power User Tips -->
    <section id="power-tips" class="section" aria-labelledby="tips-title">
        <h2 class="section-title" id="tips-title">Power User Tips</h2>

        <div class="tips-grid">
            <div class="tip-card">
                <h4>Multi-Monitor Setup</h4>
                <p>Open individual widgets in separate browser windows and position them across monitors. Each widget at <code>/widget/...</code> is self-contained.</p>
            </div>
            <div class="tip-card">
                <h4>Custom WiFi Names</h4>
                <p>Give your networks friendly names via the WiFi widget settings. Names persist across sessions and appear in all widgets.</p>
            </div>
            <div class="tip-card">
                <h4>Kill Runaway Processes</h4>
                <p>In the Processes widget, search for any process and click the kill button. Works for any process you have permission to terminate.</p>
            </div>
            <div class="tip-card">
                <h4>Customize Dashboard</h4>
                <p>Use the hamburger menu → Customize Dashboard to show/hide widgets, change sizes, and reorder. Layout persists automatically.</p>
            </div>
            <div class="tip-card">
                <h4>Programmatic Access</h4>
                <p>Use <code>curl localhost:8767/api/stats</code> to get JSON metrics in scripts. All APIs are unauthenticated for local use.</p>
            </div>
            <div class="tip-card">
                <h4>Speed Test Modes</h4>
                <p>Switch between automatic (every 5 min), manual, or disabled speed testing via the Speed Test widget settings.</p>
            </div>
            <div class="tip-card">
                <h4>Historical Analysis</h4>
                <p>Export 7 days of data via the dashboard menu. Open in Excel/Google Sheets for custom analysis and visualization.</p>
            </div>
            <div class="tip-card">
                <h4>Fleet Mode</h4>
                <p>To report to a fleet server, run <code>python3 update_fleet_config.py</code> and provide your server URL and API key.</p>
            </div>
        </div>
    </section>

    <!-- Troubleshooting -->
    <section id="troubleshooting" class="section" aria-labelledby="trouble-title">
        <h2 class="section-title" id="trouble-title">Troubleshooting</h2>

        <div class="troubleshoot-item">
            <h4>Dashboard Won't Load</h4>
            <p>The page at localhost:8767 shows connection refused or timeout.</p>
            <p class="solution"><strong>Solution:</strong> Check if the agent is running. In Terminal: <code>pgrep -f live_widgets</code>. If not running, start with <code>python3 -m atlas.live_widgets</code></p>
        </div>

        <div class="troubleshoot-item">
            <h4>Speed Tests Not Running</h4>
            <p>Speed test widget shows no data or says "No speed tests yet."</p>
            <p class="solution"><strong>Solution:</strong> Check speed test mode in widget settings. If set to "Manual", click "Run Speed Test". Also verify internet connectivity.</p>
        </div>

        <div class="troubleshoot-item">
            <h4>WiFi Data Missing</h4>
            <p>WiFi widget shows "No data" or signal strength is N/A.</p>
            <p class="solution"><strong>Solution:</strong> Ensure you're connected to WiFi (not Ethernet). On macOS, grant Location Services permission to Terminal or the Python app.</p>
        </div>

        <div class="troubleshoot-item">
            <h4>High CPU Usage</h4>
            <p>The ATLAS agent is using excessive CPU resources.</p>
            <p class="solution"><strong>Solution:</strong> This usually means speed tests are running continuously. Switch to "Automatic" mode (5-min intervals) or "Manual" mode in Speed Test settings.</p>
        </div>

        <div class="troubleshoot-item">
            <h4>Network Analysis Shows No Slowdowns</h4>
            <p>Network Analysis says "No slowdowns detected" even when internet feels slow.</p>
            <p class="solution"><strong>Solution:</strong> The tool requires 3+ consecutive slow speed tests (below 20 Mbps) to detect a slowdown. Run more speed tests or wait for automatic tests to accumulate.</p>
        </div>

        <div class="troubleshoot-item">
            <h4>Widgets Not Updating</h4>
            <p>Data appears frozen or timestamps are old.</p>
            <p class="solution"><strong>Solution:</strong> Refresh the page (Cmd+R). If still frozen, check the agent logs at <code>~/Library/Logs/atlas-agent.log</code></p>
        </div>

        <div class="troubleshoot-item">
            <h4>Export Downloads Empty File</h4>
            <p>CSV export downloads but contains no data or just headers.</p>
            <p class="solution"><strong>Solution:</strong> There may be no data for the selected time range. Try "All Data" instead of "Last 1 Hour". Data is retained for 7 days.</p>
        </div>
    </section>

    <!-- Keyboard Shortcuts -->
    <section id="keyboard" class="section" aria-labelledby="keyboard-title">
        <h2 class="section-title" id="keyboard-title">Keyboard Shortcuts</h2>

        <div class="api-grid">
            <div class="api-item">
                <span class="method get" style="background: rgba(255,255,255,0.1); color: #fff;">Cmd+R</span>
                <span class="endpoint" style="color: #fff;">Refresh Dashboard</span>
            </div>
            <div class="api-item">
                <span class="method get" style="background: rgba(255,255,255,0.1); color: #fff;">Cmd+1-9</span>
                <span class="endpoint" style="color: #fff;">Quick access to widgets</span>
            </div>
            <div class="api-item">
                <span class="method get" style="background: rgba(255,255,255,0.1); color: #fff;">Cmd+K</span>
                <span class="endpoint" style="color: #fff;">Open search in Processes widget</span>
            </div>
            <div class="api-item">
                <span class="method get" style="background: rgba(255,255,255,0.1); color: #fff;">Esc</span>
                <span class="endpoint" style="color: #fff;">Close dialogs and menus</span>
            </div>
            <div class="api-item">
                <span class="method get" style="background: rgba(255,255,255,0.1); color: #fff;">Tab</span>
                <span class="endpoint" style="color: #fff;">Navigate between elements</span>
            </div>
            <div class="api-item">
                <span class="method get" style="background: rgba(255,255,255,0.1); color: #fff;">Enter</span>
                <span class="endpoint" style="color: #fff;">Activate focused button/link</span>
            </div>
        </div>
    </section>

    <!-- FAQ Section -->
    <section id="faq" class="section" aria-labelledby="faq-title">
        <h2 class="section-title" id="faq-title">Frequently Asked Questions</h2>

        <details>
            <summary>How long is data retained?</summary>
            <p>ATLAS retains <strong>7 days</strong> of monitoring data locally. Older data is automatically cleaned up. Storage usage is typically 50-100MB.</p>
        </details>

        <details>
            <summary>Can I use ATLAS without a fleet server?</summary>
            <p><strong>Yes!</strong> ATLAS works perfectly in standalone mode. All widgets, dashboards, exports, and analysis features work locally. Fleet mode is optional for managing multiple machines.</p>
        </details>

        <details>
            <summary>Is my data sent to any cloud service?</summary>
            <p><strong>No.</strong> In standalone mode, all data stays on your machine. Nothing is sent externally. In fleet mode, data only goes to YOUR fleet server (which you control).</p>
        </details>

        <details>
            <summary>What metrics does ATLAS collect?</summary>
            <ul>
                <li><strong>System:</strong> CPU, memory, disk, GPU, processes, battery, temperature</li>
                <li><strong>Network:</strong> Bandwidth, connections, packets, errors</li>
                <li><strong>WiFi:</strong> Signal (RSSI), SNR, quality, channel, nearby networks</li>
                <li><strong>Tests:</strong> Speed tests, ping latency, traceroute, VoIP quality</li>
                <li><strong>Hardware:</strong> Displays, peripherals, disk health</li>
                <li><strong>Security:</strong> Firewall, FileVault, SIP, Gatekeeper</li>
            </ul>
        </details>

        <details>
            <summary>How do I customize speed test thresholds?</summary>
            <p>You can customize thresholds via the <strong>Network Analysis widget settings</strong>:</p>
            <ol>
                <li>Open the <a href="/widget/network-analysis">Network Analysis</a> widget</li>
                <li>Click the <strong>Settings</strong> (⚙️) button</li>
                <li>Adjust the threshold values:
                    <ul>
                        <li><strong>Slow Download:</strong> Default 20 Mbps (set higher for gigabit connections)</li>
                        <li><strong>Slow Upload:</strong> Default 5 Mbps</li>
                        <li><strong>High Ping:</strong> Default 100 ms</li>
                        <li><strong>Consecutive Tests:</strong> Number of slow tests before alerting (default 3)</li>
                    </ul>
                </li>
                <li>Click <strong>Save</strong> to apply</li>
            </ol>
            <p>Settings are stored in <code>~/.config/atlas-agent/network_analysis_settings.json</code> and persist across restarts.</p>
            <p>You can also use the API: <code>POST /api/network/analysis/settings</code> with JSON body.</p>
        </details>

        <details>
            <summary>What's the difference between widgets and dashboard?</summary>
            <p>The <strong>dashboard</strong> shows multiple widgets in a grid layout. Individual <strong>widgets</strong> are standalone pages you can open in separate windows for multi-monitor setups.</p>
        </details>

        <details>
            <summary>How do I kill a problematic process?</summary>
            <p>Go to the Processes widget, search for the process, and click the kill (X) button. You can only kill processes you have permission to terminate.</p>
        </details>

        <details>
            <summary>Can I run ATLAS on startup?</summary>
            <p>Yes! Use the provided launchd plist files (<code>com.atlas.agent.plist</code>) or add ATLAS to your Login Items in System Preferences.</p>
        </details>

        <details>
            <summary>How accurate is the Network Analysis tool?</summary>
            <p>It correlates real data to identify patterns. It excels at detecting WiFi issues, router problems, and ISP issues. It cannot detect issues outside your network or intermittent problems that don't coincide with speed tests.</p>
        </details>

        <details>
            <summary>How do I export data for external analysis?</summary>
            <p>Use the dashboard hamburger menu → Export Data. Choose from Speed Tests, Ping, WiFi Quality, or WiFi Events, with time ranges of 1h, 24h, or all data. CSV files work with Excel, Google Sheets, and pandas.</p>
        </details>

        <details>
            <summary>What ports does ATLAS use?</summary>
            <ul>
                <li><strong>8767:</strong> Local agent dashboard (this server)</li>
                <li><strong>8778:</strong> Fleet server (if running in fleet mode)</li>
            </ul>
        </details>

        <details>
            <summary>How do I check agent health?</summary>
            <p>Visit <code>/api/agent/health</code> for a JSON health check, or <code>/api/health</code> for a simple status. The dashboard also shows agent status in the header.</p>
        </details>
    </section>

    </main>

    <!-- Footer -->
    <footer role="contentinfo">
        <p><strong>Need more help?</strong></p>
        <nav style="margin-top: 10px;" aria-label="Footer navigation">
            <a href="/">← Back to Home</a> ·
            <a href="/dashboard">Dashboard</a> ·
            <a href="/widget/network-analysis">Network Analysis</a> ·
            <a href="/api/system/comprehensive">API Explorer</a>
        </nav>
        <p style="margin-top: 20px; color: #444;">
            ATLAS Agent v2.0.0 | Advanced Telemetry & Live Analysis System | All data processed locally
        </p>
    </footer>
</div>
</body>
</html>'''

def _generate_widget_iframes():
    """Generate iframe HTML from dashboard preferences.

    Uses loading="lazy" for all widgets except the first two,
    so off-screen widgets don't load until scrolled to.
    Each iframe is wrapped in a container with a loading overlay.
    """
    prefs = get_dashboard_preferences()
    visible = prefs.get_visible_widgets()
    lines = []
    for i, w in enumerate(visible):
        loading = ' loading="lazy"' if i >= 2 else ''
        lines.append(
            f'        <div class="widget-iframe-container {w["size"]}" '
            f'style="height: {w["height"]};">'
            f'<div class="iframe-loading-overlay">'
            f'<div class="spinner"></div><span>Loading...</span></div>'
            f'<iframe src="{w["route"]}" '
            f'data-widget-id="{w["id"]}"{loading}></iframe></div>'
        )
    return '\n'.join(lines)

def get_dashboard_html():
    """Main dashboard with all widgets

    Returns HTML dashboard with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Responsive design
    - Custom export format dialog (replaces prompt())
    - Toast notification system (replaces alert())
    """
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Live Widget Dashboard - ATLAS Agent</title>
<style>
    /* ========================================
       CSS Custom Properties - Design System
       ======================================== */
    :root {{
        /* Typography — Fluid scaling with clamp() */
        --font-system: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
        --font-mono: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
        --text-xs: clamp(10px, 0.7vw, 11px);
        --text-sm: clamp(12px, 0.85vw, 13px);
        --text-base: clamp(14px, 1vw, 16px);
        --text-lg: clamp(16px, 1.15vw, 18px);
        --text-xl: clamp(18px, 1.4vw, 22px);
        --text-2xl: clamp(22px, 1.8vw, 28px);
        --text-3xl: clamp(26px, 2.2vw, 32px);

        /* 8px spacing grid */
        --space-1: 4px;
        --space-2: 8px;
        --space-3: 12px;
        --space-4: 16px;
        --space-5: 20px;
        --space-6: 24px;
        --space-7: 32px;
        --space-8: 40px;
        --space-9: 48px;
        --space-10: 64px;

        /* Colors - Primary Palette */
        --color-bg: #0c0c14;
        --color-bg-elevated: #161620;
        --color-bg-surface: #1c1c28;
        --color-bg-glass: rgba(22, 22, 32, 0.65);
        --color-text-primary: #E8E8F0;
        --color-text-secondary: #9898A8;
        --color-text-tertiary: #5C5C6E;

        /* Accent Colors */
        --color-accent: #00E5A0;
        --color-accent-hover: #00C890;
        --color-accent-dim: rgba(0, 229, 160, 0.12);
        --color-secondary: #00C8FF;
        --color-warning: #FFB84D;
        --color-error: #FF6B6B;
        --color-success: #4ECDC4;

        /* Borders & Dividers */
        --border-subtle: rgba(255, 255, 255, 0.04);
        --border-medium: rgba(255, 255, 255, 0.08);
        --border-accent: rgba(0, 229, 160, 0.35);
        --border-glass: rgba(255, 255, 255, 0.12);

        /* Shadows — layered depth system */
        --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.35), 0 2px 4px rgba(0, 0, 0, 0.25);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.45), 0 4px 8px rgba(0, 0, 0, 0.3);
        --shadow-glow: 0 0 24px rgba(0, 229, 160, 0.15);
        --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.3),
                       inset 0 1px 0 rgba(255, 255, 255, 0.04);

        /* Glass effect tokens */
        --glass-blur: blur(12px) saturate(160%);
        --glass-bg: rgba(22, 22, 32, 0.65);
        --glass-border: 1px solid var(--border-glass);
        --glass-inset: inset 0 1px 0 rgba(255, 255, 255, 0.06);

        /* Border radii */
        --radius-sm: 8px;
        --radius-md: 14px;
        --radius-lg: 20px;
        --radius-xl: 24px;

        /* Transitions */
        --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
    }}

    /* ========================================
       Base Styles
       ======================================== */
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}

    body {{
        background: var(--color-bg);
        color: var(--color-text-primary);
        font-family: var(--font-system);
        font-size: var(--text-base);
        line-height: 1.5;
        padding: var(--space-7);
        min-height: 100vh;
        position: relative;
        overflow-x: hidden;
    }}

    /* Ambient Mesh Gradient Background (Phase 2) */
    body::before {{
        content: '';
        position: fixed;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background:
            radial-gradient(circle at 20% 50%, rgba(0, 229, 160, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(0, 200, 255, 0.06) 0%, transparent 50%);
        filter: blur(60px);
        opacity: 0.6;
        z-index: -1;
        animation: mesh-float 30s ease-in-out infinite;
        will-change: transform;
        pointer-events: none;
    }}

    @keyframes mesh-float {{
        0%, 100% {{ transform: translate(0, 0) scale(1); }}
        33% {{ transform: translate(30px, -30px) scale(1.1); }}
        66% {{ transform: translate(-20px, 20px) scale(0.9); }}
    }}

    /* Typography (Phase 2) */
    h1 {{
        color: var(--color-accent);
        font-size: var(--text-3xl);
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 20px;
        text-align: center;
        background: linear-gradient(135deg, var(--color-accent), var(--color-secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    /* ========================================
       Header & Navigation
       ======================================== */
    .header-container {{
        max-width: 1600px;
        margin: 0 auto var(--space-8);
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        gap: var(--space-6);
    }}

    /* E2EE Status Badge */
    .e2ee-badge {{
        display: flex;
        align-items: center;
        gap: var(--space-2);
        padding: var(--space-2) var(--space-3);
        background: var(--color-bg-surface);
        border-radius: var(--radius-sm);
        border: 1px solid var(--border-medium);
        transition: border-color var(--transition-base);
    }}
    .e2ee-badge .e2ee-icon {{
        font-size: 18px;
    }}
    .e2ee-badge .e2ee-label {{
        font-size: var(--text-xs);
        color: var(--color-text-tertiary);
    }}

    /* Live Status Bar */
    .status-bar {{
        display: flex;
        align-items: center;
        gap: var(--space-6);
        padding: var(--space-2) var(--space-5);
        background: var(--color-bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        max-width: 1600px;
        margin: 0 auto var(--space-6);
        font-size: var(--text-xs);
        color: var(--color-text-secondary);
        overflow-x: auto;
    }}
    .status-bar .status-metric {{
        display: flex;
        align-items: center;
        gap: var(--space-2);
        white-space: nowrap;
    }}
    .status-bar .status-dot {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--color-success);
        flex-shrink: 0;
    }}
    .status-bar .status-dot.warn {{
        background: var(--color-warning);
    }}
    .status-bar .status-dot.error {{
        background: var(--color-error);
    }}
    .status-bar .status-value {{
        color: var(--color-text-primary);
        font-weight: 600;
        font-family: var(--font-mono);
    }}
    .status-bar .status-divider {{
        width: 1px;
        height: 16px;
        background: var(--border-medium);
        flex-shrink: 0;
    }}

    /* Header Branding */
    .header-branding {{
        text-align: center;
    }}
    .header-branding h1 {{
        margin: 0;
    }}
    .header-subtitle {{
        color: var(--color-text-tertiary);
        font-size: var(--text-sm);
        margin-top: var(--space-1);
        letter-spacing: 0.3px;
    }}

    /* Glassmorphic Hamburger Menu (Phase 1) */
    .hamburger {{
        width: 44px;
        height: 44px;
        background: var(--color-bg-glass);
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid var(--border-medium);
        border-radius: 12px;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 5px;
        transition: all var(--transition-base);
        box-shadow: var(--shadow-sm),
                    inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }}

    .hamburger:hover {{
        background: var(--color-accent-dim);
        border-color: var(--border-accent);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md), var(--shadow-glow);
    }}

    .hamburger span {{
        width: 20px;
        height: 2px;
        background: var(--color-accent);
        border-radius: 2px;
        transition: all var(--transition-base);
    }}

    .hamburger:hover span {{
        background: var(--color-accent-hover);
    }}
    .hamburger.active span:nth-child(1) {{
        transform: rotate(45deg) translate(6px, 6px);
    }}
    .hamburger.active span:nth-child(2) {{
        opacity: 0;
    }}
    .hamburger.active span:nth-child(3) {{
        transform: rotate(-45deg) translate(6px, -6px);
    }}
    /* Glassmorphic Menu (Phase 1) */
    .menu {{
        position: absolute;
        top: 56px;
        right: 0;
        background: var(--color-bg-glass);
        backdrop-filter: blur(40px) saturate(180%);
        border: 1px solid var(--border-medium);
        border-radius: 16px;
        padding: 12px;
        min-width: 280px;
        display: none;
        z-index: 1000;
        box-shadow: var(--shadow-lg),
                    inset 0 1px 0 rgba(255, 255, 255, 0.08);
        animation: menuSlideIn var(--transition-base);
    }}

    @keyframes menuSlideIn {{
        from {{
            opacity: 0;
            transform: translateY(-8px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    .submenu {{
        position: absolute;
        right: 100%;
        top: 0;
        background: var(--color-bg-glass);
        backdrop-filter: blur(40px) saturate(180%);
        border: 1px solid var(--border-medium);
        border-radius: 16px;
        padding: 12px;
        min-width: 280px;
        max-height: 80vh;
        overflow-y: auto;
        display: none;
        margin-right: 12px;
        box-shadow: var(--shadow-lg),
                    inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }}
    .submenu.active {{
        display: block;
    }}
    .submenu::-webkit-scrollbar {{
        width: 6px;
    }}
    .submenu::-webkit-scrollbar-track {{
        background: rgba(0, 0, 0, 0.2);
        border-radius: 8px;
    }}
    .submenu::-webkit-scrollbar-thumb {{
        background: var(--color-accent);
        border-radius: 8px;
    }}
    .submenu::-webkit-scrollbar-thumb:hover {{
        background: var(--color-accent-hover);
    }}

    .menu.active {{
        display: block;
    }}

    .menu-section {{
        margin-bottom: 16px;
    }}
    .menu-section:last-child {{
        margin-bottom: 0;
    }}

    .menu-title {{
        color: var(--color-accent);
        font-size: var(--text-xs);
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 600;
        margin-bottom: 8px;
        padding: 8px 12px;
        border-bottom: 1px solid var(--border-subtle);
    }}

    .menu-item {{
        padding: 12px 16px;
        cursor: pointer;
        border-radius: 10px;
        transition: all var(--transition-base);
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        font-size: var(--text-sm);
        color: var(--color-text-primary);
    }}

    .menu-item:hover {{
        background: var(--color-accent-dim);
        color: var(--color-accent);
        transform: translateX(-2px);
    }}

    .menu-item.has-submenu::before {{
        content: '‹';
        font-size: 20px;
        margin-right: 10px;
        opacity: 0.6;
    }}

    .menu-item.active {{
        background: var(--color-accent);
        color: var(--color-bg);
        font-weight: 600;
    }}

    .theme-preview {{
        width: 24px;
        height: 24px;
        border-radius: 6px;
        border: 1px solid var(--border-medium);
        box-shadow: var(--shadow-sm);
    }}
    /* ========================================
       Dashboard Grid — Bento Layout
       ======================================== */
    .dashboard {{
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: var(--space-6);
        max-width: 1600px;
        margin: 0 auto;
    }}

    /* Default grid column span */
    .dashboard > iframe,
    .dashboard > .widget-iframe-container {{
        grid-column: span 4;
    }}

    .dashboard > .stacked-container {{
        grid-column: span 4;
    }}

    /* Bento card sizes */
    .widget-span-1 {{
        grid-column: span 4 !important;
    }}

    .widget-span-2 {{
        grid-column: span 8 !important;
    }}

    .widget-full-width {{
        grid-column: 1 / -1 !important;
    }}

    /* Bento-style: first two widgets are wider for visual hierarchy */
    .dashboard > iframe:first-child,
    .dashboard > .widget-iframe-container:first-child {{
        grid-column: span 8;
    }}
    .dashboard > iframe:first-child,
    .dashboard > .widget-iframe-container:first-child {{
        min-height: 420px;
    }}

    /* Widget card label overlay */
    .widget-iframe-container {{
        position: relative;
    }}
    .widget-iframe-container::before {{
        content: attr(data-widget-name);
        position: absolute;
        top: var(--space-3);
        left: var(--space-4);
        font-size: var(--text-xs);
        font-weight: 600;
        color: var(--color-text-tertiary);
        text-transform: uppercase;
        letter-spacing: 1px;
        z-index: 2;
        background: var(--color-bg-surface);
        padding: 2px 10px;
        border-radius: var(--radius-sm);
        opacity: 0;
        transition: opacity var(--transition-base);
        pointer-events: none;
    }}
    .widget-iframe-container:hover::before {{
        opacity: 1;
    }}

    /* Widget iframe containers with loading overlays */
    .widget-iframe-container {{
        position: relative;
    }}

    .iframe-loading-overlay {{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: var(--space-3);
        background: var(--color-bg-elevated);
        border-radius: var(--radius-lg);
        border: 1px solid var(--border-medium);
        color: var(--color-text-secondary);
        font-size: var(--text-sm);
        z-index: 1;
        transition: opacity var(--transition-base);
    }}

    .iframe-loading-overlay .spinner {{
        width: 32px;
        height: 32px;
        border: 3px solid var(--border-medium);
        border-top-color: var(--color-accent);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }}

    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}

    .iframe-loaded .iframe-loading-overlay {{
        opacity: 0;
        pointer-events: none;
    }}

    /* Widget containers */
    .widget-container {{
        position: relative;
    }}

    .widget-iframe-container iframe {{
        width: 100%;
        height: 100%;
        border: none;
        border-radius: var(--radius-lg);
        background: var(--glass-bg);
        backdrop-filter: var(--glass-blur);
        border: 1px solid var(--border-medium);
        box-shadow: var(--shadow-card);
        transition: transform var(--transition-base),
                    box-shadow var(--transition-base),
                    border-color var(--transition-base);
    }}

    iframe {{
        width: 100%;
        height: 300px;
        border: none;
        border-radius: var(--radius-lg);
        background: var(--glass-bg);
        backdrop-filter: var(--glass-blur);
        border: 1px solid var(--border-medium);
        box-shadow: var(--shadow-card);
        transition: transform var(--transition-base),
                    box-shadow var(--transition-base),
                    border-color var(--transition-base);
    }}

    iframe:hover {{
        transform: scale(1.008);
        box-shadow: var(--shadow-lg),
                    0 8px 32px rgba(0, 229, 160, 0.08);
        border-color: var(--border-accent);
    }}

    .stacked-container {{
        display: flex;
        flex-direction: column;
        gap: var(--space-6);
        grid-column: span 4;
    }}

    .stacked-container iframe {{
        width: 100%;
    }}

    /* Info Cards */
    .info {{
        margin: var(--space-6) auto;
        max-width: 1600px;
        padding: var(--space-6) var(--space-7);
        background: var(--glass-bg);
        backdrop-filter: var(--glass-blur);
        border: 1px solid var(--border-medium);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-card);
    }}

    .info h3 {{
        color: var(--color-accent);
        font-size: var(--text-lg);
        font-weight: 600;
        margin-bottom: 12px;
    }}

    .info p {{
        max-width: 70ch;
        line-height: 1.6;
    }}

    .info code {{
        background: rgba(0, 0, 0, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        color: var(--color-secondary);
        font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        font-size: var(--text-sm);
    }}

    /* ========================================
       Footer
       ======================================== */
    .footer-summary {{
        cursor: pointer;
        user-select: none;
        display: flex;
        align-items: center;
        gap: var(--space-2);
    }}
    .footer-title {{
        margin: 0;
        display: inline;
    }}
    .footer-hint {{
        font-size: var(--text-xs);
        color: var(--color-text-tertiary);
    }}
    .footer-grid {{
        margin-top: var(--space-4);
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: var(--space-4);
    }}
    .footer-section-title {{
        font-size: var(--text-sm);
        margin-bottom: var(--space-2);
    }}

    /* ========================================
       Global Focus & Interaction States
       ======================================== */
    :focus-visible {{
        outline: 2px solid var(--color-accent);
        outline-offset: 2px;
        border-radius: 4px;
    }}

    button:focus-visible,
    .menu-item:focus-visible,
    .export-option:focus-visible {{
        outline: 2px solid var(--color-accent);
        outline-offset: 2px;
    }}

    /* Details/Summary disclosure (footer) */
    details summary {{
        list-style: none;
    }}
    details summary::-webkit-details-marker {{
        display: none;
    }}
    details[open] summary span {{
        display: none;
    }}

    /* ========================================
       Responsive Design — Automatic Breakpoints
       ======================================== */

    /* --- Large Desktop (≤1400px) --- */
    @media (max-width: 1400px) {{
        .dashboard > iframe,
        .dashboard > .widget-iframe-container {{
            grid-column: span 6;
        }}
        .dashboard > .stacked-container {{
            grid-column: span 6;
        }}
        .widget-span-1 {{
            grid-column: span 6 !important;
        }}
        .widget-span-2 {{
            grid-column: span 12 !important;
        }}
    }}

    /* --- Tablet (≤768px) --- */
    @media (max-width: 768px) {{
        body {{
            padding: var(--space-3);
        }}

        .status-bar {{
            gap: var(--space-3);
            padding: var(--space-2) var(--space-3);
            font-size: 10px;
        }}

        .dashboard {{
            grid-template-columns: 1fr;
            gap: var(--space-4);
        }}

        /* Reset bento first-child override on tablet */
        .dashboard > iframe:first-child,
        .dashboard > .widget-iframe-container:first-child {{
            grid-column: 1 / -1;
            min-height: 350px;
        }}

        .dashboard > iframe,
        .dashboard > .widget-iframe-container,
        .dashboard > .stacked-container {{
            grid-column: 1 / -1;
        }}

        .widget-span-1,
        .widget-span-2,
        .widget-full-width {{
            grid-column: 1 / -1 !important;
        }}

        .widget-iframe-container, iframe {{
            height: auto !important;
            min-height: 350px;
            max-height: 80vh;
        }}

        /* Header: stack title center, controls at edges */
        .header-container {{
            flex-wrap: wrap;
            gap: var(--space-3);
            margin-bottom: var(--space-5);
        }}

        h1 {{
            font-size: var(--text-2xl);
        }}

        .header-container > .e2ee-badge {{
            order: 2;
        }}
        .header-container > .header-branding {{
            order: 1;
            flex-basis: 100%;
            text-align: center;
        }}
        .header-container > button.hamburger {{
            order: 3;
        }}

        /* Menu: full-width dropdown */
        .menu {{
            right: 0;
            left: 0;
            min-width: unset;
            border-radius: 12px;
        }}

        /* Submenus: inline instead of fly-out */
        .submenu {{
            position: static;
            margin-right: 0;
            margin-top: 4px;
            border: none;
            border-left: 2px solid var(--border-accent);
            border-radius: 0;
            padding: 4px 0 4px 8px;
            box-shadow: none;
            backdrop-filter: none;
            background: transparent;
        }}

        /* Info section: more compact */
        .info {{
            padding: 16px;
        }}
        .info p {{
            font-size: var(--text-sm);
            line-height: 1.6;
        }}

        /* Toasts: smaller width */
        .toast {{
            min-width: unset;
            max-width: calc(100vw - 48px);
        }}
        .toast-container {{
            right: 12px;
            left: 12px;
        }}

        /* Export dialog: smaller padding */
        .export-content {{
            padding: 24px;
            max-width: 95vw;
        }}

        /* No hover effects on touch devices */
        iframe:hover {{
            transform: none;
            box-shadow: var(--shadow-md),
                        inset 0 1px 0 rgba(255, 255, 255, 0.05);
            border-color: var(--border-medium);
        }}

        /* Border radius reduction */
        iframe,
        .widget-iframe-container iframe {{
            border-radius: 14px;
        }}

        .iframe-loading-overlay {{
            border-radius: 14px;
        }}
    }}

    /* --- Mobile (≤480px) --- */
    @media (max-width: 480px) {{
        body {{
            padding: var(--space-2);
        }}

        .dashboard {{
            gap: var(--space-3);
        }}

        .widget-iframe-container, iframe {{
            min-height: 280px;
            max-height: 70vh;
        }}

        /* Hide status bar on mobile */
        .status-bar {{
            display: none;
        }}

        /* Header: compact single-line */
        .header-container {{
            gap: var(--space-2);
            margin-bottom: var(--space-3);
        }}

        h1 {{
            font-size: var(--text-xl);
            margin-bottom: var(--space-1);
        }}

        /* Hide subtitle on mobile */
        .header-subtitle {{
            display: none;
        }}

        /* E2EE status: icon only */
        .e2ee-badge {{
            padding: var(--space-1) var(--space-2) !important;
        }}
        .e2ee-label {{
            display: none !important;
        }}

        /* Hamburger: slightly smaller */
        .hamburger {{
            width: 40px;
            height: 40px;
            border-radius: 10px;
        }}

        /* Menu: full-screen overlay */
        .menu {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border-radius: 0;
            padding: 60px var(--space-4) var(--space-4);
            overflow-y: auto;
            z-index: 2000;
            background: rgba(12, 12, 20, 0.98);
            backdrop-filter: blur(40px);
        }}

        /* Menu close area (hamburger stays on top) */
        .menu.active ~ .hamburger,
        .hamburger {{
            z-index: 2001;
        }}

        .menu-item {{
            padding: 14px 16px;
            font-size: var(--text-base);
        }}

        /* Toasts: full-width */
        .toast-container {{
            top: 8px;
            right: 8px;
            left: 8px;
        }}
        .toast {{
            max-width: 100%;
            border-radius: 10px;
            padding: 12px 14px;
            font-size: var(--text-sm);
        }}

        /* Export dialog: full-screen-ish */
        .export-content {{
            width: 95vw;
            padding: 20px;
            border-radius: 14px;
        }}
        .export-options {{
            flex-direction: column;
            gap: 10px;
        }}
        .export-option {{
            padding: 14px;
        }}

        /* Widget settings: mobile-friendly */
        .widget-settings-panel {{
            width: 100vw;
            max-width: 100vw;
            max-height: 100vh;
            border-radius: 0;
        }}

        /* Info section: collapse to summary */
        .info {{
            padding: 12px;
            font-size: var(--text-xs);
        }}
        .info h3 {{
            font-size: var(--text-sm);
        }}
        .info code {{
            font-size: var(--text-xs);
            padding: 2px 4px;
        }}

        /* Reduce border radius globally */
        iframe,
        .widget-iframe-container iframe {{
            border-radius: 10px;
        }}
        .iframe-loading-overlay {{
            border-radius: 10px;
        }}
        .info {{
            border-radius: 10px;
        }}

        /* Reduce ambient background intensity */
        body::before {{
            opacity: 0.3;
            animation: none;
        }}

        /* Offline banner: compact */
        .offline-banner {{
            padding: 8px 12px;
            font-size: var(--text-xs);
            border-radius: 8px;
        }}
    }}

    /* --- Small Phones (≤360px) --- */
    @media (max-width: 360px) {{
        body {{
            padding: var(--space-1);
        }}
        .dashboard {{
            gap: var(--space-2);
        }}
        h1 {{
            font-size: var(--text-lg);
        }}
        .widget-iframe-container, iframe {{
            min-height: 240px;
            max-height: 65vh;
            border-radius: 8px;
        }}
        .iframe-loading-overlay {{
            border-radius: 8px;
        }}
    }}

    /* --- Touch Device Hover Override --- */
    @media (hover: none) and (pointer: coarse) {{
        iframe:hover {{
            transform: none !important;
            box-shadow: var(--shadow-md),
                        inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
            border-color: var(--border-medium) !important;
        }}
        .menu-item:hover {{
            transform: none;
        }}
        .hamburger:hover {{
            transform: none;
        }}
    }}

    /* --- Landscape Mobile --- */
    @media (max-height: 500px) and (orientation: landscape) {{
        .widget-iframe-container, iframe {{
            min-height: 200px;
            max-height: 90vh;
        }}
        .menu {{
            max-height: 80vh;
            overflow-y: auto;
        }}
    }}
    /* ========================================
       Accessibility & UI Elements (Phase 1)
       ======================================== */
    .skip-link {{
        position: absolute;
        top: -100%;
        left: 50%;
        transform: translateX(-50%);
        background: var(--color-accent);
        color: var(--color-bg);
        padding: 10px 20px;
        border-radius: 12px;
        font-weight: 600;
        font-size: var(--text-sm);
        z-index: 10000;
        transition: top var(--transition-fast);
        text-decoration: none;
        box-shadow: var(--shadow-lg);
    }}

    .skip-link:focus {{
        top: 20px;
        outline: 2px solid var(--color-accent);
        outline-offset: 4px;
    }}

    /* Skeleton Loaders (Phase 2) */
    @keyframes shimmer {{
        0% {{ background-position: -1000px 0; }}
        100% {{ background-position: 1000px 0; }}
    }}

    .skeleton-loader {{
        background: linear-gradient(
            90deg,
            rgba(255,255,255,0.03) 25%,
            rgba(255,255,255,0.06) 50%,
            rgba(255,255,255,0.03) 75%
        );
        background-size: 1000px 100%;
        animation: shimmer 2s infinite;
        border-radius: 8px;
    }}

    .skeleton-text {{
        height: 12px;
        margin: 8px 0;
    }}

    .skeleton-title {{
        height: 20px;
        width: 60%;
        margin-bottom: 16px;
    }}

    /* ========================================
       Toast Notification System (Phase 1 + 3)
       ======================================== */
    .toast-container {{
        position: fixed;
        top: 24px;
        right: 24px;
        z-index: 2000;
        display: flex;
        flex-direction: column;
        gap: 12px;
        pointer-events: none;
    }}

    .toast {{
        background: var(--color-bg-glass);
        backdrop-filter: blur(20px) saturate(180%);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: var(--shadow-lg),
                    inset 0 1px 0 rgba(255, 255, 255, 0.08);
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 300px;
        max-width: 420px;
        pointer-events: auto;
        animation: toastSlideIn var(--transition-slow), fadeOut var(--transition-slow) 2.7s forwards;
        border: 1px solid var(--border-medium);
        border-left-width: 3px;
    }}

    .toast-success {{ border-left-color: var(--color-success); }}
    .toast-error {{ border-left-color: var(--color-error); }}
    .toast-warning {{ border-left-color: var(--color-warning); }}
    .toast-info {{ border-left-color: var(--color-secondary); }}

    .toast-icon {{
        font-size: 20px;
        flex-shrink: 0;
    }}

    .toast-message {{
        flex: 1;
        font-size: var(--text-sm);
        color: var(--color-text-primary);
        line-height: 1.4;
    }}

    .toast-close {{
        background: none;
        border: none;
        color: var(--color-text-tertiary);
        cursor: pointer;
        padding: 4px;
        font-size: 18px;
        line-height: 1;
        border-radius: 6px;
        transition: all var(--transition-fast);
    }}

    .toast-close:hover {{
        color: var(--color-text-primary);
        background: rgba(255, 255, 255, 0.1);
    }}

    @keyframes toastSlideIn {{
        from {{
            transform: translateX(100%);
            opacity: 0;
        }}
        to {{
            transform: translateX(0);
            opacity: 1;
        }}
    }}

    @keyframes fadeOut {{
        to {{
            opacity: 0;
            transform: translateX(50%);
        }}
    }}

    /* ========================================
       Export Format Dialog (Phase 1)
       ======================================== */
    .export-dialog {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn var(--transition-base);
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}

    .export-overlay {{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(8px);
    }}

    .export-content {{
        position: relative;
        background: var(--color-bg-glass);
        backdrop-filter: blur(40px) saturate(180%);
        border-radius: 20px;
        padding: 32px;
        max-width: 460px;
        width: 90%;
        box-shadow: var(--shadow-lg),
                    inset 0 1px 0 rgba(255, 255, 255, 0.08);
        border: 1px solid var(--border-medium);
        animation: dialogSlideUp var(--transition-slow);
    }}

    @keyframes dialogSlideUp {{
        from {{
            opacity: 0;
            transform: translateY(32px) scale(0.96);
        }}
        to {{
            opacity: 1;
            transform: translateY(0) scale(1);
        }}
    }}

    .export-title {{
        font-size: var(--text-xl);
        font-weight: 700;
        color: var(--color-accent);
        margin-bottom: 16px;
        letter-spacing: -0.3px;
    }}

    .export-message {{
        font-size: var(--text-base);
        color: var(--color-text-secondary);
        margin-bottom: 24px;
        line-height: 1.6;
    }}
    .export-options {{
        display: flex;
        gap: 16px;
        margin-bottom: 28px;
    }}

    .export-option {{
        flex: 1;
        padding: 20px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border-medium);
        border-radius: 14px;
        cursor: pointer;
        text-align: center;
        transition: all var(--transition-base);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }}

    .export-option:hover {{
        border-color: var(--border-accent);
        background: var(--color-accent-dim);
        transform: translateY(-2px);
        box-shadow: var(--shadow-sm), var(--shadow-glow);
    }}

    .export-option.selected {{
        border-color: var(--color-accent);
        background: var(--color-accent-dim);
        box-shadow: 0 0 0 1px var(--color-accent),
                    var(--shadow-glow);
    }}

    .export-option-label {{
        font-size: var(--text-lg);
        font-weight: 700;
        color: var(--color-text-primary);
        margin-bottom: 6px;
    }}

    .export-option-desc {{
        font-size: var(--text-xs);
        color: var(--color-text-tertiary);
    }}

    .export-actions {{
        display: flex;
        gap: 12px;
        justify-content: flex-end;
    }}

    .export-btn {{
        padding: 12px 28px;
        border: none;
        border-radius: 12px;
        font-size: var(--text-sm);
        font-weight: 600;
        cursor: pointer;
        transition: all var(--transition-base);
    }}

    .export-btn-cancel {{
        background: rgba(255, 255, 255, 0.05);
        color: var(--color-text-secondary);
        border: 1px solid var(--border-medium);
    }}

    .export-btn-cancel:hover {{
        background: rgba(255, 255, 255, 0.08);
        color: var(--color-text-primary);
        border-color: var(--border-accent);
    }}

    .export-btn-primary {{
        background: linear-gradient(135deg, var(--color-accent), var(--color-accent-hover));
        color: var(--color-bg);
        box-shadow: var(--shadow-sm);
    }}

    .export-btn-primary:hover {{
        transform: translateY(-2px);
        box-shadow: var(--shadow-md), var(--shadow-glow);
    }}

    .export-encrypt-section {{
        margin-top: 16px;
        padding: 16px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
    }}

    .export-encrypt-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: var(--text-sm);
        font-weight: 600;
        color: var(--color-text-primary);
    }}

    .export-password-input {{
        width: 100%;
        margin-top: 12px;
        padding: 10px 14px;
        background: var(--color-bg);
        border: 1px solid var(--border-medium);
        border-radius: 8px;
        color: var(--color-text-primary);
        font-size: var(--text-sm);
        font-family: inherit;
        outline: none;
        transition: border-color var(--transition-fast);
    }}

    .export-password-input:focus {{
        border-color: var(--color-accent);
    }}

    .export-encrypt-hint {{
        margin-top: 8px;
        font-size: var(--text-xs);
        color: var(--color-text-tertiary);
    }}

    .export-encrypt-modes {{
        display: flex;
        gap: 8px;
        margin-top: 12px;
    }}

    .export-encrypt-mode {{
        flex: 1;
        padding: 10px 12px;
        background: var(--color-bg);
        border: 1px solid var(--border-medium);
        border-radius: 8px;
        cursor: pointer;
        transition: all var(--transition-fast);
        text-align: center;
    }}

    .export-encrypt-mode:hover {{
        border-color: var(--color-accent);
    }}

    .export-encrypt-mode.selected {{
        border-color: var(--color-accent);
        background: rgba(0, 229, 160, 0.08);
    }}

    .export-encrypt-mode input[type="radio"] {{
        display: none;
    }}

    .export-encrypt-mode-label {{
        display: block;
        font-size: var(--text-sm);
        font-weight: 600;
        color: var(--color-text-primary);
    }}

    .export-encrypt-mode-desc {{
        display: block;
        font-size: var(--text-xs);
        color: var(--color-text-tertiary);
        margin-top: 2px;
    }}

    /* ========================================
       Widget Settings Panel
       ======================================== */
    .widget-settings-overlay {{
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.85);
        backdrop-filter: blur(8px);
        z-index: 3000;
        display: none;
        align-items: center;
        justify-content: center;
        animation: fadeIn var(--transition-base);
    }}
    .widget-settings-overlay.active {{
        display: flex;
    }}
    .widget-settings-panel {{
        background: var(--color-bg-elevated);
        border: 1px solid var(--border-medium);
        border-radius: 20px;
        width: 560px;
        max-width: 95vw;
        max-height: 85vh;
        display: flex;
        flex-direction: column;
        box-shadow: var(--shadow-lg);
        animation: dialogSlideUp var(--transition-slow);
    }}
    .ws-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 24px 16px;
        border-bottom: 1px solid var(--border-subtle);
    }}
    .ws-header h2 {{
        font-size: var(--text-xl);
        font-weight: 700;
        color: var(--color-accent);
        margin: 0;
    }}
    .ws-header-actions {{
        display: flex;
        gap: 8px;
        align-items: center;
    }}
    .ws-btn {{
        padding: 8px 16px;
        border: 1px solid var(--border-medium);
        border-radius: 10px;
        background: rgba(255,255,255,0.04);
        color: var(--color-text-secondary);
        font-size: var(--text-sm);
        cursor: pointer;
        transition: all var(--transition-fast);
    }}
    .ws-btn:hover {{
        background: var(--color-accent-dim);
        border-color: var(--border-accent);
        color: var(--color-accent);
    }}
    .ws-btn-primary {{
        background: var(--color-accent);
        color: var(--color-bg);
        border-color: var(--color-accent);
        font-weight: 600;
    }}
    .ws-btn-primary:hover {{
        background: var(--color-accent-hover);
    }}
    .ws-close {{
        width: 36px; height: 36px;
        background: none;
        border: 1px solid var(--border-medium);
        border-radius: 10px;
        color: var(--color-text-tertiary);
        font-size: 20px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all var(--transition-fast);
    }}
    .ws-close:hover {{
        color: var(--color-error);
        border-color: var(--color-error);
        background: rgba(255,107,107,0.1);
    }}
    .ws-body {{
        flex: 1;
        overflow-y: auto;
        padding: 16px 24px;
    }}
    .ws-body::-webkit-scrollbar {{
        width: 6px;
    }}
    .ws-body::-webkit-scrollbar-track {{
        background: transparent;
    }}
    .ws-body::-webkit-scrollbar-thumb {{
        background: var(--color-accent);
        border-radius: 8px;
    }}
    .ws-category {{
        margin-bottom: 16px;
    }}
    .ws-category-title {{
        font-size: var(--text-xs);
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: var(--color-accent);
        font-weight: 600;
        margin-bottom: 8px;
        padding: 0 4px;
    }}
    .ws-widget-item {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        background: rgba(255,255,255,0.03);
        border: 1px solid transparent;
        border-radius: 12px;
        margin-bottom: 6px;
        cursor: grab;
        transition: all var(--transition-fast);
        user-select: none;
    }}
    .ws-widget-item:active {{
        cursor: grabbing;
    }}
    .ws-widget-item:hover {{
        background: rgba(255,255,255,0.06);
        border-color: var(--border-medium);
    }}
    .ws-widget-item.dragging {{
        opacity: 0.5;
        border-color: var(--color-accent);
        background: var(--color-accent-dim);
    }}
    .ws-widget-item.drag-over {{
        border-top: 2px solid var(--color-accent);
    }}
    .ws-drag-handle {{
        color: var(--color-text-tertiary);
        font-size: 16px;
        flex-shrink: 0;
        cursor: grab;
    }}
    .ws-widget-info {{
        flex: 1;
        min-width: 0;
    }}
    .ws-widget-name {{
        font-size: var(--text-sm);
        font-weight: 600;
        color: var(--color-text-primary);
    }}
    .ws-widget-desc {{
        font-size: var(--text-xs);
        color: var(--color-text-tertiary);
        margin-top: 2px;
    }}
    .ws-toggle {{
        position: relative;
        width: 40px;
        height: 22px;
        flex-shrink: 0;
    }}
    .ws-toggle input {{
        opacity: 0;
        width: 0;
        height: 0;
    }}
    .ws-toggle-slider {{
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(255,255,255,0.1);
        border-radius: 11px;
        cursor: pointer;
        transition: all var(--transition-fast);
    }}
    .ws-toggle-slider::before {{
        content: '';
        position: absolute;
        width: 16px; height: 16px;
        left: 3px; bottom: 3px;
        background: var(--color-text-tertiary);
        border-radius: 50%;
        transition: all var(--transition-fast);
    }}
    .ws-toggle input:checked + .ws-toggle-slider {{
        background: var(--color-accent-dim);
    }}
    .ws-toggle input:checked + .ws-toggle-slider::before {{
        transform: translateX(18px);
        background: var(--color-accent);
    }}
    .ws-footer {{
        padding: 16px 24px;
        border-top: 1px solid var(--border-subtle);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .ws-footer-hint {{
        font-size: var(--text-xs);
        color: var(--color-text-tertiary);
    }}

    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }}
        .skeleton-loader {{
            animation: none;
        }}
    }}

    .offline-banner {{
        background: var(--color-error, #FF6B6B);
        color: white;
        padding: 12px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-radius: 12px;
        margin-bottom: 16px;
        max-width: 1600px;
        margin-left: auto;
        margin-right: auto;
        font-size: var(--text-sm);
        font-weight: 600;
        box-shadow: var(--shadow-md);
    }}
    .offline-banner .spinner {{
        width: 16px;
        height: 16px;
        border-width: 2px;
        border-top-color: white;
    }}
</style>
</head>
<body>
<!-- Skip Link for Keyboard Navigation -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- Toast Container for Notifications -->
<div class="toast-container" id="toastContainer" role="alert" aria-live="polite"></div>

<!-- Widget Settings Panel -->
<div class="widget-settings-overlay" id="widgetSettingsOverlay" onclick="if(event.target===this)closeWidgetSettings()">
    <div class="widget-settings-panel">
        <div class="ws-header">
            <h2>Customize Widgets</h2>
            <div class="ws-header-actions">
                <button class="ws-btn" onclick="resetWidgetLayout()">Reset Default</button>
                <button class="ws-close" onclick="closeWidgetSettings()" aria-label="Close">&times;</button>
            </div>
        </div>
        <div class="ws-body" id="wsBody">
            <p style="color: var(--color-text-tertiary); text-align: center; padding: 40px 0;">Loading widgets...</p>
        </div>
        <div class="ws-footer">
            <span class="ws-footer-hint">Drag to reorder. Toggle to show/hide.</span>
            <button class="ws-btn ws-btn-primary" onclick="saveWidgetLayout()">Save &amp; Apply</button>
        </div>
    </div>
</div>

<!-- Export Format Dialog -->
<div id="exportDialog" class="export-dialog" role="dialog" aria-modal="true" aria-labelledby="exportTitle" style="display: none;">
    <div class="export-overlay" onclick="closeExportDialog()"></div>
    <div class="export-content">
        <h2 id="exportTitle" class="export-title">Choose Export Format</h2>
        <p class="export-message">Select the format for your data export:</p>
        <div class="export-options" role="radiogroup" aria-label="Export format options">
            <div class="export-option selected" onclick="selectExportFormat('csv')" role="radio" aria-checked="true" tabindex="0">
                <div class="export-option-label">CSV</div>
                <div class="export-option-desc">Excel-compatible spreadsheet</div>
            </div>
            <div class="export-option" onclick="selectExportFormat('json')" role="radio" aria-checked="false" tabindex="0">
                <div class="export-option-label">JSON</div>
                <div class="export-option-desc">For programming & APIs</div>
            </div>
        </div>
        <div class="export-encrypt-section">
            <div class="export-encrypt-header">
                <span>Encrypt export</span>
                <label class="ws-toggle">
                    <input type="checkbox" id="encryptToggle" onchange="toggleExportEncryption(this.checked)">
                    <span class="ws-toggle-slider"></span>
                </label>
            </div>
            <div id="encryptModeSection" style="display: none;">
                <div class="export-encrypt-modes">
                    <label class="export-encrypt-mode selected" onclick="selectEncryptMode('fleet_key')">
                        <input type="radio" name="encryptMode" value="fleet_key" checked>
                        <span class="export-encrypt-mode-label">Fleet Key</span>
                        <span class="export-encrypt-mode-desc">Decryptable by fleet server</span>
                    </label>
                    <label class="export-encrypt-mode" onclick="selectEncryptMode('password')">
                        <input type="radio" name="encryptMode" value="password">
                        <span class="export-encrypt-mode-label">Password</span>
                        <span class="export-encrypt-mode-desc">Requires password to decrypt</span>
                    </label>
                </div>
                <div id="encryptPasswordSection" style="display: none;">
                    <input type="password" id="encryptPassword" class="export-password-input"
                           placeholder="Create a password (16+ characters)" minlength="16">
                    <div class="export-encrypt-hint" id="encryptHintText">Dual-layer encryption: AES-256-GCM + Fleet key wrap. The fleet server needs this password and your agent key to decrypt.</div>
                </div>
            </div>
        </div>
        <div class="export-actions">
            <button class="export-btn export-btn-cancel" onclick="closeExportDialog()">Cancel</button>
            <button class="export-btn export-btn-primary" onclick="confirmExport()">Download</button>
        </div>
    </div>
</div>

<main id="main-content">
<div class="header-container">
    <div id="e2eeStatus" class="e2ee-badge">
        <span id="e2eeIcon" class="e2ee-icon"></span>
        <span id="e2eeText" class="e2ee-label">Checking...</span>
    </div>
    <div class="header-branding">
        <h1>ATLAS Dashboard</h1>
        <p class="header-subtitle">Fleet Monitoring &amp; Network Intelligence</p>
    </div>
    <button class="hamburger" id="hamburger" onclick="toggleMenu()" aria-label="Open menu" aria-expanded="false" aria-controls="menu">
        <span></span>
        <span></span>
        <span></span>
    </button>
    <nav class="menu" id="menu" role="navigation" aria-label="Dashboard menu">
        <div class="menu-section">
            <div class="menu-title">Themes</div>
            <div class="menu-item" onclick="changeTheme('default')">
                <span>Default</span>
                <div class="theme-preview" style="background: linear-gradient(135deg, #00E5A0, #00C890);"></div>
            </div>
            <div class="menu-item" onclick="changeTheme('cyberpunk')">
                <span>Cyberpunk</span>
                <div class="theme-preview" style="background: linear-gradient(135deg, #ff00ff, #00ffff);"></div>
            </div>
            <div class="menu-item" onclick="changeTheme('ocean')">
                <span>Ocean</span>
                <div class="theme-preview" style="background: linear-gradient(135deg, #0080ff, #00ffff);"></div>
            </div>
            <div class="menu-item" onclick="changeTheme('sunset')">
                <span>Sunset</span>
                <div class="theme-preview" style="background: linear-gradient(135deg, #ff6400, #ff0080);"></div>
            </div>
            <div class="menu-item" onclick="changeTheme('forest')">
                <span>Forest</span>
                <div class="theme-preview" style="background: linear-gradient(135deg, #00ff64, #008040);"></div>
            </div>
            <div class="menu-item" onclick="changeTheme('monochrome')">
                <span>Monochrome</span>
                <div class="theme-preview" style="background: linear-gradient(135deg, #ffffff, #666666);"></div>
            </div>
        </div>
        <div class="menu-section">
            <div class="menu-title">Options</div>
            <div class="menu-item" onclick="toggleFullscreen()">
                <span>Fullscreen</span>
                <span style="font-size: 18px;">⛶</span>
            </div>
            <div class="menu-item" onclick="refreshAll()">
                <span>Refresh All</span>
                <span style="font-size: 18px;">↻</span>
            </div>
            <div class="menu-item" onclick="openWidgetSettings()">
                <span>Customize Widgets</span>
                <span style="font-size: 18px;">&#9881;</span>
            </div>
            <div class="menu-item has-submenu" onmouseenter="showSubmenu('exportSubmenu')" onmouseleave="hideSubmenu('exportSubmenu')">
                <span>Export Data</span>
                <span style="font-size: 18px;">⬇</span>
                <div class="submenu" id="exportSubmenu">
                    <div class="menu-section">
                        <div class="menu-title">Speed Tests</div>
                        <div class="menu-item" onclick="exportData('speedtest', 1)">
                            <span>Last 1 Hour</span>
                        </div>
                        <div class="menu-item" onclick="exportData('speedtest', 24)">
                            <span>Last 24 Hours</span>
                        </div>
                        <div class="menu-item" onclick="exportData('speedtest', null)">
                            <span>All Data</span>
                        </div>
                    </div>
                    <div class="menu-section">
                        <div class="menu-title">Ping Tests</div>
                        <div class="menu-item" onclick="exportData('ping', 1)">
                            <span>Last 1 Hour</span>
                        </div>
                        <div class="menu-item" onclick="exportData('ping', 24)">
                            <span>Last 24 Hours</span>
                        </div>
                        <div class="menu-item" onclick="exportData('ping', null)">
                            <span>All Data</span>
                        </div>
                    </div>
                    <div class="menu-section">
                        <div class="menu-title">WiFi Quality</div>
                        <div class="menu-item" onclick="exportData('wifi', 1)">
                            <span>Last 1 Hour</span>
                        </div>
                        <div class="menu-item" onclick="exportData('wifi', 24)">
                            <span>Last 24 Hours</span>
                        </div>
                        <div class="menu-item" onclick="exportData('wifi', null)">
                            <span>All Data</span>
                        </div>
                    </div>
                    <div class="menu-section">
                        <div class="menu-title">WiFi Events</div>
                        <div class="menu-item" onclick="exportData('wifi-events', 1)">
                            <span>Last 1 Hour</span>
                        </div>
                        <div class="menu-item" onclick="exportData('wifi-events', 24)">
                            <span>Last 24 Hours</span>
                        </div>
                        <div class="menu-item" onclick="exportData('wifi-events', null)">
                            <span>All Data</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="status-bar" id="statusBar" role="status" aria-label="System metrics">
    <div class="status-metric">
        <span class="status-dot" id="statusDot"></span>
        <span>Agent</span>
        <span class="status-value" id="statusUptime">--</span>
    </div>
    <div class="status-divider"></div>
    <div class="status-metric">
        <span>CPU</span>
        <span class="status-value" id="statusCpu">--%</span>
    </div>
    <div class="status-divider"></div>
    <div class="status-metric">
        <span>Memory</span>
        <span class="status-value" id="statusMem">--%</span>
    </div>
    <div class="status-divider"></div>
    <div class="status-metric">
        <span>Network</span>
        <span class="status-value" id="statusNet">-- Mbps</span>
    </div>
    <div class="status-divider"></div>
    <div class="status-metric">
        <span>Widgets</span>
        <span class="status-value" id="statusWidgets">0</span>
    </div>
</div>

<div id="offlineBanner" class="offline-banner" role="alert" aria-live="assertive" style="display: none;">
    <span>&#9888;</span>
    <span>Connection to agent lost. Attempting to reconnect...</span>
    <div class="spinner"></div>
</div>

<div class="dashboard" id="dashboardGrid">
{_generate_widget_iframes()}
</div>

<footer class="info footer-urls" role="contentinfo">
    <details>
        <summary class="footer-summary">
            <h3 class="footer-title">Widget URLs</h3>
            <span class="footer-hint">Click to expand</span>
        </summary>
        <div class="footer-grid">
            <div>
                <h3 class="footer-section-title">System</h3>
                <p><code>/widget/system-monitor</code></p>
                <p><code>/widget/processes</code></p>
                <p><code>/widget/system-health</code></p>
            </div>
            <div>
                <h3 class="footer-section-title">Network</h3>
                <p><code>/widget/wifi</code></p>
                <p><code>/widget/wifi-analyzer</code></p>
                <p><code>/widget/speedtest</code></p>
                <p><code>/widget/wifi-roaming</code></p>
                <p><code>/widget/network-analysis</code></p>
            </div>
            <div>
                <h3 class="footer-section-title">Enterprise</h3>
                <p><code>/widget/voip-quality</code></p>
                <p><code>/widget/connection-rate</code></p>
                <p><code>/widget/throughput</code></p>
                <p><code>/widget/osi-layers</code></p>
            </div>
            <div>
                <h3 class="footer-section-title">Services &amp; Hardware</h3>
                <p><code>/widget/vpn-status</code></p>
                <p><code>/widget/saas-health</code></p>
                <p><code>/widget/network-quality</code></p>
                <p><code>/widget/security-dashboard</code></p>
                <p><code>/widget/power</code></p>
                <p><code>/widget/display</code></p>
                <p><code>/widget/peripherals</code></p>
                <p><code>/widget/disk-health</code></p>
            </div>
        </div>
    </details>
</footer>

<script>
    // Live Status Bar Updates
    async function updateStatusBar() {{
        try {{
            const resp = await fetch('/api/agent/health');
            const data = await resp.json();
            const dot = document.getElementById('statusDot');
            const uptime = document.getElementById('statusUptime');
            const cpu = document.getElementById('statusCpu');
            const mem = document.getElementById('statusMem');
            const net = document.getElementById('statusNet');
            const widgets = document.getElementById('statusWidgets');

            // Agent status dot
            dot.className = 'status-dot';
            if (data.status === 'ok' || data.status === 'healthy') {{
                dot.classList.add(''); // green default
            }} else {{
                dot.classList.add('warn');
            }}

            // Uptime
            if (data.uptime_seconds) {{
                const hrs = Math.floor(data.uptime_seconds / 3600);
                const mins = Math.floor((data.uptime_seconds % 3600) / 60);
                uptime.textContent = hrs > 0 ? hrs + 'h ' + mins + 'm' : mins + 'm';
            }} else {{
                uptime.textContent = 'Online';
            }}

            // CPU & Memory (from system data)
            if (data.cpu_percent !== undefined) {{
                cpu.textContent = data.cpu_percent.toFixed(0) + '%';
            }}
            if (data.memory_percent !== undefined) {{
                mem.textContent = data.memory_percent.toFixed(0) + '%';
            }}

            // Network (if available)
            if (data.network_mbps !== undefined) {{
                net.textContent = data.network_mbps.toFixed(1) + ' Mbps';
            }}

            // Widget count
            widgets.textContent = document.querySelectorAll('.dashboard iframe').length;
        }} catch (e) {{
            document.getElementById('statusDot').className = 'status-dot error';
            document.getElementById('statusUptime').textContent = 'Offline';
        }}
    }}
    updateStatusBar();
    setInterval(updateStatusBar, 10000);

    // E2EE Status Update
    async function updateE2EEStatus() {{
        try {{
            const response = await fetch('/api/agent/health');
            const data = await response.json();
            const e2ee = data.e2ee || {{}};
            
            const icon = document.getElementById('e2eeIcon');
            const text = document.getElementById('e2eeText');
            const container = document.getElementById('e2eeStatus');
            
            if (e2ee.status === 'encrypted') {{
                icon.textContent = '';
                text.innerHTML = '<span style="color: var(--color-accent);">E2EE Active</span><br><small style="color: var(--color-text-tertiary);">Server verified</small>';
                container.style.borderColor = 'var(--color-accent)';
            }} else if (e2ee.status === 'enabled_unverified') {{
                icon.textContent = '';
                text.innerHTML = '<span style="color: var(--color-warning);">E2EE Enabled</span><br><small style="color: var(--color-text-tertiary);">Awaiting verification</small>';
                container.style.borderColor = 'var(--color-warning)';
            }} else {{
                icon.textContent = '';
                text.innerHTML = '<span style="color: var(--color-error);">Not Encrypted</span><br><small style="color: var(--color-text-tertiary);">Plaintext</small>';
                container.style.borderColor = 'var(--color-error)';
            }}
        }} catch (e) {{
            console.error('Error updating E2EE status:', e);
        }}
    }}
    
    // Check E2EE status on load and every 30 seconds
    updateE2EEStatus();
    setInterval(updateE2EEStatus, 30000);
    
    function toggleMenu() {{
        const menu = document.getElementById('menu');
        const hamburger = document.getElementById('hamburger');
        const isOpen = menu.classList.toggle('active');
        hamburger.classList.toggle('active');
        // Update ARIA states
        hamburger.setAttribute('aria-expanded', isOpen);
        hamburger.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
    }}
    
    function showSubmenu(submenuId) {{
        const submenu = document.getElementById(submenuId);
        if (submenu) {{
            submenu.classList.add('active');
        }}
    }}
    
    function hideSubmenu(submenuId) {{
        const submenu = document.getElementById(submenuId);
        if (submenu) {{
            submenu.classList.remove('active');
        }}
    }}
    
    function changeTheme(theme) {{
        const themes = {{
            'default': {{
                accent: '#00E5A0',
                accentHover: '#00C890',
                bg: '#0c0c14',
                bgElevated: '#161620',
                secondary: '#00C8FF'
            }},
            'cyberpunk': {{
                accent: '#ff00ff',
                accentHover: '#cc00cc',
                bg: '#0a0a14',
                bgElevated: '#14141e',
                secondary: '#00ffff'
            }},
            'ocean': {{
                accent: '#0080ff',
                accentHover: '#0060cc',
                bg: '#060c18',
                bgElevated: '#0c1428',
                secondary: '#00ffff'
            }},
            'sunset': {{
                accent: '#ff6400',
                accentHover: '#e05800',
                bg: '#140a06',
                bgElevated: '#1e120a',
                secondary: '#ff0080'
            }},
            'forest': {{
                accent: '#00ff64',
                accentHover: '#00cc50',
                bg: '#060e06',
                bgElevated: '#0c180c',
                secondary: '#008040'
            }},
            'monochrome': {{
                accent: '#e0e0e0',
                accentHover: '#c0c0c0',
                bg: '#0a0a0a',
                bgElevated: '#141414',
                secondary: '#888888'
            }}
        }};

        const t = themes[theme];
        if (t) {{
            const r = document.documentElement.style;
            r.setProperty('--color-accent', t.accent);
            r.setProperty('--color-accent-hover', t.accentHover);
            r.setProperty('--color-bg', t.bg);
            r.setProperty('--color-bg-elevated', t.bgElevated);
            r.setProperty('--color-secondary', t.secondary);
            r.setProperty('--color-accent-dim', t.accent + '1f');
            r.setProperty('--border-accent', t.accent + '59');

            // Update menu items
            document.querySelectorAll('.menu-item').forEach(item => {{
                item.classList.remove('active');
            }});
            event.target.closest('.menu-item').classList.add('active');

            localStorage.setItem('dashboardTheme', theme);
            toggleMenu();
        }}
    }}
    
    function toggleFullscreen() {{
        if (!document.fullscreenElement) {{
            document.documentElement.requestFullscreen();
        }} else {{
            document.exitFullscreen();
        }}
        toggleMenu();
    }}
    
    function refreshAll() {{
        document.querySelectorAll('iframe').forEach(iframe => {{
            iframe.src = iframe.src;
        }});
        toggleMenu();
    }}
    
    // Toast Notification System
    const ToastManager = {{
        container: null,
        init() {{
            if (!this.container) {{
                this.container = document.getElementById('toastContainer');
            }}
        }},
        show(message, type = 'success', duration = 3000) {{
            this.init();
            const icons = {{
                success: '&#10003;',
                error: '&#10007;',
                warning: '&#9888;',
                info: '&#8505;'
            }};
            const toast = document.createElement('div');
            toast.className = `toast toast-${{type}}`;
            toast.innerHTML = `
                <span class="toast-icon">${{icons[type] || icons.info}}</span>
                <span class="toast-message">${{message}}</span>
                <button class="toast-close" aria-label="Close notification">&times;</button>
            `;
            const closeBtn = toast.querySelector('.toast-close');
            closeBtn.addEventListener('click', () => this.dismiss(toast));
            this.container.appendChild(toast);
            setTimeout(() => this.dismiss(toast), duration);
            return toast;
        }},
        dismiss(toast) {{
            if (toast && toast.parentNode) {{
                toast.style.animation = 'fadeOut 0.3s ease forwards';
                setTimeout(() => toast.remove(), 300);
            }}
        }},
        success(message) {{ return this.show(message, 'success'); }},
        error(message) {{ return this.show(message, 'error', 5000); }},
        warning(message) {{ return this.show(message, 'warning', 4000); }},
        info(message) {{ return this.show(message, 'info'); }}
    }};

    // Export Dialog State
    let pendingExport = {{ dataType: null, hours: null }};
    let selectedFormat = 'csv';
    let selectedEncryptMode = 'fleet_key';

    function toggleExportEncryption(enabled) {{
        document.getElementById('encryptModeSection').style.display = enabled ? 'block' : 'none';
        if (enabled) selectEncryptMode('fleet_key');
    }}

    function selectEncryptMode(mode) {{
        selectedEncryptMode = mode;
        document.querySelectorAll('.export-encrypt-mode').forEach(el => {{
            const isSelected = el.querySelector('input').value === mode;
            el.classList.toggle('selected', isSelected);
            el.querySelector('input').checked = isSelected;
        }});
        document.getElementById('encryptPasswordSection').style.display = 'block';
        const pwInput = document.getElementById('encryptPassword');
        const hintText = document.getElementById('encryptHintText');
        if (mode === 'fleet_key') {{
            pwInput.placeholder = 'Create a password (16+ characters)';
            pwInput.minLength = 16;
            hintText.textContent = 'Dual-layer encryption: AES-256-GCM + Fleet key wrap. The fleet server needs this password and your agent key to decrypt.';
        }} else {{
            pwInput.placeholder = 'Enter encryption password';
            pwInput.minLength = 4;
            hintText.textContent = 'AES-256-GCM encrypted. You will need this password to decrypt the file.';
        }}
        pwInput.focus();
    }}

    function exportData(dataType, hours) {{
        // Store pending export data and show format dialog
        pendingExport = {{ dataType, hours }};
        selectedFormat = 'csv';

        // Reset encryption toggle
        document.getElementById('encryptToggle').checked = false;
        document.getElementById('encryptModeSection').style.display = 'none';
        document.getElementById('encryptPasswordSection').style.display = 'none';
        document.getElementById('encryptPassword').value = '';
        selectedEncryptMode = 'fleet_key';

        // Reset selection UI
        document.querySelectorAll('.export-option').forEach((opt, i) => {{
            if (i === 0) {{
                opt.classList.add('selected');
                opt.setAttribute('aria-checked', 'true');
            }} else {{
                opt.classList.remove('selected');
                opt.setAttribute('aria-checked', 'false');
            }}
        }});

        document.getElementById('exportDialog').style.display = 'flex';
        // Focus first option for accessibility
        document.querySelector('.export-option').focus();
        toggleMenu();
    }}

    function selectExportFormat(format) {{
        selectedFormat = format;
        document.querySelectorAll('.export-option').forEach(opt => {{
            const isSelected = opt.querySelector('.export-option-label').textContent.toLowerCase() === format;
            opt.classList.toggle('selected', isSelected);
            opt.setAttribute('aria-checked', isSelected);
        }});
    }}

    function closeExportDialog() {{
        document.getElementById('exportDialog').style.display = 'none';
        pendingExport = {{ dataType: null, hours: null }};
    }}

    function confirmExport() {{
        const {{ dataType, hours }} = pendingExport;

        if (!dataType) {{
            ToastManager.error('No export data type selected');
            closeExportDialog();
            return;
        }}

        // Build URL based on data type
        let url;
        switch(dataType) {{
            case 'speedtest':
                url = '/api/speedtest/export';
                break;
            case 'ping':
                url = '/api/ping/export';
                break;
            case 'wifi':
                url = '/api/wifi/export';
                break;
            case 'wifi-events':
                url = '/api/wifi/events/export';
                break;
            default:
                ToastManager.error('Unknown data type: ' + dataType);
                closeExportDialog();
                return;
        }}

        // Add query parameters
        const params = [];
        if (hours) {{
            params.push('hours=' + hours);
        }}
        params.push('format=' + selectedFormat);

        if (params.length > 0) {{
            url += '?' + params.join('&');
        }}

        const encrypt = document.getElementById('encryptToggle').checked;

        if (encrypt) {{
            let fetchBody;
            let toastMsg;

            if (selectedEncryptMode === 'password') {{
                const password = document.getElementById('encryptPassword').value;
                if (!password || password.length < 4) {{
                    ToastManager.error('Password must be at least 4 characters');
                    document.getElementById('encryptPassword').focus();
                    return;
                }}
                fetchBody = JSON.stringify({{ password: password, mode: 'password' }});
                toastMsg = 'Encrypting and exporting...';
            }} else {{
                const password = document.getElementById('encryptPassword').value;
                if (!password || password.length < 16) {{
                    ToastManager.error('Password must be at least 16 characters');
                    document.getElementById('encryptPassword').focus();
                    return;
                }}
                fetchBody = JSON.stringify({{ password: password, mode: 'fleet_key' }});
                toastMsg = 'Encrypting with fleet key + password...';
            }}

            ToastManager.success(toastMsg);
            const ext = selectedEncryptMode === 'fleet_key' ? '.fernet.enc' : '.enc';
            fetch(url, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: fetchBody
            }})
            .then(resp => {{
                if (!resp.ok) throw new Error('Export failed: ' + resp.statusText);
                const disposition = resp.headers.get('Content-Disposition') || '';
                const match = disposition.match(/filename="?(.+?)"?$/);
                const filename = match ? match[1] : dataType + '.' + selectedFormat + ext;
                return resp.blob().then(blob => ({{ blob, filename }}));
            }})
            .then(({{ blob, filename }}) => {{
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                setTimeout(() => {{ URL.revokeObjectURL(a.href); a.remove(); }}, 100);
                ToastManager.success('Encrypted export downloaded');
            }})
            .catch(err => {{
                ToastManager.error(err.message || 'Encrypted export failed');
            }});
        }} else {{
            ToastManager.success('Starting ' + selectedFormat.toUpperCase() + ' export...');
            window.location.href = url;
        }}
        closeExportDialog();
    }}

    // Handle keyboard navigation for export dialog
    document.addEventListener('keydown', function(e) {{
        const dialog = document.getElementById('exportDialog');
        if (dialog.style.display === 'flex') {{
            if (e.key === 'Escape') {{
                closeExportDialog();
            }} else if (e.key === 'Enter') {{
                confirmExport();
            }} else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {{
                selectExportFormat(selectedFormat === 'csv' ? 'json' : 'csv');
            }}
        }}
    }});
    
    // Close menu when clicking outside
    document.addEventListener('click', function(event) {{
        const menu = document.getElementById('menu');
        const hamburger = document.getElementById('hamburger');
        if (!menu.contains(event.target) && !hamburger.contains(event.target)) {{
            menu.classList.remove('active');
            hamburger.classList.remove('active');
        }}
    }});
    
    // Restore saved theme on load
    (function restoreTheme() {{
        const saved = localStorage.getItem('dashboardTheme');
        if (saved && saved !== 'default') {{
            // Simulate theme change without toggleMenu
            const themes = {{
                'cyberpunk': {{ accent: '#ff00ff', accentHover: '#cc00cc', bg: '#0a0a14', bgElevated: '#14141e', secondary: '#00ffff' }},
                'ocean': {{ accent: '#0080ff', accentHover: '#0060cc', bg: '#060c18', bgElevated: '#0c1428', secondary: '#00ffff' }},
                'sunset': {{ accent: '#ff6400', accentHover: '#e05800', bg: '#140a06', bgElevated: '#1e120a', secondary: '#ff0080' }},
                'forest': {{ accent: '#00ff64', accentHover: '#00cc50', bg: '#060e06', bgElevated: '#0c180c', secondary: '#008040' }},
                'monochrome': {{ accent: '#e0e0e0', accentHover: '#c0c0c0', bg: '#0a0a0a', bgElevated: '#141414', secondary: '#888888' }}
            }};
            const t = themes[saved];
            if (t) {{
                const r = document.documentElement.style;
                r.setProperty('--color-accent', t.accent);
                r.setProperty('--color-accent-hover', t.accentHover);
                r.setProperty('--color-bg', t.bg);
                r.setProperty('--color-bg-elevated', t.bgElevated);
                r.setProperty('--color-secondary', t.secondary);
                r.setProperty('--color-accent-dim', t.accent + '1f');
                r.setProperty('--border-accent', t.accent + '59');
            }}
        }}
    }})();

    // ========================================
    // Widget Settings Panel
    // ========================================
    let wsWidgets = [];
    let wsDragItem = null;

    function openWidgetSettings() {{
        toggleMenu();
        const overlay = document.getElementById('widgetSettingsOverlay');
        overlay.classList.add('active');
        loadWidgetList();
    }}

    function closeWidgetSettings() {{
        document.getElementById('widgetSettingsOverlay').classList.remove('active');
    }}

    async function loadWidgetList() {{
        try {{
            const res = await fetch('/api/dashboard/layout');
            const data = await res.json();
            wsWidgets = data.widgets || [];
            renderWidgetList(data.categories || {{}});
        }} catch (e) {{
            document.getElementById('wsBody').innerHTML =
                '<p style="color:var(--color-error);text-align:center;padding:40px 0;">Failed to load widget data.</p>';
        }}
    }}

    function renderWidgetList(categories) {{
        const body = document.getElementById('wsBody');
        // Group widgets by category in their current order
        const catGroups = {{}};
        const catOrder = Object.keys(categories);
        catOrder.forEach(c => catGroups[c] = []);

        wsWidgets.forEach((w, idx) => {{
            w._idx = idx;
            const cat = w.category || 'system';
            if (!catGroups[cat]) catGroups[cat] = [];
            catGroups[cat].push(w);
        }});

        let html = '';
        catOrder.forEach(cat => {{
            const items = catGroups[cat];
            if (!items || items.length === 0) return;
            html += `<div class="ws-category">`;
            html += `<div class="ws-category-title">${{categories[cat] || cat}}</div>`;
            items.forEach(w => {{
                html += `
                <div class="ws-widget-item" draggable="true" data-id="${{w.id}}" data-idx="${{w._idx}}">
                    <span class="ws-drag-handle">&#9776;</span>
                    <div class="ws-widget-info">
                        <div class="ws-widget-name">${{w.name}}</div>
                        <div class="ws-widget-desc">${{w.description}}</div>
                    </div>
                    <label class="ws-toggle">
                        <input type="checkbox" ${{w.visible ? 'checked' : ''}} onchange="toggleWidget('${{w.id}}', this.checked)">
                        <span class="ws-toggle-slider"></span>
                    </label>
                </div>`;
            }});
            html += `</div>`;
        }});

        body.innerHTML = html;
        initDragAndDrop();
    }}

    function toggleWidget(id, visible) {{
        const w = wsWidgets.find(x => x.id === id);
        if (w) w.visible = visible;
    }}

    function initDragAndDrop() {{
        const items = document.querySelectorAll('.ws-widget-item');
        items.forEach(item => {{
            item.addEventListener('dragstart', e => {{
                wsDragItem = item;
                item.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', item.dataset.id);
            }});
            item.addEventListener('dragend', () => {{
                item.classList.remove('dragging');
                document.querySelectorAll('.ws-widget-item').forEach(i => i.classList.remove('drag-over'));
                wsDragItem = null;
            }});
            item.addEventListener('dragover', e => {{
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                if (wsDragItem && wsDragItem !== item) {{
                    item.classList.add('drag-over');
                }}
            }});
            item.addEventListener('dragleave', () => {{
                item.classList.remove('drag-over');
            }});
            item.addEventListener('drop', e => {{
                e.preventDefault();
                item.classList.remove('drag-over');
                if (!wsDragItem || wsDragItem === item) return;
                const fromId = wsDragItem.dataset.id;
                const toId = item.dataset.id;
                // Reorder wsWidgets
                const fromIdx = wsWidgets.findIndex(x => x.id === fromId);
                const toIdx = wsWidgets.findIndex(x => x.id === toId);
                if (fromIdx >= 0 && toIdx >= 0) {{
                    const [moved] = wsWidgets.splice(fromIdx, 1);
                    wsWidgets.splice(toIdx, 0, moved);
                }}
                // Re-render
                fetch('/api/dashboard/layout').then(r => r.json()).then(data => {{
                    renderWidgetList(data.categories || {{}});
                }});
            }});
        }});
    }}

    async function saveWidgetLayout() {{
        const order = wsWidgets.map(w => w.id);
        const hidden = wsWidgets.filter(w => !w.visible).map(w => w.id);
        try {{
            const res = await fetch('/api/dashboard/layout', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ order, hidden }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                closeWidgetSettings();
                ToastManager.success('Widget layout saved. Refreshing...');
                setTimeout(() => location.reload(), 800);
            }} else {{
                ToastManager.error('Failed to save layout');
            }}
        }} catch (e) {{
            ToastManager.error('Error saving layout: ' + e.message);
        }}
    }}

    async function resetWidgetLayout() {{
        try {{
            const res = await fetch('/api/dashboard/layout/reset', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: '{{}}'
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                closeWidgetSettings();
                ToastManager.success('Layout reset to default. Refreshing...');
                setTimeout(() => location.reload(), 800);
            }} else {{
                ToastManager.error('Failed to reset layout');
            }}
        }} catch (e) {{
            ToastManager.error('Error resetting layout: ' + e.message);
        }}
    }}

    // Close settings on Escape key
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            const overlay = document.getElementById('widgetSettingsOverlay');
            if (overlay.classList.contains('active')) {{
                closeWidgetSettings();
                e.stopPropagation();
            }}
        }}
    }});

    // ========================================
    // Mobile / Desktop Auto-Detection
    // ========================================
    const MobileManager = {{
        _isMobile: false,
        _isTablet: false,
        _mediaQueryMobile: window.matchMedia('(max-width: 480px)'),
        _mediaQueryTablet: window.matchMedia('(max-width: 768px)'),
        _mediaQueryTouch: window.matchMedia('(hover: none) and (pointer: coarse)'),

        init() {{
            // Listen for viewport changes (resize, rotation)
            this._mediaQueryMobile.addEventListener('change', (e) => this._onMobileChange(e));
            this._mediaQueryTablet.addEventListener('change', (e) => this._onTabletChange(e));

            // Initial detection
            this._isMobile = this._mediaQueryMobile.matches;
            this._isTablet = this._mediaQueryTablet.matches;
            this._applyMode();

            // Handle orientation changes
            window.addEventListener('orientationchange', () => {{
                setTimeout(() => this._applyMode(), 100);
            }});

            // Touch-specific: close menu on outside tap
            if (this._mediaQueryTouch.matches) {{
                document.addEventListener('touchstart', (e) => {{
                    const menu = document.getElementById('menu');
                    const hamburger = document.getElementById('hamburger');
                    if (menu.classList.contains('active') &&
                        !menu.contains(e.target) && !hamburger.contains(e.target)) {{
                        menu.classList.remove('active');
                        hamburger.classList.remove('active');
                        hamburger.setAttribute('aria-expanded', 'false');
                    }}
                }}, {{ passive: true }});
            }}
        }},

        _onMobileChange(e) {{
            this._isMobile = e.matches;
            this._applyMode();
        }},

        _onTabletChange(e) {{
            this._isTablet = e.matches;
            this._applyMode();
        }},

        _applyMode() {{
            const body = document.body;
            body.classList.toggle('is-mobile', this._isMobile);
            body.classList.toggle('is-tablet', this._isTablet && !this._isMobile);
            body.classList.toggle('is-desktop', !this._isTablet);
            body.classList.toggle('is-touch', this._mediaQueryTouch.matches);

            // On mobile, make submenus visible inline when parent is hovered/active
            if (this._isTablet) {{
                this._enableInlineSubmenus();
            }} else {{
                this._enableFlyoutSubmenus();
            }}
        }},

        _enableInlineSubmenus() {{
            // On mobile/tablet: submenus show on click, inline
            document.querySelectorAll('.menu-item.has-submenu').forEach(item => {{
                item.removeAttribute('onmouseenter');
                item.removeAttribute('onmouseleave');
                item.onclick = function(e) {{
                    e.stopPropagation();
                    const sub = this.querySelector('.submenu');
                    if (sub) {{
                        const isActive = sub.classList.contains('active');
                        // Close all other submenus first
                        document.querySelectorAll('.submenu.active').forEach(s => s.classList.remove('active'));
                        if (!isActive) sub.classList.add('active');
                    }}
                }};
            }});
        }},

        _enableFlyoutSubmenus() {{
            // On desktop: restore hover behavior
            document.querySelectorAll('.menu-item.has-submenu').forEach(item => {{
                item.setAttribute('onmouseenter', "showSubmenu('" + item.querySelector('.submenu').id + "')");
                item.setAttribute('onmouseleave', "hideSubmenu('" + item.querySelector('.submenu').id + "')");
                item.onclick = null;
            }});
        }},

        isMobile() {{ return this._isMobile; }},
        isTablet() {{ return this._isTablet; }},
        isTouch() {{ return this._mediaQueryTouch.matches; }}
    }};

    MobileManager.init();

    // Load saved theme
    const savedTheme = localStorage.getItem('dashboardTheme');
    if (savedTheme) {{
        // Apply theme without animation on load
        const themes = {{
            'default': {{ primary: '#00E5A0', background: '#0a0a0a' }},
            'cyberpunk': {{ primary: '#ff00ff', background: '#0a0a0a' }},
            'ocean': {{ primary: '#0080ff', background: '#001a33' }},
            'sunset': {{ primary: '#ff6400', background: '#1a0a00' }},
            'forest': {{ primary: '#00ff64', background: '#0a1a0a' }},
            'monochrome': {{ primary: '#ffffff', background: '#080808' }}
        }};
        const theme = themes[savedTheme];
        if (theme) {{
            document.body.style.background = theme.background;
            document.querySelector('h1').style.color = theme.primary;
        }}
    }}

    // Iframe loading overlay dismissal
    document.querySelectorAll('.widget-iframe-container iframe').forEach(function(iframe) {{
        iframe.addEventListener('load', function() {{
            iframe.closest('.widget-iframe-container').classList.add('iframe-loaded');
        }});
    }});

    // Offline Detection
    let _wasOffline = false;
    async function checkAgentConnection() {{
        try {{
            const r = await fetch('/api/agent/health', {{ signal: AbortSignal.timeout(5000) }});
            if (r.ok) {{
                document.getElementById('offlineBanner').style.display = 'none';
                if (_wasOffline) {{
                    ToastManager.success('Connection restored');
                    _wasOffline = false;
                }}
                return;
            }}
        }} catch (e) {{ /* offline */ }}
        document.getElementById('offlineBanner').style.display = 'flex';
        _wasOffline = true;
    }}
    setInterval(checkAgentConnection, 10000);
</script>
</main>
</body>
</html>'''
