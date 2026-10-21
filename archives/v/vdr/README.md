# vdr

**Video Disk Recorder（数字视频录像机）** —— 面向 DVB-S/C/T 数字电视设备的录像、回放与电子节目单（EPG）主程序。

## 用法

```bash
vdr [options]
```

常用选项：

| 选项 | 说明 |
|------|------|
| `-c DIR, --config=DIR` | 配置目录（默认 `/var/lib/vdr`） |
| `-v DIR, --video=DIR` | 录像目录（默认 `/srv/vdr/video`） |
| `-d, --daemon` | 以守护进程方式运行 |
| `-l LEVEL, --log=LEVEL` | 日志级别 0–3 |
| `-u USER, --user=USER` | 以指定用户运行（仅 root 启动时有效） |
| `-V, --version` | 输出版本信息并退出 |
| `-h, --help` | 输出帮助并退出 |

## 构建

- 构建系统：手写 GNU make（`Makefile` + 可选 `Make.config`），无 configure / CMake / meson
- 版本：2.6.9
- 许可证：GPL-2.0-or-later
- 源码：<https://github.com/vdr-projects/vdr/archive/refs/tags/2.6.9.tar.gz>（上游 vdr-projects/vdr 仓库官方 tag 归档）
- 依赖：libjpeg-turbo、libcap、freetype、fontconfig（版本见表）

## OHOS 适配

- 新增 `patches/0001-vdr-2.6.9-ohos-libc-portability.patch`，覆盖：glibc 专属宏/类型兜底、libcap 头缺失、缺失的 `pthread_cancel`/`adjtime` 原型、`INADDR_ANY` 非字面量空指针常量、`<sys/unistd.h>`、`stdin/stdout/stderr` 为 `FILE *const`
- `gettext` 家族与 `adjtime`/`pthread_cancel` 由运行期 musl 加载器导出，以 `-L/lib -l:ld-musl-aarch64.so.1` 链接；并注入最小 `libintl.h`（SDK 自带的同名头是空桩）
- 本包只构建 `vdr` 目标，不构建上游的 i18n（需 xgettext/msgfmt）与 `PLUGINS/src` 演示插件（skincurses 需 ncurses）
- **运行期限制**：本设备 `/dev/dvb` 与 `/sys/class/dvb` 均不存在，`vdr` 启动后必然枚举到 0 个 DVB 适配器；`--version` / `--help` 及「录像目录不可访问」分支不受影响

## 已知限制

- 未安装上游的 `svdrpsend`（Perl 脚本，设备无 Perl 运行时）与示例配置文件
- 未安装插件开发头文件（`include/vdr`、`include/libsi`）
