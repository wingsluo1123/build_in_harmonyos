# Test Report — shfs 0.35

**Package**: `shfs/0.35@ohpcd/stable`
**Date**: 2026-10-17
**Harness**: `test_package/test_shfs.sh`（由 `conan create` 的 test() 阶段执行；完整原始日志为 `reports/conan-create.log`，按仓库惯例 `reports/*.log` 不入 PR，可在本地 W3 运行记录中查阅）
**Result**: 9 cases run, 0 failed

上游没有测试目标：顶层 `Makefile` 的 target 只有 `all/clean/install/uninstall/utils*/module*/docs*/dist/distclean/deb*/rpm*`，
`make -n check` 直接报 `No rule to make target 'check'`。上游唯一自带的测试工件是随 mount 工具发布的
两个能力探测脚本 `shfsmount/shell-test.in`、`shfsmount/perl-test.in`（被投递给远端 shell 执行并把结论读回）。
两者均已逐字执行（U1/U2），即上游测试用例 2/2 全量覆盖。

## 用例清单（用例数 == 断言数 == 9；断言按用例级 pass/fail 计，用例内部合计约 30 个检查点，任一失败该用例记 FAIL）

| # | 用例 | 类别 | 断言 | 结果 |
|---|------|------|------|------|
| U1 | `U1-shell-test.in` | 上游测试用例 | `/bin/sh res/shfs/shell-test.in` 输出恰为 `ok stable`（19 个 POSIX 原语 type 检查全通过） | PASS |
| U2 | `U2-perl-test.in` | 上游测试用例 | `/bin/sh res/shfs/perl-test.in` 输出以 `ok stable` 开头（perl≥5 + Fcntl/IO::File/POSIX 可加载） | PASS |
| H1 | `H1-ohos-perl-handshake` | 鸿蒙特有测试 | 打包后的 `shfsmount` 以本机 `/bin/sh` 顶替远端主机跑通全链路：上游 probe 通过 → `selected: perl` → 两次 `reply: ### 200` → 进程恰好停在 `mount(2)` 被 seccomp 拦下的 SIGSYS(159)，且 `/proc/mounts` 无残留 | PASS |
| H2 | `H2-ohos-nonroot-gate` | 鸿蒙特有测试 | 非 root 应用 uid 下 `-o cachesize=4,ro` 原样装配进 mount data（跟踪行逐字符比对，含 `,mnt=<挂载点>`）；`-o uid=0` 在建连接前退出 2 并打印 `'uid=0' used by non-root user!` | PASS |
| C1 | `C1-version` | CLI 契约 | `shfsmount -V` 输出 `shfsmount version 0.35(2)`，证明配方显式传入的 `SHFS_VERSION` 已烧进二进制 | PASS |
| C2 | `C2-help` | CLI 契约 | `shfsmount --help` 退出 0 且 usage 含 `--cmd=COMMAND` / `--type=TYPE` / `--nomtab` | PASS |
| C3 | `C3-unknown-type` | CLI 契约 | `shfsmount -t nosuch …` 退出 2 并打印 `Cannot create connection`（不触发 mount(2)、不写 mtab） | PASS |
| C4 | `C4-invalid-mountpoint` | CLI 契约 | 挂载点不存在时退出 2 且打印 `Invalid path`；上游把 NULL 交给 `%s`，musl 打印 `(null)` 而非段错误 | PASS |
| C5 | `C5-umount-contract` | CLI 契约 | `shfsumount` 无参 usage 退出 1；`-v` 输出 `shfsumount version 0.35(2)` 退出 0；普通目录被 statfs 魔数守卫拒识（`Invalid argument`, 退出 1） | PASS |

## 汇总

| 指标 | 数值 | 判定 |
|------|------|------|
| 总测试数 | 9 | — |
| 通过 | 9 | PASS |
| 失败 | 0 | FAIL |
| 跳过 | 0 | SKIP |
| 上游用例覆盖率 | 2/2 | ✅ 全量执行 |

✅ 结论：9/9 通过，上游自带测试用例 2/2 全量覆盖，另新增鸿蒙特有端到端用例 2 条 + CLI 契约用例 5 条。

## 执行日志

