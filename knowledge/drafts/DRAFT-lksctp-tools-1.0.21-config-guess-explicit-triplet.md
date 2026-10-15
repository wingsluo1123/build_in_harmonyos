# DRAFT-lksctp-tools-1.0.21-config-guess-explicit-triplet

> Contributor: pc2-45 | Status: Draft | Updated: 2026-09-29
> Source: lksctp-tools 1.0.21 PR r02（修正 PR 归属并重新远端交付）

## 问题

lksctp-tools 1.0.21（autotools）在 HarmonyOS PC（arm64）上 `configure` 第一阶段
报 `cannot guess build type`：GNU `config.guess` 不包含 HarmonyOS/`__OHOS__`
检测分支，`uname -s=HarmonyOS` 无法匹配任何已知系统模式。上游 GitHub archive
tarball 又不含 `configure`（需 autoreconf 自举），自举产物同样无法识别。

r01 的适配在配方 `generate()` 中显式追加 `--build=aarch64-unknown-linux-musl`
与 `--host=aarch64-unknown-linux-musl` 使 configure 通过，并在正文/回报中将该
适配点记为 E007/E011 等价命中（路径 A）。

## 根因

- `config.guess` 无 HarmonyOS 分支（E007 覆盖的第一道门槛）；
- 显式 `--build/--host` 是 E007 与 E011 `forbid_1_pattern`（`--build=|--host=|--target=`）
  明确禁止的做法：会让 `AC_RUN_IFELSE` 等运行期检测全部跳过，`config.h`
  检测结果默认化，且与 E007 推荐路径 `patch-autotools-ohos.pl`（输出标准三元组
  `aarch64-unknown-linux-ohos`）冲突。

## 方案（实际采用 + 如实记录）

配方 `conanfile.py` `generate()` 中：

```python
tc.configure_args.append("--build=aarch64-unknown-linux-musl")
tc.configure_args.append("--host=aarch64-unknown-linux-musl")
```

配套自举与工具版本证据：

- 自举命令：`autotools.autoreconf()`（配方 build()，源码树无 configure 时触发）
- tool_requires：`automake/1.18`、`libtool/2.5.4`（build profile 解析）
- 编译环境：clang 15.0.4（OHOS SDK 26.0.0.18 sysroot, musl），OHOS aarch64 profile
- 本地手工自举历史：本机 automake 1.17 安装破损（缺 Automake::Config.pm），
  曾临时以 automake-1.16.5 前置 PATH 完成 bootstrap

与知识库条目的适用性对照：

| 知识条目 | 推荐/禁止 | 本库实际 | 判定 |
|----------|-----------|----------|------|
| E007（config.guess 不识别 OHOS） | rec=patch-autotools-ohos.pl，输出 `aarch64-unknown-linux-ohos` | 未打 config.guess 补丁，改用显式 triplet `aarch64-unknown-linux-musl` | 不构成等价命中 |
| E011（umask 077/HMDFS） | forbid_1_pattern=`--build=|--host=|--target=` | 本适配点依赖被禁止参数 | 不得声称等价命中 E011 |
| E114（mktemp confXXXXXX 权限） | 与 umask 077→022 属同族 HMDFS 问题 | 配方 build() 同时做 umask 077→022（E011 推荐动作） | umask 修复动作可保留 |

结论：本适配点依赖被禁止参数（显式 `--build/--host`），不得声称等价命中
E007/E011，改判**路径 B**，本草稿入当前库 `knowledge/drafts/` 与正式 PR 同仓。

## 验证

- `conan create`（OHOS aarch64, `--build=missing`）：PASS，test_package 1/1 Test Passed
- G0-G4/L2/L4/L5 全部 PASS；finish/W2/W3 通过
- 鸿蒙特有测试：1 项，exit 0（`sctp_opt_info` EBADF 可达 + SOL_SCTP/IPPROTO_SCTP=132）
- func_tests：35 入口编译通过；32 个构建出二进制的入口实测全部因内核无 SCTP
  模块（`/proc/net/sctp` 不存在）失败（exit 139/124，首条 `BROK: socket:
  Protocol not supported` / `Socket type not supported`），3 个入口
  （test_interleave/test_re_conf/test_sctp_sendvrecvv）因 configure 条件
  （HAVE_SCTP_SENDV/HAVE_SCTP_FRAGMENT_INTERLEAVE/HAVE_SCTP_STREAM_RECONFIG）
  未检出而未构建 —— 属平台内核能力边界，非适配缺陷

## 适用边界

- 仅适用于"上游 config.guess 不识别 OHOS"且"配方确需显式 triplet 才能通过
  configure"的 autotools 库适配点；对能打 config.guess/config.sub 补丁的库，
  仍应优先走 E007 推荐路径（`patch-autotools-ohos.pl`）
- 库类型（无运行期自检依赖）受影响面小于 CLI/需要 AC_RUN_IFELSE 的平台库；
  依赖运行期检测结果的库不得采用本做法

## 反例 / 限制

- 反例：需要 `AC_RUN_IFELSE` 结果决定 `config.h` 宏的平台库，显式 triplet 会
  导致检测全部跳过、宏默认化 → 编译期级联错误
- 限制：`aarch64-unknown-linux-musl` 与 OHOS 实际三元组（aarch64-linux-ohos）
  不一致，跨平台可移植性差；`--disable-tests` 同时关闭 func_tests 编译
  （测试由 test_package 消费者验证承载）
- 待审核：是否应改走 E007 的 config.guess 补丁路径以消除 forbid_1_pattern 冲突
