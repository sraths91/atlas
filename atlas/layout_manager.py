"""Layout manager for custom widget layouts and multi-display support."""
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

class WidgetType(Enum):
    """Types of widgets available."""
    CPU_GAUGE = "cpu_gauge"
    GPU_GAUGE = "gpu_gauge"
    MEMORY_GAUGE = "memory_gauge"
    BATTERY_BAR = "battery_bar"
    NETWORK_GRAPH = "network_graph"
    TEMPERATURE = "temperature"
    CLOCK = "clock"
    SYSTEM_INFO = "system_info"
    PROCESS_LIST = "process_list"
    DISK_USAGE = "disk_usage"

@dataclass
class Widget:
    """Widget configuration."""
    widget_type: WidgetType
    x: int
    y: int
    width: int
    height: int
    config: Dict[str, Any] = None
    visible: bool = True
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.widget_type.value,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'config': self.config,
            'visible': self.visible
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Widget':
        """Create from dictionary."""
        return cls(
            widget_type=WidgetType(data['type']),
            x=data['x'],
            y=data['y'],
            width=data['width'],
            height=data['height'],
            config=data.get('config', {}),
            visible=data.get('visible', True)
        )

@dataclass
class Layout:
    """Display layout configuration."""
    name: str
    width: int = 320
    height: int = 480
    widgets: List[Widget] = None
    theme: str = "cyberpunk"
    background_color: Tuple[int, int, int] = (0, 0, 0)
    
    def __post_init__(self):
        if self.widgets is None:
            self.widgets = []
    
    def add_widget(self, widget: Widget):
        """Add a widget to the layout."""
        self.widgets.append(widget)
    
    def remove_widget(self, index: int) -> bool:
        """Remove a widget by index."""
        if 0 <= index < len(self.widgets):
            self.widgets.pop(index)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'width': self.width,
            'height': self.height,
            'widgets': [w.to_dict() for w in self.widgets],
            'theme': self.theme,
            'background_color': list(self.background_color)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Layout':
        """Create from dictionary."""
        layout = cls(
            name=data['name'],
            width=data.get('width', 320),
            height=data.get('height', 480),
            theme=data.get('theme', 'cyberpunk'),
            background_color=tuple(data.get('background_color', [0, 0, 0]))
        )
        layout.widgets = [Widget.from_dict(w) for w in data.get('widgets', [])]
        return layout

