# DRAFT-erlang-28.5.0.7: BEAM/语言平台类上游在 OHOS+musl 的适配诊断树

- 条目主题：语言平台型大上游（Erlang/OTP 28.5.0.7：BEAM 虚拟机 + 自举编译器 + 20+ application）在 HarmonyOS PC 上的问题分类法
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：erlang/28.5.0.7；同范式适用于所有"语言运行时 + 大量 application"型上游
- 互链：`DRAFT-fex-emu-2608-ohos-musl-uapi-runtime-differences`（musl/UAPI 差异族）、`CONFIG-GUESS-BUILD-TYPE-OHOS`（config.guess 策略）、`DRAFT-erlang-28.5.0.7-private-build-system-cross-adaptation`（私有构建体系）

## 为什么需要"诊断树"

一次性把所有报错当同一类问题会走偏：OTP 的失败点横跨 **构建脚本假设**、**C 运行时缺口**、
**运行时平台能力**、**可选依赖面** 四个互不相干的层面。先把错误归到面，再决定"补丁修"
还是"声明边界"。

## 面 1：构建自举面（必须补丁修，可上游化）

| 现象 | 根因 | 处理 |
|---|---|---|
| `configure` 中途死掉 / 脚本行为诡异 | OHOS `/system/bin/sh`(mksh) 承载不了 autoconf 脚本 | 注入 `CONFIG_SHELL`/`SHELL=/data/service/hnp/bin/bash`（configure 会自举重入 bash，递归 make 也继承） |
| `Invalid configuration ... aarch64-unknown-linux-ohos` | 自带 `config.sub` 未登记 ohos 内核 | 补 `ohos*` OS + `linux-ohos*-` 内核模式（OTP 里有 3 份 config.sub） |
| `cannot guess build type` / `ts:install` 直接失败 | 自带 `config.guess` 认识 `Linux`，不认识 `HarmonyOS`（`uname -s` 报 HarmonyOS） | 补 `HarmonyOS|OpenHarmony|OHOS` 分支输出 `<arch>-unknown-linux-ohos`；临时替代：显式传 `TARGET=`/`--build=` |
| configure 中途 "目录不可写" | autoconf 辅助脚本 `umask 077` 建临时目录 | 统一改 `umask 022` |
| 递归 make 退化成 `-j1` | OHOS 无 `mkfifo(1)`，GNU make 默认 FIFO jobserver 建不起来 | GNU make ≥ 4.4 用 `--jobserver-style=pipe` |

## 面 2：musl C 缺口面（必须补丁修，逐条实证）

- `gethostid()` 在 OHOS musl 无实现 → `erl_interface/src/connect/ei_connect.c` 在 `__OHOS__` 下走
  `s.hid = 0`（上游已有 Android/Haiku 分支，只是没登记 OHOS）。
- `mallopt()` 原型在 `<malloc.h>` 而非 `<malloc.h>` 之外 → `erts/emulator/beam/utils.c` 的条件编译加 `__OHOS__`。
- `uname()` 返回厂商内核串 `HongMeng Kernel 1.12.0`，不满足 `%u.%u` → `inet` 驱动按"现代内核
  （`SO_BSDCOMPAT` 已废弃）"处理，而不是打警告返回失败。
- `erts` termcap 探测只找 `tinfo/ncurses/curses/termcap/termlib` → OHOS 侧依赖给的是宽字符
  归档 `libncursesw.a`，需把 `ncursesw` 加进 `termcap_libs`。

> 与 `DRAFT-fex-emu-2608-ohos-musl-uapi-runtime-differences` 同族：都是"glibc 有 / musl 无或不同"，
> 处理原则一致——在源码里按 `__OHOS__` 精确收口，不用 `-D` 全局糊。

## 面 3：运行时平台边界面（声明 + 归因，不改上游库）

**HMDFS 权限模型 → Erlang distribution 不可用**（本库最有价值的发现）：

1. HMDFS 上 `chmod` 不生效，文件恒为 `-rw-rw----`（0660）、目录 `drwxrws--x`。
2. OTP 的 `auth` 读 `~/.erlang.cookie` 时强制 owner-only 校验 → 恒失败：
   `Cookie file ... must be accessible by owner only`，随后 `net_sup/auth` 起不来、`kernel` 启动
   失败（单节点直接崩）。
3. 逐层最小化复现（全部在 OHOS PC 本机）：
   - `net_adm:names()` 正常（epmd 注册与端口都拿到）→ 分布式名字服务 OK；
   - `gen_tcp:connect({127,0,0,1}, <dist port>)` 返回 ok → dist 监听端口 TCP 可达；
   - 两个 `erl -sname nX -setcookie S` 节点之间 `net_adm:ping` 恒 `pang`、
     `net_kernel:connect_node` = false、`nodes()` = [] → **节点间握手**这一层失败。
4. 缓解：用 `-setcookie`/`ERL_AFLAGS=-setcookie ...` 显式给 cookie，单节点即可带 distribution 启动；
   测试 harness 中凡要起 secondary / shielded node 的用例（`peer:start_it`、`run_on_shielded_node`）
   按环境边界排除并逐条归因。
5. 副产品：`os:type()` 返回 `{unix,harmonyos}` 不需要改代码 —— 它由 erts 的 `os_flavor()`
   在运行时 `uname()` 决定（编译期 host_os 只影响 `aarch64-unknown-linux-ohos` 这类字符串）。

## 面 4：可选面边界（显式关闭 + 如实标注）

`wx`（需 GUI 工具包）、`odbc`（需 unixODBC）、`jinterface`（需 javac）在 OHOS PC 不可达 →
`--without-wx --without-odbc --without-javac`，在 PR/notes 里标注，不计入核心交付面。

## 验证

```
cwork/_install/bin/erl -noshell -eval 'io:format("~s~n",[erlang:system_info(otp_release)]),halt().'
=> 28   （erts-16.4.0.6, jit, smp:20:8）
ts:install + ts:run(compiler,[batch]) => TEST COMPLETE, 5536 ok, 6 failed of 5554
```

## 关联

`DRAFT-fex-emu-2608-ohos-musl-uapi-runtime-differences`（musl/UAPI）、`CONFIG-GUESS-BUILD-TYPE-OHOS`
（config.guess 三策略）、`DRAFT-erlang-28.5.0.7-private-build-system-cross-adaptation`。
