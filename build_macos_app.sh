#!/bin/bash

# Atlas - Native macOS App Builder
# Creates a .app bundle that can be deployed via Jamf Pro

set -e

VERSION="1.0.0"
APP_NAME="Atlas"

echo "🚀 Building native macOS application..."
echo "Version: $VERSION"

# Check if py2app is installed
if ! python3 -c "import py2app" 2>/dev/null; then
    echo "📦 Installing py2app..."
    pip3 install py2app
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "🔨 Building application bundle..."
python3 setup_app.py py2app

if [ -d "dist/$APP_NAME.app" ]; then
    echo "✅ Application built successfully!"
    echo ""
    echo "📱 Application: dist/$APP_NAME.app"
    echo ""
    
    # Create DMG for distribution
    echo "💿 Creating DMG installer..."
    hdiutil create -volname "$APP_NAME" \
                   -srcfolder "dist/$APP_NAME.app" \
                   -ov -format UDZO \
                   "dist/Atlas-${VERSION}.dmg"
    
    echo ""
    echo "✅ DMG created: dist/Atlas-${VERSION}.dmg"
    echo ""
    
    # Create PKG from app
    echo "📦 Creating PKG installer..."
    pkgbuild --root dist \
             --identifier com.company.atlas \
             --version "$VERSION" \
             --install-location /Applications \
             "dist/Atlas-${VERSION}.pkg"
    
    echo ""
    echo "✅ PKG created: dist/Atlas-${VERSION}.pkg"
    echo ""
    echo "📤 Upload to Jamf Pro:"
    echo "   - Upload: dist/Atlas-${VERSION}.pkg"
    echo "   - Or use: dist/Atlas-${VERSION}.dmg"
    echo ""
    echo "🎯 To test locally:"
    echo "   open 'dist/$APP_NAME.app'"
    echo ""
    
else
    echo "❌ Build failed!"
    exit 1
fi
