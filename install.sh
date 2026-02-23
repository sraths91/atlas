#!/bin/bash

# Atlas Installation Script
# This script installs Atlas and its dependencies

set -e

echo "🖥️  Atlas Installer"
echo "================================"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This application is designed for macOS only."
    exit 1
fi

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "Please install Python 3.9 or later from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python $REQUIRED_VERSION or later is required. You have Python $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"
echo ""

# Check if pip is installed
echo "📋 Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 is not installed."
    echo "Installing pip..."
    python3 -m ensurepip --upgrade
fi

echo "✅ pip is available"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

echo "✅ Dependencies installed"
echo ""

# Install the package
echo "📦 Installing Atlas..."
pip3 install -e .

echo "✅ Atlas installed"
echo ""

# Create config directory
echo "📁 Creating configuration directory..."
CONFIG_DIR="$HOME/.config/atlas"
mkdir -p "$CONFIG_DIR/themes"

echo "✅ Configuration directory created at $CONFIG_DIR"
echo ""

# ============================================
# Install Homebrew packages for full functionality
# ============================================
echo "🍺 Installing Homebrew packages for enhanced monitoring..."
echo ""

# Check if Homebrew is installed, install if not
BREW_CMD=""
if [ -x "/opt/homebrew/bin/brew" ]; then
    BREW_CMD="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW_CMD="/usr/local/bin/brew"
fi

# Install Homebrew if not found
if [ -z "$BREW_CMD" ]; then
    echo "Homebrew not found. Installing Homebrew..."
    echo ""
    echo "This will install Homebrew (https://brew.sh) - the missing package manager for macOS."
    echo "Homebrew is required for full monitoring functionality."
    echo ""
    read -p "Install Homebrew now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing Homebrew (this may take a few minutes)..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Re-check for Homebrew after installation
        if [ -x "/opt/homebrew/bin/brew" ]; then
            BREW_CMD="/opt/homebrew/bin/brew"
            # Add to PATH for this session
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x "/usr/local/bin/brew" ]; then
            BREW_CMD="/usr/local/bin/brew"
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        if [ -n "$BREW_CMD" ]; then
            echo "✅ Homebrew installed successfully!"
        else
            echo "⚠️  Homebrew installation may have failed. Continuing without Homebrew packages."
        fi
    else
        echo "Skipping Homebrew installation. Some monitoring features will be limited."
    fi
fi

if [ -n "$BREW_CMD" ]; then
    echo "✅ Homebrew found at: $BREW_CMD"
    echo ""

    # Required packages for core functionality
    PACKAGES_TO_INSTALL=""

    # smartmontools - SMART disk health monitoring
    if ! command -v smartctl &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL smartmontools"
        echo "  • smartmontools (SMART disk health)"
    else
        echo "  ✅ smartmontools already installed"
    fi

    # speedtest-cli - Network speed testing
    if ! command -v speedtest-cli &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL speedtest-cli"
        echo "  • speedtest-cli (network speed tests)"
    else
        echo "  ✅ speedtest-cli already installed"
    fi

    # mtr - Network path analysis
    if ! command -v mtr &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL mtr"
        echo "  • mtr (network diagnostics)"
    else
        echo "  ✅ mtr already installed"
    fi

    # Temperature monitoring - architecture specific
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        # Apple Silicon - use macmon (sudoless)
        if ! command -v macmon &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL macmon"
            echo "  • macmon (CPU temperature - Apple Silicon)"
        else
            echo "  ✅ macmon already installed"
        fi
    else
        # Intel - use osx-cpu-temp
        if ! command -v osx-cpu-temp &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL osx-cpu-temp"
            echo "  • osx-cpu-temp (CPU temperature - Intel)"
        else
            echo "  ✅ osx-cpu-temp already installed"
        fi
    fi

    # Install packages if any are needed
    if [ -n "$PACKAGES_TO_INSTALL" ]; then
        echo ""
        echo "Installing packages..."
        if $BREW_CMD install $PACKAGES_TO_INSTALL; then
            echo "✅ Homebrew packages installed successfully"
        else
            echo "⚠️  Some packages could not be installed (non-critical)"
        fi
    else
        echo ""
        echo "✅ All required Homebrew packages already installed"
    fi
else
    echo "⚠️  Homebrew not found. Some monitoring features will be limited."
    echo ""
    echo "To enable all monitoring features, install Homebrew:"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo ""
    echo "Then install required packages:"
    echo "  brew install smartmontools speedtest-cli mtr"
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        echo "  brew install macmon"
    else
        echo "  brew install osx-cpu-temp"
    fi
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Quick Start:"
echo "  1. Run in simulated mode (no hardware needed):"
echo "     atlas --simulated"
echo ""
echo "  2. List available themes:"
echo "     atlas --list-themes"
echo ""
echo "  3. Run with a specific theme:"
echo "     atlas --theme cyberpunk"
echo ""
echo "  4. Run with your display:"
echo "     atlas"
echo ""
echo "Configuration file: $CONFIG_DIR/config.json"
echo "Themes directory: $CONFIG_DIR/themes/"
echo ""
echo "For more information, see README.md"
echo ""
