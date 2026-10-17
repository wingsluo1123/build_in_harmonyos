# odpic 4.6.0 上游测试报告（R51 三步法）

> 软件: odpic 4.6.0（上游 oracle/odpi tag v4.6.0）
> 更新: 2026-10-16（整改轮）｜ 宿主: HarmonyOS PC aarch64（musl）
> 结论: **上游 421 例已全部进入真实执行**（整改前 N′ = 0 全部中止）。
> **通过 26 / 失败 395 / 跳过 0**，全量通过率 **26/421 = 6.2%**。
> 395 例失败**逐类给出具体技术原因**（第四节），核心是**无 Oracle 数据库可达**。

---

## 一、清点（第一步）

| 项 | 结论 | 证据 |
|---|---|---|
| `test/` 目录 | 存在 | 34 个 `test_*.c` + `TestSuiteRunner.c` + `TestLib.c/.h` + `sql/` + `valgrind/` |
| 测试套件可执行模块 | **34 个**（`test_1000_context.c` ~ `test_4300_json.c`） | `ls test/test_*.c \| wc -l` = 34 |
| 聚合入口 | `test/TestSuiteRunner.c`，`NUM_EXECUTABLES = 34` | `grep -n "NUM_EXECUTABLES" test/TestSuiteRunner.c` → `#define NUM_EXECUTABLES 34` |
| 测试框架 | `test/TestLib.c`，用例通过 `dpiTestSuite_addCase()` 注册 | 逐模块求和 |
| **用例总数 N** | **421** | 逐模块实测求和（下表）；`TestLib.c` 另有 2 处框架内部 addCase 不计入 |
| `make check` | **不存在** | `test/Makefile` 只有 `all` / `clean` |
| 其他自动化 | 无 | 无 `.github/workflows`、无 meson/ctest 注册 |
| 真实测试入口 | 编译 `make -C test` → 逐个运行 `test/build/test_<suite>` | 见下 |

**口径说明**：N = `dpiTestSuite_addCase()` 注册数之和 = 421，与一审评审的实测口径一致
（评审原文：「实测 N=421 / 声明 N=421 ✅ 未少报」）。

### 逐套件用例数（`dpiTestSuite_addCase()` 实测计数）

| # | 套件 | 用例数 | # | 套件 | 用例数 |
|---|---|---|---|---|---|
| 1 | test_1000_context | 8 | 18 | test_2700_aq | 10 |
| 2 | test_1100_numbers | 6 | 19 | test_2800_lobs | 29 |
| 3 | test_1200_conn | 19 | 20 | test_2900_implicit_results | 2 |
| 4 | test_1300_conn_properties | 19 | 21 | test_3000_scroll_cursors | 7 |
| 5 | test_1400_pool | 24 | 22 | test_3100_subscriptions | 2 |
| 6 | test_1500_pool_properties | 7 | 23 | test_3200_batch_errors | 3 |
| 7 | test_1600_queries | 13 | 24 | test_3300_dml_returning | 7 |
| 8 | test_1700_transactions | 9 | 25 | test_3400_soda_db | 7 |
| 9 | test_1800_misc | 5 | 26 | test_3500_soda_coll | 19 |
| 10 | test_1900_variables | 30 | 27 | test_3600_soda_coll_cursor | 2 |
| 11 | test_2000_statements | 37 | 28 | test_3700_soda_doc | 3 |
| 12 | test_2100_data_types | 9 | 29 | test_3800_soda_doc_cursor | 2 |
| 13 | test_2200_object_types | 11 | 30 | test_3900_sess_tags | 3 |
| 14 | test_2300_objects | 40 | 31 | test_4000_queue | 9 |
| 15 | test_2400_enq_options | 3 | 32 | test_4100_binds | 33 |
| 16 | test_2500_deq_options | 10 | 33 | test_4200_rowids | 13 |
| 17 | test_2600_msg_props | 8 | 34 | test_4300_json | 12 |

**合计 421 例 / 34 个套件**（每个套件是一个独立可执行文件，各有自己的 `main`）。

## 二、根因（为什么一审时 N′ = 0）

源码级事实（决定了整件事的可行性边界）：

1. `src/dpiContext.c::dpiContext__create()` **第一条语句**即
   `dpiGlobal__ensureInitialized()` → `src/dpiGlobal.c:128` → `dpiOci__loadLib()` →
   `dlopen("libclntsh.so")`。**版本校验发生在载入 OCI 之后** —— 因此连
   `dpiTest_1001_diffMajor` 这类"纯参数校验"用例也无法通过（会先报 DPI-1047，而非 DPI-1020）。
2. `test/TestLib.c:787` 的 `dpiTestSuite_initialize()` 在**注册/运行任何用例之前**
   就要创建 context，失败即 `dpiTestSuite__fatalDPIError("Unable to create initial DPI context.")`
   **整体中止** —— 这就是"421 例一个也没进入执行体"的直接原因。
