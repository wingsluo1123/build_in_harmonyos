# libqb 2.0.10 编译笔记

## 编译信息

- 软件名: libqb
- 版本: 2.0.10
- 构建系统: autotools
- 目标平台: HarmonyOS PC (aarch64-linux-ohos)
- 编译日期: 2026-10-04
- 状态: published

## 编译流程

### 1. 源码获取

从 GitHub ClusterLabs 下载：

```
https://github.com/ClusterLabs/libqb/releases/download/v2.0.10/libqb-2.0.10.tar.xz
```

### 2. 平台适配

#### 问题 1: config.guess / config.sub 无法识别 HarmonyOS

`build-aux/config.guess` 不认识 HarmonyOS（该平台 `uname -s` 返回 `HarmonyOS` 而非 `Linux`），
configure 无法确定目标三元组。

**解决方案**: 用 skill 权威脚本 `scripts/patch-autotools-ohos.pl`
（依据 `references/autotools-patterns.md` #2/#3，禁止 `--build/--host` 绕过）生成最小增量补丁：

- `0001-build-aux-config.guess.patch`: 识别 HarmonyOS，产出 `aarch64-unknown-linux-ohos`
- `0002-build-aux-config.sub.patch`: 接受 `*-linux-ohos` 三元组

#### 问题 2: config.status 临时目录权限问题

configure 内联的 config.status 用 `(umask 077 && mktemp -d ...)` 建临时目录。鸿蒙 HMDFS 上
新建目录会落在 `file_manager` 组，而进程的 primary GID 与之不同；`umask 077` 使组无写权限，
随后写 `subs1.awk` 报 Permission denied。

**解决方案**: `0003-configure.patch` 把该处 `umask 077` 改为 `umask 022`（对齐 a52dec 先例），
使组可写。仅改动 configure 内联脚本，不触碰源码逻辑。

#### 问题 3: AX_PROG_DATE 不识别 toybox date（CI 失败根因）

`configure.ac:823` 用 autoconf-archive 的 `AX_PROG_DATE` 判定 date 类型：GNU date 靠
`date --version | head -1 | grep "\(GNU\|uutils\)"`，BSD date 靠 `date -v 1d`。鸿蒙系统
`date` 是 **toybox 0.8.12**，两条都不匹配 → 走 `AC_MSG_ERROR`，configure 报
`date utility unable to convert epoch to UTC` 硬失败。

实测 toybox date **支持 GNU 语义的 `date -u -d@<epoch>`**（configure 选中该形式后仅用于
man 页/日志时间戳；本配方已 `--disable-man`），只是探测方式（`--version` 版本串、`--date=`
长选项）不匹配。故 `0004-configure-date-toybox.patch` 做两处最小改动：

1. GNU date 探测正则增加 `toybox`（`\(GNU\|uutils\|toybox\)`）；
2. epoch 探测 `date --date=@1512031231` 改用短选项 `date -d @1512031231`（GNU/toybox 均可）。

改后 configure 判定 `ax_cv_prog_date_gnu_date=yes` / `gnu_utc=yes`，选用
`UTC_DATE_AT="date -u -d@"`，与 toybox 能力一致。

> **环境语义不可迁移警示（W0b）**: 本地首次适配能过 configure，是因为本机在
> `/storage/Users/currentUser/usr/local/bin` 装了 GNU coreutils（`date` = GNU 9.10），
> 且 conan profile `[buildenv]` 前置了该目录；CI worker 该目录为空 → `date` 落到 toybox →
> 上述硬失败。**本机命令不可假定 CI 逐字可执行**。修复后不依赖 PATH 中是否存在 GNU date。


### 3. Configure 参数

```
--disable-man --enable-slow-tests
```

`--enable-slow-tests` 用于把上游 `util.test` 一并纳入测试范围（否则 TESTS 只有 11 个）。

### 4. 依赖

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| glib | 2.84.0.1 | configure.ac `PKG_CHECK_MODULES([GLIB], [glib-2.0 >= 2.0])` |
| libxml2 | 2.15.3.1 | configure.ac `PKG_CHECK_MODULES([libxml], [libxml-2.0])` |
| check | 0.15.2 | 上游 `tests/` 套件（`check >= 0.9.4`） |

注意：三者都必须在配方 `requirements()` 中**直接**声明。经传递依赖拿到的
`package_folder` 为 `None`，`PkgConfigDeps` 会退化成裸 `-Iinclude`，configure 报
`No package 'glib-2.0' found`。

### 5. 测试

上游测试套件（`make check`）在 conan create 内完整执行，12 个用例（TESTS 11 +
`HAVE_SLOW_TESTS` 的 `util.test`）全部运行，结果写入 `tests/test-suite.log`：

