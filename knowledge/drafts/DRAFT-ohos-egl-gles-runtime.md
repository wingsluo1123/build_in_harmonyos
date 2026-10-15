# DRAFT: OHOS 设备 EGL/GLES 运行时与 qtbase OpenGL 配方机制（设备 GL 栈实测）

## 错误签名

- `EGL_FOUND = FALSE`（qtbase configure 阶段，启 `FEATURE_egl` 后）
- `Error relocating ... libGLESv2.so / libEGL.so: symbol not found`（或 `Error loading shared library libGLESv2.so`）
- `QOpenGLContext ... symbol not found` / `QSslConfiguration ... symbol not found`（PyQt6 绑定导入阶段）
- `This plugin does not support createPlatformOpenGLContext!`（offscreen QPA）

## 根因（四层机制缺口，非"设备无 GL"）

**设备其实有可用 GL 栈**——不需要 mesa/llvmpipe。真正的缺口是名字、路径、打包、镜像四层：

1. **设备栈的真实形态**：`/system/lib64/libEGL.so`（"OpenHarmony EGL 1.4"）+
   `libGLESv3.so`——GLES2 入口点在 libGLESv3 里，**没有 libGLESv2.so 这个名字**。
   独立探针实测（dlopen libEGL → eglGetPlatformDisplayEXT surfaceless →
   eglInitialize OK → GLES2 context OK → pbuffer OK → makeCurrent OK）。
2. **构建期探测**：Qt 的 FindEGL/FindGLESv2 是裸 find_path/find_library，
   **不会自己搜 OHOS SDK sysroot**——直接开 `FEATURE_egl` 必报
   `EGL_FOUND = FALSE`，必须显式注入 `EGL_INCLUDE_DIR/EGL_LIBRARY/GLESv2_*`
   cache 变量。
3. **运行期名字**：编出来的 GL 库（libQt6Gui 等）记录 `NEEDED libEGL.so`、
   `libGLESv2.so`——包若不自带这两个名字，所有 GL 消费者（qtmultimedia、
   qttexttospeech、PyQt6 绑定）运行期 dlopen 直接失败。
4. **farm 镜像覆盖**：`qtbase-sql-dbus` 等分包镜像**全量 qtbase 库**且在合并
   farm 与运行期 LD 序里**优先覆盖**基础 qtbase——分包若还是 GL=OFF/SSL=OFF
   的旧库，基础包开了 GL 也没用（消费者加载到旧 Gui/Network，报
   `QOpenGLContext/QSslConfiguration symbol not found`）。

另：offscreen QPA 不实现 `createPlatformOpenGLContext`——验证 GL 必须
走 wayland QPA（自托管 compositor，见 DRAFT-ohos-wayland-gui-selfhosted-loop）。

## 配方机制（qtbase/6.11.1.4 实测可用）

- 特性开关：`INPUT_opengl=es2` + `FEATURE_opengl/opengles2/egl=ON`
  （`FEATURE_opengl=OFF` 时代 fatal 检查消失，es2 映射平台 GL）。
- sysroot 推导：从 profile 的 `tools.build:compiler_executables["c"]`
  （…/ohos/native/llvm/bin/clang）上溯三级到 native/，拼 `sysroot`；
  注入 `EGL_INCLUDE_DIR=<sysroot>/usr/include`、
  `EGL_LIBRARY=<sysroot>/usr/lib/aarch64-linux-ohos/libEGL.so`、
  `GLESv2_INCLUDE_DIR/GLESv2_LIBRARY` 同理。
- 包层别名（package()）：复制 sysroot stub（回落 `/system/lib64/libGLESv3.so`
  /`libEGL.so`）为包内 `libGLESv2.so` + `libEGL.so`——消费者 NEEDED 即可解析。
- 分包纪律：qtbase 系分包（sql-dbus 等）升版时**必须移植同一套
  OpenGL + openssl 设置**（openssl 链接用 glob 解析 libssl/libcrypto，兼容
  `libssl.so.3` 布局），否则镜像旧库抢加载。
- 验证链（每环独立可测）：EGL 探针 → conan test_package（GL 注入）
  → PyQt6 导入矩阵 → wayland 自托管渲染一帧。

## 实测记录（2026-10-03）

- 设备：`eglInitialize OK`（OpenHarmony EGL 1.4）、GLES2 context/_makeCurrent OK。
- qtbase/6.11.1.4：`libQt6OpenGL.so.6`/`libQt6OpenGLWidgets.so.6` 产出；
  base 测试组 21/21；test_package 过。
- PyQt6 全图（override qtbase/6.11.1.4 + GL+SSL sql-dbus/6.11.1.1）：
  21/21 绑定导入 OK，QtQuick/QtOpenGL/QtOpenGLWidgets/QtQuickWidgets 解锁。
- 端到端：wayland compositor + PyQt6 客户端 `platform=wayland visible=True`，
  compositor 收到 `SURFACE-DAMAGED`（真实帧提交）。
