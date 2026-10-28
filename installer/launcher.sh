#!/bin/bash
# The app's executable (Contents/MacOS/<name>). The first launch -- and the first after an update of the app -- sets
# up the Python environment in ~/Library/Application Support/<name>: uv (inside the app) installs Python 3.11 and
# the pinned packages; later launches start the app at once. Arguments are passed to the app.
set -u
NAME="@APP_NAME@"
MODULE="@APP_MODULE@"
CONTENTS="$(cd "$(dirname "$0")/.." && pwd)"
RES="$CONTENTS/Resources"
DATA="$HOME/Library/Application Support/$NAME"
ENV="$DATA/env"
LOG="$DATA/setup.log"
BUILD="$(cat "$RES/build_id")"
mkdir -p "$DATA"

say() {   # a notification; nothing when there is no GUI session
    /usr/bin/osascript -e "display notification \"$1\" with title \"$NAME\"" >/dev/null 2>&1 || true
}

if [ ! -x "$ENV/bin/python" ] || [ "$(cat "$ENV/.build_id" 2>/dev/null)" != "$BUILD" ]; then
    say "Setting up $NAME (first launch, a few minutes)..."
    {
        echo "=== $(date) setting up build $BUILD"
        export UV_PYTHON_INSTALL_DIR="$DATA/python" UV_CACHE_DIR="$DATA/cache" UV_NO_CONFIG=1
        "$RES/uv" python install 3.11 --no-bin &&
        rm -rf "$ENV.new" &&
        "$RES/uv" venv --python 3.11 "$ENV.new" &&
        "$RES/uv" pip install --python "$ENV.new/bin/python" -r "$RES/requirements.txt" &&
        "$RES/uv" pip install --python "$ENV.new/bin/python" --no-deps "$RES"/wheels/*.whl &&
        echo "$BUILD" > "$ENV.new/.build_id" &&
        rm -rf "$ENV" && mv "$ENV.new" "$ENV"
    } >> "$LOG" 2>&1
    if [ ! -x "$ENV/bin/python" ] || [ "$(cat "$ENV/.build_id" 2>/dev/null)" != "$BUILD" ]; then
        /usr/bin/osascript -e "display alert \"$NAME could not be set up\" message \"See $LOG\"" >/dev/null 2>&1 \
            || echo "$NAME could not be set up: see $LOG" >&2
        exit 1
    fi
    say "$NAME is ready."
fi
exec "$ENV/bin/python" -m "$MODULE" "$@"
