"""In-memory rate limiter for the agent dashboard API.

Uses a sliding window counter per IP address.
"""
import time
import threading
from collections import defaultdict


class RateLimiter:
    """Simple sliding-window rate limiter.

    Args:
        max_requests: Maximum requests allowed per window
        window_seconds: Time window in seconds
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)  # ip -> [timestamp, ...]
        self._lock = threading.Lock()

    def is_allowed(self, ip: str) -> bool:
        """Check if a request from this IP is allowed.

        Returns True if under the limit, False if rate limited.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Prune old timestamps
            timestamps = self._requests[ip]
            self._requests[ip] = [t for t in timestamps if t > cutoff]

            if len(self._requests[ip]) >= self.max_requests:
                return False

            self._requests[ip].append(now)
            return True

    def cleanup(self):
        """Remove stale entries from IPs that haven't made recent requests."""
        now = time.monotonic()
        cutoff = now - self.window_seconds * 2  # Keep 2x window for safety

        with self._lock:
            stale = [ip for ip, ts in self._requests.items()
                     if not ts or ts[-1] < cutoff]
            for ip in stale:
                del self._requests[ip]