class LayoutManager:
    """Manages display layouts and presets."""
    
    def __init__(self):
        self.layouts: Dict[str, Layout] = {}
        self.current_layout: Optional[str] = None
        self.config_dir = Path.home() / '.atlas' / 'layouts'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_default_layouts()
        self._load_saved_layouts()
    
    def _load_default_layouts(self):
        """Load default layout presets."""
        # Default layout - balanced view
        default = Layout(name="default", width=320, height=480)
        default.add_widget(Widget(WidgetType.CPU_GAUGE, 30, 60, 120, 120))
        default.add_widget(Widget(WidgetType.MEMORY_GAUGE, 170, 60, 120, 120))
        default.add_widget(Widget(WidgetType.NETWORK_GRAPH, 10, 200, 300, 100))
        default.add_widget(Widget(WidgetType.BATTERY_BAR, 10, 320, 300, 30))
        default.add_widget(Widget(WidgetType.SYSTEM_INFO, 10, 360, 300, 110))
        self.layouts['default'] = default
        
        # Minimal layout - just essentials
        minimal = Layout(name="minimal", width=320, height=480)
        minimal.add_widget(Widget(WidgetType.CPU_GAUGE, 40, 80, 100, 100))
        minimal.add_widget(Widget(WidgetType.MEMORY_GAUGE, 180, 80, 100, 100))
        minimal.add_widget(Widget(WidgetType.CLOCK, 60, 220, 200, 60, {'format': '24h'}))
        minimal.add_widget(Widget(WidgetType.BATTERY_BAR, 40, 320, 240, 40))
        self.layouts['minimal'] = minimal
        
        # Performance layout - focus on metrics
        performance = Layout(name="performance", width=320, height=480)
        performance.add_widget(Widget(WidgetType.CPU_GAUGE, 20, 40, 90, 90))
        performance.add_widget(Widget(WidgetType.GPU_GAUGE, 115, 40, 90, 90))
        performance.add_widget(Widget(WidgetType.MEMORY_GAUGE, 210, 40, 90, 90))
        performance.add_widget(Widget(WidgetType.TEMPERATURE, 20, 140, 280, 40))
        performance.add_widget(Widget(WidgetType.NETWORK_GRAPH, 20, 190, 280, 100))
        performance.add_widget(Widget(WidgetType.PROCESS_LIST, 20, 300, 280, 160))
        self.layouts['performance'] = performance
        
        # Gaming layout - GPU focused
        gaming = Layout(name="gaming", width=320, height=480)
        gaming.add_widget(Widget(WidgetType.GPU_GAUGE, 100, 50, 120, 120))
        gaming.add_widget(Widget(WidgetType.CPU_GAUGE, 30, 190, 80, 80))
        gaming.add_widget(Widget(WidgetType.MEMORY_GAUGE, 210, 190, 80, 80))
        gaming.add_widget(Widget(WidgetType.TEMPERATURE, 30, 290, 260, 50))
        gaming.add_widget(Widget(WidgetType.NETWORK_GRAPH, 30, 350, 260, 110))
        self.layouts['gaming'] = gaming
        
        # Monitoring layout - detailed stats
        monitoring = Layout(name="monitoring", width=320, height=480)
        monitoring.add_widget(Widget(WidgetType.SYSTEM_INFO, 10, 10, 300, 100))
        monitoring.add_widget(Widget(WidgetType.CPU_GAUGE, 20, 120, 70, 70))
        monitoring.add_widget(Widget(WidgetType.GPU_GAUGE, 100, 120, 70, 70))
        monitoring.add_widget(Widget(WidgetType.MEMORY_GAUGE, 180, 120, 70, 70))
        monitoring.add_widget(Widget(WidgetType.DISK_USAGE, 260, 120, 50, 70))
        monitoring.add_widget(Widget(WidgetType.NETWORK_GRAPH, 10, 200, 300, 90))
        monitoring.add_widget(Widget(WidgetType.PROCESS_LIST, 10, 300, 300, 170))
        self.layouts['monitoring'] = monitoring
    
    def _load_saved_layouts(self):
        """Load user-saved layouts from disk."""
        try:
            for layout_file in self.config_dir.glob('*.json'):
                with open(layout_file, 'r') as f:
                    data = json.load(f)
                    layout = Layout.from_dict(data)
                    self.layouts[layout.name] = layout
                    logger.info(f"Loaded layout: {layout.name}")
        except Exception as e:
            logger.error(f"Failed to load saved layouts: {e}")
    
    def save_layout(self, layout: Layout) -> bool:
        """Save a layout to disk."""
        try:
            layout_path = self.config_dir / f"{layout.name}.json"
            with open(layout_path, 'w') as f:
                json.dump(layout.to_dict(), f, indent=2)
            self.layouts[layout.name] = layout
            logger.info(f"Saved layout: {layout.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
            return False
    
    def get_layout(self, name: str) -> Optional[Layout]:
        """Get a layout by name."""
        return self.layouts.get(name)
    
    def list_layouts(self) -> List[str]:
        """List all available layouts."""
        return list(self.layouts.keys())
    
    def delete_layout(self, name: str) -> bool:
        """Delete a saved layout."""
        if name in ['default', 'minimal', 'performance', 'gaming', 'monitoring']:
            logger.warning(f"Cannot delete built-in layout: {name}")
            return False
        
        try:
            layout_path = self.config_dir / f"{name}.json"
            if layout_path.exists():
                layout_path.unlink()
            if name in self.layouts:
                del self.layouts[name]
            logger.info(f"Deleted layout: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete layout: {e}")
            return False
    
    def set_current_layout(self, name: str) -> bool:
        """Set the current active layout."""
        if name in self.layouts:
            self.current_layout = name
            return True
        return False
    
    def get_current_layout(self) -> Optional[Layout]:
        """Get the current active layout."""
        if self.current_layout:
            return self.layouts.get(self.current_layout)
        return self.layouts.get('default')
    
    def create_custom_layout(self, name: str, width: int = 320, height: int = 480) -> Layout:
        """Create a new custom layout."""
        layout = Layout(name=name, width=width, height=height)
        self.layouts[name] = layout
        return layout
    
    def duplicate_layout(self, source_name: str, new_name: str) -> Optional[Layout]:
        """Duplicate an existing layout."""
        source = self.layouts.get(source_name)
        if not source:
            return None
        
        # Create a deep copy
        layout_dict = source.to_dict()
        layout_dict['name'] = new_name
        new_layout = Layout.from_dict(layout_dict)
        self.layouts[new_name] = new_layout
        return new_layout

# Singleton instance
_layout_manager = None

def get_layout_manager() -> LayoutManager:
    """Get the singleton layout manager instance."""
    global _layout_manager
    if _layout_manager is None:
        _layout_manager = LayoutManager()
    return _layout_manager
