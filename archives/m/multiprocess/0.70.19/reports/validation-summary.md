# multiprocess 0.70.19 验证报告

日期：2026-10-15，Asia/Shanghai。任务15170；分支feat/multiprocess-0.70.19。环境HarmonyOS HongMeng Kernel1.12.0/AArch64、CPython3.12.9、Conan2.29.1。

## 结果

- 真机原版W3 setup/build_and_test实际成功，原FinishPipeline自动生成回执；原始日志SHA256与回执一致，未修改回执。
- 上游清点1213个unittest实例：默认runner的12个脚本共1174例，额外执行其未发现的主模块处理39例。实际通过1057/1213（87.1393%），跳过156，失败/错误0。非跳过用例通过率100%，不宣称全量100%。逐项跳过清单见skipped-tests.md。
- 新增消费者14/14通过：三种启动方式、安装来源与元数据、默认策略、Listener/Manager、闭包池、异常传播、管道、共享内存/共享值、独立文件生产消费、导入不锁全局上下文、-E子进程bootstrap、SharedMemoryManager正常关闭。
- 真实Conan产物消费者14/14；移走该包lib后exit5且找不到主库；finally恢复14/14；重定位14/14。重复执行不增加用例数。
- 产物55个文件，无ELF/ABI对象/字节码/构建工具或CPython test支持载荷。上游自带multiprocess.tests仍作为包内容保留。
- 初轮Conan清单无pyc；初轮W3的-E消费者运行时曾生成12个未登记pyc，已记录哈希后清除并补显式-B。最终这一轮W3已包含-B，后续真实conan test仍为14/14且不再生成字节码。两轮回执与日志分别保留，未改写初轮证据。
- 本地包完整引用：`multiprocess/0.70.19#e479aaabb8bd7e4a268b07bfdebb20ba:f164e144163e174c8b336b22175a25b5af49df3b#5c29c67479d350dd996eebe13e361a9c`。解释器版本选项保留于Package ID。这个引用是本地验证结果，不是远端发布声明。

## 全量用例对账

| 上游脚本 | 总数 | 通过 | 原条件跳过 | 失败/错误 |
| --- | ---: | ---: | ---: | ---: |
| test_multiprocessing_fork/test_manager.py | 77 | 64 | 13 | 0 |
| test_multiprocessing_fork/test_misc.py | 63 | 56 | 7 | 0 |
| test_multiprocessing_fork/test_processes.py | 148 | 141 | 7 | 0 |
| test_multiprocessing_fork/test_threads.py | 102 | 75 | 27 | 0 |
| test_multiprocessing_forkserver/test_manager.py | 77 | 64 | 13 | 0 |
| test_multiprocessing_forkserver/test_misc.py | 63 | 57 | 6 | 0 |
| test_multiprocessing_forkserver/test_processes.py | 150 | 146 | 4 | 0 |
| test_multiprocessing_forkserver/test_threads.py | 102 | 75 | 27 | 0 |
| test_multiprocessing_main_handling.py | 39 | 39 | 0 | 0 |
| test_multiprocessing_spawn/test_manager.py | 77 | 64 | 13 | 0 |
| test_multiprocessing_spawn/test_misc.py | 63 | 58 | 5 | 0 |
| test_multiprocessing_spawn/test_processes.py | 150 | 143 | 7 | 0 |
| test_multiprocessing_spawn/test_threads.py | 102 | 75 | 27 | 0 |
| 合计 | 1213 | 1057 | 156 | 0 |

原版runner与补丁后完整回归分别保存。初始原版测试存在类级fixture错误，部分实例未运行；不能把summary的Ran0写成上游没有测试。补丁不删断言、不屏蔽失败，测试辅助子进程纠正被测库和安装路径，详见notes及patch2。

## 受控失败和修复

1. 精简Python缺test.support：导入失败，测试体未执行。补齐匹配的官方test命名空间；整个上游Lib会遮蔽厂商标准库，该失败构建同样保留。
2. 路径AF_UNIX在HMDFS报EPERM而抽象AF_UNIX实际可bind；原版Listener和Manager失败。消费者RED3例为1失败/2错误；能力标志、地址生成和默认策略一并修复。
3. 导入查询默认策略提交了stdlib全局context：新解释器回归先失败，改为版本受限的未提交默认context读取后通过。
4. -E子解释器忽略PYTHONPATH，spawn/tracker/forkserver无法导入包：独立回归先失败；三者公共bootstrap显式继承父sys.path且保留解释器标志后通过。
5. 上游辅助脚本仍导入标准库multiprocessing：改为本fork，保留隔离模式和原断言，四项定点4/4。
6. SharedMemoryManager析构查找已清空getpid/debug全局变量：关闭期回归先报TypeError；预绑定callable后错误输出为空。

一次中断后的旧/新构建共用create.log造成日志混写和NUL区段，该原始文件保留但不用于最终计数。本报告仅采信独立W3日志及另外完整-v复跑；两次1213例与跳过数量一致。未重写受哈希绑定日志。

