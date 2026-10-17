# trzsz 1.1.5 — OHOS H1 测试报告

日期2026-10-04；orrkri任务11309；唯一H1请求 trzsz001r1。精确来源、依赖、配方/补丁/测试与原始制品摘要见 h1-binding.json 和 notes.md。

| 测试类别 | 用例数 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| 未修改原 libs unit | 7 | 7 | 0 | 0 |
| 未修改原 svr unit | 12 | 12 | 0 | 0 |
| 新增协议回归（含两项实际CLI） | 7 | 7 | 0 | 0 |
| 新增包消费者 | 1 | 1 | 0 | 0 |
| **合计** | **27** | **27** | **0** | **0** |

原测试入口 `python -m unittest discover trzsz-libs` / `python -m unittest discover trzsz-svr`，由 upstream_tests.py 在包内完整 patched source 中执行，真实 symlink 保留；原断言未改。新增消费者核包来源、真实三发行元数据、Python prefix/版本/termios和入口；两次--help不额外计消费者。回归见 test_package/progress_regression.py 和 MANIFEST.yml。

原版相同回归另7/7，表示有限缺陷取证及正常对照，不加入修后统计。Conan verify 与自动 W3 两次必要执行均完整无跳过，不重复累计用例。

完整自动 W3 exit=0；原日志 w3-local-ci.log SHA256 `3edc78d1ac81ebb268ae882816a103728224c21193fddf86ec7bb9ab4a26ab6b`。Conan create 原日志见 conan-create.log。package transfer.py SHA256 `1c3e5318de04c58446fcb0fa80dfcaa882b39a5fd2e78d79feeedb7a35914184`。H1的完整 finish 仍自然rc1，失败阶段与工具跳过见notes；未发布包，不是官方PR CI、W4、AtomCode或有效提审回执。
