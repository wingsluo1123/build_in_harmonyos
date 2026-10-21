# isbnlib 3.10.14 验证摘要

HarmonyOS PC AArch64 / Python 3.12.9 / OHOS Conan 2.29.1，2026-10-16。

| 范围 | 收集/执行 | 结果 |
| --- | --- | --- |
| 官方完整上游 | 73/73 | 56通过、16失败、1 setup错误，0跳过；通过率76.71% |
| 默认Conan非网络 | 73收集、55执行 | 55通过、18 network deselected；零跳过 |
| 安装消费者 | 15/15 | 全部通过，包括插件发现与关闭开关、独立进程书目、spawn正常/异常任务 |
| 负向 | 2受控副本 | 缺包与缺_data均退出1，恢复安装路径后15/15 |
| W3原CI | 1包 | L0/L1/L1e/L4/L5通过；L2无CLI跳过 |

未通过的17项均为上游network标记。原日志保留超时、拒绝连接、HTTP403/405，以及3项版本返回数量断言失败；不能把这些断言失败均归因于鸿蒙平台或简单改小分母。仅1项network测试通过。在线元数据/书目重命名的端到端服务可用性未获完整验证，不声称全量100%。

当前四个补丁来自仓库原版refresh-patch --auto，逐文件应用于官方标签；最终全量所测runtime模块逐字节与安装payload的39个模块一致。上游测试只改test_files.py和test_rename.py的独立临时目录与cwd恢复，没有改变断言。默认排除network是显式可选策略，`-o isbnlib/*:network_tests=True`执行全量。未启用coverage仪表，不声明覆盖率。

真实W3由finish流程自动生成回执。该设备原缺Git/Bash，任务缓存下载已发布工具包并设置TMPDIR与进程级精确safe.directory后执行。finish整体仍有legacy packaging/.staging检查与全库空草稿遥测提示，故原始finish进程exit1；这不改变其中W3真实exit0，也不宣称完整finish无警告。未伪造旧包装归档来满足历史检查。

原始日志、回执和JUnit保留在本地交付目录，不提交PR。完整SHA256、逐项结果及模块来源见validation-evidence.json。早期两份W3备份同名被重跑覆盖，已重标为intermediate-success；环境失败只保留工具展示片段并明确不是完整原始字节。其他W0、RED、Conan失败和最终证据未受影响。

知识预审为review-similar，E339=0.43，需官方人工判定；E429为候选号。PR远端CI、审核、合并、发布、知识入库及积分分别核验。纯Python库路径B资格与10分候选须官方确认。
