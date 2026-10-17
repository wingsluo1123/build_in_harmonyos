# Erlang/OTP

## 简介

Erlang/OTP 是爱立信开源的并发编程语言平台与运行时系统。核心由三部分组成：**BEAM 虚拟机**（抢占式调度器、每进程 GC、多核 SMP 支持）、**Erlang 编译器**（编译器本身用 Erlang 编写，即"自举编译器"）、以及 **OTP 标准库与应用集合**（kernel、stdlib、crypto、ssl、mnesia、eunit、common_test 等二十余个 application）。本次交付的 `28.5.0.7` 为 OTP 28 成熟维护线版本。

## 功能概述

- **BEAM 虚拟机**：`erts-16.4.0.6`，JIT（`emu_flavor=jit`）、SMP 调度器、抢占式轻量进程、每进程独立 GC、原子/信号/定时器/mmap 运行时设施
- **开发工具链**：`erl`（REPL/脚本）、`erlc`（编译器）、`escript`（独立脚本，含 shebang 直跑）、`erl_call`、`epmd`、`dialyzer`、`typer`、`ct_run`
- **编译器自举**：`compiler` application 的编译器由 Erlang 编写，运行在本包所构建的 BEAM 上——即"用自己造出来的虚拟机编译自己"
- **标准库与 NIF/driver**：`stdlib`、`kernel`；`zlib` NIF（压缩）、`crypto` NIF（OpenSSL 3 后端）、`inet` 驱动（TCP/UDP/socket）
- **测试框架**：`common_test`、`eunit` 随包提供，可直接承载用户侧测试

## 基本信息

- 官方网站: https://www.erlang.org/
- 源码仓库: https://github.com/erlang/otp （tag `OTP-28.5.0.7`）
- 许可协议: Apache-2.0

## 版本

- **28.5.0.7**：已编译（Conan `erlang/28.5.0.7`，`os=OHOS`/`arch=armv8`/`clang-15`）

## OHOS 适配要点

Erlang/OTP 不使用单一 autotools 工程：release tarball 自带**手写顶层 `configure`**，用来驱动 `erts` 与少数几个自带 autoconf 的应用，其余工作由递归 `make`（`otp_build` 体系）完成。因此配方不套用 `AutotoolsToolchain`，而是直接驱动 `./configure` + `make` + `make install`。移植中的实测关键点：

1. **shell 自举**：OHOS 的 `/system/bin/sh`（mksh）无法承载 autoconf 脚本，须注入 `CONFIG_SHELL`/`SHELL=/data/service/hnp/bin/bash`，让 configure 与其派生的递归 make 全部自举到 bash。
2. **三元组识别**：OHOS 三元组 `aarch64-unknown-linux-ohos` 不在自带 `config.sub` 的枚举中，需补 `ohos*` OS 与 `linux-ohos*-` 内核模式（源码树内 `make/autoconf`、`erts/autoconf`、`lib/common_test/test_server` 三份 `config.sub`）。
3. **autoconf 临时目录权限**：autoconf 辅助脚本以 `umask 077` 创建临时目录，OHOS 下这种权限的目录不可写，导致 configure 中途失败；统一改为 `umask 022`。
4. **musl 缺口**（逐条探针实证）：
   - `gethostid()` 不存在 → `erl_interface` 在 `__OHOS__` 下改用 `s.hid = 0`（与 Android/Haiku 同路径）
   - `mallopt()` 原型在 `<malloc.h>` → `erts/emulator/beam/utils.c` 的条件编译加入 `__OHOS__`
   - `uname()` 返回厂商内核串 `HongMeng Kernel 1.12.0`，不符合 `<version>.<patchlevel>` 格式 → `inet` 驱动将其按现代内核处理（等价于 `SO_BSDCOMPAT` 已废弃），不再打告警
5. **termcap 探测**：`erts/configure` 只找 `tinfo/ncurses/curses/...`，OHOS 侧依赖提供的是宽字符归档 `libncursesw.a`，需把 `ncursesw` 加入 `termcap_libs`。
6. **无 mkfifo 的并行 make**：OHOS 无 `mkfifo(1)`，GNU make 默认的 FIFO jobserver 建不起来，递归 make 会退化成 `-j1`；GNU make ≥ 4.4 可用 `--jobserver-style=pipe` 恢复并行。
7. **图形/可选面边界裁剪**：`wx`（需要 GUI 工具包）、`odbc`（需要 unixODBC）、`jinterface`（需要 Java 编译器）在 HarmonyOS PC 不可达，以 `--without-wx`、`--without-odbc`、`--without-javac` 显式关闭；核心交付面是 BEAM/编译器/标准库（TUI 工具链完整可用）。

## 依赖关系

- 编译/运行依赖：`openssl/3.5.7`（crypto NIF）、`zlib/1.3.1`（zlib NIF）、`ncurses/6.5`（erl 交互式终端）
- 运行形态：`erl` 等命令行走 Conan `VirtualRunEnv` 暴露 PATH，VM 与标准库按安装根目录相对定位

## 参考资料

- 官方文档: https://www.erlang.org/docs
- 构建指引: `$ERL_TOP/HOWTO/INSTALL.md`、`$ERL_TOP/HOWTO/TESTING.md`
- 版本发布页: https://github.com/erlang/otp/releases/tag/OTP-28.5.0.7
