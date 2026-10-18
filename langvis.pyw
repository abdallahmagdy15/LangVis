# LangVis — pure-Python port of the Rust app (src/*.rs is the spec, same behavior/constants).
# Run via run.cmd (signed pyw.exe). Stdlib only. Log: %APPDATA%\LangVis\debug.log

import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import winreg
from datetime import datetime

APP_NAME = "LangVis"
LOG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
LOG_PATH = os.path.join(LOG_DIR, "debug.log")
SETTINGS_PATH = os.path.join(LOG_DIR, "settings.json")
SCRIPT_PATH = os.path.abspath(__file__)
ASSETS_DIR = os.path.join(os.path.dirname(SCRIPT_PATH), "assets")

WM_TRAYICON = 0x0401
TIMER_POLL = 1
POLL_MS = 100
MARGIN = 30
FADE_IN_STEP = 40
FADE_OUT_STEP = 35


def log(s):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", newline="\n") as f:
            f.write("<%s> %s\n" % (datetime.now().strftime("%H:%M:%S.%f")[:-3], s))
    except Exception:
        pass


# --- 64-bit-correct types ---

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
HWND = ctypes.c_void_p
HINSTANCE = ctypes.c_void_p
HICON = ctypes.c_void_p
HMENU = ctypes.c_void_p
HKL = ctypes.c_void_p

WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, ctypes.c_uint, WPARAM, LPARAM)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
gdiplus = ctypes.WinDLL("gdiplus", use_last_error=True)


class POINT(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wt.LONG), ("cy", wt.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", HWND),
        ("message", wt.UINT),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", wt.DWORD),
        ("pt", POINT),
    ]


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT),
        ("rcMonitor", wt.RECT),
        ("rcWork", wt.RECT),
        ("dwFlags", wt.DWORD),
    ]


class BLENDFUNCTION(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.UINT),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT),
        ("hWnd", HWND),
        ("uID", wt.UINT),
        ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT),
        ("hIcon", HICON),
        ("szTip", wt.WCHAR * 128),
        ("dwState", wt.DWORD),
        ("dwStateMask", wt.DWORD),
        ("szInfo", wt.WCHAR * 256),
        ("uVersion", wt.UINT),
        ("szInfoTitle", wt.WCHAR * 64),
        ("dwInfoFlags", wt.DWORD),
        ("guidItem", ctypes.c_char * 16),
        ("hBalloonIcon", HICON),
    ]


class GdiplusStartupInput(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", wt.UINT),
        ("DebugEventCallback", ctypes.c_void_p),
        ("SuppressBackgroundThread", wt.BOOL),
        ("SuppressExternalCodecs", wt.BOOL),
    ]


class GpRect(ctypes.Structure):
    _fields_ = [("X", ctypes.c_int), ("Y", ctypes.c_int), ("Width", ctypes.c_int), ("Height", ctypes.c_int)]


class RectF(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("w", ctypes.c_float), ("h", ctypes.c_float)]


class BitmapData(ctypes.Structure):
    _fields_ = [
        ("Width", wt.UINT),
        ("Height", wt.UINT),
        ("Stride", ctypes.c_int),
        ("PixelFormat", ctypes.c_int),
        ("Scan0", ctypes.c_void_p),
        ("Reserved", ctypes.c_size_t),
    ]


# --- argtypes/restype on every call ---

