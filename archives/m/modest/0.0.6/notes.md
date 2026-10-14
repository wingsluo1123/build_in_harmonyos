# modest 0.0.6 适配笔记

## 编译环境
- 构建系统: makefile (GNU Make，非 autotools；Makefile + Makefile.cfg + 模块 Makefile.mk)
- 编译日期: 2026-10-04
- 编译器: clang (OHOS 工具链, aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
export TMPDIR=$HOME/tmp
export CC=clang CFLAGS="-fPIC -O2 -Wno-void-pointer-to-enum-cast"
make clone CC=clang "CFLAGS=-fPIC -O2 -Wno-void-pointer-to-enum-cast" -j1   # 生成 include/ API 头
make library CC=clang "CFLAGS=-fPIC -O2 -Wno-void-pointer-to-enum-cast" -j1 # 构建 libmodest.so + libmodest_static.a
make test CC=clang "CFLAGS=-fPIC -O2 -Wno-void-pointer-to-enum-cast"        # 上游测试（EXIT:0）
make install prefix=$DESTDIR                                                # 安装 lib+include+pkgconfig
```

关键点：
- **不能命令行覆盖 `MODEST_CFLAGS`**：Makefile 内 `MODEST_CFLAGS ?=` + `+=` 组合注入 `-Isource`、`-std=c99`、`-D_POSIX_C_SOURCE` 等，命令行覆盖会丢掉这些内部标志导致头文件找不到。
- **正确注入点是 `CFLAGS`**（Makefile 未自行定义）+ `MODEST_CFLAGS ?=` 保持默认 `-Wall -Werror -pipe -pedantic`。
- 构建目标顺序：`make clone`（生成 API 头到 include/）在前，否则 `#include "modest/declaration.h"` 等全局头找不到。
- 库类型（纯库），非 CLI，无需 commands.json（R38）。
- 源码 URL 为官方 GitHub commit 归档（上游 0.0.6 无 git tag/release，锁定 master HEAD 2540a03259fc62fe15f47e85c20b2eedd5af66de 即 0.0.6-devel）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-Werror,-Wvoid-pointer-to-enum-cast` 编译失败（function_parser.c:469 等） | clang 15 对 `(enum_t)(void*)` 直接转型告警，上游 `-Wall -Werror` 变错误 | `CFLAGS` 注入 `-Wno-void-pointer-to-enum-cast`（配方级，非补丁） |
| 2 | `pthread_cancel` 未声明（thread.c:55） | `pthread_cancel` 是 glibc 扩展，musl/OHOS libc 不提供 | 补丁 0001：`#ifdef __GLIBC__` 守卫，非 glibc 时返回 MyCORE_STATUS_ERROR（libc 探针，PR 说明理由） |
| 3 | `-Werror,-Wunused-but-set-variable`（punycode.c:26 cp_count） | clang 15 新告警；上游代码 cp_count 只增不读 | 补丁 0002：`(void) cp_count;` 最小抑制（保留计数逻辑） |

## 源码修改（补丁）

- `patches/0001-source-myport-posix-mycore-thread.c.patch`：thread_cancel 加 `#ifdef __GLIBC__` 守卫（portability, libc 探针）
- `patches/0002-source-myurl-punycode.c.patch`：cp_count 未使用告警抑制（portability）

## 依赖版本

无第三方依赖（README 声明 "pure C99 library with no outside dependencies"；conan-verify G0/G4 确认 0 requires）。

## 验证结果

### 上游测试台账（双口径）

**统计口径**：以 `test/` 下可独立执行的测试程序源文件（含 main 的 .c 测试入口）为源码声明单位；框架 Makefile.mk 注册的每个可执行模块为配置单位；实际运行通过数为执行单位。样例（examples/，40 个）与基准/工具脚本（utils/、devel/）不属于独立上游用例，单独列明不计数。

| # | 测试入口（源码声明） | 分类 | 是否独立用例 | 是否实例化 | 是否运行 | 结果 |
|---|---|---|---|---|---|---|
| 1 | test/mycore/utils/avl_tree.c | 用户测试源 | 是 | 是（mycore/utils） | 是 | 通过（静默退出 RC:0，断言失败会打 ERROR 退出非 0） |
| 2 | test/mycss/declaration.c | 用户测试源 | 是 | 是（mycss） | 是 | 通过（Total: 4; Good: 4; Bad: 0） |
| 3 | test/myencoding/encoding_detect_meta.c | 用户测试源 | 是 | 是（myencoding） | 是 | 通过（241 个 "Ok" 检查，全部 Ok） |
| 4 | test/myhtml/commoncrawl.c | 用户测试源 | 是 | 是（myhtml） | 是 | 通过（静默 RC:0） |
| 5 | test/myhtml/pseudo_class_contains.c | 用户测试源 | 是 | 是（myhtml） | 是 | 通过（输出 Found nodes 2 个，RC:0） |
| 6 | test/myurl/url.c | 用户测试源 | 是 | 是（myurl） | 是 | 通过（12 个 data/*.test 数据文件全部处理，RC:0） |
| 7 | test/mycore/encoding_detect_meta.c | 用户测试源 | 是 | **否（上游未实例化）** | 否 | 未运行：上游 test/mycore/Makefile.mk 仅注册 `mycore_dirs := utils`，该文件位于 test/mycore/ 根目录未被构建目标收录；与 test/myencoding/encoding_detect_meta.c 仅差一个宏名（MyCORE_FMT_Z vs MyCORE_FORMAT_Z），数据文件完全一致（sha 相同），属重复副本，不按失败计 |
| — | test/*/Makefile.mk、test/Makefile | 框架注册文件 | 否 | — | — | 框架（不计入用例） |
| — | test/*/data/（.html/.test） | fixture 数据 | 否 | — | — | fixture（mycss 2 文件、myencoding 1 文件、myurl 12 文件、mycore 1 文件） |
| — | examples/（40 个 .c）、utils/、devel/、third_party/ | 样例/基准/工具 | 否 | — | — | 非测试用例 |

**双口径统计**：
- source_declared_total = 7（源码中独立测试程序入口）
- configured_executable_total = 6（上游 Makefile.mk 实际注册可执行模块）
- executed_passed_total = 6，failed = 0
- uninstantiated = 1（#7 mycore/encoding_detect_meta.c 重复副本，上游未注册）
- 全量通过率：**6/7 (85.7%)**（未实例化计入分母不计通过）
- 当前配置可执行集合通过率：**6/6 (100%)**

**执行命令**（cwd=/storage/Users/currentUser/tmp/builds/modest-0.0.6.work）：
```bash
make test CC=clang "CFLAGS=-fPIC -O2 -Wno-void-pointer-to-enum-cast"
# EXIT:0；日志: /storage/Users/currentUser/tmp/logs/modest-upstream-test.log
# SHA-256: f0748df79311c2695a93913389584181a92f674b69d283a31a831347d9c57280
```
后续重跑 `make test` 时若 test_suite/ 已有同名二进制，HMDFS 会报 `cp: Operation not permitted`（覆写限制），属平台文件系统限制，不影响首次完整运行结果（首次 EXIT:0 为台账依据）。

### Conan 配方验证（conan-verify）

- G1 配方完整性: PASS
- G2 conan create（干净构建）: PASS（ohos-aarch64 profile，自动 ghfast.top 镜像注入后恢复原始 conandata.yml）
- G3 系统同名库隔离: PASS
- G4 产物完整性: PASS
- L2/L4/L5: 完成

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | GNU Make 驱动配方（clone + library + install prefix=pkg） |
| conandata.yml | 官方源码 URL + sha256 7f3e5455f0630cb17632bc07eb6de68235636d435032362081da6d083f51e6a8 |
| patches/0001-*.patch | pthread_cancel glibc 守卫 |
| patches/0002-*.patch | punycode cp_count 告警抑制 |
| test_package/ | 配方测试（消费者验证） |
| lib/libmodest-0.0.6.so + libmodest_static.a | arm64 OHOS 库产物 |

## 知识候选台账 + 七轴查重 + 路径决定（knowledge_candidate_ledger）

### 候选 1（非噪声）：OHOS(musl) libc 不提供 pthread_cancel → 源码级正向 libc 探针守卫
- 真实错误：`source/myport/posix/mycore/thread.c:55:8: error: call to undeclared function 'pthread_cancel'`（clang -c，首个编译错误）
- 根因：`pthread_cancel` 是 glibc 扩展，OHOS musl libc 不声明该函数（sysroot pthread.h 无 pthread_cancel/pthread_setcanceltype）
- 修复：补丁 0001 —— `#ifdef __GLIBC__` 正向探针守卫（glibc 下走 pthread_cancel；非 glibc 返回 MyCORE_STATUS_ERROR），不使用 `__OHOS__` 平台宏
- 验证：make library 全绿；make test 6/6 通过；conan create 消费者 1/1
- 适用范围：任何"裸 Makefile C 库 + POSIX 线程取消调用"在 OHOS/musl 的适配；正向 libc 探针（__GLIBC__）优于平台宏（与 E407 forbid __OHOS__ 方向一致）

### 候选 2（非噪声）：clang 15 新增告警类别在 -Werror 下变错误
- 真实错误 2a：`-Werror,-Wvoid-pointer-to-enum-cast`（function_parser.c:469 等，`(enum_t)(void*)` 直接转型）
- 真实错误 2b：`-Werror,-Wunused-but-set-variable`（punycode.c:26 cp_count 只增不读）
- 根因：上游 `-Wall -Werror -pedantic`，clang 15 对 void*→enum 直转与 unused-but-set 的新告警被升级为错误
- 修复：CFLAGS 注入 `-Wno-void-pointer-to-enum-cast`（配方级，非源码补丁）+ 补丁 0002 `(void) cp_count;`
- 验证：make library / make test 全绿
- 适用范围：所有启 -Werror 的 C/C++ 库在 clang15 工具链的适配（E063 同族，新增两个具体告警签名）

### 候选 3（非噪声）：裸 Makefile 内部 flag 变量通道判别（MODEST_CFLAGS ?= + +=）
- 真实错误：命令行覆盖 `MODEST_CFLAGS="-Wall -Werror -Wno-void-pointer-to-enum-cast"` 后编译丢失 `-Isource`、`-std=c99`、`-D_POSIX_C_SOURCE`，报 `'modest/declaration.h' file not found`
- 根因：Makefile 内 `MODEST_CFLAGS ?= -Wall -Werror -pipe -pedantic` 后再 `+=` 注入内部标志；make 命令行变量赋值是整串接管，`+=` 失效
- 修复：配方 build() 走 make 命令行未赋值的 `CFLAGS`（Makefile 未自行赋值）注入告警抑制；`MODEST_CFLAGS` 保持 `?=` 默认值
- 验证：make library 全绿
- 适用范围：所有"Makefile `VAR ?=` + `VAR +=` 组合内部 flag"的手写 Make 构建库在 Conan 配方中的注入通道选择（与 DRAFT-11940 同机制）

### 四范围查重结果
| 范围 | 候选 1 | 候选 2 | 候选 3 |
|------|--------|--------|--------|
| 正式知识 (graph/E*.kv) | E085（undefined ref）、E127（undeclared）、E407（AC_CHECK_FUNCS 探针、forbid __OHOS__）、E513（joinable 线程生命周期） | E063（add-cflags-disable-werror 族） | 无（机制类条目在草稿层） |
| 图谱 index.tsv | pthread_cancel 行：E085/E127/E407/E513 | -Werror 族多条目 | 无直接条目 |
| drafts/ | DRAFT-20003（硬取消分支编译必炸+软取消挂起）、DRAFT-E680（NDK 无三函数）、DRAFT-aml（meson feature-detect）、DRAFT-eigen（threadpool boundary） | 无 | DRAFT-11940-wmcube（makefile-unassigned-flag-channel，机制与解法完全一致） |
| doc/ | E085/E127/E407/E513 配套 doc | E063.md | — |

### 七轴查重
| 轴 | 候选 1 | 候选 2 | 候选 3 |
|----|--------|--------|--------|
| exact_duplicate | 否（E127 是 undeclared 家族，无本库源码守卫实例） | 否 | 否 |
| causal_duplicate | 是（根因=musl 无 pthread_cancel，与 E085/E127/E407/E513 同根） | 是（根因=-Werror 升级告警，与 E063 同根） | 是（根因=命令行变量整串接管，与 DRAFT-11940 同根） |
| trigger_overlap | 是（undeclared，同 E127/E407 触发面） | 是（-Werror 编译期，同 E063 触发面；新增两个具体签名） | 是（make 编译期 flag 注入，同 DRAFT-11940） |
| solution_overlap | 是（正向 libc 探针 = E407 推荐方向；E513 生命周期补充） | 是（CFLAGS 注入 -Wno-* = E063 同款方案） | 是（未赋值变量通道注入 = DRAFT-11940 唯一推荐） |
| combination_novelty | 低：单库实例，组合已被 E127+E407 覆盖 | 低：E063 覆盖方案，仅新增签名数据点 | 低：DRAFT-11940 已完整覆盖机制 |
| boundary_novelty | 低（无新边界：仍是 musl 无取消 API 场景） | 低 | 低（DRAFT-11940 已含"已被赋值变量只能命令行整串接管"边界） |
| test_migration_novelty | 无 | 无 | 无 |

### 关系字段
- 候选 1：similar_to E127 / E407；caused_by （musl libc 能力缺口，已有 E085 归因）；prerequisite_of E513（若需 joinable 线程善后）；conflicts_with 无
- 候选 2：similar_to E063；caused_by 无（上游 -Werror 默认）；prerequisite_of 无；conflicts_with 无
- 候选 3：similar_to DRAFT-11940；caused_by 无；prerequisite_of 无；conflicts_with 无

### 路径决定：**reuse_existing（路径 A）**
- 依据：三项候选全部命中既有知识——候选 1 由 E127（undeclared）+ E407（正向探针方向 + forbid __OHOS__）+ E513（生命周期）覆盖；候选 2 由 E063（-Werror 家族 + CFLAGS 注入方案）覆盖；候选 3 由 DRAFT-11940（Makefile 变量通道判别，机制与解法完全一致）覆盖。无任何"已验证、可跨库复用且查重未命中/部分覆盖并存在新增差异"的候选，路径 B 必要条件不成立。
- 结论：reuse_existing=true；new_draft=false；path_a_no_knowledge=false（知识已存在，按既有条目复用，不建新草稿）。
- 本库仍按任务头声明的 task_type=知识库扩展 与 initial_pr_prefix=【知识库扩展】 交付（不新建 .md/.kv 草稿对）。

## 注意事项

- Makefile install 只装 lib + include + pkgconfig（无 bin/ → 非 CLI，R38 无 commands.json）。
- `make clean` 会清掉 test_suite/；重跑 make test 前若 test_suite/ 残留则需先手工删除目录（HMDFS cp 覆写限制）。
---

**编译结束**: 2026-10-04 19:52
**最终状态**: built
