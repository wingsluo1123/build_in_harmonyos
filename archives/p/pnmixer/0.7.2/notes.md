# pnmixer 0.7.2 适配笔记

## 编译环境

- 构建系统: cmake（上游 `CMakeLists.txt` + 各子目录 CMakeLists）
- 适配机: B 机（`nproc --all=20`，本 shell 亲和 8），HarmonyOS PC / aarch64
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，由 conan profile 的
  `tools.build:compiler_executables` 提供）
- CMake: 4.1.2 ｜ Conan: 2.29.1（OHOS 适配版）｜ profile: `ci/conan/profiles/ohos-aarch64`
- CONAN_HOME: 纯 ASCII 路径（`~/tmp/ch/home-zhuli7-pnmixer`）——含中文的路径会在
  设备侧 toybox sed 上挂掉 `config.status`（同族坑，A/B 已定证；本包为 CMake，
  但一律沿用 ASCII home 以消除变量）
- 编译日期: 2026-10-18
- 构建槽: `build-slot.sh --mem 1500 --jobs 4`（`-c tools.build:jobs=$BUILD_SLOT_JOBS`）

## 编译步骤

```bash
# 0) 环境
export TMPDIR="$HOME/tmp"
export PATH="$HOME/usr/local/bin:$HOME/.local/bin:$PATH"
export SSL_CERT_FILE="$HOME/usr/local/ssl/cert.pem"
export CONAN_HOME="$HOME/tmp/ch/home-zhuli7-pnmixer"   # 纯 ASCII

# 1) worktree（B 机建）
git fetch upstream main && git worktree add -b feat/pnmixer-0.7.2 \
    ~/qzy/主理-7-pnmixer-0.7.2 upstream/main

# 2) W0 依赖逐个核验（6/6 REMOTE_OK）
for p in alsa-lib/1.2.16.1 glib/2.88.3.1 gtk/3.24.43 libnotify/0.8.3.1 \
         libx11/1.8.13.1 gdk-pixbuf/2.44.6.1.1.1; do
  conan download "$p" -r=ohpcd --only-recipe
done

# 3) 源码与骨架
python3 scripts/ohc-run.py init-build pnmixer 0.7.2 --url=<codeload 直链> --auto
python3 scripts/ohc-run.py recipe-search pnmixer     # 无相似配方 → 手写配方
python3 scripts/ohc-run.py conan-init pnmixer 0.7.2  # 模板只出 autotools，需改写为 CMake

# 4) 图解析（不必真构建即可核二进制可达性）
conan graph info archives/p/pnmixer/0.7.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -r=ohpcd --format=json

# 5) 验证（配方生成后不再跑 build）
python3 scripts/ohc-run.py conan-verify pnmixer 0.7.2     # G0-G4 PASS
python3 scripts/ohc-run.py finish pnmixer 0.7.2 published
```

**最终构建命令（配方实际下发给 CMake 的）**

