# twodict 1.2 / H1-001 真实目标测试

输入候选：73cd566b319e01ce8cdfc91f7048b1ff1a65688d；原请求20261013-h1-twodict-001。OHOS6/armv8，Conan2.29.1，Python3.12.9精确包revision a71d1eefc7332dae9aba6862098bb2b2。源包SHA256 20dbdfa7f14a285454d34bba1e7714aad15a376ddfd0a1c0a3c24a14763bdb45。

| 实际阶段 | 清单 | 执行通过 | 原跳过 | 失败 |
|---|---:|---:|---:|---:|
| 原all_tests_suite（保留嵌套类） | 71 | 65 | 6 | 0 |
| Conan安装模块消费者 | 1流程 | 1流程/9断言 | 0 | 0 |
| 合计（不另计断言/机制输出） | 72 | 66 | 6 | 0 |

原测试命令由真实Conan build执行，消费者由真实conan create的test_package运行。原六项Python2跳过未改。运行用例通过率65/65=100%；不能写71/71。W3实际运行setup.sh及build_and_test.sh并返回0；L1e破坏性负例移走模块lib/后消费者失败，证明消费依赖实际安装包。L2无bin/明确skip，不计PASS。

日志同对象观察：public_items=[('a',1),('b',2)]；parent_copy={'a':1,'b':2}；raw_items=[('a',1),(1,'a'),('b',2),(2,'b')]。

原始完整W3日志：h1-001-w3-local-ci.log，SHA256 c7fef3e973f610942c1e92ac14e1f5c2faa50a9f6e33dcaf13428b8c29aea20b。原真实生成的.ci-result.json另以h1-001-ci-result.json保存；不手写当前候选CI标记。回收tar为16250880B，SHA256 f2ce4f879906668d69b2f2c6fb2abd17246cb064d83500527b6ab94b2bf0dc46，内部163文件、finish_rc1，原pid/pgid均GONE。

证据只证明原候选的目标原套件、消费者和W3。整体finish失败的原steps为step3、step5b、step8：G1、知识完整性、submit就绪缺报告/packaging/.staging-verified；另有非阻塞gen_summary异常及G0默认configure不适用的原FAIL。后续只变补丁导出入口/归档记录，源码补丁、build、package和消费者未变；是否复用当前门须按准确差异核定，不将本报告当官方PR CI或有效提审。
