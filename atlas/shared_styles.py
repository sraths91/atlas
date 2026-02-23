"""
Shared Design System - Common styles and scripts for ATLAS agent and fleet UI

Deduplicates toast notifications, API helpers, animations, and accessibility
utilities that are identical between agent_widget_styles.py and fleet_login_page.py.

Both modules should import from here rather than maintaining their own copies.
"""


def get_toast_css():
    """Return CSS for the toast notification system (used by both agent and fleet)."""
    return '''
        /* Toast Notification System */
        .toast-container {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 2000;
            display: flex;
            flex-direction: column;
            gap: 8px;
            pointer-events: none;
        }

        .toast {
            background: var(--bg-elevated, #2a2a2a);
            border-radius: 8px;
            padding: 16px 24px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 280px;
            max-width: 400px;
            pointer-events: auto;
            animation: slideIn 0.3s ease, fadeOut 0.3s ease 2.7s forwards;
            border-left: 4px solid var(--color-primary, #00E5A0);
        }

        .toast-success { border-left-color: var(--color-success, #22c55e); }
        .toast-error { border-left-color: var(--color-error, #ff4444); }
        .toast-warning { border-left-color: var(--color-warning, #ffd93d); }
        .toast-info { border-left-color: var(--color-secondary, #00c8ff); }

        .toast-icon {
            font-size: 18px;
            flex-shrink: 0;
        }

        .toast-message {
            flex: 1;
            font-size: 12px;
        }

        .toast-close {
            background: none;
            border: none;
            color: var(--text-muted, #888);
            cursor: pointer;
            padding: 4px;
            font-size: 18px;
            line-height: 1;
        }

        .toast-close:hover {
            color: var(--text-primary, #fff);
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

        @media (max-width: 768px) {
            .toast-container {
                left: 16px;
                right: 16px;
            }
            .toast {
                min-width: auto;
                max-width: none;
            }
        }
    '''


def get_toast_script():
    """Return the toast notification JavaScript (shared by agent and fleet)."""
    return '''
        const ToastManager = {
            container: null,

            init() {
                if (!this.container) {
                    this.container = document.createElement('div');
                    this.container.className = 'toast-container';
                    this.container.setAttribute('role', 'alert');
                    this.container.setAttribute('aria-live', 'polite');
                    document.body.appendChild(this.container);
                }
            },

            show(message, type = 'success', duration = 3000) {
                this.init();

                const icons = {
                    success: '&#10003;',
                    error: '&#10007;',
                    warning: '&#9888;',
                    info: '&#8505;'
                };

                const toast = document.createElement('div');
                toast.className = `toast toast-${type}`;
                toast.innerHTML = `
                    <span class="toast-icon">${icons[type] || icons.info}</span>
                    <span class="toast-message">${message}</span>
                    <button class="toast-close" aria-label="Close notification">&times;</button>
                `;

                const closeBtn = toast.querySelector('.toast-close');
                closeBtn.addEventListener('click', () => this.dismiss(toast));

                this.container.appendChild(toast);

                setTimeout(() => this.dismiss(toast), duration);

                return toast;
            },

            dismiss(toast) {
                if (toast && toast.parentNode) {
                    toast.style.animation = 'fadeOut 0.3s ease forwards';
                    setTimeout(() => toast.remove(), 300);
                }
            },

            success(message) { return this.show(message, 'success'); },
            error(message) { return this.show(message, 'error', 5000); },
            warning(message) { return this.show(message, 'warning', 4000); },
            info(message) { return this.show(message, 'info'); }
        };
    '''


def get_api_helpers_script():
    """Return shared API helper JavaScript (apiFetch, safeBool, safeGet, constants)."""
    return '''
        async function apiFetch(url, options) {
            try {
                const response = await fetch(url, options);

                if (!response.ok) {
                    return {
                        ok: false,
                        error: `HTTP ${response.status}: ${response.statusText}`
                    };
                }

                const data = await response.json();

                if (data && data.error) {
                    return { ok: false, error: data.error, data: data };
                }

                return { ok: true, data: data };
            } catch (e) {
                return {
                    ok: false,
                    error: e.message || 'Network request failed'
                };
            }
        }

        function safeBool(value) {
            if (typeof value === 'boolean') return value;
            if (typeof value === 'number') return value !== 0;
            if (typeof value === 'string') {
                const lower = value.toLowerCase().trim();
                return lower === 'true' || lower === '1' || lower === 'yes' || lower === 'on';
            }
            return false;
        }

        function safeGet(obj, path, defaultValue) {
            if (defaultValue === undefined) defaultValue = null;
            if (!obj) return defaultValue;
            const keys = path.split('.');
            let result = obj;
            for (let i = 0; i < keys.length; i++) {
                if (result == null || typeof result !== 'object') return defaultValue;
                result = result[keys[i]];
            }
            return (result === undefined || result === null) ? defaultValue : result;
        }

        const UPDATE_INTERVAL = Object.freeze({
            REALTIME: 2000,
            FREQUENT: 5000,
            STANDARD: 10000,
            RELAXED:  30000,
            RARE:     60000
        });

        const THRESHOLDS = Object.freeze({
            QUALITY: { EXCELLENT: 95, GOOD: 80, FAIR: 60 },
            LATENCY: { EXCELLENT: 50, GOOD: 150, FAIR: 300 },
            TREND_MAX: { DNS: 100, TLS: 200, HTTP: 500 }
        });
    '''


def get_accessibility_css():
    """Return shared accessibility CSS (skip link, sr-only, focus states)."""
    return '''
        .skip-link {
            position: absolute;
            top: -100%;
            left: 50%;
            transform: translateX(-50%);
            background: var(--color-primary, #00E5A0);
            color: var(--text-on-primary, #000);
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 600;
            z-index: 1000;
            transition: top 0.15s ease;
            text-decoration: none;
        }

        .skip-link:focus {
            top: 16px;
            outline: none;
        }

        :focus {
            outline: none;
        }

        :focus-visible {
            outline: 2px solid var(--color-primary, #00E5A0);
            outline-offset: 2px;
        }

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
    '''


def get_loading_css():
    """Return shared loading state CSS (skeleton, spinner)."""
    return '''
        .skeleton {
            background: linear-gradient(
                90deg,
                var(--bg-elevated, #2a2a2a) 25%,
                #3a3a3a 50%,
                var(--bg-elevated, #2a2a2a) 75%
            );
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 4px;
        }

        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .spinner {
            width: 24px;
            height: 24px;
            border: 3px solid var(--bg-elevated, #2a2a2a);
            border-top-color: var(--color-primary, #00E5A0);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        @media (prefers-reduced-motion: reduce) {
            .skeleton, .spinner {
                animation: none;
            }
        }
    '''


__all__ = [
    'get_toast_css',
    'get_toast_script',
    'get_api_helpers_script',
    'get_accessibility_css',
    'get_loading_css',
]
