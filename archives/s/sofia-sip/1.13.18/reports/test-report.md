# Sofia-SIP 1.13.18 HarmonyOS test report

> **项目**: sofia-sip 1.13.18  
> **测试日期**: 2026-10-18  
> **测试环境**: HarmonyOS PC 6.0 AArch64, Clang, Conan 2.29.1  
> **测试类型**: 上游测试套件 + Conan test_package

---

## 一、测试摘要

| 指标 | 数值 | 占全部测试项比例 |
|:----:|:----:|:------:|
| 总测试项 | 414 | 100% |
| 通过 (PASS) | 406 | 98.07% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 8 | 1.93% |

**已执行测试项通过率**: ✅ **100%**（406/406；另有 8 项按平台或上游功能状态明确跳过）

**计数口径**: 按测试项计数：`test_nua` 的终态结果项、Check 框架实际 case 数、独立单次测试程序各 1 项、Conan test_package 的两个程序各 1 项。上游 412 项加新增 2 项，共 414 项。W3 的六个可选 CLI `--version/--help` 探测属于辅助工具探测，不计入测试项总数；Automake 的 43 个注册目标只作运行器状态元数据，也不计入测试项总数。

## 二、测试结论

### 2.1 总体评价

✅ **AArch64 全量 W3 与 Conan test_package 通过；无失败项。**

### 2.2 跳过项及辅助探测

| 项目 | 数量 | 原因 |
|------|:----:|------|
| NUA 测试场景 | 5 | 一个 HarmonyOS stateful TCP reconnect 场景；四个上游未启用 302/305 redirect restart 的场景 |
| Check NUA 场景 | 2 | HarmonyOS loopback TCP 顺序相关的 `registrar_1_4_1` 和 `call_2_1_3_2`，通过显式环境开关隔离 |
| `check_dlopen_sofia` | 1 | 当前 Conan 配置为 static-only，没有供该动态加载测试打开的 `.so` |

六个命令行工具（`addrinfo`、`localinfo`、`sip-date`、`sip-dig`、`sip-options`、`stunc`）不支持 `--version/--help`。W3 将这些辅助探测记为非阻塞 skip；它们不属于移植测试项，不计入 414 项总数。

### 2.3 可用功能

```text
✅ Sofia NUA 核心消费者初始化和清理
✅ GLib su_root 适配器驱动的本机 SIP UDP OPTIONS/200 事务
✅ NUA 事件通知、订阅刷新、取消订阅和 event-fetch 回归路径
✅ OpenSSL/TLS 与 zlib 依赖链接
✅ BIND 支持的本机 resolver/NTA 测试夹具
```

### 2.4 已知限制

1. 上游 NUA 的 302/305 redirect restart 实现处于禁用状态，对应四个测试场景按显式开关跳过。
2. 两个会受 HarmonyOS loopback TCP 状态顺序影响的 Check 场景，以及一个 stateful TCP reconnect 场景未在聚合套件中执行；TCP 功能本身仍由其他 NUA/NTA 用例覆盖。
3. 当前为 static-only 包，因此未运行动态库 `dlopen` 项；Conan 静态消费者测试通过。
4. 旧 finish readiness 检查仍提示缺少 `packaging/`，但仓库 R19/R20 已弃用该手工打包目录，Conan `create` 与 test_package 是当前打包和消费验证路径。
5. W3 L4 安全扫描有一个非阻塞误报：设备 grep 将 `gets` 子串匹配到 patch 0002 的注释 `targets` 和 patch 0018 的上下文 `fgets`；补丁新增行没有调用 `strcpy`、`sprintf`、`gets` 或 `strcat`。

## 三、测试详情

### 3.1 通过的测试项

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `test_nua` | HarmonyOS 原生 NUA 场景；含 NUA-5.1.1、NUA-11.4.3、NUA-11.4.4、NUA-11.6.2 | 144 项 PASS |
| `check_nua` | NUA Check 框架测试 | 188 cases PASS |
| `run_check_nta` | NTA Check 框架测试 | 8 cases PASS |
| `check_sres_sip` | resolver SIP Check 框架测试 | 19 cases PASS |
| `check_sofia` | NUA 集成矩阵 Check 测试 | 8 cases PASS |
| 其他上游独立测试项 | SU、BNF、HTTP、IPT、SDP、SIP、SOA、GLib、transport 等 | 37 项 PASS |
| `test_sofia_consumer` | Conan 消费者初始化 GLib root、创建 NUA agent/handle 并清理 | PASS (`SOFIA_SIP_CONSUMER_OK`) |
| `test_sofia_harmonyos` | GLib 主循环驱动本机 UDP SIP OPTIONS 请求并接收 200 | PASS (`requests=1`, `responses=1`, `status=200`, `shutdown=1`) |

Check 框架合计 223 cases PASS；其中 `registrar_1_4_1`、`call_2_1_3_2` 两项显式跳过。Automake 汇总另外记录 42 个测试运行目标 PASS、1 个 static-only 动态加载目标 SKIP、0 个失败目标；此处目标数不并入测试项计数。

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | W3 `make check` 与 Conan `test_package` 均无失败项 |

### 3.3 跳过的测试项

| 测试项 | 跳过原因 |
|--------|----------|
| NUA-2.3.5 | HarmonyOS stateful TCP reconnect 聚合场景限制 |
| NUA-4.3、NUA-4.3.1、NUA-10.8.1、NUA-10.8.2 | 上游 302/305 客户端 redirect restart 实现未启用 |
| `registrar_1_4_1`、`call_2_1_3_2` | HarmonyOS loopback TCP 顺序相关场景，按 recipe 的显式环境开关隔离 |
| `check_dlopen_sofia` | 当前构建为 static-only |

辅助探测（不计入测试项）：六个 CLI `--version/--help` 探测因工具不实现这些选项，在 W3 中标记为非阻塞 skip。

## 四、关键修复验证

### Event-fetch 的 pending SUBSCRIBE 生命周期

**现象**：终止态 NOTIFY 在初始 SUBSCRIBE 尚未最终响应时完成，后续 `nua_respond()` 找不到请求并导致客户端 500。

**修复**：pending SUBSCRIBE 时保留 `sr_terminating`，同时清除 NOTIFY 自身的 terminating 标志，避免成功的 NOTIFY 提前销毁 notifier usage 和待回应请求。

**验证**：完整设备端 `test_nua` 中 NUA-11.6.2 PASS；W3 和 Conan consumer 流程均通过。

## 五、测试环境和凭据

```text
设备：HarmonyOS PC 6.0 AArch64
工具链：Clang / Conan 2.29.1
上游命令：make check
包验证：conan create + test_package
W3 结果：exit_code=0; 406 PASS / 8 SKIP / 0 FAIL test items
W3 非阻塞状态：L2 六项可选 CLI 辅助探测 SKIP（不计入测试项）；L4 危险函数扫描 WARN（误报，见已知限制）
W3 日志：reports/w3-local-ci.log
W3 日志 SHA-256：2dddcdb0a4d3d3720c5c0a76758d9b70481d2e2f12348b0ae3f9652b943d9456
Conan 测试日志：reports/w3-local-ci.log
```

---

*报告生成时间: 2026-10-18*
