# retro-gtk 1.0.2 适配笔记

## 编译环境
- 构建系统: meson（MesonToolchain + PkgConfigDeps）
- 编译日期: 2026-10-12
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，musl）
- 状态: built（conan create G2 通过：编译 + 上游测试 + test_package 全绿）

## 编译步骤

```bash
# 依赖（W0 预检通过，制品仓已发布）
#   glib/2.84.0.1、gtk/3.24.43、libepoxy/1.5.10
conan create archives/r/retro-gtk/1.0.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部流程（`conanfile.py`）：

1. `generate()`：PkgConfigDeps 生成依赖 .pc → staging glib 构建期工具 →
   补齐 glib .pc 缺口（-lintl / 工具变量 / gio-unix-2.0.pc）→ MesonToolchain
   写 machine file（ar/as/nm/ranlib 绝对路径、[binaries] 钉 staging 工具、
   libexecdir=libexec、可选特性开关、compat 头 -I + `-lEGL`）。
2. `build()`：apply patch → meson setup/compile → 在构建树内实跑上游 meson 测试
   （`RETRO_RUNNER_PATH` 指向构建树的 retro-runner）。
3. `package()`：`meson install --destdir` → 许可证 → 包内 ELF 统一剥旧
   `.codesign` 后重签（meson install 改写 rpath 会破坏链接期签名）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson setup` 报 `Unknown linker(s): [['llvm-ar']]`（`llvm-ar --version` ENOENT） | 构建机导出的 `AR/AS/NM/RANLIB/STRIP` 是裸名（llvm-*），conan 构建环境的 PATH 不一定能解析 | 与 libsoup3/3.6.5-r2 同款：清掉这五个变量，用 `shutil.which` 解析绝对路径钉进 machine file；`strip` 置空（strip 会破坏 .codesign） |
