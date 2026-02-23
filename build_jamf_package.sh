#!/bin/bash

# Atlas - Jamf Package Builder
# This script creates a PKG installer for deployment via Jamf Pro

set -e

VERSION="1.0.0"
IDENTIFIER="com.company.atlas"
APP_NAME="Atlas"

echo "🚀 Building Atlas package for Jamf Pro..."
echo "Version: $VERSION"

# Clean previous builds
rm -rf build_pkg
rm -f *.pkg

# Create package structure
echo "📦 Creating package structure..."
mkdir -p build_pkg/payload/Library/Application\ Support/Atlas
mkdir -p build_pkg/payload/Library/LaunchAgents
mkdir -p build_pkg/scripts

# Copy application files
echo "📋 Copying application files..."
cp -r atlas build_pkg/payload/Library/Application\ Support/Atlas/
cp requirements.txt build_pkg/payload/Library/Application\ Support/Atlas/
cp README.md build_pkg/payload/Library/Application\ Support/Atlas/

# Create startup script
echo "📝 Creating startup script..."
cat > build_pkg/payload/Library/Application\ Support/Atlas/start_dashboard.sh << 'EOF'
#!/bin/bash

# Atlas Dashboard Startup Script
LOG_FILE="/var/log/atlas.log"
ERROR_LOG="/var/log/atlas.error.log"

# Change to application directory
cd "/Library/Application Support/Atlas"

# Log startup
echo "$(date): Starting Atlas Dashboard..." >> "$LOG_FILE"

# Start the dashboard
/usr/bin/python3 -m atlas.app --theme cyberpunk --refresh-rate 1.0 >> "$LOG_FILE" 2>> "$ERROR_LOG"
EOF

chmod +x build_pkg/payload/Library/Application\ Support/Atlas/start_dashboard.sh

# Create LaunchAgent plist
echo "⚙️  Creating LaunchAgent..."
cat > build_pkg/payload/Library/LaunchAgents/com.company.atlas.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.company.atlas</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Library/Application Support/Atlas/start_dashboard.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>/var/log/atlas.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/atlas.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# Create postinstall script
echo "🔧 Creating postinstall script..."
cat > build_pkg/scripts/postinstall << 'EOF'
#!/bin/bash

echo "Installing Atlas Dashboard..."

# Install Python dependencies
cd "/Library/Application Support/Atlas"
/usr/bin/python3 -m pip install -r requirements.txt --quiet

# ============================================
# Install Homebrew packages for full functionality
# ============================================
echo "Checking for Homebrew packages..."

# Check if Homebrew is installed, install if not
BREW_CMD=""
if [ -x "/opt/homebrew/bin/brew" ]; then
    BREW_CMD="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW_CMD="/usr/local/bin/brew"
fi

# Install Homebrew if not found (non-interactive for PKG deployment)
if [ -z "$BREW_CMD" ]; then
    echo "Homebrew not found. Attempting to install Homebrew..."

    # Get the console user (the user logged in at the GUI)
    CONSOLE_USER=$(stat -f "%Su" /dev/console)

    if [ -n "$CONSOLE_USER" ] && [ "$CONSOLE_USER" != "root" ]; then
        echo "Installing Homebrew for user: $CONSOLE_USER"

        # Non-interactive Homebrew installation
        sudo -u "$CONSOLE_USER" NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>/dev/null || true

        # Re-check for Homebrew after installation
        if [ -x "/opt/homebrew/bin/brew" ]; then
            BREW_CMD="/opt/homebrew/bin/brew"
            echo "Homebrew installed successfully at /opt/homebrew/bin/brew"
        elif [ -x "/usr/local/bin/brew" ]; then
            BREW_CMD="/usr/local/bin/brew"
            echo "Homebrew installed successfully at /usr/local/bin/brew"
        else
            echo "Homebrew installation failed or is still in progress. Continuing without Homebrew packages."
        fi
    else
        echo "No console user found. Skipping Homebrew installation."
    fi
fi

