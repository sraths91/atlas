#!/usr/bin/env python3
"""
Web-based Live Display Viewer
Opens a browser window that auto-refreshes to show the display
"""
import time
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import logging

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Atlas - Live View</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        
        h1 {{
            color: #00ff00;
            margin-bottom: 10px;
            font-size: 24px;
        }}
        
        .status {{
            color: #888;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        
        .display-container {{
            border: 3px solid #333;
            border-radius: 10px;
            padding: 10px;
            background: #000;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }}
        
        #display {{
            display: block;
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;
            max-width: 100%;
            height: auto;
        }}
        
        .controls {{
            margin-top: 20px;
            color: #888;
            font-size: 12px;
        }}
        
        .controls button {{
            background: #333;
            color: #00ff00;
            border: 1px solid #555;
            padding: 8px 16px;
            margin: 0 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }}
        
        .controls button:hover {{
            background: #444;
            border-color: #00ff00;
        }}
        
        .fps {{
            color: #00ff00;
            font-weight: bold;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .updating {{
            animation: pulse 0.5s ease-in-out;
        }}
    </style>
</head>
<body>
    <h1>🖥️ Atlas - Live View</h1>
    <div class="status">
        <span id="status">Connecting...</span> | 
        Updates: <span class="fps" id="updates">0</span> | 
        FPS: <span class="fps" id="fps">0</span>
    </div>
    
    <div class="display-container">
        <img id="display" src="/preview?t=0" alt="Atlas Display">
    </div>
    
    <div class="controls">
        <button onclick="togglePause()">⏸️ Pause</button>
        <button onclick="location.reload()">Reload</button>
        <button onclick="toggleFullscreen()">⛶ Fullscreen</button>
        <span style="margin-left: 20px;">Refresh Rate: <span id="rate">{refresh_ms}ms</span></span>
    </div>
    
    <script>
        let updateCount = 0;
        let lastUpdate = Date.now();
        let paused = false;
        let refreshInterval = {refresh_ms};
        let intervalId;
        let imageLoadCount = 0;
        
        function updateDisplay() {{
            if (paused) {{
                return;
            }}
            
            const img = document.getElementById('display');
            const timestamp = Date.now();
            
            // Update stats first
            updateCount++;
            document.getElementById('updates').textContent = updateCount;
            document.getElementById('status').textContent = '🟢 Live';
            
            // Calculate FPS
            const now = Date.now();
            const fps = Math.round(1000 / (now - lastUpdate));
            document.getElementById('fps').textContent = fps;
            lastUpdate = now;
            
            // Fetch image with no-cache headers
            fetch('/preview?t=' + timestamp, {{
                method: 'GET',
                cache: 'no-store',
                headers: {{
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }}
            }})
            .then(response => {{
                return response.blob();
            }})
            .then(blob => {{
                // Create object URL from blob
                const oldSrc = img.src;
                const newSrc = URL.createObjectURL(blob);

                // Update image
                img.onload = function() {{
                    // Revoke old object URL to free memory
                    if (oldSrc.startsWith('blob:')) {{
                        URL.revokeObjectURL(oldSrc);
                    }}
                    imageLoadCount++;
                }};

                img.src = newSrc;
            }})
            .catch(error => {{
                console.error('Failed to fetch image:', error);
                document.getElementById('status').textContent = 'Error';
            }});
        }}
        
        function togglePause() {{
            paused = !paused;
            const btn = event.target;
            btn.textContent = paused ? '▶️ Resume' : '⏸️ Pause';
            document.getElementById('status').textContent = paused ? '⏸️ Paused' : '🟢 Live';
        }}
        
        function toggleFullscreen() {{
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen();
            }} else {{
                document.exitFullscreen();
            }}
        }}
        
        // Start auto-refresh
        intervalId = setInterval(updateDisplay, refreshInterval);

        // Initial update
        updateDisplay();

        // Keep updating even when tab is in background
        // (removed visibilitychange handler that was causing issues)
    </script>
</body>
</html>
"""

class DisplayHandler(BaseHTTPRequestHandler):
    """Custom HTTP handler for serving the display"""
    
    preview_path = "/tmp/atlas_preview.png"
    refresh_ms = 100  # Default refresh rate
    
    def log_message(self, format, *args):
        """Log requests for debugging"""
        logger.info(f"Request: {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        logger.debug(f"GET request for path: {self.path}")
        
        if self.path == '/' or self.path.startswith('/?'):
            # Serve HTML page
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            # Use class variable for refresh rate
            html = HTML_TEMPLATE.format(refresh_ms=self.refresh_ms)
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path.startswith('/preview'):
            # Serve preview image
            preview_file = Path(self.preview_path)
            logger.debug(f"Preview request, file exists: {preview_file.exists()}")
            if preview_file.exists():
                # Get file modification time for ETag
                mtime = preview_file.stat().st_mtime
                etag = f'"{mtime}"'
                
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.send_header('ETag', etag)
                self.send_header('Last-Modified', self.date_time_string(mtime))
                self.end_headers()
                
                with open(self.preview_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Preview not found")
        else:
            self.send_error(404)

def start_server(port=8765):
    """Start the web server"""
    server = HTTPServer(('localhost', port), DisplayHandler)
    logger.info(f"Starting web viewer on http://localhost:{port}")
    
    # Open browser
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{port}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down web viewer...")
        server.shutdown()

def start_web_viewer(port=8765, refresh_ms=100, open_browser=True):
    """Start web viewer in a background thread"""
    # Set the refresh rate on the handler class
    DisplayHandler.refresh_ms = refresh_ms
    
    def run_server():
        server = HTTPServer(('localhost', port), DisplayHandler)
        logger.info(f"Web viewer started at http://localhost:{port} (refresh: {refresh_ms}ms)")
        
        if open_browser:
            def open_browser_delayed():
                time.sleep(1)
                webbrowser.open(f'http://localhost:{port}')
            threading.Thread(target=open_browser_delayed, daemon=True).start()
        
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f"Web viewer error: {e}")
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Atlas - Web Viewer')
    parser.add_argument('--port', type=int, default=8765, help='Port to run web server on')
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  Atlas - Live Web Viewer                     ║
╚══════════════════════════════════════════════════════════╝

Starting web server on http://localhost:{args.port}
🖥️  Browser will open automatically
Display updates in real-time
⏸️  Use controls to pause/resume

Press Ctrl+C to stop
""")
    
    start_server(args.port)

if __name__ == "__main__":
    main()
