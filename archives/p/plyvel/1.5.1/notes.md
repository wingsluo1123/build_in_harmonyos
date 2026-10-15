# plyvel 1.5.1 适配笔记

## 范围和构建

分支 feat/plyvel-1.5.1，main 基线 ca72b8c6f689926d7ccc7425a08b140b9adcd26a。真机 HarmonyOS PC / HongMeng Kernel 1.12.0 / AArch64，clang 15.0.4、Conan 2.29.1、CPython 3.12.9。

官方 PyPI sdist SHA256 3caf6009e4fc24fbf8712d3f5ef3da7e56495c26a488df2161218fc34e46019c。上游说明 LevelDB>=1.20；使用发布包内 Cython 3.0.8 生成 C++，不现场重新生成。python/3.12.9、leveldb/1.23、setuptools/84.0.0、pytest/9.1.1 精确配方下载成功；真机独立缓存 --build=never 成功。pytest-cov 是未发布的覆盖率仪表，原版测试和 setup.cfg 无 coverage 导入或选项，不影响54项功能用例；本次没有覆盖率结论。

## 真实失败及修复

1. Conan 默认并行下载在 ThreadPool -> SimpleQueue -> multiprocessing.SemLock 报 Errno28；原版 Conan 提供 core.download:parallel=0，任务独立缓存使用该配置后全部二进制下载成功。不据此声称实际磁盘满或所有 POSIX 信号量不可用。
2. 第一轮设置 CC/CXX/LDSHARED 后，C++链接仍携带 Python sysconfig 中的 -fuse-ld=bfd 和旧依赖路径，clang直接拒绝。setuptools84 Compiler.configure_system 使用独立 LDCXXSHARED/linker_so_cxx，补齐对应当前 Conan C++ 编译器的命令后成功链接。没有修改 Python、setuptools 或共享 CI。
3. 随后 import 报 _ZTIN7leveldb10ComparatorE 缺失。LevelDB1.23 CMakeLists.txt 显式 -fno-rtti；发布共享库导出 Comparator vtable/析构但不导出 typeinfo。PlyvelCallbackComparator 继承该基类，启用RTTI会生成基类typeinfo引用。当前绑定无 dynamic_cast/typeid，私有 CXXFLAGS 加 -fno-rtti 后不再引用该缺失符号。保留 C++ exceptions，Cython生成代码实际含 try/catch，禁止顺便加 -fno-exceptions。
4. 原版54项执行得到53通过/1失败，test_open_read_only_dir 期望 IOError，实际 Error 表示目录仍可写、数据库不存在。独立探针 chmod(0500) 后模式仍02751且写文件成功。只在该测试新增 TemporaryFile 能力检查：PermissionError时继续原 IOError断言，实际能写则关闭临时文件并 pytest.skip，其他错误不吞掉。无平台宏、无删除用例、无降低原断言。

补丁由原仓库 refresh-patch --auto 在真机生成，并通过原 dry-run 及宿主 git apply --check。Windows 原工具 nested path 写出失败，使用真机原工具，不改共享脚本。

## 测试清点与验证

官方 sdist含 test/test_plyvel.py，AST清点54个测试函数，无参数化扩展。pytest/JUnit 实测54项：53 passed、1 skipped、0 failures/errors，普通通过率98.15%；运行的53项100%，不能表述为上游全量100%。跳过仅只读目录，原因如上；标准支持chmod的文件系统继续原断言。按 test_version 1项单元、其他53项DB/文件系统/线程集成分类。

新增消费者11/11，涵盖安装路径/版本、二进制数据、删除、批写和异常回滚、快照、区间迭代、前缀、sync持久化、Python比较器回调。运行不依赖pytest、源树或构建工具。移走本任务缓存包的lib后必须ModuleNotFoundError（退出1），finally恢复后11/11（退出0）；重复诊断不累计新用例。

扩展DT_NEEDED是libpython3.12.so.1.0、libleveldb.so、libc++_shared.so、libc.so，无缓存绝对NEEDED，无缺失Comparator typeinfo引用。产物不含测试、pytest、setuptools或pyc；最终路径签名。实际Conan引用和结构化证据见reports/validation-evidence.json；原始日志保留任务artifacts目录，哈希见reports/evidence-sha256.json。

## 知识与交付边界

新草稿 E429-draft-PV51 聚焦 setuptools C/C++扩展独立链接命令。main graph/doc/operations/drafts 检索 LDCXXSHARED、linker_so_cxx 无命中。E004/E078只覆盖LDSHARED/libpython；cdb linker草稿覆盖可用链接器但不覆盖语言选择；gclib标志传播覆盖RTTI的一般原则，故不以RTTI重复申报。draft-review 建议create，最高E045=0.21（W^X闭包，根因不同）；最终资格、通用性、编号及积分由官方确认。

## 结束

最终状态：built（真实Conan与消费者通过）。本地CI、独立审计、远端当前HEAD CI、审核、合并和发布分别取证，不沿用旧提交结果。

## 本地 CI 与流程核验

原始 conan-verify 使用任务 device-profile 实际通过；原始 FinishPipeline.step35_local_ci 调用 setup.sh/build_and_test.sh，通过 L0/L1/L4/L5，L2无CLI不适用。工具生成的回执 exit_code=0，日志SHA256 `c1bac5a05937ccb5265f9344f5189a671d1c0f8d5a9cd0472ceb5c126e9ea964` 逐字节一致，禁止手写回执。W3临时镜像/预下载改写以原脚本finally还原，提交仍为官方URL。

原 close-archive/finalize 已执行；旧 release/debug tar要求与ARCHIVE-SPEC废弃packaging规定冲突，本库由Conan真实打包，不制造tar来消警告。W5 graph validate退出0（170条存量warnings）；完整性检查在既有E219/E253/E305空字段处报告一类问题，未修改这些正式条目。本任务paired draft非空、文档配套、查重建议create。

本地成功不代表当前HEAD远端CI、审核、知识入库、合并及发布完成。

## 2026-10-14 rule12 评审修复

补充 test_11_consumer_workflow 和 consumer_workflow.py：一个完整传感器记录消费者流程，在真机 Conan run 环境中启动两个独立 CPython 进程。生产者从安装包导入签名扩展，创建前缀数据库、sync 原子批写、验证快照、回滚未完成批次、删除过期记录并关闭数据库；消费者新进程重新加载安装包、重开数据库、遍历持久化记录并汇总。两个进程都核验模块来源位于 PLYVEL_PACKAGE_ROOT，读取必须得到001=21、002=19、汇总40。使用标准API提高可移植性，不声称流程仅适用于鸿蒙。

此次新增1项完整消费者流程，原10项消费者集成测试保留；统计为单元1、集成63、鸿蒙消费者1、其他0，合计65（上游54+消费者11），不重复计算子步骤/断言。Conan test_package和W3均11/11。独立破坏记录sensor:002后新进程消费退出1，恢复生产数据后成功；移走任务包lib后导入失败、finally恢复后11/11。以上负向重跑不增加用例数。结构化进程/模块来源/数据及失败输出见validation-evidence.json，原始日志哈希见evidence-sha256.json。

旧提交18d4d169的远端CI构建89502已通过，不能作为本次修改通过的依据。本次当前HEAD远端CI和真人复核随PR更新单独跟踪。
