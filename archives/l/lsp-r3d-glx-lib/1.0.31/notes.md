# lsp-r3d-glx-lib 1.0.31 适配笔记

## 编译环境
- 构建系统: makefile（上游自研 make 系统：`make config` → `make` → `make install`）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15（OHOS SDK 26.0.0.18，`-stdlib=libc++`，C++17）
- 状态: built

## 适配方案（路径 A：新写独立 OHOS 平台后端）

OHOS 没有 X11 / 桌面 GL / GLX，上游 `src/main/backend.cpp`（X11+GLX）无法编译；
但 OHOS 普通原生进程可用 `EGL_DEFAULT_DISPLAY` + pbuffer **离屏渲染**
（方法论：`knowledge/drafts/DRAFT-ohos-egl-headless-no-gles1-baseline.md`，
验证先例：freeglut 3.6.0 PR #10168，同 SDK 26 / Maleoon 916）。
因此**上游文件零改动**，新增独立平台后端：

| 文件 | 作用 |
|------|------|
| `ohos/backend.cpp` | 新 OHOS 后端（随配方导出、`source()` 拷入 `src/ohos/`），实现与上游 `src/main/backend.cpp` 同一组 `glx::backend_t` 虚表函数 |
| `patches/0001-...patch` | 公共头 `include/lsp-plug.in/r3d/glx/backend.h` 的 X11/GLX include 用 `__has_include` 条件化（公共头不引入平台宏，R8）；缺失时给占位 typedef 保持 `backend_t` 声明完整 |
| `patches/0002-...patch` | `src/Makefile`：make 命令行变量 `PLATFORM_OHOS=1` 时编译 `src/ohos/*.cpp` 而非 `src/main/backend.cpp`；平台标识只经 make 变量注入（R8） |
| `patches/modules/0001-...patch` | 预置的内嵌 lsp-common-lib 缺 GNU `qsort_r`（musl），与 lsp-common-lib / lsp-r3d-base-lib 归档同一补丁 |

### 后端实现要点（EGL 替换 GLX/X11）

- `eglGetDisplay(EGL_DEFAULT_DISPLAY)` + `eglInitialize`
- `init_offscreen`：`eglChooseConfig(EGL_PBUFFER_BIT, EGL_OPENGL_ES3_BIT)`
  → `eglCreatePbufferSurface`(1×1) → `eglCreateContext`(ES3，回退 ES2)
  → `eglMakeCurrent`
- `init_window`：OHOS 无原生窗口句柄 —— 创建**同样的离屏 pbuffer**，
  `*out_window = NULL`（语义变更，见下）
- `locate`：EGL surface 尺寸创建时固定 → 销毁并按新尺寸重建
- `start`/`finish`：`eglMakeCurrent` 绑定/解绑，保存并恢复原上下文
  （`eglGetCurrentDisplay/Surface/Context`）
- `sync`：`glFinish`（`glXWaitGL` 无 EGL 对应）
- `read_pixels`：`glReadPixels`（GL_RGBA 直读；BGRA/RGB/BGR 用临时缓冲
  软转换，GLES 不保证这些读回格式）
- `destroy`：`eglDestroySurface`/`eglDestroyContext`/`eglTerminate`
- **GL 入口一律经 `eglGetProcAddress` 运行时解析**：OHOS 直连的 GL 符号是
  调度空桩（`knowledge/drafts/DRAFT-ohos-gl-symbols-are-dispatcher-stubs.md`），
  链了能跑但静默无效。函数指针方案使产物**零 GL 未定义符号**（实测 13 个
  EGL 符号、0 个 gl*），无需 `-Bsymbolic` 包装层、无需 `-lGLESv3`。

### 构建命令（配方内的等价手动流程）

```bash
# 1) 解包主源码 + 预置四个内嵌依赖源码（替代上游 make fetch 的 git clone）
tar xzf lsp-r3d-glx-lib-1.0.31.tar.gz && cd lsp-r3d-glx-lib-1.0.31
tar xzf lsp-common-lib-1.0.49.tar.gz && mv lsp-common-lib-1.0.49 modules/lsp-common-lib
tar xzf lsp-r3d-iface-1.0.31.tar.gz  && mv lsp-r3d-iface-1.0.31  modules/lsp-r3d-iface
tar xzf lsp-r3d-base-lib-1.0.31.tar.gz && mv lsp-r3d-base-lib-1.0.31 modules/lsp-r3d-base-lib
tar xzf lsp-test-fw-1.0.35.tar.gz    && mv lsp-test-fw-1.0.35    modules/lsp-test-fw

# 2) 打本包补丁（主源码树）+ 内嵌 lsp-common-lib 补丁 + 拷入 OHOS 后端
patch -p1 -i patches/0001-ohos-public-header-glu-conditionalization.patch
patch -p1 -i patches/0002-ohos-makefile-build-ohos-backend.patch
patch -p1 -d modules/lsp-common-lib -i patches/modules/0001-lsp-common-lib-qsort_r-ohos.patch
mkdir -p src/ohos && cp ohos/backend.cpp src/ohos/

# 3) 配置 → 编译 → 安装
make config PLATFORM=Linux PLATFORM_OHOS=1 FEATURES="test strict" INSTALL_HEADERS=1 \
    LIBX11_CFLAGS= LIBX11_LDFLAGS= LIBGL_CFLAGS= LIBGL_LDFLAGS= \
    LSP_R3D_GLX_LIB_LDFLAGS="-lEGL" PREFIX=<prefix> CXX=clang++
make -j1 PLATFORM_OHOS=1 CXX=clang++     # 递归内嵌编译四个依赖
make install PLATFORM_OHOS=1
```

