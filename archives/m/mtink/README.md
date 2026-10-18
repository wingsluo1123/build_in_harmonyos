# mtink

mtink 是 EPSON 喷墨打印机的状态监视器（2007 年最后一个上游发行版 1.0.16）：
通过并口（`/dev/lp*`、`/dev/parport*`）或 USB（`/dev/usb/lp*`）的双向连接读取墨量、
打印头状态与型号 ID，并支持清洗喷嘴、打印头对齐、更换墨盒等维护命令。

## 功能概述

- **命令行状态监视器 `ttink`**：`-s` 打印状态与各色墨量、`-i` 识别打印机型号、
  `-c` 清洗喷嘴、`-n` 喷嘴检查、`-a` 打印头对齐、`-r` 复位打印机、`-l` 列出内建型号表、
  `-D` 强制 D4 协议、`-L` 打印 D4 报文级调试信息
- **共享守护进程 `mtinkd`**：以 SysV 共享内存 + FIFO 为多个前端进程共享同一台打印机
  （`/var/run/mtink/<pid>` 登记 pid，`/var/mtink/<device>` 建 FIFO）
- **设备查询器 `askPrinter`**：并口走 `PPSETMODE`/`PPCLAIM`/`PPNEGOT`（IEEE 1284 协商），
  USB 走 `LPIOC_GET_DEVICE_ID`，把打印机自报的 device-id 字符串打到 stdout
- **协议实现**：内建 91 条 EPSON 型号记录（`Stylus Color/Cxx/Photo` 系列），
  D4（新式）与 REMOTE1（老式）两套指令集，含状态/墨量/错误码解码表

## OHOS 适配

- 上游 `Configure` 是手写脚本（非 autotools），自带上游开关 `-x|--no-x`
  （"If you want only the tty based version use the -x option"）。本包用 `-x -p /`
  构建**控制台版**：`ttink` + `mtinkd` + `askPrinter`，GUI 的 Motif/X11 编译与链接
  规则整段退出构建面 ⇒ **零源码补丁**。
- 唯一需要的编译开关是 `-fcommon`：上游 2007 年 C 代码大量使用暂定定义，
  clang 15 默认 `-fno-common` 会让 `ttink`/`mtinkd` 链接期报
  `ld.lld: error: duplicate symbol`（详见版本级 notes.md）。
- 打包自行 `copy()`：上游所有 `install-*` 目标都被 `if id | grep '=0(root)'` 包住，
  且写 `/etc/init.d`、`/etc/rc.d`、`/usr/lib/cups/backend`，在 Conan 打包场景不可用。
- 交付的三个 ELF 均以 `binary-sign-tool -selfSign` 自签（否则 OHOS 加载器 EPERM）。

### 已知限制（鸿蒙 PC）

1. **没有打印机设备节点**：本机实测 `/dev/lp0`、`/dev/lp1`、`/dev/parport0`、
   `/dev/usb/lp0`、`/dev/usblp0` 全部缺失（只有 `/dev/tty`、`/dev/null`、
   `/dev/urandom`、`/dev/watchdog`）。而 sysroot **有** `linux/lp.h`、`linux/ppdev.h`、
   `linux/parport.h` ⇒ 并口/USB 的 ioctl 面**编译能过、运行期无设备可测**。
   已交付的验证到「真实代码路径已执行并以确定的退出码与措辞收口」这一级；
   device-id 字符串的实际读取与 IEEE 1284 协商后的数据通路**未在本机验证**。
2. **无 `/var`**：`mtinkd` 的 pid 文件（`/var/run/mtink/`）与 FIFO（`/var/mtink/`）
   都建不了，守护进程启动即打 `mkdir : No such file or directory` 后退出（rc=0）；
   共享内存/FIFO 服务形态在本机不可用。
3. **GUI 面未交付**：Motif 版 `mtink`/`mtinkc` 需要 `motif/2.3.8` 闭包，而 ohpcd 上
   `conan install --requires=motif/2.3.8 --build=never` 实测报
   `Missing prebuilt package for 'libxext/6.4.0.1'`（motif 要 `libx11/1.8.Z`，
   而 `libxext/6.4.0.1` 的发布二进制按 `libx11/6.4.Z` 构建）⇒ 依赖它会在
   CI（`--build=<pkg>/*`，依赖必须预编译可得）结构性失败。待依赖面修复后去掉 `-x` 即可。
4. 上游字符串表为 Latin-1（2007 年），clang 15 构建共 260 行 `warning:`，其中 228 条是
   `illegal character encoding in string literal`（其余为 `-Wpointer-to-int-cast` 16、
   `-Wunused-command-line-argument` 7、`-Wimplicit-function-declaration` 5、
   `-Wpointer-sign` 2）；英文/数字表项不受影响。

### 与 Linux 的差异

- Linux 上 `configure`/`make` 默认走 X11 分支并使用 `uname = Linux` 决定是否把
  `mtinkd`/`askPrinter` 纳入 `PRG`；鸿蒙 `uname` 为 `HarmonyOS`，故本包显式点名目标。
- 上游 `Configure -m`（"simulation with libusb under Linux"）会定义 `MACOS`，
  而 `rw.c` 整体在 `#ifndef MACOS` 内、`d4lib.c` 仍调用 `devRead`/`devWrite`
  ⇒ 该模式自相矛盾，本包不使用；Linux/OHOS 面 `mainSrc/usbHlp.c` 是空翻译单元
  （`llvm-nm -u` 实测 0 个 `usb_*` 未定义符号）。

## 依赖关系

- 编译依赖：无（OHOS clang 15 工具链 + 平台 `make`；控制台版不链接 Motif/X11/libusb）
- 运行依赖：无第三方动态库（`llvm-readelf -dW bin/{ttink,mtinkd,askPrinter}` 实测三者
  均只有一条 `NEEDED Shared library: [libc.so]`）

## 参考资料

- 上游作者站点（已不响应，仅存档）：`http://xwtools.automatix.de/mtink/`
- 上游 1.0.16 原始归档（权威镜像）：`https://deb.debian.org/debian/pool/main/m/mtink/`
- 版本库（Debian salsa，含 `refs/tags/upstream/1.0.16`）：`https://salsa.debian.org/debian/mtink`
