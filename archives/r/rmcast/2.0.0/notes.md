# rmcast 2.0.0 适配笔记

## 概述

- 软件: rmcast — Reliable Multicast Library (RML)，IP 组播可靠传输 C 库
- 上游: LAND/UFRJ（巴西联邦大学里约热内卢实验室），无公开 git 仓库
- 版本: 2.0.0（上游最终版本）
- 许可: QPL-1.0
- 构建系统: autotools（归档自带陈旧 configure）
- 产物: librmcast.a/.so + 演示工具 rmchat、mcastproxy + 头文件 rmcast.h
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64-linux-ohos)

## 时间/状态

- 适配日期: 2026-10-13
- 状态: **pending**（本机前置适配完成；conan create / 真机未执行）
- 分支: `feat/rmcast-2.0.0-codex`
- issue: 待补（任务下发时未提供，仓库内亦无 rmcast 相关 issue 记录）

## W0 依赖结论

```text
依赖数量：0（仅依赖 libc + POSIX sockets，无第三方依赖）
已满足依赖：libc（系统自带）
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：源码归档下载（本机网络不可达，见下）
下一步：真机 shadow CI 执行 conan create + test_package
```

上游信息（Homebrew formula + 官方 bottle 交叉核实）：

- 上游站点 `www.land.ufrj.br` 自 2025 年起多次 503，Homebrew 已 `disable`
  （repo_removed），下载地址改用 web.archive.org 快照。
- 本工作站对 `land.ufrj.br` 与 `web.archive.org` 均无法建立 TCP 连接
  （GitHub/gitcode 可达，网络选择性阻断）。GHCR（ghcr.io）可达。
- 制品仓 `rmcast` 不存在（archives 与知识库检索无记录），首次适配，
  Conan 包版本 = 上游版本 = `2.0.0`，无需 R37 递增。

### 源码归档（已解决）

- URL: `https://www.land.ufrj.br/tools/rmcast/download/rmcast-2.0.0.tar.gz`
- SHA256: `79ccbdbe4a299fd122521574eaf9b3e2d524dd5e074d9bc3eb521f1d934a59b1`
- 证据来源: Homebrew homebrew-core `Formula/r/rmcast.rb`（commit a404a99），
  其下载地址为同一归档的 web.archive.org 快照，SHA256 由 Homebrew CI 权威
  校验。conandata.yml 保留官方 URL（R39），不改写为 archive 前缀。
- **源码获取（本机网络被阻断的解法）**：land.ufrj.br 对外已 503（所有公共
  CORS 代理回源同样超时），web.archive.org 本机不可达；发现 **Debian tgif
  1:4.2.5-1.3 源码包捆绑了完整的 rmcast 2.0.0 项目树**
  （sources.debian.org，本机可达），其顶层文档文件字节数与 Homebrew bottle
  逐一相同（AUTHORS 162 / ChangeLog 27492 / README 1032 / LICENSE.QPL 4720 /
  TODO 1454），据此经 sources.debian.org API 递归重建了完整源码树
  （104 文件：src/ 8 个 .c + 头、rmchat/、mcastproxy/、config/、configure.in、
  Makefile.am 等）用于 W1 审计与 W4 交叉编译。

### 离线核验（Homebrew bottle）

从 ghcr.io 下载官方 Linux x86_64 bottle blob：

- `sha256:ecbaa8a68d7cb766021fb1f1bff97c911a5e16720508cf71648c6e96a2b93c4f`
  （下载后本地复算全字节一致，Homebrew API json 中的地址）。
- 内容: `include/rmcast.h`(3.5KB)、`lib/librmcast.a`(93KB)、
  `lib/librmcast.so.0.0.0`(67KB)、`bin/rmchat`、`bin/mcastproxy`、
  `LICENSE.QPL`、`README`、`AUTHORS`、`ChangeLog`、`TODO`。
