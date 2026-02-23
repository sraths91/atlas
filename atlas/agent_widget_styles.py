"""
Agent Widget Shared Styles
Unified design system for all ATLAS Agent widgets.

Provides:
- CSS custom properties design system
- Toast notification system
- Accessibility features (skip links, focus states, ARIA support)
- Responsive breakpoints
- Shared component styles

Toast, API helpers, accessibility, and loading animations are imported from
atlas.shared_styles (shared with fleet_login_page.py).

Created: January 5, 2026 (Phase 5: Agent Dashboard UX/UI Modernization)
"""
from atlas.shared_styles import (
    get_toast_css as _shared_toast_css,
    get_toast_script as _shared_toast_script,
    get_api_helpers_script as _shared_api_helpers,
    get_accessibility_css as _shared_a11y_css,
    get_loading_css as _shared_loading_css,
)


def get_widget_base_styles():
    """Return the shared CSS design system with custom properties for agent widgets"""
    return '''
        /* ========================================
           CSS Custom Properties Design System
           ======================================== */
        :root {
            /* Colors - Primary (Unified Teal-Green) */
            --color-primary: #00E5A0;
            --color-primary-hover: #00C890;
            --color-primary-glow: rgba(0, 229, 160, 0.3);

            /* Colors - Secondary (Cyan) */
            --color-secondary: #00c8ff;
            --color-secondary-hover: #00a8dd;

            /* Colors - Accent Colors for Widgets */
            --color-speedtest: #00E5A0;
            --color-wifi: #00ff64;
            --color-ping: #00E5A0;
            --color-health: #00c8ff;
            --color-cpu: #00c8ff;
            --color-memory: #00ff64;
            --color-disk: #ffc800;
            --color-network: #64ff00;

            /* Colors - Status */
            --color-success: #22c55e;
            --color-warning: #ffd93d;
            --color-error: #ff4444;
            --color-error-hover: #dd3333;

            /* Colors - Backgrounds */
            --bg-primary: #0a0a0a;
            --bg-secondary: #1a1a1a;
            --bg-elevated: #2a2a2a;
            --bg-overlay: rgba(0, 0, 0, 0.8);

            /* Colors - Text (WCAG AA compliant - 4.5:1 contrast ratio) */
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --text-muted: #888888;
            --text-on-primary: #000000;

            /* Spacing */
            --space-xs: 4px;
            --space-sm: 8px;
            --space-md: 16px;
            --space-lg: 24px;
            --space-xl: 40px;

            /* Border Radius */
            --radius-sm: 4px;
            --radius-md: 8px;
            --radius-lg: 15px;
            --radius-xl: 20px;
            --radius-full: 9999px;

            /* Shadows */
            --shadow-glow: 0 0 20px var(--color-primary-glow);
            --shadow-glow-error: 0 0 20px rgba(255, 68, 68, 0.3);
            --shadow-elevated: 0 4px 12px rgba(0, 0, 0, 0.3);
            --shadow-widget: 0 8px 32px rgba(0, 0, 0, 0.5);
            --shadow-focus: 0 0 0 3px var(--color-primary-glow);

            /* Typography */
            --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            --font-mono: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
            --font-size-xs: 11px;
            --font-size-sm: 12px;
            --font-size-md: 14px;
            --font-size-lg: 16px;
            --font-size-xl: 18px;
            --font-size-2xl: 24px;
            --font-size-3xl: 32px;
            --line-height: 1.6;

            /* Transitions */
            --transition-fast: 0.15s ease;
            --transition-normal: 0.2s ease;
            --transition-slow: 0.3s ease;

            /* Z-index layers */
            --z-dropdown: 100;
            --z-modal: 1000;
            --z-toast: 2000;
        }

        /* ========================================
           Base Reset & Typography
           ======================================== */
        *, *::before, *::after {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            font-size: 16px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        body {
            font-family: var(--font-family);
            font-size: var(--font-size-md);
            line-height: var(--line-height);
            color: var(--text-primary);
            background: var(--bg-secondary);
            min-height: 100vh;
        }

        /* ========================================
           Accessibility - Skip Link
           ======================================== */
        .skip-link {
            position: absolute;
            top: -100%;
            left: 50%;
            transform: translateX(-50%);
            background: var(--color-primary);
            color: var(--text-on-primary);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-md);
            font-weight: 600;
            z-index: var(--z-modal);
            transition: top var(--transition-fast);
            text-decoration: none;
        }

        .skip-link:focus {
            top: var(--space-md);
            outline: none;
        }

        /* ========================================
           Focus States (Accessibility)
           ======================================== */
        :focus {
            outline: none;
        }

        :focus-visible {
            outline: 2px solid var(--color-primary);
            outline-offset: 2px;
        }

        /* ========================================
           Widget Container Styles
           ======================================== */
        .widget {
            background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-secondary) 100%);
            border-radius: var(--radius-xl);
            padding: var(--space-lg);
            box-shadow: var(--shadow-widget);
            position: relative;
            overflow: hidden;
        }

        .widget-bordered {
            border: 2px solid var(--color-primary);
        }

        .widget-bordered.speedtest { border-color: var(--color-speedtest); }
        .widget-bordered.wifi { border-color: var(--color-wifi); }
        .widget-bordered.ping { border-color: var(--color-ping); }
        .widget-bordered.health { border-color: var(--color-health); }

        /* Widget gradient border effect */
        .widget-gradient::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(45deg, var(--color-primary), var(--color-secondary));
            border-radius: var(--radius-xl);
            z-index: -1;
            opacity: 0.5;
        }

        /* ========================================
           Widget Header Styles
           ======================================== */
        .widget-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-md);
            padding-bottom: var(--space-sm);
            border-bottom: 2px solid #333;
        }

        .widget-title {
            font-size: var(--font-size-xl);
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--color-primary);
        }

        .widget-title.speedtest { color: var(--color-speedtest); }
        .widget-title.wifi { color: var(--color-wifi); }
        .widget-title.ping { color: var(--color-ping); }
        .widget-title.health { color: var(--color-health); }

        /* ========================================
           Status Badge Styles
           ======================================== */
        .status-badge {
            font-size: var(--font-size-sm);
            padding: var(--space-xs) var(--space-sm);
            border-radius: var(--radius-full);
            font-weight: bold;
        }

        .status-badge.connected,
        .status-badge.success {
            background: var(--color-success);
            color: var(--text-on-primary);
        }

        .status-badge.disconnected,
        .status-badge.error {
            background: var(--color-error);
            color: var(--text-primary);
        }

        .status-badge.warning,
        .status-badge.testing {
            background: var(--color-warning);
            color: var(--text-on-primary);
        }

        .status-badge.network-lost {
            background: #ff0080;
            color: var(--text-primary);
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        /* ========================================
           Info Grid Layout
           ======================================== */
        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--space-sm);
        }

        .info-grid.cols-3 {
            grid-template-columns: repeat(3, 1fr);
        }

        .info-grid.cols-4 {
            grid-template-columns: repeat(4, 1fr);
        }

        .info-item {
            background: var(--bg-elevated);
            padding: var(--space-sm);
            border-radius: var(--radius-md);
            border-left: 3px solid var(--color-primary);
        }

        .info-item.speedtest { border-left-color: var(--color-speedtest); }
        .info-item.wifi { border-left-color: var(--color-wifi); }
        .info-item.ping { border-left-color: var(--color-ping); }

        .info-label {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: var(--space-xs);
        }

        .info-value {
            font-size: var(--font-size-lg);
            font-weight: bold;
            color: var(--color-primary);
        }

        .info-value.speedtest { color: var(--color-speedtest); }
        .info-value.wifi { color: var(--color-wifi); }
        .info-value.ping { color: var(--color-ping); }

        /* ========================================
           Progress Bar / Quality Bar
           ======================================== */
        .progress-bar {
            width: 100%;
            height: 25px;
            background: #333;
            border-radius: var(--radius-full);
            overflow: hidden;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
            transition: width var(--transition-slow), background var(--transition-normal);
            border-radius: var(--radius-full);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-on-primary);
            font-weight: bold;
            font-size: var(--font-size-sm);
        }

        .progress-fill.good {
            background: linear-gradient(90deg, var(--color-success), #00cc50);
        }

        .progress-fill.warning {
            background: linear-gradient(90deg, var(--color-warning), #ff8800);
        }

        .progress-fill.error {
            background: linear-gradient(90deg, #ff6400, var(--color-error));
        }

        /* ========================================
           Button Styles
           ======================================== */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            padding: var(--space-md) var(--space-lg);
            font-size: var(--font-size-lg);
            font-weight: bold;
            border: none;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all var(--transition-normal);
            text-decoration: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover));
            color: var(--text-on-primary);
        }

        .btn-primary:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 4px 16px var(--color-primary-glow);
        }

        .btn-primary:active:not(:disabled) {
            transform: scale(0.95);
        }

        .btn-primary:disabled {
            background: #333;
            cursor: not-allowed;
            transform: none;
        }

        .btn-full {
            width: 100%;
        }

        /* Widget-specific button colors */
        .btn.speedtest {
            background: linear-gradient(135deg, var(--color-speedtest), #0080ff);
        }

        .btn.speedtest:hover:not(:disabled) {
            box-shadow: 0 4px 16px rgba(0, 200, 255, 0.5);
        }

        /* ========================================
           Chart Container
           ======================================== */
        .chart-container {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-sm);
            margin-top: var(--space-md);
        }

        .chart-container canvas {
            width: 100%;
            height: 100%;
        }

        /* ========================================
           Toast Notification System
           ======================================== */
        .toast-container {
            position: fixed;
            top: var(--space-lg);
            right: var(--space-lg);
            z-index: var(--z-toast);
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
            pointer-events: none;
        }

        .toast {
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            padding: var(--space-md) var(--space-lg);
            box-shadow: var(--shadow-elevated);
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            min-width: 280px;
            max-width: 400px;
            pointer-events: auto;
            animation: slideIn 0.3s ease, fadeOut 0.3s ease 2.7s forwards;
            border-left: 4px solid var(--color-primary);
        }

        .toast-success { border-left-color: var(--color-success); }
        .toast-error { border-left-color: var(--color-error); }
        .toast-warning { border-left-color: var(--color-warning); }
        .toast-info { border-left-color: var(--color-secondary); }

        .toast-icon {
            font-size: var(--font-size-xl);
            flex-shrink: 0;
        }

        .toast-message {
            flex: 1;
            font-size: var(--font-size-sm);
        }

        .toast-close {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: var(--space-xs);
            font-size: var(--font-size-xl);
            line-height: 1;
        }

        .toast-close:hover {
            color: var(--text-primary);
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes fadeOut {
            to {
                opacity: 0;
                transform: translateX(50%);
            }
        }

        /* ========================================
           Loading States
           ======================================== */
        .skeleton {
            background: linear-gradient(
                90deg,
                var(--bg-elevated) 25%,
                #3a3a3a 50%,
                var(--bg-elevated) 75%
            );
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: var(--radius-sm);
        }

        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .spinner {
            width: 24px;
            height: 24px;
            border: 3px solid var(--bg-elevated);
            border-top-color: var(--color-primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-md);
            color: var(--color-primary);
        }

        /* ========================================
           Diagnostic / Alert Panel
           ======================================== */
        .diagnosis-panel {
            background: var(--bg-elevated);
            padding: var(--space-md);
            border-radius: var(--radius-md);
            margin-top: var(--space-sm);
            border-left: 3px solid var(--color-warning);
        }

        .diagnosis-title {
            font-size: var(--font-size-sm);
            color: var(--color-warning);
            font-weight: bold;
            margin-bottom: var(--space-xs);
        }

        .diagnosis-text {
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            line-height: 1.4;
        }

        /* ========================================
           Responsive Breakpoints
           ======================================== */
        @media (max-width: 768px) {
            :root {
                --space-lg: 20px;
                --space-xl: 32px;
            }

            .toast-container {
                left: var(--space-md);
                right: var(--space-md);
            }

            .toast {
                min-width: auto;
                max-width: none;
            }

            .info-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .info-grid.cols-3,
            .info-grid.cols-4 {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 480px) {
            :root {
                --font-size-2xl: 20px;
                --font-size-xl: 16px;
            }

            .info-grid {
                grid-template-columns: 1fr;
            }

            .widget {
                padding: var(--space-md);
            }
        }

        /* ========================================
           Visually Hidden (Screen Reader Only)
           ======================================== */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }

        /* ========================================
           Tooltip System (Touch-Friendly)
           ======================================== */
        [data-tooltip] {
            position: relative;
        }

        [data-tooltip]::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: var(--space-xs) var(--space-sm);
            border-radius: var(--radius-sm);
            font-size: var(--font-size-xs);
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity var(--transition-fast);
            border: 1px solid var(--bg-elevated);
            z-index: var(--z-dropdown);
        }

        [data-tooltip]:hover::after,
        [data-tooltip]:focus::after {
            opacity: 1;
        }

        @media (hover: none) {
            [data-tooltip]:active::after {
                opacity: 1;
            }
        }

        /* ========================================
           Print Styles
           ======================================== */
        @media print {
            body {
                background: white;
                color: black;
            }

            .widget {
                box-shadow: none;
                border: 1px solid #ccc;
            }

            .toast-container {
                display: none;
            }
        }

        /* ========================================
           Reduced Motion Accessibility
           ======================================== */
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
            .skeleton {
                animation: none;
                background: var(--bg-elevated);
            }
            .spinner {
                animation: none;
            }
            .status-badge.network-lost {
                animation: none;
            }
        }
    '''