user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.RegisterClassW.restype = wt.ATOM
user32.CreateWindowExW.argtypes = [
    wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    HWND, HMENU, HINSTANCE, ctypes.c_void_p,
]
user32.CreateWindowExW.restype = HWND
user32.DefWindowProcW.argtypes = [HWND, wt.UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterWindowMessageW.argtypes = [wt.LPCWSTR]
user32.RegisterWindowMessageW.restype = wt.UINT
user32.RegisterShellHookWindow.argtypes = [HWND]
user32.RegisterShellHookWindow.restype = wt.BOOL
user32.DeregisterShellHookWindow.argtypes = [HWND]
user32.DeregisterShellHookWindow.restype = wt.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = wt.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = HWND
user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetKeyboardLayout.argtypes = [wt.DWORD]
user32.GetKeyboardLayout.restype = HKL
user32.GetDC.argtypes = [HWND]
user32.GetDC.restype = ctypes.c_void_p
user32.ReleaseDC.argtypes = [HWND, ctypes.c_void_p]
user32.ReleaseDC.restype = ctypes.c_int
user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL
user32.SetTimer.argtypes = [HWND, ctypes.c_size_t, wt.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_size_t
user32.KillTimer.argtypes = [HWND, ctypes.c_size_t]
user32.KillTimer.restype = wt.BOOL
user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
user32.ShowWindow.restype = wt.BOOL
user32.DestroyWindow.argtypes = [HWND]
user32.DestroyWindow.restype = wt.BOOL
user32.UpdateLayeredWindow.argtypes = [
    HWND, ctypes.c_void_p,
    ctypes.POINTER(POINT), ctypes.POINTER(SIZE),
    ctypes.c_void_p, ctypes.POINTER(POINT),
    wt.DWORD, ctypes.POINTER(BLENDFUNCTION), wt.DWORD,
]
user32.UpdateLayeredWindow.restype = wt.BOOL
user32.MonitorFromWindow.argtypes = [HWND, wt.DWORD]
user32.MonitorFromWindow.restype = ctypes.c_void_p
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wt.BOOL
user32.LoadIconW.argtypes = [HINSTANCE, ctypes.c_void_p]
user32.LoadIconW.restype = HICON
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.SetForegroundWindow.argtypes = [HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.CreatePopupMenu.argtypes = []
user32.CreatePopupMenu.restype = HMENU
user32.AppendMenuW.argtypes = [HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
user32.AppendMenuW.restype = wt.BOOL
user32.TrackPopupMenu.argtypes = [HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, HWND, HMENU]
user32.TrackPopupMenu.restype = wt.BOOL
user32.DestroyMenu.argtypes = [HMENU]
user32.DestroyMenu.restype = wt.BOOL

gdi32.CreateDIBSection.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wt.UINT,
    ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, wt.UINT,
]
gdi32.CreateDIBSection.restype = ctypes.c_void_p
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.SelectObject.restype = ctypes.c_void_p
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
gdi32.DeleteObject.restype = wt.BOOL
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
gdi32.DeleteDC.restype = wt.BOOL

kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = HINSTANCE
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
kernel32.CreateMutexW.restype = ctypes.c_void_p

shell32.Shell_NotifyIconW.argtypes = [wt.UINT, ctypes.c_void_p]
shell32.Shell_NotifyIconW.restype = wt.BOOL

gdiplus.GdiplusStartup.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(GdiplusStartupInput), ctypes.c_void_p]
gdiplus.GdiplusStartup.restype = ctypes.c_int
gdiplus.GdiplusShutdown.argtypes = [ctypes.c_size_t]
gdiplus.GdiplusShutdown.restype = None
gdiplus.GdipCreateBitmapFromFile.argtypes = [wt.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateBitmapFromFile.restype = ctypes.c_int
gdiplus.GdipGetImageWidth.argtypes = [ctypes.c_void_p, ctypes.POINTER(wt.UINT)]
gdiplus.GdipGetImageWidth.restype = ctypes.c_int
gdiplus.GdipGetImageHeight.argtypes = [ctypes.c_void_p, ctypes.POINTER(wt.UINT)]
gdiplus.GdipGetImageHeight.restype = ctypes.c_int
gdiplus.GdipCreateBitmapFromScan0.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateBitmapFromScan0.restype = ctypes.c_int
gdiplus.GdipGetImageGraphicsContext.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipGetImageGraphicsContext.restype = ctypes.c_int
gdiplus.GdipSetInterpolationMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetInterpolationMode.restype = ctypes.c_int
gdiplus.GdipDrawImageRectI.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdiplus.GdipDrawImageRectI.restype = ctypes.c_int
gdiplus.GdipDeleteGraphics.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteGraphics.restype = ctypes.c_int
gdiplus.GdipBitmapLockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(GpRect), wt.UINT, ctypes.c_int, ctypes.POINTER(BitmapData)]
gdiplus.GdipBitmapLockBits.restype = ctypes.c_int
gdiplus.GdipBitmapUnlockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(BitmapData)]
gdiplus.GdipBitmapUnlockBits.restype = ctypes.c_int
gdiplus.GdipDisposeImage.argtypes = [ctypes.c_void_p]
gdiplus.GdipDisposeImage.restype = ctypes.c_int
gdiplus.GdipSetSmoothingMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetSmoothingMode.restype = ctypes.c_int
gdiplus.GdipSetTextRenderingHint.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetTextRenderingHint.restype = ctypes.c_int
gdiplus.GdipCreateFontFamilyFromName.argtypes = [wt.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateFontFamilyFromName.restype = ctypes.c_int
gdiplus.GdipCreateFont.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateFont.restype = ctypes.c_int
gdiplus.GdipCreateSolidFill.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateSolidFill.restype = ctypes.c_int
gdiplus.GdipCreateStringFormat.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateStringFormat.restype = ctypes.c_int
gdiplus.GdipSetStringFormatAlign.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetStringFormatAlign.restype = ctypes.c_int
gdiplus.GdipSetStringFormatLineAlign.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdiplus.GdipSetStringFormatLineAlign.restype = ctypes.c_int
gdiplus.GdipDrawString.argtypes = [ctypes.c_void_p, wt.LPCWSTR, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(RectF), ctypes.c_void_p, ctypes.c_void_p]
gdiplus.GdipDrawString.restype = ctypes.c_int
gdiplus.GdipDeleteFont.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteFont.restype = ctypes.c_int
gdiplus.GdipDeleteFontFamily.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteFontFamily.restype = ctypes.c_int
gdiplus.GdipDeleteStringFormat.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteStringFormat.restype = ctypes.c_int
gdiplus.GdipDeleteBrush.argtypes = [ctypes.c_void_p]
gdiplus.GdipDeleteBrush.restype = ctypes.c_int
gdiplus.GdipCreateHICONFromBitmap.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gdiplus.GdipCreateHICONFromBitmap.restype = ctypes.c_int


# --- settings (port of settings.rs) ---

DEFAULTS = {
    "duration_seconds": 0.7,
    "use_top_corners": False,
    "scale": 0.28,
    "opacity": 0.5,
    "run_on_startup": False,
}


class Settings:
    def __init__(self):
        data = {}
        try:
            with open(SETTINGS_PATH, "r") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
        self.duration_seconds = self._num(data, "duration_seconds")
        self.use_top_corners = self._bool(data, "use_top_corners")
        self.scale = self._num(data, "scale")
        self.opacity = self._num(data, "opacity")
        self.run_on_startup = self._bool(data, "run_on_startup")

    @staticmethod
    def _num(d, k):
        try:
            return float(d[k])
        except Exception:
            return DEFAULTS[k]

    @staticmethod
    def _bool(d, k):
        v = d.get(k)
        return v if isinstance(v, bool) else DEFAULTS[k]

    def save(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            d = {
                "duration_seconds": self.duration_seconds,
                "use_top_corners": self.use_top_corners,
                "scale": self.scale,
                "opacity": self.opacity,
                "run_on_startup": self.run_on_startup,
            }
            with open(SETTINGS_PATH, "w") as f:
                json.dump(d, f, indent=2)
        except Exception as e:
            log("settings save failed: %r" % (e,))


# --- startup registry (port of settings.rs registry part, via winreg) ---

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launcher_path():
    cands = []
    exe = getattr(sys, "executable", "") or ""
    if exe:
        d, base = os.path.split(exe)
        if base.lower() == "python.exe":
            exe = os.path.join(d, "pythonw.exe")
        cands.append(exe)
    cands.append(os.path.join(sys.base_prefix, "pythonw.exe"))
    cands.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Launcher", "pyw.exe"))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return exe or "pythonw.exe"


def startup_command():
    return '"%s" "%s"' % (_launcher_path(), SCRIPT_PATH)


def is_startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_startup(enable):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                cmd = startup_command()
                log("startup cmd: %s" % cmd)
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                winreg.DeleteValue(k, APP_NAME)
    except OSError as e:
        log("set_startup(%s) failed: %r" % (enable, e))


# --- PNG load via GDI+ (port of png.rs/WIC) ---

GDIP_PXFMT_32PARGB = 0x000E200B
INTERP_HIGH_QUALITY_BICUBIC = 7
IMAGE_LOCK_MODE_READ = 1


def gdiplus_init():
    token = ctypes.c_size_t()
    inp = GdiplusStartupInput()
    inp.GdiplusVersion = 1
    st = gdiplus.GdiplusStartup(ctypes.byref(token), ctypes.byref(inp), None)
    if st != 0:
        log("FATAL GdiplusStartup status=%d" % st)
        return None
    return token


def load_png(path, scale):
    if not os.path.isfile(path):
        log("png missing: %s" % path)
        return None
    src = ctypes.c_void_p()
    dst = ctypes.c_void_p()
    g = ctypes.c_void_p()
    w = wt.UINT()
    h = wt.UINT()
    bd = BitmapData()
    try:
        if gdiplus.GdipCreateBitmapFromFile(path, ctypes.byref(src)) != 0:
            log("GdipCreateBitmapFromFile failed: %s" % path)
            return None
        if gdiplus.GdipGetImageWidth(src, ctypes.byref(w)) != 0:
            return None
        if gdiplus.GdipGetImageHeight(src, ctypes.byref(h)) != 0:
            return None
        tw = max(1, int(w.value * scale))
        th = max(1, int(h.value * scale))
        if gdiplus.GdipCreateBitmapFromScan0(tw, th, 0, GDIP_PXFMT_32PARGB, None, ctypes.byref(dst)) != 0:
            log("GdipCreateBitmapFromScan0 failed")
            return None
        if gdiplus.GdipGetImageGraphicsContext(dst, ctypes.byref(g)) != 0:
            return None
        gdiplus.GdipSetInterpolationMode(g, INTERP_HIGH_QUALITY_BICUBIC)
        gdiplus.GdipDrawImageRectI(g, src, 0, 0, tw, th)
        gdiplus.GdipDeleteGraphics(g)
        g = ctypes.c_void_p()
        rect = GpRect(0, 0, tw, th)
        if gdiplus.GdipBitmapLockBits(dst, ctypes.byref(rect), IMAGE_LOCK_MODE_READ, GDIP_PXFMT_32PARGB, ctypes.byref(bd)) != 0:
            log("GdipBitmapLockBits failed")
            return None
        row = tw * 4
        stride = bd.Stride if bd.Stride > row else row
        scan0 = bd.Scan0 or 0
        buf = ctypes.create_string_buffer(row * th)
        for y in range(th):
            ctypes.memmove(ctypes.addressof(buf) + y * row, scan0 + y * stride, row)
        gdiplus.GdipBitmapUnlockBits(dst, ctypes.byref(bd))
        return tw, th, buf
    finally:
        if g.value:
            gdiplus.GdipDeleteGraphics(g)
        if dst.value:
            gdiplus.GdipDisposeImage(dst)
        if src.value:
            gdiplus.GdipDisposeImage(src)


# --- overlay (port of overlay.rs) ---

HIDDEN, FADING_IN, HOLDING, FADING_OUT = 0, 1, 2, 3


class Overlay:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.width = 1
        self.height = 1
        self.pos_x = 0
        self.pos_y = 0
        self.memdc = None
        self.hbitmap = None
        self.alpha = 0
        self.max_alpha = 153
        self.hold_frames_left = 0
        self.state = HIDDEN

    def show(self, lang):
        path = os.path.join(ASSETS_DIR, lang + ".png")
        loaded = load_png(path, SETTINGS.scale)
        if loaded is None:
            return
        w, h, pixels = loaded
        self.width = w
        self.height = h
        self.max_alpha = int(255 * SETTINGS.opacity)
        self.create_bitmap(w, h, pixels)
        self.position(lang == "AR")
        if self.state == HIDDEN:
            self.alpha = 0
            user32.SetWindowPos(
                self.hwnd, None, self.pos_x, self.pos_y, self.width, self.height,
                0x10 | 0x40 | 0x4,
            )
        self.state = FADING_IN
        self.hold_frames_left = int(SETTINGS.duration_seconds * 62.0)
        self.render()
        user32.SetTimer(self.hwnd, 2, 16, None)

    def create_bitmap(self, w, h, pixels):
        if self.memdc:
            gdi32.DeleteDC(self.memdc)
            self.memdc = None
        if self.hbitmap:
            gdi32.DeleteObject(self.hbitmap)
            self.hbitmap = None
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        bmi.bmiHeader.biSizeImage = w * h * 4
        hdc = user32.GetDC(None)
        bits = ctypes.c_void_p()
        self.hbitmap = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        if self.hbitmap and bits.value:
            ctypes.memmove(bits.value, pixels, len(pixels))
        self.memdc = gdi32.CreateCompatibleDC(hdc)
        gdi32.SelectObject(self.memdc, self.hbitmap)
        user32.ReleaseDC(None, hdc)

    def position(self, right_aligned):
        fg = user32.GetForegroundWindow()
        mon = user32.MonitorFromWindow(fg, 2)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(mon, ctypes.byref(mi))
        if right_aligned:
            self.pos_x = mi.rcWork.right - self.width - MARGIN
        else:
            self.pos_x = mi.rcWork.left + MARGIN
        if SETTINGS.use_top_corners:
            self.pos_y = mi.rcWork.top + MARGIN
        else:
            self.pos_y = mi.rcWork.bottom - self.height - MARGIN

    def render(self):
        if not self.hbitmap:
            return
        blend = BLENDFUNCTION()
        blend.BlendOp = 0
        blend.BlendFlags = 0
        blend.SourceConstantAlpha = self.alpha & 0xFF
        blend.AlphaFormat = 1
        pt_dst = POINT(self.pos_x, self.pos_y)
        pt_src = POINT(0, 0)
        size = SIZE(self.width, self.height)
        hdc = user32.GetDC(None)
        user32.UpdateLayeredWindow(
            self.hwnd, hdc,
            ctypes.byref(pt_dst), ctypes.byref(size),
            self.memdc, ctypes.byref(pt_src),
            0, ctypes.byref(blend), 2,
        )
        user32.ReleaseDC(None, hdc)

    def animate_frame(self):
        if self.state == HIDDEN:
            return False
        if self.state == FADING_IN:
            self.alpha = min(self.alpha + FADE_IN_STEP, 255)
            if self.alpha >= self.max_alpha:
                self.alpha = self.max_alpha
                self.state = HOLDING
            self.render()
            return True
        if self.state == HOLDING:
            if self.hold_frames_left > 0:
                self.hold_frames_left -= 1
                return True
            self.state = FADING_OUT
            return self.animate_frame()
        self.alpha = max(self.alpha - FADE_OUT_STEP, 0)
        if self.alpha <= FADE_OUT_STEP:
            self.alpha = 0
            self.state = HIDDEN
            user32.ShowWindow(self.hwnd, 0)
            return False
        self.render()
        return True


# --- tray (port of tray.rs; language glyph "Aع" drawn with GDI+) ---

NID = None
ICON_ARGB = 0xFF3DA5FF  # sky blue


def create_app_icon():
    # "A" (Latin) + "ع" (Arabic) language glyph, antialiased, on a transparent 32x32 bitmap.
    bmp = ctypes.c_void_p()
    if gdiplus.GdipCreateBitmapFromScan0(32, 32, 0, GDIP_PXFMT_32PARGB, None, ctypes.byref(bmp)) != 0:
        return None
    gr = ctypes.c_void_p()
    fam = ctypes.c_void_p()
    font = ctypes.c_void_p()
    brush = ctypes.c_void_p()
    fmt = ctypes.c_void_p()
    hicon = ctypes.c_void_p()
    try:
        if gdiplus.GdipGetImageGraphicsContext(bmp, ctypes.byref(gr)) != 0:
            return None
        gdiplus.GdipSetSmoothingMode(gr, 4)        # AntiAlias
        gdiplus.GdipSetTextRenderingHint(gr, 4)    # AntiAliasGridFit
        if gdiplus.GdipCreateFontFamilyFromName("Segoe UI", None, ctypes.byref(fam)) != 0:
            return None
        gdiplus.GdipCreateFont(fam, 21.0, 1, 2, ctypes.byref(font))  # Bold, UnitPixel
        gdiplus.GdipCreateSolidFill(ICON_ARGB, ctypes.byref(brush))
        gdiplus.GdipCreateStringFormat(0, 0, ctypes.byref(fmt))
        gdiplus.GdipSetStringFormatAlign(fmt, 1)       # center
        gdiplus.GdipSetStringFormatLineAlign(fmt, 1)   # middle
        rc_a = RectF(-2.0, -2.0, 22.0, 36.0)
        rc_ayn = RectF(12.0, -2.0, 22.0, 36.0)
        gdiplus.GdipDrawString(gr, "A", -1, font, ctypes.byref(rc_a), fmt, brush)
        gdiplus.GdipDrawString(gr, "ع", -1, font, ctypes.byref(rc_ayn), fmt, brush)
        if gdiplus.GdipCreateHICONFromBitmap(bmp, ctypes.byref(hicon)) != 0:
            return None
        return hicon.value
    finally:
        if fmt.value:
            gdiplus.GdipDeleteStringFormat(fmt)
        if brush.value:
            gdiplus.GdipDeleteBrush(brush)
        if font.value:
            gdiplus.GdipDeleteFont(font)
        if fam.value:
            gdiplus.GdipDeleteFontFamily(fam)
        if gr.value:
            gdiplus.GdipDeleteGraphics(gr)
        gdiplus.GdipDisposeImage(bmp)


def add_tray_icon(hwnd):
    global NID
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = 0x1 | 0x2 | 0x4
    nid.uCallbackMessage = WM_TRAYICON
    icon = None
    try:
        icon = create_app_icon()
    except Exception as e:
        log("create_app_icon failed: %r" % (e,))
    nid.hIcon = icon if icon else user32.LoadIconW(None, 32512)
    nid.szTip = APP_NAME
    NID = nid
    if not shell32.Shell_NotifyIconW(0, ctypes.byref(nid)):
        log("Shell_NotifyIconW NIM_ADD failed gle=%d" % ctypes.get_last_error())


def remove_tray_icon():
    global NID
    if NID is not None:
        shell32.Shell_NotifyIconW(2, ctypes.byref(NID))
        NID = None


def show_context_menu(hwnd):
    menu = user32.CreatePopupMenu()
    if not menu:
        return
    startup_flags = 0x8 if is_startup_enabled() else 0
    user32.AppendMenuW(menu, startup_flags, 1002, "Run on Startup")
    user32.AppendMenuW(menu, 0, 1003, "Reload Assets")
    user32.AppendMenuW(menu, 0x800, 0, "")
    user32.AppendMenuW(menu, 0, 1004, "Exit")
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    user32.SetForegroundWindow(hwnd)
    user32.TrackPopupMenu(menu, 0x2 | 0x20, pt.x, pt.y, 0, hwnd, None)
    user32.DestroyMenu(menu)


# --- globals ---

SETTINGS = None
OVERLAY = None
LAST_LANG_ID = 0xFFFF
SHELL_MSG = 0
_WNDPROC_REF = None


# --- detection (port of main.rs, spike-proven decode) ---

def check_language():
    global LAST_LANG_ID
    if OVERLAY is None or SETTINGS is None:
        return
    fg = user32.GetForegroundWindow()
    if not fg:
        return
    tid = user32.GetWindowThreadProcessId(fg, None)
    if not tid:
        return
    hkl = user32.GetKeyboardLayout(tid)
    lang_id = (hkl or 0) & 0xFFFF
    if lang_id == LAST_LANG_ID:
        return
    LAST_LANG_ID = lang_id
    lang = "AR" if (lang_id & 0xFF) == 0x01 else "EN"
    log("LANG 0x%04X -> %s" % (lang_id, lang))
    OVERLAY.show(lang)


def handle_command(hwnd, cmd):
    global LAST_LANG_ID
    if cmd == 1002:
        enable = not SETTINGS.run_on_startup
        SETTINGS.run_on_startup = enable
        SETTINGS.save()
        set_startup(enable)
    elif cmd == 1003:
        LAST_LANG_ID = 0xFFFF
        check_language()
    elif cmd == 1004:
        remove_tray_icon()
        user32.DestroyWindow(hwnd)


def wnd_proc(hwnd, msg, wp, lp):
    try:
        if msg == 0x0113:
            if wp == TIMER_POLL:
                check_language()
            elif wp == 2 and OVERLAY is not None:
                keep = OVERLAY.animate_frame()
                if not keep:
                    user32.KillTimer(hwnd, 2)
            return 0
        if msg == WM_TRAYICON:
            if (lp & 0xFFFF) == 0x0205:
                show_context_menu(hwnd)
            return 0
        if msg == 0x0111:
            handle_command(hwnd, wp & 0xFFFF)
            return 0
        if msg == 0x0002:
            remove_tray_icon()
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)
    except Exception as e:
        log("wndproc error msg=0x%X: %r" % (msg, e))
        return 0


def main():
    global SETTINGS, OVERLAY, SHELL_MSG, LAST_LANG_ID, _WNDPROC_REF

    kernel32.CreateMutexW(None, False, "LangVis_SingleInstance_7B2F9A4C")
    if ctypes.get_last_error() == 183:
        log("already running, exiting")
        sys.exit(0)

    token = gdiplus_init()
    if token is None:
        return

    hinst = kernel32.GetModuleHandleW(None)
    if not hinst:
        log("FATAL GetModuleHandleW gle=%d" % ctypes.get_last_error())
        return

    _WNDPROC_REF = WNDPROC(wnd_proc)
    wc = WNDCLASS()
    wc.lpfnWndProc = _WNDPROC_REF
    wc.hInstance = hinst
    wc.lpszClassName = "LangVisWindow"
    if user32.RegisterClassW(ctypes.byref(wc)) == 0:
        log("FATAL RegisterClassW gle=%d" % ctypes.get_last_error())
        return

    ex_style = 0x80000 | 0x20 | 0x80 | 0x8000000 | 0x8
    hwnd = user32.CreateWindowExW(
        ex_style, "LangVisWindow", APP_NAME, 0x80000000,
        0, 0, 1, 1, None, None, hinst, None,
    )
    if not hwnd:
        log("FATAL CreateWindowExW gle=%d" % ctypes.get_last_error())
        return

    SETTINGS = Settings()
    OVERLAY = Overlay(hwnd)

    fg = user32.GetForegroundWindow()
    if fg:
        tid = user32.GetWindowThreadProcessId(fg, None)
        hkl = user32.GetKeyboardLayout(tid) if tid else None
        LAST_LANG_ID = (hkl or 0) & 0xFFFF
    else:
        LAST_LANG_ID = 0xFFFF

    add_tray_icon(hwnd)
    user32.SetTimer(hwnd, TIMER_POLL, POLL_MS, None)
    log("START python=%s poll=%dms" % (sys.executable, POLL_MS))

    msg = MSG()
    while True:
        ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if ret == 0 or ret == -1:
            if ret == -1:
                log("GetMessageW error gle=%d" % ctypes.get_last_error())
            break
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    gdiplus.GdiplusShutdown(token)
    log("exit")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log("FATAL %r" % (e,))