平台判定：上游 `make` 按 `uname -s` 探测，OHOS PC 返回 `HarmonyOS`
（未识别），`make config` 显式传 `PLATFORM=Linux`；OHOS aarch64 路径与上游
Linux 一致。`PLATFORM_OHOS=1` 只影响源码选择，源码中无平台宏（R8）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建期 `make fetch` git clone 四个 lsp-* 依赖，联网不可用 | 上游 `*TYPE=src` 内嵌编译 | conandata.yml 按上游 pin 版本登记四份 tarball，`source()` 预置到 `modules/` |
| 2 | 内嵌 lsp-common-lib 编译报 `no member named 'qsort_r'` | musl 无 GNU qsort_r | `patches/modules/0001`（与 lsp-common-lib 归档同内容，路径基准 `modules/lsp-common-lib`） |
| 3 | 公共头 `include/X11/Xlib.h` 等不存在 | OHOS 无 X11/GL/GLX | `__has_include` 条件化 + 占位 typedef（公共头不引入平台宏） |
| 4 | `make config` 经 pkg-config 探测到**宿主机** X11，把 `-lX11 -I...` 注入交叉链接 | `dependencies.mk` 在 PLATFORM=Linux 下加入 pkg 型 LIBX11/LIBGL；构建机装着 brew libx11 | config/make 命令行显式 `LIBX11_*= LIBGL_*=` 置空（命令行变量优先于 makefile 内 eval 赋值），构建结果与宿主机 pkg-config 环境无关 |
| 5 | 消费者链接静态库后 `Factory::enumerate` 返回空 | 注册用的静态 `Factory` 对象在合并归档成员内，仅引用 `enumerate` 不会拉入该成员 | 消费者先构造 `glx::factory_t`（公共 API）拉入成员、触发静态注册，再枚举 |
| 6 | `GLXContext`/`GLXFBConfig` 占位 typedef 写成 `void`/`void**` 编译失败 | 上游成员是值/指针语义 | 占位 typedef 与上游句柄形状一致（`void *GLXContext` / `void GLXFBConfig`） |
| 7 | W3 本地 CI 的 L0i 失败 `unpublished_deps`（lsp-r3d-iface、lsp-r3d-base-lib） | R36 发布顺序约束，两个依赖尚未发布到制品仓 | **发布顺序约束，非配方缺陷**：整链 lsp-test-fw → lsp-common-lib → lsp-r3d-iface → lsp-r3d-base-lib → lsp-r3d-glx-lib；本包 conan-verify 已全绿 |

## 源码修改

| 文件 | 补丁 | 内容 |
|------|------|------|
| `include/lsp-plug.in/r3d/glx/backend.h` | `patches/0001-ohos-public-header-glu-conditionalization.patch` | X11/GLX include `__has_include` 条件化 + 占位 typedef |
| `src/Makefile` | `patches/0002-ohos-makefile-build-ohos-backend.patch` | `PLATFORM_OHOS=1` 时编译 `src/ohos/*.cpp` 替代 `src/main/backend.cpp` |
| `modules/lsp-common-lib/src/main/stdlib.cpp`（预置后） | `patches/modules/0001-lsp-common-lib-qsort_r-ohos.patch` | musl qsort_r 移植（同 lsp-common-lib 归档 0001） |

上游 `src/main/backend.cpp`（X11/GLX 实现）在 OHOS 构建中**不被编译**，
文件本身零改动。OHOS 后端为新增文件 `src/ohos/backend.cpp`（配方资产）。

## 依赖版本

- 生产依赖：`lsp-r3d-iface 1.0.31`、`lsp-r3d-base-lib 1.0.31`（Conan requires，
  头文件传递；目标码内嵌编译，源码由 conandata 预置）。
