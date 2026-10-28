#!/bin/bash
# Install an update into a macOS app's Python environment once the app has quit, and open the app again.
#
# The app (its Python) downloads the update, then starts this script detached and quits. The script waits for it to
# end, installs the pinned packages and the new package into a copy of the environment (on APFS a clone: instant,
# no space until files differ), checks the new version imports, and only then puts the copy in place of the
# environment: an update that fails anywhere leaves the app as it was. Settings come from the environment:
#
#   UPD_NAME           the app's name (notifications)
#   UPD_DATA           the folder holding env/ (~/Library/Application Support/<name>)
#   UPD_UV             uv
#   UPD_REQUIREMENTS   the pinned packages (a requirements file)
#   UPD_PACKAGE        the new version: a wheel, or a source folder
#   UPD_PACKAGE_NAME   its distribution name (reinstalled even when its version is unchanged)
#   UPD_MODULE         the module that must import in the new environment
#   UPD_LOG            the log (appended to)
#   UPD_WAIT_PID       the app's process, waited for (optional)
#   UPD_WARM           a module run in the new environment after it is in place (optional; failures ignored)
#   UPD_BUNDLE_ID      the app's bundle identifier, to open it again (optional)
#   UPD_NO_RESTART     set: do not open the app again
#   UPD_QUIET          set: no notifications or alerts (an alert waits for a click: tests)
set -u
: "${UPD_NAME:?}" "${UPD_DATA:?}" "${UPD_UV:?}" "${UPD_REQUIREMENTS:?}" "${UPD_PACKAGE:?}" "${UPD_PACKAGE_NAME:?}"
: "${UPD_MODULE:?}" "${UPD_LOG:?}"
ENV="$UPD_DATA/env"
NEW="$UPD_DATA/env.update"
OLD="$UPD_DATA/env.old"
exec >> "$UPD_LOG" 2>&1
echo "=== $(date) updating $UPD_NAME from $UPD_PACKAGE"

notify() {
    [ -n "${UPD_QUIET:-}" ] && return 0
    /usr/bin/osascript -e "display notification \"$1\" with title \"$UPD_NAME\"" >/dev/null 2>&1 || true
}

reopen() {
    if [ -z "${UPD_NO_RESTART:-}" ] && [ -n "${UPD_BUNDLE_ID:-}" ]; then
        /usr/bin/open -b "$UPD_BUNDLE_ID" || echo "could not open $UPD_BUNDLE_ID"
    fi
}

tidy() {
    # this update's staging folder (the script's own: bash has it open, so it may go), when it is the app's
    local here
    here="$(cd "$(dirname "$0")" && pwd)"
    case "$here" in "$UPD_DATA"/update-*) rm -rf "$here" ;; esac
}

fail() {
    rm -rf "$NEW"
    tidy
    echo "FAILED: $1"
    [ -n "${UPD_QUIET:-}" ] || /usr/bin/osascript -e "display alert \"$UPD_NAME was not updated\" message \"$1. $UPD_NAME is as it was before. Details: $UPD_LOG\"" \
        >/dev/null 2>&1 || true
    reopen
    exit 1
}

give_numba_openmp() {
    # numba's macOS wheel loads @rpath/libomp.dylib for its thread-safe OpenMP layer but does not ship it: a link to
    # PyTorch's in the Python's own lib folder (a link: two copies in one process end it). The link names
    # env/.../torch, which stays the same path across updates; made again in case PyTorch's file name changed.
    local python="$1" lib omp
    lib="$("$python" -c 'import os, sys; print(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(sys.executable))), "lib"))')"
    omp="$("$python" -c 'import glob, os, importlib.util as u; s = u.find_spec("torch"); print((glob.glob(os.path.join(s.submodule_search_locations[0], "lib", "libomp*.dylib")) or [""])[0] if s else "")')"
    if [ -n "$omp" ] && [ -d "$lib" ]; then
        ln -sf "$omp" "$lib/libomp.dylib" && echo "numba's OpenMP: $lib/libomp.dylib -> $omp"
    fi
}

# 1. the app has quit
if [ -n "${UPD_WAIT_PID:-}" ]; then
    for _ in $(seq 1 600); do
        kill -0 "$UPD_WAIT_PID" 2>/dev/null || break
        sleep 1
    done
    kill -0 "$UPD_WAIT_PID" 2>/dev/null && fail "$UPD_NAME did not quit within 10 minutes"
fi
# ... and nothing else runs from its environment (a second window, a job it started)
others="$(pgrep -f "$ENV/bin/python" || true)"
[ -n "$others" ] && fail "other $UPD_NAME processes are still running (process $(echo $others | tr '\n' ' ')): quit them, then update again"

notify "Updating $UPD_NAME..."
# 2. a copy of the environment, the update installed into it
rm -rf "$NEW" "$OLD"
cp -cR "$ENV" "$NEW" 2>/dev/null || { rm -rf "$NEW"; cp -R "$ENV" "$NEW"; } || fail "the environment could not be copied"
echo "--- the pinned packages"
"$UPD_UV" pip install --python "$NEW/bin/python" -r "$UPD_REQUIREMENTS" || fail "the packages could not be installed"
echo "--- $UPD_PACKAGE_NAME"
"$UPD_UV" pip install --python "$NEW/bin/python" --no-deps --reinstall-package "$UPD_PACKAGE_NAME" "$UPD_PACKAGE" \
    || fail "the new version could not be installed"
"$NEW/bin/python" -c "import $UPD_MODULE" || fail "the new version does not start"
# 3. in place of the environment
mv "$ENV" "$OLD" || fail "the environment could not be moved aside"
if ! mv "$NEW" "$ENV"; then
    mv "$OLD" "$ENV"
    fail "the new environment could not be put in place"
fi
rm -rf "$OLD"
give_numba_openmp "$ENV/bin/python"
if [ -n "${UPD_WARM:-}" ]; then
    "$ENV/bin/python" -m "$UPD_WARM" || echo "(the warm-up failed; the app compiles what it needs when first used)"
fi
tidy
echo "=== $(date) updated"
notify "$UPD_NAME is updated."
reopen
exit 0
