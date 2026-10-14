# 包图解析成功不能代替语言运行时强依赖闭包

## 场景与问题现象

从真实制品仓解析解释器及模块得到完整版本身份、Download 和空
info_invalid 后，实际运行仍提示缺少下一层语言模块。另一个常见误判是
主线归档写 published，但只有元数据没有可执行配方。不能把这两类静态
信号直接写成父包可用或“只剩 CI”。

## 根因与通用触发特征

Conan 只解析配方声明的边；它不能推断遗漏的上游 runtime requires。
解释器的动态 import、require 或插件注册是另一层依赖语义。触发特征是
包图成功而目标导入失败，或软件目录存在却精确远端配方未解析。纯模块
与 XS/FFI 模块还需分别验证：不把同名 SONAME、可选纯后端或其它解释器
版本的二进制包装成等价能力。

## 可复用处置步骤

1. 保留实际命令、RC 与原错误链；图成功和运行失败同时真实保存。
2. 对比官方元数据的 runtime requires 与精确配方依赖图，区分核心模块、
   非核心强依赖、作者测试和上游可选后端。不要无条件拉入所有建议项。
3. 对每个非核心强依赖绑定真实提供者版本及 RREV/PID/PREV。recipe-only
   的远端策略错误不解释为不存在；以 --build=never 实际解析校准。
4. 在实际目标隔离环境加载模块，验证真实API及当前路径/哈希；先补最低
   缺失层再回父包。不得用假模块、伪aggregate、共享site目录或假凭据代替。
5. 完整原测试、消费者/鸿蒙专项和正式Conan分别通过后再提交。代码、
   运行闭包或当前HEAD变化必须重新绑定；旧失败与旧回执不追改。

## 本次证据与验证方式

发布的 SQL 解析器和当前 Perl 在同图实际下载后，真机导入先报告
Params::Util、再报告 Module::Runtime 缺失，实际RC2。原图省略这些强边；
主线 Module::Runtime 的0.018只有元数据，没有 conanfile.py/conandata.yml。
这不是设备权限例外，而是实际提供者缺失。

本次恢复的0.018.1为官方0.018的适配修复后缀。官方源归档 SHA-256：
`0bf77ef68e53721914ff554eada20973596310b4e2cf1401fc958601807de577`。
新鲜正式 r1239 实际 ConanVerifier 和 Finish step35 RC0，原11程序/365
断言零失败、零skip/TODO；真实消费者2流程及OHOS私有POSIX加载1场景
通过。安装模块与官方成员字节相同，SHA-256
`d42f55f7db768b4780a9992ebcb5b772af66cfe07e846ed23ad293298a2e0def`。
独立15回执/30WAL、唯一launch、own0和原release/postrelease均核验。
原 r1229/L0 源后缀失败及 r1233/L1 分号marker失败保留，不升级旧结果。

本任务 reports/official-same-run-observed.json、conan-create.log、
conan-verify-report.md、w3-local-ci.log及实际安装绑定报告提供可核验材料。
365是原TAP断言/测试点，不是365个独立程序；不由此虚增高难测试数量。

## 适用、安全边界及无效方案

E155解决解释器搜索/安装根。本条补充图内未声明强依赖与真实导入错误链
的双层闭包，不能只改 PERL5LIB 来掩盖不存在的模块。适用于语言模块与
插件，不改变系统解释器、账号、权限或服务。已选择上游真实可选后端时
仍要说明实际加载的是哪个实现，不声称未加载的XS也通过。

父SQL解析器的Clone闭包和父钱包尚待完成；此叶节点通过不等于父包通过。
本地Conan/Finish与平台CI、提审、合并及远端发布是独立终态，不能迁移。

## 构建目录与安全临时根不能混为一谈（本次增量）

平台 worker 的 Conan 构建目录处于服务投影文件系统，能够完成源码复制，
但其 inode UID 不等于实际进程 UID。对整个构建目录套用私有认证缓存的
所有者条件会在运行原测试之前错误拒绝；反过来取消真正临时根的 UID
检查同样不安全。遇到“可写构建目录却被 owned POSIX build root 拒绝”时，
应先定位需要私有语义的实际路径，只隔离测试 TMPDIR，不迁移整个构建树。

选择实际可写、非链接的 POSIX 父根，使用 TemporaryDirectory 创建独有的
0700 子目录，验证真实进程 UID、规范路径和访问能力；实例持有目录管理器
直至其构建/安装生命周期结束，之后自动清理。OHOS 不接受投影 UID 冒充
进程所有者；其他 POSIX 主机的根所有者 sticky 临时父目录另按原语义验证。
不修改系统所有权、共享缓存或认证保护。

新鲜 r1356 使用此生产配方，真实规范 ConanVerifier 与 Finish step35
通过：原11程序/365点、消费者2流程、鸿蒙1场景，零skip/TODO；独立15回执/
30WAL及release/postrelease验证。正式日志SHA-256
57c65f710049daf8dd89a65474f2807b3cfd27010e6796de8e45026227cecd0f。
这证明当前修复配方及私有根场景，不宣称已在原失败worker完成平台CI；
不适用于弱化Kerberos replay缓存或其他安全敏感文件的真实UID检查。


### 配方与消费者的临时根生命周期

A build-tree ownership predicate cannot serve as the identity contract of private test/configuration state. Retain the accessible Conan build tree and create a per-instance POSIX root for both production Config projection and consumer fixtures; enforce real UID, canonical path and 0700, release the consumer directory on every exit. Fresh original tests and actual public consumers/Harmony validate this distinct lifetime boundary; no permissions, accounts, package ABI or original assertions are weakened.

 本轮当前CI缺陷修复在新事务module-runtime-0.018.1-official-20261013-consumer132r001实际规范ConanVerifier/Finish step35通过，原11程序/365断言零跳过、消费者2流程和鸿蒙1场景均完成，15回执30WAL/own0/release/postrelease核验；原日志SHA 5e4f8c983b2cce2d4276fb2bd0b717b3acf9d135ecf9dcfc4cb4bc193cc8e301。平台新HEAD CI/Review仍待实际结果，未发布。

实际CI拒绝位于路径规范性/所有权复合guard；没有其即时stat字段，不追认单个Worker当时具体UID。保留该失败。修复不把整个构建树当成认证根；本轮Config与消费者均创建并校验真实私有目录，不改测试原断言，消费者退出时由TemporaryDirectory收尾。
