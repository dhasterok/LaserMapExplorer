#!/usr/bin/env bash
#
# Build the distributable macOS app bundle and wrap it in a DMG.
#
# Run from the repository root:
#     ./packaging/build_macos.sh
#
# Produces dist/LaME.app and dist/LaME-macos-arm64.dmg. The result is unsigned --
# testers must right-click -> Open the first time (see packaging/README-testers.md).

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"
PYTHON="${PYTHON:-python}"

echo "==> Building the blockly bundle (gitignored, so never present in a fresh clone)"
(cd blockly && npm install --no-audit --no-fund && npx webpack)

echo "==> Building the user guide"
"$PYTHON" -m sphinx -b html docs/source docs/build/html

echo "==> Generating application icons"
"$PYTHON" packaging/make_icons.py

echo "==> Freezing with PyInstaller"
"$PYTHON" -m PyInstaller --noconfirm --clean packaging/LaME.spec

echo "==> Smoke-testing the frozen bundle"
QT_QPA_PLATFORM=offscreen ./dist/LaME.app/Contents/MacOS/LaME --selftest

# An arm64 bundle must carry at least an ad-hoc signature or macOS refuses to launch
# it. PyInstaller signs during BUNDLE, but re-sign here so the step is explicit and
# survives any post-processing added later.
echo "==> Ad-hoc signing"
codesign --force --deep --sign - dist/LaME.app
codesign --verify --deep --strict dist/LaME.app

echo "==> Building the DMG"
DMG="dist/LaME-macos-arm64.dmg"
rm -f "$DMG"
STAGE="$(mktemp -d)"
cp -R dist/LaME.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/README-testers.md "$STAGE/README.md"
hdiutil create -volname "LaME" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"

echo "==> Done: $ROOT/$DMG"
