"""The stand-in app: a window that reports what it found (Python, PyTorch and its Apple GPU, numba's threading
layer, PySide6), as a packaged scientific GUI app would need it.

    python -m standin_app                  # the window
    python -m standin_app --selftest DIR   # the window for a moment, its picture and a report.json in DIR
"""
import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path


def report() -> dict:
    out = {"python": sys.version.split()[0], "executable": sys.executable, "platform": platform.platform(),
           "machine": platform.machine()}
    t0 = time.perf_counter()
    import torch

    out["torch"] = torch.__version__
    out["mps_available"] = bool(torch.backends.mps.is_available())
    if out["mps_available"]:
        x = torch.randn(512, 512, device="mps")
        out["mps_matmul_ok"] = bool(torch.isfinite((x @ x).cpu()).all())
    import numba
    import numpy as np

    @numba.njit(parallel=True)
    def total(a):
        s = 0.0
        for i in numba.prange(a.size):
            s += a[i]
        return s

    out["numba"] = numba.__version__
    out["numba_parallel_ok"] = float(total(np.ones(10_000))) == 10_000.0
    out["numba_threading_layer"] = numba.threading_layer()
    import PySide6

    out["pyside6"] = PySide6.__version__
    out["imports_s"] = round(time.perf_counter() - t0, 2)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="standin_app")
    parser.add_argument("--selftest", metavar="DIR", help="show the window briefly, save its picture and report.json")
    args = parser.parse_args(argv)
    info = report()
    from PySide6 import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Stand-in app")
    text = QtWidgets.QPlainTextEdit(json.dumps(info, indent=1))
    text.setReadOnly(True)
    window.setCentralWidget(text)
    window.resize(720, 480)
    window.show()
    if args.selftest:
        folder = Path(args.selftest)
        folder.mkdir(parents=True, exist_ok=True)

        def finish():
            info["device_pixel_ratio"] = window.devicePixelRatioF()
            info["screen"] = app.primaryScreen().name() if app.primaryScreen() else None
            window.grab().save(str(folder / "window.png"))
            (folder / "report.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
            app.quit()

        QtCore.QTimer.singleShot(2000, finish)
    print(json.dumps(info), flush=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
