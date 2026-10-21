# xgks 2.6.1-dfsg.2 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.13 生成的 configure + 手写递归 Makefile）
- 编译日期: 2026-10-14
- 编译器: clang/clang++（真机 /data/service/hnp 工具链，待预检实证）
- 状态: built（本轮重建配方文件并新增mkfont NUL修复，本地门禁通过后工作树未提交，待 HMBS 真机预检与 rule4 门禁）

## 上游信息
- 软件：XGKS，ANSI Graphical Kernel System 的 level 2C 实现（IBM / 伊利诺伊大学，1989）
- 主页：http://xgks.sourceforge.net
- 打包参考：https://salsa.debian.org/science-team/xgks.git
- 版本映射：任务版本 `2.6.1-dfsg.2` 对应 Debian 归档名 `2.6.1+dfsg.2`（`+`/`-` 写法差异，内容同一）
- 源码包：xgks_2.6.1+dfsg.2.orig.tar.gz，1688680 字节，
  sha256 `451dd35080fd3e2fc1f5ed83b8b86e29c5ad0af2adf4c4d08ff13643ece641ab`
  （已用清华镜像下载全文验签，与 .dsc 记录一致；conandata 另列 deb.debian.org 官方源为首选）
- 源码结构：顶层 `src/` 下含 configure（autoconf 2.13 生成）、port/（udport 可移植库 + fortc 生成器）、
  lib/c（C 库：core + cgm + gksm + x 驱动）、lib/fortran（Fortran 绑定）、
  lib/iso-c（ISO C 绑定草案头）、progs/（演示程序）、fontdb（Hershey 字体库）、doc（troff 文档）

## 编译步骤

配方实际执行的步骤（真机 conan create 内）：

```bash
sh ./configure --prefix=/usr            # cwd=src，conanbuild 环境提供 CC/FLAGS 与 X11 路径
make -j1 misc/all fortc/all             # cwd=src/port：libudport.a + fortc 脚本
make -j1 c/all                           # cwd=src/lib：libxgks.a（含 cgm/gksm/x 子目录）
make -j1 mkfont r.gksfont ... G.gksfont  # cwd=src/fontdb：字体数据（显式目标，避开数字 symlink）
# 不执行 make install：package() 显式拷贝 libxgks.a、libudport.a、
# 头文件（include/xgks.h、include/xgks/、include/cgm/、include/udport/）、
# 字体库（lib/xgksfonts + 数字别名文件拷贝）、COPYRIGHT 到 licenses/
```

