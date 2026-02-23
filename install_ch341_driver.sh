#!/bin/bash

echo "================================================"
echo "  CH341 Driver Installation for macOS"
echo "================================================"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is for macOS only"
    exit 1
fi

echo "📥 Step 1: Downloading CH341 Driver..."
echo ""

# Try multiple download sources
DOWNLOAD_SUCCESS=0

# Source 1: WCH official site (direct link)
echo "Trying official WCH website..."
curl -L -o /tmp/CH341SER_MAC.ZIP "http://www.wch.cn/downloads/file/178.html" 2>/dev/null
if [ -f /tmp/CH341SER_MAC.ZIP ] && file /tmp/CH341SER_MAC.ZIP | grep -q "Zip archive"; then
    echo "✅ Downloaded from official site"
    DOWNLOAD_SUCCESS=1
fi

# Source 2: Alternative download link
if [ $DOWNLOAD_SUCCESS -eq 0 ]; then
    echo "Trying alternative source..."
    curl -L -o /tmp/CH341SER_MAC.ZIP "https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver/raw/master/CH34x_Install_V1.5.pkg" 2>/dev/null
    if [ -f /tmp/CH341SER_MAC.ZIP ]; then
        echo "✅ Downloaded from alternative source"
        DOWNLOAD_SUCCESS=1
    fi
fi

# If download failed, provide manual instructions
if [ $DOWNLOAD_SUCCESS -eq 0 ]; then
    echo ""
    echo "⚠️  Automatic download failed. Please download manually:"
    echo ""
    echo "Option 1: Official WCH Website"
    echo "   URL: http://www.wch-ic.com/downloads/CH341SER_MAC_ZIP.html"
    echo "   1. Open the URL in your browser"
    echo "   2. Click the download button"
    echo "   3. Save to /tmp/CH341SER_MAC.ZIP"
    echo ""
    echo "Option 2: GitHub Mirror (Recommended)"
    echo "   URL: https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver"
    echo "   1. Download CH34x_Install_V1.5.pkg"
    echo "   2. Save to /tmp/"
    echo ""
    echo "After downloading, run this script again."
    echo ""
    
    # Open browser to help
    read -p "Open download page in browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver"
    fi
    
    exit 1
fi

echo ""
echo "📦 Step 2: Extracting driver..."
echo ""

# Check if it's a ZIP or PKG
if file /tmp/CH341SER_MAC.ZIP | grep -q "Zip archive"; then
    unzip -o /tmp/CH341SER_MAC.ZIP -d /tmp/CH341_Driver/
    DRIVER_PATH=$(find /tmp/CH341_Driver -name "*.pkg" | head -n 1)
elif file /tmp/CH341SER_MAC.ZIP | grep -q "package"; then
    DRIVER_PATH="/tmp/CH341SER_MAC.ZIP"
else
    echo "❌ Downloaded file is not a valid driver package"
    exit 1
fi

if [ -z "$DRIVER_PATH" ]; then
    echo "❌ Could not find driver package"
    exit 1
fi

echo "✅ Driver package found: $DRIVER_PATH"
echo ""

echo "🔧 Step 3: Installing driver..."
echo ""
echo "⚠️  This requires administrator privileges"
echo ""

# Install the driver
sudo installer -pkg "$DRIVER_PATH" -target /

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Driver installed successfully!"
    echo ""
    echo "================================================"
    echo "  IMPORTANT: REBOOT REQUIRED"
    echo "================================================"
    echo ""
    echo "The CH341 driver requires a system reboot to work."
    echo ""
    echo "After rebooting:"
    echo "  1. Reconnect your XuanFang display"
    echo "  2. Run: python3 -m atlas.app"
    echo ""
    
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
        sleep 5
        sudo reboot
    else
        echo ""
        echo "Please reboot manually when ready:"
        echo "  sudo reboot"
        echo ""
    fi
else
    echo ""
    echo "❌ Driver installation failed"
    echo ""
    echo "Please try manual installation:"
    echo "  1. Open Finder"
    echo "  2. Go to /tmp/CH341_Driver/"
    echo "  3. Double-click the .pkg file"
    echo "  4. Follow the installation wizard"
    echo ""
fi
