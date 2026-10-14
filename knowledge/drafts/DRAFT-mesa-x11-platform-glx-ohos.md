# DRAFT: OHOS PC 上 mesa 启用 EGL x11 window 平台 + GLX（platforms=x11 + glx=dri）

- 条目主题：任何依赖 GL/EGL/GLX 的 OHOS PC 库（gtk4 gsk-gl、libepoxy GLX 上游测试等）需要 mesa 提供 EGL x11 window 平台（`WINDOW_BIT` 配置 + `EGL_EXT_platform_x11`/`KHR_platform_x11`）与 `libGL.so.1` 时，mesa 配方的启用方法。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：mesa 24.3.4.1.1.1（上游 Mesa 24.3.4）；同范式适用于所有消费 GL/EGL/GLX 的 OHOS PC 库。
- 产生源：mesa-24.3.4.1.1.1-r01-pc3-1-20261009T092543Z（gtk4 gsk-gl 2450 项恢复目标）。

## 错误特征
- `meson.build: ERROR: Values "surfaceless, drm" for option "platforms" are not in allowed choices: "auto, x11, wayland, haiku, android, windows, macos"`
- `meson.build: ERROR: Value "enabled" for option "glx" is not one of the choices. Possible choices: "auto", "disabled", "dri", "xlib"`
- `Dependency "xext"/"xfixes"/"glproto"/"dri2proto"/"xrandr" not found`
- `fatal error: 'X11/Xlib-xcb.h' file not found`（loader_dri3_helper.c）
- `fatal error: 'xcb/xcb.h' file not found`（gbm_dri.c via loader_dri_helper.h）
- 消费侧：`WINDOW_BIT=0`、`EGL_EXT_platform_x11` 缺失、无 `libGL.so.1`

## 根因
1. mesa 24.3.4 默认 `platforms=` 空（无窗口系统平台），EGL 仅 surfaceless/PBUFFER 配置，无 X11 window 变体与 `EGL_EXT_platform_x11`/`KHR_platform_x11`；Xvfb 又无 GLX 且 mesa 无 libGL.so.1 → 消费库 gsk-gl 全灭。
2. mesa 的 `platforms`/`glx` 选项合法值约束严格：surfaceless/drm 不是 platforms 的合法值（surfaceless 是 EGL 内建自动启用、drm 由 gbm/dri 提供）；glx 不接受 `enabled`。
3. x11 平台启用后 meson 需要 X11 客户端依赖链与协议 pc，且两个目标（libdri、dri_gbm）的依赖列表未挂 x11-xcb/xcb include 路径。

## 修复（mesa 配方侧）
```python
def requirements(self):
    self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
    self.requires("libxcb/1.16", transitive_headers=True, transitive_libs=True)
    self.requires("xorgproto/2025.1", transitive_headers=True)
    self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
    self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)
    self.requires("libxshmfence/1.3.3", transitive_headers=True, transitive_libs=True)
    self.requires("libxxf86vm/1.1.5", transitive_headers=True, transitive_libs=True)
    self.requires("glproto/1.4.17", transitive_headers=True)
    self.requires("libxrandr/1.5.5", transitive_headers=True, transitive_libs=True)

def generate(self):
    PkgConfigDeps(self).generate()
    # xorgproto 的协议 pc（dri2proto.pc 等）PkgConfigDeps 不生成、meson 探测
    # PKG_CONFIG_PATH 只含 generators 目录 → 复制进 generators
    if "xorgproto" in self.dependencies:
        xg = os.path.join(self.dependencies["xorgproto"].package_folder, "share", "pkgconfig")
        for pc in ("dri2proto.pc", "glproto.pc"):
            src = os.path.join(xg, pc)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(self.generators_folder, pc))
    tc = MesonToolchain(self)
    tc.project_options["platforms"] = "x11"      # 不是 surfaceless,drm,x11
    tc.project_options["glx"] = "dri"             # 不是 enabled
    ...
```
补丁（meson.build）：
- `src/gallium/frontends/dri/meson.build`：`with_dri_platform=='drm'` 分支补 `deps_for_libdri += dep_x11_xcb`（loader_dri3_helper.c 需 `X11/Xlib-xcb.h`）
- `src/gbm/backends/dri/meson.build`：`with_platform_x11` 时补 `deps_gbm_dri += dep_xcb`（loader_dri_helper.h 拖入 xcb/dri3/present/sync）
- build 目标列表加 `GL`（libGL.so.1）与 `dril_dri`（meson install 要求）

## 验证口径（对照 24.3.4.1.1 WINDOW_BIT=0）
- `eglChooseConfig` 返回 `WINDOW_BIT` 配置（16 个，SURFACE_TYPE 含 0x4）
- 客户端扩展含 `EGL_EXT_platform_x11`、`EGL_KHR_platform_x11`
- `libGL.so.1` 产出（SONAME libGL.so.1，glXGetProcAddress 导出）
- Xvfb :199 进程级：`eglGetPlatformDisplay(EGL_PLATFORM_X11)` + `eglCreateWindowSurface` + `eglMakeCurrent` + 渲染 readback，exit 0

## 适用边界 / 反例
- 仅客户端依赖（libx11/libxcb/xorgproto 等）；禁止 Xvfb 服务器端依赖混入
- mesa 24.3.4 的 `platforms`/`glx` 合法值约束（见上），不能照抄其他版本的选项写法
- EGL 上下文属性：mesa 该构建不支持 `EGL_CONTEXT_CLIENT_TYPE`（BAD_ATTRIBUTE），用 `EGL_CONTEXT_MAJOR_VERSION` 建 GLES2 上下文
- 不适用：纯 surfaceless 消费（无需 x11）、无 X 消费端（保持 platforms= 空）

## 关系
- similar_to：mesa 24.3.4 GBM/EGL 适配知识、mesa 24.3.4.1 共享 EGL 知识
- caused_by：mesa 24.3.4 `platforms=` 空（无窗口平台）
- prerequisite_of：gtk4 gsk-gl EGL x11 window 路径、libepoxy GLX 上游测试、任何 GL/EGL/GLX 消费库
- conflicts_with：无
