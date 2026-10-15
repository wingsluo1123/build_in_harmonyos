# lmbench 3.0-a9 适配笔记

## 编译环境

- 平台：HarmonyOS PC（HAD-W32，aarch64，HarmonyOS 6.1.0.117，内核 1.12）
- 构建系统：makefile（上游自带 `scripts/build` 驱动，无 configure/CMake）
- 编译器：OHOS SDK clang 15.0.4（`tools.build:compiler_executables`，R33）
- 编译日期：2026-10-14
- 状态：built（conan-verify G0-G4 通过，未 upload；upload 由合并后 release 流水线执行）

## 上游测试清点（R51）

| 项目 | 结果 |
|------|------|
| `tests/`、`test/` 目录 | 无（`find . -maxdepth 3 -type d -iname 'test*'` 为空） |
| Makefile test/check 目标 | 无（`grep -n '^test\|check' src/Makefile` 为空；仅 `testmake` 供 `scripts/make` 探测 gmake） |
| ctest/pytest/unittest 注册 | 无（`grep -ril ctest\|pytest\|unittest` 无命中） |
| 上游“测试面” | 基准程序本身：49 个 `lat_*`/`bw_*` 程序运行即产出测量值 |

口径：上游测试用例 N=0（无断言式测试框架）；适配后以 test_package 消费者回归补全
（26 项断言，见 `test_package/MANIFEST.yml` 与 `reports/test-report.md`）。

## 编译步骤

```sh
# 源码：https://downloads.sourceforge.net/project/lmbench/development/lmbench-3.0-a9/lmbench-3.0-a9.tgz
#      sha256 cbd5777d15f44eab7666dcac418054c3c09df99826961a397d9acf43d8a2a551
cd src
make OS=aarch64-ohos CC=<OHOS SDK clang> AR=llvm-ar    # 等价于 conanfile.py 的 build()
```

- `make`（默认目标 `lmbench`）先执行 `../scripts/build all` + `../scripts/build opt`：
  编译器特性探测（写入 `$TMPDIR`）→ 生成 `bin/aarch64-ohos/` 下 49 个基准程序 +
  `lmbench.a` + 驱动脚本；随后 `package()` 按上游 install 目标布局复制产物。
- OS 标签显式传 `aarch64-ohos`：`scripts/os` 在未显式指定时会回退到
  `scripts/gnu-os`（config.guess），该脚本在 OHOS 上无法运行（需要可写临时目录
  且不认识 HarmonyOS 系统类型，实测报 `unable to guess system type`）。
- 依赖：无第三方库依赖（W0：`init-build` 依赖解析“所有依赖已就绪”；
  源码仅链接 libc + `-lm`；`-lnsl`/`-lsocket`/`-lrt`/`-lrpc` 探测在 OHOS 均不命中，
  属正常）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 特性探测全部静默失败（`-DRUSAGE`/`-DHAVE_DRAND48` 等缺失，valloc 探测假阴性） | `scripts/build` 的探测临时文件基址固定 `/tmp/dummy`，候选目录仅 `/usr/tmp`、`/var/tmp`、`/tmp`；OHOS `/tmp` 只读（E002）、另两者不存在 | 补丁 0001：探测基址优先 `$TMPDIR`（Conan/CI 均有可写 TMPDIR；CI /tmp 可写时行为不变） |
