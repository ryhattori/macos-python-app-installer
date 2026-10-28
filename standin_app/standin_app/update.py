"""Updating the installed app from within it: stage the new version and start macos_update.sh, which installs it
once the app has quit and opens the app again.

    python -m standin_app.update WHEEL REQUIREMENTS [--wait-pid PID]

Needs the variables the app's launcher sets (MACAPP_DATA, MACAPP_UV, MACAPP_BUNDLE_ID). The script is the one in
the new version when its wheel brings one, else this version's.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT = "macos_update.sh"
PACKAGE_NAME = "standin-app"
MODULE = "standin_app"


def installed() -> "dict | None":
    """The launcher's variables, when this copy runs from an installed app; else None."""
    data, uv = os.environ.get("MACAPP_DATA", ""), os.environ.get("MACAPP_UV", "")
    if not (data and uv and Path(uv).is_file() and Path(sys.prefix).resolve() == (Path(data) / "env").resolve()):
        return None
    return {"data": data, "uv": uv, "bundle_id": os.environ.get("MACAPP_BUNDLE_ID", "")}


def script_from(wheel: Path) -> bytes:
    """The update script the new version brings, else this version's."""
    try:
        with zipfile.ZipFile(wheel) as archive:
            return archive.read(f"{MODULE}/{SCRIPT}")
    except (KeyError, OSError, zipfile.BadZipFile):
        return (Path(__file__).with_name(SCRIPT)).read_bytes()


def start(wheel: Path, requirements: Path, wait_pid: int, warm: str = "") -> Path:
    """Stages the update and starts its script detached; the script's log."""
    where = installed()
    if where is None:
        raise RuntimeError("only an installed app updates itself (started by its launcher)")
    work = Path(tempfile.mkdtemp(prefix="update-", dir=Path(where["data"])))
    staged = work / wheel.name
    shutil.copy2(wheel, staged)
    shutil.copy2(requirements, work / "requirements.txt")
    script = work / SCRIPT
    script.write_bytes(script_from(staged))
    log = Path(where["data"]) / "update.log"
    env = dict(os.environ, UPD_NAME="StandIn", UPD_DATA=where["data"], UPD_UV=where["uv"],
               UPD_REQUIREMENTS=str(work / "requirements.txt"), UPD_PACKAGE=str(staged),
               UPD_PACKAGE_NAME=PACKAGE_NAME, UPD_MODULE=MODULE, UPD_LOG=str(log), UPD_WAIT_PID=str(wait_pid),
               UPD_WARM=warm, UPD_BUNDLE_ID=where["bundle_id"])
    for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        env.pop(key, None)
    subprocess.Popen(["/bin/bash", str(script)], env=env, start_new_session=True, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="standin_app.update")
    ap.add_argument("wheel", type=Path)
    ap.add_argument("requirements", type=Path)
    ap.add_argument("--wait-pid", type=int, default=os.getppid())
    args = ap.parse_args(argv)
    print("update log:", start(args.wheel, args.requirements, args.wait_pid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
