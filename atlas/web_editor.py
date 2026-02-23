"""
Web-based Theme Editor for Atlas
Provides a browser-based interface for creating and editing themes
"""
import json
import logging
from pathlib import Path
from typing import Optional
from flask import Flask, render_template_string, request, jsonify, send_file
from .themes import ThemeManager
from .config import ConfigManager

logger = logging.getLogger(__name__)

# HTML template for the theme editor
EDITOR_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas - Theme Editor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            padding: 30px;
        }
        
        .section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        
        .section h2 {
            margin-bottom: 20px;
            color: #667eea;
            font-size: 1.5em;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group input[type="text"],
        .form-group input[type="number"],
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .color-input {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .color-input input[type="color"] {
            width: 60px;
            height: 40px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        
        .color-input input[type="text"] {
            flex: 1;
        }
        
        .preview {
            background: #000;
            border-radius: 10px;
            padding: 20px;
            min-height: 400px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
        }
        
        .preview-title {
            font-size: 24px;
            margin-bottom: 20px;
        }
        
        .preview-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            width: 100%;
            max-width: 300px;
        }
        
        .stat-box {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 12px;
            opacity: 0.7;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .btn {
            flex: 1;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background: #218838;
        }
        
        .theme-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .theme-card {
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        
        .theme-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }
        
        .theme-card.active {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: #28a745;
            color: white;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            display: none;
            animation: slideIn 0.3s;
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
        
        .notification.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="notification" id="notification"></div>
    
    <div class="container">
        <div class="header">
            <h1>Theme Editor</h1>
            <p>Create and customize themes for your Atlas</p>
        </div>
        
        <div class="content">
            <div class="left-panel">
                <div class="section">
                    <h2>Load Theme</h2>
                    <div class="theme-list" id="themeList"></div>
                </div>
                
                <div class="section">
                    <h2>Theme Info</h2>
                    <div class="form-group">
                        <label>Theme Name</label>
                        <input type="text" id="themeName" placeholder="my-awesome-theme">
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="themeDescription" rows="2" placeholder="A beautiful theme..."></textarea>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Colors</h2>
                    <div class="form-group">
                        <label>Background</label>
                        <div class="color-input">
                            <input type="color" id="colorBackground" value="#000000">
                            <input type="text" id="colorBackgroundHex" value="#000000">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Primary</label>
                        <div class="color-input">
                            <input type="color" id="colorPrimary" value="#0078ff">
                            <input type="text" id="colorPrimaryHex" value="#0078ff">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Secondary</label>
                        <div class="color-input">
                            <input type="color" id="colorSecondary" value="#1a1a1a">
                            <input type="text" id="colorSecondaryHex" value="#1a1a1a">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Accent</label>
                        <div class="color-input">
                            <input type="color" id="colorAccent" value="#00d4ff">
                            <input type="text" id="colorAccentHex" value="#00d4ff">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Text Primary</label>
                        <div class="color-input">
                            <input type="color" id="colorTextPrimary" value="#ffffff">
                            <input type="text" id="colorTextPrimaryHex" value="#ffffff">
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="right-panel">
                <div class="section">
                    <h2>Preview</h2>
                    <div class="preview" id="preview">
                        <div class="preview-title" id="previewTitle">Atlas</div>
                        <div class="preview-stats">
                            <div class="stat-box" id="statCpu">
                                <div class="stat-label">CPU</div>
                                <div class="stat-value">45%</div>
                            </div>
                            <div class="stat-box" id="statRam">
                                <div class="stat-label">RAM</div>
                                <div class="stat-value">62%</div>
                            </div>
                            <div class="stat-box" id="statDisk">
                                <div class="stat-label">DISK</div>
                                <div class="stat-value">78%</div>
                            </div>
                            <div class="stat-box" id="statNet">
                                <div class="stat-label">NET</div>
                                <div class="stat-value">12MB/s</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Actions</h2>
                    <div class="button-group">
                        <button class="btn btn-primary" onclick="saveTheme()">Save Theme</button>
                        <button class="btn btn-success" onclick="applyTheme()">✓ Apply</button>
                    </div>
                    <div class="button-group">
                        <button class="btn btn-secondary" onclick="exportTheme()">Export JSON</button>
                        <button class="btn btn-secondary" onclick="resetTheme()">Reset</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Load available themes
        async function loadThemes() {
            const response = await fetch('/api/themes');
            const themes = await response.json();
            const themeList = document.getElementById('themeList');
            themeList.innerHTML = '';
            
            themes.forEach(theme => {
                const card = document.createElement('div');
                card.className = 'theme-card';
                card.textContent = theme;
                card.onclick = () => loadTheme(theme);
                themeList.appendChild(card);
            });
        }
        
        // Load a specific theme
        async function loadTheme(name) {
            const response = await fetch(`/api/theme/${name}`);
            const theme = await response.json();
            
            document.getElementById('themeName').value = name;
            document.getElementById('themeDescription').value = theme.description || '';
            
            // Load colors
            setColor('Background', theme.colors.background);
            setColor('Primary', theme.colors.primary);
            setColor('Secondary', theme.colors.secondary);
            setColor('Accent', theme.colors.accent);
            setColor('TextPrimary', theme.colors.text_primary);
            
            updatePreview();
            showNotification(`Loaded theme: ${name}`);
        }
        
        // Set color inputs
        function setColor(name, value) {
            const colorInput = document.getElementById(`color${name}`);
            const hexInput = document.getElementById(`color${name}Hex`);
            
            if (Array.isArray(value)) {
                const hex = rgbToHex(value[0], value[1], value[2]);
                colorInput.value = hex;
                hexInput.value = hex;
            } else {
                colorInput.value = value;
                hexInput.value = value;
            }
        }
        
        // RGB to Hex conversion
        function rgbToHex(r, g, b) {
            return "#" + [r, g, b].map(x => {
                const hex = x.toString(16);
                return hex.length === 1 ? "0" + hex : hex;
            }).join('');
        }
        
        // Update preview
        function updatePreview() {
            const preview = document.getElementById('preview');
            const bg = document.getElementById('colorBackground').value;
            const primary = document.getElementById('colorPrimary').value;
            const secondary = document.getElementById('colorSecondary').value;
            const accent = document.getElementById('colorAccent').value;
            const textPrimary = document.getElementById('colorTextPrimary').value;
            
            preview.style.background = bg;
            document.getElementById('previewTitle').style.color = primary;
            
            document.querySelectorAll('.stat-box').forEach((box, i) => {
                box.style.background = secondary;
                box.style.color = textPrimary;
                if (i % 2 === 0) {
                    box.querySelector('.stat-value').style.color = primary;
                } else {
                    box.querySelector('.stat-value').style.color = accent;
                }
            });
        }
        
        // Save theme
        async function saveTheme() {
            const name = document.getElementById('themeName').value;
            if (!name) {
                alert('Please enter a theme name');
                return;
            }
            
            const theme = {
                name: name,
                description: document.getElementById('themeDescription').value,
                colors: {
                    background: document.getElementById('colorBackgroundHex').value,
                    primary: document.getElementById('colorPrimaryHex').value,
                    secondary: document.getElementById('colorSecondaryHex').value,
                    accent: document.getElementById('colorAccentHex').value,
                    text_primary: document.getElementById('colorTextPrimaryHex').value
                }
            };
            
            const response = await fetch('/api/theme/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(theme)
            });
            
            if (response.ok) {
                showNotification('Theme saved successfully!');
                loadThemes();
            } else {
                alert('Failed to save theme');
            }
        }
        
        // Apply theme
        async function applyTheme() {
            const name = document.getElementById('themeName').value;
            const response = await fetch(`/api/theme/apply/${name}`, {method: 'POST'});
            
            if (response.ok) {
                showNotification('Theme applied!');
            } else {
                alert('Failed to apply theme');
            }
        }
        
        // Export theme
        function exportTheme() {
            const theme = {
                name: document.getElementById('themeName').value,
                description: document.getElementById('themeDescription').value,
                colors: {
                    background: document.getElementById('colorBackgroundHex').value,
                    primary: document.getElementById('colorPrimaryHex').value,
                    secondary: document.getElementById('colorSecondaryHex').value,
                    accent: document.getElementById('colorAccentHex').value,
                    text_primary: document.getElementById('colorTextPrimaryHex').value
                }
            };
            
            const dataStr = JSON.stringify(theme, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            
            const exportFileDefaultName = `${theme.name}.json`;
            
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
        }
        
        // Reset theme
        function resetTheme() {
            if (confirm('Reset to default values?')) {
                loadTheme('dark');
            }
        }
        
        // Show notification
        function showNotification(message) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.classList.add('show');
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
        
        // Sync color inputs
        document.querySelectorAll('input[type="color"]').forEach(input => {
            input.addEventListener('input', (e) => {
                const id = e.target.id;
                const hexInput = document.getElementById(id + 'Hex');
                hexInput.value = e.target.value;
                updatePreview();
            });
        });
        
        document.querySelectorAll('input[id$="Hex"]').forEach(input => {
            input.addEventListener('input', (e) => {
                const id = e.target.id.replace('Hex', '');
                const colorInput = document.getElementById(id);
                if (/^#[0-9A-F]{6}$/i.test(e.target.value)) {
                    colorInput.value = e.target.value;
                    updatePreview();
                }
            });
        });
        
        // Initialize
        loadThemes();
        updatePreview();
    </script>
</body>
</html>
"""


class ThemeEditorServer:
    """Web server for theme editor"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.theme_manager = ThemeManager()
        self.config_manager = ConfigManager()
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template_string(EDITOR_HTML)
        
        @self.app.route('/api/themes')
        def get_themes():
            themes = self.theme_manager.list_themes()
            return jsonify(themes)
        
        @self.app.route('/api/theme/<name>')
        def get_theme(name):
            theme = self.theme_manager.get_theme(name)
            if theme:
                return jsonify({
                    'name': name,
                    'description': theme.description,
                    'colors': {
                        'background': theme.colors.background,
                        'primary': theme.colors.primary,
                        'secondary': theme.colors.secondary,
                        'accent': theme.colors.accent,
                        'text_primary': theme.colors.text_primary
                    }
                })
            return jsonify({'error': 'Theme not found'}), 404
        
        @self.app.route('/api/theme/save', methods=['POST'])
        def save_theme():
            data = request.json
            try:
                # Save theme to custom themes directory
                themes_dir = Path.home() / '.config' / 'atlas' / 'themes'
                themes_dir.mkdir(parents=True, exist_ok=True)

                theme_path = themes_dir / f"{data['name']}.json"
                with open(theme_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Theme saved: {data['name']}")
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Failed to save theme: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/theme/apply/<name>', methods=['POST'])
        def apply_theme(name):
            try:
                self.config_manager.set('display.theme', name)
                self.config_manager.save()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def run(self):
        """Start the web server"""
        logger.info(f"Starting theme editor at http://{self.host}:{self.port}")
        print(f"\nTheme Editor running at: http://{self.host}:{self.port}")
        print("Press Ctrl+C to stop\n")
        self.app.run(host=self.host, port=self.port, debug=False)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Atlas Theme Editor')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    
    args = parser.parse_args()
    
    server = ThemeEditorServer(host=args.host, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