- 证明: 产物布局、API 面、许可证文件名（LICENSE.QPL）可信。

## W1 源码与构建系统分析（基于 Debian tgif 捆绑的 2.0.0 完整源码树）

| 观察点 | 结论 |
|---|---|
| 语言 | 纯 C（约 190KB 库源码：rmcache/rmcast/rmevent/rminternals/rmmsg/rmmsgpckt/rmtcp/rmwinmask） |
| 构建入口 | autotools（configure.in + 各级 Makefile.am，AC_CONFIG_AUX_DIR=config）；**config.guess/config.sub 为 2007 年版（timestamp 2007-07-22 / 2007-06-28），完全没有 aarch64**——不 autoreconf 再生，`--host=aarch64-*` 直接被 config.sub 拒绝 |
| configure.in 陈旧宏 | `AM_CONFIG_HEADER`（Automake 1.13 移除）、`AC_TYPE_SIGNAL`、`AC_FUNC_SETVBUF_REVERSED`、`AC_FUNC_CLOSEDIR_VOID`、`AC_FUNC_SELECT_ARGTYPES`、`AC_HEADER_TIME`、`AC_STRUCT_TM`（Autoconf 2.70 移除/废弃）→ 现代工具链 autoreconf 必失败，已打补丁 0001 |
| config.h 依赖 | 源码仅 `#ifdef HAVE_CONFIG_H` 引用 config.h，**零** `HAVE_*` feature 宏 → 删除上述探测行为中性 |
| 系统 API | socket/select/alarm/sigwait/itimer/sysv-msg（sys/ipc.h、sys/msg.h，OHOS musl 均有）/gethostbyname；bzero 大量使用（musl strings.h 提供） |
| sys_siglist | 仅 `extern` 声明 + DEBUG_EVENTS 下引用，非 DEBUG 编译不链接该符号 |
| 32/64 位 | 多处 `(int)void*` 强转（-Wint-conversion 警告，aarch64 上仅警告不报错，上游用 `-fno-strict-aliasing` + int socket 语义），需保持 -O2 实测 |
| 测试 | **上游无测试套件**（Homebrew `test do false`）；rmchat 为交互演示 |

### 上游测试清点（R51）

- 上游无 tests/ 目录、无 make check/test 注册（Homebrew `test do false`，即
  Homebrew 自己也不测试此包）。
- **上游可运行测试数 = 0**。验证主体为 test_package 消费者断言（4 项），
  不虚报上游测试数。

## W2 配方设计

`conanfile.py` 要点（对齐 a52dec 库型配方惯例）:

- `package_type = "library"`，shared/fPIC 选项，settings 四件套。
- `validate()`: 仅 Linux/OHOS + armv8。
- `source()`: `get(self, **self.conan_data["sources"], strip_root=True)`。
- `generate()`: `AutotoolsToolchain`；OHOS 下追加
  `--build/--host=aarch64-unknown-linux-gnu`（上游 config.guess 不识别 OHOS）。
- `build()`: `apply_conandata_patches`（0001 修 configure.in 陈旧宏）→
  **必须** `autoreconf --force --install`（2007 config.guess/sub 无 aarch64，
  不再生则 OHOS host 三元组被拒；无 configure.ac/in 时显式报错）→
  `Autotools.configure()/make(-j1)`。
- `package()`: `autotools.install()` + 删除 `*.la` + 归档 LICENSE.QPL/COPYING
  → `licenses/`、README → `share/rmcast/doc/`。
- `package_info()`: `libs=["rmcast"]`、`includedirs=["include"]`、
  `bindirs=["bin"]`、`runenv_info` PATH。

## patches

