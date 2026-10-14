# DRAFT-crosstool-1.28.0-runtime-probe-vendor-bootstrap-tri-channel
> Autotools强制工具缺失时运行时探针钉选与vendor自举三通道接线通用范式
## 问题特征（真实日志片段/标记）
- HMBS_PLATFORM_CAPABILITIES shell为/bin/sh，真机仅有cmake加make加ninja加python3可用
- configure重执行/data/service/hnp/bin/bash报inaccessible or not found，Error 127；conftest执行/data/service/hnp/bin/clang报inaccessible，config.log返回127后报C compiler cannot create executables
- 编译器段通过后失败点逐轮后移：checking for flex... no后报missing required tool: flex；随后同模式报missing required tool: help2man、Required tool not found: GNU bash大于等于4.0、Required tool not found: libtool、curses library not found、panel library not found
- make阶段报yacc含/bin/bison报inaccessible Error 127；绕行后报bison找不到/share/bison下m4sugar文件cannot open；随后报libtool悬空路径No such file与libtoolize不认silent参数
- test_package消费者曾0过4，上游upgrade套件曾6过8失败但rc均为0并伴随大量符号absent
## 根因
- ci profile把CONFIG_SHELL与CC写成真机沙箱不可见的hnp绝对路径，os.environ覆盖会被conanbuildenv二次覆盖，必须内联前缀并显式用/bin/sh执行
- 声明tool_requires只保证安装，不保证进入自定义self.run的configure PATH，flex包甚至无bin目录，静态注入无目标
- bison二进制重定位后仍用编译期默认数据目录，包内yacc包装硬编码/bin/bison；libtool包无可运行二进制且Makefile烘焙悬空绝对路径
- ncurses包缺panel头且AX宏走无pkg-config的fallback链接测试，裸requires与单预设均不足，需显式接线与忠实探针配方
- 同一探针加三通道预设加vendor兜底在flex、m4、bash、libtool、bison、panel-menu、help2man共7种强制工具上重复生效，每次换工具对象策略同构，属构建系统行为类而非单库版本补丁
## 修复方案（rec）
1. 在conanfile.py build首部做CC三重验证探针：按conf、环境CC、PATH、已知绝对路径、SDK llvm/bin顺序逐个跑version加带旗标链接加运行，全过者追加到conanbuild.sh并内联CC前缀到configure，plain模式剥离fuse-ld相关旗标；CONFIG_SHELL与SHELL内联覆盖为/bin/sh
2. 在generate从build域依赖取flex、bison、m4、bash、pkgconf等bindir前置PATH并定义对应变量；在build对每项工具做tool包优先到设备候选的真实执行探针：flex用version，m4用-P管道，bash只接受主版本大于等于4，libtool用上游同款version正则，胜出者经os.environ加conanbuild.sh加configure内联前缀三通道钉选
3. 无胜出者时vendor自举到构建目录私有prefix：flex用官方2.6.4源码仅编src，help2man用官方1.49.3源码，libtool用官方2.4.7源码并加文档熔断与直拷config.status脚本兜底，均以冒烟通过才钉选PATH
4. bison通道跳过坏yacc包装器，YACC固定为胜出bison加-y，并审计包内m4sugar存在性后三通道钉选BISON_PKGDATADIR，另加空文法冒烟取证
5. curses通道显式追加ncurses的头库搜索路径并暴露其pkgconfig目录，vendor抽取缺失panel头到私有目录经CPPFLAGS双通道生效，用含头真实API探针实测plain与加tinfo两种配方后预设PANEL与MENU链接变量，pkgconf用远端可用版本并补齐缺失pc文件
6. 三处configure统一修autoconf临时目录权限与mktemp回退，make统一加V等于1与文档熔断，垫片目录持久化进进程PATH避免多内联前缀覆盖丢失
## 禁止策略
- 禁止复用硬编码/bin/bison的yacc包装器：bison本身version正常不代表包装器可用，必须绕行为胜出bison加-y，否则kconfig必死于parser.tab.c
- 禁止钉选未经真实执行的胜出者：仅version猜测或无头桩链接不能证明头加链接双重测试，无胜出者必须如实失败，不得伪造变量放行
- 禁止vendor失败免检直拷：直拷脚本仍须走同款冒烟，失败即报错；腐烂套件未获tag级实证前不得转证据口径或删断言
## 与相近条目的边界（查重）
- 与通用平台能力行、tmpdir行、shell行、configure failed通用行零重叠：本条目只在强制工具探针钉选与三通道接线成立时命中
- 与E165类链接器运行库缺失条目相邻异因：彼为lld缺运行库路径致conftest链接失败，此为编译器路径本身不可执行，需先探针钉选再谈链接旗标
- 与buildtorrent类config-sub缺失条目相邻异因：彼为缺体系三元组识别文件，此为生成器工具链缺失需自举
- 与本任务内flex无bin转vendor、BISON_PKGDATADIR接线、yacc硬编码绕行、多PATH覆盖丢失修复、腐烂套件转证据口径互为同范式分例，不另立异因
## 适用判断
- 适用于Autotools配方在真机报C compiler cannot create executables且conftest返回127，或报missing required tool与Required tool not found且失败点随补依赖逐轮后移的情形
- 不适用于源码下载中断、SSH网关熔断、依赖图远端不可解析等环境与版本引用错误，应按实际日志换路
- 验收以config.log失败段后移、探针胜出者取证、消费者烟囱通过为准；上游套件腐烂须有tag级不存在证据才可转证据口径
