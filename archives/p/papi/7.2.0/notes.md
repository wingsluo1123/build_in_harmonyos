# papi 7.2.0 适配笔记

## 编译环境
- 构建系统: autotools（自定义 `src/configure` + make，非根目录 configure）
- 上游: https://github.com/icl-utk-edu/papi/releases/tag/papi-7-2-0-t（PAPI 7.2.0，2025-06）
- 源码校验: sha256 `a9bff89c…0af39c`，md5 `fc7f90ef8686d15261831fd35dfdbb1b` 与官方 release notes 一致
- 编译器: clang/clang++（真机 /data/service/hnp 工具链，待预检确认）
- 状态: 首轮工作树，未经真机验证（manifest 暂标 failed，验证通过后更新）

## 编译步骤

```bash
cd papi-7.2.0/src
sh ./configure --prefix=/ --disable-fortran --with-shared-lib=no --with-static-lib=yes
make -j1
make -C testlib -j1 && make -C validation_tests -j1 && make -C ctests -j1
# 上游 smoke 子集（纯查询，无需硬件计数器）
LD_LIBRARY_PATH=.:./libpfm4/lib ./version ./code2name ./eventname ./describe ./hwinfo ./cmpinfo
make install DESTDIR=<package_folder>
```

conanfile.py 中以上步骤均显式指定 `cwd=src`，编译器/标志来自
AutotoolsToolchain 聚合的 conanbuild 环境（无裸 `${CC}`，R33）。

## 上游测试盘点（manual_audit）

| 套件 | 数量 | 说明 |
|------|------|------|
| src/ctests/*.c | 116 | 含 burn、attach_target 两个 support 程序；run_tests_exclude.txt 另排除长耗时/MPI 项 |
| src/validation_tests/*.c | 36 | 含 *_testcode helper 对象；flops/cycles/cache 精度验证 |
| src/ftests/*.F | 22 | Fortran；`--disable-fortran` 未构建（OHOS 无 Fortran 工具链） |
| src/utils/*.c | 16 | 17 个 .c 减 print_header helper 按文件口径计 16（papi_avail/component_avail/native_avail/version 等查询工具；cost_utils 按文件计入，类比 validation helpers）；审查员实测 N=190 对齐 |
| src/components/*/tests | 86 | 绑定 CUDA/ROCM/infiniband 等硬件，harness 按 active components 过滤，本轮不计入总数 |
| **合计** | **190** | build() 执行其中 6 项纯查询 smoke，其余 184 以 gaps 上报（110+36+22+16=184=190-6） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不在归档根目录 | PAPI 自定义构建树，入口为 `src/configure` | conanfile 全程 `cwd=src` 显式驱动，不依赖 Autotools helper 默认路径 |
| 2 | 无 ctest/gtest 注册表可供计数 | 自研 harness（run_tests.sh 动态 find 可执行文件） | `upstream_test_count_method: manual_audit` + 源码清点表；标记计数恒等式由 build() 代码保证 |
| 3 | 绝大多数测试需硬件计数器 | overflow/profile/multiplex 系列依赖 perf_event_open 真实计数 | 仅 6 项纯查询进 build() smoke；其余记 ohos_feature gaps，待计数器硬件补测 |
| 5 | 真机 configure 重执行 bash 不可用（Error 127） | configure 内 autoconf 重执行逻辑选中 CONFIG_SHELL=/data/service/hnp/bin/bash，预检 worker 上该路径 inaccessible（./configure[159]），且原配方 sh 调用与 toolchain 参数旁路 | build() 内改用命令串内联 export CONFIG_SHELL/SHELL（conanbuild 作用域会覆盖 os.environ，前次 pin 无效，错误原样重现），经 _pick_configure_shell() 按 isfile+X_OK 探测后取首个可用（/bin/sh 优先，hnp bash 备选）并显式驱动 configure（HMBS 保证），显式 /bin/sh ./configure + env=conanbuild + umask 022；generate()/build() 补 --build/--host=aarch64-unknown-linux-gnu 绕过 config.guess（zzuf/0.15 先例）；package() 统一 umask+conanbuild |
| 9 | perf_event 编译报 unknown type __u32/__s32/__u16/__s16/__u8/__s8（2026-10-15 预检，perf_helpers.h 6 errors） | perf_helpers.h 直接 typedef 内核类型 __uXX，而 OHOS sysroot 经 sys/ioctl 链不提供 linux/types.h 定义；libpfm4 侧同名符号仅出现在 _IOW 宏内未展开 | build() 新增 _fix_perf_helpers_stdint（配方内源码编辑：__u32->uint32_t 等 6 处等宽替换 + 缺失时补 #include <stdint.h>，锚点缺失即大声失败；不新增补丁文件，不关组件） |

