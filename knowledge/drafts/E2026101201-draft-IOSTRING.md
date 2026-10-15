# 重定位 Perl：核心搜索路径不等于模块安装路径

## 触发特征与现象

将实际发布的 Perl 恢复到新的 Conan 缓存后，下游纯 Perl 模块可能出现 MakeMaker 的核心目录缺失警告，或 `Can't locate ... in @INC`。仅设置 `INSTALL_BASE` 不能恢复解释器核心模块搜索；仅把安装模块目录写入 `PERL5LIB` 还可能覆盖必需的解释器核心与架构目录。

## 根因与通用决策

必须区分三个路径契约：解释器运行所需的核心与架构目录、MakeMaker 使用的 `PERL_LIB/PERL_ARCHLIB` 输入、以及下游模块的 `INSTALL_BASE`。发布包内 `Config.pm` 保留的历史构建前缀不一定就是当前真实缓存路径。先定位实际解释器包，再核验核心及架构目录，不根据全局 Perl 或历史日志猜测路径。

修复步骤：

1. 绑定实际发布依赖身份与恢复后的解释器、核心、架构目录。
2. 为原生构建设置包含两个真实核心根的 `PERL5LIB`；将其分别传入原 `Makefile.PL` 的 `PERL_LIB` 与 `PERL_ARCHLIB`。
3. 将 `INSTALL_BASE` 独立指向当前软件包目录，执行原构建、原测试及安装。
4. 消费者只叠加已安装模块根，不覆盖解释器核心闭包。需要真实文件操作时使用当前 UID 拥有、可写且无链接的 POSIX 临时根，而不把共享投影目录所有者误当真实进程身份。

## 验证证据及无效尝试

IO::String 原版 1.08 是本次例证，修复适配版本为 1.08.1。实际隔离目标事务 `io-string-1.08.1-finish-step5-20261012-r1110` 使用已发布 Perl 5.42.2；原 6 个测试文件共 43 条断言全部通过、零跳过，安装包消费者 1 个流程的 3 条断言及真实鸿蒙私有文件/内存流场景 1 项通过。实际规范 ConanVerifier 与 Finish step35 均 RC0；产物路径及10文件基线已真正核验，不把缺cache路径的跳过当通过。源包 SHA-256 为 `2a3f4ad8442d9070780e58ef43722d19d1ee21a803bf7c8206877a10482de5a0`；实际安装的IO/String.pm与官方源成员同SHA-256 `1ab64bb458aff8fa644ef8b89ffdf28b7e76f647ecc130032ee25df4b95ca993`。独立观察报告 `io-string-complete-official-observed-oct12-r1111.json` 绑定完整15回执/30WAL、host回读承诺链、唯一启动与清理终态。

不能把消费者源码复制到自己所在目录：真实 Conan 的布局错误曾导致相同文件复制失败；通过独立 build 目录解决，而非忽略异常。不能只依据原测试的最终 shell RC 声称覆盖完整：应同时保存原 TAP 清单和无跳过结果。显式核心目录修复后仍存在 Config.pm 架构位置提示；本次纯 Perl 原测试成功不等于所有解释器配置警告已消失，也不证明 XS ABI。

## 查重增量与安全边界

E155 已介绍 `@INC` 与纯 Perl 安装。这里新增的是发布解释器重定位到实际隔离 Conan 缓存后，运行时核心、MakeMaker 核心输入和安装根的三者分离，以及真实文件临时根的身份要求。不是全局安装教程，不修改系统环境或其他任务缓存。

适用于原生执行的纯 Perl MakeMaker 项目；不适用于用主机解释器代跑目标测试、XS ABI 兼容证明或伪造跨编译探测。上述正式配方与Finish step35结果不是平台CI、PR提审或远端provider已发布证明；没有CLI或ELF的纯模块不伪造可执行文件smoke/security测试，真实加载/API消费者与源模块字节核验独立保留。

### 构建树投影所有者与三根合同的后续验证

真实worker004在原MakeMaker入口前拒绝HMDFS构建目录的投影UID。构建树
不是安全临时根；只为实际TMPDIR创建真实进程自有的0700非链接POSIX
子目录，核心/架构/INSTALL_BASE三个输入不变，不修改投影所有者、系统
权限或认证缓存检查。临时目录管理器随配方实例持有并自动清理，避免
在build与package之间丢失测试临时根。

新鲜r1360原规范ConanVerifier及Finish step35 RC0，原6程序43点、消费者
1流程3点与鸿蒙1场景零失败/跳过；独立15回执30WAL及清理终态通过。
日志SHA-256 e78238c5021ca311d71a6bfa61a4e23601c20066dd46fbcd9ee0d5fe85ac566b。
这验证三根合同与私有临时根同时成立，不能冒充原worker的HMDFS平台CI
或扩展成XS ABI证明；旧r1110及平台真实失败保留。


### 实际POSIX构建目录与Conan安装根

本轮保留真实Worker在Makefile.PL后3600秒超时的失败记录。只将实际构建、原测试与MakeMaker安装驱动的工作目录放到实例UID所有、规范且无链接的0700 POSIX source-build；实际Conan安装根、原源码及全部断言不改。新事务 `io-string-1.08.1-official-20261014-privatebuild132r001` 同轮规范ConanVerifier/Finish step35真实通过：原6程序43条TAP断言零skip/TODO，消费者3项及鸿蒙专项1项通过；15回执30WAL、唯一launch、own0和release/postrelease独立核验。测试输入tree `127168611f67a76769c2445a7364440c0f0b90c6`，原日志SHA-256 `cdb398a166ec5563e1c70219f326d7876f08db6211dd99055c93e447fe1e4308`。新提交的平台CI及Review仍需独立通过，未声明已发布。


### 实际POSIX构建目录与Conan安装根

本轮保留真实Worker在Makefile.PL后3600秒超时的失败记录。只将实际构建、原测试与MakeMaker安装驱动的工作目录放到实例UID所有、规范且无链接的0700 POSIX source-build；实际Conan安装根、原源码及全部断言不改。新事务 `io-string-1.08.1-official-20261014-consumerfix132r002` 同轮规范ConanVerifier/Finish step35真实通过：原6程序43条TAP断言零跳过及待实现标记，消费者3项及鸿蒙专项1项通过；15回执30WAL、唯一launch、own0和release/postrelease独立核验。测试输入tree `7647d29ed594730de856a453d266e6f452307dd1`，原日志SHA-256 `ce2aa5a3ace4c120948ff99da1fdba7082c42c1f1bc2e0a044d4c094b16f9296`。原平台build104166的鸿蒙专项报Foreign task root，现为该原场景绑定实例真实UID所有的0700规范目录，原Perl断言不改；新提交的平台CI及Review仍需独立通过，未声明已发布。
