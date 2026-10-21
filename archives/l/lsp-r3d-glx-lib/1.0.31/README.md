# lsp-r3d-glx-lib

## 简介

lsp-r3d-glx-lib 是 [lsp-plugins](https://github.com/lsp-plugins) 项目的
**GLX 3D 渲染后端**：`glx::backend_t`（继承 `r3d::base_backend_t`）基于
X11 + GLX 实现 3D 场景渲染的窗口/离屏上下文管理、光照、图元绘制与像素回读，
经工厂（`glx::factory_t` / `lsp_r3d_factory`）向消费者暴露。

## OHOS 适配

- **适配方式（路径 A：新写独立平台后端，上游文件零改动）**：OHOS 无 X11 /
  桌面 GL / GLX，但普通原生进程可用 `EGL_DEFAULT_DISPLAY` + pbuffer 离屏
  渲染（`knowledge/drafts/DRAFT-ohos-egl-headless-no-gles1-baseline.md`）。
  新增 `ohos/backend.cpp`（配方导出、`source()` 拷入 `src/ohos/`），实现与
  上游 `src/main/backend.cpp` **同一组 `glx::backend_t` 虚表函数**，用 EGL
  替换 GLX/X11；构建系统补丁使 `PLATFORM_OHOS=1`（make 命令行变量）
  时编译 `src/ohos/*.cpp`，平台标识**只经 make 变量注入**，源码里不裸用
  平台宏（R8）。
- **公共头条件化**：`include/lsp-plug.in/r3d/glx/backend.h` 的 X11/GLX
  include 用 `__has_include` 条件化（公共头不引入平台宏），缺失时给占位
  typedef 保持 `backend_t` 声明完整。
- **EGL 后端流程**：`eglGetDisplay(EGL_DEFAULT_DISPLAY)` +
  `eglInitialize` → `eglChooseConfig(EGL_PBUFFER_BIT, EGL_OPENGL_ES3_BIT)`
  → `eglCreatePbufferSurface` → `eglCreateContext`（ES3，回退 ES2）→
  `eglMakeCurrent`；`locate` 改变尺寸时销毁并重建 surface（EGL surface
  尺寸不可变）；`start/finish` 经 `eglMakeCurrent` 绑定/解绑并保存恢复原
  上下文；`sync` 用 `glFinish`（`glXWaitGL` 无对应）；`read_pixels` 用
  `glReadPixels`；`destroy` 走 `eglDestroySurface/eglDestroyContext/
  eglTerminate`。
- **GL 符号经 `eglGetProcAddress` 运行时解析**：OHOS 直连的 GL 符号是
  调度空桩（链得上、跑得了、静默无效，见
  `knowledge/drafts/DRAFT-ohos-gl-symbols-are-dispatcher-stubs.md`），
  函数指针方案使产物零 GL 未定义符号（实测 13 个 EGL、0 个 gl*），无需
  `-Bsymbolic` 包装层与 `-lGLESv3`，链接只需 `-lEGL`。
- **依赖处理**：四个内嵌依赖（lsp-common-lib 1.0.49 / lsp-r3d-iface 1.0.31 /
  lsp-r3d-base-lib 1.0.31 生产 + lsp-test-fw 1.0.35 测试）按上游
  `*TYPE=src` 内嵌编译，源码由 conandata.yml 预置到 `modules/`，构建离线
  可复现；`lsp-r3d-iface` 与 `lsp-r3d-base-lib` 按 R27 声明为 Conan 依赖
  （`transitive_headers=True`，两者头文件属于本包公共接口）。上游 pkg 型
  系统依赖 `LIBX11/LIBGL` 在 OHOS 不存在且新后端不依赖它们——构建时显式
  清空其 pkg-config 标志，避免把宿主机 X11 注入交叉链接。
- **交付物**：`liblsp-r3d-glx-lib-1.0.31.a`（含内嵌依赖目标码与 OHOS 后端，
  DT_NEEDED 仅 libEGL.so/libc.so）+ `lib/pkgconfig/lsp-r3d-glx-lib.pc` +
  头文件 `include/lsp-plug.in/r3d/glx/**`；`shared=True` 时 .so 自签名。
- **版本**：1.0.31（上游 tag）。

## 平台能力边界（如实声明，不是缺陷）

| 能力 | OHOS 实际语义 |
|------|--------------|
| `init_window` | OHOS 无窗口系统：无原生窗口句柄，创建**离屏 pbuffer** 并返回 NULL 窗口句柄；无可见窗口 |
| `set_lights` / `draw_primitives` | GL 1.x 固定管线（`glLight*`/`glVertexPointer`/`glDrawArrays`…）在只有 GLES 3.2 的 OHOS 上**不存在**，返回 `STATUS_NOT_IMPLEMENTED`，不渲染 |
| 桌面 GL 状态 | `GL_SMOOTH` 着色、`GL_RESCALE_NORMAL`、`GL_COLOR_MATERIAL`、`GL_POLYGON_OFFSET_POINT/LINE`、`glXWaitGL/X`、`glXSwapBuffers` 无 EGL/GLES 对应，移除或替换（sync→`glFinish`） |
| `read_pixels` 格式 | 仅 RGBA 为 GL 原生读回；BGRA/RGB/BGR 以临时缓冲软转换 |
| 尺寸变更 | EGL surface 尺寸创建时固定：`locate` 销毁并按新尺寸重建 |

参照先例：freeglut 3.6.0（PR #10168）同样"新写平台后端 + 声明 GLES1 固定
管线不可用"。

## 功能验证

```bash
python3 scripts/ohc-run.py conan-verify lsp-r3d-glx-lib 1.0.31 --profile ohos-local
#   G1: PASS   G2: PASS（含 test_package 消费者测试）
#   verdict: PASS
```

消费者测试（`test_package/test.cpp`，经 `backend_t` 虚表）：

- 工厂：`glx::factory_t` 构造（metadata/create 装配）+
  `lsp::r3d::Factory::enumerate` 枚举拿到后端（id=`glx_2x`）；
- 上下文：`init_offscreen`（重复 init 被拒 `BAD_STATE`）→ `locate(0,0,64,48)`
  → `get_location` 往返；
- **真渲染**：`set_bg_color`（红）→ `start` 按背景色清屏 → `sync` →
  `read_pixels` 全图断言 `255,0,0,255`；换蓝帧再断言 `0,0,255,255`
  —— 证明 GL 调度真实生效（空桩下读回为 0）；
- 矩阵/颜色：`set/get_matrix` 往返 + NULL/非法类型拒绝；`set/get_bg_color`
  往返；
- 能力边界：`set_lights`/`draw_primitives` 如实断言
  `STATUS_NOT_IMPLEMENTED`（不把不可用功能写成通过）；
- `init_window`：返回 OK 且窗口句柄为 NULL，离屏回退可渲染；
- `destroy` 释放。

实测输出：

```
lsp-r3d-glx-lib 1.0.31
backend metadata: id=glx_2x display=openGL 2.0+ (GLX) wnd_type=1
consumer checks passed
```

上游测试：`src/test/` 仅测试框架入口（无用例），验证以 test_package 为主。

## 依赖

- `lsp-r3d-iface 1.0.31`、`lsp-r3d-base-lib 1.0.31`（Conan requires，
  头文件传递；目标码内嵌编译）
- 构建期源码：`lsp-common-lib 1.0.49`、`lsp-test-fw 1.0.35`（内嵌编译）
- 系统库：`libEGL.so`（消费者侧经 `cpp_info.system_libs` 传递）

发布顺序（R36）：lsp-test-fw → lsp-common-lib → lsp-r3d-iface →
lsp-r3d-base-lib → lsp-r3d-glx-lib。