| 8 | make 报 #include OSCONTEXT/OSLOCK empty filename（2026-10-15 预检，-DOSLOCK="" -DOSCONTEXT=""） | PAPI 的 OS 变量取自 uname 而非 --build/--host 三元组；HarmonyOS 下 uname 命中 none 分支，OSLOCK/OSCONTEXT 留空（configure.in 以 OS 分支赋值，MAKEVER 回落 generic） | generate()/build() 在 OHOS 时追加 --with-OS=linux（映射到 linux-lock.h/linux-context.h 与 linux-memory/timer/common 源；--with-arch 仍取 uname -m=aarch64，不改测试口径） |

| 7 | config.status conf subs1.awk Permission denied (2026-10-15 预检，Error 1) | configure 内部 umask 077 + mktemp -d ./confXXXXXX 在 HMDFS 上留下 owner-unwritable 目录；命令串外层 umask 022 无法覆盖内部值，且 mktemp 目录后续不可写（HMBS unsafe_local_mktemp） | build() 新增 _fix_autoconf_umask（src/configure 内 umask 077->022，cyrus-sasl-scram 先例）+ HMBS_AUTOCONF_MKTEMP_FALLBACK=1 时 mktemp 垫片（./conf* 返回失败走 mkdir fallback，其余委托真实 mktemp，仅 configure 阶段前置 PATH）+ TMPDIR/TMP/TEMP 显式透传到 configure/make |

| 6 | GitHub 直连超时 + configure 报 C compiler cannot create executables（Error 77，2026-10-15 预检） | 下载：github.com 连接超时 30s 后重试才成功；编译：configure 回显 `checking for aarch64-unknown-linux-gnu-xlc... /data/service/hnp/bin/clang`（pinned $CC 泄漏进交叉探测）后 conftest 链接失败，与 ifplugd/0.28、zurl/1.12.0 指纹同构（pinned 绝对路径在部分 worker 上不可用，PATH 上有可用 clang） | conandata.yml url 改为有序列表（gh-proxy 镜像在前、官方 URL 保底回退，复用 ci/conan/build_and_test.sh 的 GitHub 映射，sha256 不变）；conanfile 新增 _resolve_compiler()（conf 路径 --version 实测可用则零改动，否则同目录兄弟→PATH clang 回退，仅覆盖 CC/CXX、不碰标志）+ configure/make 命令串内联 export CC/CXX（conanbuild sourcing 在 os.environ 之上，内联最近作用域才生效）+ configure 失败时转储 config.log 尾部供下轮取证 |
| 10 | utils 链接缺 libpfm OS 层符号 + Rules.pfm4_pe:45 libpfm.a Error 2（2026-10-15 预检，papi_avail undefined pfmlib_os_perf/pfmlib_os_perf_ext/perf_event_support/pfm_arm_get_perf_encoding 等，libpapi.a 仅含 6 个 pfmlib 对象） | 内嵌 libpfm4 的 config.mk 用 `uname -s` 判定 SYS，仅 SYS==Linux 才编译 pfmlib_perf_event*.c；HarmonyOS/HongMeng 下该层被跳过，但 pfmlib_common.c/arm_armv8.c 仍引用其符号；PAPI 的 --with-OS=linux 不透传（Rules.pfm4_pe 只转发 ARCH/CC，不转发 SYS） | build() 新增 _fix_libpfm_sys_linux（配方内编辑 src/libpfm4/config.mk：未知 SYS 统一 override 到 Linux，锚点缺失即大声失败；ARCH 仍由 PAPI/8uname -m 提供 aarch64，不改测试口径） |
| 11 | validation_tests 链接 R_AARCH64_ABS64 + 拆分后 libpapi 缺 pfmlib 对象（2026-10-15/16 预检：先 papi_ld_ins ABS64，后 papi_avail undefined pfm_* 且 ar 清单零 pfmlib 对象） | ABS64 因 load_store_testcode.c 绝对字面池需非 PIE；拆分 `make static/libsde/utils` 绕过 Rules.pfm4_pe 默认目标自举（PFM_OBJS 为空时首目标先建 libpfm 再递归），致 libpfm 未建 | 显式 `make -C libpfm4 -j1 lib` 先建内嵌库（ARCH 自检 aarch64、CC 走环境、SYS 已映射 Linux），再 `make static/shared libsde utils`，测试目录仍 LDFLAGS 追加 -no-pie，不跳过测试 |

