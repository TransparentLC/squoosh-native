import functools
import subprocess
import os
import typing
import wvruntime
from concurrent.futures import ThreadPoolExecutor

binDir = os.path.join(wvruntime.executablePath, 'bin')

class ImageData(typing.TypedDict):
    width: int
    height: int
    data: bytes

class EncoderState(typing.TypedDict):
    type: str
    options: dict[str, int | float | bool]

class AbstractEncoderOptions:
    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    @staticmethod
    def checkInfo() -> str | None:
        raise NotImplementedError()

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        raise NotImplementedError()

class MozJPEGEncoderOptions(AbstractEncoderOptions):
    # https://github.com/GoogleChromeLabs/squoosh/blob/dev/codecs/mozjpeg/enc/mozjpeg_enc.cpp
    # https://github.com/mozilla/mozjpeg/blob/master/cjpeg.c
    quality: bool
    baseline: bool
    arithmetic: bool
    progressive: bool
    optimize_coding: bool
    smoothing: int
    color_space: int
    quant_table: int
    trellis_multipass: bool
    trellis_opt_zero: bool
    trellis_opt_table: bool
    trellis_loops: int
    auto_subsample: bool
    chroma_subsample: int
    separate_chroma_quality: bool
    chroma_quality: int

    @staticmethod
    def checkInfo() -> str | None:
        try:
            r = subprocess.run(
                (os.path.join(binDir, 'cjpeg'), '-version'),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stderr.strip()
            return r if 'mozjpeg' in r else None
        except FileNotFoundError:
            return None

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        args = [os.path.join(binDir, 'cjpeg')]
        args.append('-quant-table')
        args.append(str(self.quant_table))
        if self.optimize_coding:
            args.append('-optimize')
        if self.arithmetic:
            args.append('-arithmetic')
        args.append('-smooth')
        args.append(str(self.smoothing))
        # Unable to set in CLI
        # jpeg_c_set_bool_param(&cinfo, JBOOLEAN_USE_SCANS_IN_TRELLIS, opts.trellis_multipass);
        # jpeg_c_set_bool_param(&cinfo, JBOOLEAN_TRELLIS_EOB_OPT, opts.trellis_opt_zero);
        # jpeg_c_set_bool_param(&cinfo, JBOOLEAN_TRELLIS_Q_OPT, opts.trellis_opt_table);
        # jpeg_c_set_int_param(&cinfo, JINT_TRELLIS_NUM_LOOPS, opts.trellis_loops);
        args.append('-quality')
        if self.separate_chroma_quality and self.color_space == 3:
            args.append(f'{self.quality},{self.chroma_quality}')
        else:
            args.append(str(self.quality))
        if not self.auto_subsample and self.color_space == 3:
            args.append('-sample')
            args.append(f'{self.chroma_subsample}x{self.chroma_subsample}')
        elif self.color_space == 2:
            args.append('-rgb')
        elif self.color_space == 1:
            args.append('-grayscale')
        if self.progressive:
            args.append('-progressive')
            args.append('-dc-scan-opt')
            args.append('2')
        else:
            args.append('-baseline')
        args.append('-verbose')
        args.append('-outfile')
        args.append(outputFile)
        args.append(inputFile)
        return args

class AVIFEncoderOptions(AbstractEncoderOptions):
    # https://github.com/GoogleChromeLabs/squoosh/blob/dev/codecs/avif/enc/avif_enc.cpp
    quality: int
    qualityAlpha: int
    tileRowsLog2: int
    tileColsLog2: int
    speed: int
    subsample: int
    chromaDeltaQ: bool
    sharpness: int
    tune: int
    denoiseLevel: int
    enableSharpYUV: bool

    @staticmethod
    def checkInfo() -> str | None:
        try:
            return subprocess.check_output(
                (os.path.join(binDir, 'avifenc'), '--version'),
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).strip()
        except FileNotFoundError:
            return None

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        args = [os.path.join(binDir, 'avifenc')]
        args.append('--jobs')
        args.append('all')
        args.append('--yuv')
        args.append(('400', '420', '422', '444')[self.subsample])
        if self.enableSharpYUV:
            args.append('--sharpyuv')
        if self.quality == 100 and self.qualityAlpha in {-1, 100} and self.subsample == 3:
            args.append('--lossless')
        else:
            args.append('--qcolor')
            args.append(str(self.quality))
            args.append('--qalpha')
            args.append(str(self.quality if self.qualityAlpha == -1 else self.qualityAlpha))
            args.append('--advanced')
            args.append(f'sharpness={self.sharpness}')
            if self.tune == 2 or (self.tune == 0 and self.quality >= 50):
                args.append('--advanced')
                args.append('tune=ssim')
            if self.chromaDeltaQ:
                args.append('--advanced')
                args.append('color:enable-chroma-deltaq=1')
            args.append('--advanced')
            args.append(f'color:denoise-noise-level={self.denoiseLevel}')
        args.append('--tilerowslog2')
        args.append(str(self.tileRowsLog2))
        args.append('--tilecolslog2')
        args.append(str(self.tileColsLog2))
        args.append('--speed')
        args.append(str(self.speed))
        args.append('--')
        args.append(inputFile)
        args.append(outputFile)
        return args

class JXLEncoderOptions(AbstractEncoderOptions):
    # https://github.com/GoogleChromeLabs/squoosh/blob/dev/codecs/jxl/enc/jxl_enc.cpp
    # https://github.com/libjxl/libjxl/blob/master/tools/cjxl_main.cc
    effort: int
    quality: float
    progressive: bool
    epf: int
    lossyPalette: bool
    decodingSpeedTier: int
    photonNoiseIso: float
    lossyModular: bool

    @staticmethod
    def checkInfo() -> str | None:
        try:
            return subprocess.check_output(
                (os.path.join(binDir, 'cjxl'), '--version'),
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).strip()
        except FileNotFoundError:
            return None

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        args = [os.path.join(binDir, 'cjxl')]
        args.append(inputFile)
        args.append(outputFile)
        args.append('--brotli_effort=11')
        args.append('--num_threads=-1')
        args.append(f'--effort={self.effort}')
        args.append(f'--epf={self.epf}')
        args.append(f'--faster_decoding={self.decodingSpeedTier}')
        args.append(f'--photon_noise_iso={self.photonNoiseIso}')
        modular_mode = False
        responsive = False
        if self.lossyPalette:
            args.append('--modular_lossy_palette')
            args.append('--modular_palette_colors=0')
            args.append('--modular_predictor=0')
            args.append('--responsive=0')
            responsive = True
            modular_mode = True
        if self.lossyModular or self.quality == 100:
            modular_mode = True
            # Unable to set in CLI
            # cparams.quality_pair.first = cparams.quality_pair.second = ...
            # x = min(35 + (self.quality - 7) * (3 if self.quality < 7 else (65 / 93)), 100)
        else:
            modular_mode = False
        args.append(f'--quality={self.quality}')
        if self.progressive:
            args.append('--progressive')
            responsive = True
            if not modular_mode:
                args.append('--progressive_dc=1')
        # Unable to set in CLI
        # cparams.color_transform = ...
        args.append(f'--modular={int(modular_mode)}')
        args.append(f'--responsive={int(responsive)}')
        args.append('--verbose')
        return args

class OxiPNGEncoderOptions(AbstractEncoderOptions):
    level: int
    interlace: bool

    @staticmethod
    def checkInfo() -> str | None:
        try:
            return subprocess.check_output(
                (os.path.join(binDir, 'oxipng'), '--version'),
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).strip()
        except FileNotFoundError:
            return None

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        args = [os.path.join(binDir, 'oxipng')]
        args.append('--verbose')
        args.append('--verbose')
        args.append('--opt')
        args.append(str(self.level))
        args.append('--interlace')
        args.append(str(int(self.interlace)))
        args.append('--strip')
        args.append('safe')
        args.append('--alpha')
        args.append('--out')
        args.append(outputFile)
        args.append(inputFile)
        return args

class WebPEncoderOptions(AbstractEncoderOptions):
    # https://github.com/GoogleChromeLabs/squoosh/blob/dev/codecs/webp/enc/webp_enc.cpp
    # https://github.com/webmproject/libwebp/blob/main/examples/cwebp.c
    # https://github.com/webmproject/libwebp/blob/main/src/webp/encode.h
    quality: float
    target_size: int
    target_PSNR: float
    method: int
    sns_strength: int
    filter_strength: int
    filter_sharpness: int
    filter_type: bool
    partitions: int
    segments: int
    # pass: int # Conflicts with Python keywords, use getattr(self, 'pass') instead
    show_compressed: bool
    preprocessing: int
    autofilter: bool
    partition_limit: int
    alpha_compression: bool
    alpha_filtering: int
    alpha_quality: int
    lossless: bool
    exact: int
    image_hint: int
    emulate_jpeg_size: bool
    thread_level: int
    low_memory: bool
    near_lossless: int
    use_delta_palette: bool
    use_sharp_yuv: bool

    @staticmethod
    def checkInfo() -> str | None:
        try:
            return subprocess.check_output(
                (os.path.join(binDir, 'cwebp'), '-version'),
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).strip()
        except FileNotFoundError:
            return None

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        args = [os.path.join(binDir, 'cwebp')]
        args.append('-v')
        args.append('-q')
        args.append(str(self.quality))
        if self.target_size:
            args.append('-size')
            args.append(str(self.target_size))
        if self.target_PSNR:
            args.append('-psnr')
            args.append(str(self.target_PSNR))
        args.append('-m')
        args.append(str(self.method))
        args.append('-sns')
        args.append(str(self.sns_strength))
        if self.autofilter:
            args.append('-af')
        else:
            args.append('-f')
            args.append(str(self.filter_strength))
        args.append('-sharpness')
        args.append(str(self.filter_sharpness))
        args.append('-strong' if self.filter_type else '-nostrong')
        args.append('-segments')
        args.append(str(self.segments))
        args.append('-pass')
        args.append(str(getattr(self, 'pass')))
        args.append('-pre')
        args.append(str(self.preprocessing))
        args.append('-partition_limit')
        args.append(str(self.partition_limit))
        args.append('-alpha_method')
        args.append(str(self.alpha_compression))
        args.append('-alpha_filter')
        args.append(['none', 'fast', 'best'][self.alpha_filtering])
        args.append('-alpha_q')
        args.append(str(self.alpha_quality))
        if self.lossless:
            args.append('-lossless')
            args.append('-z')
            args.append('9')
            if self.near_lossless:
                args.append('-near_lossless')
                args.append(str(self.near_lossless))
        if self.exact:
            args.append('-exact')
        if self.image_hint:
            args.append('-hint')
            args.append(('', 'photo', 'picture', 'graph')[self.image_hint])
        if self.emulate_jpeg_size:
            args.append('-jpeg_like')
        if self.use_sharp_yuv:
            args.append('-sharp_yuv')
        args.append('-mt')
        args.append('-o')
        args.append(outputFile)
        args.append(inputFile)
        return args

class JpegliEncoderOptions(AbstractEncoderOptions):
    quality: int
    subsample: int
    xyb: bool

    @staticmethod
    def checkInfo() -> str | None:
        try:
            subprocess.check_output((os.path.join(binDir, 'cjpegli'), ), creationflags=subprocess.CREATE_NO_WINDOW)
            return 'Available'
        except FileNotFoundError:
            return None

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        args = [os.path.join(binDir, 'cjpegli')]
        args.append(inputFile)
        args.append(outputFile)
        args.append('--verbose')
        args.append('--verbose')
        args.append(f'--quality={self.quality}')
        if self.xyb:
            args.append('--xyb')
        else:
            args.append(f'--chroma_subsampling={('420', '422', '440', '444')[self.subsample]}')
        args.append('--progressive_level=2')
        return args

class PngquantEncoderOptions(AbstractEncoderOptions):
    quality: int
    effort: int
    fs: bool
    strip: bool

    @staticmethod
    def checkInfo() -> str | None:
        try:
            r = subprocess.run(
                (os.path.join(binDir, 'pngquant'),),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stderr.strip().splitlines()[0]
            return r if 'pngquant' in r else None
        except FileNotFoundError:
            return None

    def buildCommand(self, inputFile: str, outputFile: str) -> list[str]:
        args = [os.path.join(binDir, 'pngquant')]
        args.append('--output')
        args.append(outputFile)
        args.append('--quality')
        args.append(f'0-{self.quality}')
        args.append('--speed')
        args.append(str(12 - self.effort))
        if not self.fs:
            args.append('--nofs')
        if self.strip:
            args.append('--strip')
        args.append('--verbose')
        args.append('--')
        args.append(inputFile)
        return args

encoderOptionsClassMapping: dict[str, AbstractEncoderOptions] = {
    'mozJPEG': MozJPEGEncoderOptions,
    'avif': AVIFEncoderOptions,
    'jxl': JXLEncoderOptions,
    'oxiPNG': OxiPNGEncoderOptions,
    'webP': WebPEncoderOptions,
    'jpegli': JpegliEncoderOptions,
    'pngquant': PngquantEncoderOptions,
}

class AbstractMetric:
    executable: str

    @classmethod
    def check(cls) -> bool:
        return os.path.exists(os.path.join(binDir, cls.executable + ('.exe' if os.name == 'nt' else '')))

    @staticmethod
    def parseOutput(output: str) -> float:
        raise NotImplementedError()

    @classmethod
    def calculate(cls, originalFile: str, distortedFile: str) -> float:
        return cls.parseOutput(
            subprocess.check_output(
                (os.path.join(binDir, cls.executable), originalFile, distortedFile),
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).strip()
        )

class DSSIMMetric(AbstractMetric):
    executable = 'dssim'

    @staticmethod
    def parseOutput(output: str) -> float:
        return float(output.split('\t', 2)[0])

class ButteraugliMetric(AbstractMetric):
    executable = 'butteraugli'

    @staticmethod
    def parseOutput(output: str) -> float:
        return float(output.split('\n')[1].removeprefix('3-norm: '))

class SSIMULACRA2Metric(AbstractMetric):
    executable = 'ssimulacra2'

    @staticmethod
    def parseOutput(output: str) -> float:
        return float(output)


metricClassMapping: dict[str, AbstractMetric] = {
    'dssim': DSSIMMetric,
    'butteraugli': ButteraugliMetric,
    'ssimulacra2': SSIMULACRA2Metric,
}

@functools.cache
def checkCodec() -> dict[str, str | None]:
    with ThreadPoolExecutor() as executor:
        return dict(executor.map(lambda k: (k, encoderOptionsClassMapping[k].checkInfo()), encoderOptionsClassMapping))

@functools.cache
def checkMetric() -> dict[str, bool]:
    return {k: metricClassMapping[k].check() for k in metricClassMapping}
