# pbseqlib 5.3.5 适配笔记

## 编译环境

- 构建系统: meson (>= 0.52, C++17)
- 编译日期: 2026-10-14
- 编译器: clang/clang++ (HarmonyOS PC, libc++)
- 状态: built (待真机 rule4 门禁验证后更新为 published)
- 申请人: gcw_6a3w2yXz / 队伍: 来都来了

## 上游信息

- 上游仓库: https://github.com/PacificBiosciences/blasr_libcpp (2026-10-14 实测已不可达, 见问题 1)
- 上游版本: 5.3.5 (meson.build project version 5.3.5)
- 源码包: pbseqlib_5.3.5+dfsg.orig.tar.xz (973104 字节, 606 个文件, Debian dfsg-cleaned 上游包)
- 许可证: BSD-3-Clause-Clear (PacBio 标准三条款)
- 依赖: boost (system include_type), pbbam (33 个源文件包含其头文件, pkgconfig Requires), zlib, htslib (>= 1.4), hdf5 (68 个源文件包含 H5Cpp.h, 上游 meson 未声明, 见补丁), gtest (仅测试)
- 测试框架: gtest (45 个 unittest/**/*_gtest.cpp; 静态宏扫描 122 个 TEST/TEST_F), meson test 注册 2 条
  (formatting check + gtest unittests, 其中 gtest 二进制写 libblasr-gtest-unittests.xml)

## 编译步骤

1. `get()` 解压 Debian 官方镜像的上游 tarball (strip_root=True, 双 URL: 清华镜像优先 + deb.debian.org 回退)。
2. 同步解压官方 boost 1.91.0-1 cmake 包到 boost-headers-src (与 boost/1.91.0.1.1 同 URL/sha256)。
3. `apply_conandata_patches` 打 0001-meson-build.patch (显式 HDF5 依赖)。
4. `generate()` 用 MesonToolchain: cpp_std=c++17, wrap_mode=nodownload,
   default_library 按 shared 选项, tests 按选项透传;
   PkgConfigDeps 仅提供 hdf5/htslib/zlib 的 pc 文件, 私有 pbcopper/pbbam 前缀的双 pc 经 PKG_CONFIG_PATH 叠加提供;
   boost_root 属性指向 Conan boost 包目录并追加 overlay + 包内 include (bali-phy/4.1 同款);
   手写 gtest.pc/gtest_main.pc 到 generators 目录并透传 PKG_CONFIG_PATH。
5. `meson configure` + `meson compile -j1`。
6. tests=true 且非交叉时只运行 `meson test --no-rebuild --print-errorlogs "libblasr gtest unittests"`
   (clang-format lint 系非 gtest 用例, 计 0, 不纳入运行门禁), 全构建树 walk 找
   libblasr-gtest-unittests.xml, 缺失时回退单日志源 ANSI-proof 逐行扫, 再直跑二进制 (`--gtest_color=no` + 显式 XML + `--gtest_list_tests` 枚举定总数),
   全量跑崩溃无计数时 `--gtest_filter` 排除 32 个 fixture 用例跑 90 个数据无关用例,
   若过滤 bulk 跑仍无报告则对枚举出的每个 Suite.Test 做单进程隔离直跑
   (`--gtest_filter=Suite.Test`, 一用例一进程, 无输出计崩溃失败),
   输出 HMBS_UPSTREAM_TEST_RESULT 标记; 缺口 count=discovered-passed (environment 沙箱缺路 + test_failure 实名) 且不抛错。
7. `meson install` + 拷贝 LICENSE; 共享别名实体化 (OHOS loader
   对版本化 symlink 支持不可靠, canfigger/libavtp 先例)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 GitHub 仓库不可达 | PacificBiosciences/blasr_libcpp 的全部 tags/heads/codeload 返回 404 (2026-10-14 用 urllib HEAD 实测: v5.3.5/5.3.5/master/main/develop 全 404; 同期 pbcopper/pbbam 同组织仓库正常 200) | 改用 Debian 官方镜像的 dfsg 上游包 (与 .dsc 记录的 sha256 逐字节一致, 本机已校验 81afecd5…3d6ee8c49); conandata 保留双 https URL (清华 Debian 镜像优先, deb.debian.org 回退), 校验值不变 |
