"""
Security Headers Middleware
Adds security headers to HTTP responses
"""
import logging
import secrets
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def generate_csp_nonce() -> str:
    """Generate a cryptographically random nonce for Content-Security-Policy."""
    return secrets.token_urlsafe(16)


class SecurityHeaders:
    """Add security headers to HTTP responses"""
    
    def __init__(self, use_ssl: bool = True, allowed_origins: Optional[list] = None):
        """
        Initialize security headers
        
        Args:
            use_ssl: Whether SSL/TLS is enabled
            allowed_origins: List of allowed CORS origins (None = no CORS)
        """
        self.use_ssl = use_ssl
        self.allowed_origins = allowed_origins or []
    
    def get_security_headers(self, request_origin: Optional[str] = None,
                             nonce: Optional[str] = None) -> Dict[str, str]:
        """
        Get security headers to add to response

        Args:
            request_origin: Origin header from request (for CORS)
            nonce: CSP nonce for inline scripts/styles. If provided, replaces
                   'unsafe-inline' with the nonce directive.

        Returns:
            Dictionary of headers to add
        """
        # Use nonce-based CSP when a nonce is provided, otherwise fall back to unsafe-inline
        if nonce:
            script_src = f"'self' 'nonce-{nonce}'"
            style_src = f"'self' 'nonce-{nonce}'"
        else:
            script_src = "'self' 'unsafe-inline'"
            style_src = "'self' 'unsafe-inline'"

        headers = {
            # Prevent clickjacking
            'X-Frame-Options': 'DENY',

            # Prevent MIME sniffing
            'X-Content-Type-Options': 'nosniff',

            # XSS Protection (legacy browsers)
            'X-XSS-Protection': '1; mode=block',

            # Referrer policy
            'Referrer-Policy': 'no-referrer-when-downgrade',

            # Content Security Policy
            'Content-Security-Policy': (
                "default-src 'self'; "
                f"script-src {script_src}; "
                f"style-src {style_src}; "
                "img-src 'self' data:; "                # Allow data URLs for images
                "font-src 'self'; "
                "connect-src 'self' wss: ws:; "         # Allow WebSocket connections
                "frame-ancestors 'none'; "              # Prevent framing (clickjacking)
                "base-uri 'self'; "                     # Prevent base tag hijacking
                "form-action 'self'"                    # Restrict form submissions
            ),
        }
        
        # Add HSTS if SSL is enabled
        if self.use_ssl:
            # Enforce HTTPS for 1 year
            headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Add CORS headers if configured
        if request_origin and self.allowed_origins:
            if request_origin in self.allowed_origins or '*' in self.allowed_origins:
                headers['Access-Control-Allow-Origin'] = request_origin
                headers['Access-Control-Allow-Credentials'] = 'true'
            else:
                logger.warning(f"Blocked CORS request from unauthorized origin: {request_origin}")
        
        return headers
    
    def get_cors_preflight_headers(self, request_origin: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for CORS preflight (OPTIONS) requests
        
        Args:
            request_origin: Origin header from request
            
        Returns:
            Dictionary of headers to add
        """
        headers = {}
        
        if request_origin and self.allowed_origins:
            if request_origin in self.allowed_origins or '*' in self.allowed_origins:
                headers['Access-Control-Allow-Origin'] = request_origin
                headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
                headers['Access-Control-Allow-Credentials'] = 'true'
                headers['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return headers
    
    def get_secure_cookie_flags(self) -> str:
        """
        Get security flags for Set-Cookie header
        
        Returns:
            String with cookie security flags
        """
        flags = ['HttpOnly', 'SameSite=Strict']
        
        # Add Secure flag if using SSL
        if self.use_ssl:
            flags.append('Secure')
        
        return '; '.join(flags)


class RateLimiter:
    """Simple rate limiter for API endpoints with automatic memory management"""

    # Maximum number of unique IPs to track before forced cleanup
    MAX_TRACKED_IPS = 10000

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, count), ...]}
        self._last_cleanup = 0.0  # monotonic timestamp of last full cleanup
        self._cleanup_interval = max(window_seconds * 2, 120)  # cleanup every 2 windows or 2 min

    def is_allowed(self, ip: str) -> bool:
        """
        Check if request from IP is allowed

        Args:
            ip: Client IP address

        Returns:
            True if request is allowed, False if rate limited
        """
        import time

        now = time.time()
        window_start = now - self.window_seconds

        # Periodic full cleanup to prevent unbounded memory growth
        if now - self._last_cleanup > self._cleanup_interval:
            self.cleanup()
            self._last_cleanup = now

        # Emergency cleanup if too many IPs tracked
        if len(self.requests) > self.MAX_TRACKED_IPS:
            self.cleanup()
            self._last_cleanup = now

        # Clean old entries for this IP
        if ip in self.requests:
            self.requests[ip] = [(ts, count) for ts, count in self.requests[ip]
                                if ts > window_start]
            if not self.requests[ip]:
                del self.requests[ip]

        # Count requests in current window
        current_count = sum(count for ts, count in self.requests.get(ip, []))

        if current_count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {ip} ({current_count} requests)")
            return False

        # Record this request
        if ip not in self.requests:
            self.requests[ip] = []
        self.requests[ip].append((now, 1))

        return True

    def cleanup(self):
        """Clean up old rate limit data"""
        import time

        now = time.time()
        window_start = now - self.window_seconds

        # Remove old entries and empty IPs
        for ip in list(self.requests.keys()):
            self.requests[ip] = [(ts, count) for ts, count in self.requests[ip]
                                if ts > window_start]
            if not self.requests[ip]:
                del self.requests[ip]


# Example usage
if __name__ == '__main__':
    # Initialize with SSL enabled, restrict CORS
    security = SecurityHeaders(
        use_ssl=True,
        allowed_origins=['https://192.168.50.191:8778', 'https://localhost:8778']
    )
    
    # Get security headers
    headers = security.get_security_headers()
    print("Security Headers:")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    
    # Get secure cookie flags
    cookie_flags = security.get_secure_cookie_flags()
    print(f"\nCookie Flags: {cookie_flags}")
    
    # Rate limiter
    limiter = RateLimiter(max_requests=100, window_seconds=60)
    print(f"\nRate Limiter: {limiter.max_requests} requests per {limiter.window_seconds}s")
