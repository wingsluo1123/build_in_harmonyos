# GUI 工具库后端专属 API：按工具包后端宏源码守卫

**状态**：operations（已落地样例验证）
**同族条目**：`knowledge/drafts/DRAFT-gui-toolkit-backend-macro-guard.md`（机理与查重记录）
**样例库**：`pa-applet/g20181009`（GTK3 + PulseAudio 托盘小程序，2026-10 适配）

## 触发场景

目标平台（HarmonyOS PC / OHOS aarch64）上的 GTK3 制品是 **broadway-only** 构建：
`gdkconfig.h` 里 `#undef GDK_WINDOWING_X11` / `#define GDK_WINDOWING_BROADWAY`，
X11/Wayland/Win32/Quartz 的后端专用头（`gdk/gdkx.h` 等）**不随包安装**。
源码级消费者只要无条件 include 这些头、或调用后端专属符号，就会在编译期直接失败：

```text
src/key_grabber.c:10:10: fatal error: 'gdk/gdkx.h' file not found
```

```text
ml_gdk.c:435:32: error: use of undeclared identifier 'AnyPropertyType'
```

```text
ml_gtk.c:931:7: warning: call to undeclared function 'gtk_plug_new'; ISO C99 ...
ml_gtk.c:931:7: error: incompatible integer to pointer conversion passing 'int'
```

检测：

```sh
detect-gui-toolkit-backend-macro-guard.sh <源码目录>     # HARD 命中 → exit 1
detect-gui-toolkit-backend-macro-guard.sh --log build.log
```

HARD 形态两类：`backend-header-unguarded`（无条件 include 后端专用头）、
`backend-symbol-unguarded`（直接调用 `XGrabKey` / `GDK_DISPLAY_XDISPLAY` /
`gdk_x11_*` 等后端专属符号且文件无 `GDK_WINDOWING_X11` 守卫）。
另有 WARN 形态：`backend-symbol-guarded`（已守卫，可接受）、
`platform-macro-guard`（用平台名而非工具包后端宏，属反模式）。

### 守卫形态（检测器判定口径）

| 写法 | 判定 | 说明 |
|---|---|---|
| `#if defined(GDK_WINDOWING_X11)` / `#if defined GDK_WINDOWING_X11` | 算守卫（WARN） | 最常见写法 |
| `#ifdef GDK_WINDOWING_X11` | 算守卫（WARN） | GTK 自身写法（`gtk/gtkplug.h:34` 同款） |
| `#elif defined(...)` / `#elifdef ...` | 算守卫（WARN） | 多后端 `#if`/`#elif` 链 |
| `#ifndef GDK_WINDOWING_X11` | **不算**（HARD） | 语义相反：只在宏未定义时编译，broadway-only 平台必炸 |
| `#if !defined(GDK_WINDOWING_X11)` | **不算**（HARD） | 同上 |
| `#ifdef __OHOS__` 等平台名 | **不算**（HARD）+ WARN `platform-macro-guard` | 平台名不是工具包发布的后端宏 |

正反两侧都由 `sample/guard-forms/check.sh` 离线锁定（`./check.sh` 一命令 7 例全跑）。

## 适用库范围

**正向适用**——任何「多后端 GUI 工具库 × 源码级消费者」组合：

| 工具库 | 后端宏发布面 | 专属头 |
|---|---|---|
| GTK3/GDK3 | `gdkconfig.h` 的 `GDK_WINDOWING_{X11,WAYLAND,WIN32,QUARTZ,BROADWAY}` | `gdk/gdkx.h`、`gdk/gdkwayland.h`、`gdk/win32/gdkwin32.h`、`gdk/quartz/gdkquartz.h` |
| GTK4 | 同上（`GDK_WINDOWING_*`） | `gdk/x11/gdkx.h` 等（路径带后端子目录） |
| Qt5/Qt6 | `QT_CONFIG(xcb)` / 平台插件特性 | `QtX11Extras`、`xcb` 私有头 |

**不适用（须换策略）**：

- 该后端能力是**功能必需**（X 客户端工具、截屏、真·全局热键）→ 属运行级不可用，
  按 E463/E471 分类，不能用宏守卫"掩盖"。
- 缺口在**构建期宏未传播到消费者**（库自带 `X_DISPLAY_MISSING` 但没进 cpp_info）
  → 用配方向 `cpp_info.cflags` 注入宏（宏注入法，见 imlib2 草稿）。
- 只差构建开关：消费者已有 `-DWITH_X11=OFF` / `--disable-x11` → 直接用开关编掉模块。

## 处理要点（详见 `strategy.md`）

1. 守卫谓词取**工具包发布的后端宏**；`#include <gtk/gtk.h>` 之后再判（宏来自 `gdkconfig.h`）。
2. 头与**函数体**都要守卫；`#else` 分支保留公开 API 的桩实现（打印诊断、幂等），
   不要删函数、不要改 ABI。
3. 补上 `*_get_type()` 注册等隐藏爆炸点，否则链接期 `undefined reference`。
4. **禁止**无条件 `-DGDK_WINDOWING_X11`、**禁止** `#ifndef __OHOS__` 平台名分支。

## 限制

- 守卫后的功能是**降级**而非等价：全局媒体键抓取需要 X11 GDK 后端，broadway-only
  平台上不可用，桩实现只打印诊断。运行期限制必须写进适配 notes 与 PR 正文。
- 检测器是文本级启发式：跨函数/跨文件的宏传递（如守卫宏定义在公共头里、命中文件
  自身不含 `#if`）会漏报，需配合构建日志（`--log`）复核。
- 检测器不判断"该能力是否功能必需"，这一步必须人工过一遍（`strategy.md` 判定链步骤 1）。

## 复现（双向验证样例库）

```sh
# 默认在临时目录里跑完两向：关守卫 → 原报错，开守卫 → 编译通过
# （第一步先跑守卫形态矩阵，离线、不需要 GTK/conan/网络）
./reproduce.sh

# 只跑守卫形态矩阵（7 例：#ifdef / #if defined / #elif / #ifndef / !defined / 平台名 / 无守卫）
sample/guard-forms/check.sh

# 指定 pa-applet 源码包（离线环境用本地 tar 包，sha256 会校验）
./reproduce.sh --tarball /path/to/pa-applet-g20181009.tar.gz
```

`reproduce.sh` 的判据（不依赖 ABI 之外的假设）：

| 阶段 | 期望 |
|---|---|
| 守卫形态矩阵 | 7/7 符合预期（exit 0） |
| 检测器（原始源码） | `hard=15`（后端符号 14 + 后端头 include 1）、exit 1 |
| 编译（原始源码） | 非 0 退出，stderr 含 `'gdk/gdkx.h' file not found` |
| 检测器（打补丁） | `hard=0`、exit 0 |
| 编译（打补丁） | exit 0（8 个 .c 全部编过） |

完整端到端（`conan create` + test_package）见 `sample/pa-applet/README.md`。