```
cmake -G Ninja <src> -DCMAKE_INSTALL_PREFIX=<package_folder> -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DWITH_GTK3=ON -DWITH_LIBNOTIFY=OFF -DENABLE_NLS=OFF
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed` | 上游写 `cmake_minimum_required(VERSION 3.0)`，平台 CMake 4.1.2 移除 <3.5 兼容 | 配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，**必须走 `CMakeToolchain.cache_variables`**（写成普通 `variables` 只进 toolchain 文件，不参与策略检查） |
| 2 | `ERROR: Version conflict: Conflict between gdk-pixbuf/2.44.6 and gdk-pixbuf/2.44.6.1 ... originates from libnotify/0.8.3.1` | libnotify 钉 gdk-pixbuf/2.44.6，gtk/3.24.43 钉 2.44.6.1 | 先试保版 override；最终因 libnotify 另有不可解冲突而整体不声明 libnotify（见 #4） |
| 3 | `ERROR: Version conflict: Conflict between expat/2.8.2 and expat/2.8.2.1 ... originates from dbus/1.14.10` | libnotify→dbus/1.14.10 钉 expat/2.8.2，fontconfig/2.18.1.1 钉 2.8.2.1 | 同上，随 libnotify 一并消失 |
| 4 | `ERROR: Version conflict: between glib/2.88.0.1 and glib/2.84.0.1`（libnotify/0.8.3.1 `force=True`） | 全部已发布 gtk3 钉 glib/2.84.0.1；覆盖任一侧都会改 package_id ⇒ 触发 meson 源码重建 | 1) 先改用 `libnotify/0.8.3`（同 glib/2.84 生态；已合入 `lomiri-polkit-agent/0.3.3` 同款处置）→ 图可解；2) 但见 #5，最终仍置 `WITH_LIBNOTIFY=OFF` |
| 5 | `libnotify/0.8.3.1: Error in build() method, line 145  meson.configure()  ConanException: Error 127 while executing`；上一行 `/bin/sh: meson: inaccessible or not found` | libnotify 配方的 `build()` 直接调裸 meson，且未声明 `tool_requires("meson")`；本机与 conan 缓存都没有 meson（`conan cache path meson/1.11.0` → `Recipe not found`） | 避免任何触发源码重建的图（改用 0.8.3 后已无重建） |
| 6 | `Error loading shared library libnotify.so.4: (needed by .../bin/pnmixer)` + `notify_init: symbol not found` | 制品仓 `libnotify/0.8.3` 的 `lib/libnotify.so.4.0.0` **带 `.codesign` 段但签名不被 OHOS 加载器接受** | 见下方「运行期限制」实测；处置 = `WITH_LIBNOTIFY=OFF`（上游支持的选项），交付一个真能启动的二进制 |
| 7 | `src/hotkeys.c:23:10: fatal error: 'gdk/gdkx.h' file not found` | OHOS 的 gtk3 只编 broadway 后端（`x11_backend=false`），`include/gtk-3.0` 下无 `gdk/gdkx.h`，libgdk-3 也无 `gdk_x11_*` 符号 | 源码补丁 0002–0006：`__has_include(<gdk/gdkx.h>)` 编译期探测 + `HAVE_GDK_X11` 守卫；无 X11 时热键子系统降级为 no-op（并在启用热键时打一条 WARN） |
| 8 | `ld.lld: error: undefined symbol: exp10`（referenced by alsa.c） | `exp10()` 是 GNU 扩展：OHOS sysroot 的 `<math.h>` 不声明它、共享 libm 不导出（`llvm-nm` 实测动态符号 0；只有静态 `libc.a` 有） | 源码补丁 0001：`#define exp10(x) pow(10.0,(x))`（数学等价、必然可用；无代码取 `exp10` 地址，宏替换安全） |
| 9 | `find_package(Gettext)` FATAL_ERROR / `xgettext not found`（若 `ENABLE_NLS=ON`） | 上游在 NLS 打开时硬要求 `xgettext`；干净 CI worker 不保证有 gettext 工具链 | `ENABLE_NLS=OFF`（仓内 212 份配方同款）；顺带避开 `support-intl.h` 的 `<libintl.h>`（OHOS 空壳，E660） |
| 10 | `ERROR: Failed checking for binary 'check/0.15.2:...' in remote 'ohpcd': remote not available` + `SSLError(SSLEOFError(8, ...))` | 外部 registry 抖动（基建） | 同刻 `curl` ping 回 200、`conan download check/0.15.2 --only-recipe` rc=0 ⇒ 受控重试 1 次即过，**未改配方** |

## 源码修改（补丁 6 个，全部 `patch_type: portability`，无平台宏）

补丁由 `refresh-patch --auto` 生成（`a/`/`b/` 前缀 ⇒ `conandata.yml` 每条 `strip: 1`；
本机实测 `patch -p0 --dry-run` 全 FAIL / `-p1` 全 OK）。**未使用 `__OHOS__` 平台宏**。

| 补丁 | 文件 | 改动 | 原因 |
|---|---|---|---|
| 0001 | `src/alsa.c` | +10/-0 | `exp10()` GNU 扩展在本平台不可用 → `pow(10.0,x)` |
| 0002 | `src/hotkey.c` | +40/-3 | Xlib/XKBlib 抓键代码用 `HAVE_GDK_X11` 守卫，缺失时 no-op |
| 0003 | `src/hotkey.h` | +16/-1 | 编译期探测 `<gdk/gdkx.h>`（`__has_include`），缺失时退回 `<gdk/gdk.h>` |
| 0004 | `src/hotkeys.c` | +23/-3 | 无 X11 后端时编译掉 root-window key filter；启用热键时改为一条明确的 WARN，不再逐键假报抓取失败 |
| 0005 | `src/ui-popup-window.c` | +2/-1 | 删掉未使用的 `<gdk/gdkx.h>` include（该文件无任何 `gdk_x11_*` 调用） |
| 0006 | `src/ui-prefs-dialog.c` | +2/-1 | 同上 |

