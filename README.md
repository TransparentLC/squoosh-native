# Squoosh Native

[![build](https://github.com/TransparentLC/squoosh-native/actions/workflows/build.yml/badge.svg)](https://github.com/TransparentLC/squoosh-native/actions/workflows/build.yml)

![](https://github.com/TransparentLC/squoosh-native/assets/47057319/bd377ebe-96f0-426f-8661-7d5713322bfa)

## 基本介绍

使用 pywebview 框架和 Squoosh 的源代码构建的桌面应用。

[Squoosh](https://github.com/GoogleChromeLabs/squoosh) 是由 Google Chrome Labs 推出的在线图像压缩工具。它的另一层意义是演示 WASM（WebAssembly）和 PWA（Progressive Web App）技术的应用：前者使得用 C/C++/Rust 编写的图像处理模块（缩放、减色、编解码）可以在浏览器中运行；后者可以将整个应用进行离线缓存，在浏览器支持的情况下还可以“安装到桌面”，像一般的应用程序一样使用（实际上打开的还是浏览器）。

不过，如果真的把 Squoosh 当成桌面应用来使用，编译到 WASM 毕竟是存在性能损耗的，对于需要重度计算的图像压缩来说这是就是很难忽视的问题了。这也是项目名称中“Native”的含义：不仅是通过套上 GUI 框架的浏览器内核，将它转变为桌面应用（例如使用 Electron 构建的 [matiasbenedetto/squoosh-desktop-app](https://github.com/matiasbenedetto/squoosh-desktop-app)，似乎已经弃坑了），同时也将编码的后端从 WASM 重新替换回使用 native code 的命令行程序（CLI），实现更快的压缩速度。

## 下载和使用

可以直接从 [Actions](https://github.com/TransparentLC/squoosh-native/actions) 或 [nightly.link](https://nightly.link/TransparentLC/squoosh-native/workflows/build/master) 下载。

* `squoosh-native-*`：解压即用的本体
* `tools-*`：所有支持的 CLI 的整合包，解压后可以选择要启用的 CLI 放入 `bin` 目录下

<details>

<summary>从源代码运行和开发</summary>

需要 Python 3.12、Node.js 21 和 pnpm 9.x 或更新的版本。

由于前端代码是单独的 [repo](https://github.com/TransparentLC/squoosh-native-frontend)，因此不要忘了 clone submodule。

```sh
# 安装依赖
pip install -r requirements.txt

# 构建前端资源
cd squoosh
pnpm install
pnpm run build
cd ..

# 将构建好的前端资源打包为单个文件squoosh.pak
python bundle_squoosh.py

# 编译svpng，Linux下请将扩展名dll改为so
gcc -Wall -Ofast -march=native -mtune=native -shared -o libsvpng.dll svpng.c
strip libsvpng.dll

# 运行Squoosh Native
python main.py
```

如果需要开发调试的话：

```sh
# 在另一个终端中运行前端资源的dev server，无需打包
cd squoosh
pnpm run dev

# 在环境变量DEBUG为非空值的情况下运行main.py
DEBUG=1 python main.py
```

</details>

## 功能介绍

| 编码器 | Squoosh WASM | Native CLI | WASM 压缩时间 | CLI 压缩时间 | 比例 | 备注 |
| - | :-: | :-: | - | - | - | - |
| AVIF (libavif)   | ✅ | ✅ | 10621.86 | 3995.51 | 2.66x 🐇 | Effort 4 |
|                  |    |    | 72836.76 | 18994.40 | 3.83x 🐇 | Effort 7 |
| JPEG XL (libjxl) | ✅ | ✅ | 6486.63 | 3893.59 | 1.67x 🐇 | Effort 5 |
|                  |    |    | 12245.34 | 6771.26 | 1.81x 🐇 | Effort 7 |
| Jpegli           | ❌ | ✅ |  |  |  |  |
| MozJPEG          | ✅ | ✅ | 1806.30 | 2827.67 | 0.64x 🐢 |  |
| OxiPNG           | ✅ | ✅ | 15039.15 | 12065.13 | 1.25x 🐇 | Effort 2 |
|                  |    |    | 22692.70 | 18722.72 | 1.21x 🐇 | Effort 4 |
| QOI              | ✅ | ❌ |  |  |  |  |
| WebP             | ✅ | ✅ | 2352.89 | 3347.34 | 0.70x 🐢 | Effort 4 |
|                  |    |    | 3269.96 | 5048.69 | 0.65x 🐢 | Effort 6 |
| WebP2            | ✅ | ❌ |  |  |  |  |

*“压缩时间”的测试环境：Squoosh 自带的尺寸为 3872x2592 的 photo.jpg，除备注外均使用各编码器的默认配置，Windows 下的 Edge 浏览器及 Edge WebView2 Runtime，结果为 ms。*

*由于编码器的调用方式和版本不同，通过 WASM 和 CLI 压缩的图像只能做到质量和大小上相似，但是并不能得到相同的文件。*

其他的更改：

* 去除 Google Analytics 埋点
* 去除 Browser JPEG/PNG 编码器
    * 已经有更好的 MozJPEG 和 OxiPNG 了
* 添加图像质量指标的计算
    * 被 Squoosh 放弃的功能（[GoogleChromeLabs/squoosh  Quality metrics #271](https://github.com/GoogleChromeLabs/squoosh/issues/271)）
    * 在显示图片文件大小的位置悬停即可显示
    * 各指标的含义后述
* 支持 Jpegli 编码器
    * 目前还没有被 Squoosh 支持（[GoogleChromeLabs/squoosh [Feature Request] Support for jpegli #1408](https://github.com/GoogleChromeLabs/squoosh/issues/1408)）
    * 在相同的文件大小下，图片质量一般比 MozJPEG 更好

## 可能遇到的问题

### 如何启用命令行工具

将各个编码器/图像质量评估工具的 CLI 放在 `bin` 目录下就可以了，启动时可以通过下方的“Available native codecs/metrics”检查已经启用的工具。

你可以查看 `bin/README.txt` 来了解从哪里下载这些 CLI，也可以直接使用整合包。

使用没有配置 CLI 的编码器时将回退到使用 Squoosh 自带的 WASM 进行编码。

### 各个图像质量指标的含义

* DSSIM ∈ [0, +∞)
    * 越接近 0 表示两个图像越相似
    * 如果更熟悉 SSIM ∈ (0, 1] 的话，实际上 DSSIM = 1/SSIM - 1
    * 参见：[kornelski/dssim](https://github.com/kornelski/dssim#interpreting-the-values)
* Butteraugli ∈ [0, +∞)
    * 越接近 0 表示两个图像越相似
    * 一般来说，值为 1.5 时的失真大致相当于进行质量 90 的 JPEG 压缩，小于这个值的失真一般是可以接受的
    * 参见：[google/butteraugli Is there any suggest about the butteraugli compare result value? #22](https://github.com/google/butteraugli/issues/22)
* SSIMULACRA2 ∈ (-∞, 100]
    * 越接近 100 表示两个图像越相似
    * 在 [30, 100] 内的值可以理解为使用对应质量进行 JPEG 压缩的失真程度
    * 低/中等/高/极高质量的分界线为 30/50/70/90
    * 参见：[cloudinary/ssimulacra2](https://github.com/cloudinary/ssimulacra2#usage)

以上指标是在（缩放和减色后的）原始图片和压缩后的图片之间计算的，根据这些指标可以定量比较不同编码器或参数下的压缩效果。一般来说，选择一个指标进行比较就可以了。

### 是否会考虑添加○○功能

有计划添加的功能：

* Linux 版
* 其他与已有的相比更好的编码器的支持

不会考虑的功能：

* 多语言
    * 需要对原版 Squoosh 的前端做大量的修改
    * 很多编码器选项并没有合适的翻译
* 批量处理
    * 需要对原版 Squoosh 的前端做大量的修改
    * 有这种需求的话，自行编写脚本更适合
* macOS 版
    * 没有条件进行测试
* QOI 和 WebP2 的 CLI 支持
    * 并不是常用的格式
