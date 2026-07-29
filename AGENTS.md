# LangVis

Windows keyboard-language overlay. Rust + Win32. Shows a glassy PNG briefly when the user switches keyboard layout (AR bottom-right, EN bottom-left).

## Build & run

```powershell
# Cargo is NOT in system PATH on this machine — prefix every session:
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"

cargo build --release
```

Binary lands in `target/release/langvis.exe`. **Copy it to project root** next to `assets/` before running — the exe resolves PNGs relative to `current_exe()`:

```powershell
Copy-Item target/release/langvis.exe langvis.exe -Force
```

Then launch: `langvis.exe` (no args). A tray icon appears; right-click for menu.

## Architecture

Single-threaded Win32 message loop, no async runtime.

| File | Role |
|---|---|
| `main.rs` | Entry, window class, message loop, 50ms polling timer, tray-message dispatch. Global state in `static mut APP: Option<AppState>` (single-threaded, no Send/Sync needed). |
| `overlay.rs` | Layered window rendering via `UpdateLayeredWindow` + per-pixel alpha. PNG → DIB section → blend. Animation state machine: Hidden → FadingIn → Holding → FadingOut → Hidden. |
| `png.rs` | WIC PNG decoder: load → `IWICBitmapScaler` → format-convert to `GUID_WICPixelFormat32bppPBGRA` (premultiplied BGRA) → `Vec<u8>`. |
| `tray.rs` | `Shell_NotifyIconW` + popup menu. Custom blue-circle icon generated via `CreateIconIndirect` (raw pixel buffer, no resource file). |
| `settings.rs` | `UserSettings` JSON at `%APPDATA%/LangVis/settings.json`. Startup registry (`HKCU\...\Run\LangVis`). |

`build.rs` is a no-op stub — safe to delete.

## Critical Win32 API notes (windows crate 0.61)

These cost significant debugging time:

- **`GetDC(None)` returns `HDC`**, but `CreateDIBSection` and `CreateCompatibleDC` expect `Option<HDC>` — use `.into()` to convert.
- **`SetTimer` / `KillTimer` / `PostMessageW`** take `Option<HWND>` — wrap in `Some()`.
- **`CreateMutexW`** takes 3 args: `(attrs: Option<*const SA>, binitialowner: bool, name)`. Needs `Win32_Security` feature for `SECURITY_ATTRIBUTES`.
- **`GetMessageW`** not `GetMessage` (which doesn't exist). Returns `BOOL` — check `.0 > 0`, not `.into()` (−1 on error is truthy).
- **`GetLastError`** is `unsafe` — wrap in `unsafe {}`.
- **`WM_USER`** is `u32`, not a tuple struct. `WM_USER + 1` works directly.
- **`Result` conflict**: importing `windows::core::*` brings in `windows::core::Result<T>` (1 generic). Use `std::result::Result<T, E>` or `windows::core::Result<T>` explicitly.
- **`AC_SRC_OVER` / `AC_SRC_ALPHA`** are bare `u32` constants. Use `as u8` for `BLENDFUNCTION` fields.
- **Feature flags are granular**: every Win32 sub-namespace needs its own feature in `Cargo.toml`. A missing feature = compile error "cannot find function". See current list in `Cargo.toml`.

## Detection mechanism

Polls every 50ms via `WM_TIMER` (timer ID 1). **Must query the foreground window's thread**, not thread 0:

```
fg  = GetForegroundWindow()
tid = GetWindowThreadProcessId(fg)
hkl = GetKeyboardLayout(tid)       // foreground app's layout
```

Thread 0 = the overlay app's own thread — its layout never changes. This was a bug in an earlier C# version.

Arabic: `(lang_id & 0xFF) == 0x01`. Everything else → "EN". AR positions bottom-right, EN bottom-left, on the **monitor of the foreground window** (`MonitorFromWindow`).

## Rendering pipeline

1. WIC loads PNG → scales (`settings.scale`) → converts to premultiplied BGRA.
2. `CreateDIBSection` (32bpp, top-down `biHeight = -h`) → `copy_nonoverlapping` pixels in.
3. `SelectObject` DIB into compatible DC.
4. `UpdateLayeredWindow` with `ULW_ALPHA` + `BLENDFUNCTION { SourceConstantAlpha: alpha, AlphaFormat: AC_SRC_ALPHA }`.
5. Alpha tweened via 16ms timer (ID 2): fade-in step → hold → fade-out step → `ShowWindow(SW_HIDE)`.

`max_alpha` = `(255 * settings.opacity)` — caps peak opacity. Default 0.6 (40% more transparent than full).

## Tunable parameters

| Location | Parameter | Default |
|---|---|---|
| `settings.rs` | `duration_seconds` | 0.7 |
| `settings.rs` | `scale` (PNG display scale) | 0.35 |
| `settings.rs` | `opacity` (peak transparency) | 0.6 |
| `overlay.rs` | `FADE_IN_STEP` | 40 |
| `overlay.rs` | `FADE_OUT_STEP` | 35 |
| `main.rs` | `TIMER_POLL` interval | 50ms |

## Assets

User-supplied PNGs in `assets/EN.png` and `assets/AR.png`. Current: 677×369, 32bpp ARGB. Hot-swappable — tray menu "Reload Assets" resets `last_lang_id` to force re-detection. PNGs carry the full visual design (glassy/frosted styling baked in); the window just composites them with per-pixel alpha.

## Gotchas

- `#![windows_subsystem = "windows"]` in `main.rs` — no console. `eprintln!` is invisible in release. For debugging, add file logging to `%APPDATA%/LangVis/debug.log`.
- `WS_EX_TRANSPARENT` = click-through. Do not remove unless you want the overlay to capture mouse events.
- The overlay window starts at 1×1 hidden. `SetWindowPos` with `SWP_SHOWWINDOW` positions/sizes/shows it on first trigger.
- Settings file at `%APPDATA%/LangVis/settings.json` persists between runs. Delete it to reset to defaults.
- Binary is ~160 KB with `[profile.release]` size opts (`opt-level="z"`, LTO, strip, `panic="abort"`).
