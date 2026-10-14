# libglvnd

## 简介

libglvnd 是 OpenGL / OpenGL ES / EGL 的 **厂商中立分发层**（GL Vendor-Neutral Dispatch）。
它对外导出标准的 GL / GLES / EGL 入口函数，运行时再根据 EGL/GLX 厂商配置（`egl_vendor.d`）
把调用转发到具体驱动，使同一进程可以同时加载多个厂商的 GL 实现。

## OHOS 适配

- 构建系统：Meson
- 关闭 `x11` / `glx`：OHOS 无 X11 服务端，GLX 后端不可用
- 关闭 `entrypoint-patching`：OHOS 对文件映射禁止 `mprotect(PROT_EXEC)`（W^X），
  厂商入口点打桩 ABI 无法工作；上游相关用例会自行 SKIP（见 notes.md）
- `libEGL` 以**静态库**形式打包：`/system/lib64/libEGL.so` 已存在，动态库同名会遮蔽系统
  加载器（铁律 R26）

## 依赖

- 无外部库依赖（仅系统 `m` / `pthread` / `dl`）
- 可选：`libx11` / `libxext` / `glproto` 仅在启用 x11/glx 时需要，本包已关闭

## 产物

| 类型 | 路径 |
|------|------|
| 动态库 | `lib/libGLdispatch.so*`、`lib/libOpenGL.so*`、`lib/libGLESv1_CM.so*`、`lib/libGLESv2.so*` |
| 静态库 | `lib/libEGL.a` |
| 头文件 | `include/GL`、`include/GLES`、`include/GLES2`、`include/GLES3`、`include/KHR`、`include/glvnd` |
| pkg-config | `lib/pkgconfig/libglvnd.pc`、`opengl.pc`、`egl.pc`、`glesv1_cm.pc`、`glesv2.pc` |

## 功能验证

```bash
conan create archives/l/libglvnd/1.7.0 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 主页: https://gitlab.freedesktop.org/glvnd/libglvnd