产物布局对标 Debian（libxgks-dev + libxgks2-data 的文件清单，减去 Fortran 与演示二进制）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游有无自动化测试 | 698 条目审计：无 tests/ 目录、无测试框架；唯一的 test 目标是交互式 X11 演示；Debian 打包明示禁用测试 | status:no_tests，MANIFEST 写 manual_audit 口径，test_package 做 MO 工作站消费者验证（6 项） |
| 2 | Fortran 绑定无法构建 | OHOS 无 Fortran 编译器且制品仓无预编译包（知识 E109） | 只构建 C 子集；lib/fortran、Fortran 演示（star/gksdemo）与 fortc 无关部分全部跳过 |
| 3 | 旧 Makefile 不支持 DESTDIR，fontdb 写死相对 prefix | 1990 年代构建系统（Debian 自带 destdir.patch，不在 orig 包内） | 不调用 make install，package() 显式拷贝；首轮不手写补丁（R3：补丁须来自真实构建编辑，真机失败再按需生成） |
| 4 | 旧 autoconf 在 OHOS/HMDFS 上的经典三坑 | 同年代 autoconf 通病（libx11/1.8.13 已实证） | 沿用三件套：umask 077→022、bash shebang 改 hnp 路径、conftest stdin 重定向改文件参数，均为 strict=False 尽力修复 |
| 5 | fontdb 数字别名 1-9 是 symlink | HMBS symlink 能力未必可用 | 构建时用显式字体目标避开 ln；打包时用文件内容拷贝生成别名 |
| 6 | Windows 本机无法验证 | 本机为 Windows，conan/OHOS 工具链只在真机 | 本轮只交未提交工作树；一切结论以 HMBS 真机预检日志为准 |
| 7 | 2026-10-15 preflight compile fail: X11/X.h not found in cgm/cgmi.c via Xlib.h | CPP_X11 only had -I<libx11>/include; X.h lives in xorgproto package | v4-v7 aggregates transitive X header closure into CPP_X11 + CFLAGS 双通道，并直引 xorgproto/2025.1；本轮日志证明已生效（失败点从 cgmi.c 后移到 xcolours.c） |
| 8 | 2026-10-15 preflight compile fail: xcolours.c:523/525 error passing 'XcMap' to 'XcMap *'，44 warnings + 2 errors，make[2] xcolours.o Error 1 | 上游1989年K&R代码笔误：XcMap_enter首参为 XcMap*，但XcInit两处传入 ws->XcMap 结构体值；clang16+将incompatible-pointer作为硬错误（旧gcc仅警告）。另同文件 XcMap_enter 内 map->GKSindexes[pixel]=index 在TrueColor下pixel远超length会越界写 | 新增 patches/0001（Debian xcolours.patch 移植：ws->XcMap→&(ws->XcMap) 两处；GKSindexes[pixel]→[index]并删越界assert）+ patches/0002（Debian gcc-14.patch xopws单hunk移植：XCreateWindow 的 &wk->vinfo 加 (Visual*) 强制转换，同类clang硬错误、同一C子集，防下一轮复现）。Fortran侧hunk超出C子集不引入；44个implicit-int仍为警告不阻断 |
| 9 | 2026-10-16 preflight compile fail: fortc Couldn't find macro file .../harmonyos.m4，make[1] gerhnd.o Error 1（xcolours/xopws已过，构建推进到lib/c） | fortc按OPSYS（uname -s小写）选宏文件：master.mk以$(FORTC) -O $(OS)调fortc，OS=@OPSYS@；真机uname得harmonyos，但上游仅带linux.m4等（2000年后无更新）；与X头/指针两轮无关的新失败域 | 配方build()在apply patches后把src/port/fortc/linux.m4拷贝为harmonyos.m4（Linux兼容的Fortran改名：小写+下划线，见linux.m4 NAMEF；X路径外唯一OS相关点）。不改OPSYS全局值、不新增补丁文件；m4缺失暂无证据，缺时再补tool_requires |
| 10 | 2026-10-16 preflight compile fail: src/port/fortc/fortc[103] can't create /tmp/fortc57803_1: Read-only file system，make[1] gerhnd.o Error 1（harmonyos.m4已过，构建推进到同一gerhnd.fc转换） | fortc生成器硬编码/tmp做中转（上游1990年代脚本），真机/tmp只读（HMBS诊断readonly_tmp）；HMBS已注入每任务可写TMPDIR | 配方build()新增_fix_fortc_tmpdir：沿用已探测SHELL顺带重定向fortc shebang；仅把fortc内/tmp/根目录替换为当轮TMPDIR绝对路径（无TMPDIR时回退${TMPDIR:-/tmp}），mkdir建目录并同步TMP/TEMP；不删逻辑不改口径 |
| 11 | 2026-10-16 preflight compile fail（同一指纹第2次）: fortc[103] can't create /tmp/fortc52379_1，make c/all在gerhnd.o中断（build目录路径.../p/b/.../b/src/port/fortc/fortc） | 首轮只补了source树configure前单文件且仅匹配/tmp/；执行副本在build树或configure重生成致补丁未命中（os.environ亦未必 carries HMBS注入） | 改不同策略：补丁覆盖source+build双树fortc/fortc.in及同目录含/tmp文件、匹配裸/tmp、configure后与make间幂等重打、TMPDIR经conan conf兜底解析、make命令显式前缀TMPDIR/TMP/TEMP |
| 12 | 2026-10-16 preflight compile fail（同一链第3次）: fortc[103] can't create /storage/.../runtime/xgks-*/storage/.../runtime/xgks-*/storage/.../tmp/fortc53949_1: No such file or directory（三重嵌套，make c/all在gerhnd.o中断） | _fix_fortc_tmpdir在build()内被调3次（configure前/后、lib/c前），但HMBS tmpdir本身以/tmp结尾；无幂等保护的text.replace("/tmp",tmpdir)会把已注入路径尾部的/tmp再次展开，逐轮叠加成2重/3重嵌套，目录不存在致fortc中转文件创建失败 | 加already-patched守卫：当文件已含本轮tmpdir绝对路径或${TMPDIR}回退时跳过/tmp替换（同tmpdir下后两次调用变no-op，仅shebang仍可修）；删掉错误的“单遍不递归故安全”注释，docstring记录三重嵌套教训 |
| 13 | 2026-10-16 preflight compile fail（同一链第4次，新失败域）: fortc[103]: m4: inaccessible or not found，make c/all在gerhnd.o中断（tmpdir三重嵌套已消，fortc -O harmonyos已正常启动） | fortc是sed+m4生成器，harmonyos.m4/tmpdir两关已过才暴露下一依赖：HMBS conanbuild PATH无m4（HMBS_BUILD_TOOLS仅列cmake/make/ninja/python3）；与前三轮的tmpdir字符串展开无关，是新失败域 | 新增build_requirements: tool_requires("m4/1.4.19")（仓内已OHOS构建版本）；make均已用env=conanbuild故PATH自动带m4，不改fortc调用逻辑 |
| 14 | 2026-10-16 preflight compile fail（同一链第5次，新失败域）: input.c 5 errors non-void function should return a value（XgksIProcessXEvent:209、XgksIDevDisable:367/374、XgksIDevEnable:463/471），make[1] input.o Error 1（gerhnd/m4已过，构建推进到lib/c input.o） | 1989年K&R函数无声明类型即隐式int，但三函数全用裸return且从不返回值；clang将-Wreturn-type作硬错误（旧gcc仅警告）。与m4/tmpdir无关的新失败域；调用方全作语句调用、无返回值使用、无extern原型冲突 | 新增patches/0003：三函数定义前加void、static DisCount补int（裸return在void中合法）；不加-Wno-return-type掩盖，不改调用逻辑 |
| 15 | 2026-10-16 preflight compile fail（同一链第6次，同类新位置）: prmgr.c 2 errors non-void function 'XgksProcessPrimi' should return a value（:215/:218两处裸return），make[1] prmgr.o Error 1（input.o已过，构建推进到lib/c prmgr.o） | 同0003的K&R隐式int+裸return在clang下为硬错误，但位置是新文件；上一轮0003本身有效（构建已从input.o推进到prmgr.o），不是假设错误，而是同类缺陷在全树扩散。逐文件打补丁会陷入多轮循环，故本轮改不同验证手段：对57个lib/c源文件做裸return全树扫描 + 逐函数体brace配对核对（纯裸return vs 混合返回值）+ 调用方返回值使用核查 | 新增patches/0004（7个hunk，一次覆盖当前及后续同类失败点）：prmgr.c XgksProcessPrimi加void；segments.c XgksOutputSeg/XgksRenameWsSeg补static void、XgksReDrawSeg加void；transforms.c XgksUnpendPendingTrans/XgksUpdateWsClip/XgksWsWinInterset加void。7函数经brace配对验证体内只有裸return、无return <值>混用，调用方全为语句调用、无头文件原型；其余裸return（act_ws/open_ws/已声明void函数、xtext.c TDEBUG守卫）不动。补丁已对debian orig包解压树git apply --check验证干净应用 |
| 16 | 2026-10-16 preflight compile fail（同一链第7次，segments.o 352 warnings + 2 errors；prmgr.o已过）: 摘要省略了2个error原文。上一轮0004的void路线对prmgr有效，但把void直接加在“同TU先调用后定义”的函数上会引入第二类硬错误conflicting types（先前的隐式int声明与void定义冲突），且无参K&R函数（def后直接跟{）漏过了上一轮的扫描启发式 | 本地复现路线（与上一轮不同的实现路线）：pip装ziglang取其clang做等效编译。复现树=orig包+0001~0004，-I与真机一致，X11用类型级stub、真机warning级诊断（implicit-int/implicit-decl/non-prototype）降为warning。复现出真机2错误：①XgksAppendSegClip:2297裸return（上一轮扫描漏网：def行`XgksAppendSegClip()`后无K&R参数声明行）；②XgksReDrawSeg:2402 conflicting types（1944/2275先调用形成隐式int声明，与0004的void定义冲突）——第②个是0004自身引入的。同文件审计确认OutputSeg/RenameWsSeg/Primi/input三函数无同TU前置调用，无需前置声明；transforms三函数均有前置调用（124/142/594/738），同样需前置声明 | 修订patches/0004为10个hunk：保留原7个void声明，新增segments.c文件头void XgksReDrawSeg();前置声明、XgksAppendSegClip加void、transforms.c文件头三函数void前置声明。复现树重打补丁后本地门禁：全lib/c共57文件（top+cgm+gksm+x）在真机诊断级别映射下零硬错误（umalloc.c另在aarch64-linux-musl目标下验证为零错误，其sigset系Windows目标产物，非真机问题） |
| 17 | 2026-10-16 preflight失败（补丁应用阶段，非编译）：conan apply_conandata_patches拒收0004（`source file is different - src/lib/c/transforms.c`，actual `b'/*'`），build()第537行直接报错。上一轮10-hunk版0004本地git apply --check全过、且旧7-hunk版曾在真机成功应用（含同文件多插入hunk的偏移自适应），故conan解析器行为与git不同：新版唯二的结构 novelty 是含空行上下文的插入hunk（segments S0、transforms T0），其中S0所在segments.c通过、唯T0所在transforms.c被拒 | 改混合路线（与上一轮“全放补丁”不同的策略，onedpl/2022.12.0先例：解析器拒收→配方内源码编辑）：0004瘦身为8个单行void hunk（去掉S0/T0两个前置声明插入hunk；新版经严格字节级核对：hunk计数与文件行号精确匹配，且不含任何空行上下文），4个void前置声明改由conanfile.py source()经replace_in_file注入（锚点均为文件内唯一出现，strict=True缺失即大声失败）。复现树按真实顺序（source编辑→0001~0004）验证：git全应用成功，zig-clang等效门禁segments/transforms/prmgr零硬错误 |
| 18 | 2026-10-16 preflight失败（补丁应用阶段，非编译，同指纹第2次）：conan apply_conandata_patches仍拒收0004（`source file is different - src/lib/c/transforms.c`，actual `b'/*'`），build()第571行直接报错。上一轮混合路线（0004瘦身为8个无空行单行hunk+4声明移入配方）本地git apply --check全过但真机解析器仍拒收，证明conan解析器对transforms.c的容忍度与git不同——继续调补丁字节是重复已失败策略 | 换不同路线（与上一轮不同的实现路线，onedpl/2022.12.0先例全量应用）：删除patches/0004并移除conandata登记，8个void定义+4个前置声明全部经conanfile.py source()内replace_in_file完成（_fix_void_returns_and_decls），10锚点已在orig包解压树逐个验证唯一出现；0001-0003保留（解析器接受）。本地复现树验证10处替换各命中1次、conanfile可compile |
| 19 | 2026-10-16 preflight新失败域（补丁应用已过，构建推进到fontdb）：mkfont.c:370 error: incompatible pointer to integer conversion assigning to 'char' from 'void *'（sp[strlen(sp)-1] = NULL），make mkfont.o Error 1。lib/c（含全部void修复）已编译通过，0001-0003解析器通过，证明上一轮全转配方编辑路线有效；本轮是新文件新错误，与解析器无关 | 沿用配方内源码编辑（不再新增补丁文件以绝解析器风险）：在_fix_void_returns_and_decls追加mkfont.c替换（NULL→NUL字符，sp为char *，注释past the space & null佐证意图），锚点在orig包唯一出现；全树扫描同类sp[/=NULL写法仅此一处。本地验证11锚点各命中1次、conanfile可compile |
| 20 | 2026-10-16 preflight新失败域（mkfont.o编译已过，卡fontdb链接）：`@CXX@ -o mkfont -stdlib=libc++ -std=c++17 -O3 mkfont.o ...` + `/bin/sh: @CXX@: inaccessible or not found`，`make: *** [Makefile:394: mkfont] Error 1`。上一轮mkfont NUL修复有效（构建从mkfont.o编译错误推进到mkfont链接错误），不是假设错误；本轮是1991年configure无C++探测（无AC_SUBST(CXX)）导致fontdb/Makefile残留字面量@CXX@，与之前void/NULL两类clang硬错误无关 | 改文件文本路线（与之前源码语义修复不同的实现路线）：configure后新增_fix_unsubstituted_cxx，把source/build双树下所有含字面量@CXX@的生成Makefile替换为与toolchain一致的CXX（_compiler_executable("cpp","clang++")，幂等、无占位符则留原文件）；CUSTOMIZE同步加CXX=c++兜底。规则用字面量@CXX@而非$(CXX)，故make命令行覆盖变量够不着，必须改文件 |
| 21 | 2026-10-16 preflight新失败域（编译/打包已过，卡package_info校验）：`ERROR: package_info(): The direct dependency 'xorgproto' is not used`（@CXX@链接修复后构建与打包均已成功：`Package ... created`，仅最后的元数据校验失败）。上一轮@CXX@文件文本路线有效（构建从fontdb链接错误推进到打包完成），不是假设错误 | 改打包元数据路线（与上一轮构建期文件修复不同的策略）：package_info的cpp_info.requires追加`xorgproto::xorgproto`（与requirements直引对应；xorgproto为header-library无libs但仍须声明消费关系，否则Conan 2硬校验失败）。不降级为transitive、不删依赖 |
| 23 | 2026-10-16 preflight新失败域（主包编译/打包已过，卡test_package链接）：`ld.lld: undefined symbol: gerrorhand`（act_ws.o + 391 more）与 `undefined symbol: gerlog_`（gerhnd.o），`make test_xgks Error 1`。上一轮test_package工具链修复有效（本轮已越过cmake.configure进入链接），不是假设错误 |
 src/lib/c/gerrorhand.c存在但Makefile.in的csrcs/LIBOBJS遗漏该文件，`make c/all`从不编译它；gerhnd.fc经fortc生成的gerhnd.o调用FC_NAME(gerlog)（linux/harmonyos下即gerlog_），两者上游均由lib/fortran/error.fc提供（经REMOTE_LIBRARY并入同一libxgks.a）。C-only子集跳过Fortran目录故归档缺这两符号；直接编Fortran的error.fc会连带error_lun/getlunname/inquire_lun.f等Fortran运行时，不适用无Fortran编译器的OHOS |
 配方build()在`make c/all`后新增_complete_c_only_error_objects：用同目录make后缀规则编漏掉的gerrorhand.c（复用精确CC/CFLAGS/CPPFLAGS），另生成纯C垫片hmbs_gerlog_shim.c提供gerlog_/gerlog__（经同errfp全局直调C的gerrorlog，忽略LUN，与上游gerlog语义一致），再用ar/ranlib并入lib/c/libxgks.a；不碰Fortran目录、不改测试口径 |
| 22 | 2026-10-16 preflight新失败域（主包编译/打包已过，卡test_package）：`CMake Error: CMAKE_C_COMPILER: /data/service/hnp/bin/clang`损坏导致`cmake.configure()` Error 1（上一轮package_info补xorgproto声明有效：本轮日志已越过该校验进入test_package，与元数据无关的新失败域） | 改消费者工具链路线（与上一轮主包元数据修复不同的策略，复用xmhtml/1.1.10 test_package范式）：test_package改显式generate()——CMakeDeps + CMakeToolchain(cache_variables重写CMAKE_C/CXX_COMPILER为实际存在编译器，仅OHOS) + 生成后回写conan_toolchain.cmake双保险 + VirtualRunEnv显式生成；编译器解析沿用主配方同款conf存在性检查+PATH回退 |

## 源码修改

- patches/0001-xcolours-xcmap-pointer.patch（bugfix，Debian xcolours.patch 移植）：src/lib/c/x/xcolours.c 两处 XcMap_enter(ws->XcMap,…)→(&(ws->XcMap),…)；XcMap_enter 内 GKSindexes[pixel]→[index] 并删除 assert(pixel < length)（BlackPixel/WhitePixel 在 TrueColor 下可远超 map->length，-DNDEBUG 下原代码越界写）。
- patches/0002-xopws-visual-cast.patch（portability，Debian gcc-14.patch 中 xopws.c 单 hunk 移植）：src/lib/c/x/xopws.c 中 XCreateWindow 的 &wk->vinfo→(Visual*)&wk->vinfo，消除同类 incompatible-pointer 硬错误（X 路径不被 MO 消费者测试执行，仅保编译通过）。
- patches/0003-input-void-return.patch（portability，clang -Wreturn-type 硬错误修复）：src/lib/c/input.c 中 XgksIProcessXEvent/XgksIDevDisable/XgksIDevEnable 定义前加 void（全用裸 return 且调用方均不取返回值、无 extern 原型冲突），static DisCount 补 int。
- 配方 source() 内 _fix_void_returns_and_decls（portability，onedpl/2022.12.0先例的解析器拒收退路，替代已删除的 patches/0004）：经 replace_in_file 完成 12 处编辑——8 个纯裸 return K&R 函数定义前加 void（prmgr.c XgksProcessPrimi；segments.c XgksOutputSeg/XgksRenameWsSeg 为 static void、XgksAppendSegClip/XgksReDrawSeg；transforms.c XgksUnpendPendingTrans/XgksUpdateWsClip/XgksWsWinInterset）+ 4 个同TU前置声明（segments.c 插 void XgksReDrawSeg();、transforms.c 插三函数 void 前置声明；调用点 segments.c 1944/2275、transforms.c 124/142/594/738，否则隐式int声明与void定义冲突）；10 个锚点均为 Debian orig 包内唯一出现（已用解压树逐个计数验证），strict=True 缺失即大声失败。
- 0001-0003 保留为补丁（解析器可接受，真机已证明通过对应编译单元）；已删 patches/0004 并移除 conandata 登记，manifest.yaml patches_applied 同步为 3 项。
- 配方 source() 内追加 fontdb/mkfont.c:370 修复（portability，clang -Wint-conversion 硬错误）：`sp[strlen(sp) - 1] = NULL;`→`sp[strlen(sp) - 1] = '\0';`（sp 系 `char s[80], *sp`，存 NUL 终止符为原意；全树同类赋值仅此一处）。

## 依赖版本

- libx11/1.8.13（X11 头文件与链接；仓库已有同版本配方，发布状态待预检侧复核）
- xorgproto/2025.1（直引：X.h/Xfuncproto.h/Xdefs.h；钉住与libx11一致版本）
- m4/1.4.19（构建工具：fortc生成器需m4；仓内已OHOS构建，经build_requirements/tool_requires引入）
- 系统 libc 的 stdio/stdlib/string/math（-lm 随 cpp_info.system_libs 声明）

## 验证结果

```bash
# 待 HMBS 真机预检回填（conan create + test_package 6 项 + 上游 no_tests 标记）
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libxgks.a | C 库静态库（core + cgm + gksm + x） |
| lib/libudport.a | 可移植支撑库 |
| include/xgks.h、include/xgks/、include/cgm/、include/udport/ | 公开与支撑头文件 |
| lib/xgksfonts/ | Hershey 字体库 + 数字别名（含 XGKSFontDir 运行机制） |

## 注意事项

- MO（metafile output）工作站是唯一无需 X 显示的验证路径；X 窗口类功能在无显示真机上无法执行，不纳入断言。
- 编译进库的默认字体路径是 /usr/lib/xgksfonts（--prefix=/usr 的 Debian 布局），运行时一律用 XGKSFontDir 指向包内 lib/xgksfonts（与上游演示程序的用法一致）。
- fortc 实为 sed+m4 脚本（pre1/pre2/m4/common+OS/post）：2026-10-16第4轮真机证实缺m4（fortc[103]: m4: inaccessible or not found），已补tool_requires("m4/1.4.19")；此前“m4是否存在待确认”已关闭。
- 若 configure 硬性要求 Fortran 编译器（UC_PROG_FC 在无 FC 时报错），下一轮改传 FC=true 并保持 C 子集构建（已预留该退路，见本表第 2 项）。
