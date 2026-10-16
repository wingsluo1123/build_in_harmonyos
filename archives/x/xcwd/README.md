# xcwd — X current working directory

`xcwd` 是一个单文件 X11 命令行工具：读取**当前焦点窗口**所属进程的工作目录并
打印到 stdout，便于把新终端/文件管理器直接打开到与当前程序相同的目录
（如 `urxvt -cd "$(xcwd)"`）。当无法判定焦点窗口的目录时回退 `$HOME`；连 X 显示
都连接不上时以非零状态退出。

## 功能概述

- 通过 `XGetInputFocus` / `XQueryTree` 取得焦点窗口句柄；
- 读取窗口属性 `_NET_WM_PID` 得到进程号，缺失时退回 `WM_CLASS` 与进程名匹配；
- 沿父子关系找到最深的子进程，经 `/proc/<pid>/cwd` 解析其工作目录并打印；
- 任一步失败则打印 `$HOME`；无法连接 X 显示时直接以 `EXIT_FAILURE` 退出。

产物是命令行程序 `bin/xcwd`（application 包，无库/头文件）。

## OHOS 适配

| 要点 | 说明 |
|------|------|
| 平台闸 | 上游 `Makefile:7` 用 `UNAME:=$(shell uname)` 选分支；HarmonyOS 的 `uname -s` 返回 `HarmonyOS`，既不命中 `Linux` 也不命中 `FreeBSD` → `Makefile:20` 直接 `$(error Operating System not supported.)`。适配在**不改源码**的前提下，通过命令行传入上游自带变量 `UNAME=Linux`，选中上游自身的 Linux 分支（`/proc` + `glob`，在 OHOS bionic 下行为正确）。 |
| `-DLINUX` 必须显式重述 | GNU make 的命令行变量优先于 makefile 内赋值，`ifeq` 分支里的 `CFLAGS += -DLINUX` 会被静默丢弃；而 `LINUX`/`BSD` 两个 `#ifdef` 分支都定义了 `getProcesses()`/`readPath()`，丢宏不会报错，只会编出功能缺失的二进制。配方因此在命令行 CFLAGS 中重述上游自带标志并追加 `-DLINUX`。 |
| 依赖 | 头/库全部来自制品仓（`libx11/6.4.0`、header-only `xorgproto/2025.1`）。OHOS 系统无同名 `libX11`，产物不写 `RUNPATH`（OHOS 加载器拒绝指向 Conan 缓存目录的 `RUNPATH`），运行期由 `conanrun` 提供搜索路径。 |
| 已知限制 | OHOS PC 无 X 服务器（无 `Xorg`/`Xvfb`/`Xwayland`，制品仓亦无对应配方，无 `/tmp/.X11-unix`），因此依赖真实 X 会话的功能（焦点窗口、`_NET_WM_PID`、`WM_CLASS`、`/proc/<pid>/cwd` 打印）**未在真机端到端验证**；消费者测试覆盖可验证契约（无显示退出码、`#ifdef LINUX` 分支已编入、ELF 动态段不变量、运行期依赖负向验证）。逐项说明见 `0-2.gbpe2c777c/notes.md` 与 `test_package/MANIFEST.yml`。 |

## 依赖关系

- 编译依赖：`libx11/6.4.0`、`xorgproto/2025.1`（传递：`libxcb/1.16`、`libxau/1.0.11`、`libxdmcp/1.1.5`、`xtrans/1.6.0`）
- 运行依赖：`libX11.so.6`（来自 Conan 包，由 `conanrun` 环境提供库路径）
- 运行前提：可连接的 X 显示（`DISPLAY`）

## 参考资料

- 上游仓库：https://github.com/schischi/xcwd
- 本仓库配方：`archives/x/xcwd/0-2.gbpe2c777c/conanfile.py`

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| `0-2.gbpe2c777c` | built | 锁定上游 commit `e2c777c`，手写 Makefile 适配，消费者用例 5/5（13 项检查）通过 |