| 4 | Windows 本机无法完整检出上游 main | `archives/g/gama` 含 `\r\r` 结尾文件名；`archives/l/libXext` 与 `libxext` 大小写冲突 | 本地稀疏检出排除以上两处（`core.protectNTFS=false`），仅影响本机工作树，不进版本内容 |

## 源码修改

无补丁（`patches: {}`）。configure 对 OHOS 的识别与组件自适应结果待真机预检确认后补。

## 依赖版本

无外部依赖（`dependencies: []`）。libpfm4 为源码内置（src/libpfm4）。

## 验证结果

```bash
# 待 HMBS 真机预检（conan create）回填：
# - HMBS_UPSTREAM_TEST_RESULT（build() smoke 子集，discovered=190）
# - HMBS_TEST_PACKAGE_RESULT（test_papi，discovered=5）
```

- 上游测试用例通过率：待真机 evidence 回填
- 新增测试用例通过率：待真机 evidence 回填

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libpapi.a（或 .so，视 shared 选项） | 主库 |
| include/papi.h 等 | 头文件 |
| bin/papi_*（15 个） | papi_avail、papi_native_avail、papi_version 等查询工具 |

## 注意事项

- PAPI 不是系统同名库，保留动态/静态选项（默认静态，减少首轮动态装载风险）。
- `PAPI_num_components() > 0` 断言依赖真机至少激活一个组件；若 HongMeng 内核无 perf 支持，该断言将如实失败并转入下一轮修复。
- test_package 另运行 `papi_version` 工具验证 bin/ 可用性。

