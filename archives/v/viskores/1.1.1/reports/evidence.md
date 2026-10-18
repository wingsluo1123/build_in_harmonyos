# 原始证据与精简范围

本轮只精简提交组织，7个已验证的配方/补丁/测试输入逐字节不变；没有重跑或增加成功次数。
原始完整证据位于已公开提交 `e65190186b41e1b21e069649144a1078d8eb3208`，本分支通过普通追加提交保留其祖先关系。
当前PR净差异保留代码、论证、摘要和索引，原始XML/日志不再作为当前新增文件重复审查。

[完整证据目录](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports)；逐文件长度及SHA256见 [evidence-index.tsv](evidence-index.tsv)。
索引覆盖原提交的84份报告/原文，包括历史审计；新审计只绑定精简后的当前文件。

| 内容 | 原始文件及边界 |
|---|---|
| 完整native构建 | [create日志](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/native-create-output.txt)，RC0/3175秒；independent-native是同次运行副本 |
| 上游最终结果 | [JUnit](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/upstream-tests.xml)、[注册清点](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/upstream-inventory.json)，371/371，0失败/跳过 |
| 初始失败基线 | [JUnit](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/baseline/upstream-tests.xml)、[完整输出](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/baseline/create-output.txt)，366/5/0 |
| 安装消费者 | [JUnit](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/consumer-tests.xml)，1个CTest，13项内部检查 |
| 最终包及重定位 | [26库SHA表](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/installed-result.json)、[重新编译/运行](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/relocation-output.txt)、[JUnit](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/relocation-consumer-tests.xml)，1/1及13/13 |
| 安装机制对照 | [字节替换表](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/install/byte-only-comparison.json)、[修复后smoke](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/install/rpath-fix-smokes.xml)，机制与最终包分别记录 |
| Math独立参考 | [精确分数脚本](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/fma/exact-oracle.py)、[FMA探针](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/fma/probe.cpp)、[复跑脚本](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/fma/run-repro.sh)；见当前math-oracle.md |
| B独立zlib对照 | [脚本与四组原文](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/parallel)，每组34次真实编译及CTest2/2；并发2/2/1/1 |
| 官方W3失败 | [完整原文](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/w3-local-ci-output.txt)，RC1/2400秒；755步shell启动SDK链接命令OOM/126，未进入CTest |
| 恢复后的诊断 | [结果](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/resource-retry-result.json)，SDK版本查询及同目标单独链接RC0，不覆盖完整W3失败 |
| 历史独立审计 | [原报告](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/audit-result.json)，96文件快照P0/P1=0；当前审计另列audit-result.json |

在完整Git克隆中运行（若使用浅克隆，先补齐上述祖先历史）：

```sh
python3 archives/v/viskores/1.1.1/reports/verify-evidence.py
python3 archives/v/viskores/1.1.1/reports/verify-evidence.py --extract /absolute/new-evidence-directory
```

校验器从固定Git对象取回原字节，重算84份SHA、6份JUnit、注册名称及当前7输入绑定；
缺少对象/文件、哈希不符或测试数量不符都会失败。extract仅导出到不存在的新目录，供运行原复现脚本。
官方W3仍失败，通用PF9共享文档结构误报仍失败；本次精简和审计不把它们或远端CI/AI改写为通过。