def get_widget_api_helpers_script():
    """Return shared JavaScript helpers for API response validation,
    boolean coercion safety, and standardized error handling."""
    return _shared_api_helpers()


def get_widget_toast_script():
    """Return the toast notification JavaScript for agent widgets."""
    return _shared_toast_script()


def get_widget_confirm_dialog_html():
    """Return the HTML for a custom confirmation dialog"""
    return '''
        <!-- Accessible Confirmation Dialog -->
        <div id="confirmDialog" class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirmTitle" style="display: none;">
            <div class="confirm-overlay"></div>
            <div class="confirm-content">
                <h2 id="confirmTitle" class="confirm-title">Confirm Action</h2>
                <p id="confirmMessage" class="confirm-message"></p>
                <div class="confirm-actions">
                    <button id="confirmCancel" class="btn confirm-btn-cancel">Cancel</button>
                    <button id="confirmOk" class="btn btn-primary confirm-btn-danger">Confirm</button>
                </div>
            </div>
        </div>
    '''


def get_widget_confirm_dialog_styles():
    """Return the CSS for the confirmation dialog"""
    return '''
        /* Confirmation Dialog Styles */
        .confirm-dialog {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: var(--z-modal);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .confirm-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg-overlay);
            backdrop-filter: blur(4px);
        }

        .confirm-content {
            position: relative;
            background: var(--bg-elevated);
            border-radius: var(--radius-lg);
            padding: var(--space-xl);
            max-width: 400px;
            width: 90%;
            box-shadow: var(--shadow-widget);
            border: 1px solid #333;
        }

        .confirm-title {
            font-size: var(--font-size-xl);
            color: var(--text-primary);
            margin-bottom: var(--space-md);
        }

        .confirm-message {
            font-size: var(--font-size-md);
            color: var(--text-secondary);
            margin-bottom: var(--space-lg);
            line-height: var(--line-height);
        }

        .confirm-actions {
            display: flex;
            gap: var(--space-md);
            justify-content: flex-end;
        }

        .confirm-btn-cancel {
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border: 1px solid #333;
        }

        .confirm-btn-cancel:hover {
            background: var(--bg-primary);
            color: var(--text-primary);
        }

        .confirm-btn-danger {
            background: var(--color-error);
            color: var(--text-primary);
        }

        .confirm-btn-danger:hover {
            background: var(--color-error-hover);
        }
    '''


