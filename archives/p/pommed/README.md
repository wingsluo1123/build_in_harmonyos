# pommed

Apple 笔记本热键处理守护进程（Apple laptops hotkeys handler）。

pommed 监听 evdev 输入事件，并通过 sysfs / ACPI / D-Bus 驱动笔记本的
LCD 背光、键盘背光、环境光传感器、CD/DVD 弹出、蜂鸣器与视频输出。
它把热键事件通过 D-Bus 广播出去，同 tarball 内的 `gpomme`（GTK+ 2）
与 `wmpomme`（X11/WindowMaker）客户端负责显示 OSD。

- 上游版本：1.39（Debian 源码包 `1.39~dfsg`）
- 许可证：GPL-2.0-or-later
- 源码：<https://deb.debian.org/debian/pool/main/p/pommed/>
- 参考页面：<https://sources.debian.org/src/pommed/>

## OHOS 适配要点

| 项 | 说明 |
|----|------|
| 构建系统 | 递归 Makefile（无 configure / 无 `make check` / 无 install 目标） |
| 构建对象 | 仅 `pommed` 守护进程本体；`gpomme` / `wmpomme` GUI 客户端不在范围内 |
| 依赖 | dbus、alsa-lib、audiofile、libconfuse、pciutils（均取自 OHOS 制品仓） |
| 补丁 | 3 个可移植性补丁：`<pthread.h>`、`<limits.h>`、x86 I/O 端口驱动架构守卫 |

## 使用

```bash
conan install --requires=pommed/1.39-dfsg -r=ohpcd
```

守护进程需要 root 权限运行，配置文件为 `/etc/pommed.conf`（示例见
`share/pommed/pommed.conf.mactel`、`pommed.conf.pmac`）。

```
pommed      -- 以守护进程方式启动
pommed -v   -- 打印版本并退出
pommed -f   -- 前台运行并输出日志
pommed -d   -- 前台运行并输出调试日志
```

> 注意：pommed 的硬件后端（背光 / 环境光 / CD 弹出 / 蜂鸣）针对 Apple
> MacBook 硬件；在非 Apple 机器上 `check_machine()` 会以
> `Unknown non-Apple machine` 正常退出。本次适配的目标是让该守护进程在
> HarmonyOS PC（aarch64）上正确构建、加载并运行，而不是驱动 Mac 专用硬件。