上游**没有**任何测试文件被修改或删除（上游本来就没有自动化测试）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| gtk | 3.24.43 | `gtk+-3.0`，传递提供 glib 2.84.0.1 / gdk-pixbuf 2.44.6.1 / pango / cairo / atk / libepoxy |
| alsa-lib | 1.2.16.1 | `alsa`，`src/alsa.c` 直接调 ALSA mixer API |
| libx11 | 1.8.13.1 | `x11`，`src/hotkey.c` 用 `XKBlib` |
| libnotify | **未声明** | `WITH_LIBNOTIFY=OFF`（制品侧签名缺陷 + 依赖冲突，见上表 #4/#6） |

`conan graph info` 终态读数：`{Cache: 25, Skip: 9}`，**零缺失、零源码重建**
（即 gtk 闭包全部用制品仓已发布二进制）。

## 验证结果

```bash
$ conan graph info archives/p/pnmixer/0.7.2 -pr:h=...ohos-aarch64 -pr:b=...ohos-aarch64 -r=ohpcd
rc=0   binary summary: {Cache: 25, Skip: 9}   NOT-AVAILABLE: 仅 pnmixer/0.7.2 自身

$ python3 scripts/ohc-run.py conan-verify pnmixer 0.7.2
G1: PASS   G0: PASS   G2: PASS   G3: PASS   G4: PASS
✅ 配方验证通过: pnmixer 0.7.2        （VERIFY_RC=0）
```

**消费者测试（test_package）真实执行读数**（原文照抄，取自
`reports/conan-create.log`）：

```
HMBS_TEST_PACKAGE_STRUCTURAL={"total":15,"passed":15,"failed":0,"skipped":0}
pnmixer/0.7.2@ohpcd/stable (test package): OK: pnmixer --help -> 'Usage:'
pnmixer/0.7.2@ohpcd/stable (test package): OK: unknown option falls through to normal startup (rc=1): '(pnmixer:61378): Gtk-WARNING **: 05:22:42.771: cannot open display:'
pnmixer/0.7.2@ohpcd/stable (test package): OK: pnmixer without a display failed fast (rc=1): '(pnmixer:61390): Gtk-WARNING **: 05:22:43.260: cannot open display:'
pnmixer/0.7.2@ohpcd/stable (test package): starting broadwayd: <gtk pkg>/bin/broadwayd :77
pnmixer/0.7.2@ohpcd/stable (test package): broadwayd is listening
pnmixer/0.7.2@ohpcd/stable (test package): OK: --version with a live display -> 'pnmixer version: 0.7.2'
pnmixer/0.7.2@ohpcd/stable (test package): OK: -v with a live display -> 'pnmixer version: 0.7.2'
pnmixer/0.7.2@ohpcd/stable (test package): OK: pnmixer started, built its UI from the installed data files, hooked audio and reached the main loop (6 markers)
```

`-d` 真启动日志中的关键标记（6/6 命中，逐字取自运行输出）：

```
debug: .../src/ui-popup-menu.c: Building from ui file '<pkg>/share/pnmixer/ui/popup-menu-gtk3.glade'
debug: .../src/ui-tray-icon.c: Creating tray icon
debug: .../src/ui-tray-icon.c: Loading PNMixer icon 'pnmixer-high.png' from '<pkg>/share/pnmixer/pixmaps/pnmixer-high.png'
debug: .../src/hotkeys.c: Creating hotkeys control
debug: .../src/audio.c: Hooking soundcard '(default) ((null))' to the audio system
error: .../src/alsa.c: 'default': Can't attach card to mixer: No such file or directory
debug: .../src/audio.c: No soundcard could be hooked !
debug: .../src/main.c: ---- Running main loop ----
```

> 进程随后由测试自身终止（`subprocess.wait(timeout=20)` 超时即「仍在跑」），
> 说明确实停在主循环里，由此把「交付物能起」从声明变成断言。

## 交付物