## 依赖、门禁及限制

W0：dill/0.4.1和setuptools/84.0.0精确download退出0、revisionsHTTP200，真机依赖二进制安装成功；主库原精确接口404。未pip注入或以本地依赖冒充发布。

W3用官方公开提交7d1f961b778fd04c81bb8d74c8176be3c7da647a中的脚本，在任务独立CONAN_HOME/profile中执行。bash/git来自已有已发布工具环境；设备profile只在验证环境指定，没有改共享CI。原G0、L0/L1/L2/L4/L5结果以w3-local-ci原输出为准。

当前测试支持来源为官方CPython GitHub v3.12.9标签归档，SHA256 `039f6fb89a427f9be79f7c792d51ede216c0d0f74662c797e7cbd510e92f2078`。此前python.org发布归档SHA256 `7220835d9f90b37c006e9842a8dff4580aaca4318674f947302b8d28f3f81112` 在远端CI93518下载极慢（当时仍运行，不能记为测试失败）。两归档Lib/test的1581个文件路径/内容逐文件SHA256完全一致，无特殊条目；独立审计重复核验。新来源沿用仓库已有GitHub镜像回退，真机完整下载27590757字节用时113.21秒并通过SHA256。主库版本、源码补丁、测试断言不变，改来源后重新执行完整W3、产物控制和-v全量回归。CI93518只对应前轮SHA，不能用于新提交结论。

重跑时独立验证目录曾漏带官方.gitignore，部署工具将任务运行状态和真实快照加入私有索引，被原JC门禁拦截，测试未运行。已补回同一官方提交的原.gitignore、只从私有索引移除运行文件并收紧为仅部署Git跟踪的本库文件，原失败日志保留；未删除原始证据、未修改门禁或共享CI。随后最终W3成功。

原版静态门禁仅PF9误报ARCHIVE-SPEC允许的软件级README.md/manifest.yaml缺版本层；精确排除这两项路径再运行该检查，其余原函数无问题。纯库没有commands.json。保留原误报与例外证明，未修改基础设施。

仅验证CPython3.12.9；其他版本/解释器不得推断支持。内部自动生成socket使用抽象命名空间，用户显式文件socket仍受策略约束；抽象端点没有文件权限ACL。保留上游平台/资源条件跳过。原日志中resource_tracker重入清理警告未过滤，不将警告计为通过用例。

## 原始证据哈希

原始日志、产物快照、运行状态和带完整性哈希回执保存在本任务外部证据目录，未提交PR。公开报告只保留统计与哈希。

- `baseline.log`: `d585070d711dbf9f8907003519d5a7b2b04592c6e9e8bc7b3674177bfb6eee80`
- `consumer-red.log`: `09d5988379df9fde7b9bf8dcdcf6f860c8165f849ddbaee899b66be6f08889f1`
- `import-red.log`: `e57739de7828a214c5cd37df6ee55a570c05c6a01bf1e7874941ea82ea7f8d33`
- `bootstrap-red.log`: `dc8810d4c72976fbddbbb2074b6a2c71352b854d40cb9bfb45da8064567dd135`
- `shutdown-red.log`: `25d125bc9ce5f7ecae30e4068c3d920a5761b8ccc0e41043c5041b7d9431096e`
- `consumer-green-v5.log`: `0ad59d37386ac48b9e50f5d6056a27d6e937b1154021f9d7c4734cfb3c20ba2f`
- `helper-targeted-v3.log`: `0462f75745cac92ea80384da88aea95383af612d2c0506d9c2ca3e06b271adef`
- `w3-build.log`: `2e846354fe54cc42e2628b9945d4771e97049a21eaaeabd11087cde39445d7e7`
- `w3-local-ci.log`: `658fe1366c1aa0a7e327ca6aed2283f704e00c3d495ff5723ed73e1e22f16026`
- `consumer-conan-final.log`: `eadf27fd3ec9ba7adf4a78d83d9f173e9a870c98ce8d824db150498956254260`
- `verbose-upstream.json`: `7ab6ed5c6e11ff12af0ddd8665bba8345ab9bd6f5d797e15d6b485be45146fc4`
- `verbose-upstream-raw.tar.gz`: `2cbbb9f43ab8070ed95542552fb6fd7e07fbaefa992f7c30a1a99cd906160824`
- `cpython-tag-comparison.json`: `75db032ef192eb7a5e28f5c7c97cd5b4954c5c332ed25e631898062e8d77fa6c`
- `tag-mirror-probe-full.log`: `2de1699d1500b69df70d4968b7eedbfc37e7c3534e80ad09373adbd883501fb5`
- `w3-source-v2-junk.log`: `52335b0783f4228b64b983325e07134f83618a9e1d8b7dc24f567ea62726eb1a`
- `source-v1-evidence/w3-local-ci.log`: `589d7f1af3b0dfd115f3ed50bb0a2053953f405d1440ac1d35c7d52f326c4514`

远端当前HEADCI、独立W4审核、正式知识入库、合并和发布各自核验；本地验证不替代这些状态。