- 构建期源码依赖：`lsp-common-lib 1.0.49`、`lsp-test-fw 1.0.35`（内嵌编译，
  不单独进生产依赖；common-lib 头文件经 iface/base 传递）。
- 系统链接依赖：`libEGL.so`（OHOS SDK，consumer 侧经 `cpp_info.system_libs`）。
- 编译器：OHOS SDK 26.0.0.18 clang/clang++ 15；profile：`ohos-local`。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify lsp-r3d-glx-lib 1.0.31 --profile ohos-local
#   G1: PASS   G2: PASS（含 test_package 消费者测试）
#   verdict: PASS
```

test_package 消费者测试（真渲染路径，经 `backend_t` 虚表）：
版本宏校验；`glx::factory_t` 构造（metadata/create 装配）+
`lsp::r3d::Factory::enumerate` 枚举拿到后端（id=glx_2x）；
`init_offscreen` → 重复 init 被拒（BAD_STATE）→ `locate(0,0,64,48)`
→ `get_location` 往返；`set/get_matrix` 往返 + NULL/非法类型拒绝；
**真渲染**：`set_bg_color(红)` → `start`（按背景色清屏）→ `sync`
→ `read_pixels` 全图断言 `255,0,0,255`；换蓝帧再断言 `0,0,255,255`
（证明 eglGetProcAddress 调度真实生效而非空桩）；背景色往返；
**平台能力边界如实断言**：`draw_primitives(NULL)→BAD_ARGUMENTS`、
`set_lights→BAD_STATE`（未绘图）、绘制中 `set_lights/draw_primitives
→ STATUS_NOT_IMPLEMENTED`；`init_window` 语义变更断言：返回 OK 且
窗口句柄为 NULL、离屏回退仍可渲染；`destroy` 释放。退出码 0。

上游测试：`src/test/` 只有测试框架入口（无用例），验证以 test_package 为主。

## 交付物

| 文件 | 说明 |
|------|------|
| `ohos/backend.cpp` | OHOS EGL 离屏后端源码 |
| `patches/0001-...patch` / `patches/0002-...patch` | 公共头条件化 / Makefile 平台分支 |
| `patches/modules/0001-...patch` | 内嵌 lsp-common-lib qsort_r 移植 |
| `reports/conan-create.log` | 完整构建日志 |
| `reports/conan-verify-report.md` | G0-G4 验证报告 |

包内容（shared=False 语义）：`lib/liblsp-r3d-glx-lib-1.0.31.a`（含内嵌的
lsp-r3d-iface / lsp-r3d-base-lib / lsp-common-lib / lsp-test-fw 目标码与
OHOS 后端）+ `lib/pkgconfig/lsp-r3d-glx-lib.pc` + 头文件
`include/lsp-plug.in/r3d/glx/**`；`shared=True` 时 .so 自签（DT_NEEDED 仅
libEGL.so / libc.so）。

## 注意事项

- **平台能力边界（如实声明，非缺陷）**：
  1. `init_window` 无可见窗口：OHOS 无窗口系统，创建离屏 pbuffer 并返回
     NULL 窗口句柄；
  2. GL 1.x 固定管线（`set_lights` / `draw_primitives`：光照、顶点/索引
     缓冲绘制）在只有 GLES3.2 的 OHOS 上不存在，返回
     `STATUS_NOT_IMPLEMENTED`，**不渲染、不粉饰**；
  3. 桌面 GL 专用状态（`GL_SMOOTH` 着色、`GL_RESCALE_NORMAL`、
     `GL_COLOR_MATERIAL`、`GL_POLYGON_OFFSET_POINT/LINE`、`glXWaitGL/X`、
     `glXSwapBuffers`）在 EGL/GLES 下无对应，已移除或替换（sync 用
     `glFinish`）；
  4. `read_pixels` 仅 RGBA 为 GL 原生读回，其余格式软转换。
- **发布顺序（R36）**：本包 requires lsp-r3d-iface 与 lsp-r3d-base-lib，
  须先发布；整链顺序 lsp-test-fw → lsp-common-lib → lsp-r3d-iface →
  lsp-r3d-base-lib → lsp-r3d-glx-lib。
- **补丁位置**：`patches/modules/` 不进 conandata 的 `patches` 表，由配方
  `source()` 预置后应用；移到 `patches/` 顶层会让 clean-verify 的 G0 失败。
- **finish 的非阻塞告警（与 lsp-r3d-base-lib 先例一致）**：Step3 的 G0 干净构建
  验证报「找不到原始 tarball」（G0 只会按 autotools 语义找本地 tarball 重编，
  makefile 项目必然失败，非阻塞）；真实构建质量以 conan-verify 全绿为准。
---

**编译结束**: 2026-09-29 07:33
**最终状态**: built
