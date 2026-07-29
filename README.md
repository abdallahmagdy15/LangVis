# LangVis

A lightweight Windows overlay that briefly shows a glassy language indicator when you switch keyboard layouts.

![LangVis preview](assets/EN.png)

## Features

- Shows **AR** (Arabic) bottom-right and **EN** (English) bottom-left.
- Appears on the monitor of the currently focused window.
- Smooth fade-in / hold / fade-out animation.
- Lives in the system tray with a right-click menu.
- Hot-swappable PNG assets via tray menu.
- Persistent settings in `%APPDATA%/LangVis/settings.json`.

## Build

Cargo is required. On this machine it is not in `PATH`, so prefix each session:

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
cargo build --release
```

The binary lands at `target/release/langvis.exe`. Copy it next to the `assets/` folder before running:

```powershell
Copy-Item target/release/langvis.exe langvis.exe -Force
```

## Run

```powershell
langvis.exe
```

A tray icon appears. Right-click it for options such as **Reload Assets**, **Settings**, and **Exit**.

## Configuration

Settings are stored in `%APPDATA%/LangVis/settings.json`:

| Setting | Default | Description |
|---|---|---|
| `duration_seconds` | `0.7` | How long the overlay stays fully visible. |
| `scale` | `0.35` | Display scale of the PNG. |
| `opacity` | `0.6` | Peak opacity (0.0–1.0). |

Delete the file to reset to defaults.

## Assets

Replace `assets/EN.png` and `assets/AR.png` with your own 32-bit ARGB PNGs. The visual style is baked into the PNGs; the app only composites them with per-pixel alpha.

## Architecture

- `main.rs` — Win32 message loop, 50 ms polling timer, layout detection, tray dispatch.
- `overlay.rs` — Layered window rendering with `UpdateLayeredWindow`.
- `png.rs` — WIC PNG decoder and premultiplied BGRA conversion.
- `tray.rs` — System tray icon and popup menu.
- `settings.rs` — JSON settings and startup registry handling.

## Notes

- Layout detection queries the **foreground window's thread**, not the overlay app's thread.
- Arabic is detected when `(lang_id & 0xFF) == 0x01`; everything else is treated as English.
- Release builds are optimized for size with LTO and `panic = "abort"`.
