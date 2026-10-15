# E429-draft-PV51：Setuptools C++ 扩展独立链接命令与解释器历史配置

## 问题及输入输出

输入为 Conan 当前编译器/依赖路径、解释器 sysconfig 和选定 setuptools 版本。预期输出为采用当前工具链的 C/C++ 扩展链接命令、可加载的签名模块与真实消费者。

Plyvel1.5.1 首轮只设置 CC/CXX/LDSHARED，实际 C++ 链接仍含 -fuse-ld=bfd 和 Python 发布者缓存路径；clang15.0.4报 invalid linker name。不是先删除源码参数：设置本身没有覆盖到 C++ 链接通道。

## 根因及修复

setuptools84 的 Unix Compiler.configure_system 分别读取 LDSHARED和LDCXXSHARED，设置linker_so和linker_so_cxx。后者不会因前者已覆盖而跟随变化。准确配置二者，保留当前依赖libdirs与扩展的显式libpython链接；不修改依赖Python的共享sysconfig，不注入伪平台宏。

从Conan tools.build:compiler_executables读CC/CXX，再设置 LDSHARED=<CC> -shared、LDCXXSHARED=<CXX> -shared。库路径从dependencies[].cpp_info取得，不复用Python旧缓存路径。在原setup.py build/build_ext路径验证实际命令，不只相信环境变量存在。

适用范围：实际工具版本使用分离 C/C++ linker 的 setuptools 扩展及复制/迁移过的解释器配置。不适用于原版本没有此分离逻辑、平台要求额外链接参数却被删掉、或基础库ABI不兼容的情形。

## 实际验证与反例

首轮原链接失败日志 create-bfd-failure.log保留；读取实际sysconfig和Compiler.configure_system确证不同通道。补齐LDCXXSHARED后越过链接，但加载又出现Comparator typeinfo缺失——证明链接器修复不等于ABI修复。LevelDB无RTTI，绑定子类需匹配-fno-rtti；保留异常机制，generated C++含try/catch，不能盲目复制LevelDB-fno-exceptions。

最终真机53/54通过、1项HMDFS权限能力跳过，消费者11/11（含跨进程完整流程1项）、载荷移走失败/恢复通过，ELF依赖均为basename、无缺失Comparator typeinfo引用。对应结构化证据为 archives/p/plyvel/1.5.1/reports/validation-evidence.json、upstream-tests.xml、evidence-sha256.json、validation-summary.md；原始日志只本地保留。不宣称所有工具链/平台已验证，不伪造历史CI失败编号。

## 查重与实际增量

基线main ca72b8c6f689926d7ccc7425a08b140b9adcd26a，检索graph/doc/operations/drafts：LDCXXSHARED、linker_so_cxx未命中。E004/E078指导LDSHARED+libpython，未覆盖C++通道独立配置；DRAFT-cdb-20251021-hnp-clang15-no-bfd-linker解释链接器可用性，未覆盖选错通道；gclib标志传播已覆盖一般RTTI匹配，不拿RTTI本身重复申请。

draft-review建议create，最高E045=0.21，属于libffi W^X闭包，与本例不同。工具只辅助；本条为paired draft，正式编号、入库、路径B与10分候选资格由主编/官方判定。
