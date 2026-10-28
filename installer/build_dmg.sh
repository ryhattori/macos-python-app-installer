#!/bin/bash
# Build <name>.app and <name>-<version>.dmg (macOS): the app holds uv, the pinned requirements and the app's wheel;
# its launcher sets up the Python environment on first launch (installer/launcher.sh). The app is ad-hoc signed
# only (no Developer ID): Gatekeeper asks the user to allow it once.
#
#   installer/build_dmg.sh            # -> dist/StandIn.app, dist/StandIn-0.1.0.dmg
set -euo pipefail
cd "$(dirname "$0")/.."
NAME="${APP_NAME:-StandIn}"
MODULE="${APP_MODULE:-standin_app}"
BUNDLE_ID="${BUNDLE_ID:-io.github.ryhattori.standin}"
VERSION="${APP_VERSION:-0.1.0}"
UV_VERSION="${UV_VERSION:-0.13.6}"
DIST="dist"
APP="$DIST/$NAME.app"

rm -rf "$DIST" && mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/wheels"

# uv for Apple Silicon, from its release (its checksum file checked)
TMP="$(mktemp -d)"
BASE="https://github.com/astral-sh/uv/releases/download/$UV_VERSION"
curl -fsSL -o "$TMP/uv.tar.gz" "$BASE/uv-aarch64-apple-darwin.tar.gz"
curl -fsSL -o "$TMP/uv.sha256" "$BASE/uv-aarch64-apple-darwin.tar.gz.sha256"
(cd "$TMP" && echo "$(awk '{print $1}' uv.sha256)  uv.tar.gz" | shasum -a 256 -c -)
tar -xzf "$TMP/uv.tar.gz" -C "$TMP"
cp "$TMP"/uv-aarch64-apple-darwin/uv "$APP/Contents/Resources/uv"

# the app's wheel and the pins
"$APP/Contents/Resources/uv" build --wheel --out-dir "$APP/Contents/Resources/wheels" standin_app
cp installer/requirements.txt "$APP/Contents/Resources/requirements.txt"
echo "$VERSION-$(date -u +%Y%m%d%H%M%S)" > "$APP/Contents/Resources/build_id"

sed -e "s/@APP_NAME@/$NAME/" -e "s/@APP_MODULE@/$MODULE/" -e "s/@BUNDLE_ID@/$BUNDLE_ID/" installer/launcher.sh \
    > "$APP/Contents/MacOS/$NAME"
chmod +x "$APP/Contents/MacOS/$NAME" "$APP/Contents/Resources/uv"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$NAME</string>
  <key>CFBundleDisplayName</key><string>$NAME</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleExecutable</key><string>$NAME</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>15.0</string>
  <key>LSArchitecturePriority</key><array><string>arm64</string></array>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

codesign --force --deep --sign - "$APP"          # ad-hoc: Apple Silicon runs only signed code
codesign --verify --deep --strict "$APP"

# the disk image: the app and a link to Applications, to drag it onto
STAGE="$TMP/dmg" && mkdir -p "$STAGE" && cp -R "$APP" "$STAGE/" && ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "$NAME" -srcfolder "$STAGE" -ov -format UDZO "$DIST/$NAME-$VERSION.dmg" >/dev/null
rm -rf "$TMP"
ls -la "$DIST"
