# lirc

LIRC（Linux Infrared Remote Control）是 Linux 红外遥控生态的参考实现：`lircd`
守护进程从红外接收设备（串口、USB HID、uinput、soundcard、i2c 等）读取原始
脉冲并解码为按键事件，通过 UNIX socket 分发给客户端；`liblirc_client` 提供
`lirc_init()`/`lirc_readconfig()`/`lirc_code2char()` 等消费端 API；随包发布的
还有约 30 个硬件驱动插件与 `irsend`/`irrecord`/`mode2`/`irw` 等命令行工具。

## 功能概述

- 守护进程：`lircd`（解码/分发）、`lircrcd`（客户端侧配置守护）、`lircmd`（鼠标模拟）
- 客户端库：`liblirc`、`liblirc_client`、`liblirc_driver`、`libirrecord`
- 硬件插件：`lib/lirc/plugins/*.so`（hiddev、i2cuser、dsp、file、udp、livedrive、irToy 等）
- 命令行工具：`irsend`、`irrecord`、`mode2`、`irw`、`ircat`、`irsimreceive`、`irsimsend`、
  `lirc-lsplugins`、`lirc-config-tool`、`irdb-get` 等

## OHOS 适配

- 依赖探测全部按真实能力进行：本机无 `/dev/input`、`/dev/uinput`、`/dev/lirc`，
  因此 `HAVE_DEVINPUT=no`、`ENABLE_UINPUT=no`，`lircd-uinput` 与 devinput 驱动不构建；
  libusb/libftdi/portaudio/ALSA/systemd/libudev 均未探测到，相关插件自动关闭（30/40）。
- 上游 release tarball 无 `test/` 目录，CppUnit 上游测试（35 条注册用例）由
  `upstream-tests/` 逐字随源码提供并在 `build()` 中真实执行，详见 `notes.md`。
- musl/OHOS 差异修补（`rindex`→`strrchr`、`pthread_cancel` 原型、`pthread_t` 哨兵值）、
  HMDFS 的 `umask 077` 临时目录问题、大小写不敏感文件系统下 `<version>` 被 `VERSION`
  抢占的问题，均见 `notes.md`「OHOS 适配要点」。

## 依赖关系

- 编译依赖：无硬依赖（`pkg-config`、`xsltproc` 由 HNP 工具链提供）
- 测试依赖：`cppunit/1.15.1`（`test_requires`，不进包）
- 构建工具：`automake/1.18`（仅取用其新版 `config.sub`/`config.guess`）

## 已知限制

- HMDFS 工作区内 `AF_UNIX` `bind()` 被拒（EPERM），需要 lircd UNIX socket 的
  9 条 `ClientTest` 用例在设备上失败；`/data/storage/el2/base` 下 bind 正常。
- `DrvAdminTest` 硬编码 `DRIVER_COUNT=51`/`PLUGIN_COUNT=40`（Linux 全功能构建），
  本平台实测 39/30。

## 参考资料

- 官网：https://www.lirc.org
- 源码仓库：https://git.code.sf.net/p/lirc/git
- 发布页：https://sourceforge.net/projects/lirc/files/LIRC/0.10.2/
