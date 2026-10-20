# DRAFT-sniffit-0.7-rrev-pin-ohpcd-direct-build-ncursesw-fix
> CCI依赖链拖入m4源码构建失败时RREV-pin切至ohpcd配方并直编规避工具链及宽字符ncurses链接修正
## 问题特征（真实日志片段/标记）
- 依赖构建阶段卡死：m4/1.4.19: ERROR，Package 579a4b17efad2529af523121b5f4edcffd66d829 build failed，RUN configure后configure[139]报/data/service/hnp/bin/bash: inaccessible or not found Error127，本包构建从未执行到。
- 直编切边后暴露链接失败：ld.lld: error: unable to find library -lncurses，clang-15 linker failed，sniffit/0.7 Error in build，Package 2fed5cb21ea3c6755b3a28bfcbd5a32ee0bf52f4 build failed，此前已有编译通过的8 warnings仅链接失败。
- 平台能力：shell为/bin/sh，cmake/make/ninja/python3均在HMBS路径可用，profile将SHELL/CONFIG_SHELL钉死到缺失hnp bash。
## 根因
- 裸libpcap/1.10.6按远端顺序先命中conancenter autotools配方，其tool_requires经bison/flex再经requires拖入CCI m4/1.4.19源码构建，其configure重exec profile钉死的hnp bash直接Error127；本包generate域sniffit_hmos_fix脚本只作用本包构建域，无法触及先构建的依赖，故本包SHELL加固重复无效。
- ohpcd libpcap为cmake配方无任何tool_requires，RREV-pin切至ohpcd即可切断CCI-libpcap到bison/flex到CCI-m4边，从依赖图消除m4构建。
- ncurses/6.6为宽字符静态构建，package_info libs为formw/menuw/panelw/ncursesw，包内仅libncursesw.a无libncurses.a，直编硬编码-lncurses必然找不到；上游仅include ncurses.h故编译能过，问题只在库名。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. archives/s/sniffit/0.7/conanfile.py requirements改为RREV-pin libpcap/1.10.6到ohpcd配方，切断CCI-bison/flex到m4边；ncurses/6.6因CCI无此版本保持裸引用。
2. 删除automake/autoconf/libtool tool_requires，消除本包对m4构建边的直接依赖；build直编SOURCES的7个TU并排除sn_conn_desc.c，按configure.ac探针生成config.h到构建目录隔离区，package直拷产物。
3. 链接行去掉-lncurses，改为随LDFLAGS透传LIBS并显式兜底-lpcap -lformw -lmenuw -lpanelw -lncursesw，保持formw/menuw/panelw/ncursesw消费端在前顺序，py_compile校验conanfile.py通过。
4. notes.md新增链分析条目与两级manifest同步，真机conan create验证不再构建m4源码且无-lncurses缺失，全部门禁通过。
## 禁止策略
- 禁止在宽字符静态包下回退到-lncurses：模式-lncurses未接w即拦截；包内无libncurses.a，硬编码必触发ld.lld unable to find library -lncurses退回修复循环；config.h的HAVE_LIBNCURSES仅为界面门控不得改动掩盖。
## 与相近条目的边界（查重）
- 与twopaco自检占位、kyua vendored缺makeinfo、agg-1缺失编译器回退均已判reject：本轮是依赖configure重exec缺失shell与宽字符库名错误，无自检开关、无文档重编、无编译器缺失证据。
- 增量性：现有条目无RREV-pin至ohpcd、删tool_requires直编规避依赖域m4失败、-lncurses到-lncursesw修正覆盖；通用性：RREV-pin切边与宽字符链接名修正换库仍有效，非单库临时绕过；近似aldo/0.7.8 vendoring直编变体但本条新增依赖图切边口径。
## 适用判断
- 适用：裸依赖先命中conancenter autotools配方并经bison/flex传递引入CCI m4源码构建且configure报hnp bash inaccessible Error127时；依赖为ncurses宽字符静态包且用AutotoolsDeps透传LIBS直接cc链接报-lncurses缺失时。
- 不适用：失败在本包configure自身缺shell且无传递m4边时；缺makeinfo等文档工具链时；链接缺失为头文件或符号本身而非库名后缀w时。关键词rrev-pin/tool_requires/ncursesw/hmbs_repair_method命中时优先匹配本条。