| 2 | `fatal error: 'rpc/rpc.h' file not found` | `bench.h` 无条件 include Sun RPC 头（`rpc/rpc.h`、`rpc/types.h`）；musl/OHOS 无 Sun RPC | 补丁 0002：按上游自身的 `HAVE_pmap_clnt_h` 探测保护 include；未定义时补 `TRUE/FALSE`（原由 `rpc/types.h` 提供，`lat_usleep.c` 使用） |
| 3 | `lat_rpc` 依赖整套 Sun RPC API（CLIENT/SVCXPRT/xdr_*）无法编译 | 同上（musl 无 RPC） | 补丁 0003：`HAVE_pmap_clnt_h` 未定义时提供明确报错的诊断入口（非 0 退出）；TCP/UDP/Unix 延迟与带宽基准不受影响 |
| 4 | `lib_tcp.c`/`lib_udp.c` 链接 `pmap_set/pmap_unset/pmap_getport` 失败 | 上游 `NO_PORTMAPPER` 保护不完整（`tcp_server`/`tcp_done`/`tcp_connect`/`udp_done` 四处仍无条件引用） | 补丁 0004/0005：用既有 `NO_PORTMAPPER` 宏保护四处 pmap 调用（负端口号直连路径不受影响） |
| 5 | 共享设备高负载时基准程序长时间无输出（看似 hang） | lmbench 自适应标定（`find_N` ±2% 窗口）对测量噪声敏感；另一参与者并发 `conan create -j8` 时负载 ~26/20 核，10 次测量 min 值散布 2 倍以上，N 被放大到 10^8 量级，单次 duration 即秒级 | 非适配缺陷：按上游官方机制先运行 `enough`/`timing_o`/`loop_o` 取本机标定参数（`scripts/config-run` 同口径），再运行基准；test_package 对三件套设超时回退（详见 reports/test-report.md） |
| 6 | `lat_unix_connect -s` 无法服务（`bind: Operation not permitted`） | OHOS 平台禁止在文件系统创建命名 AF_UNIX socket（实测 /tmp、HOME、work 等所有可写目录 bind 均 EPERM；抽象 socket 正常可用）；上游该程序硬编码 `/tmp/af_unix` | 平台能力限制，非适配缺陷：未改动上游行为（尝试过 TMPDIR 感知补丁，确认 bind 仍在任何目录 EPERM 后回退）；`lat_unix`/`bw_unix` 用 `socketpair` 正常 |

## 源码修改（补丁清单）

| 补丁 | 文件 | 类型 | 内容 |
|------|------|------|------|
| 0001 | `scripts/build` | portability | 探测临时文件基址 `BASE` 与候选目录支持 `$TMPDIR` |
| 0002 | `src/bench.h` | portability | RPC 头 include 加 `HAVE_pmap_clnt_h` 保护；未定义时补 TRUE/FALSE |
| 0003 | `src/lat_rpc.c` | portability | RPC 实现整体受 `HAVE_pmap_clnt_h` 保护，未定义时诊断入口 |
| 0004 | `src/lib_tcp.c` | portability | 三处 pmap 调用加 `NO_PORTMAPPER` 保护 |
| 0005 | `src/lib_udp.c` | portability | `udp_done` 的 pmap 调用加 `NO_PORTMAPPER` 保护 |

补丁均无 `__OHOS__` 平台宏注入（PF5 口径：guard 全部使用上游既有特性探测宏
`HAVE_pmap_clnt_h`/`NO_PORTMAPPER` 与环境变量 `TMPDIR`）。

## 依赖版本

- 无第三方库依赖（libc + libm 由平台/Conan toolchain 提供）。

## 验证结果

```text
conan-verify G0-G4 / L2/L4/L5：见 reports/conan-verify-report.md（本地，未入仓）
W3 本地 CI（ci/conan/build_and_test.sh）：exit 0，见 .ci-result.json（本地，未入仓）
test_package：26/26 checks passed（含 6 项基准真机实跑 + consumer 链接测试）
真机样例（空载时刻）：lat_syscall null 1.09us；lat_pipe 34.6us；
                      bw_pipe 1120 MB/sec；lat_ctx(2) 11.7us；lat_proc fork 8358us
```

## 注意事项

- 基准数值受机器负载影响显著；共享设备/CI 上只作功能冒烟口径（标签 + 正数值），
  不与官方 Linux 数据做数值对比。