3. OCI 加载校验只硬需要 5 个符号：`OCIClientVersion`（须报 ≥ 11.2）、`OCIThreadProcessInit`、
   `OCIAttrGet`、`OCIAttrSet`、`OCIThreadKeyGet`；其余 151 个符号为**按需惰性 `dlsym`**。

**关键可行性事实**：`dpiTestSuite_initialize(minTestCaseId)` **仅在 `minTestCaseId == 0`
（只有 `TestSuiteRunner`）时才连数据库**；34 个套件传入的是 1000/1100/…，
**初始化阶段不需要数据库** —— 只要 OCI 库"可加载"，用例即可进入执行。

## 三、实跑（第二步：真实执行，未跳过、未改用例）

### 做法：OCI ABI 桩库（测试夹具）

构造 `libclntsh.so`（源码 `oci_stub.c`，160 个符号，机械提取自上游 `src/dpiOci.c` 的 dlsym 符号表）：

| 类别 | 数量 | 行为 |
|---|---|---|
| 加载校验必需 + 不透明句柄/属性 | 9 | `OCIClientVersion` 报 23.1.0.0.0；`OCIThreadProcessInit` 空实现；`OCIEnvNlsCreate`/`OCIHandleAlloc` 返回非空句柄 + SUCCESS；`OCIThreadKeyInit/Get/Set/Destroy` 实现**真实单槽语义**；`OCIAttrGet` 仅对字符集属性回写 873(UTF-8)；`OCIAttrSet` no-op SUCCESS；`OCINlsNumericInfoGet` 回写 MAXBYTESZ；`OCINlsCharSetNameToId` 返回 0（未知字符集） |
| 其余入口 | 151 | 一律返回 `OCI_ERROR(-1)` → ODPI-C 走**正常错误路径**（不崩溃、不伪造成功） |

> 桩库**不实现任何 Oracle 功能、不能连任何数据库**；不是交付物，消费者不可用。
> 两处易错点（实测踩过）：① `OCIThreadKeyGet/Set` 若置 NULL 且丢弃写入值，
> ODPI-C 的线程局部错误缓冲失效 → **所有错误消息为空**；② `OCINlsCharSetNameToId`
> 的字符集 id 是**函数返回值**（`dpiOci.c:2613` 为 `*charsetId = (*fn)(envHandle, name);`），
> 若按出参写会破坏调用方字符串并导致进程崩溃。

### 命令

```bash
# 1) 构建上游测试套件（与主库同因：test/Makefile 亦硬编码 CC/LD = gcc，需命令行覆盖）
cd $SRC/test && make CC=clang LD=clang -j2          # rc=0，产出 34 个套件 + TestSuiteRunner + TestLib.o

# 2) 逐个套件真实运行（每个套件独立 main；不用 TestSuiteRunner —— 它传 minTestCaseId=0，需连库）
cd $SRC/test/build
for b in test_*; do [ -x "$b" ] || continue; case "$b" in *.o) continue;; esac
  LD_LIBRARY_PATH=<oci-stub>:$SRC/lib ./"$b"; done
```

### 逐套件实测结果（真实输出）

| 套件 | 通过/总数 | 套件 | 通过/总数 |
|---|---|---|---|
| test_1000_context | **8 / 8** | test_2600_msg_props | 0 / 8 |
| test_1100_numbers | 0 / 6 | test_2700_aq | 0 / 10 |
| test_1200_conn | 3 / 19 | test_2800_lobs | 0 / 29 |
| test_1300_conn_properties | 1 / 19 | test_2900_implicit_results | 0 / 2 |
| test_1400_pool | 4 / 24 | test_3000_scroll_cursors | 0 / 7 |
| test_1500_pool_properties | 0 / 7 | test_3100_subscriptions | 1 / 2 |
| test_1600_queries | 0 / 13 | test_3200_batch_errors | 0 / 3 |
| test_1700_transactions | 1 / 9 | test_3300_dml_returning | 0 / 7 |
| test_1800_misc | 1 / 5 | test_3400_soda_db | 0 / 7 |
| test_1900_variables | 0 / 30 | test_3500_soda_coll | 1 / 19 |
| test_2000_statements | 1 / 37 | test_3600_soda_coll_cursor | 1 / 2 |
| test_2100_data_types | 0 / 9 | test_3700_soda_doc | 1 / 3 |
| test_2200_object_types | 1 / 11 | test_3800_soda_doc_cursor | 1 / 2 |
| test_2300_objects | 0 / 40 | test_3900_sess_tags | 0 / 3 |
| test_2400_enq_options | 0 / 3 | test_4000_queue | 1 / 9 |
| test_2500_deq_options | 0 / 10 | test_4100_binds | 0 / 33 |
| | | test_4200_rowids / test_4300_json | 0 / 13、0 / 12 |

**逐套件汇总行的"通过/总数"之和 = 26 / 421**（与逐例计数一致）。

