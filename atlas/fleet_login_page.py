"""
Fleet Dashboard Login Page
Enhanced with modern UX/UI best practices:
- Accessibility (ARIA labels, focus states, screen reader support)
- Toast notifications instead of alerts
- Responsive design with mobile breakpoints
- CSS custom properties design system
- Skeleton loading states
- Improved color contrast (WCAG AA compliant)

Toast script imported from atlas.shared_styles (shared with agent_widget_styles.py).
"""
from atlas.shared_styles import get_toast_script as _shared_toast_script


def get_base_styles():
    """Return the shared CSS design system with custom properties"""
    return '''
        /* ========================================
           CSS Custom Properties Design System (2026)
           ======================================== */
        :root {
            /* Typography */
            --font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
            --font-size-xs: 11px;
            --font-size-sm: 13px;
            --font-size-md: 15px;
            --font-size-lg: 17px;
            --font-size-xl: 21px;
            --font-size-2xl: 28px;
            --font-size-3xl: 36px;
            --line-height: 1.6;

            /* Colors - Primary Palette (Modern) */
            --bg-primary: #121212;
            --bg-secondary: #1a1a1a;
            --bg-elevated: rgba(26, 26, 26, 0.7);
            --bg-glass: rgba(26, 26, 26, 0.7);
            --bg-overlay: rgba(0, 0, 0, 0.85);

            /* Text Colors (WCAG AA+) */
            --text-primary: #E0E0E0;
            --text-secondary: #999;
            --text-muted: #666;
            --text-on-primary: #121212;

            /* Accent Colors (Softer Palette) */
            --color-primary: #00E5A0;
            --color-primary-hover: #00C890;
            --color-primary-dim: rgba(0, 229, 160, 0.15);
            --color-primary-glow: rgba(0, 229, 160, 0.2);

            --color-secondary: #00C8FF;
            --color-secondary-hover: #00A8DD;

            /* Status Colors */
            --color-success: #4ECDC4;
            --color-warning: #FFB84D;
            --color-error: #FF6B6B;
            --color-error-hover: #DD5555;
            --shadow-glow-error: 0 0 20px rgba(255, 107, 107, 0.3);

            /* Borders & Dividers */
            --border-subtle: rgba(255, 255, 255, 0.06);
            --border-medium: rgba(255, 255, 255, 0.1);
            --border-accent: rgba(0, 229, 160, 0.4);

            /* Shadows (Enhanced) */
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
            --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.3);
            --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.4);
            --shadow-glow: 0 0 20px var(--color-primary-glow);
            --shadow-elevated: var(--shadow-md);
            --shadow-focus: 0 0 0 3px var(--color-primary-glow);

            /* Spacing (Consistent Scale) */
            --space-xs: 4px;
            --space-sm: 8px;
            --space-md: 16px;
            --space-lg: 24px;
            --space-xl: 40px;

            /* Border Radius (Refined) */
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 16px;
            --radius-xl: 20px;
            --radius-full: 9999px;

            /* Transitions (Cubic Bezier) */
            --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);

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
            background: var(--bg-primary);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }

        /* Ambient Mesh Gradient Background */
        body::before {
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
        }

        @keyframes mesh-float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(30px, -30px) scale(1.1); }
            66% { transform: translate(-20px, 20px) scale(0.9); }
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
            background: var(--bg-glass);
            backdrop-filter: blur(20px) saturate(180%);
            border-radius: 12px;
            padding: var(--space-md) 20px;
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
        }

        @keyframes toastSlideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .toast-success { border-left-color: var(--color-success); }
        .toast-error { border-left-color: var(--color-error); }
        .toast-warning { border-left-color: var(--color-warning); }

        .toast-icon {
            font-size: var(--font-size-lg);
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
            font-size: var(--font-size-lg);
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
           Skeleton Loaders
           ======================================== */
        @keyframes shimmer {
            0% { background-position: -1000px 0; }
            100% { background-position: 1000px 0; }
        }

        .skeleton-loader {
            background: linear-gradient(
                90deg,
                rgba(255,255,255,0.03) 25%,
                rgba(255,255,255,0.06) 50%,
                rgba(255,255,255,0.03) 75%
            );
            background-size: 1000px 100%;
            animation: shimmer 2s infinite;
            border-radius: var(--radius-md);
        }

        .skeleton-text {
            height: 12px;
            margin: 8px 0;
        }

        .skeleton-title {
            height: 20px;
            width: 60%;
            margin-bottom: 16px;
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
        }

        @media (max-width: 480px) {
            :root {
                --font-size-2xl: 24px;
                --font-size-xl: 20px;
            }
        }

        /* ========================================
           Skeleton Loading Animation
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
        }

        /* ========================================
           Button Styles
           ======================================== */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            padding: 14px var(--space-lg);
            font-size: var(--font-size-md);
            font-weight: 600;
            border: none;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all var(--transition-normal);
            text-decoration: none;
        }

        .btn-primary {
            background: var(--color-primary);
            color: var(--text-on-primary);
        }

        .btn-primary:hover:not(:disabled) {
            background: var(--color-primary-hover);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px var(--color-primary-glow);
        }

        .btn-primary:active:not(:disabled) {
            transform: translateY(0) scale(0.98);
        }

        .btn-primary:disabled {
            background: var(--text-muted);
            cursor: not-allowed;
        }

        .btn-full {
            width: 100%;
        }

        /* ========================================
           Form Styles
           ======================================== */
        .form-group {
            margin-bottom: var(--space-lg);
        }

        .form-label {
            display: block;
            color: var(--text-secondary);
            margin-bottom: var(--space-sm);
            font-size: var(--font-size-sm);
            font-weight: 500;
        }

        .form-input {
            width: 100%;
            padding: 12px 15px;
            background: var(--bg-elevated);
            border: 1px solid var(--text-muted);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-size: var(--font-size-md);
            transition: all var(--transition-normal);
        }

        .form-input::placeholder {
            color: var(--text-muted);
        }

        .form-input:hover:not(:disabled) {
            border-color: var(--text-secondary);
        }

        .form-input:focus {
            border-color: var(--color-primary);
            box-shadow: var(--shadow-focus);
        }

        .form-input:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        /* Prevent iOS zoom on input focus */
        @media (max-width: 480px) {
            .form-input {
                font-size: 16px;
            }
        }

        /* ========================================
           Alert/Message Styles
           ======================================== */
        .alert {
            padding: 12px 15px;
            border-radius: var(--radius-md);
            font-size: var(--font-size-sm);
            display: flex;
            align-items: center;
            gap: var(--space-sm);
        }

        .alert-error {
            background: rgba(255, 68, 68, 0.15);
            border: 1px solid var(--color-error);
            color: var(--color-error);
        }

        .alert-success {
            background: rgba(34, 197, 94, 0.15);
            border: 1px solid var(--color-success);
            color: var(--color-success);
        }

        .alert-info {
            background: var(--bg-elevated);
            border-left: 4px solid var(--color-primary);
            color: var(--text-secondary);
        }

        /* ========================================
           Spinner Animation
           ======================================== */
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
    '''