- `lat_rpc` 在 OHOS 上按平台事实返回明确报错（非 0 退出）；`scripts/config-run`
  的 “RPC [default yes]” 交互项在该平台上应回答 no。
- `scripts/results` 完整套件驱动（config-run → lmbench runner）未随包分发
  （上游 install 目标也不安装它）；包内为独立基准程序 + 标定三件套。

### 对话 #1（2026-10-14，W0–W1 准备）
- 平台任务 #8520（lmbench 3.0-a9，assigned，claimer=kasumizawa-miyuu，taskBranch=feat/lmbench-3.0-a9）确认；共享设备（三人）与 Conan 单实例互斥纪律确认。
- 建隔离 worktree `lmbench-wt`（基于 main b6fd9ca0a）并切分支；W0：源码无第三方依赖（init-build「所有依赖已就绪」）；init-build（SourceForge 官方源，sha256 cbd5777d…a551）；lang-preflight 通过（detected=c，c↔cpp 兼容族）。

### 对话 #2（2026-10-14，W1–W2 适配）
- 源码勘察：make + `scripts/build` 自驱动（无 configure/CMake）；探测脚本临时目录 /tmp 只读导致全部探测静默失败 → 补丁 0001（`$TMPDIR` 优先）；`bench.h` 无条件 include `rpc/rpc.h`（musl 无 Sun RPC）→ 补丁 0002-0005（按上游 `HAVE_pmap_clnt_h` 保护 include、补 TRUE/FALSE；lib_tcp/lib_udp 的 pmap 调用按既有 `NO_PORTMAPPER` 补齐保护；lat_rpc 改为诊断入口）。
- 全绿构建 49 个基准 + `lmbench.a`；真机 smoke（hello/lat_syscall/lat_pipe/bw_pipe）通过；`lat_rpc` rc=1 诊断符合预期。
- 新发现：文件系统命名 AF_UNIX socket 平台 EPERM（`lat_unix_connect -s` 不可用）。曾做 TMPDIR 感知补丁，实测 `bind` 在任何可写目录均 EPERM（抽象 socket 正常），遂回退该补丁并记录为平台限制（上游行为未改动）。

### 对话 #3（2026-10-14，W2–W3 调试与证据）
- 高负载标定发散定位：`find_N` ±2% 窗口对测量噪声敏感（并发 `conan create -j8` 时 load ~26/20 核），`-D_DEBUG` 重编译 + /proc/proc 采样确认 N 被放大到 10^8 量级（单程序长时间无输出）。按上游官方机制（`enough`/`timing_o`/`loop_o`，等价 `scripts/config-run`）固定标定参数解决；test_package 采用该机制并加超时回退（回退不伪造数值）。
- test_package 26 项断言（包布局、标定三件套、6 项基准真机实跑、RPC 平台能力断言、负向对照、consumer 链接 `libmbench.a` 运行 `tvsub()`）；本地 dry-run 26/26。
- W3：conan-verify G0-G4 + L2/L4/L5 PASS；本地 CI（增量模式）L0/L1/L2/L4/L5 PASS 且 test_package 在 `conan create` 内执行 26/26；`.ci-result.json` exit_code=0。

### 对话 #4（2026-10-14，W3–W4 提交准备）
- `finish`：状态 built；非阻塞警告：G0 clean-verify 假定 autotools（本包无 configure，平台限制，已记录）、step5b/step8 为他人知识条目与工具 bug。
- 白名单提交 17 文件（commit f99e3b614）；`pre_pr_audit generate`（17 文件）后由独立子代理完成 W4 审计：verdict=pass（P0=0，P1=0；P2=1，P3=2 建议项），审计还独立下载官方源复核 sha256 一致、独立清点上游测试 N=0。
- 提交准备：packaging 发布 tarball + `.staging-verified` + `reports/audit-result.json`（W4）。

**编译结束**: 2026-10-14 20:19
**最终状态**: built