def get_widget_confirm_dialog_script():
    """Return the JavaScript for the confirmation dialog"""
    return '''
        // Custom Confirmation Dialog
        function showConfirm(title, message) {
            return new Promise((resolve) => {
                const dialog = document.getElementById('confirmDialog');
                const titleEl = document.getElementById('confirmTitle');
                const messageEl = document.getElementById('confirmMessage');
                const cancelBtn = document.getElementById('confirmCancel');
                const okBtn = document.getElementById('confirmOk');

                titleEl.textContent = title;
                messageEl.textContent = message;
                dialog.style.display = 'flex';

                // Focus trap
                okBtn.focus();

                const handleCancel = () => {
                    dialog.style.display = 'none';
                    resolve(false);
                    cleanup();
                };

                const handleOk = () => {
                    dialog.style.display = 'none';
                    resolve(true);
                    cleanup();
                };

                const handleKeydown = (e) => {
                    if (e.key === 'Escape') {
                        handleCancel();
                    } else if (e.key === 'Tab') {
                        // Keep focus within dialog
                        const focusables = dialog.querySelectorAll('button');
                        const first = focusables[0];
                        const last = focusables[focusables.length - 1];

                        if (e.shiftKey && document.activeElement === first) {
                            e.preventDefault();
                            last.focus();
                        } else if (!e.shiftKey && document.activeElement === last) {
                            e.preventDefault();
                            first.focus();
                        }
                    }
                };

                const cleanup = () => {
                    cancelBtn.removeEventListener('click', handleCancel);
                    okBtn.removeEventListener('click', handleOk);
                    document.removeEventListener('keydown', handleKeydown);
                };

                cancelBtn.addEventListener('click', handleCancel);
                okBtn.addEventListener('click', handleOk);
                document.addEventListener('keydown', handleKeydown);
            });
        }
    '''