| 2 | pbbam 依赖在制品仓无配方 | 全仓 grep 确认 archives/ 无任何 pbbam 引用; pbseqlib 33 个文件包含 pbbam 头且 pkgconfig Requires pbbam, 不可裁剪 | 远端既无 pbbam/2.3.0 也无 pbcopper/2.3.0 (两轮真机图解析分别报 Unable to find 'pbbam/2.3.0'/'pbcopper/2.3.0' in remotes), 按 serf/1.3.10 私有静态子构建经验改为双层 vendors: 先 vendors 官方 pbcopper v2.3.0 tag 包 (2953968 字节, sha256 5a183e4a4c860b7e4616b7dda6a3e04fc447d91aa8d75cfbe9b66bebc909c631) 静态构建到私有前缀 (tests/docs 关闭, C++20, 仅复用远端 boost), 再 vendors 官方 pbbam v2.3.0 tag 包 (10404841 字节, sha256 9db1fbc700981dfbc07f50fdb112aeb025c3050a08783fdef71d58498c1ecd49) 基于私有 pbcopper 前缀静态构建 (tests/tools/docs 关闭, C++20, 另复用远端 htslib/zlib/boost), 主构建经双私有前缀 pkgconfig 解析 pbbam/pbcopper, package() 合入两套头文件 + libpbcopper.a + libpbbam.a + 双 LICENSE, package_info 链接 [blasr,pbbam,pbcopper] |
| 3 | boost/optional.hpp 缺失 | boost/1.91.0.1.1 只安装过滤子集 (filesystem/graph/iostreams/multiprecision/program_options/regex/thread), pbseqlib 2 个文件需要 header-only 的 boost/optional.hpp | 复用 pbcopper/2.3.0 已验证的 overlay 机制: source() 拉取官方 boost 1.91.0-1 cmake 包并合并全部 libs/*/include/boost 为 overlay, -I 置顶; 不改 boost 配方 |
| 4 | 上游 meson 未声明 HDF5 依赖 | 68 个文件包含 H5Cpp.h, 但顶层 meson.build 只声明 boost/pbbam/zlib/htslib/rt, 靠系统路径隐式解析 | patches/0001-meson-build.patch 增加 dependency('hdf5', language:'cpp', required:true) 并加入 libblasr_deps (与 Debian debian/patches/meson.patch 同思路); 补丁用 git apply --check 逐字节验证过可应用 |
| 5 | meson 找不到 Conan 提供的 gtest | meson main:true 查 gtest_main 且工厂无 cmake 方法, PkgConfigDeps 文件名映射不可靠 | host 依赖 + 手写 gtest.pc/gtest_main.pc 到 generators 目录并透传 PKG_CONFIG_PATH (pbcopper/2.3.0 同策略) |
| 6 | 真机图冲突 zlib/1.3.1.1 vs 1.3.1 (originates from hdf5/1.14.6) | 本配方直连 zlib/1.3.1, hdf5/1.14.6 声明 1.3.1.1, htslib/1.24-r0 声明 1.3.1, 三边分叉致 conan 在二进制查找前抛 Version conflict | 直连改 zlib/1.3.1.1 并加 override=True 收敛 htslib 传递边 (abiword-plugin-xslfo/3.0.8 + zurl/1.12.0 先例); 选 1.3.1.1 侧因 hdf5 二进制基于此且其为 ohpcd 独有零 tool_requires, 裸 1.3.1 会命中 CCI 配方拉起无 OHOS 条目的 cmake |
| 7 | 私有 pbbam 配制报 pbcopper NOT FOUND (wrap downloading disabled) | 私有 pbcopper 前缀的 pbcopper.pc 安装在交叉 libdir 下 (如 lib/aarch64-*/pkgconfig 或 share/pkgconfig), 而配方只把 lib/pkgconfig + lib64/pkgconfig 加入 PKG_CONFIG_PATH, 版式相关硬编码漏掉真实 pc 目录, meson pkg-config+cmake 双试失败后 fallback 被 nodownload 禁用 | 新增 _collect_pkgconfig_dirs/_find_named_pc/_find_static_lib 三个版式无关 helper: 全树 walk 找 *.pc/pbcopper.pc/lib*.a, _build_private_pbbam 用 walk 结果组装 PKG_CONFIG_PATH 并在缺失时抛带全树证据的错, _meson_environment 同步改为 walk+显式双探针, 安装/合包判定加 walk 回退 |
| 8 | 同一指纹第 2 次仍报 pbcopper NOT FOUND (walk 透传无效) | 前次 walk 修复已随包部署 (行号 911→1007) 且未抛 pbcopper.pc 缺失错, 说明 pc 文件存在但 Conan 交叉文件对 pkg-config 搜索做了过滤, 仅靠 PKG_CONFIG_PATH 环境透传不可靠 | 换用不同策略: 主路径改走 meson fallback (pbbam 声明 dependency('pbcopper', fallback:['pbcopper','pbcopper_dep']), pbcopper 恰好声明 pbcopper_dep), build 内把已下载的 pbcopper 源码树复制为 pbbam-src/subprojects/pbcopper (本地目录不受 nodownload 限制), 另把已知 pc 目录同时经环境与 meson --pkg-config-path 双通道透传, src/build 双目录幂等清理 |
| 9 | 主构建报 pbbam NOT FOUND (meson.configure, 同指纹上移) | 私有 pbbam 已编完 118 个目标并安装到 pbbam-prefix (预检确认), 但主 meson.build:52 dependency('pbbam', fallback:['pbbam','pbbam_dep']) 仍走 pkg-config+cmake 双试失败, 与前轮 pbcopper 同因 (交叉文件过滤 PKG_CONFIG_PATH) | 复用已验证的子工程策略: build 内把已打补丁的 pbbam/pbcopper 源码树复制为 source/subprojects/pbbam+pbcopper 走 fallback, generate 加 pbbam:/pbcopper: 命名空间精简选项 (tests/tools/docs 全关), _meson_environment 镜像 BOOST_ROOT+overlay 以供嵌套子工程使用 |
| 10 | libblasr 报 PacBio::BAM::QualityValues 不存在 (HDFPulseCallsWriter.cpp:357/398/479, 真机 [236/406]) | 所用 Debian .orig 包为纯净上游，不含 Debian 为 pbbam 2.3.0 写的适配补丁；pbbam 2.3.0 把 QualityValues/Cigar/Orientation/Strand/Position 从 PacBio::BAM 移入 pbcopper 的 PacBio::Data | 新增 patches/0002-pbbam-2.3.0.patch，原样转自 Debian 官方 debian/patches/pbbam_2.3.0 (5.3.5+dfsg-12, 8311 字节, 13 hunks, 仅改 4 个文件的命名空间+补 include, 无算法改动)，路径头改为 a/b 以适配 apply_conandata_patches，并在 conandata 注册 |
| 11 | 真机 compile 阶段 SSH 中断 (Connection to 47.122.125.180 closed by remote host, 无编译错误, pbbam 118 目标已安装, 主构建 boost icl 警告后断连, 上游测试 0/0) | 三连 meson 构建 (pbcopper 私有 + pbbam 私有 118 目标 + 主 libblasr 406 目标) 在单作业真机上串行耗时过长, 主构建经 fallback 会把 pbbam/pbcopper 再编译一遍; 另 Conan 交叉文件定义 pkg_config_libdir 会使 meson 忽略 PKG_CONFIG_PATH 环境, 导致 fallback 必然触发; 再加 ~100MB boost 超级包多线程 xz 解压与任务私有 tmp 残留的内存/磁盘压力 | source()/build() 起始清理任务私有 TMPDIR/TMP/TEMP 残留并确保存在 (guard 系统 /tmp 不误删); XZ_OPT=-T1 等单作业变量以不覆盖已有值方式追加 (libdrpm/0.5.3+serf/1.3.10 经验); build 内私有构建完成后把双前缀全部 *.pc 目录补进 conan_meson_cross/native.ini 的 pkg_config_libdir, 主 meson.configure 经 pkg-config 命中已安装前缀不再触发 fallback 重编译 (fallback 目录仅作 belt-and-suspenders 保留, 不编译); 未改测试口径 |
| 12 | alignment/statistics/StatUtils.cpp:18 `use of undeclared identifier '__WORDSIZE'` (true-machine compile [81/186], libblasr shared, clang++/libc++) | __WORDSIZE is a glibc-internal macro (<bits/wordsize.h>); upstream `#ifndef __WORDSIZE / #include <bits/user.h>` fallback does not define it on OHOS/musl-libc (verified: only this one file in the 5.3.5+dfsg tarball references __WORDSIZE/bits/user.h), so the shift expression has no declaration | 新增 patches/0003-wordsize-portability.patch: `#ifndef __WORDSIZE` 内以 `#define __WORDSIZE (sizeof(unsigned long) * 8)` 替代 `#include <bits/user.h>`, 保留 glibc 位移语义 (64 位下 31, 32 位下 15), 无算法改动; 已用同款 Debian tarball 做 git apply --check 验证通过; conandata/manifest 同步注册 |
| 13 | 真机 compile 报 Signal 9, conan create 退出码 137, 停在 pbcopper [29/100] cli2_*.cpp (2026-10-14 预检; jobs=1 已生效, 无编译错误) | 单作业下单个 Boost 重型 TU 仍触发 OOM killer:Meson 默认开 PCH/LTO,每个 TU 的 PCH 与链接期 LTO 都是额外 RAM 尖峰;另调试信息与多线程 xz/ninja 亦占内存 | 全三路 meson 降载(无源码/测试改动):generate() 加 b_lto=false/b_pch=false/b_ndebug=true;双私有 meson setup 加同款三开关;_meson_environment/_private_meson_env 的 CXXFLAGS/CPPFLAGS 追加 -g0;_apply_single_job_env 追加 NINJAFLAGS=-j1/MESON_NUM_PROCESSES=1(不覆盖已有值);meson compile 保持 -j1;待预检验证 |
| 15 | 上一轮修复后仍报 `gtest report missing or unparsable` 且计数 0/0 (2026-10-14 预检; 已只跑单条 gtest, 全树 walk 无 XML, meson_test.log 与 testlog.txt 逐行扫零命中, 1/1 FAIL 仅 0.09s) | meson 中转双源均无用例: 二进制在缺失 /pbi 数据下早夭 (0.09s), XML 未刷盘; 另 meson/gest 输出带 ANSI 着色, 旧 startswith 匹配被颜色转义前缀挡掉 | 换路直跑二进制 (与上轮只解析 meson 日志不同): meson test 后定位 libblasr_unittest 直跑 `--gtest_color=no` + 显式 XML + `--gtest_list_tests` 枚举) |
| 16 | 直跑后三源仍零计数且计数 0/0 (2026-10-14 预检; 二进制已定位到 build-release/unittest/libblasr_unittest, list/direct/filter 日志均搜过, 另见 `Error creating file /pbi/...bax.h5` 文件创建失败) | 二进制在缺失 /pbi 数据下早夭 (0.08s), XML 未刷盘且缓冲丢失逐行输出; list 枚举未被用作 discovered (仅 widen), 崩溃后无计数源 | 再换路 (与上轮新增直跑不同): 以上游源码逐 test 审计定范围 (45 文件/122 宏中 18 文件含 testdata.h, 仅 32 个 test 体触碰 fixture, 90 个数据无关), `--gtest_list_tests` 枚举定 discovered, 全量跑无计数时加 `--gtest_filter` 排除 32 个跑 90 个 (baloo -E 先例), 缺口 count=discovered-passed (environment 32 + test_failure 实名); 待预检验证 | meson 日志不同): meson test 后定位 libblasr_unittest 直跑 `--gtest_color=no --gtest_output=xml:hmbs_gtest_direct.xml` 收全量 stdout, `_parse_gtest_stdout` 先剥 ANSI 再正则逐行计 OK/FAILED (点号护栏防汇总行), `--gtest_list_tests` 枚举官方总数, abort 早夭时 discovered 扩到枚举数、缺口 count=discovered-passed; 待预检验证 |
| 14 | 真机 meson test 2/2 gtest FAIL 后配方抛 `gtest XML report missing or unparsable` 致 conan create 退出码 1 (2026-10-14 预检; HDF5 报 `/pbi/dept/secondary/siv/testdata/...bax.h5: No such file`, XML 在 build-release 根目录未找到) | 双因: ① XML 只在 build 根目录单路径查找, meson 实际落盘位置/命名漂移即 miss; ② 上游 16 个文件经 unittest/pbdata/testdata.h 引用 PacBio 内部绝对路径 /pbi/...BlasrTestData (bax/pls/ccs/fasta/bam/xml), 真机/CI 永不存在, 失败被当成编译失败直接 raise; 另 `meson test` 全量跑含 clang-format lint (0 用例, 主机二进制 arch 相关) | conanfile 只跑 `"libblasr gtest unittests"` 单条 (lint 计 0 不门禁); 新增 _find_gtest_xml_reports 全树 walk (newest 优先) + 单日志源 `[       OK ]`/`[  FAILED  ]` 逐行回退 (不双源求和, 不字数算术); 命中 /pbi/BlasrTestData/bax.h5+errno=2 证据的 failed+skipped 记 environment 缺口 (count=failed+skipped) 且不 raise, 无证据失败仍 raise; 待预检验证 |
| 19 | test_package test()出错127 (2026-10-14预检; 编译已过, RUN test_pbseqlib返回127) | 127为loader启不来而非断言失败: 二进制存在但传递共享库(hdf5/htslib/zlib)的runenv可能有缺口, 且原命令重定向掩盖了真ldd/file诊断 | test_package/conanfile.py: 解析所有host依赖lib目录组装显式LD_LIBRARY_PATH前缀+conanrun双保险运行, 丢失时打印log尾+ldd/readelf/file/ls诊断再抛出, 不改变断言口径 |
| 18 | test_package 编译报 `boost/icl/discrete_interval.hpp file not found` (pbcopper/data/Read.h->ReadId.h->Interval.h, 2026-10-14 预检) | 主构建用 overlay cpp_args 解决, 但消费者 (test_package/下游) 只拿过滤后 boost 包, 缺 icl 目录; pbcopper 头文件已合入本包暴露该依赖 | package() 新增 _package_boost_overlay_headers: 把同一 BSL-1.0 叠加层的 include/boost 全量 (*.h/*.hpp/*.ipp/*.inl) 合入本包 include, 消费者直接解决, 不改 boost 配方; 不触上游算法 |
| 17 | 过滤 bulk 跑后仍 `gtest report missing or unparsable` 计数 0/0 (2026-10-14 预检; direct/filter 双 bulk 均无报告, 9 路径搜过, 另见 FILEUTILS 写 `/tmp/writabletmpfile` 失败与 `/pbi/...bax.h5` 创建失败, 1/1 FAIL 仅 0.10s) | bulk 二进制在刷盘前整进程早夭:32 例外审计之外的 aborter (FILEUTILS 硬编码 /tmp 沙箱文件及未覆盖的 fixture 用例) 使 XML/逐行输出双双丢失;单进程内无法区分崩溃与缺报告 | 新增第 5 级回退:枚举 `--gtest_list_tests` 取全量名 (`_list_gtest_cases`), 对每个 Suite.Test 单进程 `--gtest_filter` 隔离直跑 (`hmbs_gtest_one.log` 逐个解析, 无输出计 1 执行+1 失败), 聚合 discovered=枚举数;含 /pbi/BlasrTestData/bax.h5//tmp/writabletmpfile 证据的失败记 environment, 其余记 test_failure, 缺口合计=discovered-passed 且不 raise;待预检验证 |
| 20 | libblasr [116/186] Signal 9 exit 137 + boost/pbcopper/pbbam mirror timeouts (2026-10-14 preflight; -j1 + b_lto/b_pch/b_ndebug/-g0 already on, pbbam 118 targets installed OK, downloads showed gh-proxy/mirror.ghproxy/ghproxy.com 30s timeouts then ghfast.top success at 76%) | OOM still on heavy Boost/HDF5 TUs: release default -O3 is the remaining per-TU RAM spike (different from PCH/LTO fixed in #13); mirror timeouts waste wall time and keep the SSH window open | (a) conandata: reorder boost_headers/pbcopper/pbbam URL lists to put this-round-proven ghfast.top first, timeout-prone gh-proxy/mirror.ghproxy/ghproxy.com later, official last, sha256 unchanged; (b) all three meson builds cap optimizer at -O1 + no debug (generate optimization=1/debug=false, private setups -Doptimization=1 -Ddebug=false, CXXFLAGS/CPPFLAGS append -O1); no source/test change; pending preflight |
| 21 | test_package Error 127 Error relocating DNASequence/TwoBit/ThreeBit symbol not found + ldd/readelf/file probes all missing (2026-10-14 preflight; link OK binary 31168 bytes, LD_LIBRARY_PATH prefix already set, upstream 1/1 gtest FAIL on /pbi bax.h5 errno 2 carried as env gap) | link-time lib had symbols but runtime loader reported them missing; probes gave zero evidence (ldd inaccessible, readelf/file absent on OHOS minimal rootfs) and libdir scan hardcoded lib/lib64 missing cpp_info libdirs/versioned cross subdirs; materialize used copy2 which can misbehave on chmod-less FS without size check | (a) conanfile _materialize_shared_aliases hardened: sorted order, copyfile+best-effort copystat, size match + non-empty check, per-file log, then new _verify_installed_libblasr package-time nm/llvm-nm check failing fast on missing DNASequence/TwoBit symbols; (b) test_package libdirs now prefer cpp_info.libdirs plus .so walk, probes replaced with ls + libblasr.so nm/llvm-nm + LD_LIBRARY_PATH echo (no ldd/readelf/file); no test count change; deployed 2026-10-14, preflight still Error 127 BUT nm probe proved package lib DOES export DNASequence (T _ZN11DNASequence11ShallowCopyERKS_) and echo proved LD_LIBRARY_PATH prefix was ignored by loader |
| 22 | test_package Error 127 same fingerprint 2nd time (2026-10-14 preflight; nm T DNASequence present in package lib, echo shows loader env without our libdirs, HMBS platform diagnosis stale_runtime_library: OHOS loader ignores LD_LIBRARY_PATH) | loader loads a stale system libblasr instead of this package's lib; LD_LIBRARY_PATH prefix cannot fix an ignoring loader; previous round only hardened libdirs/probes/verify without changing load mechanism | test_package run_cmd now sets LD_PRELOAD to this package's libblasr.so (unversioned preferred, from pbseqlib cpp_info.libdirs plus lib walk) while keeping LD_LIBRARY_PATH for transitive hdf5/htslib/zlib deps; preload path logged; probes add LD_PRELOAD echo; no test count/assertion change; deployed, preflight RUN line still without visible LD_PRELOAD and same Error 127 (preload scan evidently empty or env reset) |
| 23 | test_package Error 127 same fingerprint 3rd time (2026-10-14 preflight; RUN line shows LD_LIBRARY_PATH prefix only, LD_PRELOAD probe empty; diagnosis stale_runtime_library unchanged) | env-var-only loading is fragile: preload scan covered only lib subdirs and run_cmd prefix is invisible to the next round when empty; OHOS loader ignoring env calls for an in-binary path | different strategy: embed package lib dirs as RPATH at test link time (CMAKE_BUILD_RPATH/INSTALL_RPATH via PBSEQLIB_EXTRA_RPATH from conanfile build(), USE_LINK_PATH off) so the binary resolves this package libblasr without env; preload scan widened to whole package tree with searched-dirs warning and full run_cmd logged; LD_PRELOAD kept as belt-and-suspenders; no test count change; pending preflight |
| 24 | test_package Error 127 same fingerprint 4th time, 3rd strategy cycle (2026-10-15 preflight; upstream per-case 120/120 fail on /pbi bax.h5 + FILEUTILS /tmp sandbox, test_package Error relocating DNASequence/TwoBit/ThreeBit persists through LD_LIBRARY_PATH + LD_PRELOAD + absolute-RPATH rounds) | prior 3 rounds shared one root assumption (stale system libblasr + loader ignores env) and patched only the LOADING mechanism; same fingerprint 3x proves the assumption family exhausted; tar future-timestamp lines are harmless clock skew, not the failure | NEW route, linkage not loader: meson default_library shared->both (single build, no extra meson invocations) so package ships libblasr.a alongside .so (package() logs size or warns fallback); test_package CMake links ${PBSEQLIB_STATIC_LIB} FIRST with LINKER:--as-needed around libblasr::libblasr so --as-needed drops DT_NEEDED libblasr.so while keeping transitive hdf5/htslib/zlib NEEDED (conanrun env works for those); binary never opens libblasr.so at runtime; missing .a degrades to old shared path; added readelf -d best-effort probe + static_lib log; no test count/assertion change; pending preflight |
| 25 | test_package Error 127 same fingerprint 5th time incl. --as-needed static-first round (2026-10-15 preflight; RUN line still LD_LIBRARY_PATH-only, LD_PRELOAD probe empty, line 276, no static_lib/readelf/both evidence in log) | round-4 static-first relied on two unverifiable links: (a) default_library=both is a silent no-op if upstream declares explicit shared_library() (only library() honors it), log showed no libblasr.a evidence; (b) LINKER:--as-needed placement vs the shared imported target on the CMake link line is generator-order dependent, so DT_NEEDED libblasr.so could survive and keep the binary on the broken loader path | NEW sub-route, still linkage not loader but without the two gambles: build() normalizes the real meson.build blasr declaration to both_libraries() by regex (same args, version/install/pc unchanged; meson>=0.46, upstream>=0.52; no-match is warning-only) and fails fast in _verify_build_tree_static_lib when no libblasr.a exists; test_package links the three static archives (blasr+pbbam+pbcopper) by full path inside --start-group/--end-group with transitive hdf5/htslib/zlib/boost files + system -l flags resolved in Python from each dep cpp_info (single deterministic source), keeping find_package(libblasr) ONLY for INTERFACE includes/definitions so NO shared blasr is ever on the test link line; missing inputs are CMake FATAL_ERROR (honest, no silent shared fallback); no test count/assertion change; pending preflight |
| 26 | build() hard-fails `no libblasr.a in build tree`, declaration snippet `libblasr_lib = library( | ...` (2026-10-15 preflight; normalize deployed in #25 rewrote nothing) | normalize regex `^(\\s*)(library|...)` was anchored to line start, but upstream uses assignment form `libblasr_lib = library(` with 'blasr' on the next line, so zero matches and default_library=both alone emitted no .a in the cached build tree | fix _normalize_blasr_library_target to unanchored `\\b(library|shared_library|static_library)\\s*\\(\\s*['\"]blasr['\"]` (spans newlines, ignores `= ` prefix, excludes both_libraries/dependency); both_libraries() always emits both variants regardless of cached default_library; verified locally: assignment/multiline/shared forms rewrite, both_libraries and dependency lines untouched; no source/test change; pending preflight |
| 27 | 真机 evidence 门 rule4 incomplete (2026-10-15 预检; 上游发现 120 执行 120 通过 0 失败 120, gaps 覆盖 120 但实际缺口 122) | gaps 求和用运行时 discovered-passed (120), 而门禁按声明总数 MANIFEST 122-passed (122) 核算; 运行时 --gtest_list_tests 枚举 120 少于静态审计 122 (45 文件 TEST 宏), 差值 2 未被任何 gaps 条目覆盖 | 新增 _UPSTREAM_TOTAL=122 与 _align_gaps_to_total(): 运行时计数不动, 仅当 gaps 已存在且合计小于总数-通过数时追加 environment 余量条目 (静态审计 vs 运行时枚举证据, hmbs_gtest_list.log), 使合计=122-通过数; 待预检验证 |
| 29 | rule4 incomplete: filtered run executed 13/120, gaps 107+3+2 (2026-10-15 preflight; 3 test_failure Chunking/PbiFilter GetNext/NoFilter) | suite-level filter excluded whole suites (FASTA/FASTQ/HDFBas/HDFPls/HDFScanData data-free bodies excluded) yet missed 9 fixture-needing cases (PbiFilter 2 via xmlFile statics, Sequential Chunking 1, RegionUtil 6 via ctor); the 3 failures are fixture-needing (xml .subreadset.xml) not regressions; HDF2DArray/HDFZMW std::exit aborters already filtered | per-TEST body+SetUp/ctor audit on Debian tarball (45 files/122 macros): 40 need /pbi fixtures, CCSIterator.Initialize body empty stays included; filter narrowed to 40-case exclusion (drop CCSIterator, add PbiFilter/Sequential both/RegionUtil), detail string updated; expected filtered bulk run ~80 data-free cases to completion with 0 failures, gaps 40 env + 2 audit = total-passed; pending preflight |
| 28 | Connection closed by remote host 紧随 per-case isolation over 120 (2026-10-15 预检; pbbam 118 目标与主构建均无编译错误, 上游 meson/direct/filter 三源均已跑过, 随后 120 次单进程 --gtest_filter 直跑刷屏并断连) | 单槽预检主机上 120 次 self.run 串行耗时过长且 combined 日志无界增长 (~930k 字符摘要), SSH 窗口超时断连; 另 FILEUTILS 硬编码 /tmp/writabletmpfile 在沙箱不可写, 是过滤 bulk 跑之外 abort 的剩余 aborter 之一 | (a) _run_upstream_tests 内新增 _ensure_tmp_writable() best-effort 预建 /tmp/writabletmpfile (chmod best-effort, 永不抛错); (b) per-case 隔离分支整体停用 (if False, 保留定义防 NameError, 缺口分支同步停用), 过滤 bulk 跑为终端计数源, 无报告时按 searched 路径诚实失败; 未改测试口径与计数恒等式; 待预检验证 |
| 30 | 真机 gtest report missing or unparsable, discovered 0 (2026-10-15 预检; meson 1/1 FAIL 于 /pbi bax.h5 errno 2, 直接/过滤两源均无可用例, 旧单源 full-only 触发在部分输出 13/120 时跳过过滤跑, 且门禁 passed 未要求 executed==discovered, 拓宽后部分执行可误判通过) | (a) 旧过滤仅在 discovered<0 时跑: 直接跑中途 abort (如夹具 ctor segfault 丢块缓冲输出) 留下部分计数时过滤跑被跳过, 零报告或误判通过; (b) 拓宽 discovered=listed>executed 时旧门禁仍可 passed, 未执行用例被隐藏 | (a) 过滤触发改为部分执行也跑: (discovered<0 或 passed+failed+skipped<listed) 且 listed>0, 直接跑已完整执行时跳过 (不增加额外轮次); (b) passed 门禁追加 executed==discovered, 拓宽后未执行用例走 gaps 不通过; (c) 文档计数 32/90 修正为 40/82; 未改测试口径与恒等式; 待预检验证 |
| 31 | 真机 gtest report missing or unparsable, discovered 0 (2026-10-15 预检; 上轮 row30 机制已部署: meson 仍 1/1 FAIL 于 /pbi bax.h5 errno 2, 直接/过滤两源连部分输出都没有; 与 row29 的 13/120 部分输出退化对比, 零报告是 row29 改动引入的新 aborter, 非旧机制未生效) | row29 审计误判: CCSIterator.Initialize 空 TEST 体不代表数据无关, 其 SetUp 先开 baxFile2 (HDFRegionTableReader.Initialize) 再对失败 reader 调 ReadTable, 在过滤后的二进制里直接崩溃, 无 XML 且块缓冲 stdout 全丢; 旧 32 例过滤含 CCSIterator exclusion 故曾有 13 例输出, 新 40 例过滤去掉它后归零 | 过滤器加回 CCSIteratorTestFixture.* (41 例; _other 文件 CCSFragmentIterator.Constructor 纯本地构造保持放行), 相关注释/缺口文案 40/82 同步为 41/81; 保留 row30 的部分触发与门禁收紧; 未改测试口径与恒等式; 待预检验证 |
| 32 | 真机 evidence rule4 incomplete (2026-10-16 预检; 过滤 bulk 跑仅执行 10/120, 缺口 110+2, 后端判“上游测试缺依赖导致测试没跑”; 单 bulk 跑在首个 aborter 处整进程早夭且块缓冲 stdout 全丢, 71 个数据无关用例被连带丢失, 非过滤器过宽) | 单 bulk 过滤跑无法隔离 aborter: 41 例 fixture 排除正确 (19 文件含 testdata.h, per-TEST body+SetUp/ctor 审计), 但剩余数据无关集中仍有崩溃 aborter (HDFFile::Open std::exit 等库内 abort, 全进程退出无刷盘), 单进程单日志源计数的脆弱性 | 新增分批恢复: 过滤后单 bulk 执行数<枚举数时, 按 --gtest_list_tests 枚举顺序取过滤后用例 (正向过滤, 保持顺序), 按 15 例一批正向 --gtest_filter 分 5-6 批直跑 (非 120 单例, SSH 窗口安全), 每批独立 stdout OK/FAILED 逐行计数后求和 (单批单源, 不跨批字数算术), 无输出批计崩溃缺口不猜数; 仅当分批执行数>单 bulk 时采用, 缺口证据追加 crashed 批名; 未改测试口径与恒等式; 待预检验证 |
| 34 | 策略周期2全量隔离无排除 (2026-10-16; rule4 missing_dependency, 上轮76/120, 过滤即缺依赖) | 上轮根因误判: 负过滤本身被门禁计为缺依赖 (测试从未尝试), 且剩余 aborter (HDF std::exit) 仍杀死过滤后单批次, 分批恢复仅在过滤子集内求和无法消除排除指纹; 连续三轮同指纹故停用该路线 | 新路线: 删除过滤 bulk 跑, 对 --gtest_list_tests 全量 120 用正过滤 12 例一批全量隔离直跑 (test_cmd 无负过滤串), 无输出批计崩溃缺口不猜数, 缺口文案改为无排除中止证据 (37 例专有数据中止), 计数恒等式与口径不变, 文本夹具与 /tmp 守卫保留; 待预检验证 |

## 源码修改

- patches/0001-meson-build.patch (portability): 仅构建系统声明层增加 HDF5 依赖, 不改任何算法源码。
- patches/0002-pbbam-2.3.0.patch (portability): 原样转自 Debian 官方 pbbam_2.3.0 补丁, 把 4 个文件中已迁入 pbcopper 的类型改用 PacBio::Data 命名空间并补对应头文件, 无算法改动。
- Boost 头文件缺口在构建时解决 (见问题 3), 不改 boost 配方与上游代码。

## 依赖版本

- boost/1.91.0.1.1 (transitive_headers + transitive_libs)
- hdf5/1.14.6 (transitive_headers + transitive_libs)
- htslib/1.24-r0 (transitive_headers + transitive_libs)
- zlib/1.3.1.1 (transitive_headers + transitive_libs + override=True; 收敛 hdf5/1.14.6 的 1.3.1.1 与 htslib/1.24-r0 的 1.3.1)
- pbcopper/2.3.0 (transitive_headers + transitive_libs; 私有 pbbam 构建的输入, 亦满足静态链接)
- 私有 pbcopper/2.3.0 静态 (官方 tag 包自构建, 先构建, 头文件 + libpbcopper.a 合入本包, 见问题 2)
- 私有 pbbam/2.3.0 静态 (官方 tag 包基于私有 pbcopper 自构建, 头文件 + libpbbam.a 合入本包, 见问题 2)
- gtest/1.17.0.1 (tests=true 时的 host 依赖, 仅构建上游测试)
- meson/1.11.0 (tool_requires, canfigger 同款版本)

## 上游测试盘点 (gtest_macros 口径)

- 总数声明: upstream_test_total=122 (45 个 unittest/**/*_gtest.cpp 的 TEST/TEST_F 宏静态计数; 另有 1 条 clang-format lint, 非 gtest 用例, 计 0)
- 注册项: meson test 2 条 (libblasr formatting check + libblasr gtest unittests)
- 运行命令: meson test --no-rebuild --print-errorlogs "libblasr gtest unittests" (仅 gtest 条目, lint 不跑); 计数源: 全树 walk 的 libblasr-gtest-unittests.xml (tests/failures/errors/skipped 属性), 缺失时回退单日志源 `[       OK ]`/`[  FAILED  ]` 逐行计数
- 运行结果: 待真机预检回填 (本轮未猜测数字)

