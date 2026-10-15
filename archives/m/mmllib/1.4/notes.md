# 固定来源、范围与当前证据

orrkri / task 8956 / feat/mmllib-1.4。新适配 A+B；无 PR、发布租约或提审回执。官方 main f6a25613daaf1aec7170321c249d6ccf3f329593；源码 sdist SHA256 c2bffd2357b8ff087b02cc1d902973eed385340667ed4c000588ad5d85111964。

生产源码只改 musicxml.py 的 ply→extra 判别对象；数字音符用原表归一化，-1 休止不索引，字母拼写不重写。无格式扩展、额外运行库或测试框架。

上游清点：test_parser.py 3 方法、test_playlist.py 1 方法、test_musicxml.py 1 方法，共 5。test/util.py 与 loreley.mml/xml 保留。新增 MusicXML 3 回归方法含 5 参数化子用例；合计 8 方法。消费者另计 1 程序场景/11 断言，不混加。

首轮主机 suite 保留元数据失败及沙箱临时目录 errors；沙箱外消除环境错误后仍为元数据失败。原未改源码在 CPython3.12.14 同样 4/5；duration 唯一差异约 7.1e-15 秒。仅该浮点断言改为 12 位小数比较，其他元数据仍严格相等；未删除测试或改生产求和。最终 Windows suite 8/8。

setuptools84.0.0 构建纯 wheel，原 test_suite 选项及许可证分类警告保留；测试由独立 unittest 入口实际执行，不依赖 setup.py test。wheel 安装到本软件私有目录，API + 两 CLI 消费者 1/1、11 断言通过。消费者首轮缺包运行环境的失败已保留；明确接入 PYTHONPATH 后复测，未重建未变 wheel。

供给复用：Python3.12.9#d8eda770878152bea40b42db9f7024cd，package 6c7db42132821d241106bb3c9ac38ad21bf97eec / PREV a71d1eefc7332dae9aba6862098bb2b2，OHOS6.0/armv8/Clang15/Release。供给不等于本包目标成功。setuptools84.0.0 wheel SHA256 51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670；无需 pytest 或额外运行依赖。

H1-001原始输入head ee8680a220e83fa3a6ef19c5a5b9052ec3f0774d，15文件与输入manifest一致，3补丁最终字节未变，两个Conan源码树的3修后文件均与本机已测源摘要一致。OHOS6.0/armv8/clang15/Release profile下Python3.12.9固定RREV/PID/PREV实际用于构建及消费。Conan完整8方法suite通过，安装包消费者1场景/11断言通过；正式finish内两个Conan构建流程各实际执行，方法/场景分母不重复加倍。详见 reports/test-report.md 及保留的原始conan-create/W3日志。

W3 L0/L1/L1e/L4/L5通过，L1e真实移走bin/lib后反向验证本消费者依赖被测包；L2帮助/版本探测skip。实际转换与lint CLI已在消费者成功，未新增--version/--help上游功能。finish一次自然结束rc1，PID/PGID30344均GONE，无外层signal；未把回收成功或报告Verdict PASS写成全量finish通过。

原G0 configure exit127，日志同时有getcwd Permission denied及无./configure；纯Python源码不具备configure，未添加空脚本。W5提示共享基线E219/E253/E305缺字段；本配对草稿另经实际解析。gen_summary的str.append错误保留，本项两个manifest可由同一官方解析函数读取；未认定全局错误根因。旧packaging/tar/staging警告保留；正式Conan包替代手工tar的规范依据及这些检查适用性交二级/W4裁决，不造标记或修改框架。

尚缺独立W4、B申请、有限发布租约、PR/任务面板关联、当前head官方CI、真实AtomCode检视评论及有效PR视角提审。平台cpp/实际Python差异保留，不改标签或调用Worker终态接口。

唯一审核入口 work/mmllib-1.4/ENTRY.md。目标软件/Conan/W3分项已有真实证据；没有published、官方CI PASS或有效提审。
