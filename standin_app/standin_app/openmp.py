"""numba's thread-safe OpenMP layer on macOS.

numba's macOS wheel has its OpenMP layer (numba/np/ufunc/omppool), which loads @rpath/libomp.dylib, but does not
ship that library; without it numba falls back to its workqueue layer, which ends the process when two threads
launch parallel kernels at once. PyTorch and scikit-learn ship a libomp.dylib. probe() tries each way of giving numba
one, each in a fresh process, and reports the layer numba then uses.
"""
import glob
import os
import subprocess
import sys

PROBE = r"""
import ctypes, glob, os, sys
how = sys.argv[1]
if how == "preload-torch":
    import torch
    for path in glob.glob(os.path.join(os.path.dirname(torch.__file__), "lib", "libomp*.dylib")):
        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
if how == "preload-sklearn":
    import sklearn
    for path in glob.glob(os.path.join(os.path.dirname(sklearn.__file__), ".dylibs", "libomp*.dylib")):
        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
try:
    import numba.np.ufunc.omppool  # noqa: F401
    omp = "omppool imports"
except Exception as exc:
    omp = f"omppool fails: {exc!s:.200}"
import numba, numpy as np
@numba.njit(parallel=True)
def f(a):
    s = 0.0
    for i in numba.prange(a.size):
        s += a[i]
    return s
f(np.ones(1000))
print(f"{how}|{numba.threading_layer()}|{omp}")
"""


def torch_libomp():
    import importlib.util

    spec = importlib.util.find_spec("torch")
    if spec is None or not spec.submodule_search_locations:
        return None
    found = glob.glob(os.path.join(spec.submodule_search_locations[0], "lib", "libomp*.dylib"))
    return found[0] if found else None


def python_lib_dirs():
    """Where @rpath may lead from this interpreter: the real executable's ../lib, and sys.base_prefix/lib."""
    dirs = [os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(sys.executable))), "lib"),
            os.path.join(sys.base_prefix, "lib")]
    return list(dict.fromkeys(os.path.normpath(d) for d in dirs))


def _run(how, env=None):
    done = subprocess.run([sys.executable, "-c", PROBE, how], capture_output=True, text=True, env=env)
    line = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""
    if "|" not in line:
        return {"how": how, "layer": None, "detail": f"exit {done.returncode}: {done.stderr.strip()[-400:]}"}
    _how, layer, detail = line.split("|", 2)
    return {"how": how, "layer": layer, "detail": detail}


def probe():
    """[{how, layer, detail}] for: plain; torch's or scikit-learn's libomp preloaded; torch's libomp copied into each
    of python_lib_dirs (removed again after); $DYLD_FALLBACK_LIBRARY_PATH set to torch's lib folder."""
    out = [_run("plain"), _run("preload-torch"), _run("preload-sklearn")]
    lib = torch_libomp()
    if lib:
        for folder in python_lib_dirs():
            target = os.path.join(folder, "libomp.dylib")
            if os.path.exists(target) or not os.path.isdir(folder):
                out.append({"how": f"copy-to {folder}", "layer": None, "detail": "exists or no such folder"})
                continue
            try:
                import shutil

                shutil.copyfile(lib, target)
                result = _run("plain")
                result["how"] = f"copy-to {folder}"
                out.append(result)
            except OSError as exc:
                out.append({"how": f"copy-to {folder}", "layer": None, "detail": str(exc)})
            finally:
                try:
                    os.remove(target)
                except OSError:
                    pass
        env = dict(os.environ, DYLD_FALLBACK_LIBRARY_PATH=os.path.dirname(lib))
        result = _run("plain", env)
        result["how"] = "DYLD_FALLBACK_LIBRARY_PATH"
        out.append(result)
    return out


if __name__ == "__main__":
    for row in probe():
        print(f"{row['how']:60s} {row['layer']!s:10s} {row['detail']}")
