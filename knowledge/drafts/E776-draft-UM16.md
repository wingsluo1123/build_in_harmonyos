# E776：测试辅助包与测量工具的依赖环

## 现象与证据

coverage 5.0.4 的完整测试需要 unittest-mixins 1.6；该辅助包的 tox 命令又是 `coverage run -m py.test`。隔离真机运行原测量包装命令实际失败 `No module named coverage`。这条失败尚未修复，不属于通过的测试。

检查官方 sdist：setup.py 仅声明 six>=1.4.0；tox 将 coverage 用于测量，.coveragerc 只有 source、branch、parallel 配置，没有 fail_under 或测试选择守卫。原始测试模块31项均为 unittest TestCase，可由 stdlib 和 pytest 执行；内部故意失败的场景由外层断言捕获，不能重复计数。

## 根因与处理

将运行依赖图、原始断言执行图和测量工具图合并成一张阻塞图，会把可以独立验证的叶子也暂停。本方法仅分离测量包装：保留原测试文件、断言、参数化和守卫，使用可用的原测试执行器，保留源码哈希和完整用例清单。覆盖率阈值、影响测试选择的插件及原始守卫不能按此方法取消。存在此类语义时必须先补齐工具或提供精确证据请求针对性验收调整。

## 真机验证

- 官方 sdist SHA256：05363abe099f0724b7bb6d71d0ce1046078c868cb10b3f1ebdf3ca6593c52507。
- 同一原版测试：stdlib 31/31，已发布 pytest 9.1.1 31/31，0失败、0跳过，源码哈希一致；两种执行器结果不能累加计数。
- 真实 Conan create 中上游31/31，安装制品消费者8/8，独立HMDFS机制1/1。二进制缺失反证实际失败。安装的两个模块逐字节等于官方sdist，无测试或字节码混入。
- 原 coverage 测量包装仍未通过；正式W3、当前HEAD远端CI、审核、合并、正式发布及父项恢复另行验收。标准补丁入口变更后需重新绑定正式验证，不能继承旧recipe修订的结果。

## 查重与适用范围

基于当前主分支181a7f692ba962d15a4e76a1a084a71bf18f935b，对 graph/drafts/doc/operations 进行测量环、工具环、instrumentation/measurement cycle、coverage bootstrap等检索；对全状态Issue33页和PR164页查重。既有线程、HMDFS权限及元数据缺失知识不作为本条新增点。新增候选仅为三种依赖图的识别、完整原断言的等价验证和测量状态单列。

本条为待审核草稿，仅有一个测试辅助库的实际验证，不宣称对所有覆盖率插件、测试套件或语言普遍成立，不宣称官方知识新增资格或分数。

2026-10-17 补充查重：主分支 c3e27421f516d97fb6dbfadfae47af0971c06ee6 的 graph/drafts/doc/operations（1,035条正式知识）使用扩展的测试测量依赖环关键词检索。相近 E588-draft-57EA 与 E545-draft-CP11 讨论测试子进程/动态库的依赖环境保留，DRAFT-E547 讨论临时目录优先级，均不处理测试辅助包与测量工具的依赖环；不把这些既有经验作为本条新增。全状态PR/Issue历史分页及新增页已复核；类别与知识资格仍待官方认定。

## 后续验证

叶子经官方门禁、合并和正式发布可用后恢复 coverage 5.0.4。coverage 正式发布后，应补回 unittest-mixins 的原 coverage 包装命令并保存测量结果；此前始终报告 measurement unverified。
