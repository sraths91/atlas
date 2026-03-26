"""Page HTML Generators — loads templates from atlas/templates/

Templates use string.Template ($variable) for substitution.
Shared CSS design tokens are injected into each page.
"""
import os
from string import Template
from atlas.dashboard_preferences import get_dashboard_preferences

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

# Cache loaded templates in memory
_cache = {}


def _load_template(name):
    """Load and cache a template file."""
    if name not in _cache:
        path = os.path.join(_TEMPLATE_DIR, name)
        with open(path, 'r', encoding='utf-8') as f:
            _cache[name] = f.read()
    return _cache[name]


def _get_design_tokens():
    """Load the shared CSS design tokens."""
    return _load_template('design_tokens.css')


def get_homepage_html():
    """Enhanced homepage showcasing all ATLAS features.

    Returns HTML homepage with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Semantic HTML structure
    - Responsive design
    """
    tmpl = Template(_load_template('homepage.html'))
    return tmpl.safe_substitute(design_tokens=_get_design_tokens())


def get_help_html():
    """Help and feature discovery page.

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
    return _load_template('help.html')


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
    """Main dashboard with all widgets.

    Returns HTML dashboard with:
    - Accessibility features (ARIA labels, focus states, skip links)
    - WCAG AA compliant color contrast
    - Responsive design
    - Custom export format dialog (replaces prompt())
    - Toast notification system (replaces alert())
    """
    tmpl = Template(_load_template('dashboard.html'))
    return tmpl.safe_substitute(
        design_tokens=_get_design_tokens(),
        widget_iframes=_generate_widget_iframes()
    )
