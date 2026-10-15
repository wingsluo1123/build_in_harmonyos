# kamailio-xhttp_prom 6.0.6 适配笔记

## 编译环境

- 构建系统: makefile（kamailio 经典 Makefile 体系：src/Makefile + Makefile.defs）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，/data/service/hnp/bin/clang）
- 目标: aarch64-linux-ohos（HarmonyOS PC）
- 状态: published

## 软件与模块定位

`xhttp_prom` 是 kamailio 6.0.6 源码包内的一个模块（src/modules/xhttp_prom/），为
kamailio 的 xhttp（HTTP/WebSocket）服务面导出 Prometheus 指标，供 /metrics 抓取；
模块自带 Prometheus 指标实现（prom.c / prom_metric.c），上游 README 明示无外部依赖，
模块 Makefile 的 `LIBS` 为空。产物为单个插件共享库 `xhttp_prom.so`，由 kamailio
运行时 `loadmodule "xhttp_prom.so"` 加载。因此打包口径参照同版本先例
`archives/k/kamailio-tls/6.0.6`：取官方源码包全量构建，只编译并打包该模块。

## 编译步骤

```bash
# 1) make cfg 生成 src/config.mak（探测到 aarch64-unknown-linux-ohos 三元组）
make cfg include_modules=xhttp_prom extra_defs='-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 \
    -DHAVE_SCHED_YIELD -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H \
    -DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN'

# 2) 编译 xhttp_prom 模块
make modules modules=modules/xhttp_prom -j1 extra_defs='<同上>'
```

产物：`src/modules/xhttp_prom/xhttp_prom.so`（895,296 字节，ELF64 aarch64，ET_DYN，
not stripped；NEEDED 仅 `libc.so`，FLAGS 含 `BIND_NOW`）。

## 历史先例核验（W0b）

同版本（6.0.6）kamailio 模块级适配已有先例：`archives/k/kamailio-tls/6.0.6`。
- **环境语义可迁移**：先例与本任务在同一 SDK（26.0.0.18）、同一交叉编译器（clang 15.0.4）、
  同一构建体系（make cfg + make modules）下完成，历史命令在 CI 环境逐字可执行，
  无额外工具链依赖（不像 Rust/OCaml 类需要 tool_requires）。
- **历史踩坑逐项比对**：先例记录了「OS=harmonyos 不在 Makefile.defs 平台分支 →
  core 头 HAVE_* 宏缺失 → resolve.h #error」，本模块同样包含 core 头（sr_module.h 链），
  配方沿用同一 `extra_defs` 宏集（逐字比对一致），未偏离。
- 先例与本任务的差异：tls 依赖 openssl/3.5.7（SSL_BUILDER/LOCALBASE 探测分支），
  本模块 0 依赖，无 SSL 探测分支；本任务新增的验证手段见下「适配测试设计」。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | core 头（resolve.h/sched_yield.h 等）在 OS=harmonyos 下 `#error` | Makefile.defs 只处理 linux/solaris/freebsd/darwin 等分支，harmonyos 不注入任何 HAVE_* 探测宏 | make 命令行 `extra_defs` 注入 linux 分支等价宏集（见编译步骤）。每个宏的符号均对照 OHOS SDK（musl 语义）头文件与 libc 实证：gethostbyname2（netdb.h，_GNU_SOURCE 守卫内）、sched_yield/sched_setscheduler（sched.h）、MSG_NOSIGNAL/msg_control（sys/socket.h）、timegm（time.h）、ip_mreqn（netinet/in.h）、alloca.h。运行期再以 dladdr 确认这些符号由 `/lib/ld-musl-aarch64.so.1` 导出 |
| 2 | HAVE_UNION_SEMUN 是否注入 | musl sys/sem.h 不导出 union semun | 不注入：core lock_ops.h 在宏未定义时自带条件定义，注入反而冲突（与先例结论一致，编译通过实证） |

## 源码修改

无。平台探测宏全部经 make 命令行 `extra_defs` 注入，未改动任何源文件，0 补丁。

## 依赖版本

无外部依赖。制品仓探测（并行确认，避免遗漏依赖闸）：
`libprom`/`prometheus` 类包在制品仓无记录，但上游实现已内联进模块（prom.c/prom_metric.c），
模块 UND 符号分类显示仅 35 个 kamailio 核心符号 + 18 个 OHOS libc 符号，
无第三类外部库符号 → **无依赖缺口**（PF4 依赖闸零风险）。

## 上游测试清点（R51 三步法）

| 清点项 | 结果 | 证据 |
|--------|------|------|
| 源码包顶层 test/ 目录 | 不存在 | `ls -d test` → 无（utils/kamctl/dbtextdb/tests/ 是 kamctl 工具的 Python 测试数据，与模块无关） |
| 模块目录内测试源文件 | 无 | `ls src/modules/xhttp_prom/` → CMakeLists.txt / Makefile / README / doc / librpath.lst / makecfg.lst / prom.c / prom.h / prom_metric.c / prom_metric.h / xhttp_prom.c / xhttp_prom.h |
| 模块 Makefile 测试目标 | 无 | `grep -c test src/modules/xhttp_prom/Makefile` → 0 |
| 模块 CMakeLists.txt | 无测试 | 无 add_test/enable_testing |
| 顶层与 src/Makefile | 无 check 目标 | 上游 CI 走 pkg/kamailio 的 Smoketest（需运行中的 SIP 场景），非源码内自动化套件 |