def get_toast_script():
    """Return the toast notification JavaScript (delegated to shared_styles)."""
    return _shared_toast_script()


def generate_login_page(error_message=None, touchid_available=False):
    """Generate the login page HTML with modern UX/UI

    Args:
        error_message: Optional error message to display
        touchid_available: Whether TouchID is available on this system
    """

    error_html = ""
    if error_message:
        error_html = f'''
        <div class="alert alert-error" role="alert" aria-live="assertive">
            <span aria-hidden="true">&#10007;</span>
            <span>{error_message}</span>
        </div>
        '''

    # TouchID section (only shown on macOS with TouchID)
    touchid_html = ""
    if touchid_available:
        touchid_html = '''
            <div class="divider" role="separator">
                <span>or</span>
            </div>

            <button type="button" class="btn btn-touchid" id="touchidButton" onclick="authenticateWithTouchID()" aria-label="Sign in with Touch ID">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M17.81 4.47c-.08 0-.16-.02-.23-.06C15.66 3.42 14 3 12.01 3c-1.98 0-3.86.47-5.57 1.41-.24.13-.54.04-.68-.2-.13-.24-.04-.55.2-.68C7.82 2.52 9.86 2 12.01 2c2.13 0 3.99.47 6.03 1.52.25.13.34.43.21.67-.09.18-.26.28-.44.28zM3.5 9.72c-.1 0-.2-.03-.29-.09-.23-.16-.28-.47-.12-.7.99-1.4 2.25-2.5 3.75-3.27C9.98 4.04 14 4.03 17.15 5.65c1.5.77 2.76 1.86 3.75 3.25.16.22.11.54-.12.7-.23.16-.54.11-.7-.12-.9-1.26-2.04-2.25-3.39-2.94-2.87-1.47-6.54-1.47-9.4.01-1.36.7-2.5 1.7-3.4 2.96-.08.14-.23.21-.39.21zm6.25 12.07c-.13 0-.26-.05-.35-.15-.87-.87-1.34-1.43-2.01-2.64-.69-1.23-1.05-2.73-1.05-4.34 0-2.97 2.54-5.39 5.66-5.39s5.66 2.42 5.66 5.39c0 .28-.22.5-.5.5s-.5-.22-.5-.5c0-2.42-2.09-4.39-4.66-4.39-2.57 0-4.66 1.97-4.66 4.39 0 1.44.32 2.77.93 3.85.64 1.15 1.08 1.64 1.85 2.42.19.2.19.51 0 .71-.11.1-.24.15-.37.15zm7.17-1.85c-1.19 0-2.24-.3-3.1-.89-1.49-1.01-2.38-2.65-2.38-4.39 0-.28.22-.5.5-.5s.5.22.5.5c0 1.41.72 2.74 1.94 3.56.71.48 1.54.71 2.54.71.24 0 .64-.03 1.04-.1.27-.05.53.13.58.41.05.27-.13.53-.41.58-.57.11-1.07.12-1.21.12zM14.91 22c-.04 0-.09-.01-.13-.02-1.59-.44-2.63-1.03-3.72-2.1-1.4-1.39-2.17-3.24-2.17-5.22 0-1.62 1.38-2.94 3.08-2.94 1.7 0 3.08 1.32 3.08 2.94 0 1.07.93 1.94 2.08 1.94s2.08-.87 2.08-1.94c0-3.77-3.25-6.83-7.25-6.83-2.84 0-5.44 1.58-6.61 4.03-.39.81-.59 1.76-.59 2.8 0 .78.07 2.01.67 3.61.1.26-.03.55-.29.64-.26.1-.55-.04-.64-.29-.49-1.31-.73-2.61-.73-3.96 0-1.2.23-2.29.68-3.24 1.33-2.79 4.28-4.6 7.51-4.6 4.55 0 8.25 3.51 8.25 7.83 0 1.62-1.38 2.94-3.08 2.94s-3.08-1.32-3.08-2.94c0-1.07-.93-1.94-2.08-1.94s-2.08.87-2.08 1.94c0 1.71.66 3.31 1.87 4.51.95.94 1.86 1.46 3.27 1.85.27.07.42.35.35.61-.05.23-.26.38-.47.38z"/>
                </svg>
                Sign in with Touch ID
            </button>
        '''

    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Fleet Dashboard - Secure login portal for fleet monitoring">
    <meta name="theme-color" content="#0a0a0a">
    <title>Fleet Dashboard - Login</title>
    <style>
        {get_base_styles()}

        /* ========================================
           Login Page Specific Styles
           ======================================== */
        .login-page {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: var(--space-md);
        }}

        .login-container {{
            background: var(--bg-glass);
            backdrop-filter: blur(40px) saturate(180%);
            border: 1px solid var(--border-medium);
            border-radius: var(--radius-xl);
            padding: var(--space-xl);
            width: 100%;
            max-width: 480px;
            box-shadow: var(--shadow-lg),
                        inset 0 1px 0 rgba(255, 255, 255, 0.08);
            animation: fadeIn var(--transition-slow);
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .login-header {{
            text-align: center;
            margin-bottom: var(--space-lg);
        }}

        .login-title {{
            font-size: var(--font-size-2xl);
            font-weight: 700;
            margin-bottom: var(--space-sm);
            background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }}

        .login-subtitle {{
            color: var(--text-secondary);
            font-size: var(--font-size-sm);
        }}

        .login-form {{
            margin-bottom: var(--space-lg);
        }}

        .login-info {{
            margin-top: var(--space-lg);
        }}

        /* TouchID Button Styles */
        .divider {{
            display: flex;
            align-items: center;
            margin: var(--space-lg) 0;
            color: var(--text-muted);
            font-size: var(--font-size-sm);
        }}

        .divider::before,
        .divider::after {{
            content: "";
            flex: 1;
            border-bottom: 1px solid var(--border-medium);
        }}

        .divider span {{
            padding: 0 var(--space-md);
        }}

        .btn-touchid {{
            background: var(--bg-elevated);
            border: 1px solid var(--border-medium);
            color: var(--text-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            width: 100%;
            padding: 14px var(--space-lg);
            font-size: var(--font-size-md);
            font-weight: 500;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all var(--transition-normal);
        }}

        .btn-touchid:hover:not(:disabled) {{
            background: rgba(255, 255, 255, 0.08);
            border-color: var(--text-secondary);
        }}

        .btn-touchid:focus-visible {{
            outline: 2px solid var(--color-primary);
            outline-offset: 2px;
        }}

        .btn-touchid:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}

        .btn-touchid svg {{
            flex-shrink: 0;
        }}

        /* Responsive adjustments */
        @media (max-width: 480px) {{
            .login-container {{
                padding: var(--space-lg);
                border-radius: var(--radius-md);
            }}
        }}
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="login-page" role="main">
        <div class="login-container">
            <header class="login-header">
                <h1 class="login-title">Fleet Dashboard</h1>
                <p class="login-subtitle">Secure Access Portal</p>
            </header>

            {error_html}

            <form id="loginForm" class="login-form" method="POST" action="/login" aria-label="Login form">
                <div class="form-group">
                    <label for="username" class="form-label">Username</label>
                    <input
                        type="text"
                        id="username"
                        name="username"
                        class="form-input"
                        autocomplete="username"
                        placeholder="Enter your username"
                        required
                        autofocus
                        aria-required="true"
                        aria-describedby="username-hint"
                    >
                    <span id="username-hint" class="sr-only">Enter the username you registered with</span>
                </div>

                <div class="form-group">
                    <label for="password" class="form-label">Password</label>
                    <input
                        type="password"
                        id="password"
                        name="password"
                        class="form-input"
                        autocomplete="current-password"
                        placeholder="Enter your password"
                        required
                        aria-required="true"
                        aria-describedby="password-hint"
                    >
                    <span id="password-hint" class="sr-only">Enter your account password</span>
                </div>

                <button type="submit" class="btn btn-primary btn-full" id="loginButton">
                    <span id="loginButtonText">Sign In</span>
                </button>

                <div id="loadingState" class="loading-state" style="display: none;" aria-live="polite">
                    <div class="spinner" role="status">
                        <span class="sr-only">Loading</span>
                    </div>
                    <span>Authenticating...</span>
                </div>
            </form>

            {touchid_html}

            <div class="alert alert-info login-info" role="note">
                <span aria-hidden="true">&#128274;</span>
                <span>Your credentials are encrypted and transmitted securely.</span>
            </div>
        </div>
    </main>

    <script>
        {get_toast_script()}

        // Form submission handling
        document.getElementById('loginForm').addEventListener('submit', function(e) {{
            const loginButton = document.getElementById('loginButton');
            const loadingState = document.getElementById('loadingState');

            // Show loading state
            loginButton.style.display = 'none';
            loadingState.style.display = 'flex';

            // Announce to screen readers
            loadingState.setAttribute('aria-busy', 'true');
        }});

        // Focus management for error state
        document.addEventListener('DOMContentLoaded', function() {{
            const errorAlert = document.querySelector('.alert-error');
            if (errorAlert) {{
                // Focus on error for screen readers
                errorAlert.focus();
            }}
        }});

        // TouchID Authentication
        async function authenticateWithTouchID() {{
            const touchidButton = document.getElementById('touchidButton');
            const loadingState = document.getElementById('loadingState');
            const loginButton = document.getElementById('loginButton');

            // Disable buttons while authenticating
            if (touchidButton) touchidButton.disabled = true;
            if (loginButton) loginButton.style.display = 'none';
            if (loadingState) {{
                loadingState.style.display = 'flex';
                loadingState.querySelector('span:last-child').textContent = 'Authenticating with Touch ID...';
            }}

            try {{
                const response = await fetch('/login', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                    body: 'use_touchid=true'
                }});

                if (response.redirected) {{
                    window.location.href = response.url;
                }} else if (response.ok) {{
                    // Check if we got a redirect header
                    window.location.href = '/dashboard';
                }} else {{
                    // Show error
                    const text = await response.text();
                    if (text.includes('alert-error')) {{
                        // Page contains error, reload with error
                        document.body.innerHTML = text;
                    }} else {{
                        ToastManager.error('Touch ID authentication failed. Please try again.');
                        // Reset UI
                        if (touchidButton) touchidButton.disabled = false;
                        if (loginButton) loginButton.style.display = 'block';
                        if (loadingState) loadingState.style.display = 'none';
                    }}
                }}
            }} catch (err) {{
                console.error('TouchID auth error:', err);
                ToastManager.error('Touch ID authentication failed. Please try again.');
                // Reset UI
                if (touchidButton) touchidButton.disabled = false;
                if (loginButton) loginButton.style.display = 'block';
                if (loadingState) loadingState.style.display = 'none';
            }}
        }}
    </script>
