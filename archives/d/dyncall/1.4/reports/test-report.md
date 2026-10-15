# dyncall 1.4 真机验证报告

环境：`10.62.210.132:2222`，HarmonyOS PC，小端 aarch64；Clang 15.0.4、CMake 4.1.2、Python 3.12.9、Conan 2.29.1。设备 boot `2488bc3f-f5fe-4b70-b131-07c630c7157b`，UID `20020084`。

正式共享 Conan W3：`dyncall-official-w3-20261013-r2`；完整上游 5,010/5,010，失败 0，跳过 0；19/19 上游程序。9 个生成/参数化套件保留连续编号，另 10 个程序各计一个复合用例，不将消费者混入上游分母。

| 上游程序 | 计数 |
|---|---:|
| suite2 | 16 |
| suite3 | 341 |
| suite_floats | 2047 |
| ellipsis | 85 |
| call_suite | 400 |
| call_suite_aggrs | 400 |
| callback_suite | 800 |
| callback_suite_aggrs | 400 |
| suite | 511 |
| plain_c++, callback_plain_c++, plain, callf, nm, dynload_plain, resolve_self, test_thunk, malloc_wx, callback_plain | 10 |
| 合计 | 5010 |

新增包外消费者计 1 个复合用例、15 项断言，覆盖普通聚合体、小/大返回、HFA 四个返回寄存器、GPR/FP 整体栈溢出、回调 x8 与返回 marshalling、VM 错误状态和真实 dynload 符号查询。ELF 在执行前签名，callback 分配保持 RX；原始 thunk 测试仍要求 heap/stack NX 违规触发 SIGSEGV。

正式原工具生成 `.ci-result.json`，不是人工编造。CI L0、L1、L5 通过；L1e 移走包库与头文件后确认消费者失败；L2 因纯库无 bin/ 不适用；L4 对 symbol-export CMake 补丁给出 generic warning，不是失败，也不解释为本地 AI 检视结果。

- 测试输入 candidate SHA-256：`6202578a61a4b49460c18afc4a24c55289ca4d64699ee9d135f6f30ab149aa5a`。
- 测试 tree：`bf9aa3d131ab0e8e453444bc5ade7c70e97a9eb5`；base HEAD：`f6a25613daaf1aec7170321c249d6ccf3f329593`。
- 原始日志 SHA-256：`65532ea12ef76b1acc6b6a9c5ef59ec6ab7a3a5f4488aaabdda81f4e6043f4c3`。
- 包引用：`dyncall/1.4#3cb50e3509d228296d9a36e7ba9f8bcb:0726937e17000c634ad5fc029642008575bda6b0#dca1e4b3de03d1c707bb8e3a0622bc7a`。
- 事务唯一 launch，12/12 回执，runner 与任务子进程释放后不存在。

本报告不代表已提交 PR、平台 worker CI 成功、赛事 C 类审核通过或制品发布。静态包正式验证另行记录，不挪用共享包证据。

## 后续独立正式验证

- 静态 W3 r3：完整 5,010/5,010 上游用例和消费者 15 项断言通过，12 回执及 release/postrelease 通过。日志 SHA-256 `a3c4be42e1fe882f8b3b72ffd7baa6243f9e1cba137093cc2cadcd5116f88786`。
- 当前共享 W3 r4：测试驱动增加明确 N/N 输出行用于提交合同识别，重新完整执行并通过 5,010/5,010、消费者 1/1/15 assertions、L1e 和全部事务回执。日志 SHA-256 `5e5c6b6ceb50105ab40a30155400d1db7e71f336600f8a439225ca1954ec1272`；输入 candidate `d492ae40cfee55e4cae71116eebaecee60ca2b284c08160c1d1c6e8ffeb99b23`；tested tree `867d9801b0ed54cda852768e050edafe29136f74`。
- r4 包引用 `dyncall/1.4#852bc5e34a41690985ea1aab44733906:0726937e17000c634ad5fc029642008575bda6b0#dca1e4b3de03d1c707bb8e3a0622bc7a`。
- r3/r4 ABI 源码和 20 个补丁不变，测试驱动仅新增输出行；每个 run 的 PASS 独立验证，原失败记录不覆盖。
