# Waffle

## 简介
跨平台 GL/EGL context 与 window 创建库（Intel/VMware/ChromeOS 等图形栈常用）。
提供统一的 API 在运行时选择合适的 OpenGL API 与窗口系统（GLX/Wayland/GBM/
X11-EGL 后端）以及核心的属性列表/错误/初始化逻辑。

## 功能概述
- 统一的 context/window/display 创建 API（`waffle_init`、`waffle_display_connect`、
  `waffle_config_choose`、`waffle_context_create`、`waffle_window_*`）
- 跨平台后端：GLX、Wayland、X11/EGL、GBM、surfaceless-EGL、CGL、WGL
- 核心工具：属性列表（`waffle_attrib_list_*`）、错误处理（`waffle_error_*`）、
  `wflinfo` 命令行工具

## OHOS 适配
- 采用上游主推的 **meson** 构建（CMake 构建已废弃，且 Linux 目标强制至少启用
  一个 GL 后端，OHOS 无法满足）。
- OHOS PC 不提供 GL/EGL/GBM/DRM/X11/Wayland 图形/窗口子系统，meson 以 auto
  探测全部 GL 后端均 disabled，本配方构建**核心库 + linux_platform 薄层**，
  不含任何 GL 后端。
- 真机与 CI PATH 均无 meson，采用 vendored meson 1.11.2（源码随配方下载，
  build 时经 python3 进程内 sys.path 注入调用）；cmocka 单元测试框架同样
  vendoring 到 `subprojects/cmocka/` 并设 `wrap_mode=nodownload`。
- 上游核心单元测试（3 个 cmocka 可执行文件共 86 用例）与平台无关，OHOS 上
  全部构建并通过；GL 后端功能测试（gl_basic per platform）因后端禁用而不注册。

## 依赖关系
- 编译依赖：标准 C 库、POSIX threads、dl（均系统自带）
- 运行依赖：无第三方运行时依赖
- 测试依赖：vendored cmocka 1.1.2

## 参考资料
- 官网: https://waffle.freedesktop.org/
- 发布包: https://waffle.freedesktop.org/files/release/