| 文件 | 说明 |
|---|---|
| `<package>/bin/pnmixer` | 单可执行文件，ELF64 aarch64，带 `.codesign` 段（配方内 `binary-sign-tool` 自签名并回读段计数=1） |
| `<package>/share/applications/pnmixer.desktop` | 桌面入口 |
| `<package>/share/icons/hicolor/128x128/apps/pnmixer.png` | 应用图标 |
| `<package>/share/man/man1/pnmixer.1` | man 页 |
| `<package>/share/pnmixer/pixmaps/*.png` | 5 张托盘图标（muted/off/low/medium/high） |
| `<package>/share/pnmixer/ui/*-gtk3.glade` | 5 个 GTK3 界面描述文件 |

## 运行期限制（本平台实测，逐条留证）

1. **没有 X11/Wayland 显示服务**：OHOS 的 gtk3 只编 broadway 后端（E527），
   `GtkStatusIcon` 依赖 X11 系统托盘协议 ⇒ **托盘 GUI 本体在无显示服务时不可用**。
   但 `--help`（GOptionContext 在 GTK 后置钩子之前处理）不需要显示；
   `--version`/`-v` 需要显示（`main()` 把 `gtk_get_option_group(TRUE)` 加进了
   option context，后置钩子先 `gtk_init()`），因此测试用 gtk 包自带的
   `bin/broadwayd` 起一个私有 display 后真实执行。
2. **没有音频设备**：容器内 `/dev/snd` 不可访问，ALSA 报
   `cannot find card '0'` / `Can't attach card to mixer: No such file or directory`，
   程序按设计继续运行（`No soundcard could be hooked !`）⇒ mixer 的读写行为不可验证，
   可验证面是「确实链接 libasound」+「音频子系统能走到该错误路径而不崩」。
3. **桌面通知不可用**：见「依赖版本」表；根因是**制品侧**签名缺陷，非本包配方问题。
   实测对照：`ctypes.CDLL(<libnotify pkg>/lib/libnotify.so.4)` →
   `Error loading shared library ...: Permission denied`；把同一份字节用
   `binary-sign-tool sign -selfSign 1` 重新签名后，错误变为
   `Error loading shared library libgdk_pixbuf-2.0.so.0`（即签名有效后已能进入依赖解析）
   ⇒ `.codesign` 段在但签名不通。
   另注：即使能加载，freedesktop 通知还需要 D-Bus 上的通知守护进程，OHOS PC 不提供。
4. **界面文案为英文**：`ENABLE_NLS=OFF` ⇒ 不安装 `.mo` 翻译（见 #9）。
5. **上游行为观察（非本包缺陷，未修改）**：`main()` 忽略
   `g_option_context_parse()` 的返回值，因此未知选项**不会被拒绝**，而是与裸调用
   等价（落到 `gtk_init()` 后按无显示失败）。测试按这个真实契约断言，不写假期望。

## 注意事项

- `conandata.yml` 的 URL 是官方 `codeload.github.com` 标量，末段无扩展名 ⇒ 必须显式
  `filename: pnmixer-0.7.2.tar.gz`（E276/E483）。**提交前回读**：
  `git show HEAD:archives/p/pnmixer/0.7.2/conandata.yml | grep -Ec 'ghfast|gh-proxy|file://'` = 0。
  `conan-verify` 运行期会临时注入 `ghfast.top` 并「恢复」，本次已核对恢复成功，
  且清理了遗留的 `conandata.yml.ghfast-bak`。
- 本包为 `package_type = "application"`：产物只有 `bin/pnmixer` + `share/` 数据，
  不装任何库，因此 R26（系统同名库静态化）不适用；软件级 `commands.json` 已按 R38 提供。
- 手工改动只落在 `~/tmp/builds/pnmixer-0.7.2.work`，由 `refresh-patch --auto` 固化成
  6 个补丁；补丁文件本身**不进**源码树以外的任何地方。
- 设备侧 `/tmp` 只读（E002），配方内 `TMPDIR/TMP/TEMP` 指向
  `<build_folder>/hmbs-tmp`，避免 cmake/clang 临时文件失败。

**编译结束**：2026-10-18 05:23 CST
**最终状态**：conan-verify PASS（G0–G4），消费者测试 24 项断言 0 失败；待提交 PR
---

**编译结束**: 2026-10-18 05:45
**最终状态**: published
