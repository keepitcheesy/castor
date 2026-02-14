#!/bin/bash
# Build script for creating Castor executable with PyInstaller

set -e

echo "Building Castor executable with PyInstaller..."

# Clean previous builds
rm -rf build dist

# Run PyInstaller
pyinstaller castor.spec

echo ""
echo "Build complete!"
echo "Executable can be found in: dist/castor"
echo ""
echo "To test the executable:"
echo "  ./dist/castor"
