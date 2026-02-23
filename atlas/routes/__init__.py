"""
Agent HTTP route modules.

Splits the LiveWidgetHandler routing into domain-specific modules.
Each module exports dispatch_get(handler, path) and/or
dispatch_post(handler, path) functions that return True when handled.
"""
