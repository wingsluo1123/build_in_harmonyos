# pasystray

pasystray 是 PulseAudio 的**系统托盘控制器**：在系统托盘里放一个图标，用它控制
PulseAudio 服务的音量、默认设备与各条音频流（GTK+3 前端，C/autotools）。

## 功能概述

- 系统托盘图标：显示/切换 PulseAudio 状态，滚轮直接调音量
- 菜单：切换默认 sink/source、静音、按 sink/source/stream 调整音量
- 可选 X11 音量键抓取（`--key-grabbing`）、可选桌面通知（libnotify）
- 可选 Avahi/zeroconf 网络音频设备发现、可选 libappindicator 托盘后端

## OHOS 适配要点

- **上游硬依赖 `libpulse-mainloop-glib`**（`configure.ac:51`；`src/pulseaudio.c`
  调用 `pa_glib_mainloop_new` / `pa_glib_mainloop_get_api`），用于把 PulseAudio
  的 mainloop 接到 GLib `GMainContext` 上。制品仓中只有 `pulseaudio/17.0.1`
  提供该库（`pulseaudio/17.0` 以 `glib=disabled` 构建，不含此库）。
- **已知依赖冲突（平台任务 9324）**：`pulseaudio/17.0.1` 钉 `glib/2.88.0`，
  而制品仓**全部** gtk3（3.24.38 / 3.24.38.1 / 3.24.43）钉 `glib/2.84.0.1`；
  朴素配方不可解。按**用户明确选择的选项 (2)**，照已合入的 `pavucontrol-qt/2.4.0`
  先例交付：本配方用 **recipe 级 override**（`self.requires("glib/2.84.0.1",
  override=True)`）让 gtk3 的 glib 全局生效，并让 pulseaudio 的 package_id 变化后
  从源码重建。**序列化注意**：这条 override 随配方进入 CI，而 profile 级
  `[replace_requires]` 不会。**越界事实**：它改变了已发布依赖 `pulseaudio/17.0.1`
  的构建语义（glib 2.88 → 2.84），未覆盖远端既有制品；详见 `0.8.2/notes.md`。
- **运行期限制（本机实测，按先例如实声明并容忍）**：
  1. OHOS 加载器拒绝加载**未签名**（无 `.codesign`）的共享库（实测 `dlopen`
     返回 `Permission denied`；签名后同一文件加载成功）。制品仓里 gtk/glib 的共享库
     是签过名的，**pulseaudio/17.0.1 的 `libpulse.so.0` / `libpulse-mainloop-glib.so.0`
     没有签名**，因此链接 pulseaudio 的交付物在本机无法启动（rc=127）。该缺陷属于
     pulseaudio 制品侧。
  2. 无显示后端时，上游 `main()` 先调 `gtk_init_with_args()`，失败后 `parse_options()`
     不执行，故 `--version` / `--notify=help` 也无法在无显示环境完成。
  因此消费者测试照 `pavucontrol-qt/2.4.0` 先例：结构性/链接性断言（ELF、DT_NEEDED
  含 `libpulse.so.0` 与 `libpulse-mainloop-glib.so.0`）保持**硬断言**；CLI 契约
  **真实执行**，命中已声明的 OHOS 限制特征时打印
  `Execution skipped due to OHOS platform limitation: ...` 并容忍。
- **无原生显示后端**：OHOS PC 没有 X11/Wayland，gtk/3.24.43 为 broadway 后端
  （E527）。pasystray 的托盘图标依赖 `GtkStatusIcon`（X11 系统托盘协议），
  因此**完整 GUI 功能当前不可用**；可离线验证的是库链接与 CLI 契约。
- **autotools 引导**：上游 tag archive 不含 `configure`/`Makefile.in`，
  `build()` 用 `autoreconf -fi` 重建（本机缺 aclocal/automake，
  由 `tool_requires("automake/1.18")` 提供）。
- E007：automake 自带 `config.guess` 不认识 HarmonyOS，配方内**内联**补丁加入
  `__OHOS__` LIBC 探测与 `*:HarmonyOS:*:*` 分支（三元组
  `aarch64-unknown-linux-ohos`）；`config.sub` 补 `ohos-linux` 三元组。
  内联实现（不依赖 `OHC_SKILL_ROOT`）以保证 CI 与本地结果一致。
- E011/E114：HMDFS 上 0700 的 `config.status` 临时目录不可写，
  `configure` 的 `umask 077` 降为 `umask 022`。

## 依赖关系

编译依赖（recipe 声明）：

| 依赖 | 版本 | 说明 |
|---|---|---|
| gtk | 3.24.43 | GTK+3（broadway 后端），传递提供 glib/gdk-pixbuf/pango/cairo/atk |
| glib | 2.84.0.1 | **override 强制**：压制 pulseaudio 的 glib/2.88.0 |
| pulseaudio | 17.0.1 | 提供 `libpulse` + `libpulse-mainloop-glib`；package_id 变化需源码重建 |
| automake | 1.18 | tool_require，autoreconf 引导 |

运行期依赖：pulseaudio 共享库（`libpulse.so.0`、`libpulse-mainloop-glib.so.0`、
`libpulsecommon-17.0.so`）与 GTK3/GLib 共享库；需要一个 PulseAudio 服务与一个
系统托盘宿主。

## 参考资料

- 上游源码：<https://github.com/christophgysin/pasystray>
- 上游 README：<https://github.com/christophgysin/pasystray/blob/master/README.md>
- PulseAudio 客户端库：<https://www.freedesktop.org/wiki/Software/PulseAudio/>
