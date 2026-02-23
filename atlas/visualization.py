"""Visualization module for generating performance graphs and charts."""
import logging
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class ChartRenderer:
    """Renders various types of charts and graphs."""
    
    def __init__(self, width: int = 300, height: int = 200):
        self.width = width
        self.height = height
        self.padding = 10
        self.colors = {
            'cpu': (0, 150, 255),
            'gpu': (255, 100, 0),
            'memory': (0, 255, 150),
            'temperature': (255, 50, 50),
            'network_up': (100, 200, 255),
            'network_down': (255, 200, 100),
            'grid': (50, 50, 50),
            'text': (200, 200, 200),
            'background': (20, 20, 30)
        }
    
    def render_line_chart(
        self,
        data: List[Tuple[float, float]],
        title: str = "",
        color: Tuple[int, int, int] = None,
        y_max: Optional[float] = None
    ) -> Image.Image:
        """Render a line chart from time-series data."""
        if color is None:
            color = self.colors['cpu']
        
        img = Image.new('RGB', (self.width, self.height), self.colors['background'])
        draw = ImageDraw.Draw(img)
        
        if not data:
            draw.text((self.width // 2 - 30, self.height // 2), "No Data", fill=self.colors['text'])
            return img
        
        # Calculate bounds
        chart_width = self.width - 2 * self.padding
        chart_height = self.height - 2 * self.padding - 20  # Leave space for title
        
        times = [d[0] for d in data]
        values = [d[1] for d in data]
        
        min_time = min(times)
        max_time = max(times)
        max_value = y_max if y_max else max(values) if values else 100
        
        # Draw grid
        for i in range(5):
            y = self.padding + 20 + (chart_height * i // 4)
            draw.line([(self.padding, y), (self.width - self.padding, y)], fill=self.colors['grid'])
        
        # Draw title
        if title:
            draw.text((self.padding, 5), title, fill=self.colors['text'])
        
        # Draw data line
        points = []
        for time_val, value in data:
            if max_time > min_time:
                x = self.padding + ((time_val - min_time) / (max_time - min_time)) * chart_width
            else:
                x = self.padding + chart_width / 2
            
            y = self.padding + 20 + chart_height - (value / max_value * chart_height)
            points.append((x, y))
        
        if len(points) > 1:
            draw.line(points, fill=color, width=2)
        
        # Draw value labels
        for i in range(5):
            value = max_value * (4 - i) / 4
            y = self.padding + 20 + (chart_height * i // 4)
            draw.text((5, y - 6), f"{value:.0f}", fill=self.colors['text'], font=None)
        
        return img
    
    def render_multi_line_chart(
        self,
        datasets: Dict[str, List[Tuple[float, float]]],
        title: str = "",
        y_max: Optional[float] = None
    ) -> Image.Image:
        """Render multiple lines on one chart."""
        img = Image.new('RGB', (self.width, self.height), self.colors['background'])
        draw = ImageDraw.Draw(img)
        
        if not datasets:
            draw.text((self.width // 2 - 30, self.height // 2), "No Data", fill=self.colors['text'])
            return img
        
        # Calculate bounds
        chart_width = self.width - 2 * self.padding
        chart_height = self.height - 2 * self.padding - 40  # Leave space for title and legend
        
        all_times = []
        all_values = []
        for data in datasets.values():
            if data:
                all_times.extend([d[0] for d in data])
                all_values.extend([d[1] for d in data])
        
        if not all_times:
            return img
        
        min_time = min(all_times)
        max_time = max(all_times)
        max_value = y_max if y_max else max(all_values) if all_values else 100
        
        # Draw grid
        for i in range(5):
            y = self.padding + 30 + (chart_height * i // 4)
            draw.line([(self.padding, y), (self.width - self.padding, y)], fill=self.colors['grid'])
        
        # Draw title
        if title:
            draw.text((self.padding, 5), title, fill=self.colors['text'])
        
        # Draw each dataset
        legend_x = self.padding
        for name, data in datasets.items():
            color = self.colors.get(name, (255, 255, 255))
            
            points = []
            for time_val, value in data:
                if max_time > min_time:
                    x = self.padding + ((time_val - min_time) / (max_time - min_time)) * chart_width
                else:
                    x = self.padding + chart_width / 2
                
                y = self.padding + 30 + chart_height - (value / max_value * chart_height)
                points.append((x, y))
            
            if len(points) > 1:
                draw.line(points, fill=color, width=2)
            
            # Draw legend
            draw.rectangle([legend_x, self.height - 15, legend_x + 10, self.height - 5], fill=color)
            draw.text((legend_x + 15, self.height - 17), name.upper(), fill=self.colors['text'])
            legend_x += 80
        
        return img
    
    def render_bar_chart(
        self,
        data: Dict[str, float],
        title: str = "",
        max_value: Optional[float] = None
    ) -> Image.Image:
        """Render a bar chart."""
        img = Image.new('RGB', (self.width, self.height), self.colors['background'])
        draw = ImageDraw.Draw(img)
        
        if not data:
            draw.text((self.width // 2 - 30, self.height // 2), "No Data", fill=self.colors['text'])
            return img
        
        chart_height = self.height - 2 * self.padding - 40
        bar_width = (self.width - 2 * self.padding) // len(data) - 5
        
        max_val = max_value if max_value else max(data.values()) if data.values() else 100
        
        # Draw title
        if title:
            draw.text((self.padding, 5), title, fill=self.colors['text'])
        
        # Draw bars
        x = self.padding
        for name, value in data.items():
            bar_height = (value / max_val) * chart_height
            y = self.padding + 30 + chart_height - bar_height
            
            color = self.colors.get(name, (100, 150, 255))
            draw.rectangle([x, y, x + bar_width, self.padding + 30 + chart_height], fill=color)
            
            # Draw label
            label = f"{value:.1f}"
            draw.text((x, y - 15), label, fill=self.colors['text'])
            draw.text((x, self.height - 20), name[:3].upper(), fill=self.colors['text'])
            
            x += bar_width + 5
        
        return img
    
    def render_gauge(
        self,
        value: float,
        max_value: float = 100,
        label: str = "",
        color: Tuple[int, int, int] = None
    ) -> Image.Image:
        """Render a circular gauge."""
        if color is None:
            color = self.colors['cpu']
        
        size = min(self.width, self.height)
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center = size // 2
        radius = size // 2 - 10
        thickness = 15
        
        # Draw background arc
        draw.arc(
            [center - radius, center - radius, center + radius, center + radius],
            start=-225, end=45, fill=(50, 50, 50), width=thickness
        )
        
        # Draw value arc
        percentage = (value / max_value) * 270  # 270 degrees total
        draw.arc(
            [center - radius, center - radius, center + radius, center + radius],
            start=-225, end=-225 + percentage, fill=color, width=thickness
        )
        
        # Draw value text
        value_text = f"{value:.0f}%"
        # Approximate text size
        text_width = len(value_text) * 12
        draw.text((center - text_width // 2, center - 10), value_text, fill=(255, 255, 255))
        
        # Draw label
        if label:
            label_width = len(label) * 8
            draw.text((center - label_width // 2, center + 15), label, fill=(200, 200, 200))
        
        return img
    
    def render_stats_summary(self, stats: Dict[str, Any]) -> Image.Image:
        """Render a summary statistics panel."""
        img = Image.new('RGB', (self.width, self.height), self.colors['background'])
        draw = ImageDraw.Draw(img)
        
        y = 10
        draw.text((10, y), "Performance Summary", fill=self.colors['text'])
        y += 25
        
        metrics = [
            ("CPU Avg", stats.get('avg_cpu', 0), "%"),
            ("CPU Max", stats.get('max_cpu', 0), "%"),
            ("GPU Avg", stats.get('avg_gpu', 0), "%"),
            ("GPU Max", stats.get('max_gpu', 0), "%"),
            ("Memory Avg", stats.get('avg_memory', 0), "%"),
            ("Memory Max", stats.get('max_memory', 0), "%"),
            ("Temp Avg", stats.get('avg_temp', 0), "°C"),
            ("Temp Max", stats.get('max_temp', 0), "°C"),
        ]
        
        for label, value, unit in metrics:
            text = f"{label}: {value:.1f}{unit}"
            draw.text((10, y), text, fill=self.colors['text'])
            y += 20
        
        return img

def create_performance_report(
    aggregated_data: Dict[str, List[Tuple[float, float]]],
    stats: Dict[str, Any],
    output_path: str
) -> bool:
    """Create a comprehensive performance report image."""
    try:
        # Create a large canvas
        report_width = 800
        report_height = 1000
        report = Image.new('RGB', (report_width, report_height), (20, 20, 30))
        
        renderer = ChartRenderer(width=380, height=200)
        
        # CPU chart
        if 'cpu' in aggregated_data:
            cpu_chart = renderer.render_line_chart(
                aggregated_data['cpu'],
                title="CPU Usage (%)",
                color=(0, 150, 255)
            )
            report.paste(cpu_chart, (10, 10))
        
        # GPU chart
        if 'gpu' in aggregated_data:
            gpu_chart = renderer.render_line_chart(
                aggregated_data['gpu'],
                title="GPU Usage (%)",
                color=(255, 100, 0)
            )
            report.paste(gpu_chart, (410, 10))
        
        # Memory chart
        if 'memory' in aggregated_data:
            memory_chart = renderer.render_line_chart(
                aggregated_data['memory'],
                title="Memory Usage (%)",
                color=(0, 255, 150)
            )
            report.paste(memory_chart, (10, 230))
        
        # Temperature chart
        if 'temperature' in aggregated_data:
            temp_chart = renderer.render_line_chart(
                aggregated_data['temperature'],
                title="Temperature (°C)",
                color=(255, 50, 50)
            )
            report.paste(temp_chart, (410, 230))
        
        # Network chart
        network_data = {
            'network_up': aggregated_data.get('network_up', []),
            'network_down': aggregated_data.get('network_down', [])
        }
        network_chart = renderer.render_multi_line_chart(
            network_data,
            title="Network Usage (KB/s)"
        )
        report.paste(network_chart, (10, 450))
        
        # Stats summary
        stats_renderer = ChartRenderer(width=380, height=200)
        stats_panel = stats_renderer.render_stats_summary(stats)
        report.paste(stats_panel, (410, 450))
        
        # Save report
        report.save(output_path)
        logger.info(f"Performance report saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create performance report: {e}")
        return False
