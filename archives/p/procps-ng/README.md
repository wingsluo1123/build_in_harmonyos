# procps-ng

## 简介

procps-ng 是 Linux/Unix 的系统与进程信息工具集：提供 `ps`/`top`/`free`/`uptime`/`vmstat`/`w`/
`pgrep`/`pkill`/`pidof`/`sysctl`/`slabtop`/`tload`/`watch` 等命令行工具，以及供其它程序复用的
**libproc2** 库。

## 功能概述

- **进程查看**：`ps`（进程快照）、`top`（实时，curses 界面）、`pgrep`/`pidof`（按名/模式查找）、
  `pkill`（按名/模式发送信号）
- **系统资源**：`free`（内存）、`vmstat`（虚拟内存/IO/CPU）、`uptime`（运行时长与负载）、
  `slabtop`/`tload`
- **登录用户**：`w`（读取 utmp/utmpx 记录）
- **内核参数**：`sysctl`（读写 /proc/sys）
- **库**：libproc2 —— 进程列表、内存、负载、uptime、用户等 API
  （头文件 `include/libproc2/`，pkg-config 名 `libproc2`）

## OHOS 适配要点

- **config.guess 识别 HarmonyOS**：上游发布 tarball 自带的 config.guess 不认识 HarmonyOS，
  回落到需要可写临时目录的编译探测并失败 → 补丁加入 HarmonyOS 分支
  （识别为 `aarch64-unknown-linux-ohos`）。
- **HMDFS 临时目录**：configure 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，
  在 HMDFS 上该目录呈 0700 且拒所有者写入（config.status 报 could not setup config files
  machinery）→ 补丁把该处 umask 改为 022。
- **utmpx 接口缺失**：OHOS 的 `utmpx.h` 只定义 `struct utmpx` 与常量，既不声明也不导出
  `getutxent/setutxent/endutxent`（libc 导出的是 `getutent/setutent/endutent/utmpname`）
  → 以上游风格的**函数级**探针 `HAVE_UTMPX_FUNCS`（`AC_CHECK_FUNCS`）选择访问族，
  替代只反映头文件存在的 `HAVE_UTMPX_H`。
- **缺 strverscmp**：OHOS libc 不提供 `strverscmp`，链接 libproc2 时报未定义符号
  → 以上游自带备用实现 `local/strverscmp.c` 补入 `library/sort.c`
  （由上游既有的 `HAVE_STRVERSCMP` 守卫）。
- **terminfo**：设备不带 terminfo 数据库，`top`/`watch` 运行时须把 ncurses 的
  `share/terminfo` 指给 `TERMINFO`/`TERMINFO_DIRS`，否则批处理 `top -b` 也会静默以非零码退出。
- **已知限制**：`procps_linux_version()` 在本平台返回文档规定的负错误码——内核版本串
  （/proc/sys/kernel/osrelease）为 `HongMeng Kernel 1.12.0`，不含 Linux 版本号，
  /proc/version 亦不可读。

## 依赖关系

### 编译依赖

- **ncurses**（6.6 / ncursesw）— 必需，top/watch/slabtop/tload 的 curses 界面
- 可选但未启用：libnl、gettext（NLS）、systemd

### 运行依赖

- 采用静态链接（`--disable-shared --enable-static`），工具本身无额外运行时库依赖
- `top`/`watch` 需要 terminfo 数据（见上）

## 参考资料

- 官网与源码：https://gitlab.com/procps-ng/procps
- 发布包：https://downloads.sourceforge.net/project/procps-ng/Production/
