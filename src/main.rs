#![windows_subsystem = "windows"]

mod overlay;
mod png;
mod settings;
mod tray;

use windows::Win32::Foundation::*;
use windows::Win32::System::Com::*;
use windows::Win32::System::LibraryLoader::*;
use windows::Win32::System::Threading::*;
use windows::Win32::UI::Input::KeyboardAndMouse::*;
use windows::Win32::UI::WindowsAndMessaging::*;
use windows::core::*;

const TIMER_POLL: usize = 1;
const WM_TRAYICON: u32 = WM_USER + 1;

const CMD_SETTINGS: u32 = 1001;
const CMD_STARTUP: u32 = 1002;
const CMD_RELOAD: u32 = 1003;
const CMD_EXIT: u32 = 1004;

struct AppState {
    overlay: overlay::Overlay,
    settings: settings::UserSettings,
    last_lang_id: u16,
}

static mut APP: Option<AppState> = None;

fn main() {
    let _mutex = unsafe { CreateMutexW(None, false, w!("LangVis_SingleInstance_7B2F9A4C")) };
    if unsafe { GetLastError() } == ERROR_ALREADY_EXISTS {
        return;
    }

    let _ = unsafe { CoInitializeEx(None, COINIT_APARTMENTTHREADED) };

    let hinstance = unsafe { GetModuleHandleW(None) }.expect("GetModuleHandleW");

    let wc = WNDCLASSW {
        lpfnWndProc: Some(wnd_proc),
        hInstance: hinstance.into(),
        lpszClassName: w!("LangVisWindow"),
        ..Default::default()
    };
    if unsafe { RegisterClassW(&wc) } == 0 {
        return;
    }

    let ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST;
    let hwnd = unsafe {
        CreateWindowExW(
            ex_style,
            w!("LangVisWindow"),
            w!("LangVis"),
            WS_POPUP,
            0, 0, 1, 1,
            None, None,
            Some(hinstance.into()),
            None,
        )
    };
    let hwnd = match hwnd {
        Ok(h) => h,
        Err(_) => return,
    };

    let overlay = overlay::Overlay::new(hwnd);
    let loaded_settings = settings::UserSettings::load();

    let initial_lang = unsafe {
        let fg = GetForegroundWindow();
        if fg.is_invalid() {
            0xFFFFu16
        } else {
            let mut pid = 0u32;
            let tid = GetWindowThreadProcessId(fg, Some(&mut pid));
            let hkl = GetKeyboardLayout(tid);
            (hkl.0 as u32 & 0xFFFF) as u16
        }
    };

    unsafe {
        APP = Some(AppState {
            overlay,
            settings: loaded_settings,
            last_lang_id: initial_lang,
        });
    }

    let _tray = tray::Tray::new(hwnd, WM_TRAYICON);
    let _ = unsafe { SetTimer(Some(hwnd), TIMER_POLL, 50, None) };

    let mut msg = MSG::default();
    loop {
        let ret = unsafe { GetMessageW(&mut msg, None, 0, 0) };
        if ret.0 <= 0 {
            break;
        }
        let _ = unsafe { TranslateMessage(&msg) };
        unsafe { DispatchMessageW(&msg) };
    }
}

extern "system" fn wnd_proc(hwnd: HWND, msg: u32, wp: WPARAM, lp: LPARAM) -> LRESULT {
    match msg {
        WM_TIMER => {
            let id = wp.0 as usize;
            if id == TIMER_POLL {
                check_language();
            } else if id == 2 {
                step_animation();
            }
            LRESULT(0)
        }

        x if x == WM_TRAYICON => {
            if lp.0 as u32 == WM_RBUTTONUP {
                tray::show_context_menu(hwnd);
            }
            LRESULT(0)
        }

        WM_COMMAND => {
            let cmd = (wp.0 as u32) & 0xFFFF;
            handle_command(cmd);
            LRESULT(0)
        }

        WM_DESTROY => {
            unsafe { PostQuitMessage(0) };
            LRESULT(0)
        }

        _ => unsafe { DefWindowProcW(hwnd, msg, wp, lp) },
    }
}

fn check_language() {
    unsafe {
        let app = match APP.as_mut() {
            Some(a) => a,
            None => return,
        };

        let fg = GetForegroundWindow();
        if fg.is_invalid() {
            return;
        }
        let mut pid = 0u32;
        let tid = GetWindowThreadProcessId(fg, Some(&mut pid));
        if tid == 0 {
            return;
        }
        let hkl = GetKeyboardLayout(tid);
        let lang_id = (hkl.0 as u32 & 0xFFFF) as u16;

        if lang_id == app.last_lang_id {
            return;
        }
        app.last_lang_id = lang_id;

        let is_arabic = (lang_id & 0xFF) == 0x01;
        let lang_str = if is_arabic { "AR" } else { "EN" };
        let settings = app.settings.clone();
        app.overlay.show(lang_str, &settings);
    }
}

fn step_animation() {
    unsafe {
        let app = match APP.as_mut() {
            Some(a) => a,
            None => return,
        };
        let keep_going = app.overlay.animate_frame();
        if !keep_going {
            let _ = KillTimer(Some(app.overlay.hwnd), 2);
        }
    }
}

fn handle_command(cmd: u32) {
    match cmd {
        CMD_EXIT => unsafe {
            let app = APP.as_ref().unwrap();
            let _ = PostMessageW(Some(app.overlay.hwnd), WM_CLOSE, WPARAM(0), LPARAM(0));
        },

        CMD_STARTUP => {
            let enable = unsafe {
                let app = APP.as_mut().unwrap();
                let enable = !app.settings.run_on_startup;
                app.settings.run_on_startup = enable;
                app.settings.save();
                enable
            };
            settings::set_startup(enable);
        }

        CMD_RELOAD => unsafe {
            APP.as_mut().unwrap().last_lang_id = 0xFFFF;
        },

        _ => {}
    }
}
