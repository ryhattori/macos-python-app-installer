"""The app's name in the macOS menu bar and Dock.

The launcher starts the environment's Python, which macOS names the app after ("python"): before the first window,
the name is set in the main bundle's Info dictionary (CFBundleName), as PyObjC would do it, through the Objective-C
runtime with ctypes. Nothing elsewhere than macOS.
"""
import ctypes
import ctypes.util
import sys


def set_app_name(name: str) -> bool:
    """True when the name was set (call before the QApplication)."""
    if sys.platform != "darwin":
        return False
    try:
        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        ctypes.cdll.LoadLibrary(ctypes.util.find_library("Foundation"))
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p))
        send_str = ctypes.cast(objc.objc_msgSend,
                               ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p))
        send_two = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p,
                                                                     ctypes.c_void_p, ctypes.c_void_p))
        sel = objc.sel_registerName

        def ns(text):
            return send_str(objc.objc_getClass(b"NSString"), sel(b"stringWithUTF8String:"), text.encode("utf-8"))

        bundle = send(objc.objc_getClass(b"NSBundle"), sel(b"mainBundle"))
        info = send(bundle, sel(b"localizedInfoDictionary")) or send(bundle, sel(b"infoDictionary"))
        if not info:
            return False
        for key in ("CFBundleName", "CFBundleDisplayName"):
            send_two(info, sel(b"setObject:forKey:"), ns(name), ns(key))
        return True
    except Exception:
        return False
