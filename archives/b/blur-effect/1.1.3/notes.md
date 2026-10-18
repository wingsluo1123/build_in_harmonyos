# blur-effect 1.1.3 适配笔记

> 上游：https://github.com/sonald/blur-effect （deepin 离屏高斯模糊工具，tag 1.1.3）
> 产物：`blur_image` 命令行工具（bin/blur_image，OpenGL ES 3.0 离屏渲染）

## B 判定 hit 依据（同一上游的第二归档，主动披露）

| 事项 | 实测读数 |
|---|---|
| 上游身份 | `sonald/blur-effect` tag `1.1.3`，直链 `https://github.com/sonald/blur-effect/archive/refs/tags/1.1.3.tar.gz` → HTTP=200 / 22657 B / sha256 `80baead168e117cdbd7dd915dac94b8055e63dc05ec5797f3030acfaf19e5654` |
| 已合入姊妹配方 | `archives/b/blur/1.1.3/`（package_type=application、homepage 同为 `sonald/blur-effect`），**在 upstream/main 树内** |
| 姊妹配方已发布 | `conan download --only-recipe blur/1.1.3 -r ohpcd` → revision `9addfb36f648f708107c9e8f716765a6`（2026-09-16） |
| 本包归档目录 | `archives/b/blur-effect` 在本分支基线 upstream/main 树内为 0 文件 ⇒ 无同名归档 |
| 本包与姊妹的关系 | 同一份源码（sha256 逐字一致）、**复用其补丁 0001/0002 与 test_package 成熟解，未产生新机制** ⇒ 不满足 `create`，判 `hit` |
| 为何仍交付 | 平台任务 6030 指定的包名是 `blur-effect`，故以独立归档名交付同一份源码的第二个归档。**此点如实披露**，是否视为重复由 reviewer 判断 |

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-18
- 编译器: clang/clang++ 15（设备原生构建，非交叉）
- conan: 2.29.1（OHOS 适配版，`os=OHOS` 为有效枚举）
- 状态: published

## R51 上游测试清点（上游 N_static=0 证据）

| 清点方法 | 结果 |
|---|---|
| CMakeLists.txt 全文 grep `enable_testing\|add_test\|make check\|check:` | 无任何匹配 |
| 源码树 `ls tests test` | 目录不存在 |
| 上游源文件 | 仅 2 个：`src/blur_image.cc`（主程序）、`src/main.cc`（BUILD_DEMO demo，默认 off 不构建） |

**结论：上游 1.1.3 无任何测试用例（N_static=0），全部测试由鸿蒙侧 test_package 承载。**

## 编译步骤

```bash
# 1. 依赖解析（conan 制品仓）
conan install --requires=gdk-pixbuf/2.44.6.1 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 2. 配方内构建：apply_conandata_patches → cmake.configure → cmake.build → cmake.install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游依赖 libdrm/gbm/pkg-config egl/glesv2 全缺失 | OHOS 无 /dev/dri、无 libgbm；系统 EGL/GLESv3 不提供 .pc 文件 | 补丁 0002 改为 `eglGetDisplay(EGL_DEFAULT_DISPLAY)` + pbuffer surface 替代 GBM/DRM 路径；补丁 0001 去掉 gbm/egl/glesv2 的 pkg-config 依赖并直链平台库 `EGL GLESv3` |
| 2 | 原生路线本机实测不可行 | `conan install --requires=mesa/24.3.4.1.1.1 --build=never -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` 失败：首条真实错误 `ERROR: Missing prebuilt package for 'libxrender/0.9.12'` ⇒ 缓存内检不到 `gbm.pc/glesv2.pc/egl.pc/libdrm.pc` | 不保留 mesa 原生 GBM/DRM 路线（即便有 .pc，运行时也无 /dev/dri）；走已合入姊妹配方的 EGL pbuffer 成熟解 |
| 3 | `cmake_minimum_required(VERSION 2.8.11)` 被 cmake 4.1.2 拒绝 | cmake 4.x 移除 <3.5 兼容（首错 `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed`） | 补丁 0001 升至 3.10（同上游 PR#7 / nixpkgs cmake-4.patch 方向） |
| 4 | 链接错误 `unable to find library -lwebp/-lglib-2.0/...` | `pkg_check_modules` 只在 CMake 目标属性带 libdir，裸 `target_link_libraries(${DEPS2_LIBRARIES})` 不注入 `-L` | CMakeLists 补 `link_directories(${DEPS2_LIBRARY_DIRS})`（补丁 0001） |
| 5 | `getopt` 不识别 `blur_image test.png -o out.png`（infile 在前） | musl getopt 无 GNU 参数重排（glibc 扩展） | 调用时选项前置（`blur_image -o out.png test.png`），未改源码 |
| 6 | shader 编译错误 P0005 `#version must be on the first line` | 上游 `R"(` 字面量带前导换行；Linux Mesa 容忍，OpenHarmony GLES 严格 | 补丁 0002：7 处 shader 改 `R"(#version` 贴起始 |
| 7 | shader 编译错误 L0002 `No matching function for call to 'texture2D'` | GLSL ES 3.00 已废弃 `texture2D`（ES 1.00 函数）；Mesa 宽松，OHOS 严格 | 补丁 0002：2 处 `#define texpick texture2D` → `texture` |