| 2 | `pkgconfig.generate got unknown keyword arguments "export_packages", "namespace"` | 上游 `retro-gtk/meson.build` 的 `pkg.generate()` 误带了 GI 专用关键字，现代 meson（1.12）直接报错 | 补丁 0002 删除这两个关键字（对 .pc 输出无影响） |
| 3 | `Dependency "gio-unix-2.0" not found` | glib 的 conan recipe 未声明 `gio-unix-2.0` 组件，PkgConfigDeps 不生成该 .pc；而 retro-gtk 显式依赖它 | 用生成的 `gio-2.0.pc` 克隆一份 `gio-unix-2.0.pc`（gio-unix API 就在 libgio-2.0 内，无额外库） |
| 4 | `glib-compile-resources: Operation not permitted`（rc=126） | 制品仓 glib 包内工具自带的 `.codesign` 在本机 `execve` 直接被拒（跨 UID/签名不匹配）；python 工具（glib-mkenums 等）的 shebang 亦不可用 | staging 到 bld 目录：python 工具套 `#!/bin/sh exec <解释器> <脚本>` wrapper；ELF 工具剥旧 `.codesign` 后用本机 signer 重签（同 gtk/3.24.43） |
| 5 | staging 出的 ELF 工具报 `Error loading shared library libgio-2.0.so.0` | 该工具无 RUNPATH，按 soname 找 glib 的动态库 | 构建环境把 glib 包 `lib/` 加入 `LD_LIBRARY_PATH` |
| 6 | `epoxy/egl.h file not found`（retro-runner/retro-gl-renderer.c） | 制品仓 `libepoxy/1.5.10` 以 `-Dglx=no -Degl=no -Dx11=false` 构建（OHOS 无窗口系统），不安装 `epoxy/egl.h` | `compat/epoxy/egl.h` 直接暴露平台 EGL API（`<EGL/egl.h>`/`<EGL/eglext.h>`，OHOS SDK sysroot），链接 `-lEGL`（运行期 `/system/lib64/libEGL.so`）；GL 侧仍走 libepoxy，未改写 |
| 7 | pulseaudio 后端无法启用：`Version conflict: glib/2.88.0 vs glib/2.84.0.1`（pulseaudio/17.0.1）或 `expat/2.8.2 vs expat/2.8.2.1`（pulseaudio/17.0） | 制品仓 pulseaudio 与 gtk3 栈的传递依赖钉死不同版本 | `-Dpulseaudio=disabled`（可选后端按可用依赖裁剪；与 bluez 因 libical 未发布而 `--disable-obex` 同款） |
| 8 | 上游 reftest 报 `Gtk-WARNING: cannot open display` → SIGTRAP | 上游 reftest 用 `gtk_test_init()`（需要显示连接；上游 CI 自身用 `xvfb-run` 包裹），而该 reftest 只比较软件渲染 pixdata、不建 widget | 补丁 0003：改用 `g_test_init()`（断言一条未删），使上游测试可在无显示器沙箱内实跑 |
| 9 | 上游测试可从构建树跑，但 `retro-runner` 编译期路径指向安装前缀 | `RETRO_RUNNER_PATH` 是编译期常量（`<prefix>/libexec/retro-runner`） | 补丁 0001：允许 `RETRO_RUNNER_PATH` 环境变量覆盖（同时解决非 root 重定位部署） |
| 10 | 消费者调用 `retro_core_boot()` 后 retro-runner 断言 `argc >= 3` | `retro-runner-process` 用 `g_get_application_name()` 作为 runner 的 argv[1]，纯 GLib 消费者未设置应用名时该值为 NULL，`g_subprocess_launcher_spawn` 的 argv 提前截断 | 消费者侧 `g_set_application_name()`（上游由 GTK/GApplication 或 g_test_init 顺带设置，隐藏了该前提）；已在 notes/MANIFEST 里作为使用注意记录 |
| 11 | `meson install` 后包内 `.so`/`retro-runner` 无法 dlopen/execve | meson 安装期会改写 rpath，使链接期写入的 `.codesign` 哈希失配 | packaging 后统一 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` + `chmod 755` |
| 12 | **CI（PR #15550 / 构建 #88913）：`ERROR: retro-gtk/1.0.2: Error in source() method` → `conan create failed`** | 官方归档只在 `gitlab.gnome.org`（`download.gnome.org/sources/retro-gtk/` 无 1.0.2 发布物，GNOME 镜像站亦 404），而该 host 在 CI 沙箱 `/-/archive/` 持续 **HTTP 503**；`ci/conan/build_and_test.sh` 的镜像回退白名单里 `get_mirrors()` 对 `gitlab.gnome.org` **只返回原 URL**（不改写），CI worker 又无 `curl`（pre-download `[Errno 2] No such file or directory: 'curl'`）→ 既无镜像兜底也无预下载兜底 | 改用**字节一致镜像**：只换 host，文件名与 sha256 不变（R37/L0j 源身份未变更），托管到 CI 可达平台并以**固定 commit 锚定**（`api/v5/repos/.../raw/<path>?ref=<sha>`，不用滚动分支）；三方 sha256 复核一致（官方归档 = 镜像下载 = conandata 声明）。范式见 `knowledge/drafts/DRAFT-ohos-conan-source-host-unreachable-byte-identical-mirror.md` 与 `siril/1.2.3` 先例 |

## 源码修改

3 个补丁（`patches/`）：

- `0001-retro-runner-process-env-path.patch`：`retro-runner` 路径允许由
  `RETRO_RUNNER_PATH` 环境变量覆盖（编译期常量 + 环境覆盖兜底）。
- `0002-retro-gtk-meson-pkgconfig-drop-gi-kwargs.patch`：删除
  `pkgconfig.generate()` 里 GI 专用的 `namespace` / `export_packages` 关键字
  （现代 meson 报 unknown keyword，configure 直接失败）。
- `0003-retro-reftest-headless-init.patch`：上游 reftest 的 `gtk_test_init()`
  改为 `g_test_init()`（无显示器沙箱可跑；断言未删）。

`compat/epoxy/egl.h`：OHOS 侧头文件补偿（内容详见文件中注释）。

## 依赖版本

- glib/2.84.0.1（传递：libffi/3.4.4、pcre2/10.45、zlib/1.3.1.1）
- gtk/3.24.43（传递：cairo、pango、gdk-pixbuf、atk、fribidi、libepoxy 等）
- libepoxy/1.5.10
- 平台库：EGL（OHOS SDK sysroot `libEGL.so`，运行期 `/system/lib64/libEGL.so`）

## 验证结果

```bash
# 1) 真实构建 + 上游测试（build() 内实跑）
conan create archives/r/retro-gtk/1.0.2 -pr:h=... -pr:b=...
#   Ok: 2  Fail: 0
#     1/2 retro-gtk:/retro-dummy reftest OK 0.33s
#     2/2 retro-gtk:RetroCore test      OK 1.78s

# 2) test_package（消费者 + 鸿蒙专项）
#   consumer（真实 API：runner + GDBus IPC + memfd 帧缓冲 + RetroPixdata）：
#     RETRO_GTK_OHOS_CONSUMER_OK frames=3 geometry=320x240 fps=60.00 frame=3 checksum=0x52f0e94d
#   test_ohos.sh：19/19 断言通过
#     all retro-gtk HarmonyOS assertions passed
```

## 使用注意

- `retro-runner` 装在 `libexec/`，库通过编译期 `RETRO_RUNNER_PATH`（= `/libexec/retro-runner`）
  或运行期环境变量 `RETRO_RUNNER_PATH` 定位它；**非 root/非 `/` 前缀部署必须设置该环境
  变量**（本适配新增的覆盖口）。
- 使用 `RetroCore` 的应用必须先 `g_set_application_name()`（runner 以应用名作为
  argv[1]，内部断言 `argc >= 3`）。
- 制品仓 EGL 头/库不在 libepoxy 包内，`compat/epoxy/egl.h` 仅供本包
  构建使用（不随包安装）。
- **R40 适配完整性人工确认项**：本包属图形/多媒体类，`RetroCoreView` 的 GL 显示
  路径（GTK3 + libepoxy + 平台 EGL）需要真实显示环境，沙箱内无法实跑；已实测覆盖的
  是 runner 进程 + 软件帧缓冲链路（上游 reftest 与消费者测试均走该路径），GL 显示
  路径的适配完整性需在带显示的真机上人工确认（构建期 `-lEGL` 链接、离屏 EGL 上下文
  创建代码路径已编译通过）。
---

**编译结束**: 2026-10-12 15:24
**最终状态**: built