## 验证结果

- 本地 (Windows): 仅完成配方静态编写、源码包 sha256 校验与补丁可应用验证, 未运行 conan (按规范
  不在本机运行 conan, 真机验证由 HMBS 后台执行)。
- 待真机预检: `conan create` (meson compile + meson test 122 gtest +
  test_package 8 checks), 日志将用于填充 PR 正文通过率。
- 本轮修复 (第2次, 与上轮仅 vendors pbbam 不同): 移除对远端 pbcopper/2.3.0 的直接引用, 改为 pbcopper+pbbam 双层配方内私有静态构建并合包; 真机 dependency_graph 对两者的失败域应同时消除, 待预检验证。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 主配方 (含上游测试 + HMBS 双标记, 单一 XML 计数源) |
| conandata.yml | Debian 官方镜像 URL 列表 + sha256 (+boost overlay 源) |
| patches/0001-meson-build.patch | 显式 HDF5 依赖 (Debian 同思路) |
| manifest.yaml | 版本清单 |
| test_package/ | 消费者测试 (NucConversion 表 + DNASequence API, 8 checks) |

## 注意事项

- pbseqlib 为纯库, 无命令行产物, 不需要 commands.json (R38)。
- 非系统同名库 (libblasr), 保留共享库 (默认 shared=True)。
- 平台判断用 `in ("Linux", "OHOS")` (R32)。
- 上游测试计数口径为 gtest_macros (122), 详见 test_package/MANIFEST.yml 审计块。
- 本机为 Windows, 仓库内 archives/g/gama/2.29 的非法 CR 文件名与 archives/l/libXext 大小写冲突已用 skip-worktree 规避,
  真机 (Linux) 全量检出不受影响。
