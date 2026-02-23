"""
Test script to verify Atlas installation
"""
import sys
import importlib

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    modules = [
        'atlas',
        'atlas.app',
        'atlas.config',
        'atlas.system_monitor',
        'atlas.display_driver',
        'atlas.themes',
        'atlas.ui_components',
    ]
    
    failed = []
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"  {module}")
        except ImportError as e:
            print(f"  {module}: {e}")
            failed.append(module)
    
    return len(failed) == 0

def test_dependencies():
    """Test that all dependencies are installed"""
    print("\nTesting dependencies...")
    
    dependencies = [
        ('psutil', 'System monitoring'),
        ('PIL', 'Image processing'),
        ('serial', 'Serial communication'),
    ]
    
    failed = []
    for module, description in dependencies:
        try:
            importlib.import_module(module)
            print(f"  {module} ({description})")
        except ImportError:
            print(f"  {module} ({description}) - NOT INSTALLED")
            failed.append(module)
    
    return len(failed) == 0

def test_system_monitor():
    """Test system monitoring functionality"""
    print("\nTesting system monitor...")
    
    try:
        from atlas.system_monitor import SystemMonitor
        
        monitor = SystemMonitor()
        stats = monitor.get_all_stats()
        
        print(f"  CPU Usage: {stats['cpu'] * 100:.1f}%")
        print(f"  Memory Usage: {stats['memory'] * 100:.1f}%")
        print(f"  Disk Usage: {len(stats['disks'])} disk(s) monitored")
        print(f"  Network: Up={stats['network']['up']:.0f} B/s, Down={stats['network']['down']:.0f} B/s")
        
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_themes():
    """Test theme system"""
    print("\nTesting themes...")
    
    try:
        from atlas.themes import ThemeManager
        
        theme_manager = ThemeManager()
        themes = theme_manager.list_themes()
        
        print(f"  Found {len(themes)} themes:")
        for theme_name in themes:
            theme = theme_manager.get_theme(theme_name)
            print(f"     - {theme_name}: {theme.description}")
        
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_display_driver():
    """Test display driver"""
    print("\nTesting display driver...")
    
    try:
        from atlas.display_driver import SimulatedDisplay
        
        display = SimulatedDisplay()
        if display.connect():
            print(f"  Simulated display connected")
            print(f"     Resolution: {display.width}x{display.height}")
            display.disconnect()
            return True
        else:
            print(f"  Failed to connect to simulated display")
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_ui_components():
    """Test UI components"""
    print("\nTesting UI components...")
    
    try:
        from atlas.ui_components import (
            GaugeChart, ProgressBar, TextLabel, NetworkGraph, SystemInfoPanel
        )
        from PIL import Image
        
        # Create a test canvas
        image = Image.new('RGB', (320, 480), color=(0, 0, 0))
        
        # Test each component
        gauge = GaugeChart(x=100, y=100, radius=50)
        gauge.render(image, 0.75, "Test")
        print("  GaugeChart")
        
        bar = ProgressBar(x=10, y=200, width=300, height=20)
        bar.render(image, 0.5)
        print("  ProgressBar")
        
        label = TextLabel(x=160, y=250, align='center')
        label.render(image, "Test Label")
        print("  TextLabel")
        
        graph = NetworkGraph(x=10, y=300, width=300, height=80)
        graph.render(image, {'up': 1000, 'down': 5000})
        print("  NetworkGraph")
        
        panel = SystemInfoPanel(x=10, y=400, width=300, height=70)
        panel.render(image, {'title': 'Test', 'items': []})
        print("  SystemInfoPanel")
        
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_config():
    """Test configuration system"""
    print("\nTesting configuration...")
    
    try:
        from atlas.config import ConfigManager
        
        config = ConfigManager()
        
        # Test getting values
        refresh_rate = config.get('display.refresh_rate', 1.0)
        theme = config.get('display.theme', 'dark')
        
        print(f"  Refresh rate: {refresh_rate}s")
        print(f"  Theme: {theme}")
        print(f"  Config file: {config.config_path}")
        
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Atlas - Installation Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Dependencies", test_dependencies),
        ("System Monitor", test_system_monitor),
        ("Themes", test_themes),
        ("Display Driver", test_display_driver),
        ("UI Components", test_ui_components),
        ("Configuration", test_config),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n{name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll tests passed! Atlas is ready to use.")
        print("\nQuick start:")
        print("  atlas --simulated")
        return 0
    else:
        print("\n Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
