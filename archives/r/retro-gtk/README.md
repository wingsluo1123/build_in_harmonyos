# retro-gtk

基于 GObject 的 [Libretro](https://www.libretro.com/) 前端库（GNOME Games 的模拟器
内核宿主）。它把 Libretro 核心（任意 `libretro_*.so`）封装成 `RetroCore`，在独立的
`retro-runner` 进程里运行核心——两者之间用私有 GDBus 连接通信、用 memfd 共享
帧缓冲——再由 GTK3 控件（`RetroCoreView`）与 GL 渲染视频。

## OHOS 适配

- **构建系统**: Meson（Conan `MesonToolchain` + `PkgConfigDeps`）
- **依赖**: `glib/2.84.0.1`、`gtk/3.24.43`、`libepoxy/1.5.10`（均取自制品仓）；
  平台 EGL 走 OHOS SDK sysroot（运行期 `/system/lib64/libEGL.so`）
- **产物**: `lib/libretro-gtk-1.so.0`、`libexec/retro-runner`、
  `include/retro-gtk/*.h`、`lib/pkgconfig/retro-gtk-1.pc`
- **关键适配点**（细节见 `1.0.2/notes.md`）:
  1. glib 包内构建期工具在 HMFS 上不可直接执行 → staging（python 工具套 wrapper、
     ELF 工具剥旧 `.codesign` 后重签）
  2. glib 的 conan 包缺 `gio-unix-2.0` 组件与 `-lintl`/工具变量 → 在生成的 .pc 上补齐
  3. 制品仓 libepoxy 以 `egl=no` 构建、无 `epoxy/egl.h` → `compat/epoxy/egl.h`
     直接暴露平台 EGL API + 链接平台 libEGL
  4. 上游 pulseaudio 后端与 gtk 栈版本互斥 → `-Dpulseaudio=disabled`
  5. 包内 ELF 统一重签名（meson install 改写 rpath 会破坏链接期 `.codesign`）

## 使用注意

```bash
# 1) 使用 RetroCore 前必须设置应用名（retro-runner 以它作为 argv[1]）
g_set_application_name ("my-frontend");

# 2) retro-runner 装在 <pkg>/libexec/retro-runner；库按编译期前缀
#    （/libexec/retro-runner）查找它。非 root/非 "/" 部署需显式指定：
export RETRO_RUNNER_PATH=/path/to/pkg/libexec/retro-runner
```

## 依赖

- `glib/2.84.0.1`
- `gtk/3.24.43`
- `libepoxy/1.5.10`

## 验证

```bash
conan create archives/r/retro-gtk/1.0.2 -pr:h=ci/conan/profiles/ohos-aarch64 \
                                        -pr:b=ci/conan/profiles/ohos-aarch64
# 上游测试: Ok 2 / Fail 0（meson test，build() 内实跑）
# 消费者测试: 真实 RetroCore 启动 runner + 假核心，逐像素校验视频输出，
#             设备端整帧校验和 0x52f0e94d（鸿蒙专项 19/19 断言）
```
