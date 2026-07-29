use std::mem::size_of;
use windows::Win32::Foundation::*;
use windows::Win32::Graphics::Gdi::*;
use windows::Win32::UI::WindowsAndMessaging::*;

use crate::png;
use crate::settings::UserSettings;

const FADE_IN_STEP: u8 = 40;
const FADE_OUT_STEP: u8 = 35;
const TIMER_ANIM: usize = 2;

#[derive(PartialEq)]
enum AnimState {
    Hidden,
    FadingIn,
    Holding,
    FadingOut,
}

pub struct Overlay {
    pub hwnd: HWND,
    width: i32,
    height: i32,
    pos_x: i32,
    pos_y: i32,
    memdc: HDC,
    hbitmap: HBITMAP,
    bits: *mut u8,
    alpha: u8,
    max_alpha: u8,
    hold_frames_left: u32,
    state: AnimState,
}

impl Overlay {
    pub fn new(hwnd: HWND) -> Self {
        Self {
            hwnd,
            width: 1,
            height: 1,
            pos_x: 0,
            pos_y: 0,
            memdc: HDC::default(),
            hbitmap: HBITMAP::default(),
            bits: std::ptr::null_mut(),
            alpha: 0,
            max_alpha: 153,
            hold_frames_left: 0,
            state: AnimState::Hidden,
        }
    }

    pub fn show(&mut self, lang: &str, settings: &UserSettings) {
        let Some(exe_dir) = (|| std::env::current_exe().ok()?.parent().map(|p| p.to_path_buf()))() else {
            return;
        };

        let png_path = exe_dir.join("assets").join(format!("{lang}.png"));
        let png_path_str = png_path.to_string_lossy().to_string();

        let data = match png::load_png(&png_path_str, settings.scale) {
            Ok(d) => d,
            Err(_) => return,
        };

        self.width = data.width as i32;
        self.height = data.height as i32;
        self.max_alpha = (255.0 * settings.opacity) as u8;
        self.create_bitmap(&data);
        self.position(lang == "AR", settings.use_top_corners);

        if self.state == AnimState::Hidden {
            self.alpha = 0;
            let _ = unsafe {
                SetWindowPos(
                    self.hwnd,
                    None,
                    self.pos_x,
                    self.pos_y,
                    self.width,
                    self.height,
                    SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_NOZORDER,
                )
            };
        }

        self.state = AnimState::FadingIn;
        self.hold_frames_left = (settings.duration_seconds * 62.0) as u32;
        self.render();
        unsafe { SetTimer(Some(self.hwnd), TIMER_ANIM, 16, None) };
    }

    fn create_bitmap(&mut self, data: &png::PngData) {
        unsafe {
            if !self.hbitmap.is_invalid() {
                let _ = DeleteObject(self.hbitmap.into());
            }
            if !self.memdc.is_invalid() {
                let _ = DeleteDC(self.memdc);
            }

            let bmi = BITMAPINFO {
                bmiHeader: BITMAPINFOHEADER {
                    biSize: size_of::<BITMAPINFOHEADER>() as u32,
                    biWidth: data.width as i32,
                    biHeight: -(data.height as i32),
                    biPlanes: 1,
                    biBitCount: 32,
                    biCompression: 0,
                    biSizeImage: (data.width * data.height * 4) as u32,
                    biXPelsPerMeter: 0,
                    biYPelsPerMeter: 0,
                    biClrUsed: 0,
                    biClrImportant: 0,
                },
                bmiColors: [RGBQUAD::default()],
            };

            let hdc_screen = GetDC(None);
            let mut bits: *mut std::ffi::c_void = std::ptr::null_mut();
            self.hbitmap = CreateDIBSection(hdc_screen.into(), &bmi, DIB_RGB_COLORS, &mut bits, None, 0)
                .unwrap_or_default();

            if !self.hbitmap.is_invalid() && !bits.is_null() {
                std::ptr::copy_nonoverlapping(data.pixels.as_ptr(), bits as *mut u8, data.pixels.len());
                self.bits = bits as *mut u8;
            }

            self.memdc = CreateCompatibleDC(hdc_screen.into());
            let _ = SelectObject(self.memdc, self.hbitmap.into());
            let _ = ReleaseDC(None, hdc_screen);
        }
    }

    fn position(&mut self, right_aligned: bool, use_top: bool) {
        unsafe {
            let foreground = GetForegroundWindow();
            let monitor = MonitorFromWindow(foreground, MONITOR_DEFAULTTONEAREST);
            let mut mi = MONITORINFO {
                cbSize: size_of::<MONITORINFO>() as u32,
                ..Default::default()
            };
            let _ = GetMonitorInfoW(monitor, &mut mi);

            let margin = 30i32;
            self.pos_x = if right_aligned {
                mi.rcWork.right - self.width - margin
            } else {
                mi.rcWork.left + margin
            };
            self.pos_y = if use_top {
                mi.rcWork.top + margin
            } else {
                mi.rcWork.bottom - self.height - margin
            };
        }
    }

    fn render(&self) {
        if self.hbitmap.is_invalid() {
            return;
        }
        unsafe {
            let blend = BLENDFUNCTION {
                BlendOp: AC_SRC_OVER as u8,
                BlendFlags: 0,
                SourceConstantAlpha: self.alpha,
                AlphaFormat: AC_SRC_ALPHA as u8,
            };

            let pt_dst = POINT { x: self.pos_x, y: self.pos_y };
            let pt_zero = POINT { x: 0, y: 0 };
            let size = SIZE { cx: self.width, cy: self.height };

            let hdc_screen = GetDC(None);
            let _ = UpdateLayeredWindow(
                self.hwnd,
                Some(hdc_screen),
                Some(&pt_dst),
                Some(&size),
                Some(self.memdc),
                Some(&pt_zero),
                COLORREF(0),
                Some(&blend),
                ULW_ALPHA,
            );
            let _ = ReleaseDC(None, hdc_screen);
        }
    }

    pub fn animate_frame(&mut self) -> bool {
        match self.state {
            AnimState::Hidden => false,

            AnimState::FadingIn => {
                self.alpha = self.alpha.saturating_add(FADE_IN_STEP);
                if self.alpha >= self.max_alpha {
                    self.alpha = self.max_alpha;
                    self.state = AnimState::Holding;
                }
                self.render();
                true
            }

            AnimState::Holding => {
                if self.hold_frames_left > 0 {
                    self.hold_frames_left -= 1;
                    true
                } else {
                    self.state = AnimState::FadingOut;
                    self.animate_frame()
                }
            }

            AnimState::FadingOut => {
                self.alpha = self.alpha.saturating_sub(FADE_OUT_STEP);
                if self.alpha <= FADE_OUT_STEP {
                    self.alpha = 0;
                    self.state = AnimState::Hidden;
                    let _ = unsafe { ShowWindow(self.hwnd, SW_HIDE) };
                    false
                } else {
                    self.render();
                    true
                }
            }
        }
    }
}
