"""
UI Components for rendering system metrics
"""
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional, Dict, Any
import logging
import math

logger = logging.getLogger(__name__)

class UIComponent:
    """Base class for UI components"""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        """
        Initialize UI component
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Component width
            height: Component height
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def render(self, image: Image.Image, data: Any):
        """
        Render the component
        
        Args:
            image: PIL Image to render on
            data: Data to display
        """
        raise NotImplementedError


class ProgressBar(UIComponent):
    """Progress bar component"""
    
    def __init__(self, x: int, y: int, width: int, height: int,
                 bg_color: Tuple[int, int, int] = (40, 40, 40),
                 fg_color: Tuple[int, int, int] = (0, 200, 100),
                 border_color: Optional[Tuple[int, int, int]] = None,
                 show_percentage: bool = True):
        """
        Initialize progress bar
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Bar width
            height: Bar height
            bg_color: Background color
            fg_color: Foreground color
            border_color: Border color (None for no border)
            show_percentage: Whether to show percentage text
        """
        super().__init__(x, y, width, height)
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.border_color = border_color
        self.show_percentage = show_percentage
    
    def render(self, image: Image.Image, progress: float):
        """
        Render the progress bar
        
        Args:
            image: PIL Image to render on
            progress: Progress value (0.0 to 1.0)
        """
        draw = ImageDraw.Draw(image)
        
        # Clamp progress
        progress = max(0.0, min(1.0, progress))
        
        # Draw background
        draw.rectangle(
            [self.x, self.y, self.x + self.width, self.y + self.height],
            fill=self.bg_color
        )
        
        # Draw progress
        progress_width = int(self.width * progress)
        if progress_width > 0:
            draw.rectangle(
                [self.x, self.y, self.x + progress_width, self.y + self.height],
                fill=self.fg_color
            )
        
        # Draw border
        if self.border_color:
            draw.rectangle(
                [self.x, self.y, self.x + self.width, self.y + self.height],
                outline=self.border_color,
                width=1
            )
        
        # Draw percentage text
        if self.show_percentage:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except Exception:
                font = ImageFont.load_default()
            
            percentage_text = f"{int(progress * 100)}%"
            bbox = draw.textbbox((0, 0), percentage_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            text_x = self.x + (self.width - text_width) // 2
            text_y = self.y + (self.height - text_height) // 2
            
            # Draw text with shadow for better visibility
            draw.text((text_x + 1, text_y + 1), percentage_text, font=font, fill=(0, 0, 0))
            draw.text((text_x, text_y), percentage_text, font=font, fill=(255, 255, 255))


class GaugeChart(UIComponent):
    """Circular gauge chart component"""
    
    def __init__(self, x: int, y: int, radius: int,
                 bg_color: Tuple[int, int, int] = (40, 40, 40),
                 fg_color: Tuple[int, int, int] = (0, 200, 100),
                 text_color: Tuple[int, int, int] = (255, 255, 255),
                 start_angle: int = 135,
                 end_angle: int = 405):
        """
        Initialize gauge chart
        
        Args:
            x: Center X coordinate
            y: Center Y coordinate
            radius: Gauge radius
            bg_color: Background arc color
            fg_color: Foreground arc color
            text_color: Text color
            start_angle: Start angle in degrees
            end_angle: End angle in degrees
        """
        super().__init__(x - radius, y - radius, radius * 2, radius * 2)
        self.center_x = x
        self.center_y = y
        self.radius = radius
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.text_color = text_color
        self.start_angle = start_angle
        self.end_angle = end_angle
    
    def render(self, image: Image.Image, value: float, label: str = ""):
        """
        Render the gauge chart
        
        Args:
            image: PIL Image to render on
            value: Value (0.0 to 1.0)
            label: Optional label text
        """
        draw = ImageDraw.Draw(image)
        
        # Clamp value
        value = max(0.0, min(1.0, value))
        
        # Calculate bounding box
        bbox = [
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius
        ]
        
        # Draw background arc
        draw.arc(bbox, self.start_angle, self.end_angle, fill=self.bg_color, width=8)
        
        # Draw foreground arc
        angle_range = self.end_angle - self.start_angle
        current_angle = self.start_angle + (angle_range * value)
        draw.arc(bbox, self.start_angle, current_angle, fill=self.fg_color, width=8)
        
        # Draw center value
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except Exception:
            font = ImageFont.load_default()
            label_font = ImageFont.load_default()
        
        percentage_text = f"{int(value * 100)}%"
        bbox = draw.textbbox((0, 0), percentage_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = self.center_x - text_width // 2
        text_y = self.center_y - text_height // 2
        
        draw.text((text_x, text_y), percentage_text, font=font, fill=self.text_color)
        
        # Draw label
        if label:
            bbox = draw.textbbox((0, 0), label, font=label_font)
            label_width = bbox[2] - bbox[0]
            label_x = self.center_x - label_width // 2
            label_y = self.center_y + self.radius // 2
            
            draw.text((label_x, label_y), label, font=label_font, fill=self.text_color)


class TextLabel(UIComponent):
    """Text label component"""
    
    def __init__(self, x: int, y: int, font_size: int = 16,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 align: str = "left"):
        """
        Initialize text label
        
        Args:
            x: X coordinate
            y: Y coordinate
            font_size: Font size
            color: Text color
            align: Text alignment ('left', 'center', 'right')
        """
        super().__init__(x, y, 0, 0)
        self.font_size = font_size
        self.color = color
        self.align = align
    
    def render(self, image: Image.Image, text: str):
        """
        Render the text label
        
        Args:
            image: PIL Image to render on
            text: Text to display
        """
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", self.font_size)
        except Exception:
            font = ImageFont.load_default()
        
        # Calculate text position based on alignment
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        x = self.x
        if self.align == "center":
            x = self.x - text_width // 2
        elif self.align == "right":
            x = self.x - text_width
        
        draw.text((x, self.y), text, font=font, fill=self.color)


class NetworkGraph(UIComponent):
    """Network usage graph component"""
    
    def __init__(self, x: int, y: int, width: int, height: int,
                 max_points: int = 60,
                 upload_color: Tuple[int, int, int] = (255, 100, 100),
                 download_color: Tuple[int, int, int] = (100, 100, 255),
                 bg_color: Tuple[int, int, int] = (20, 20, 20)):
        """
        Initialize network graph
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Graph width
            height: Graph height
            max_points: Maximum number of data points
            upload_color: Upload line color
            download_color: Download line color
            bg_color: Background color
        """
        super().__init__(x, y, width, height)
        self.max_points = max_points
        self.upload_color = upload_color
        self.download_color = download_color
        self.bg_color = bg_color
        self.upload_data = []
        self.download_data = []
    
    def add_data(self, upload: float, download: float):
        """
        Add data point
        
        Args:
            upload: Upload speed (bytes/s)
            download: Download speed (bytes/s)
        """
        self.upload_data.append(upload)
        self.download_data.append(download)
        
        # Keep only max_points
        if len(self.upload_data) > self.max_points:
            self.upload_data.pop(0)
        if len(self.download_data) > self.max_points:
            self.download_data.pop(0)
    
    def render(self, image: Image.Image, data: Dict[str, float]):
        """
        Render the network graph
        
        Args:
            image: PIL Image to render on
            data: Dictionary with 'up' and 'down' keys
        """
        draw = ImageDraw.Draw(image)
        
        # Add new data
        self.add_data(data.get('up', 0), data.get('down', 0))
        
        # Draw background
        draw.rectangle(
            [self.x, self.y, self.x + self.width, self.y + self.height],
            fill=self.bg_color
        )
        
        if len(self.upload_data) < 2:
            return
        
        # Find max value for scaling
        max_value = max(max(self.upload_data), max(self.download_data))
        if max_value == 0:
            max_value = 1
        
        # Draw upload line
        self._draw_line(draw, self.upload_data, max_value, self.upload_color)
        
        # Draw download line
        self._draw_line(draw, self.download_data, max_value, self.download_color)
        
        # Draw border
        draw.rectangle(
            [self.x, self.y, self.x + self.width, self.y + self.height],
            outline=(100, 100, 100),
            width=1
        )
    
    def _draw_line(self, draw: ImageDraw.ImageDraw, data: list, max_value: float, color: Tuple[int, int, int]):
        """Draw a line graph"""
        if len(data) < 2:
            return
        
        points = []
        for i, value in enumerate(data):
            x = self.x + (i * self.width // self.max_points)
            y = self.y + self.height - int((value / max_value) * self.height)
            points.append((x, y))
        
        # Draw line
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=color, width=2)


class SystemInfoPanel(UIComponent):
    """Panel displaying system information"""
    
    def __init__(self, x: int, y: int, width: int, height: int,
                 bg_color: Tuple[int, int, int] = (30, 30, 30),
                 text_color: Tuple[int, int, int] = (255, 255, 255),
                 accent_color: Tuple[int, int, int] = (0, 150, 255)):
        """
        Initialize system info panel
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Panel width
            height: Panel height
            bg_color: Background color
            text_color: Text color
            accent_color: Accent color
        """
        super().__init__(x, y, width, height)
        self.bg_color = bg_color
        self.text_color = text_color
        self.accent_color = accent_color
    
    def render(self, image: Image.Image, data: Dict[str, Any]):
        """
        Render the system info panel
        
        Args:
            image: PIL Image to render on
            data: Dictionary with system information
        """
        draw = ImageDraw.Draw(image)
        
        # Draw background
        draw.rectangle(
            [self.x, self.y, self.x + self.width, self.y + self.height],
            fill=self.bg_color
        )
        
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            value_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except Exception:
            title_font = ImageFont.load_default()
            value_font = ImageFont.load_default()
        
        # Draw title
        title = data.get('title', 'System Info')
        draw.text((self.x + 10, self.y + 5), title, font=title_font, fill=self.accent_color)
        
        # Draw info items
        y_offset = self.y + 30
        items = data.get('items', [])
        
        for item in items:
            label = item.get('label', '')
            value = item.get('value', '')
            
            # Draw label
            draw.text((self.x + 10, y_offset), f"{label}:", font=value_font, fill=self.text_color)
            
            # Draw value
            draw.text((self.x + self.width // 2, y_offset), str(value), font=value_font, fill=self.accent_color)
            
            y_offset += 20
        
        # Draw border
        draw.rectangle(
            [self.x, self.y, self.x + self.width, self.y + self.height],
            outline=self.accent_color,
            width=1
        )