| 12 | ctests overflow_pthreads 编译 Error 1（2026-10-15 预检：`myid[EventSet1] = PAPI_thread_id()` 报 int->pthread_t 指针转换硬错误，clang>=19 无 -Werror 也报错；另有 `(int) pthread_self()` 指针截断警告） | 上游按 glibc 假设 pthread_t == unsigned long，可直接存 PAPI_thread_id()（unsigned long）；OHOS/musl 下 pthread_t 为 struct __pthread*，赋值即硬错误，同类 idiom 遍布其余 ctests/validation 文件 | build() 新增 _fix_ctests_pthread_portability（配方内源码编辑：myid 类型改为 unsigned long〈仅 memset/赋值，#if 0 外无 pthread_* 用法，语义不变〉+ `(int) pthread_self()` 改为 `(unsigned int)(uintptr_t) pthread_self()` + 缺失时补 stdint.h，锚点缺失即大声失败）+ 测试目录 make 行追加 CC="<cc> -Wno-int-conversion -Wno-pointer-to-int-cast" 兜底（生成 Makefile 烘焙 CC 会覆盖环境，必须走 make 命令行覆盖；-no-pie 经 LDFLAGS 保留；不跳过任何测试） |
| 13 | make install 报 Error 64（2026-10-16 预检） | HMBS 能力 install_shim=true/chmod=0：多源 install 与 install -d 一律 EX_USAGE 64，裸 chmod 无 dash 前缀亦失败 | package 新增 install/chmod/ldconfig 垫片并 PATH 前置 + INSTALL 重定向，另加 Python fallback 兜底关键产物 |
| 14 | smoke 6 项全失败 Signal 11（2026-10-16 预检） | 待完整日志定位；先对齐 run_tests.sh 执行语义（cwd=src + LD_LIBRARY_PATH=.:./libpfm4/lib ./ctests/<name>），原 cwd=ctests 相对路径基准不同 | smoke 改为 src cwd 执行并逐项 warning 记录，不伪造通过 |
| 15 | test_package CMake 配置失败（2026-10-16 预检二轮：System is unknown to cmake + CMAKE_C_COMPILER 错误，cmake.configure Error 1） | CMake 无 Platform/HarmonyOS 模块，4.x 编译器检查在真机失败；test_package 仅需编译单个 C 文件，不必经 CMake 平台探测 | test_package 改 direct-cc（profile CC + conanbuild env + dependencies 头文件/库目录，-lm -pthread），保留 test_papi 标记与 papi_version 绝对路径执行；CMakeLists.txt 留存仅供结构检查 |
| 16 | smoke 仍 0/6 Signal 11（2026-10-16 预检二轮，前轮 cwd 对齐未生效） | 改用不同路线：-no-pie 原为 validation_tests ABS64 所加，却 blanket 施加到 ctests；OHOS 侧 PIE 为默认，6 个纯查询二进制无需该重定位修复，非 PIE 疑似触发加载期崩溃 | ctests 构建去掉 LDFLAGS -no-pie（仅保留 CC 警告抑制），validation_tests 保留 -no-pie；test_package 同样默认 PIE |
| 17 | test_package direct-cc 报 Error 127（2026-10-16 预检三轮：/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found） | direct-cc 沿用了 profile 钉死的绝对 CC，主包同指纹曾报 Error 77；test_package 语境下该路径在部分 worker 不可达，而上一版无回退直接使用 | test_package 新增 _resolve_cc：pinned 先 --version 实测，可用则零改动，否则同目录兄弟→PATH clang 回退，最终裸 clang 走 conanbuild PATH；仅覆盖 CC，不碰标志 |
| 18 | smoke 三轮 0/6 Signal 11（前两轮 cwd 对齐与 PIE 收敛均无效） | 改用第三条路线隔离环境与库：前两轮均导出 LD_LIBRARY_PATH=.:./libpfm4/lib（照抄 run_tests.sh 共享库语义），而 smoke 链接 ../libpapi.a 为静态，该共享路径非必需且是混杂预加载候选 | smoke 去掉 LD_LIBRARY_PATH 直接 ./ctests/<name> 执行，并先跑 utils/papi_component_avail 与 papi_version 做 triage（同为库 init 路径），区分库范围崩溃与用例特异失败；标记仍如实 test_failure |
| 19 | test_package direct-cc 编译 Error 1（2026-10-16 预检四轮：`const char *v = PAPI_version()` 报 int-to-pointer -Wint-conversion 硬错误；`PAPI_shutdown() != PAPI_OK` 报 void-vs-int 非法操作数） | test_papi.c 误假设了不存在的 `const char *PAPI_version()` 字符串接口与 `int PAPI_shutdown()` 返回值；上游 src/papi.h 实为 `void PAPI_shutdown(void)` 且无 PAPI_version（版本为 `PAPI_get_opt(PAPI_LIB_VERSION,NULL)` 返回的 `PAPI_VERSION_NUMBER` int，见 src/ctests/version.c 与 src/utils/papi_version.c） | test_papi.c 改用 `PAPI_get_opt(PAPI_LIB_VERSION,NULL)` + `PAPI_VERSION_MAJOR/MINOR` 判 7.2.x，shutdown 改为 void 直接调用；MANIFEST/manifest 断言数 9→7（version 3→2，shutdown 1→0）；与 smoke 崩溃无关的独立根因 |
| 20 | smoke 连续三轮 0/6 Signal 11（cwd 对齐、PIE 收敛、去 LD 路径均无效，属第 4 策略周期） | 重读 src/run_tests.sh：harness 自身以 `utils/papi_component_avail` 是否含 Active perf_event 为门禁，不满足则跳过全部 ctests/validation_tests/ftests；本配方无条件强跑 6 项纯查询 smoke，可能跑了 harness 会跳过的子集；且三轮均只记 test_failure、无组件证据，无法区分“库 init 在无计数器 VM 上崩溃”与“用例特异失败” | 本轮不改执行环境（cwd=src、ctests 保持 PIE、无 LD 导出维持原样）：triage 改为捕获 `papi_component_avail` 输出到日志并解析 Active perf_event，marker 新增 perf_active 归因分支（inactive→ohos_feature 附 triage 证据，active→test_failure）；执行计数与 gaps 总和恒等式不变，不跳过任何测试 |
| 21 | test_package 可编译但运行即 Signal 11，且 triage 的 ohos_feature 归因失实（2026-10-16 第 4 轮预检：test_papi 仅打印首行即 Error 139；`papi_component_avail` triage 日志仅有 Signal 11、无组件列表，却被记为“perf_event 未激活”） | 上轮归因逻辑错误：triage 二进制自身崩溃时输出无 perf_event 字符串，旧代码仍置 perf_active=False 并伪造组件证据；另所有二进制（triage+6 smoke+test_papi）在 `PAPI_library_init` 内同状崩溃，指向某组件初始化而非单个用例，但无二分证据；test_papi 缺 fflush 使崩溃点被缓冲掩盖 | 本轮改走组件二分新路线：triage 仅在成功且解析到 Active 块时才置 True/False，崩溃时置 None（unknown）并如实记 test_failure；新增 `_run_component_probes`（单探针链接 ./libpapi.a，逐个 `PAPI_disable_component_by_name` 后 init，三轮运行均捕获不中断构建）；test_papi 加 fflush 与 init 前后标记以精确定位下轮崩溃点 |

