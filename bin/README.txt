Place the encoder and comparison tool binaries in this folder.

---

Download CLI tools on Windows:

mozjpeg
https://github.com/garyzyg/mozjpeg-windows/releases (mozjpeg-x64.zip)
Extract "cjpeg-static.exe" and rename to "cjpeg.exe".

avif
https://github.com/AOMediaCodec/libavif/releases (libavif-v*-avifenc-avifdec-windows.zip)
https://ci.appveyor.com/project/louquillio/libavif/build/artifacts
https://jeremylee.sh/bins/avif.7z
Extract "avifenc.exe".

jxl
https://github.com/libjxl/libjxl/releases (jxl-x64-windows-static.zip)
https://jeremylee.sh/bins/jpegxl.7z
Extract "cjxl.exe".

oxipng
https://github.com/shssoichiro/oxipng/releases (oxipng-*-x86_64-pc-windows-msvc.zip)
Extract "oxipng.exe".

webp
https://storage.googleapis.com/downloads.webmproject.org/releases/webp/index.html (libwebp-*-windows-x64.zip)
https://jeremylee.sh/bins/webp.7z
Extract "cwebp.exe".

jpegli
https://github.com/libjxl/libjxl/releases (jxl-x64-windows-static.zip)
Extract "cjpegli.exe".
Images with alpha mess with jpegli using XYB · Issue #2671 · libjxl/libjxl
https://github.com/libjxl/libjxl/issues/2671
v0.10.2 or earlier cannot handle RGBA images if encoding with XYB colorspace. Use nightly builds instead.
https://github.com/libjxl/libjxl/actions/workflows/release.yaml (jxl-x64-windows-static.zip)
https://artifacts.lucaversari.it/libjxl/libjxl/latest/jxl-x64-windows-static.zip

dssim
https://github.com/kornelski/dssim/releases (dssim-*.zip)
https://jeremylee.sh/bins/dssim.7z
Extract "dssim.exe".

butteraugli
https://github.com/libjxl/libjxl/releases (jxl-x64-windows-static.zip)
https://jeremylee.sh/bins/butteraugli.7z
Extract "butteraugli_main.exe" and rename to "butteraugli.exe".

ssimulacra2
https://github.com/libjxl/libjxl/releases (jxl-x64-windows-static.zip)
Extract "ssimulacra2.exe".