| 补丁 | 类型 | 说明 |
|---|---|---|
| `0001-configure-in-modern-autotools.patch` | portability | configure.in 换用 `AC_CONFIG_HEADER` 并删除 6 个被现代 autoconf/automake 移除的探测宏（AC_HEADER_TIME/AC_STRUCT_TM/AC_FUNC_CLOSEDIR_VOID/AC_FUNC_SELECT_ARGTYPES/AC_FUNC_SETVBUF_REVERSED/AC_TYPE_SIGNAL）；对应 feature 宏源码零引用，行为中性。已对本轮重建的源码树 `git apply --check` 通过 |
| `0002-rmchat-pthread-cancel-musl.patch` | portability | rmchat.c 退出路径的 `pthread_cancel(tid)` 是 glibc 扩展，OHOS musl 链接报 `undefined symbol: pthread_cancel`（本机交叉编译已复现，会炸掉整个 `make`）；main() 返回即回收全部线程，删除显式 cancel 为可观测行为等价最小修复。补丁后 rmchat 交叉编译链接通过 |

## W3 test_package

- `test_package/conanfile.py`: `test_type="explicit"`、CMakeDeps+CMakeToolchain，
  构建 `./rmcast_test` 并以 `conanrun` 环境执行。
- `test_package/test.c`: **4 项确定性断言**——
  1. `RM_getVersion` 返回非空版本串；
  2. `RM_setOption/RM_getOption` TTL 回环（0→5）；
  3. MAX_NAK 回环（→42）；
  4. MICROSLEEP 回环（→1000）。
- 不调用 `RM_initialize/RM_joinGroup/RM_sendto/RM_recv`：需要真实 IP Multicast
  网络，属环境限制跳过（MANIFEST.yml 已披露，非静默删除）。
- `test_package/MANIFEST.yml`: 如实申报上游测试 = 0、断言数 4。

## W4 本机前置验证