| 22 | smoke/triage/test_package 全链路 Signal 11，且组件二分探针自身亦崩溃（2026-10-16 第 5 轮预检：disable=[perf_event/uncore] 三轮均 Signal 11，无 post-disable 标记） | 前四轮（cwd 对齐、PIE 收敛、去 LD 路径、组件二分+归因）沿用同一“perf_event 在无计数器 VM 上 init 崩溃”假设且无堆栈证据；二分调用的 PAPI_disable_component_by_name（init 前）自身可能触碰未初始化全局，且第三组件 sysdetect 从未覆盖 | 本轮改走崩溃定位新路线：停用 disable 二分，新增 _run_crash_probes（nolink 空二进制证 exec 正常→linkonly 链接 libpapi.a 但零 PAPI 调用辨构造/加载期崩溃→SIGSEGV-handler 包裹 PAPI_library_init 辨 init 内崩溃（exit 42）+ gdb batch 兜底）；执行环境零 churn，不改测试口径 |
| 23 | 全链路 Signal 11 且 handler 探针 exit 42（2026-10-16 第 6 轮预检：triage/smoke/test_papi 均崩溃，probe segv caught in/after init） | 前 5 轮均为执行环境 churn（cwd/PIE/LD/归因/二分/探针），从未触碰库源码；本轮重读上游源码定位 init 内必经路径：_pe handler 证实在 init 同步崩溃（非 loader），sysdetect init 为空返回，perf_event 各错误分支均为优雅 disable，唯一无保护的解引用是 src/linux-common.c decode_cpuinfo_arm() 的 `t=strchr(s,'('); tmp=*(t+2)-'0'`（Processor/model name 回退）；HongMeng /proc/cpuinfo 无 Linux 括号形式时 strchr 返回 NULL 即 SEGV，崩溃点在 _linux_get_cpu_info→_linux_get_system_info→_papi_hwi_init_os，早于任何组件 | 新路线：配方内源码加固（_fix_linux_common_arm_cpuinfo，正则覆盖 2 处回退点，加 NULL/长度/isdigit 守卫，Linux 语义不变，缺括号时优雅跳过；锚点缺失即大声失败）；执行环境零改动，不跳过任何测试 |
| 24 | paren 守卫后仍全链路 Signal 11（2026-10-16 第 6 轮预检后复盘：6 smoke + triage + test_papi 同状崩溃，handler exit 42） | 第 6 轮锚点 `t=strchr(s,'(')` 实际位于 `if (cpuid_family<0)` 死分支内（strtol("8")/AArch64 永不为负），HongMeng 上根本不执行，故守卫零效果；重读 init 必经链 `_papi_hwi_init_os→_linux_get_system_info→_linux_get_memory_info→aarch64_get_memory_info→generic_get_memory_info`（每次 aarch64 init 必跑）发现 src/linux-memory.c 有两处无保护崩溃：(a) cache sysfs 缺失时 `opendir==NULL→goto unrecoverable_error→closedir(NULL)` 即 SEGV（HongMeng VM 隐藏 /sys cache 节点）；(b) `level_index=level-1` 无界，level 0/超大即 L[-1]/越界写；另 linux-common.c 尾部 MIPS 块 `strstr(s," V")+2` 无 NULL 守卫，同帧可崩 | 新路线：配方内加固同帧两处（_fix_linux_memory_sysfs：opendir 失败早返 levels=0 不 close、error 标号 close 加 NULL 守卫、size/line/assoc/sets/level 置零初值、level_index 越界 continue；_fix_linux_common_mips_cpu_model：cpu model 缺失/" V" 缺失时跳过而非解引用；Linux 语义不变）；保留第 6 轮 paren 守卫；执行环境零改动，不跳过任何测试 |
| 25 | 真机 6/6 全绿仍判 incomplete：rule4“passed 状态与上游结果矛盾”（2026-10-16 预检：discovered 174 / executed 6（当时声明 174，本轮按审查员实测纠为 190） / passed 6 / failed 0 / skipped 0 却标 passed） | 内存/sysfs 加固后崩溃已修复（6 smoke + 5 test_package 全过），但 _emit_upstream_marker 沿用“failed==0 即 passed”旧语义：executed(6)!=discovered(190) 时标 passed 自相矛盾（ifopt/2.1.4 同指纹 1/2 标 passed 被打回；idsgrep/0.6、libngf/0.28、libm2k/0.9.0、vibecheck/1.7.7 均在有 gaps 时用 incomplete） | 只改状态语义不改执行/计数：failed>0 或 executed==0 或 infra 为 failed；executed!=discovered 为 incomplete（含 reason“6/190、0 失败、非 100% 故 incomplete”）；仅全量时为 passed；gaps 保持 110+36+22+16=184=190-6 不变，构建不 raise |
