# SDL2_image

## 简介

SDL2_image 是 SDL2 的图像加载库，提供对多种图像格式的加载支持，包括 BMP、GIF、JPEG、LBM、PCX、PNG、PNM、SVG、TGA、TIFF、WEBP、XCF、XPM、XV 等格式。

## OHOS 适配

**适配要点**：
- 构建系统切换：由于 autotools 的 heredoc 在 HMDFS 上权限受限（E009/E011），推荐使用 CMake 构建
- 依赖 SDL2：必须先安装 SDL2（建议使用 cmd-pkgs 预编译包 `SDL2 2.30.0`）
- pkg-config 路径：需设置 `PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH`

**已知问题**：
- 无标准测试套件（cmake/test/ 为示例程序，非单元测试）
- config.guess/config.sub 需要补丁以识别 HarmonyOS 平台（E007）

**与 Linux 的差异**：
- 构建系统偏好 CMake 而非 autotools（避免 heredoc 权限问题）
- 需 ELF 签名才能执行（已由 ohc-run.py package 处理）

## 排除与替代

无排除项。

## 依赖

**编译依赖**：
- SDL2 >= 2.0.9（通过 pkg-config 检测）
- libpng（可选，PNG 支持）
- libjpeg（可选，JPEG 支持）
- libtiff（可选，TIFF 支持）
- libwebp（可选，WebP 支持）

**运行依赖**：
- SDL2 库文件
- 各图像格式库（根据启用的支持）

## 功能验证

```bash
# pkg-config 验证
pkg-config --modversion SDL2_image
# 期望输出: 2.6.0

pkg-config --cflags --libs SDL2_image
# 期望输出: -D_REENTRANT -I~/usr/local/include/SDL2 -L~/usr/local/lib -lSDL2_image -lSDL2

# 库文件验证
ls ~/usr/local/lib/libSDL2_image.so
file ~/usr/local/lib/libSDL2_image.so
# 期望: ELF 64-bit LSB shared object, ARM aarch64, dynamically linked

# 加载图像测试（示例程序）
# cd $BUILD_SRC_DIR && cmake/test/testload
```

## 参考

- 官网：https://www.libsdl.org/projects/SDL_image/
- 源码：https://github.com/libsdl-org/SDL_image
- 文档：https://wiki.libsdl.org/SDL2_image