"""
Theming system for Atlas
"""
from typing import Dict, Any, Tuple, List
from dataclasses import dataclass, field
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class ColorScheme:
    """Color scheme for a theme"""
    background: Tuple[int, int, int] = (0, 0, 0)
    foreground: Tuple[int, int, int] = (255, 255, 255)
    primary: Tuple[int, int, int] = (0, 150, 255)
    secondary: Tuple[int, int, int] = (100, 100, 100)
    accent: Tuple[int, int, int] = (255, 100, 0)
    success: Tuple[int, int, int] = (0, 200, 100)
    warning: Tuple[int, int, int] = (255, 200, 0)
    danger: Tuple[int, int, int] = (255, 50, 50)
    text_primary: Tuple[int, int, int] = (255, 255, 255)
    text_secondary: Tuple[int, int, int] = (180, 180, 180)


@dataclass
class ThemeLayout:
    """Layout configuration for a theme"""
    cpu_gauge: Dict[str, int] = field(default_factory=lambda: {"x": 80, "y": 100, "radius": 50})
    memory_gauge: Dict[str, int] = field(default_factory=lambda: {"x": 240, "y": 100, "radius": 50})
    network_graph: Dict[str, int] = field(default_factory=lambda: {"x": 10, "y": 200, "width": 300, "height": 100})
    disk_bar: Dict[str, int] = field(default_factory=lambda: {"x": 10, "y": 320, "width": 300, "height": 20})
    info_panel: Dict[str, int] = field(default_factory=lambda: {"x": 10, "y": 360, "width": 300, "height": 110})


@dataclass
class Theme:
    """Complete theme definition"""
    name: str
    description: str
    colors: ColorScheme = field(default_factory=ColorScheme)
    layout: ThemeLayout = field(default_factory=ThemeLayout)
    font_sizes: Dict[str, int] = field(default_factory=lambda: {
        "title": 20,
        "subtitle": 16,
        "body": 14,
        "small": 12
    })


