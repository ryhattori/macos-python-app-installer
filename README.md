# macOS installer for a Python GUI app

A test bed for packaging a Python scientific GUI application (PySide6, PyTorch, numba) for macOS on Apple Silicon:

- `installer/build_dmg.sh` builds `StandIn.app` and a `.dmg`. The app holds [uv](https://github.com/astral-sh/uv), a
  pinned `requirements.txt` and the app's wheel; it is ad-hoc signed (no Developer ID).
- `installer/launcher.sh` is the app's executable. Its first launch sets up Python 3.11 and the pinned packages in
  `~/Library/Application Support/StandIn`; later launches start at once. An update of the app sets them up again.
- `standin_app` is a stand-in application: a window reporting what it found (PyTorch and the Apple GPU, numba's
  threading layer, PySide6). `python -m standin_app.openmp` reports which way, if any, gives numba its thread-safe
  OpenMP layer: numba's macOS wheel loads `@rpath/libomp.dylib` but does not ship it.
- `.github/workflows/macos.yml` builds the disk image on GitHub's macOS runner, installs from it as a user would,
  launches the app twice, and keeps the reports, a screenshot and the disk image as the run's artifact.

## Opening the unsigned app

macOS blocks an app from an unidentified developer the first time: open it, then **System Settings > Privacy &
Security > Open Anyway**.
