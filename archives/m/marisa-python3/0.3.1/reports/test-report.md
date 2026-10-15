# 原生测试报告

设备：10.62.201.39:2222，aarch64 HarmonyOS PC，Clang 15。
事务：`marisa-python3-w3-r2-20261013`，冻结校验器 W3_PASS，12 阶段完整。

| 范围 | 结果 |
| --- | --- |
| 正式 Conan create | RC 0 |
| 原始 C++ CTest 测试组（base/io/vector/trie/marisa） | 5/5，100% |
| 完整原始 Python 3 sample.py | 1/1；额外示例，不混入 CTest 分母 |
| 安装后 Python 扩展 API 消费者 | 8/8，100% |
| 任务进程清零及 release/postrelease | PASS |

日志 SHA-256：`84bb95a95c0110be1e7a42d4bc719b42f83d59f38132012657fed5f4302a777c`。
模块命名清单摘要：`1a080d52b97521ced95880c209741abaade598fbf778e45c4376d448f9f1bae7`。

消费者包含四键构建、lookup、缺失键、reverse lookup、日文 Unicode、common prefix、
save/load、mmap/predictive，且 `marisa` 与 `_marisa` 的文件来源必须属于被测包。
原始测试断言和案例不修改、不减少。OOM 容错路径未进行真机内存耗尽注入；不宣称覆盖该异常路径。
尚无比赛 worker CI、平台 AI Review 或正式发布证据。
