# DRAFT-14823: 桌面会话态后端依赖的 meson feature 选项化裁剪（fuse3/libpipewire/gstreamer-pbutils 硬依赖三连无在档制品）

> Contributor: j669539 | Status: Draft | Updated: 2026-10-06
> Source: xdg-desktop-portal 1.22.1 HarmonyOS PC 适配（任务卡 #14890）
> Evidence: PR !14823（本地 conan create 8 轮全绿 + W3 本地 CI 门禁 100% pass）

## 现象：三个"不可能完成"的硬依赖

xdg-desktop-portal 1.22.1 上游 meson.build 将以下三者声明为**无条件硬依赖**
（`dependency()` 不带 `required:` 参数，configure 阶段缺一即死）：

| 依赖 | 上游版本要求 | 实测在档状态 |
|---|---|---|
| fuse3 | >= 3.10.0 | ohpcd 制品仓 0 命中 + 主仓 archives 无 |
| libpipewire-0.3 | >= 0.2.90 | ohpcd 制品仓 0 命中 + 主仓 archives 无 |
| gstreamer-pbutils-1.0 | （无版本约束） | **特殊**：主仓有 gstreamer 1.28.3 全家桶，但 gst-plugins-base 配方只包装 gstreamer core 的 5 个 pc（gstreamer/base/controller/net/check），**不生成 gstreamer-pbutils-1.0.pc**——即使装齐 gstreamer 系也链接不到 pbutils |

直接 `conan create` 会在 meson configure 阶段报：

```
ERROR: Dependency "fuse3" is required but not found
```

（fuse3 位于根 meson.build 第 190 行、libpipewire 第 198 行、
gstreamer-pbutils 第 192 行，均为裸 `dependency()` 调用。）

## 根因：桌面会话态后端 vs 核心交付的依赖分层

这三个依赖有一个共同特征——**只服务桌面会话态后端功能**，与软件的核心交付
零耦合：

- **fuse3** → 仅 document-portal 的 FUSE 挂载后端（文档沙箱文件系统）。
  注意子目录内 xdg-permission-store 守护进程在 meson.build **前部**且只依赖
  gvdb+glib，与 fuse3 无关——这是"子目录分段跳过"的关键洞察。
- **libpipewire** → 仅 camera/screen-cast/remote-desktop/clipboard 四个
  portal 的视频源。C 侧符号耦合：clipboard.c 调 remote-desktop 会话函数，
  必须与 remote-desktop 归入同一守卫组。
- **gstreamer-pbutils** → 仅 validate-sound 声音校验助手。

在无桌面会话的 OHOS PC 环境中三者本就无运行时（无 FUSE 内核态、无 PipeWire
守护进程、无 pbutils 制品），属于"上游为桌面 Linux 设计的可选功能面被硬编码
为必选"的平台差异。

## 解决：完全复制上游既有的 geoclue/gudev 可选模式

上游对 geoclue/gudev/systemd 已有成熟的可选依赖模式，本改造不做任何发明，
逐字对齐该模式：

```meson
# 1. meson_options.txt：新增三个 feature 选项
option('fuse3', type: 'feature', value: 'auto',
       description: 'Enable FUSE support. ...')
option('pipewire', type: 'feature', value: 'auto', ...)
option('sound-validation', type: 'feature', value: 'auto', ...)

# 2. 根 meson.build：硬依赖 → required: get_option(...)
fuse3_dep = dependency('fuse3', version: '>= 3.10.0',
                       required: get_option('fuse3'))
...
have_fuse3 = fuse3_dep.found()
config_h.set10('HAVE_FUSE3', have_fuse3)
have_pipewire = pipewire_dep.found()
config_h.set10('HAVE_PIPEWIRE', have_pipewire)
# summary 段补三行状态输出

# 3. src/xdp-context.c：#if HAVE_PIPEWIRE 守卫 include 与 init_*() 调用
#if HAVE_PIPEWIRE
#include "camera.h"
#include "clipboard.h"
#endif
...
#if HAVE_PIPEWIRE
  init_camera (context);
  init_screen_cast (context);
  init_remote_desktop (context);
  init_clipboard (context);
#endif

# 4. src/meson.build：源文件移入条件块
if have_pipewire
  xdg_desktop_portal_sources += files('camera.c', 'clipboard.c',
      'pipewire.c', 'remote-desktop.c', 'screen-cast.c')
endif
if gst_pbutils_dep.found()
  xdp_validate_sound = executable(...)   # 声音校验助手整体条件化
endif

# 5. document-portal/meson.build：子目录分段跳过
if not have_fuse3
  subdir_done()   # 跳过 FUSE 挂载后端；前面的 permission-store 保留
endif
```

## 裁剪前的必备功课：符号交叉引用矩阵

裁剪前必须 grep 全量确认被裁文件对外无符号泄漏（否则链接失败才发现漏守卫）：

```
grep -rln "screen_cast_\|remote_desktop_\|camera_\|pipewire_remote" src/*.c \
  | grep -vE "screen-cast.c|remote-desktop.c|camera.c|pipewire.c|clipboard.c"
# 期望输出为空
```

本例实测：六文件（screen-cast/remote-desktop/camera/pipewire/clipboard +
pipewire.h）之外零符号引用；input-capture.c 虽含 clipboard_enabled 字段
处理但无对被裁符号的外部依赖，**保留编译**（不扩大裁剪面）。

## 交付验证（fallback 后的核心完整性）

禁用三后端后，核心交付完整保留并全部实测通过：

- `bin/xdg-desktop-portal`（portal 守护进程，`--version` 输出
  `xdg-desktop-portal 1.22.1`，OHOS 已签名可 exec）
- `bin/xdg-permission-store`（fuse3 无关交付物，保留）
- `bin/xdg-desktop-portal-validate-icon`（gdk-pixbuf 在档故保留）
- `share/dbus-1/interfaces/*.xml`（57 个 portal 接口 XML）
- `share/dbus-1/services/*.service` + dataonly pc（interfaces_dir 可重定位）

## verify_builds

- xdg-desktop-portal/1.22.1（archives/x/xdg-desktop-portal/1.22.1，PR !14823）
- 本地 conan create 8 轮迭代全绿（CONAN_RC=0）+ W3 本地 CI 门禁 100% pass
  （L0/L1/L4/L5 全过 + L1e 负向破坏测试确认 test 真实依赖交付物）
- 可复用面：任何依赖 fuse3/pipewire/gstreamer-pbutils 的桌面生态件
  （xdg 组件、屏幕共享工具、音频校验组件、GNOME 系桌面服务）

## 关联

- 配套 .kv：`knowledge/drafts/DRAFT-14823-xdg-desktop-portal-desktop-session-backend-feature-optional.kv`
- 同族既有条目：DRAFT-8959-raqm（meson ninja LD_LIBRARY_PATH 污染——本 PR
  同场踩到，已按该条处置，不重复立条）；E527（GTK broadway 后端——同为
  "上游可选面"主题但方向为后端替代而非依赖裁剪）；DRAFT-vips-8.18.4.1
  （meson feature+pkgconfig——方向为"补回"编解码器，与本文"裁剪"互补）