</body>
</html>
    '''


def generate_password_reset_page(username):
    """Generate the forced password reset page with modern UX/UI"""

    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Update your password to meet security requirements">
    <meta name="theme-color" content="#0a0a0a">
    <title>Password Update Required - Fleet Dashboard</title>
    <style>
        {get_base_styles()}

        /* ========================================
           Password Reset Page Specific Styles
           ======================================== */
        .reset-page {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: var(--space-md);
        }}

        .reset-container {{
            background: var(--bg-secondary);
            border: 2px solid var(--color-error);
            border-radius: var(--radius-lg);
            padding: var(--space-xl);
            width: 100%;
            max-width: 500px;
            box-shadow: var(--shadow-glow-error);
        }}

        .reset-header {{
            text-align: center;
            margin-bottom: var(--space-lg);
        }}

        .reset-title {{
            color: var(--color-error);
            font-size: var(--font-size-xl);
            font-weight: 700;
            margin-bottom: var(--space-sm);
        }}

        .reset-subtitle {{
            color: var(--text-secondary);
            font-size: var(--font-size-sm);
            line-height: var(--line-height);
        }}

        .requirements-box {{
            background: var(--bg-elevated);
            border-left: 4px solid var(--color-error);
            padding: var(--space-md);
            border-radius: var(--radius-sm);
            margin-bottom: var(--space-lg);
        }}

        .requirements-title {{
            color: var(--color-error);
            font-size: var(--font-size-md);
            font-weight: 600;
            margin-bottom: var(--space-sm);
        }}

        .requirements-list {{
            color: var(--text-secondary);
            font-size: var(--font-size-sm);
            margin-left: var(--space-lg);
            line-height: 1.8;
        }}

        .requirements-list li {{
            margin-bottom: var(--space-xs);
        }}

        .password-feedback {{
            margin-top: var(--space-sm);
            font-size: var(--font-size-xs);
            min-height: 24px;
        }}

        .feedback-valid {{
            color: var(--color-success);
        }}

        .feedback-invalid {{
            color: var(--color-error);
        }}

        .feedback-item {{
            display: flex;
            align-items: center;
            gap: var(--space-xs);
            margin-bottom: 2px;
        }}

        .logout-link {{
            text-align: center;
            margin-top: var(--space-lg);
        }}

        .logout-link a {{
            color: var(--color-primary);
            text-decoration: none;
            font-size: var(--font-size-sm);
            transition: color var(--transition-fast);
        }}

        .logout-link a:hover {{
            text-decoration: underline;
        }}

        .logout-link a:focus-visible {{
            outline: 2px solid var(--color-primary);
            outline-offset: 2px;
        }}

        /* Responsive adjustments */
        @media (max-width: 480px) {{
            .reset-container {{
                padding: var(--space-lg);
                border-radius: var(--radius-md);
            }}
        }}
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <main id="main-content" class="reset-page" role="main">
        <div class="reset-container">
            <header class="reset-header">
                <h1 class="reset-title">Password Update Required</h1>
                <p class="reset-subtitle">
                    Your password does not meet current security requirements.
                    Please create a new password to continue.
                </p>
            </header>

            <div class="requirements-box" role="note" aria-label="Password requirements">
                <h2 class="requirements-title">Password Requirements:</h2>
                <ul class="requirements-list">
                    <li>Minimum 12 characters</li>
                    <li>At least one uppercase letter (A-Z)</li>
                    <li>At least one lowercase letter (a-z)</li>
                    <li>At least one number (0-9)</li>
                    <li>At least one symbol (!@#$%^&*()_+-=[]{{}}etc.)</li>
                </ul>
            </div>

            <div id="errorMessage" class="alert alert-error" style="display: none; margin-bottom: var(--space-lg);" role="alert" aria-live="assertive">
                <span aria-hidden="true">&#10007;</span>
                <span id="errorText"></span>
            </div>

            <form id="resetForm" aria-label="Password reset form">
                <input type="hidden" id="username" value="{username}">

                <div class="form-group">
                    <label for="newPassword" class="form-label">New Password</label>
                    <input
                        type="password"
                        id="newPassword"
                        class="form-input"
                        autocomplete="new-password"
                        placeholder="Create a strong password"
                        required
                        aria-required="true"
                        aria-describedby="passwordFeedback"
                    >
                    <div id="passwordFeedback" class="password-feedback" aria-live="polite"></div>
                </div>

                <div class="form-group">
                    <label for="confirmPassword" class="form-label">Confirm New Password</label>
                    <input
                        type="password"
                        id="confirmPassword"
                        class="form-input"
                        autocomplete="new-password"
                        placeholder="Re-enter your password"
                        required
                        aria-required="true"
                    >
                </div>

                <button type="submit" class="btn btn-primary btn-full" id="updateButton">
                    <span id="buttonText">Update Password & Continue</span>
                </button>

                <div id="loadingState" class="loading-state" style="display: none;" aria-live="polite">
                    <div class="spinner" role="status">
                        <span class="sr-only">Loading</span>
                    </div>
                    <span>Updating password...</span>
                </div>
            </form>

            <nav class="logout-link" aria-label="Secondary navigation">
                <a href="/logout">
                    <span aria-hidden="true">&larr;</span>
                    Sign out and return to login
                </a>
            </nav>
        </div>
    </main>

    <script>
        {get_toast_script()}

        // Password validation
        function validatePasswordComplexity(password) {{
            const requirements = [
                {{ test: password.length >= 12, message: `At least 12 characters (${{password.length}}/12)` }},
                {{ test: /[A-Z]/.test(password), message: 'At least one uppercase letter (A-Z)' }},
                {{ test: /[a-z]/.test(password), message: 'At least one lowercase letter (a-z)' }},
                {{ test: /[0-9]/.test(password), message: 'At least one number (0-9)' }},
                {{ test: /[!@#$%^&*()_+\\-=\\[\\]{{}}; :'\"\\\\|,.<>\\/?`~]/.test(password), message: 'At least one symbol' }}
            ];

            return {{
                isValid: requirements.every(r => r.test),
                requirements: requirements
            }};
        }}

        // Real-time password feedback
        document.getElementById('newPassword').addEventListener('input', function() {{
            const password = this.value;
            const feedbackEl = document.getElementById('passwordFeedback');

            if (!password) {{
                feedbackEl.innerHTML = '';
                return;
            }}

            const result = validatePasswordComplexity(password);

            if (result.isValid) {{
                feedbackEl.innerHTML = '<div class="feedback-item feedback-valid"><span>&#10003;</span> Password meets all requirements</div>';
            }} else {{
                const feedbackHtml = result.requirements
                    .filter(r => !r.test)
                    .map(r => `<div class="feedback-item feedback-invalid"><span>&#10007;</span> ${{r.message}}</div>`)
                    .join('');
                feedbackEl.innerHTML = feedbackHtml;
            }}
        }});

        // Form submission
        document.getElementById('resetForm').addEventListener('submit', async function(e) {{
            e.preventDefault();

            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const errorEl = document.getElementById('errorMessage');
            const errorText = document.getElementById('errorText');
            const updateBtn = document.getElementById('updateButton');
            const loadingState = document.getElementById('loadingState');

            // Hide previous errors
            errorEl.style.display = 'none';

            // Validate passwords match
            if (newPassword !== confirmPassword) {{
                errorText.textContent = 'Passwords do not match';
                errorEl.style.display = 'flex';
                errorEl.focus();
                return;
            }}

            // Validate complexity
            const validation = validatePasswordComplexity(newPassword);
            if (!validation.isValid) {{
                errorText.textContent = 'Password does not meet all requirements';
                errorEl.style.display = 'flex';
                errorEl.focus();
                return;
            }}

            // Show loading state
            updateBtn.style.display = 'none';
            loadingState.style.display = 'flex';

            try {{
                const response = await fetch('/reset-password', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ new_password: newPassword }})
                }});

                const data = await response.json();

                if (data.success) {{
                    ToastManager.success('Password updated successfully! Redirecting...');
                    setTimeout(() => {{
                        window.location.href = '/dashboard';
                    }}, 1500);
                }} else {{
                    errorText.textContent = data.message || 'Failed to update password';
                    errorEl.style.display = 'flex';
                    errorEl.focus();
                    updateBtn.style.display = 'block';
                    loadingState.style.display = 'none';
                }}
            }} catch (err) {{
                ToastManager.error('Network error. Please try again.');
                updateBtn.style.display = 'block';
                loadingState.style.display = 'none';
            }}
        }});
    </script>
</body>
</html>
    '''
