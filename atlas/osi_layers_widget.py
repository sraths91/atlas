"""
OSI Layers Network Diagnostic Widget

Displays a visual 7-layer OSI stack with pass/warning/fail/blocked
status for each layer. Helps identify which network layer is causing
issues with a waterfall effect (lower-layer failures block higher layers).
"""
import logging

logger = logging.getLogger(__name__)


def get_osi_layers_widget_html():
    """Generate OSI Layers diagnostic widget HTML.

    Returns complete HTML page with:
    - 7-layer vertical stack (Layer 7 at top, Layer 1 at bottom)
    - Per-layer color accents (classic OSI color scheme)
    - Layer descriptions explaining what each layer tests
    - Color-coded status per layer (green/yellow/red/gray)
    - Expandable detail section per layer
    - Health score progress bar
    - Real-time per-layer progress during on-demand diagnostic
    - Run Diagnostic button for on-demand testing
    - Auto-refresh every 10 seconds
    """
    from atlas.agent_widget_styles import (
        get_widget_base_styles,
        get_widget_toast_script,
        get_widget_api_helpers_script,
    )

    base_styles = get_widget_base_styles()
    toast_script = get_widget_toast_script()
    api_helpers = get_widget_api_helpers_script()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSI Layers Diagnostic - ATLAS Agent</title>
    <style>
{base_styles}