def get_tab_keyboard_script():
    """Return JavaScript for accessible tab keyboard navigation (Arrow keys, Home, End)."""
    return '''
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
    '''


def get_widget_html_start(title, accent_color=None, skip_link_target='main-content'):
    """Generate the HTML start with accessibility features

    Args:
        title: Page title
        accent_color: CSS variable name for accent color (e.g., 'speedtest', 'wifi')
        skip_link_target: ID of the main content for skip link

    Returns:
        HTML string with doctype, head, and body start
    """
    accent_var = f'var(--color-{accent_color})' if accent_color else 'var(--color-primary)'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - ATLAS Agent</title>
    <style>
{get_widget_base_styles()}

        /* Widget-specific accent override */
        :root {{
            --accent-color: {accent_var};
        }}

        .widget-title {{ color: var(--accent-color); }}
        .info-item {{ border-left-color: var(--accent-color); }}
        .info-value {{ color: var(--accent-color); }}
    </style>
</head>
<body>
    <!-- Skip Link for Keyboard Navigation -->
    <a href="#{skip_link_target}" class="skip-link">Skip to main content</a>

    <!-- Toast Container for Notifications -->
    <div class="toast-container" role="alert" aria-live="polite"></div>
'''


def get_widget_html_end(include_toast_script=True, include_confirm_dialog=False,
                        include_api_helpers=True):
    """Generate the HTML end with scripts

    Args:
        include_toast_script: Include toast notification system
        include_confirm_dialog: Include confirmation dialog component
        include_api_helpers: Include API validation helpers (apiFetch, safeBool, safeGet)

    Returns:
        HTML string with scripts and closing tags
    """
    scripts = ''

    if include_api_helpers:
        scripts += f'''
    <script>
{get_widget_api_helpers_script()}
    </script>
'''

    if include_toast_script:
        scripts += f'''
    <script>
{get_widget_toast_script()}
    </script>
'''

    if include_confirm_dialog:
        scripts += f'''
    <script>
{get_widget_confirm_dialog_script()}
    </script>
'''

    return f'''{scripts}
</body>
</html>'''


def get_css_var_reader_script():
    """Return JS helper for reading CSS custom properties in canvas drawing code."""
    return '''
        function cssVar(name) {
            return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        }
    '''


# Export for easy import
__all__ = [
    'get_widget_base_styles',
    'get_widget_api_helpers_script',
    'get_widget_toast_script',
    'get_widget_confirm_dialog_html',
    'get_widget_confirm_dialog_styles',
    'get_widget_confirm_dialog_script',
    'get_tab_keyboard_script',
    'get_css_var_reader_script',
    'get_widget_html_start',
    'get_widget_html_end'
]
