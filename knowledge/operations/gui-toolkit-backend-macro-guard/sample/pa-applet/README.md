# 样例库：pa-applet g20181009

本目录演示本知识条目在**真实项目**上的落地结果。权威配方不在本目录，而是随适配
归档一起维护：

```text
archives/p/pa-applet/g20181009/{conanfile.py,CMakeLists.txt,conandata.yml,notes.md,manifest.yaml}
archives/p/pa-applet/g20181009/patches/0001-guard-x11-key-grabber.patch
archives/p/pa-applet/g20181009/test_package/{conanfile.py,test_pa_applet.sh,MANIFEST.yml}
```

本目录只保留**可直接套用到别的消费者**的补丁副本，避免配方双份漂移。

## 为什么它是本知识条目的典型样例

pa-applet 是 GTK3 + PulseAudio 的托盘小程序，`src/key_grabber.c` 用 X11 专属 API
（`XGrabKey` / `GDK_DISPLAY_XDISPLAY` / `GDK_WINDOW_XID` / `XStringToKeysym`）
实现全局媒体键抓取。制品仓 `gtk/3.24.43` 是 broadway-only 构建，因此：

```text
src/key_grabber.c:10:10: fatal error: 'gdk/gdkx.h' file not found
```

这不是 pa-applet 的专属问题，而是「多后端 GUI 工具库 × 源码级消费者」在无后端平台上的
通例，所以修法用**工具包自身后端宏**而不是平台宏。

## 源码侧改动（唯一补丁，+24/−1）

`patches/0001-guard-x11-key-grabber.patch`：

1. `<gdk/gdkx.h>` / `<X11/Xlib.h>` 包进 `#if defined(GDK_WINDOWING_X11)`，
   放在 `#include <gtk/gtk.h>` 之后（宏来自 `gtk/gtk.h` 引入的 `gdkconfig.h`）；
2. `key_grabber_grab_keys()` 等 X11-only 函数体整块守卫，
   `#else` 分支保留公开 API：一次性 `g_printerr` 诊断 + 幂等 free；
3. 关键：**函数没删**——`key_grabber.h` 的 ABI 与调用方（`main.c`）零改动。

## 双向验证

```sh
# ① 知识库级：关守卫 → 报错，开守卫 → 通过（不需要 conan）
knowledge/operations/gui-toolkit-backend-macro-guard/reproduce.sh

# ② 归档级：完整 conan create（8 个 .c + 链接 + test_package）
cd archives/p/pa-applet/g20181009
conan create . -pr=ohos-aarch64 --build=missing
```

实测结果：

| 阶段 | 结果 |
|---|---|
| 关侧检测器 | `hard=14 warn=0`，exit 1 |
| 关侧编译 | 非 0，`fatal error: 'gdk/gdkx.h' file not found` |
| 开侧检测器 | `hard=0 warn=14`（命中项变为 `backend-symbol-guarded`，可接受），exit 0 |
| 开侧编译 | exit 0，8 个 `.c` 全过 |
| `conan create` | `CONAN_RC=0`，test_package `PASS=7 FAIL=0 SKIP=7` |

## 依赖侧的连带问题（不是本知识条目主题，但适配时会撞上）

| 现象 | 处理 |
|---|---|
| `pulseaudio/17.0` 无 `pulse-mainloop-glib` 组件（`pa_glib_mainloop_new` 用它） | 依赖改 `pulseaudio/17.0.1` |
| `gtk/3.24.43` 钉 `glib/2.84.0.1`，而 `pulseaudio/17.0.1`/`libnotify/0.8.3.1` 要 `glib/2.88.0` | 用 `force=True` 守 gtk 线，只让这两个小包走源码重建（详见归档 notes.md） |
| pango 头 `#include <hb.h>` 但目标不传播 harfbuzz include | 配方显式 `self.requires("harfbuzz/<图中的版本>")` |
| 上游 autotools 但环境无 automake | 配方自带 `CMakeLists.txt`（仓库已有 40+ 先例） |

## 运行期限制

broadway-only 平台没有 X11 GDK 后端，全局媒体键抓取**不可用**（补丁后打印诊断）。
另有：无系统托盘宿主、无通知守护、无 PulseAudio 服务端直连时程序进入等待状态。
这些都在归档 `notes.md` 与 PR 正文中写明，属已知降级而非"已支持"。
