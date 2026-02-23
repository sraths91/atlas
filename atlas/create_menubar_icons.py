#!/usr/bin/env python3
"""
Create menu bar icons based on ATLAS logo design
Generates PNG icons for macOS menu bar with status indicators
"""

from pathlib import Path
from PIL import Image, ImageDraw

# ATLAS color scheme
SLATE_BLUE = (44, 75, 92)      # #2C4B5C
TEAL_GREEN = (95, 181, 157)    # #5FB59D
YELLOW = (255, 170, 0)         # #FFAA00
RED = (255, 68, 68)            # #FF4444
GRAY = (128, 128, 128)         # #808080
WHITE = (255, 255, 255)        # #FFFFFF

def create_atlas_icon(size, dot_color=TEAL_GREEN, template_mode=False):
    """
    Create ATLAS triangular network icon
    
    Args:
        size: Icon size (e.g., 16, 32, 48)
        dot_color: Color for the node dots (status indicator)
        template_mode: If True, create black icon for macOS template mode
    
    Returns:
        PIL Image
    """
    # Create transparent image
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale coordinates based on size
    scale = size / 18.0  # Base design at 18px
    
    # Define triangle vertices (ATLAS "A" shape)
    # Top node
    top_x = size // 2
    top_y = int(2 * scale)
    
    # Bottom left node
    bl_x = int(3 * scale)
    bl_y = int(16 * scale)
    
    # Bottom right node
    br_x = int(15 * scale)
    br_y = int(16 * scale)
    
    # Middle right node (on right edge)
    mr_x = int(13 * scale)
    mr_y = int(8 * scale)
    
    # Line color
    if template_mode:
        line_color = (0, 0, 0, 255)  # Black for template
    else:
        line_color = SLATE_BLUE + (255,)
    
    # Line width
    line_width = max(1, int(2 * scale))
    
    # Draw triangle edges
    draw.line([top_x, top_y, bl_x, bl_y], fill=line_color, width=line_width)
    draw.line([bl_x, bl_y, br_x, br_y], fill=line_color, width=line_width)
    draw.line([br_x, br_y, mr_x, mr_y], fill=line_color, width=line_width)
    draw.line([mr_x, mr_y, top_x, top_y], fill=line_color, width=line_width)
    
    # Node dot radius
    dot_radius = max(2, int(2.5 * scale))
    
    # Draw node dots (status indicators)
    nodes = [
        (top_x, top_y),
        (bl_x, bl_y),
        (br_x, br_y),
        (mr_x, mr_y)
    ]
    
    # Dot color for status
    if template_mode:
        status_color = (0, 0, 0, 255)  # Black for template
    else:
        status_color = dot_color + (255,)
    
    for x, y in nodes:
        # Draw dot
        draw.ellipse(
            [x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius],
            fill=status_color,
            outline=status_color
        )
    
    return img


def create_all_icons(output_dir):
    """Create all icon variations"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    sizes = {
        '1x': 18,
        '2x': 36,
        '3x': 54
    }

    statuses = {
        'connected': TEAL_GREEN,
        'disconnected': GRAY,
        'warning': YELLOW,
        'error': RED
    }

    # Create colored icons for each status
    for status_name, color in statuses.items():
        for size_name, size in sizes.items():
            icon = create_atlas_icon(size, dot_color=color)
            filename = f"atlas_{status_name}@{size_name}.png"
            icon.save(output_path / filename)
            print(f"Created {filename}")

    # Create template icons (for automatic dark mode support)
    for size_name, size in sizes.items():
        icon = create_atlas_icon(size, template_mode=True)
        filename = f"atlas_template@{size_name}.png"
        icon.save(output_path / filename)
        print(f"Created {filename} (template)")


def create_simple_dot_icon(size, color):
    """Create simple colored dot icon (fallback)"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw circle
    margin = size // 4
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color + (255,),
        outline=(0, 0, 0, 128),
        width=1
    )
    
    return img


if __name__ == '__main__':
    # Create icons directory
    script_dir = Path(__file__).parent
    icons_dir = script_dir / 'menubar_icons'

    print("Creating ATLAS menu bar icons...")
    create_all_icons(icons_dir)
    
    print(f"\nIcons created in: {icons_dir}")
    print("\nIcon variations:")
    print("  - atlas_connected@*.png (green dots)")
    print("  - atlas_disconnected@*.png (gray dots)")
    print("  - atlas_warning@*.png (yellow dots)")
    print("  - atlas_error@*.png (red dots)")
    print("  - atlas_template@*.png (black, auto dark mode)")