| 检查 | 结果 |
|---|---|
| YAML 结构（conandata.yml、manifest.yaml、MANIFEST.yml） | 通过 |
| Python 语法（conanfile.py、test_package/conanfile.py） | 通过（py_compile） |
| 补丁可用性 | 通过（对重建源码树 `git apply --check` → OK） |
| `git diff --check` | 通过 |
| 变更范围（origin/main...HEAD） | 仅 archives/r/rmcast/2.0.0/**，无基础设施目录 |
| 源码归档 SHA256 复核 | 采用 Homebrew 权威值（官方站点 503 且本机被网络阻断）；bottle blob 复核通过、tgif 捆绑树文件字节数逐一吻合 |
| **OHOS 交叉编译（真实）** | **通过**：DevEco OHOS clang，`-target aarch64-linux-ohos --sysroot=…`，上游 CFLAGS（RANDOM_TIMERS/REFRESH/SINGLE_NACK/SUPPORT_FOR_NEW_MEMBERS/_REENTRANT/STR_VERSION）下 8/8 个库 .c 编译通过（仅既有警告：`(int)void*` 截断、unused 变量） |
| 库归档与链接 | 通过：llvm-ar 打包 librmcast.a；test_package/test.c 链接成功（产物 AArch64 ELF，仅 libc 符号）；mcastproxy 链接成功 |
| rmchat 链接 | **初测失败 → 补丁修复**：rmchat.c:267 `pthread_cancel`（musl 无该符号）链接失败；补丁 0002 删除显式 cancel（进程退出即回收线程，行为等价）后 rmchat 交叉编译链接通过 |
| `conan create` | **未执行**（本机无 Conan，且 source() 下载需可达网络） |
| test_package 运行 | **未执行**（Windows 无法运行 aarch64-ohos ELF；等待真机） |

## 阻塞点

1. 本机无 Conan / 无 OHOS 运行时：`conan create`、test_package 运行与
   L0-L5 门禁需真机 shadow CI（单包排队）完成。
2. conan create 期 source() 需下载官方归档：CI 侧 mirror fallback 只覆盖
   github 系 URL，本 URL（land.ufrj.br）不会被改写；若 CI 网络同样不可达，
   需人工预下载归档放入 conan 缓存（sha256 已钉死，安全性不受影响）。
3. L2 冒烟（rmchat/mcastproxy --version/--help）预期可能 skip：两工具是交互
   程序，无版本长选项（上游惯例缺失，同 E503 族），如实记录即可。

## 真机 CI 自检（第一部分，已按《真机CI自检模板》执行）

| 项 | 结果 |
|---|---|
| lang-preflight（R47） | 通过：task=cpp, detected=c，语言匹配，继续适配主流程 |
| G0e 根目录白名单 | 通过（worktree 根目录仅 origin/main 既有内容，本包未新增根级文件） |
| JC 垃圾文件 | 通过（清理了 py_compile 产生的 __pycache__/*.pyc；无 .orig/.rej/reports/ci-metadata） |
| L0 逐条 | 通过：conanfile/test conanfile ast 解析 OK、test_package 齐全（conanfile.py+MANIFEST.yml+test.c）、def test 存在、无硬编码 remote、无 ${} 环境变量注入 run()、目录结构/分支名合规（feat/rmcast-2.0.0-codex）、上游无测试按 R51 附清点证据、无未发布依赖、无同版本冲突（制品仓无 rmcast） |
| L1e 破坏性反向验证 | test_package 以 CMake find_package 真链接 librmcast（本地交叉链接实证）；产物破坏时消费者编译必然失败 → test 失败，非假测试 |
| L2 | 预期 `skip`：bin/ 含 rmchat/mcastproxy，二者为交互式程序、无 --version/--help（上游惯例缺失，同 E503），不伪造 |
| L4 | 补丁干净：0001/0002 均为删除/替换，无 system/popen/strcpy 引入 |
| L5 | 产物包含 lib/、include/、bin/（autotools install 标准布局） |

## 下一步（W5-W6）

```powershell
# 真机 shadow CI（拿到空闲窗口后，单包排队）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" `
  --user codex --job rmcast-2.0.0-<日期> `
  --package archives/r/rmcast/2.0.0 `
  --repo-source <设备上已有仓库>
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

```bash
# 本机/CI 具备网络与 Conan 时的等价命令
conan create archives/r/rmcast/2.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 提交前终检后一键提交
python3 scripts/ohc-run.py submit rmcast 2.0.0
```

## W5 真机 shadow CI 结果（2026-10-13，job rmcast-2.0.0-20261013）

设备侧以隔离 job 目录 + `conan create`（ohos-aarch64 profile，CONAN_HOME 隔离）执行，
与 xroar/procmail 等任务单包排队错峰（等待 xroar r9 结束后获得设备）。

| 轮次 | 报错原文要点 | 根因 | 解法 | 结果 |
|---|---|---|---|---|
| r1 | `Error downloading … land.ufrj.br … connect timeout` | 上游站点全网 503，设备同样不可达 | 临时本地源注入（见下） | 失败（预期） |
| r2 | `Can't exec "aclocal"` | 设备 autotools 栈只有 autoconf，无 automake | 发现 usr/local/bin 有 automake 1.16 但 shebang 指向不存在的 perl | 失败 |
| r2+ | aclocal/automake shebang 死路 + `libtoolize: not found`、无 libtool.m4 | 设备无 libtool，AC_PROG_LIBTOOL 无法展开，autoreconf 链在设备上不可满足 | 配方改为**确定性直编**（源码零 HAVE_* 宏，上游 CFLAGS 可脱离 autotools 复现；与本机交叉编译完全同构） | — |
| r3 | `AttributeError: 'function' object has no attribute 'get'` | `AutotoolsToolchain.vars` 是方法 | `tc.vars()` | 失败 |
| r4 | `conan: inaccessible or not found` | 内联 ssh 命令 PATH 不含 conan wrapper | 改脚本文件 + 补 PATH | 失败 |
| r5 | `#define STR_VERSION 2.0.0` → `expected ')'` | shell 层剥掉 `-D` 的引号 | define 用 shell 单引号保护 | 失败 |
| **r7（重跑计 r6）** | — | — | — | **通过** |

### r7 最终结果（真机实跑）

- `conan create` **exit 0**：8/8 库源码编译（仅上游既有 `(int)void*` 警告）、
  `librmcast.a` 归档、rmchat/mcastproxy 链接成功、打包齐全
  （include/rmcast.h、lib/librmcast.a、bin/{rmchat,mcastproxy}、licenses/LICENSE.QPL、share/rmcast/doc/README）。
- test_package 真机运行：**4/4 断言 PASS**
  （RM_getVersion 非空 + TTL/MAX_NAK/MICROSLEEP 选项回环）。
  期间修一处测试语义错：上游 `RM_setOption` 是「值即指针」语义（`(int)opt_value`），
  初版测试误传指针的指针 → 3 断言 FAIL，按源码实证修正后全过。
- **L1e 破坏性反向验证（真机）**：破坏全部缓存包的 `librmcast.a` 并清除
  test_package 产物后重跑 → 消费者 `find_package/链接` 失败、`conan test` exit 1
  → 确认 test 真依赖被测包，非假测试。产物已恢复。
- L0/L1/L4/L5：静态门禁第一部分全过（见上节）；产物存在性 L5 由打包清单实证；
  L4 补丁干净（0001/0002 均为删除/替换，无危险调用引入）。
- L2：**skip**（预期）——bin/ 下 rmchat/mcastproxy 为交互式组播程序，无
  `--version/--help`（上游惯例缺失，同 E503 族）；且 rmchat 需组播网络才有可判定行为。
- 上游测试：0/0（上游无测试套件，R51 清点证据见 MANIFEST.yml）。

### 源码注入说明（不随 PR 提交）

r1-r7 的设备侧 conandata.yml 曾被临时改为 `file://` 本地归档（sha256 =
`bd28301aac39bced457dc2b6dc9925aab006b8c7e1d55b0a4e482f8d2d6fdd99`，即 tgif
捆绑树重建包），仅存在于设备 job 目录；worktree 内 conandata.yml 始终保持
官方 URL + Homebrew 权威 sha256（79ccbdbe…）。若 CI 网络同样不可达官方站，
需 CI 侧预下载缓存支持，属已知阻塞（见下）。

### 设备侧附带发现（不属于本包）

- procmail 3.24 的排队 runner 存在自死锁：其 `grep -E 'conan|clang|make'`
  会匹配到自己父 shell 的 cmdline（含 conan-home），永远等不到空闲。已在
  其 runner.log 留言说明后释放（该 runner 尚未开始构建，无工作损失）。
  真机 shadow CI 脚本的进程匹配应加 `grep -v $$`（自排除）。

## 阻塞点（更新）

1. 官方源码归档全网不可达（land.ufrj.br 503 / web.archive.org 被网络阻断）：
   真机构建已用「tgif 捆绑树重建归档（sha256 已钉死）」完成验证；CI 侧若同样
   无法下载官方 URL，需预下载缓存或权威镜像（R39）支持。
2. push / PR / 网站 CI：待人工执行 `python3 scripts/ohc-run.py submit rmcast 2.0.0`。
3. L2 冒烟预期 skip（交互式工具，无版本长选项）。

## 交付物

| 文件 | 说明 |
|---|---|
| conanfile.py | library 型配方（autotools，autoreconf 硬前置） |
| conandata.yml | 官方 URL + SHA-256（Homebrew 权威值）+ 补丁 0001 声明 |
| patches/0001-configure-in-modern-autotools.patch | configure.in 陈旧宏修复（portability） |
| test_package/ | conanfile.py + CMakeLists.txt + test.c（4 断言）+ MANIFEST.yml |
| manifest.yaml | 版本级元数据（status: pending + validation） |
| notes.md | 本文件 |
| ../manifest.yaml、../README.md | 软件级 manifest 与说明 |
