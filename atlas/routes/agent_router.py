"""
Agent Router — thin adapter around FleetRouter for agent HTTP routes.

Provides the dispatch_get / dispatch_post interface expected by
live_widgets.py while delegating all matching and dispatch to FleetRouter.

Usage:
    from atlas.routes.agent_router import agent_router

    @agent_router.route('GET', '/api/health')
    def handle_health(handler):
        handler.serve_json(get_system_health())

    agent_router.get('/api/ping', handle_ping)

    # In LiveWidgetHandler.do_GET / do_POST:
    if agent_router.dispatch_get(handler, path):
        return
"""

from atlas.fleet.server.router import FleetRouter


class AgentRouter:
    """Wraps FleetRouter with the dispatch_get/dispatch_post contract.

    LiveWidgetHandler calls dispatch_get(handler, path) and
    dispatch_post(handler, path). Each returns True if a registered
    route matched, False otherwise — allowing the caller to fall
    through to other handlers.
    """

    def __init__(self) -> None:
        self._router = FleetRouter()

    # -- decorator registration ------------------------------------------------

    def route(self, method: str, path: str):
        """Decorator to register a handler for *method* and *path*.

        Args:
            method: HTTP method (GET, POST, etc.)
            path:   URL pattern — supports ``{param}`` placeholders.

        Returns:
            A decorator that registers the wrapped function and returns
            it unchanged.
        """
        def decorator(fn):
            self._router.register(method, path, fn)
            return fn
        return decorator

    # -- convenience helpers ---------------------------------------------------

    def get(self, path: str, handler) -> None:
        """Register a GET route."""
        self._router.register('GET', path, handler)

    def post(self, path: str, handler) -> None:
        """Register a POST route."""
        self._router.register('POST', path, handler)

    # -- dispatch (backward-compatible with live_widgets.py) -------------------

    def dispatch_get(self, handler, path: str) -> bool:
        """Dispatch a GET request. Returns True if handled."""
        return self._router.dispatch(handler, 'GET', path)

    def dispatch_post(self, handler, path: str) -> bool:
        """Dispatch a POST request. Returns True if handled."""
        return self._router.dispatch(handler, 'POST', path)


# Module-level singleton — import this from route modules.
agent_router = AgentRouter()