逐字摘自 `conan create` 的 test() 阶段输出（`reports/conan-create.log`，日志不入库，此处为原文拷贝，
非人工转写；`p/b/shfsa08540fa1f361` 为本次构建的 conan 包 ID）：

```
======== Testing the package: Executing test ========
shfs/0.35@ohpcd/stable (test package): Running test()
shfs/0.35@ohpcd/stable (test package): RUN: "/data/service/hnp/bin/bash" "/storage/Users/currentUser/sztu/.worktrees/shfs-0.35/archives/s/shfs/0.35/test_package/test_shfs.sh" "/data/storage/el2/base/files/home/.conan2/p/b/shfsa08540fa1f361/p"
[PASS] U1-shell-test.in
[PASS] U2-perl-test.in
[PASS] H1-ohos-perl-handshake
[PASS] H2-ohos-nonroot-gate
[PASS] C1-version
[PASS] C2-help
[PASS] C3-unknown-type
[PASS] C4-invalid-mountpoint
[PASS] C5-umount-contract

9 cases run, 0 failed
OK: shfs 0.35 OHOS suite passed (9/9)
```

## 已知未纳入自动化的一项

shell 协议的远端 helper（`shfsmount/shell-code.in`）在 `s_init` 里对硬编码路径 `/tmp/._shfs_.<i>` 逐个
`mkdir` 试探，失败时用 `expr` 自增重试到 10000。本机 `/tmp` 可写时首试即中（全链路 ~1s），但 `/tmp`
不可写时会退化为 10000 次 fork——该最坏分支的下限实测 4 分 15 秒（计时对象是裸自增循环
`/bin/sh -c 'i=0; while test $i -lt 10000; do i=\`expr $i + 1\`; done'` → `4:15.23 total`，不是整条挂载链路）。
本机的 `/tmp` 是 hmfs 上的实体目录（`/dev/block/.../userdata` 挂载，mode `drwxrws---`、属主 `1076:expert`），
并非 tmpfs：能不能写只取决于运行 uid 是否在 `expert` 组。所以同一份脚本在不同沙箱下要么 ~1s、要么 4 分钟，
计时口径随沙箱成员身份漂移；这是移植后的既有行为、非本次适配引入，也正是它不进自动化的原因。
因此 shell 协议只自动化到上游探测脚本本身（U1），协议全链路的端到端消费者用例走无循环的 perl 分支（H1，`s_init` 仅设环境变量并回 `### 200`）。
手工验证记录：`shfsmount -t shell -c "exec /bin/sh" -vvv -n <mnt>` → `Testing shell... ok stable` /
`selected: shell` / 两次 `reply: ### 200` / SIGSYS(159)，与 H1 形态一致。

## 已知限制

1. `mount(2)`/`umount2(2)` 被鸿蒙 seccomp 拦截，挂载动作本身在 OHOS PC 上不可完成：`shfsmount` 全链路恰好停在 SIGSYS(159)。这是平台 syscall 能力边界，不是适配缺陷（H1/C5 把这两个停止点固化成了断言）。
2. Linux 内核模块 `shfs/`（顶层 `make all` 的 `module` 分支）在无内核模块加载能力的平台上没有对应物，配方只构建 `shfsmount/` 用户态工具。
3. mtab 写入分支（补丁 0002/0003）只有链接期证明，运行期无法触发（受限制 1 影响，走不到 `update_mtab()`）。
4. shell 协议的 `s_init` 挂载点探测在 `/tmp` 不可写时退化为 10000 次 `expr` fork（实测 4 分 15 秒），故 shell 全链路只做手工验证记录，自动化端到端用例走 perl 分支。

## 链接期已验证（无运行期等价物）

`addmntent(3)` 缺失的替换（补丁 0002/0003）由链接本身证明：OHOS sysroot 的 `mntent.h` 只导出
`setmntent/endmntent/getmntent/getmntent_r`，未改用 `shfs_addmntent()` 前 `ld.lld` 报
`undefined symbol: addmntent`。运行期无法触发 mtab 写入分支——`mount(2)` 被 seccomp 拦死，
`shfsmount` 走不到 `update_mtab()`，`shfsumount` 走不到其 mtab 重写（H1/C5 分别断言了这两处停止点）。
