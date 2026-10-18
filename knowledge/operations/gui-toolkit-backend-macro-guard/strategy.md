# 处理策略：GUI 工具库后端专属 API 的源码守卫

> 适用检测器：`detect-gui-toolkit-backend-macro-guard.sh`（命中 HARD 即按本策略处置）
> 同族知识：`knowledge/drafts/DRAFT-gui-toolkit-backend-macro-guard.md`

## 一句话策略

**用工具包自己发布的后端宏（GTK/GDK 系为 `GDK_WINDOWING_*`）把后端专属头与符号
守卫起来，后端缺失时走向上游已有的「无该后端」桩分支；禁止无条件 `-D` 强开宏，
禁止按平台名（`__OHOS__`）硬编码分支。**

## 判定链（先判类型，再选修法）

| 步骤 | 判据 | 结论 |
|---|---|---|
| 1 | 该后端能力是否是**功能必需**（X 客户端、抓屏、全局热键）而非「锦上添花」 | 必需 → 属运行级不可用，按 E463/E471 分类，**不要**用宏守卫掩盖；可选项 → 走步骤 2 |
| 2 | 目标平台的工具库是否真的没编译该后端 | `grep GDK_WINDOWING_* <gtk-prefix>/include/gtk-3.0/gdk/gdkconfig.h`，`#undef` 即未启用 |
| 3 | 后端专用头是否随包安装 | `ls <gtk-prefix>/include/gtk-3.0/gdk/gdkx.h` —— broadway-only 包无此头 |
| 4 | 上游自身怎么表达「无该后端」 | 读工具库/消费者自身的同类写法：`gtk/gtkplug.h:34` 就是 `#ifdef GDK_WINDOWING_X11`；消费者若有既有桩分支，**复用**它 |

## 两种修法（按缺口位置二选一）

### A. 源码守卫法（首选；缺口在消费者源码）

适用：消费者（应用 / 语言绑定 / 插件）无条件 include 后端头或调用后端符号。

1. **头文件**：把 `#include <gdk/gdkx.h>`、`<X11/Xlib.h>` 等包进
   `#if defined(GDK_WINDOWING_X11) … #endif`。放在 `#include <gtk/gtk.h>` 之后——
   宏来自 `gtk/gtk.h` 引入的 `gdkconfig.h`，早了会拿到「未定义」。
2. **函数体**：整块 `#if defined(GDK_WINDOWING_X11) … #else … #endif`，
   `#else` 分支保留**公开 API 的桩实现**（打印诊断、返回可用句柄、保持幂等 free），
   **不要**把函数删掉——删函数等于改公开 ABI，调用方/插件仍会链接。
3. **注册点也要守卫**：`*_get_type()` 注册、静态函数指针表等属于「守卫只盖一半」的
   隐藏爆炸点，漏了会在链接期报 `undefined reference`（检测器给 WARN
   `log-link-backend-symbol` 就是这个形态）。
4. 守卫谓词只能是工具包发布的宏；`#ifndef __OHOS__` 之类平台名分支会让同一份源码
   在其他 broadway/Wayland-only 平台继续坏，检测器记为 WARN `platform-macro-guard`。

### B. 构建期 flag / 配置开关（次选；缺口在构建系统，或消费者已有开关）

适用：消费者本就有 `--disable-key-grabbing` 一类开关，或后端头只在某个可选模块里用。

- 用**消费者自己的开关**把该模块编掉（例：`pa-applet --disable-key-grabbing` 是运行期
  开关，编译期仍需 A 法；而 `-DWITH_X11=OFF` 这类 CMake 选项可直接编掉整个模块）。
- 反向禁止：`CPPFLAGS=-DGDK_WINDOWING_X11` 之类的**无条件强开宏**——头不存在，
  换了种死法（`fatal error: 'gdk/gdkx.h' file not found`），且会在有该头的平台上
  编出与实际后端不符的代码。

## 必须同时做的事

1. **检测器双向验证**：关掉补丁 → `detect…` 命中 HARD 且构建失败；打上补丁 →
   HARD=0、构建通过（`reproduce.sh` 已把这条闭环自动化）。
2. **DT_NEEDED / 符号断言**：守卫后产物仍应链接 gtk/libpulse/libnotify 等真实依赖，
   证明补丁没有把功能面整体悄悄砍掉（见 `sample/pa-applet/README.md`）。
3. **运行期限制写清**：后端缺失意味着该功能在目标平台不可用（全局热键需要 X11 GDK
   后端）。这是**已知且可接受的降级**，必须在 `notes.md` 与 PR 正文写明，
   不能当作"已支持"。

## 常见误判

| 现象 | 不是本策略的问题 | 正确归类 |
|---|---|---|
| `'X11/Xlib.h' file not found`，但库自带 `X_DISPLAY_MISSING` 宏 | 缺口在**构建期宏未传给消费者** | 配方注入 `-DX_DISPLAY_MISSING`（宏注入法，见 imlib2 草稿） |
| 后端头存在、符号也在，但**运行期**连不上显示/服务 | 属运行环境缺失 | E463/E471 运行级分类 |
| 编译通过、链接报 `undefined reference to gtk_plug_get_type` | 守卫漏了注册点 | 回到 A.3 |