- 通过 3 个：`sock_ipc_wrapper.test` / `resources.test` / `blackbox-segfault.sh`
- 失败 9 个：全部因 CI 沙箱环境限制（非 libqb 缺陷）
  1. libcheck 把 IPC 临时文件硬编码在 `/tmp`（`libcheck.so` 字符串 `%s/check_XXXXXX` + `/tmp`），
     而鸿蒙 HMDFS 上 `/tmp` 只读，`TMPDIR` 覆盖无效 → 8 个 `check_*.test` 报
     `Unable to create temporary file for communication`；
  2. `start.test` 需要写 `${localstatedir}/run`（= `//var/run`），沙箱不可写。

配方对「测试根本没跑起来」（依赖库加载失败 exit 127 / 崩溃 ≥128）仍保留硬性失败判定。

用例执行改为 `make check -j1`（仓库标准做法，见 bison/blis/libgee 等）：串行执行，
避免 `start.test` / `ipc.test` 的 qb 守护进程与 Unix socket 在用例并发时相互干扰
（libcheck 已为 `test_ipc_stress_connections*` 设置 3600s 单用例超时，不会无限挂起），
使测试阶段结果稳定可复现。

注意：配方 `shared` 默认为 `False`（`--enable-static --disable-shared`），产出 `libqb.a`；
这是本仓库主流约定（1183 个配方 vs 599 个默认 shared）。

另外，`make check` 在 CI 沙箱里需要显式 `LD_LIBRARY_PATH` 指向直接依赖的 libdir，
否则测试二进制报 `Error loading shared library libcheck.so`（exit 127）。

### 6. 消费者测试

`test_package/test.c` 以下游消费者身份独立链接发布出的制品并真实调用 API：
`qb_rb_open`（共享内存 ring buffer）/ `qb_rb_chunk_write` / `qb_rb_chunk_read` 往返一致性 /
`qb_rb_shared_user_data_get` / `qb_rb_refcount_get` / `qb_log_init` / `qb_log_ctl` / `qb_log`。

## 环境注意事项

- 本环境 **无 `install` 命令**（仅 `~/usr/local/bin/ginstall`），构建驱动需 `INSTALL=install`。
- 鸿蒙 HMDFS 上 `/tmp` 只读；zsh 的 here-document 临时文件用 `TMPPREFIX`（默认 `/tmp/zsh`）
  而非 `TMPDIR`，本地 CI 需同时设置 `TMPDIR` 与 `TMPPREFIX` 到可写目录。
- HMDFS 会强制目录权限/属主（新建目录恒定落在 `file_manager` 组、模式 `drwxrws--x`）。

## 对话记录

### 对话 #1 — 依赖链预检与 worktree 建立

- 2026-10-04: 加载 build_in_harmonyos skill，W0 依赖预检确认 libqb/corosync/pacemaker/kronosnet
  均未发布，因此采用依赖链全适配（路径 B）。
- 2026-10-04: 建立独立 worktree `.worktrees/libqb-2.0.10`，用 `patch-autotools-ohos.pl` 生成
  config.guess/config.sub 增量补丁；PR 补丁统一为 -p1（`a/` `b/`）格式。

### 对话 #2 — configure 失败定位

- 2026-10-04: 排查 configure 失败：定位到 HMDFS + `umask 077` 组合导致 config.status 临时目录
  不可写，改为 `umask 022` 后 configure 通过。

### 对话 #3 — 上游测试运行环境

- 2026-10-04: G2 conan create 起初 12 个用例报 `Error loading shared library libcheck.so`（exit 127），
  定位为构建环境未注入依赖 libdir，改为显式内联 `LD_LIBRARY_PATH` 后库可加载；剩余 9 个用例
  失败根因是只读 `/tmp` 与不可写 `/var/run`，属环境限制，逐条记录在 `reports/test-report.md`。

### 对话 #4 — 归档发布

- 2026-10-04: conan-verify 全门通过（G0–G4），finish 归档完成，状态 published；
  产出 `packaging/libqb-2.0.10-ohos-aarch64.tar.gz`。

### 对话 #5 — CI configure 失败修复（date 检测）

- 2026-10-12: PR #14609 CI 报 `configure: error: date utility unable to convert epoch to UTC`
  （类别：编译失败 / Autotools configure 失败）。定位为 `AX_PROG_DATE` 不识别 toybox date
  （见「问题 3」）。新增 `0004-configure-date-toybox.patch`。
  本地以「CI 忠实 profile」（去掉 `usr/local/bin` 前置，令 `date`=toybox）复现并验证通过。


## 最终状态

- 状态: published
- 制品: `packaging/libqb-2.0.10-ohos-aarch64.tar.gz`
- 补丁: 4 个（0001/0002/0003/0004）
- 编译结束。

该版本适配工作已结束（COMPLETED）。