/* ==================== OSI Widget Styles ==================== */
body {{ padding: 15px; background: var(--bg-base, #0a0a0f); color: var(--text-primary, #e8e8e8); }}

.nav-bar {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    font-size: 12px;
}}

.nav-bar a {{
    color: var(--text-muted, #666);
    text-decoration: none;
    transition: color 0.2s;
}}

.nav-bar a:hover {{ color: var(--text-primary, #e8e8e8); }}
.nav-bar .sep {{ color: var(--text-muted, #444); }}
.nav-bar .current {{ color: var(--text-secondary, #999); }}

.widget-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 8px;
}}

.widget-title {{
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

.header-right {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.health-score {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-secondary, #999);
}}

.health-score .score-value {{
    font-size: 22px;
    font-weight: 700;
    font-family: 'SF Mono', 'Menlo', monospace;
}}

.health-score .score-value.good {{ color: #22c55e; }}
.health-score .score-value.warning {{ color: #fbbf24; }}
.health-score .score-value.error {{ color: #ef4444; }}

.health-bar {{
    width: 120px;
    height: 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
    overflow: hidden;
}}

.health-bar-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s ease, background-color 0.3s ease;
}}

.health-bar-fill.good {{ background: #22c55e; }}
.health-bar-fill.warning {{ background: #fbbf24; }}
.health-bar-fill.error {{ background: #ef4444; }}

.overall-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.overall-badge.pass {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
.overall-badge.warning {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
.overall-badge.fail {{ background: rgba(239,68,68,0.15); color: #ef4444; }}

.meta-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    gap: 8px;
    flex-wrap: wrap;
}}

.last-tested {{
    font-size: 12px;
    color: var(--text-muted, #666);
}}

.btn-diagnostic {{
    padding: 6px 16px;
    border: 1px solid rgba(99,102,241,0.4);
    background: rgba(99,102,241,0.1);
    color: #818cf8;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}}

.btn-diagnostic:hover {{ background: rgba(99,102,241,0.2); }}
.btn-diagnostic:disabled {{ opacity: 0.5; cursor: not-allowed; }}

/* OSI Layer Stack */
.osi-stack {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}

/* Per-layer accent colors (classic OSI palette) */
.osi-layer {{
    background: var(--bg-elevated, #141420);
    border-radius: 8px;
    border-left: 4px solid #555;
    overflow: hidden;
    transition: border-color 0.3s ease, opacity 0.3s ease;
    animation: layerSlideIn 0.3s ease both;
}}

@keyframes layerSlideIn {{
    from {{ opacity: 0; transform: translateX(-8px); }}
    to {{ opacity: 1; transform: translateX(0); }}
}}

/* Layer accent colors - applied to border and number badge */
.osi-layer[data-layer="7"] {{ --layer-accent: #ef4444; }}
.osi-layer[data-layer="6"] {{ --layer-accent: #f97316; }}
.osi-layer[data-layer="5"] {{ --layer-accent: #eab308; }}
.osi-layer[data-layer="4"] {{ --layer-accent: #22c55e; }}
.osi-layer[data-layer="3"] {{ --layer-accent: #06b6d4; }}
.osi-layer[data-layer="2"] {{ --layer-accent: #3b82f6; }}
.osi-layer[data-layer="1"] {{ --layer-accent: #8b5cf6; }}

/* Pass state: use layer accent color */
.osi-layer.pass {{ border-left-color: var(--layer-accent); }}
.osi-layer.pass .layer-number {{ background: var(--layer-accent); }}

/* Override for warning/fail/blocked — status color takes priority */
.osi-layer.warning {{ border-left-color: #fbbf24; }}
.osi-layer.fail {{ border-left-color: #ef4444; }}
.osi-layer.blocked {{ border-left-color: #444; opacity: 0.5; }}
.osi-layer.unknown {{ border-left-color: #555; }}
.osi-layer.testing {{ border-left-color: var(--layer-accent); opacity: 0.7; }}

.osi-layer-header {{
    display: flex;
    align-items: center;
    padding: 10px 14px;
    cursor: pointer;
    gap: 10px;
    user-select: none;
}}

.osi-layer-header:hover {{ background: rgba(255,255,255,0.03); }}

.layer-number {{
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 13px;
    background: var(--layer-accent, #555);
    color: #fff;
    flex-shrink: 0;
    transition: background-color 0.3s;
}}

.layer-number.warning {{ background: #fbbf24; color: #000; }}
.layer-number.fail {{ background: #ef4444; color: #fff; }}
.layer-number.blocked {{ background: #444; color: #888; }}
.layer-number.unknown {{ background: #555; color: #888; }}
.layer-number.testing {{ background: var(--layer-accent, #555); opacity: 0.6; }}

@keyframes pulse {{
    0%, 100% {{ opacity: 0.6; }}
    50% {{ opacity: 1; }}
}}

.osi-layer.testing .layer-number {{
    animation: pulse 1.2s ease-in-out infinite;
}}

.layer-info {{
    flex: 1;
    min-width: 0;
}}

.layer-name {{
    font-weight: 600;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.layer-desc {{
    font-size: 10px;
    color: var(--text-muted, #666);
    margin-top: 1px;
    letter-spacing: 0.3px;
}}

.layer-status {{
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.layer-status.pass {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
.layer-status.warning {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
.layer-status.fail {{ background: rgba(239,68,68,0.15); color: #ef4444; }}
.layer-status.blocked {{ background: rgba(100,100,100,0.15); color: #888; }}
.layer-status.unknown {{ background: rgba(100,100,100,0.15); color: #666; }}
.layer-status.testing {{ background: rgba(99,102,241,0.15); color: #818cf8; }}

.layer-latency {{
    font-family: 'SF Mono', 'Menlo', monospace;
    font-size: 12px;
    color: var(--text-secondary, #999);
    min-width: 55px;
    text-align: right;
}}

.expand-icon {{
    font-size: 12px;
    color: #555;
    transition: transform 0.2s;
}}

.osi-layer.expanded .expand-icon {{ transform: rotate(90deg); }}

.layer-summary {{
    font-size: 11px;
    color: var(--text-muted, #666);
    padding: 0 14px 8px 52px;
}}

.layer-tests {{
    padding: 0 14px 10px 52px;
    display: none;
    border-top: 1px solid rgba(255,255,255,0.04);
    margin-top: 4px;
    padding-top: 8px;
}}

.osi-layer.expanded .layer-tests {{ display: block; }}

.test-row {{
    display: flex;
    align-items: center;
    padding: 4px 0;
    font-size: 12px;
    gap: 8px;
}}

.test-name {{
    flex: 1;
    color: var(--text-secondary, #999);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.test-status {{
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.test-status.pass {{ color: #22c55e; }}
.test-status.warning {{ color: #fbbf24; }}
.test-status.fail {{ color: #ef4444; }}
.test-status.blocked {{ color: #888; }}

.test-value {{
    font-family: 'SF Mono', 'Menlo', monospace;
    color: var(--text-muted, #666);
    font-size: 11px;
    min-width: 80px;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.duration-note {{
    text-align: center;
    font-size: 11px;
    color: var(--text-muted, #666);
    margin-top: 12px;
}}

.empty-state {{
    text-align: center;
    padding: 40px;
    color: var(--text-muted, #666);
    font-size: 14px;
}}

.empty-state p {{ margin-bottom: 12px; }}

/* Progress bar during diagnostic */
.diag-progress {{
    height: 3px;
    background: rgba(255,255,255,0.05);
    border-radius: 2px;
    margin-bottom: 12px;
    overflow: hidden;
    display: none;
}}

.diag-progress.active {{ display: block; }}

.diag-progress-fill {{
    height: 100%;
    background: linear-gradient(90deg, #818cf8, #6366f1);
    border-radius: 2px;
    transition: width 0.4s ease;
    width: 0%;
}}

/* ==================== QoE Panel ==================== */
.qoe-panel {{
    margin-top: 18px;
    padding: 14px;
    background: var(--bg-elevated, #141420);
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.06);
    display: none;
}}

.qoe-panel.visible {{ display: block; }}

.qoe-panel-title {{
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary, #999);
    margin-bottom: 12px;
}}

.qoe-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 10px;
}}

.qoe-card {{
    background: rgba(255,255,255,0.03);
    border-radius: 6px;
    padding: 10px 12px;
    border: 1px solid rgba(255,255,255,0.04);
}}

.qoe-card-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted, #666);
    margin-bottom: 4px;
}}

.qoe-card-value {{
    font-size: 20px;
    font-weight: 700;
    font-family: 'SF Mono', 'Menlo', monospace;
}}

.qoe-card-sub {{
    font-size: 11px;
    color: var(--text-muted, #666);
    margin-top: 2px;
}}

.vc-badges {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 4px;
}}

.vc-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
}}

.vc-badge.good {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
.vc-badge.fair {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
.vc-badge.poor {{ background: rgba(239,68,68,0.15); color: #ef4444; }}

.cf-trace {{
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.02);
    border-radius: 4px;
    font-family: 'SF Mono', 'Menlo', monospace;
    font-size: 11px;
    color: var(--text-muted, #666);
    border: 1px solid rgba(255,255,255,0.04);
}}

.btn-nq {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: 1px solid rgba(6,182,212,0.4);
    background: rgba(6,182,212,0.1);
    color: #22d3ee;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 10px;
}}

.btn-nq:hover {{ background: rgba(6,182,212,0.2); }}
.btn-nq:disabled {{ opacity: 0.5; cursor: not-allowed; }}

.btn-nq .hint {{
    font-size: 10px;
    color: rgba(34,211,238,0.5);
    font-weight: 400;
}}

.nq-results {{
    margin-top: 10px;
    display: none;
}}

.nq-results.visible {{ display: block; }}

.nq-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 8px;
}}

.nq-card {{
    background: rgba(6,182,212,0.05);
    border: 1px solid rgba(6,182,212,0.1);
    border-radius: 6px;
    padding: 8px 10px;
    text-align: center;
}}

.nq-card-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted, #666);
}}

.nq-card-value {{
    font-size: 18px;
    font-weight: 700;
    font-family: 'SF Mono', 'Menlo', monospace;
    color: #22d3ee;
    margin-top: 2px;
}}

.nq-card-unit {{
    font-size: 10px;
    color: var(--text-muted, #666);
}}

/* ==================== Custom Scan Panel ==================== */
.custom-scan-toggle {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: 1px solid rgba(168,85,247,0.4);
    background: rgba(168,85,247,0.1);
    color: #c084fc;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}}

.custom-scan-toggle:hover {{ background: rgba(168,85,247,0.2); }}

.custom-scan-panel {{
    margin-top: 12px;
    padding: 14px;
    background: var(--bg-elevated, #141420);
    border-radius: 8px;
    border: 1px solid rgba(168,85,247,0.15);
    display: none;
}}

.custom-scan-panel.visible {{ display: block; }}

.cs-section {{
    margin-bottom: 12px;
}}

.cs-section:last-child {{ margin-bottom: 0; }}

.cs-label {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary, #999);
    margin-bottom: 6px;
}}

.cs-layer-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    font-size: 10px;
    font-weight: 700;
    color: #fff;
}}

.cs-layer-badge.l3 {{ background: #06b6d4; }}
.cs-layer-badge.l4 {{ background: #22c55e; }}
.cs-layer-badge.l6 {{ background: #f97316; }}
.cs-layer-badge.l7 {{ background: #ef4444; }}

.cs-input {{
    width: 100%;
    padding: 8px 10px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px;
    color: var(--text-primary, #e8e8e8);
    font-family: 'SF Mono', 'Menlo', monospace;
    font-size: 12px;
    outline: none;
    transition: border-color 0.2s;
    box-sizing: border-box;
}}

.cs-input:focus {{ border-color: rgba(168,85,247,0.5); }}

.cs-input::placeholder {{ color: var(--text-muted, #555); }}

.cs-hint {{
    font-size: 10px;
    color: var(--text-muted, #555);
    margin-top: 3px;
}}

.cs-actions {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 14px;
}}

.btn-custom-scan {{
    padding: 8px 20px;
    border: 1px solid rgba(168,85,247,0.5);
    background: rgba(168,85,247,0.15);
    color: #c084fc;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}}

.btn-custom-scan:hover {{ background: rgba(168,85,247,0.25); }}
.btn-custom-scan:disabled {{ opacity: 0.5; cursor: not-allowed; }}

.cs-status {{
    font-size: 12px;
    color: var(--text-muted, #666);
}}

.cs-results {{
    margin-top: 14px;
    display: none;
}}

.cs-results.visible {{ display: block; }}

.cs-results-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}}

.cs-results-title {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary, #999);
}}

.cs-results-summary {{
    font-family: 'SF Mono', 'Menlo', monospace;
    font-size: 11px;
    color: var(--text-muted, #666);
}}

.cs-result-row {{
    display: flex;
    align-items: center;
    padding: 6px 0;
    font-size: 12px;
    gap: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}}

.cs-result-row:last-child {{ border-bottom: none; }}

.cs-result-name {{
    flex: 1;
    color: var(--text-secondary, #999);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.cs-result-status {{
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.cs-result-status.pass {{ color: #22c55e; }}
.cs-result-status.warning {{ color: #fbbf24; }}
.cs-result-status.fail {{ color: #ef4444; }}

.cs-result-value {{
    font-family: 'SF Mono', 'Menlo', monospace;
    color: var(--text-muted, #666);
    font-size: 11px;
    min-width: 100px;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

@media (max-width: 480px) {{
    .widget-header {{ flex-direction: column; align-items: flex-start; }}
    .layer-latency {{ min-width: 40px; font-size: 11px; }}
    .test-value {{ min-width: 60px; font-size: 10px; }}
    .layer-desc {{ display: none; }}
    .qoe-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .nq-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .cs-result-value {{ min-width: 70px; font-size: 10px; }}
}}
    </style>
</head>
<body>
    <a href="#osi-stack" class="skip-link" aria-label="Skip to layer stack">Skip to content</a>

    <nav class="nav-bar" aria-label="Breadcrumb">
        <a href="/">Dashboard</a>
        <span class="sep">/</span>
        <span class="current">OSI Layers</span>
    </nav>

    <main>
        <div class="widget-header">
            <span class="widget-title">OSI Layers Diagnostic</span>
            <div class="header-right">
                <div class="health-score">
                    <div>
                        <span class="score-value good" id="healthScore">--</span>
                        <span>/100</span>
                    </div>
                    <div class="health-bar">
                        <div class="health-bar-fill good" id="healthBar" style="width: 0%"></div>
                    </div>
                </div>
                <span class="overall-badge pass" id="overallStatus">--</span>
            </div>
        </div>

        <div class="meta-row">
            <span class="last-tested" id="lastTested">Not yet tested</span>
            <div style="display:flex;gap:8px">
                <button class="custom-scan-toggle" onclick="toggleCustomScan()"
                        aria-label="Toggle custom scan panel">Custom Scan</button>
                <button class="btn-diagnostic" id="runBtn" onclick="runDiagnostic()"
                        aria-label="Run network diagnostic">Run Diagnostic</button>
            </div>
        </div>

        <!-- Custom Scan Panel -->
        <div class="custom-scan-panel" id="customScanPanel">
            <div class="cs-section">
                <div class="cs-label"><span class="cs-layer-badge l4">4</span> Port Scan</div>
                <input class="cs-input" id="csPorts" type="text"
                       placeholder="e.g. google.com:443, github.com:22, smtp.gmail.com:587">
                <div class="cs-hint">host:port pairs, comma-separated</div>
            </div>
            <div class="cs-section">
                <div class="cs-label"><span class="cs-layer-badge l3">3</span> Ping Targets</div>
                <input class="cs-input" id="csPing" type="text"
                       placeholder="e.g. 8.8.8.8, 1.1.1.1, cloudflare.com">
                <div class="cs-hint">IP addresses or hostnames, comma-separated</div>
            </div>
            <div class="cs-section">
                <div class="cs-label"><span class="cs-layer-badge l7">7</span> DNS Lookup</div>
                <input class="cs-input" id="csDns" type="text"
                       placeholder="e.g. example.com, myapp.internal, api.company.com">
                <div class="cs-hint">Hostnames to resolve, comma-separated</div>
            </div>
            <div class="cs-section">
                <div class="cs-label"><span class="cs-layer-badge l7">7</span> HTTP Check</div>
                <input class="cs-input" id="csHttp" type="text"
                       placeholder="e.g. https://api.github.com, https://slack.com/api/api.test">
                <div class="cs-hint">Full URLs to GET, comma-separated</div>
            </div>
            <div class="cs-section">
                <div class="cs-label"><span class="cs-layer-badge l6">6</span> TLS Check</div>
                <input class="cs-input" id="csTls" type="text"
                       placeholder="e.g. google.com, api.stripe.com:443">
                <div class="cs-hint">Hostnames (optional :port), comma-separated</div>
            </div>
            <div class="cs-actions">
                <button class="btn-custom-scan" id="csRunBtn" onclick="runCustomScan()">Run Custom Scan</button>
                <span class="cs-status" id="csStatus"></span>
            </div>
            <div class="cs-results" id="csResults">
                <div class="cs-results-header">
                    <span class="cs-results-title">Scan Results</span>
                    <span class="cs-results-summary" id="csSummary"></span>
                </div>
                <div id="csResultsList"></div>
            </div>
        </div>

        <div class="diag-progress" id="diagProgress">
            <div class="diag-progress-fill" id="diagProgressFill"></div>
        </div>

        <div class="osi-stack" id="osiStack" role="list" aria-label="OSI Layer diagnostic results">
            <div class="empty-state" id="emptyState">
                <p>No diagnostic data yet.</p>
                <p>Click <strong>Run Diagnostic</strong> to test all 7 OSI layers.</p>
            </div>
        </div>

        <div class="duration-note" id="durationNote" style="display:none"></div>

        <!-- QoE Summary Panel -->
        <div class="qoe-panel" id="qoePanel">
            <div class="qoe-panel-title">Quality of Experience</div>
            <div class="qoe-grid" id="qoeGrid"></div>
            <div class="cf-trace" id="cfTrace" style="display:none"></div>
            <button class="btn-nq" id="nqBtn" onclick="runNetworkQuality()">
                Run networkQuality <span class="hint">(~20s test)</span>
            </button>
            <div class="nq-results" id="nqResults">
                <div class="nq-grid" id="nqGrid"></div>
            </div>
        </div>
    </main>

    <script>
{api_helpers}
{toast_script}

// ==================== Layer Metadata ====================
const LAYER_META = {{
    7: {{ desc: 'HTTP, DNS, SaaS Endpoints, Captive Portal' }},
    6: {{ desc: 'TLS/SSL, DNS-over-HTTPS, Encryption' }},
    5: {{ desc: 'Connections, Keep-Alive' }},
    4: {{ desc: 'TCP, UDP, Port Blocking Detection' }},
    3: {{ desc: 'IP, Routing, IPv6, Path MTU' }},
    2: {{ desc: 'MAC, ARP, Switching' }},
    1: {{ desc: 'Cables, WiFi, Signal Strength' }}
}};

// ==================== State ====================
let diagnosticData = null;

// ==================== Update from API ====================
async function update() {{
    try {{
        const result = await apiFetch('/api/osi-layers');
        if (result.ok && result.data && result.data.layers && result.data.layers.length > 0) {{
            diagnosticData = result.data;
            renderLayers(diagnosticData);
        }}
    }} catch (e) {{
        console.error('OSI update failed:', e);
    }}
}}

// ==================== On-demand Diagnostic ====================
async function runDiagnostic() {{
    const btn = document.getElementById('runBtn');
    const progress = document.getElementById('diagProgress');
    const progressFill = document.getElementById('diagProgressFill');
    btn.disabled = true;
    btn.textContent = 'Testing...';
    progress.classList.add('active');

    // Show testing state on all layers
    showTestingState();

    // Animate progress bar (estimated ~5s)
    let pct = 0;
    const progressTimer = setInterval(() => {{
        pct = Math.min(pct + 2, 90);
        progressFill.style.width = pct + '%';
    }}, 100);

    try {{
        const result = await apiFetch('/api/osi-layers/test', {{ method: 'POST' }});
        clearInterval(progressTimer);
        progressFill.style.width = '100%';

        if (result.ok && result.data) {{
            diagnosticData = result.data.result || result.data;
            renderLayers(diagnosticData);
            if (typeof ToastManager !== 'undefined') {{
                ToastManager.success('Diagnostic complete');
            }}
        }} else {{
            if (typeof ToastManager !== 'undefined') {{
                ToastManager.error('Diagnostic failed');
            }}
        }}
    }} catch (e) {{
        clearInterval(progressTimer);
        console.error('Diagnostic failed:', e);
        if (typeof ToastManager !== 'undefined') {{
            ToastManager.error('Diagnostic request failed');
        }}
    }}

    setTimeout(() => {{
        progress.classList.remove('active');
        progressFill.style.width = '0%';
    }}, 500);

    btn.disabled = false;
    btn.textContent = 'Run Diagnostic';
}}

function showTestingState() {{
    const stack = document.getElementById('osiStack');
    const empty = document.getElementById('emptyState');
    if (empty) empty.style.display = 'none';

    // If layers exist, set them all to testing state
    if (diagnosticData && diagnosticData.layers) {{
        stack.innerHTML = '';
        const sorted = [...diagnosticData.layers].sort((a, b) => b.layer_number - a.layer_number);
        for (const layer of sorted) {{
            const el = createLayerElement({{
                ...layer,
                status: 'testing',
                summary: 'Testing...'
            }});
            stack.appendChild(el);
        }}
    }} else {{
        // No previous data — show placeholder layers
        stack.innerHTML = '';
        for (let i = 7; i >= 1; i--) {{
            const names = {{7:'Application',6:'Presentation',5:'Session',4:'Transport',3:'Network',2:'Data Link',1:'Physical'}};
            const el = createLayerElement({{
                layer_number: i,
                layer_name: names[i],
                status: 'testing',
                tests: [],
                summary: 'Testing...',
                latency_ms: null
            }});
            stack.appendChild(el);
        }}
    }}
}}

// ==================== Render ====================
function getScoreClass(score) {{
    if (score >= 80) return 'good';
    if (score >= 50) return 'warning';
    return 'error';
}}

function renderLayers(data) {{
    if (!data || !data.layers) return;

    // Hide empty state
    const empty = document.getElementById('emptyState');
    if (empty) empty.style.display = 'none';

    // Health score
    const scoreEl = document.getElementById('healthScore');
    const barEl = document.getElementById('healthBar');
    const cls = getScoreClass(data.health_score);
    scoreEl.textContent = data.health_score;
    scoreEl.className = 'score-value ' + cls;
    barEl.style.width = data.health_score + '%';
    barEl.className = 'health-bar-fill ' + cls;

    // Overall status
    const statusEl = document.getElementById('overallStatus');
    statusEl.textContent = data.overall_status.toUpperCase();
    statusEl.className = 'overall-badge ' + data.overall_status;

    // Timestamp
    if (data.timestamp) {{
        const ts = new Date(data.timestamp);
        document.getElementById('lastTested').textContent =
            'Last tested: ' + ts.toLocaleTimeString();
    }}

    // Duration
    if (data.duration_ms) {{
        const note = document.getElementById('durationNote');
        note.style.display = 'block';
        note.textContent = 'Diagnostic completed in ' + (data.duration_ms / 1000).toFixed(1) + 's';
    }}

    // Render layer stack (7 at top -> 1 at bottom)
    const stack = document.getElementById('osiStack');
    const sortedLayers = [...data.layers].sort((a, b) => b.layer_number - a.layer_number);

    stack.innerHTML = '';
    sortedLayers.forEach((layer, idx) => {{
        const el = createLayerElement(layer);
        el.style.animationDelay = (idx * 0.05) + 's';
        stack.appendChild(el);
    }});

    // Render QoE panel if data exists
    renderQoE(data);
}}

function createLayerElement(layer) {{
    const el = document.createElement('div');
    el.className = 'osi-layer ' + layer.status;
    el.setAttribute('role', 'listitem');
    el.setAttribute('data-layer', layer.layer_number);

    const meta = LAYER_META[layer.layer_number] || {{}};
    const latencyStr = layer.latency_ms != null
        ? layer.latency_ms.toFixed(0) + 'ms'
        : '';

    const statusLabel = layer.status === 'testing' ? 'TESTING' : layer.status.toUpperCase();

    const testsHtml = (layer.tests || []).map(t => `
        <div class="test-row">
            <span class="test-name">${{escapeHtml(t.name)}}</span>
            <span class="test-status ${{t.status}}">${{t.status.toUpperCase()}}</span>
            <span class="test-value">${{escapeHtml(t.value || t.error || '--')}}</span>
        </div>
    `).join('');

    el.innerHTML = `
        <div class="osi-layer-header" onclick="toggleLayer(this)"
             role="button" aria-expanded="false" tabindex="0"
             onkeydown="if(event.key==='Enter'||event.key===' '){{toggleLayer(this);event.preventDefault();}}">
            <span class="layer-number ${{layer.status}}">${{layer.layer_number}}</span>
            <div class="layer-info">
                <div class="layer-name">${{escapeHtml(layer.layer_name)}}</div>
                <div class="layer-desc">${{escapeHtml(meta.desc || '')}}</div>
            </div>
            <span class="layer-status ${{layer.status}}">${{statusLabel}}</span>
            <span class="layer-latency">${{latencyStr}}</span>
            <span class="expand-icon">&#9654;</span>
        </div>
        <div class="layer-summary">${{escapeHtml(layer.summary || '')}}</div>
        ${{layer.tests && layer.tests.length ? `<div class="layer-tests">${{testsHtml}}</div>` : ''}}
    `;

    return el;
}}

function toggleLayer(headerEl) {{
    const layer = headerEl.closest('.osi-layer');
    layer.classList.toggle('expanded');
    headerEl.setAttribute('aria-expanded',
        layer.classList.contains('expanded') ? 'true' : 'false');
}}

function escapeHtml(str) {{
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}}

// ==================== QoE Rendering ====================
function capitalize(s) {{
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1);
}}

function getMosColor(mos) {{
    if (mos >= 4.0) return '#22c55e';
    if (mos >= 3.0) return '#fbbf24';
    if (mos >= 2.0) return '#f97316';
    return '#ef4444';
}}

function renderQoE(data) {{
    const panel = document.getElementById('qoePanel');
    const grid = document.getElementById('qoeGrid');
    const cfEl = document.getElementById('cfTrace');
    if (!data || !data.qoe) return;

    const qoe = data.qoe;
    panel.classList.add('visible');
    grid.innerHTML = '';

    // MOS Score card
    if (qoe.mos != null) {{
        const mosColor = getMosColor(qoe.mos);
        grid.innerHTML += `
            <div class="qoe-card">
                <div class="qoe-card-label">Voice Quality (MOS)</div>
                <div class="qoe-card-value" style="color: ${{mosColor}}">${{qoe.mos.toFixed(1)}}</div>
                <div class="qoe-card-sub">${{capitalize(qoe.mos_rating || '')}}</div>
            </div>`;
    }}

    // Video Conferencing card
    if (qoe.video_conf) {{
        let badges = '';
        for (const [app, rating] of Object.entries(qoe.video_conf)) {{
            const cls = rating === 'good' ? 'good' : rating === 'fair' ? 'fair' : 'poor';
            badges += `<span class="vc-badge ${{cls}}">${{capitalize(app)}} ${{capitalize(rating)}}</span>`;
        }}
        grid.innerHTML += `
            <div class="qoe-card">
                <div class="qoe-card-label">Video Conferencing</div>
                <div class="vc-badges">${{badges}}</div>
            </div>`;
    }}

    // VPN Status card
    if (qoe.vpn != null) {{
        const vpnConnected = qoe.vpn.connected;
        const vpnColor = vpnConnected ? '#22c55e' : '#666';
        const vpnLabel = vpnConnected ? (qoe.vpn.client || 'Connected') : 'Not Connected';
        grid.innerHTML += `
            <div class="qoe-card">
                <div class="qoe-card-label">VPN Status</div>
                <div class="qoe-card-value" style="color: ${{vpnColor}}; font-size: 16px;">${{escapeHtml(vpnLabel)}}</div>
            </div>`;
    }}

    // Captive Portal card
    if (qoe.captive_portal != null) {{
        const cpOk = !qoe.captive_portal;
        const cpColor = cpOk ? '#22c55e' : '#ef4444';
        const cpText = cpOk ? 'Clear' : 'Detected';
        grid.innerHTML += `
            <div class="qoe-card">
                <div class="qoe-card-label">Captive Portal</div>
                <div class="qoe-card-value" style="color: ${{cpColor}}; font-size: 16px;">${{cpText}}</div>
            </div>`;
    }}

    // Cloudflare Trace
    if (data.cloudflare_trace && Object.keys(data.cloudflare_trace).length > 0) {{
        const cf = data.cloudflare_trace;
        const parts = [];
        if (cf.colo) parts.push('PoP: ' + cf.colo);
        if (cf.tls) parts.push('TLS: ' + cf.tls);
        if (cf.http) parts.push(cf.http);
        if (cf.loc) parts.push('Location: ' + cf.loc);
        if (cf.ip) parts.push('IP: ' + cf.ip);
        if (parts.length > 0) {{
            cfEl.style.display = 'block';
            cfEl.textContent = parts.join(' | ');
        }}
    }}
}}

// ==================== networkQuality ====================
async function runNetworkQuality() {{
    const btn = document.getElementById('nqBtn');
    const results = document.getElementById('nqResults');
    const grid = document.getElementById('nqGrid');

    btn.disabled = true;
    btn.innerHTML = 'Running... <span class="hint">(please wait)</span>';

    try {{
        const result = await apiFetch('/api/osi-layers/network-quality', {{ method: 'POST' }});

        if (result.ok && result.data && result.data.status === 'success') {{
            const d = result.data;
            grid.innerHTML = `
                <div class="nq-card">
                    <div class="nq-card-label">Download</div>
                    <div class="nq-card-value">${{d.download_mbps}}</div>
                    <div class="nq-card-unit">Mbps</div>
                </div>
                <div class="nq-card">
                    <div class="nq-card-label">Upload</div>
                    <div class="nq-card-value">${{d.upload_mbps}}</div>
                    <div class="nq-card-unit">Mbps</div>
                </div>
                <div class="nq-card">
                    <div class="nq-card-label">DL Responsiveness</div>
                    <div class="nq-card-value">${{d.dl_responsiveness_rpm}}</div>
                    <div class="nq-card-unit">RPM</div>
                </div>
                <div class="nq-card">
                    <div class="nq-card-label">UL Responsiveness</div>
                    <div class="nq-card-value">${{d.ul_responsiveness_rpm}}</div>
                    <div class="nq-card-unit">RPM</div>
                </div>
                <div class="nq-card">
                    <div class="nq-card-label">Idle Latency</div>
                    <div class="nq-card-value">${{d.idle_latency_ms}}</div>
                    <div class="nq-card-unit">ms</div>
                </div>
                <div class="nq-card">
                    <div class="nq-card-label">Bufferbloat</div>
                    <div class="nq-card-value">${{d.bufferbloat_grade}}</div>
                    <div class="nq-card-unit">grade</div>
                </div>
            `;
            results.classList.add('visible');
            if (typeof ToastManager !== 'undefined') {{
                ToastManager.success('networkQuality complete');
            }}
        }} else {{
            const err = (result.data && result.data.error) || 'Test failed';
            if (typeof ToastManager !== 'undefined') {{
                ToastManager.error(err);
            }}
        }}
    }} catch (e) {{
        console.error('networkQuality failed:', e);
        if (typeof ToastManager !== 'undefined') {{
            ToastManager.error('networkQuality request failed');
        }}
    }}

    btn.disabled = false;
    btn.innerHTML = 'Run networkQuality <span class="hint">(~20s test)</span>';
}}

// ==================== Custom Scan ====================
function toggleCustomScan() {{
    const panel = document.getElementById('customScanPanel');
    panel.classList.toggle('visible');
}}

function parseHostPort(str) {{
    str = str.trim();
    if (!str) return null;
    const parts = str.split(':');
    if (parts.length === 2 && parts[1]) {{
        return {{ host: parts[0].trim(), port: parseInt(parts[1].trim(), 10) }};
    }}
    return null;
}}

function parseTlsTarget(str) {{
    str = str.trim();
    if (!str) return null;
    const parts = str.split(':');
    if (parts.length === 2 && parts[1]) {{
        return {{ host: parts[0].trim(), port: parseInt(parts[1].trim(), 10) }};
    }}
    return {{ host: str, port: 443 }};
}}

async function runCustomScan() {{
    const btn = document.getElementById('csRunBtn');
    const statusEl = document.getElementById('csStatus');
    const resultsDiv = document.getElementById('csResults');
    const listDiv = document.getElementById('csResultsList');
    const summaryEl = document.getElementById('csSummary');

    // Parse inputs
    const portsRaw = document.getElementById('csPorts').value;
    const pingRaw = document.getElementById('csPing').value;
    const dnsRaw = document.getElementById('csDns').value;
    const httpRaw = document.getElementById('csHttp').value;
    const tlsRaw = document.getElementById('csTls').value;

    const options = {{}};

    if (portsRaw.trim()) {{
        options.ports = portsRaw.split(',').map(s => parseHostPort(s)).filter(Boolean);
    }}
    if (pingRaw.trim()) {{
        options.ping_targets = pingRaw.split(',').map(s => s.trim()).filter(Boolean);
    }}
    if (dnsRaw.trim()) {{
        options.dns_hostnames = dnsRaw.split(',').map(s => s.trim()).filter(Boolean);
    }}
    if (httpRaw.trim()) {{
        options.http_urls = httpRaw.split(',').map(s => s.trim()).filter(Boolean);
    }}
    if (tlsRaw.trim()) {{
        options.tls_targets = tlsRaw.split(',').map(s => parseTlsTarget(s)).filter(Boolean);
    }}

    const totalTargets = (options.ports || []).length + (options.ping_targets || []).length +
        (options.dns_hostnames || []).length + (options.http_urls || []).length +
        (options.tls_targets || []).length;

    if (totalTargets === 0) {{
        statusEl.textContent = 'Enter at least one target';
        statusEl.style.color = '#fbbf24';
        return;
    }}

    btn.disabled = true;
    statusEl.textContent = `Scanning ${{totalTargets}} target${{totalTargets > 1 ? 's' : ''}}...`;
    statusEl.style.color = '#818cf8';
    resultsDiv.classList.remove('visible');

    try {{
        const result = await apiFetch('/api/osi-layers/custom-scan', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(options)
        }});

        if (result.ok && result.data && result.data.result) {{
            const r = result.data.result;
            const tests = r.tests || [];
            const s = r.summary || {{}};

            // Render summary
            summaryEl.textContent = `${{s.pass || 0}} pass · ${{s.warning || 0}} warn · ${{s.fail || 0}} fail · ${{r.duration_ms}}ms`;

            // Render individual results
            listDiv.innerHTML = tests.map(t => `
                <div class="cs-result-row">
                    <span class="cs-result-name" title="${{escapeHtml(t.detail || t.name)}}">${{escapeHtml(t.name)}}</span>
                    <span class="cs-result-status ${{t.status}}">${{t.status.toUpperCase()}}</span>
                    <span class="cs-result-value" title="${{escapeHtml(t.detail || '')}}">${{escapeHtml(t.value || t.error || '--')}}</span>
                </div>
            `).join('');

            resultsDiv.classList.add('visible');
            statusEl.textContent = 'Scan complete';
            statusEl.style.color = '#22c55e';

            if (typeof ToastManager !== 'undefined') {{
                ToastManager.success(`Custom scan: ${{s.pass}}/${{s.total}} passed`);
            }}
        }} else {{
            const err = (result.data && result.data.error) || 'Scan failed';
            statusEl.textContent = err;
            statusEl.style.color = '#ef4444';
            if (typeof ToastManager !== 'undefined') {{
                ToastManager.error(err);
            }}
        }}
    }} catch (e) {{
        console.error('Custom scan failed:', e);
        statusEl.textContent = 'Request failed';
        statusEl.style.color = '#ef4444';
        if (typeof ToastManager !== 'undefined') {{
            ToastManager.error('Custom scan request failed');
        }}
    }}

    btn.disabled = false;
}}

// ==================== Init ====================
update();
const _ivUpdate = setInterval(update, 10000);
window.addEventListener('beforeunload', () => {{ clearInterval(_ivUpdate); }});
    </script>
</body>
</html>'''
