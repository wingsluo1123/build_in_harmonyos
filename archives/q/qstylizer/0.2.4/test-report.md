# 验证结果

固定官方 PyPI qstylizer 0.2.4 sdist SHA256：`4880991d912c9837454832e8e2b58d60b66848d8c4a7cf57ed544fd68b91a23a`。新官方生成补丁在目标应用后源码与原受测字节一致，配方及测试行为未变。复用已有有效验证，未另行重跑独立软件测试；官方W3必要conan create实际执行原suite、回归及消费者，计数不累加。

| 层次 | Windows CPython3.11 | OHOS Python3.12.9 |
| --- | --- | --- |
| 原suite（未改原文件/fixtures） | 原版及修复后均72/72 | 修复后72/72 |
| 新增边界回归 | 原版1通过6失败，修复后7/7 | 7/7 |
| 交付布局/交付Conan包消费者 | 1/1流程、8断言 | 1/1流程、8断言 |

目标：HarmonyOS / HongMeng Kernel 1.12.0 / aarch64；Conan2.29.1、Python3.12.9。目标消费者核实模块来自实际交付包，完成QSS解析、修改颜色及data URL、输出、再解析；`"left;right"`保持完整。上游46单元/26集成，新增6单元/1集成；消费者单列，不把8断言当8消费者。

Conan Verify报告为PASS，G2实际conan create成功；其G4曾报告无法定位包ID，L2/L4/L5因此跳过，不冒称执行。随后真实postflight取得完整包引用及路径，并核交付style.py与R3受测源码一致；无bin库的L2不作CLI测试。

实际W3包引用：`qstylizer/0.2.4#aa7d0eaedeaf3d3d0372668fb262cfd3:da39a3ee5e6b4b0d3255bfef95601890afd80709#30871850785b421f0d160a50c70e3cec`。目标新补丁patch_ng应用后raw style.py SHA256为`afa8f8af1a3e6ef80c86c9f1d68fd8fe9e56564246d64efbe662ddcec6bcf926`，与原受测字节相同；其他源码不变。新export为`qstylizer/0.2.4@ohpcd/stable#aa7d0eaedeaf3d3d0372668fb262cfd3`。

完整W3：**PASS**，官方`FinishPipeline.step35_local_ci`实际执行setup/build_and_test并生成`.ci-result.json`，exit_code=0。L0、L1、L1e破坏性负向测试、L4、L5 PASS；无bin目录，L2 SKIP。必要W3 create实际取得72/72上游、7/7回归及1流程/8断言消费者。

官方基线d11b980的G0b与后续KC2/KC5历史失败均保留。私有目标运行目录仅同步官方ad0c1a73eaeeb0807aebf150606a75a9ee950bd0的build_and_test.sh及knowledge_check.sh；没有改共享框架或知识graph。未重放完整finish，不把单个官方W3步骤说成整个finish终态。

原始依据：作者原ENTRY索引的H1-001旧失败、H1-003 RESULT/RELEASE、新patch原生应用/export及完整W3日志。W3日志SHA256 `5d7e7a896da750dc82c978c48b4bb52c65679b2ab0a37797f350cbac5966eaff`；官方.ci-result.json SHA256 `c1d32782ee4f0ee06d9e7f15a69d5afd9b163ea200a472ad0712f12377acdd03`。原独立W4和R3受影响复核通过，原FAIL保留；本次仅更新结果文本，不重开完整W4。AtomCode、本PR官方CI及提审尚未完成。
