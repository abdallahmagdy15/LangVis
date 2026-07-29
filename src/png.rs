use windows::Win32::Foundation::GENERIC_ACCESS_RIGHTS;
use windows::Win32::Graphics::Imaging::*;
use windows::Win32::System::Com::*;
use windows::core::HSTRING;

pub struct PngData {
    pub width: u32,
    pub height: u32,
    pub pixels: Vec<u8>,
}

pub fn load_png(path: &str, scale: f32) -> std::result::Result<PngData, String> {
    unsafe {
        let factory: IWICImagingFactory =
            CoCreateInstance(&CLSID_WICImagingFactory, None, CLSCTX_INPROC_SERVER)
                .map_err(|e| format!("CoCreateInstance: {e:?}"))?;

        let path_h = HSTRING::from(path);
        let decoder = factory
            .CreateDecoderFromFilename(&path_h, None, GENERIC_ACCESS_RIGHTS(0x8000_0000), WICDecodeMetadataCacheOnLoad)
            .map_err(|e| format!("CreateDecoderFromFilename: {e:?}"))?;

        let frame = decoder.GetFrame(0).map_err(|e| format!("GetFrame: {e:?}"))?;

        let mut src_w = 0u32;
        let mut src_h = 0u32;
        frame.GetSize(&mut src_w, &mut src_h).map_err(|e| format!("GetSize: {e:?}"))?;

        let target_w = ((src_w as f32 * scale) as u32).max(1);
        let target_h = ((src_h as f32 * scale) as u32).max(1);

        let scaler = factory.CreateBitmapScaler().map_err(|e| format!("CreateBitmapScaler: {e:?}"))?;
        scaler
            .Initialize(&frame, target_w, target_h, WICBitmapInterpolationModeHighQualityCubic)
            .map_err(|e| format!("Scaler init: {e:?}"))?;

        let converter = factory.CreateFormatConverter().map_err(|e| format!("CreateFormatConverter: {e:?}"))?;
        converter
            .Initialize(
                &scaler,
                &GUID_WICPixelFormat32bppPBGRA,
                WICBitmapDitherTypeNone,
                None,
                0.0,
                WICBitmapPaletteTypeCustom,
            )
            .map_err(|e| format!("Converter init: {e:?}"))?;

        let stride = target_w * 4;
        let mut pixels = vec![0u8; (stride * target_h) as usize];
        converter
            .CopyPixels(std::ptr::null(), stride, &mut pixels)
            .map_err(|e| format!("CopyPixels: {e:?}"))?;

        Ok(PngData { width: target_w, height: target_h, pixels })
    }
}
