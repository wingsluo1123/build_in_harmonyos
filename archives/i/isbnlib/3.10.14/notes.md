# isbnlib 3.10.14 适配记录

## 来源与 W0

基线 origin/main: b5e60d0ad3f16f717baff6ea0c0cb969be16ad27。任务分支 feat/isbnlib-3.10.14。
官方 PyPI `requires_dist=null` 不足以证明无运行依赖；源码 registry.py 隐式依赖 pkg_resources，已在隔离真机复现。使用标准库 importlib.metadata 迁移入口点发现，保留两个插件分组和配置开关，无需注入旧 setuptools 或 dummy 包。

PyPI sdist 未携带 isbnlib/test；以官方 v3.10.14 标签为测试及配方源，固定 SHA256。源代码的 Poetry/twine 声明不参与本配方的直接源码布局打包；本配方不运行 pip/Poetry，不声称发布 wheel 或覆盖率。pytest 的 cov-config 仅为可选仪表参数，命令行 `-o addopts=` 禁用仪表，不删改断言。

pytest/9.1.1 精确 download 成功，独立真机 `conan install --build=never` 下载并消费 5 个已发布包：pytest、iniconfig/2.3.0、packaging/26.3、pluggy/1.6.0、pygments/2.20.0.1。Python 3.12.9 为真机既有解释器，recipe 另已精确核验发布。未以 pip 安装缺失依赖。

## 真实失败与修复

1. 原版 pytest 收集 70 项并有 2 个收集错误：registry 导入 pkg_resources 失败。0001 迁移标准库入口点，支持 Python 3.8/3.9 的 mapping 返回形式和新版本 select 形式。Python 3.8/3.9 仅代码兼容，未实机执行。
2. 原版 sdist 构建无 tests，pytest 收集 0 项并退出 5；改官方标签后收集 73 项。
3. 非网络回归最初 48 通过、1 失败、6 错误、18 deselected；/tmp 只读导致文件测试错误，spawn 无法 pickle 局部 worker 导致 multi 失败。0002 将 worker 移至模块级；0003/0004 将 test_files.py/test_rename.py 改为每模块 TemporaryDirectory，恢复原 cwd，保留所有文件名、重命名及网络断言，防止在共享临时目录删除无关 PDF。

## 测试清点与结果

官方标签有 22 个 test_*.py 文件，pytest 实收集 73 项，其中 network 标记 18 项，非网络 55 项。静态函数定义计数不能代替pytest实际分母。
Conan 默认网络选项 false：55/55 通过，18 deselected，零 skip；开启 network_tests=True 执行完整套件。完整 73 项网络实测的失败和错误单独记录于 validation-summary；不把默认子集写为上游全量通过。

安装消费者 15/15，通过 `python3 -I -S`：安装来源、ISBN10/13 正反例、转换、清洗、校验位、范围数据、语种、两种格式、注册服务、真实 dist-info 两分组发现、关闭插件、无插件内建项、独立生产/消费进程、显式 spawn 正常及异常任务。只认独立用例数，重复回归不累加。

## 环境与知识

HarmonyOS HongMeng Kernel 1.12.0 AArch64，Python 3.12.9，OHOS Conan 2.29.1。独立任务目录 codex-isbnlib-3.10.14-20261016；设备 profile 指向现有用户目录工具链，未修改共享 CI 配置。
复用 E002/E265 的临时目录知识、E055 的进程环境边界、E512 的依赖审计、E319 的 Python noarch 布局；sdist 测试缺失复用既有标签追溯草稿。
新增 E429-draft-ISBN：废弃运行时 API 的插件发现迁移及真实 dist-info 正反对照。候选号和路径 B / 10 分候选由官方确认，不声明正式入库或获得积分；纯 Python 库赛事范围需官方确认。

## 验证边界

当前构建成功仅指非网络回归及安装产物消费者；完整网络结果、W3、独立 W4、当前 HEAD 远端 CI、评审、合并与发布分别报告。原始日志保留在本地交付目录，以 SHA256 引用，按仓库规则不把本地状态与日志提交 PR。

## 最终实测

完整73项：56通过/16失败/1setup错误/0跳过，通过率76.71%；55非网络全部通过，18网络中1通过、16失败、1错误。详情见reports/validation-summary.md与validation-evidence.json。W3新回执绑定原始日志SHA256 ab52e768debba69fbce5df01b801b9730025f401bc3f5d182cf7ae1a6cce2843。四个逐文件补丁由refresh-patch自动生成，原/工作目录哈希299ad7cef619ae23/d48bd3a55a1d7cf2。安装payload39模块逐字节等于最终全量所测runtime源码。
---

**编译结束**: 2026-10-16 03:03
**最终状态**: built
