"""Zip an app bundle as a build on another system would (Windows, Linux): no macOS tools, no signature -- the files
written straight into the zip with their macOS permissions (the launcher and uv executable).

    python installer/zip_app.py dist/StandIn.app dist/StandIn-unsigned.zip
"""
import os
import sys
import zipfile
from pathlib import Path


def write_zip(path: Path, files: dict) -> None:
    """``files``: {path in the zip: (bytes, executable)}; folders are entered too, with macOS permissions."""
    folders = sorted({str(Path(name).parent).replace("\\", "/") for name in files} - {"."})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        every = set()
        for folder in folders:
            parts = folder.split("/")
            every.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
        for folder in sorted(every):
            entry = zipfile.ZipInfo(folder + "/")
            entry.create_system = 3                  # unix: the permissions below are read
            entry.external_attr = (0o40755 << 16) | 0x10
            archive.writestr(entry, b"")
        for name, (data, executable) in sorted(files.items()):
            entry = zipfile.ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = ((0o100755 if executable else 0o100644) << 16)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)


def main(app: str, out: str) -> int:
    app = Path(app)
    files = {}
    for path in app.rglob("*"):
        if path.is_file() and "_CodeSignature" not in path.parts:       # unsigned, as built elsewhere
            name = f"{app.name}/{path.relative_to(app).as_posix()}"
            files[name] = (path.read_bytes(), os.access(path, os.X_OK))
    write_zip(Path(out), files)
    print(f"{out}: {len(files)} files, executable: {[n for n, (_, x) in files.items() if x]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
