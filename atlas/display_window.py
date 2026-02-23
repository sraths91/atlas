#!/usr/bin/env python3
"""
Enhanced Display Window
Creates a real-time display window for simulated mode that looks and feels like hardware
"""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DisplayWindow:
    """Real-time display window for simulated mode"""
    
    def __init__(self, width=320, height=480, title="Atlas", always_on_top=True):
        self.width = width
        self.height = height
        self.title = title
        self.always_on_top = always_on_top
        self.running = False
        self.window = None
        self.canvas = None
        self.photo = None
        self.preview_path = "/tmp/atlas_preview.png"
        
    def create_window(self):
        """Create the display window"""
        self.window = tk.Tk()
        self.window.title(self.title)
        
        # Set window properties
        if self.always_on_top:
            self.window.attributes('-topmost', True)
        
        # Create frame with border to look like hardware
        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create canvas for display
        self.canvas = tk.Canvas(
            frame,
            width=self.width,
            height=self.height,
            bg='black',
            highlightthickness=2,
            highlightbackground='#333333'
        )
        self.canvas.grid(row=0, column=0)
        
        # Create control frame
        control_frame = ttk.Frame(frame, padding="5")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Add controls
        ttk.Button(control_frame, text="📌 Pin", command=self.toggle_pin).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Refresh", command=self.force_refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="📁 Open Folder", command=self.open_folder).pack(side=tk.LEFT, padx=2)
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="🟢 Live", foreground="green")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # Center window on screen
        self.center_window()
        
        # Bind close event
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'+{x}+{y}')
    
    def toggle_pin(self):
        """Toggle always-on-top"""
        self.always_on_top = not self.always_on_top
        self.window.attributes('-topmost', self.always_on_top)
        
    def force_refresh(self):
        """Force refresh the display"""
        self.update_display()
        
    def open_folder(self):
        """Open the folder containing preview"""
        import subprocess
        subprocess.run(['open', '/tmp'], timeout=5)
    
    def update_display(self):
        """Update the display with latest preview"""
        try:
            # Load preview image
            if Path(self.preview_path).exists():
                img = Image.open(self.preview_path)
                
                # Resize if needed
                if img.size != (self.width, self.height):
                    img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                self.photo = ImageTk.PhotoImage(img)
                
                # Update canvas
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                
                # Update status
                self.status_label.config(text="🟢 Live", foreground="green")
            else:
                # Show "waiting" message
                self.canvas.delete("all")
                self.canvas.create_text(
                    self.width // 2,
                    self.height // 2,
                    text="Waiting for display...",
                    fill="white",
                    font=("Helvetica", 14)
                )
                self.status_label.config(text="⏳ Waiting", foreground="orange")
                
        except Exception as e:
            logger.error(f"Error updating display: {e}")
            self.status_label.config(text="Error", foreground="red")
    
    def auto_refresh_loop(self):
        """Auto-refresh loop"""
        while self.running:
            try:
                self.update_display()
                time.sleep(0.5)  # Refresh every 500ms
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the display window"""
        self.running = True
        
        # Create window
        self.create_window()
        
        # Start auto-refresh thread
        refresh_thread = threading.Thread(target=self.auto_refresh_loop, daemon=True)
        refresh_thread.start()
        
        # Initial update
        self.update_display()
        
        # Start main loop
        self.window.mainloop()
    
    def on_close(self):
        """Handle window close"""
        self.running = False
        if self.window:
            self.window.destroy()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Display Window')
    parser.add_argument('--width', type=int, default=320, help='Display width')
    parser.add_argument('--height', type=int, default=480, help='Display height')
    parser.add_argument('--title', default='Atlas', help='Window title')
    parser.add_argument('--no-pin', action='store_true', help='Disable always-on-top')
    
    args = parser.parse_args()
    
    print("🖥️  Starting Enhanced Display Window...")
    print(f"   Resolution: {args.width}x{args.height}")
    print(f"   Always on top: {not args.no_pin}")
    print("\nTip: Run the app in another terminal:")
    print("   python3 -m atlas.app --simulated\n")
    
    window = DisplayWindow(
        width=args.width,
        height=args.height,
        title=args.title,
        always_on_top=not args.no_pin
    )
    
    window.start()

if __name__ == "__main__":
    main()
