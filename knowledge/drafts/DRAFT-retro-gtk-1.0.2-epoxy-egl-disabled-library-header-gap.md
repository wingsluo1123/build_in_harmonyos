# DRAFT: libepoxy 以 egl=no 构建导致的 epoxy/egl.h 缺口（retro-gtk 1.0.2 实测）

## 现象

```
../src/retro-runner/retro-gl-renderer.c:6:10: fatal error: 'epoxy/egl.h' file not found
#include "epoxy/egl.h"
         ^~~~~~~~~~~~~
```

meson 已经把 libepoxy 的 include 目录（`<libepoxy_pkg>/include`）放进命令行，
但该目录下只有 `epoxy/common.h`、`epoxy/gl.h`、`epoxy/gl_generated.h`。

## 根因

OHOS 无窗口系统（无 X11 / Wayland / Quartz），制品仓 `libepoxy/1.5.10` 的配方以
`-Dglx=no -Degl=no -Dx11=false` 构建，因此不安装 `epoxy/egl.h`
（libepoxy 只在 EGL 启用时才安装该头）。需要 EGL 的消费者（retro-gtk 的
`retro-runner` 要建离屏 GL 上下文）编译期缺头。

## 修复（本包采用的路径）

1. `compat/epoxy/egl.h`：只 `#include <EGL/egl.h>` / `<EGL/eglext.h>`，
   **不**引入 `epoxy_egl*` 转发层（retro-gtk 只调用原生 `egl*` 函数）。
   OHOS SDK sysroot 自带这两个头，裸 clang 默认可见。
2. `generate()`：`tc.extra_cflags.append("-I<compat>")` + `tc.c_link_args.append("-lEGL")`。
   运行期 EGL 实现来自 `/system/lib64/libEGL.so`（与 blur / coin3 / astromenace
   直链平台 EGL/GLES 同款）。
3. GL 侧不改：`epoxy/gl.h` + `libepoxy.a` 照常使用。

## 备选

- `requires("egl/1.0.5")`（制品仓已发布：EGL 头 + **静态** libEGL.a，cogl 先例），
  代价是静态 libEGL.a 为 C++ 实现，链接行需补 `-lc++_shared`。
- 不可修改 libepoxy 本身（跨库修改违反 PR 原子性；需要时另立依赖项任务）。

## 验证

retro-gtk 1.0.2：meson configure/compile 通过；`readelf -d` 产物含 `libEGL.so`；
`conan create` 全绿，test_package 的消费者测试在设备上真实启动 runner 并跑通
离屏渲染路径（软件核心；GL 显示路径需真实显示环境，未在沙箱内运行）。
