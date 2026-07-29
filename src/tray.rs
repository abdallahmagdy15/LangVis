use std::mem::size_of;
use windows::Win32::Foundation::*;
use windows::Win32::Graphics::Gdi::*;
use windows::Win32::UI::Shell::*;
use windows::Win32::UI::WindowsAndMessaging::*;
use windows::core::*;

pub struct Tray;

impl Tray {
    pub fn new(hwnd: HWND, callback_msg: u32) -> Option<Self> {
        unsafe {
            let icon = create_app_icon().unwrap_or_else(|_| {
                LoadIconW(None, IDI_APPLICATION).unwrap_or_default()
            });

            let mut nid = NOTIFYICONDATAW {
                cbSize: size_of::<NOTIFYICONDATAW>() as u32,
                hWnd: hwnd,
                uID: 1,
                uFlags: NIF_MESSAGE | NIF_ICON | NIF_TIP,
                uCallbackMessage: callback_msg,
                hIcon: icon,
                ..Default::default()
            };

            let tip = w!("LangVis");
            for (i, &c) in tip.as_wide().iter().take(127).enumerate() {
                nid.szTip[i] = c;
            }

            let _ = Shell_NotifyIconW(NIM_ADD, &nid);
        }
        Some(Self)
    }
}

fn create_app_icon() -> windows::core::Result<HICON> {
    const S: i32 = 32;
    unsafe {
        let color_bmi = BITMAPINFO {
            bmiHeader: BITMAPINFOHEADER {
                biSize: size_of::<BITMAPINFOHEADER>() as u32,
                biWidth: S,
                biHeight: S,
                biPlanes: 1,
                biBitCount: 32,
                biCompression: 0,
                biSizeImage: (S * S * 4) as u32,
                ..Default::default()
            },
            bmiColors: [RGBQUAD::default()],
        };

        let hdc = GetDC(None);
        let mut color_bits: *mut std::ffi::c_void = std::ptr::null_mut();
        let hbm_color = CreateDIBSection(hdc.into(), &color_bmi, DIB_RGB_COLORS, &mut color_bits, None, 0)?;

        // Draw blue circle with raw pixels
        let px = color_bits as *mut u8;
        let cx = 15.5_f32;
        let cy = 15.5_f32;
        let r = 14.0_f32;
        let r_inner = 11.0_f32;
        for y in 0..S {
            for x in 0..S {
                let dx = x as f32 - cx;
                let dy = y as f32 - cy;
                let dist = (dx * dx + dy * dy).sqrt();
                let off = ((y * S + x) * 4) as isize;
                if dist <= r {
                    if dist > r_inner {
                        // Ring: lighter blue border
                        *px.offset(off) = 180;
                        *px.offset(off + 1) = 160;
                        *px.offset(off + 2) = 40;
                        *px.offset(off + 3) = 255;
                    } else {
                        // Inner: deep blue
                        *px.offset(off) = 200;
                        *px.offset(off + 1) = 100;
                        *px.offset(off + 2) = 20;
                        *px.offset(off + 3) = 255;
                    }
                }
            }
        }

        // Mask: all zeros (alpha handles transparency)
        let mask_bmi = BITMAPINFO {
            bmiHeader: BITMAPINFOHEADER {
                biSize: size_of::<BITMAPINFOHEADER>() as u32,
                biWidth: S,
                biHeight: S,
                biPlanes: 1,
                biBitCount: 1,
                biCompression: 0,
                ..Default::default()
            },
            bmiColors: [RGBQUAD::default()],
        };
        let mut mask_bits: *mut std::ffi::c_void = std::ptr::null_mut();
        let hbm_mask = CreateDIBSection(hdc.into(), &mask_bmi, DIB_RGB_COLORS, &mut mask_bits, None, 0)?;
        let _ = ReleaseDC(None, hdc);

        let ii = ICONINFO {
            fIcon: true.into(),
            xHotspot: 0,
            yHotspot: 0,
            hbmMask: hbm_mask,
            hbmColor: hbm_color,
        };

        CreateIconIndirect(&ii)
    }
}

pub fn show_context_menu(hwnd: HWND) {
    unsafe {
        let Ok(menu) = CreatePopupMenu() else {
            return;
        };

        let _ = AppendMenuW(menu, MF_STRING, 1001, w!("Settings\u{2026}"));

        let startup_on = crate::settings::is_startup_enabled();
        let startup_flags = MF_STRING | if startup_on { MF_CHECKED } else { MF_UNCHECKED };
        let _ = AppendMenuW(menu, startup_flags, 1002, w!("Run on Startup"));

        let _ = AppendMenuW(menu, MF_STRING, 1003, w!("Reload Assets"));
        let _ = AppendMenuW(menu, MF_SEPARATOR, 0, w!(""));
        let _ = AppendMenuW(menu, MF_STRING, 1004, w!("Exit"));

        let mut pt = POINT::default();
        let _ = GetCursorPos(&mut pt);
        let _ = SetForegroundWindow(hwnd);

        let _ = TrackPopupMenu(
            menu,
            TPM_RIGHTBUTTON | TPM_BOTTOMALIGN,
            pt.x,
            pt.y,
            None,
            hwnd,
            None,
        );

        let _ = DestroyMenu(menu);
    }
}