class ThemeManager:
    """Manages themes for the application"""
    
    def __init__(self, theme_dir: str = None):
        """
        Initialize theme manager
        
        Args:
            theme_dir: Directory containing custom themes
        """
        self.theme_dir = theme_dir or self._get_default_theme_dir()
        self.themes: Dict[str, Theme] = {}
        self.current_theme: Theme = None
        
        # Load built-in themes
        self._load_builtin_themes()
        
        # Load custom themes
        self._load_custom_themes()
        
        # Set default theme
        self.set_theme("dark")
    
    @staticmethod
    def _get_default_theme_dir() -> Path:
        """Get default theme directory"""
        theme_dir = Path.home() / ".config" / "atlas" / "themes"
        theme_dir.mkdir(parents=True, exist_ok=True)
        return theme_dir
    
    def _load_builtin_themes(self):
        """Load built-in themes"""
        
        # Dark Theme (Default)
        dark_theme = Theme(
            name="dark",
            description="Modern dark theme with blue accents",
            colors=ColorScheme(
                background=(15, 15, 20),
                foreground=(255, 255, 255),
                primary=(0, 150, 255),
                secondary=(50, 50, 60),
                accent=(100, 200, 255),
                success=(0, 200, 100),
                warning=(255, 180, 0),
                danger=(255, 70, 70),
                text_primary=(255, 255, 255),
                text_secondary=(180, 180, 200)
            )
        )
        self.themes["dark"] = dark_theme
        
        # Light Theme
        light_theme = Theme(
            name="light",
            description="Clean light theme",
            colors=ColorScheme(
                background=(245, 245, 250),
                foreground=(20, 20, 30),
                primary=(0, 100, 200),
                secondary=(200, 200, 210),
                accent=(50, 150, 255),
                success=(0, 150, 70),
                warning=(200, 140, 0),
                danger=(200, 50, 50),
                text_primary=(20, 20, 30),
                text_secondary=(80, 80, 100)
            )
        )
        self.themes["light"] = light_theme
        
        # Cyberpunk Theme
        cyberpunk_theme = Theme(
            name="cyberpunk",
            description="Neon cyberpunk theme with pink and cyan",
            colors=ColorScheme(
                background=(10, 0, 20),
                foreground=(255, 0, 200),
                primary=(255, 0, 150),
                secondary=(40, 0, 60),
                accent=(0, 255, 255),
                success=(0, 255, 150),
                warning=(255, 255, 0),
                danger=(255, 0, 100),
                text_primary=(255, 255, 255),
                text_secondary=(200, 100, 255)
            )
        )
        self.themes["cyberpunk"] = cyberpunk_theme
        
        # Matrix Theme
        matrix_theme = Theme(
            name="matrix",
            description="Green matrix-style theme",
            colors=ColorScheme(
                background=(0, 0, 0),
                foreground=(0, 255, 0),
                primary=(0, 200, 0),
                secondary=(0, 50, 0),
                accent=(100, 255, 100),
                success=(0, 255, 100),
                warning=(200, 255, 0),
                danger=(255, 100, 0),
                text_primary=(0, 255, 0),
                text_secondary=(0, 150, 0)
            )
        )
        self.themes["matrix"] = matrix_theme
        
        # Nord Theme
        nord_theme = Theme(
            name="nord",
            description="Nord color palette theme",
            colors=ColorScheme(
                background=(46, 52, 64),
                foreground=(236, 239, 244),
                primary=(136, 192, 208),
                secondary=(67, 76, 94),
                accent=(143, 188, 187),
                success=(163, 190, 140),
                warning=(235, 203, 139),
                danger=(191, 97, 106),
                text_primary=(236, 239, 244),
                text_secondary=(216, 222, 233)
            )
        )
        self.themes["nord"] = nord_theme
        
        # Dracula Theme
        dracula_theme = Theme(
            name="dracula",
            description="Dracula color scheme",
            colors=ColorScheme(
                background=(40, 42, 54),
                foreground=(248, 248, 242),
                primary=(189, 147, 249),
                secondary=(68, 71, 90),
                accent=(255, 121, 198),
                success=(80, 250, 123),
                warning=(241, 250, 140),
                danger=(255, 85, 85),
                text_primary=(248, 248, 242),
                text_secondary=(98, 114, 164)
            )
        )
        self.themes["dracula"] = dracula_theme
        
        # Solarized Dark Theme
        solarized_dark_theme = Theme(
            name="solarized_dark",
            description="Solarized dark color scheme",
            colors=ColorScheme(
                background=(0, 43, 54),
                foreground=(131, 148, 150),
                primary=(38, 139, 210),
                secondary=(7, 54, 66),
                accent=(42, 161, 152),
                success=(133, 153, 0),
                warning=(181, 137, 0),
                danger=(220, 50, 47),
                text_primary=(147, 161, 161),
                text_secondary=(88, 110, 117)
            )
        )
        self.themes["solarized_dark"] = solarized_dark_theme
        
        # Monokai Theme
        monokai_theme = Theme(
            name="monokai",
            description="Monokai color scheme",
            colors=ColorScheme(
                background=(39, 40, 34),
                foreground=(248, 248, 242),
                primary=(102, 217, 239),
                secondary=(73, 72, 62),
                accent=(249, 38, 114),
                success=(166, 226, 46),
                warning=(230, 219, 116),
                danger=(249, 38, 114),
                text_primary=(248, 248, 242),
                text_secondary=(117, 113, 94)
            )
        )
        self.themes["monokai"] = monokai_theme
        
        # Minimal Theme
        minimal_theme = Theme(
            name="minimal",
            description="Minimalist black and white theme",
            colors=ColorScheme(
                background=(0, 0, 0),
                foreground=(255, 255, 255),
                primary=(200, 200, 200),
                secondary=(50, 50, 50),
                accent=(150, 150, 150),
                success=(180, 180, 180),
                warning=(220, 220, 220),
                danger=(100, 100, 100),
                text_primary=(255, 255, 255),
                text_secondary=(180, 180, 180)
            )
        )
        self.themes["minimal"] = minimal_theme
        
        # Sunset Theme
        sunset_theme = Theme(
            name="sunset",
            description="Warm sunset colors",
            colors=ColorScheme(
                background=(30, 20, 40),
                foreground=(255, 200, 150),
                primary=(255, 120, 80),
                secondary=(60, 40, 70),
                accent=(255, 180, 100),
                success=(200, 255, 150),
                warning=(255, 220, 100),
                danger=(255, 100, 100),
                text_primary=(255, 230, 200),
                text_secondary=(200, 150, 120)
            )
        )
        self.themes["sunset"] = sunset_theme
    
    def _load_custom_themes(self):
        """Load custom themes from theme directory"""
        theme_dir = Path(self.theme_dir)
        if not theme_dir.exists():
            return

        for theme_path in theme_dir.glob('*.json'):
            try:
                with open(theme_path, 'r') as f:
                    theme_data = json.load(f)

                theme = self._theme_from_dict(theme_data)
                self.themes[theme.name] = theme
                logger.info(f"Loaded custom theme: {theme.name}")
            except Exception as e:
                logger.error(f"Failed to load theme {theme_path.name}: {e}")
    
    def _theme_from_dict(self, data: Dict[str, Any]) -> Theme:
        """Create a Theme object from a dictionary"""
        colors_data = data.get('colors', {})
        colors = ColorScheme(
            background=tuple(colors_data.get('background', [0, 0, 0])),
            foreground=tuple(colors_data.get('foreground', [255, 255, 255])),
            primary=tuple(colors_data.get('primary', [0, 150, 255])),
            secondary=tuple(colors_data.get('secondary', [100, 100, 100])),
            accent=tuple(colors_data.get('accent', [255, 100, 0])),
            success=tuple(colors_data.get('success', [0, 200, 100])),
            warning=tuple(colors_data.get('warning', [255, 200, 0])),
            danger=tuple(colors_data.get('danger', [255, 50, 50])),
            text_primary=tuple(colors_data.get('text_primary', [255, 255, 255])),
            text_secondary=tuple(colors_data.get('text_secondary', [180, 180, 180]))
        )
        
        layout_data = data.get('layout', {})
        layout = ThemeLayout(
            cpu_gauge=layout_data.get('cpu_gauge', {"x": 80, "y": 100, "radius": 50}),
            memory_gauge=layout_data.get('memory_gauge', {"x": 240, "y": 100, "radius": 50}),
            network_graph=layout_data.get('network_graph', {"x": 10, "y": 200, "width": 300, "height": 100}),
            disk_bar=layout_data.get('disk_bar', {"x": 10, "y": 320, "width": 300, "height": 20}),
            info_panel=layout_data.get('info_panel', {"x": 10, "y": 360, "width": 300, "height": 110})
        )
        
        return Theme(
            name=data.get('name', 'custom'),
            description=data.get('description', 'Custom theme'),
            colors=colors,
            layout=layout,
            font_sizes=data.get('font_sizes', {
                "title": 20,
                "subtitle": 16,
                "body": 14,
                "small": 12
            })
        )
    
    def set_theme(self, theme_name: str) -> bool:
        """
        Set the current theme
        
        Args:
            theme_name: Name of the theme to set
            
        Returns:
            True if theme was set successfully
        """
        if theme_name in self.themes:
            self.current_theme = self.themes[theme_name]
            logger.info(f"Theme set to: {theme_name}")
            return True
        
        logger.warning(f"Theme not found: {theme_name}")
        return False
    
    def get_theme(self, theme_name: str = None) -> Theme:
        """
        Get a theme by name or return current theme
        
        Args:
            theme_name: Name of the theme (None for current theme)
            
        Returns:
            Theme object
        """
        if theme_name:
            return self.themes.get(theme_name, self.current_theme)
        return self.current_theme
    
    def list_themes(self) -> List[str]:
        """
        Get list of available theme names
        
        Returns:
            List of theme names
        """
        return list(self.themes.keys())
    
    def save_theme(self, theme: Theme, filename: str = None):
        """
        Save a theme to file
        
        Args:
            theme: Theme to save
            filename: Filename (defaults to theme name)
        """
        filename = filename or f"{theme.name}.json"
        filepath = Path(self.theme_dir) / filename
        
        theme_dict = {
            "name": theme.name,
            "description": theme.description,
            "colors": {
                "background": list(theme.colors.background),
                "foreground": list(theme.colors.foreground),
                "primary": list(theme.colors.primary),
                "secondary": list(theme.colors.secondary),
                "accent": list(theme.colors.accent),
                "success": list(theme.colors.success),
                "warning": list(theme.colors.warning),
                "danger": list(theme.colors.danger),
                "text_primary": list(theme.colors.text_primary),
                "text_secondary": list(theme.colors.text_secondary)
            },
            "layout": {
                "cpu_gauge": theme.layout.cpu_gauge,
                "memory_gauge": theme.layout.memory_gauge,
                "network_graph": theme.layout.network_graph,
                "disk_bar": theme.layout.disk_bar,
                "info_panel": theme.layout.info_panel
            },
            "font_sizes": theme.font_sizes
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(theme_dict, f, indent=2)
            logger.info(f"Theme saved to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save theme: {e}")
    
    def export_theme_template(self, filepath: str):
        """
        Export a theme template file
        
        Args:
            filepath: Path to save the template
        """
        template = {
            "name": "my_custom_theme",
            "description": "My custom theme description",
            "colors": {
                "background": [0, 0, 0],
                "foreground": [255, 255, 255],
                "primary": [0, 150, 255],
                "secondary": [100, 100, 100],
                "accent": [255, 100, 0],
                "success": [0, 200, 100],
                "warning": [255, 200, 0],
                "danger": [255, 50, 50],
                "text_primary": [255, 255, 255],
                "text_secondary": [180, 180, 180]
            },
            "layout": {
                "cpu_gauge": {"x": 80, "y": 100, "radius": 50},
                "memory_gauge": {"x": 240, "y": 100, "radius": 50},
                "network_graph": {"x": 10, "y": 200, "width": 300, "height": 100},
                "disk_bar": {"x": 10, "y": 320, "width": 300, "height": 20},
                "info_panel": {"x": 10, "y": 360, "width": 300, "height": 110}
            },
            "font_sizes": {
                "title": 20,
                "subtitle": 16,
                "body": 14,
                "small": 12
            }
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(template, f, indent=2)
            logger.info(f"Theme template exported to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export theme template: {e}")
