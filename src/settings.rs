use serde::{Deserialize, Serialize};
use windows::Win32::Foundation::ERROR_SUCCESS;
use windows::Win32::System::Registry::*;
use windows::core::*;

#[derive(Clone, Serialize, Deserialize)]
pub struct UserSettings {
    #[serde(default = "default_duration")]
    pub duration_seconds: f64,
    #[serde(default)]
    pub use_top_corners: bool,
    #[serde(default = "default_scale")]
    pub scale: f32,
    #[serde(default = "default_opacity")]
    pub opacity: f32,
    #[serde(default)]
    pub run_on_startup: bool,
}

fn default_duration() -> f64 {
    0.7
}
fn default_scale() -> f32 {
    0.35
}
fn default_opacity() -> f32 {
    0.6
}

impl Default for UserSettings {
    fn default() -> Self {
        Self {
            duration_seconds: 0.7,
            use_top_corners: false,
            scale: 0.35,
            opacity: 0.6,
            run_on_startup: false,
        }
    }
}

fn settings_path() -> std::path::PathBuf {
    let appdata = std::env::var("APPDATA").unwrap_or_default();
    std::path::PathBuf::from(appdata).join("LangVis").join("settings.json")
}

impl UserSettings {
    pub fn load() -> Self {
        match std::fs::read_to_string(settings_path()) {
            Ok(s) => serde_json::from_str(&s).unwrap_or_default(),
            Err(_) => Self::default(),
        }
    }

    pub fn save(&self) {
        let path = settings_path();
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if let Ok(s) = serde_json::to_string_pretty(self) {
            let _ = std::fs::write(&path, s);
        }
    }
}

const RUN_KEY: PCWSTR = w!("Software\\Microsoft\\Windows\\CurrentVersion\\Run");
const APP_NAME: PCWSTR = w!("LangVis");

pub fn is_startup_enabled() -> bool {
    unsafe {
        let mut handle = HKEY::default();
        let result = RegOpenKeyExW(HKEY_CURRENT_USER, RUN_KEY, Some(0), KEY_READ, &mut handle);
        if result != ERROR_SUCCESS {
            return false;
        }
        let found = RegQueryValueExW(handle, APP_NAME, None, None, None, None) == ERROR_SUCCESS;
        let _ = RegCloseKey(handle);
        found
    }
}

pub fn set_startup(enable: bool) {
    unsafe {
        let mut handle = HKEY::default();
        let result = RegOpenKeyExW(HKEY_CURRENT_USER, RUN_KEY, Some(0), KEY_SET_VALUE, &mut handle);
        if result != ERROR_SUCCESS {
            return;
        }

        if enable {
            if let Ok(exe) = std::env::current_exe() {
                let path = exe.to_string_lossy();
                let h = HSTRING::from(path.as_ref());
                let bytes = std::slice::from_raw_parts(h.as_ptr() as *const u8, h.len() * 2);
                let _ = RegSetValueExW(handle, APP_NAME, None, REG_SZ, Some(bytes));
            }
        } else {
            let _ = RegDeleteValueW(handle, APP_NAME);
        }
        let _ = RegCloseKey(handle);
    }
}
