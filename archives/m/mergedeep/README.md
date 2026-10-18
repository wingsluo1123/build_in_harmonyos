# mergedeep 1.3.4

纯 Python 深合并库，MIT；本候选修复三个严格类型策略被递归 Mapping 分支绕过的通用缺陷。平台 task8806 标为cpp，实际源码为Python，按真实材料披露，不更改平台标签。`feat/mergedeep-1.3.4` 为已领任务分支。

固定来源、最小补丁、原suite和真实消费者见1.3.4配方及test_package。原suite确实存在，是未修改的unittest.TestCase；原tox使用pytest/py36–py39，本次用标准库收集完整14项，不复建旧环境。

宿主验证：Windows AMD64 CPython3.12.14原suite14/14；现有setup.py install后1消费者、20公开merge调用/20功能向量/2身份检查通过。新消费者对固定未修源码第一次真实运行按预期拒绝，精确报告策略静默绕过；不重复原卡的旧内存probe。缺wheel命令的宿主尝试RC1保留，随后既有setuptools安装RC0。宿主setup.py安装不等于Conan包或OHOS验证。

H1-003在OHOS6.0/armv8/clang15/Release profile及隔离Conan cache中，一次官方conan-verify rc0；真实source/build/package/test_package通过，原suite14/14与真实包消费者1/1通过，20向量/20merge调用/2身份检查分别披露。实际供应Python3.12.9，包模块SHA256 `a3fa951ba5ae9ed0c23751e8d45f8894794920e29c5fbc013b9a31a529f6fb2b`、原tests摘要未变。manifest status=built只表示Conan已验证、未upload，不能直接发布或称W3通过。

003未执行finish/W3且其G4缺cache包ID、L2/L4/L5跳过的原报告保留。随后W3-004在同一固定源码、12文件输入和真实完整diff上完成一次官方完整W3：setup/build rc0，L0/L1通过，L2无bin跳过，L4补丁检查通过，L5真实包lib有内容；阶段内原suite14/14、真实包消费者1/1/20向量完成。这不是额外手动Conan或完整finish；002原configure127与整树JC1/JC5失败、003原验证历史均保留。

W3官方固定基线的mirror fallback将本地conandata源URL从单条GitHub地址改为gh-proxy加原URL的列表。原输入conandata SHA256 `a2a5d4ff23f3754c5e61335d26e75fc526447b1a0ac1ab3b105ad55e8622cb09`，回收后SHA256 `0e04b78e700dcf107e8f2104fc24a3df758d60e761146e57d1b1d2b8dac5bc01`；源归档SHA及补丁字段不变，真实包模块和原tests摘要一致。本Git候选保留原固定源地址，不把官方生成文件误称原输入，也不混换配方源码。

W3通过不等于整体可发布。软件级README/manifest与PF9路径规则的具体支持处置、Conan纯库提交材料适用记录、正式W4、完整AtomCode、外写窗、PR/面板关联/当前CI/有效提审尚待原链闭环；不重播有效验证。

相关知识：`knowledge/drafts/E8806-draft-8806.kv` / `.md`，解释严格策略检查与递归dispatch的顺序，适用边界和近邻差异。无CLI，不增commands.json，不改索引、框架或其他库。

配方沿已有Conan2纯Python路径，以Python runtime dependency提供目标解释器，source固定完整GitHub归档SHA并应用补丁，build执行原suite，package复制原模块/测试/py.typed和MIT许可，test_package从实际包消费。接口依据见[Conan source](https://docs.conan.io/2/reference/conanfile/methods/source.html)和[package_info](https://docs.conan.io/2/reference/conanfile/methods/package_info.html)。具体目标证据及当前状态由本作者私有ENTRY索引。
