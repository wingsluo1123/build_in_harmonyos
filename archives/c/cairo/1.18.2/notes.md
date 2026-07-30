# cairo 1.18.2 适配笔记

## 编译环境
- 构建系统: meson (裸 meson + ninja, 绕开 conan MesonToolchain OHOS 兼容问题)
- 编译日期: 2026-07-28
- 编译器: clang 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)
- 构建方式: 设备原生编译 (鸿蒙 PC HiShell)
- 状态: built

## 编译步骤

1. 安装 C 依赖 (cmd-pkgs): pixman/fontconfig/freetype/glib/libpng/harfbuzz/expat/libxml2/zlib/libffi/pcre2/libiconv
2. 安装 meson: `pip3 install meson`
3. 设置环境: `export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ PATH=... LD_LIBRARY_PATH=... PKG_CONFIG_PATH=...`
4. meson 构建:
```bash
meson setup builddir --prefix=$DEFAULT_PREFIX --default-library=shared \
  --native-file=ohos-native.ini \
  -Dc_args="-I/storage/Users/currentUser/usr/local/include -DHAVE_CTIME_R" \
  -Dtests=disabled -Dxlib=disabled -Dxcb=disabled \
  -Dfontconfig=enabled -Dwrap_mode=nofallback
ninja -C builddir -j4
ninja -C builddir install
```
5. 签名 .so: `binary-sign-tool sign -mode localSign -selfSign 1 -inFile libcairo.so.2 -outFile ...`
6. 创建 soname 符号链接: `libcairo.so.2 -> libcairo.so.2.11802.2`, `libcairo.so -> libcairo.so.2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ctime_r` 静态声明冲突 | cairo 声明 static ctime_r，OHOS sysroot time.h 已有同名非静态声明 | `-DHAVE_CTIME_R` 跳过 cairo 的 static 声明 |
| 2 | meson 找不到 clang | conan conanbuild.sh 覆盖 PATH, 只含 hnp/bin | `--native-file` 指定编译器全路径 + `export CC/CXX/PATH && meson ...` |
| 3 | git clone 挂死 | meson 尝试下载 glib subproject, 设备网络受限 | `-Dwrap_mode=nofallback` 禁止下载 subproject |
| 4 | lld 链接器找不到 libxml2.so.16 | lld 自身依赖 libxml2, 不在默认搜索路径 | LD_LIBRARY_PATH 含 SDK llvm/lib 目录 |
| 5 | .so 无法 dlopen | OHOS 强制 ELF 签名校验 | `binary-sign-tool sign -selfSign 1` |
| 6 | soname 符号链接缺失 | cmd-pkgs 只装版本化 .so, 无 soname 链接 | 手动创建 libfoo.so.N -> libfoo.so.N.X.Y |
| 7 | test_package dlopen 失败 | 系统库 (pixman/fontconfig) 不在 conan 运行环境 | `runenv_info LD_LIBRARY_PATH` 指向系统库目录 |
| 8 | conan settings.os.version 未定义 | 标准 conan 不识别 OHOS | 删除 settings_user.yml, 用 OHOS 适配版 conan (内置 OHOS) |

## 源码修改

无补丁。cairo 1.18.2 源码未修改, 所有适配通过 meson 构建选项和环境变量完成。

## 依赖版本 (cmd-pkgs 安装, 非 conan 依赖)

- pixman: 0.46.4
- fontconfig: 2.16.0
- freetype2: 26.6.20
- libpng: 1.6.43
- glib-2.0: 2.88.0
- harfbuzz: 14.2.0
- zlib: 1.3.1
- expat: 2.7.1
- libxml2: 2.15.3

## R40 深度适配说明

cairo 1.18.2 已移除 GL/GLES 后端。本构建禁用了 xlib/xcb 窗口系统后端, 仅保留以下渲染后端:
- **image** (内存位图)
- **png** (PNG 输出)
- **pdf** (PDF 输出)
- **ps** (PostScript 输出)
- **svg** (SVG 输出)

这是 headless 模式构建, 满足 svglib → reportlab → cairo 的 SVG→PDF 转换链路需求, 不涉及窗口渲染或 GPU 加速。如需窗口渲染支持, 需额外适配 OHOS EGL/Wayland 后端。

## 验证结果

- conan create: PASS (meson 编译 686 目标 + ninja install + .so 签名)
- test_package: PASS (dlopen libcairo.so + dlsym cairo_version)
- G1 (配方完整性): PASS
- G2 (conan create 干净构建): PASS
- G3 (系统同名库隔离): PASS
- W3 (本地 CI 模拟): PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcairo.so.2.11802.2 | 4.0MB | 核心库 (已签名) |
| libcairo-script-interpreter.so.2.11802.2 | 394KB | 脚本解释器 (已签名) |

## 注意事项

1. cairo 1.18.2 已移除 OpenGL/GLES 后端, 无需 -Dgl-backend=disabled
2. 使用 OHOS 适配版 conan (pip 从 CNB 源安装), 标准 conan 不识别 os=OHOS
3. binary-sign-tool 位于 /data/service/hnp/bin/ (OHOS SDK 自带, 无需 Java/DevEco)
4. soname 符号链接由 conanfile.py 的 _create_soname_symlinks() 自动创建

---

**编译结束**: 2026-07-28
**最终状态**: built