if [ -n "$BREW_CMD" ]; then
    echo "Homebrew found at: $BREW_CMD"

    # Required packages for core functionality
    PACKAGES_TO_INSTALL=""

    # smartmontools - SMART disk health monitoring
    if ! command -v smartctl &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL smartmontools"
    fi

    # speedtest-cli - Network speed testing
    if ! command -v speedtest-cli &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL speedtest-cli"
    fi

    # mtr - Network path analysis
    if ! command -v mtr &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL mtr"
    fi

    # Temperature monitoring - architecture specific
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        if ! command -v macmon &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL macmon"
        fi
    else
        if ! command -v osx-cpu-temp &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL osx-cpu-temp"
        fi
    fi

    # Install packages if any are needed
    if [ -n "$PACKAGES_TO_INSTALL" ]; then
        echo "Installing Homebrew packages:$PACKAGES_TO_INSTALL"
        $BREW_CMD install $PACKAGES_TO_INSTALL 2>/dev/null && \
            echo "Homebrew packages installed successfully" || \
            echo "Some packages could not be installed (non-critical)"
    else
        echo "All required Homebrew packages already installed"
    fi
else
    echo "Homebrew not found. Some monitoring features will be limited."
    echo "Install Homebrew: https://brew.sh"
fi

# Set correct permissions
chmod 755 "/Library/Application Support/Atlas/start_dashboard.sh"
chmod 644 "/Library/LaunchAgents/com.company.atlas.plist"
chown -R root:wheel "/Library/Application Support/Atlas"
chown root:wheel "/Library/LaunchAgents/com.company.atlas.plist"

# Create log files
touch /var/log/atlas.log
touch /var/log/atlas.error.log
chmod 644 /var/log/atlas.log
chmod 644 /var/log/atlas.error.log

# Load LaunchAgent for all users
# Note: This will be loaded when users log in
echo "Atlas installed successfully!"
echo "The dashboard will start automatically on next login."
echo "Access it at: http://localhost:8767"

exit 0
EOF

chmod +x build_pkg/scripts/postinstall

# Create preinstall script (stops existing service)
echo "🛑 Creating preinstall script..."
cat > build_pkg/scripts/preinstall << 'EOF'
#!/bin/bash

# Stop existing service if running
if launchctl list | grep -q "com.company.atlas"; then
    echo "Stopping existing Atlas service..."
    launchctl unload /Library/LaunchAgents/com.company.atlas.plist 2>/dev/null || true
fi

exit 0
EOF

chmod +x build_pkg/scripts/preinstall

# Create uninstall script (for reference)
echo "🗑️  Creating uninstall script..."
cat > build_pkg/uninstall.sh << 'EOF'
#!/bin/bash

# Atlas Uninstaller

echo "Uninstalling Atlas..."

# Unload LaunchAgent
launchctl unload /Library/LaunchAgents/com.company.atlas.plist 2>/dev/null || true

# Remove files
rm -rf "/Library/Application Support/Atlas"
rm -f /Library/LaunchAgents/com.company.atlas.plist
rm -f /var/log/atlas.log
rm -f /var/log/atlas.error.log

echo "Atlas uninstalled successfully!"
exit 0
EOF

chmod +x build_pkg/uninstall.sh

# Build the package
echo "🔨 Building PKG installer..."
pkgbuild --root build_pkg/payload \
         --scripts build_pkg/scripts \
         --identifier "$IDENTIFIER" \
         --version "$VERSION" \
         --install-location / \
         "${APP_NAME}-${VERSION}.pkg"

# Create distribution package (optional, for more control)
echo "📦 Creating distribution package..."
productbuild --package "${APP_NAME}-${VERSION}.pkg" \
             --identifier "$IDENTIFIER" \
             --version "$VERSION" \
             "${APP_NAME}-${VERSION}-distribution.pkg"

echo ""
echo "✅ Package built successfully!"
echo ""
echo "📦 Package: ${APP_NAME}-${VERSION}.pkg"
echo "📦 Distribution: ${APP_NAME}-${VERSION}-distribution.pkg"
echo ""
echo "📤 Next steps:"
echo "1. Upload ${APP_NAME}-${VERSION}.pkg to Jamf Pro"
echo "2. Create a policy to deploy the package"
echo "3. Scope the policy to target computers"
echo ""
echo "🌐 Dashboard will be accessible at: http://localhost:8767"
echo "📝 Logs: /var/log/atlas.log"
echo ""
echo "🗑️  To uninstall, run: sudo bash build_pkg/uninstall.sh"