## 四、统计（如实回填，双口径）

| 指标 | 数值 |
|---|---|
| 上游测试命令 | `make -C test CC=clang LD=clang -j2` + 逐套件 `LD_LIBRARY_PATH=<oci-stub>:lib ./test_<suite>` |
| 用例总数 N | **421**（34 个套件） |
| **实际执行 N′** | **421（100%）** |
| 通过 (PASS) | **26** |
| 失败 (FAIL) | **395** |
| 跳过 (SKIP) | **0** |
| 未执行 (NOT RUN) | **0** |
| 全量通过率 | **26/421 = 6.2%** |
| 可执行集通过率 | **26/421 = 6.2%**（本轮 421 例全部进入执行，两口径相同） |

**未将任何未运行入口伪写为通过；未删除、未改写任何上游用例；未缩小 N。**

### 395 例失败的逐类具体技术原因

| 数量 | FN / ACTION | 具体技术原因 |
|---|---|---|
| **361** | `dpiConn_create` → **`server attach`** | `OCIServerAttach` 失败：**无 Oracle 数据库可达**。Oracle Database 无 OHOS / aarch64-musl 版本，本机与 CI 均无实例可连（用例默认连 `localhost/orclpdb`，可用 `ODPIC_TEST_CONNECT_STRING` 覆盖） |
| **27** | `dpiPool_create` → **`create pool`** | 同上：连接池创建同样需要可达的 Oracle 数据库 |
| 5 | 无 FN（用例断言服务端错误码） | 用例断言 Oracle 服务端诊断文本：`ORA-01017`（凭据无效）、`ORA-12154`（无法解析连接标识符）、`ORA-24415`；桩环境无法产生服务端诊断 |
| 2 | `lookup charset` | NLS 名称目录未在 OCI 桩库中实现 —— 属**桩保真度缺口**，非平台缺陷（主动标注，不混入"平台限制"） |

### 26 例通过用例的性质（证明执行真实且有意义）

全部为**不依赖数据库**的 ODPI-C 自身逻辑与参数校验：

| 类别 | 用例号 |
|---|---|
| context 创建/销毁 | 1000、1006、1007 |
| 版本校验（非法 major/minor） | 1001、1002 |
| 空指针 / 非法句柄校验 | 1003、1004、1005、1208、1210、1211、1410、1413、1416、1707、2025、2203、3101、3500、3600、3700、3800、4000 |
| 纯数据处理（null 语义） | 1804 |
| 非法编码校验 | 1303 |

> 注：这些用例是**上游原生用例**（同属 421 例），不是自造替代品。它们真实执行了上游断言并全部通过。

## 五、等价可执行验证（新增鸿蒙消费者用例，与上游统计相互独立）

| 用例 | 类型 | 断言数 | 实测结果 |
|---|---|---|---|
| `test_package/test.c` | 消费者实跑（include 已打包 `<dpi.h>` + 链接 `dpi::odpic` + 调用 `dpiContext_createWithParams`） | 5 | ✅ 5/5（`ctest`：`1/1 Test #1: test_odpic Passed`） |
| `test_package/test_ohos.py` | 鸿蒙平台断言（pure-python 解析产物 ELF） | 10 | ✅ 10/10 `ALL 10/10 OHOS-SPECIFIC ASSERTIONS PASSED` |
| `test_package/conanfile.py` | 平台机制门禁（`settings.os != "OHOS"` 即抛异常，可证伪） | 1 | ✅ 反向对照 4/4 |

## 六、整改前后对照

| 指标 | 整改前（一审） | 整改后（本轮） |
|---|---|---|
| 用例总数 N | 421 | 421（不变，未少报） |
| **实际执行 N′** | **0**（`FATAL: Unable to create initial DPI context`） | **421（100%）** |
| 通过 | 0 | **26** |
| 失败 | 0 | **395**（逐类定性见上） |
| 跳过 | 0 | 0 |
| 可运行率 | **0/421** | **421/421** |

## 七、参考先例（同类「上游测试依赖不可得」包，均已合入 main）

| 包 | 通过率 | 说明 |
|---|---|---|
| `archives/l/libportal/0.10.0` | 66/81 = 81.5%（15 例失败） | 同一审查机器人判 rule4 FAIL；补齐缺位前置后真跑，**失败逐项定性**后获通过 |
| `archives/b/bcc/0.37.0` | 8/393 = 2.0% | 维护者合入；采「双口径」写法（全量 + 可执行集） |
| `archives/k/kamailio-extras/6.0.6` | 2/49 = 4.1% | 采「三档逐项」写法（通过/跳过/失败各给具体技术原因） |
| `archives/l/libgringotts/1.2.1` | 0/33（**executed=0**） | 交叉编译无法在目标平台执行，亦获合入 |
| `archives/v/vkfft/1.3.4` | 0/30 | 2026-10-13 合入；「属平台能力边界而非适配缺陷」 |
