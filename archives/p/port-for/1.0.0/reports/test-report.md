# port-for 1.0.0 测试报告

日期：2026-10-10。账号gcw_tlRDjnsx，task9665。目标为OHOS6/armv8、Conan2.29.1、Python3.12.9、pytest9.1.1；本机Windows/Python3.11.0rc2结果单列。生产修正仅在API调用边界把`to_ranges(list(ports))`改为`to_ranges(sorted(ports))`，追加1条回归，原22项断言和skip条件均保留。

来源为官方PyPI sdist `port_for-1.0.0.tar.gz`，21681B，SHA256 `404d161b1b2c82e2f6b31d8646396b4847d02bf5ee10068c92b7263657a14582`。固定补丁同时修改api.py与tests/test_cases.py；实际apply/check后字节与受测源一致，未改边界、长度或socket规则。

| 阶段 | 注册项或程序 | 通过 | 失败 | 跳过 | 实际结果 |
|---|---:|---:|---:|---:|---|
| 原版Windows完整上游 | 22 | 21 | 0 | 1 | 原低端口绑定Windows skip条件 |
| 修后Windows完整套件 | 23 | 22 | 0 | 1 | 同原skip条件 |
| 首次目标修后完整套件 | 23 | 23 | 0 | 0 | 23 passed in 0.51s |
| 官方W3内完整套件 | 23 | 23 | 0 | 0 | 23 passed in 0.55s |
| 目标Conan包消费者 | 1程序 | 1程序 | 0 | 0 | 11功能检查+2身份断言，均通过 |

同一套件的两次执行不相加为46项；适配后声明23个pytest注册项加1消费者程序，共24项，比原22项新增2项。内部100次循环、11功能检查与2身份断言不另计程序。目标修后保留的原上游22项全部通过，不声称未修目标原版22项曾完整运行。

真实缺陷触发：目标未修API的`set(range(1000,1040))`实际先迭代1024..1039、再1000..1023，原返回`[]`，预期`[(1003,1036)]`。唯一新增回归在未修API实际1FAIL；修后完整套件及交付包消费者的区间均正确。该红测试为修复前证据，未删除或包装为通过。

真实命令链为`python3 -B scripts/ohc-run.py conan-verify port-for 1.0.0`及`python3 -B scripts/ohc-run.py finish port-for 1.0.0 built`内部正式zsh setup/build_and_test。W3实际强制Conan create并执行build()完整pytest，再执行test_package消费者；消费者从本次包p/lib/python/port_for/__init__.py导入，覆盖区间、端口选择、实际listener占用、PortStore持久重读、重复关联拒绝及解绑。

首次目标实际包ref：`port-for/1.0.0@ohpcd/stable#bbbbce9164b080026a38a3bdf3367d2c:da39a3ee5e6b4b0d3255bfef95601890afd80709#8259ab313771901978a9d802a661add1`。正式W3实际plain ref：`port-for/1.0.0#bbbbce9164b080026a38a3bdf3367d2c:da39a3ee5e6b4b0d3255bfef95601890afd80709#8259ab313771901978a9d802a661add1`，消费者路径为私有Conan cache的`p/b/port-0e898ca7f1bec/p/lib/python/port_for/__init__.py`。均为本次真实构建，未远端发布。

正式W3的setup/build_and_test均RC0；G0、KC（542条/542索引行）、JC（prdiff完整13文件）、L0、L1、L4、L5实际通过。原W3日志SHA256 `06a295375e4abb4c0610943a08c1995cff62b1afc6369bfc9f21253922bec1e1`，官方生成.ci-result.json的exit_code=0。L2裸CLI --version/--help失败后skip，未称smoke通过，独立核验标准生产VirtualRunEnv：准确缓存包conan install --build=never --no-remote -g VirtualRunEnv实际RC0，全部Cache/Skip，无构建或下载；激活conanrun.sh后version/help均RC0（port-for1.0.0/usage），解释器/模块来自生产依赖和交付包。裸CLI两命令均RC1/ModuleNotFoundError；bash shell-init getcwd权限警告保留。最终文档候选新增本报告后为14文件，旧13文件JC结果不移称已覆盖新14范围。

整体finish真实RC1：旧归档打包/staging与当时缺少命名报告/基线MD的状态原样保留；本报告已补，准确542MD补供后的首次官方graph validate RC0，170条既有警告保留。R19/R20及项目限定裁决沿真实Conan交付，不补废弃打包器或空验证标记，内部裁决不称官方豁免；自动handoff的finish_success/EXIT_CODE0不覆盖实际RC1。首次图谱输入缺失造成的W3 FAIL、构建工具/PYTHONPATH旧FAIL、9次curl缺失预下载诊断、Conan报告缓存定位跳过及本机记录器错误均保留。本机wheel消费者成功和目标Conan消费者成功分别归档，不混用。

原命令、stdout/stderr、固定候选与自然终态由本任务私有ENTRY引用。目标W3回执为`evidence/h1-001/w3-graph-supplement-001-20261010T141614Z/RESULT.json`，SHA256 `360b488b2664fd5847edf52c7dd476afb3f6fdd651f41e4932b43671fd7d6502`，638原件raw包SHA256 `8d57942bfd5f76e7f011009522d90961af9bdb3e2eadde1719419c4bb274aaa2`。窄收口回执为`evidence/h1-001/finish-closeout-001-20261010T145427Z/RESULT.json`，SHA256 `db126c360738a45e19f9827c237e2aa795222dc277b30a56943d14edc42a036f`；629原件raw包SHA256 `aea27d68e4eeb2cfc79f74d251d8850c1158d70caaa2232574c3c075742654ee`。完整独审、当前PR CI/真实AtomCode、面板关联、有效提审须按最终提交和真实回执单独核。