**结论**：上游 xhttp_prom 无自动化测试套件 → 本 PR 属"补全测试用例"分支（上游测试
0 项，适配侧新增 2 个用例 / 33 项断言，全部通过）。上游测试用例未被修改（无补丁）。

## 适配测试设计（消费者视角，替代纯结构断言）

模块的未定义符号面已实测清楚：53 个 UND 符号 = 35 个 kamailio 核心符号（运行期由
kamailio 主程序导出：`_pkg_root`/`_shm_root`/`parse_params`/`fixup_spve_*`/`counter_*`/
日志宏等）+ 18 个 OHOS libc 符号，**不存在第三类符号**。据此构造真实消费者：

1. **consumer（C 程序，运行期真实加载）** —— 复刻 kamailio 模块加载器的动作序列：
   `dlopen(模块)` → `dlsym("exports")` 取 `struct module_exports`（本地镜像 80 字节，
   与 `llvm-readelf` 实测 `exports` 符号 size=80 交叉校验）→ 解析模块名(`xhttp_prom`)、
   22 项配置命令（prom_check_uri/prom_dispatch/prom_counter_reset/prom_gauge_reset/
   prom_counter_inc/prom_gauge_set/prom_histogram_observe）、10 个模块参数（含绑定地址
   非空校验）→ `dlsym("mod_register")` 并**实际调用** → 核对 10 个 `prom_*` 指标 API →
   核对 6 个 OHOS libc 平台符号并以 `dladdr` 确认归属 `/lib/ld-musl-aarch64.so.1`。
   共 17 项断言。模块以 BIND_NOW 构建，故 `dlopen` 成功即等价于"符号闭包在本平台完整"。
   kamailio 核心符号由 `gen_shim.py` 生成的占位定义提供（占位符不被调用，仅满足重定位；
   `sr_kemi_modules_add` 因会被 `mod_register()` 调用而生成真实空实现）。
2. **check_artifact.py（产物合规 + 鸿蒙平台适配核对）** —— 共 16 项断言：随包文件三件
   （模块 / licenses/COPYING / 上游模块 README）、ELF64+AArch64+ET_DYN、NEEDED 仅
   `libc.so`、无 RPATH/RUNPATH、导出 `exports`/`mod_register`/10 个 `prom_*` 符号、
   无 glibc 专属未定义符号（`__xstat`/`_IO_2_1_stdout_`/`stat64` 等）、53 个 UND 符号
   全部归类且 18 个平台符号逐个在 OHOS libc 中可解析（符号分类与 `gen_shim.py` 同源，
   单一事实源）。

`gen_shim.py` 生成 shim 前会先向 OHOS libc 查询候选符号，凡 libc 提供的符号一律
不生成占位符（避免 shim 遮蔽真实平台符号，保证平台核对不被架空）。

## 验证结果

```bash
$ file xhttp_prom.so
ELF shared object, 64-bit LSB arm64, not stripped          # 895,296 字节
$ llvm-readelf -h xhttp_prom.so | grep -E "Type|Machine"
Type:    DYN (Shared object file)      Machine: AArch64
$ llvm-readelf -d xhttp_prom.so | grep -E "NEEDED|BIND"
NEEDED  Shared library: [libc.so]
FLAGS   BIND_NOW
$ ./consumer <pkg>/lib/kamailio/modules/xhttp_prom.so
consumer: 17/17 checks passed
$ python3 check_artifact.py
check_artifact: 16/16 checks passed
```

`conan create` 全量验证见 `.ci-result.json`（finish 自动写入）。

## 知识库使用与扩展

- **使用**：本任务的诊断入口为"平台探测宏缺失"类问题，配方与验证设计参考了
  E004 / E078（musl BIND_NOW：dlopen 时要求全部符号在加载期可解析 → 消费者用例把
  "能否 dlopen"作为 ABI 完整性判据、以及为什么需要符号 shim）与 E019
  （NEEDED/RPATH 与 musl 运行期依赖解析 → 产物动态段核对项）。
- **沉淀**：本次适配新增的平台知识——「kamailio 模块体系在 HarmonyOS 上平台探测宏缺失」
  （Makefile.defs 无 harmonyos 分支 → core 头 HAVE_* 全缺 → 编译中断；解法为 make 命令行
  extra_defs 注入等价宏集，0 补丁）以及新增验证手法（UND 符号分类 + 独立消费者 dlopen
  加载 + OHOS libc 符号归属核对）——记入本目录 manifest.yaml 的 knowledge_gained 与本节，
  **未随本 PR 提交知识图谱草稿**，可供后续 kamailio 模块适配直接复用。
---

**编译结束**: 2026-09-27 14:34
**最终状态**: published