## 源码修改（2 个补丁，均 portability，均无 `__OHOS__` 宏）

> 两个补丁与已合入姊妹包 `archives/b/blur/1.1.3/patches/` 逐字相同（同一上游同一份源码 ⇒ 同源复用，B 判定 hit 的组成部分）。

1. **0001-CMakeLists.txt.patch**（构建系统）
   - `cmake_minimum_required` 2.8.11 → 3.10
   - `DEPS2` 移除 `libdrm/gbm/egl/glesv2`（OHOS 无 DRM 渲染节点；EGL/GLESv3 直链平台库）
   - `target_link_libraries` 补 `EGL GLESv3`；补 `link_directories(${DEPS2_LIBRARY_DIRS})`
2. **0002-src-blur_image.cc.patch**（EGL pbuffer 替代 GBM/DRM + GLES 严格性）
   - 删 `gbm.h`/DRM 设备探测（`is_device_viable`/`choose_best_card`/`open_best_device` 等）、`ctx` 的 fd/gbm 字段、`getopt` 的 `-d` 选项
   - `setup_context()` 重写：`eglGetDisplay(EGL_DEFAULT_DISPLAY)` + `EGL_PBUFFER_BIT` + `eglCreatePbufferSurface`（**按 ctx.width/ctx.height 创建**；历史 W4 审计 P1：曾硬编码 64x64 导致大图回读越界 UB，256x256 回归用例已入 test_package）
   - 7 处 shader `R"(` 前导换行 → `R"(#version`；2 处 `texpick texture2D` → `texture`

## 依赖版本

| 依赖 | 版本 | 来源 |
|---|---|---|
| gdk-pixbuf | 2.44.6.1 | conan ohpcd（传递 glib/libpng/libjpeg-turbo/libtiff/libwebp/zstd/zlib） |
| EGL / GLESv3 | 系统 1.4 / 3.0 | OpenHarmony 平台库（SDK sysroot 头文件 + stub，裸 clang 默认可见） |
| glew / glfw / libdrm / mesa | 不需要 | 仅 BUILD_DEMO=on 时需 glew/glfw3（OHOS 永远关闭）；libdrm/mesa 仅在原生 GBM 路线需要，本包已移除该路线 |

## 验证结果

```bash
# 上游无测试可运行（N_static=0）；消费者测试 = test_package/test.sh（2 用例 × 5 断言 = 10 断言）
# 详见下游执行记录（G0-G4/L2/L4/L5 + test_package 实际输出）
```

## 注意事项

- **命令行调用**：musl getopt 无 GNU 重排，`-o` 等选项必须放在输入文件路径之前（usage 已是此序）。
- **渲染设备**：OHOS 上走 EGL 默认显示，`-d drmdev` 选项已随 GBM 路径移除。
- **BUILD_DEMO**：依赖 glew/glfw3（X11 窗口系统），OHOS 永远关闭，勿在配方中开启。
- **test_package 二进制 fixture**：GitCode PR `.diff` 端点不携带二进制补丁数据，CI `git apply` 对 PR 内二进制文件必失败 ⇒ fixture 一律 base64 文本随仓（`*.png.b64`），test.sh 运行时 `base64 -d` 解码到 `$TMPDIR` 再用。

---
**编译结束**: 2026-10-18
**最终状态**: published
---

**编译结束**: 2026-10-18 04:31
**最终状态**: built
