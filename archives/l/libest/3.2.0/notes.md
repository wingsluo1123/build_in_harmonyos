# libest 3.2.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, libtool)
- 适配日期: 2026-10-18
- 编译器: clang（HarmonyOS PC aarch64 真机工具链，待 HMBS 预检实测）
- 状态: built（首轮工作树，待真机验证后按实测更新）

## 上游信息
- 上游仓库: https://github.com/cisco/libest
- 上游版本: 3.2.0（Release 3.2.0，tag r3.2.0，2020-07-06）
- 源码归档: https://github.com/cisco/libest/archive/refs/tags/r3.2.0.tar.gz
- sha256: 324b3a2b16cd14ea4234d75fa90f08b29509bac9cd3795c44268e22f906ee0ad（GitHub 官方归档实测）
- 许可证: BSD-3-Clause（LICENSE/COPYING，Cisco BSD 风格）
- 本版本主要新增（相对 1.0.0 时代）: OpenSSL 1.1.1 支持、仅客户端构建、服务端 keygen、BRSKI/EST over CoAP、增强证书认证（ECA）、事件回调

## 编译步骤（待真机执行）

```bash
# 配方构建（conan create 内执行）：
./configure --with-ssl-dir=<openssl 3.5.6.1 包目录> --enable-static --disable-shared --enable-brski
make -C safe_c_stub -j1   # 先构建内嵌 stub：src/est 链接 -lsafe_lib
make -C src -j1           # 再构建库本体（含 BRSKI，见问题 15）
make -C src install -j1   # 仅安装库本体（libest + include/est/est.h）
```

## 与 1.0.0 配方的差异
1. **依赖沿用 openssl/3.5.6.1**：制品仓已发布 OHOS 二进制版本（与 1.0.0
   已验证配方一致），直接命中预编译包；3.2.0 源码已含 HAVE_OLD_OPENSSL
   分支，仅需 0004-0006 移植 OpenSSL 3.x 余量修复（FIPS_mode/extern/attr释放）。
2. **构建顺序多一步 safe_c_stub**：3.2.0 新增内嵌 safe_c stub
  （safe_c_stub/lib/Makefile.am: noinst_LIBRARIES = libsafe_lib.a，非安装静态库），
   src/est 通过 -Lsafe_c_stub/lib -lsafe_lib 链接，必须先构建 stub。
3. **补丁共 6 个**：0001-0003 平台补丁（config.guess/config.sub/configure，
   逻辑与已验证的 1.0.0 补丁 0001-0003 相同，hunk 偏移按 3.2.0 源码重算）
   + 0004-0006 OpenSSL 3.x 余量修复（FIPS_mode→EVP_default_properties_is_fips_enabled、
   X509_ATTRIBUTE_free 双释放、clang -fno-common extern）。
4. **许可证与元数据修正**：1.0.0 配方 license 误标 MIT 且 homepage 为空；
   本版本按 LICENSE/COPYING 实测修正为 BSD-3-Clause，homepage 填上游仓库地址。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2014 版 config.guess 无 HarmonyOS 分支 | patches/0001：uname 为 HarmonyOS 时输出 <arch>-unknown-linux-ohos（沿用 1.0.0 验证逻辑） |
| 2 | config.sub 不接受 linux-ohos 三元组 | 无 ohos 内核系统名 | patches/0002：两处 linux-* 列表追加 linux-ohos* |
| 3 | configure 创建临时目录 Permission denied（预期） | HMDFS 平台 umask 077 临时目录组写被禁（1.0.0 E011/E052/E060/E112/E125 同类） | patches/0003：umask 077→002 |
| 4 | src/est 链接找不到 -lsafe_lib（预期） | safe_c_stub 为非安装库，需先构建 | conanfile build() 先 make -C safe_c_stub 再 make -C src |
| 5 | 真机 configure 报 C compiler cannot create executables（2026-10-18 预检，CC=/data/service/hnp/bin/clang） | 私有 `_configure_args` 透传丢失显式参数 + profile  stale SHELL/CONFIG_SHELL（HNP bash 不可执行）覆盖 conanbuild 聚合 + 缺少 config.log 证据 | bwm/0.6.3 模式：generate() 用 Environment 存 build-scope SHELL=/bin/sh + TMPDIR + CC/CXX 回退；build() 显式 `"$SHELL" ./configure --prefix --with-ssl-dir --enable-static`（R15 去 --build/--host，aggregate #34 去重），inline exports 在 conanbuild.sh 生效后覆盖；新增 _probe_toolchain（CC/clang/plain-cc/TMPDIR）与 _dump_config_log（12k tail + 编译段），_patch_autoconf_umask 覆盖全部 configure/config.status（含 umash 变体） |
| 6 | 真机 test_package 的 CMake configure 失败：`System is unknown to cmake, create Platform/HarmonyOS` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang is not able to compile a simple test program`（2026-10-18 预检；库本体已编译安装成功，失败点在 test_package 的 cmake.configure） | CMakeToolchain 把 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，但预检 cmake（stock 4.4.3）无 Platform/HarmonyOS 模块致 project() 失败；叠加 profile 固化的旧编译器路径在部分 HMBS 宿主缺失 | test_package generate() 显式 CMakeToolchain：os=OHOS 时 `CMAKE_SYSTEM_NAME=Linux`（earcut/3.2.3、easyloggingpp/9.97.1 在仓先例；HarmonyOS 与 Linux 同内核，本纯 C 消费者无平台分支，别名行为不变）+ `CMAKE_SYSTEM_PROCESSOR=<arch>`；编译器按 zydis/4.1.1 模式回退解析（conf 绝对路径优先，仅其缺失时 PATH/已知 SDK 目录找 clang/clang++ 并 pin cache + build-scope CC/CXX + 生成物文本替换，CI 有效路径不受影响） |
| 7 | 真机依赖图阶段 m4/1.4.19 构建失败：`configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`，Error 127（2026-10-18 预检；失败在 cunit 依赖链的 m4，而非 libest 本体） | test_requires(cunit/2.1-3) 在双 remote 预检宿主优先命中 conancenter，其 autotools 链（libtool/automake/autoconf/m4）在 profile CONFIG_SHELL 指向的 HNP bash 不可执行时必然失败；本配方 generate/build 的 SHELL 覆盖只影响本包，不影响外部依赖构建 | 改用 test_requires(cunit/2.1.3)（libcoap/4.3.5b 先例）：点版本仅存在于 ohpcd（在仓 CMake 配方），无 autotools 链、无 conancenter 碰撞，提供相同 -lcunit API；curl/8.15.0 已命中 ohpcd 二进制，保持不变 |
| 9 | 真机上游55套件 executed=0/passed=0（2026-10-19 预检，rule4 incomplete） | CUnit Basic Run Summary suites行Passed列恒为n/a（如 suites 36 36 n/a 0 0），旧解析器digits-only正则永不命中，恒返回None记executed=0；与runtest是否构建成功无关 | conanfile _parse改读n/a容忍的suites/tests行 + verbose Suite:/Test:...passed/FAILED分组计数（executed=observed，failed=含FAILED套件数），_save按36可运行子集+19个CoAP条件套件ohos_feature gaps诚实上报；已用合成CUnit日志自测（3套件/1失败分组正确，旧正则确认恒为None） |
| 8 | 真机上游55 个 CUnit 套件 executed=0/passed=0，runtest 未生成可执行文件(2026-10-19 预检) | 手写 Makefile 硬编码 CC=gcc+/usr/local* 默认路径 + 回退手工缺 -DHAVE_CUNIT/-I test/util/-ldl 及 tests行解析错配 | Strategy1 改为 make 命令行覆盖编译器/依赖目录 + ENABLE_BRSKI=1；Strategy2 补 defines/includes/ldflags；解析器改读 suites 行；CoAP 条件套件以 ohos_feature 报 gaps |
| 10 | 真机上游仍 0/55（2026-10-19 预检，rule4 incomplete，发现55执行0通过0跳过55） | Strategy2 的 `*.c + */*.c` glob 误收录 test/UT/US748/perftest.c（独立 perf 工具，自带 main 致 duplicate-main 链接失败）与 test/util/st_*_windows.c（需 windows.h，在 OHOS/Linux 编译失败）；Strategy1 make 失败时无日志留存，无法定位 | Strategy2 改为上游 Makefile SRC 显式清单（runtest.c + 52 个 US 套件源 + 6 个 test/util 非 windows  helper；perftest/US4747/windows 明确排除并注释依据），缺失文件如实 warning；Strategy1 make 输出重定向到 build_folder/libest_upstream_make.log 并在失败时打印 4k tail；_parse 同步容忍 suites 行 n/a 并按 verbose Suite:/Test: 分组计数 |
| 11 | 上游真机仍 0/55（2026-10-19 预检第二轮，rule4 incomplete，发现55执行0通过0跳过55，reason 为通用 produced-no-executable 且 log tail 为空） | 上一周期 all-or-nothing 假设失效：FULL 显式清单中任一 TU 编译失败即整体返回空，通用 reason 丢失了失败文件名与编译输出，无法定位；且 BRSKI 5 套件与核心 30 套件绑死，一坏全零 | 改走分级实现路线：Strategy1 去内层引号传值并必落盘 make 日志；Strategy2 改为 FULL(35套件,含BRSKI)优先、MINIMAL(30套件,不含BRSKI/CoAP)回退，runtest.c 的 ENABLE_BRSKI/HAVE_LIBCOAP 守卫保证分级链接合法，US5248 常驻两档；构建证据必落盘 libest_upstream_build_evidence.txt 并随失败标记上报非空 evidence；_save 按 tier 文件区分 gaps：19 CoAP 恒为 ohos_feature，MINIMAL 另缺 5 BRSKI 为 test_failure 带编译证据，55 审计差 1(US4747 从未注册)以 residual 补齐 |
| 12 | 上游真机仍 0/55（2026-10-19 预检第三轮，rule4 incomplete：ld.lld duplicate symbol client_cert/client_priv_key，US3646/US4710/US4778，tier=full-brski 与 minimal 均链接失败） | 现代 clang（≥11，真机 clang-15）默认 -fno-common，BRSKI 测试源跨编译单元 tentative definition 在链接期报 duplicate symbol；与 0006 已修复的库内 e_ctx_ssl_exdata_index 同类问题，但位置在上游测试代码 | 仅测试 runner 作用域加 -fcommon（DRAFT-24660 (a) 应用型可执行档允许档）：Strategy1 make 命令行追加 CFLAGS=-fcommon（Makefile 用 CFLAGS+= 追加 BRSKI 定义，命令行值被保留并流入 CCFLAGS 编译行）；Strategy2 手工编译 extra_cflags 与链接行追加 -fcommon；交付库本体不加 -fcommon（保持 0006 源级 extern 修复）。技术债：期望上游将测试全局改为 extern 声明 + 单一 .c 定义；待真机预检验证 |
| 13 | 上游真机仍 0/55（2026-10-19 预检第四轮，rule4 incomplete：-fcommon 后 duplicate symbol 消失，改为 ld.lld undefined symbol strcmp_s/memset_s/strstr_s/strtok_s/strncpy_s 等，make Makefile:121 与 full-brski/minimal 两档链接均失败） | 上轮 -fcommon 只修了编译期 tentative 定义合并；链接期新矛盾暴露：静态 libest.a 不内嵌 bundled safe_c stub 的 *_s 符号（safe_c_stub/lib 为 noinst 归档），而上游 test/UT/Makefile 的 LIBS 只有 -lest、无 -lsafe_lib（上游默认走 shared，符号已内嵌；本配方 --disable-shared 后悬空）。与库本体无关，纯测试链接缺件 | 新策略（与上轮不同）：① 新增 Strategy 1b，复用 make 已编好的原位对象（上游 SRC 全集，与上游默认行为一致）做修正链接，把 safe 归档以绝对路径追加在 -lest 之后（静态顺序敏感），落盘 tier=full-brski(make-objs)；② Strategy2 链接重定向落盘并回填证据尾、打印所选归档路径；③ CFLAGS 标记文件 + 变更时 make clean，防旧对象残留。交付库与 package_info 不变；待真机预检验证 |
| 14 | 上游真机仍 0/55（2026-10-19 预检第五轮，rule4 incomplete：minimal 档报 undefined us1864_test1 referenced by us1864.o，all manual tiers failed） | 子集拆分路线本身不成立：us1864_test1 在 us1864.c 内为 static，子集链接仍报其未定义，证明上游各 TU 间存在跨文件 helper 依赖（定义体落在被排除的 TU 中），任何排除 CoAP/BRSKI 文件的子集链接必然缺符号；与上轮 safe 缺件不同域 | 改走单 FULL 集路线（与前两次策略不同）：Strategy2 改为唯一 full 档（base+BRSKI+CoAP+util = 上游 SRC 全集 60 对象，-DENABLE_BRSKI 且不带 HAVE_LIBCOAP，与上游默认 make 一致），不再拆分；CoAP 套件无 LIBCOAP_DIR 时经 runtest.c 守卫休眠，按 ohos_feature 报 gaps；注释与 MANIFEST 口径同步。交付库不动；待真机预检验证 |
| 15 | 上游真机仍 0/55（2026-10-19 预检第六轮，rule4 incomplete：st_server.o: undefined est_find_ser_num_in_subj + libest.a: undefined strcmp_s/memset_s/strstr_s/strtok_s/strncpy_s 等，make 与 full 两档均失败） | 上一周期库测试配置失配：est_find_ser_num_in_subj 定义于 src/est/est_ossl_util.c 的 #if ENABLE_BRSKI 块内（configure --enable-brski 才编译进库），而配方库侧未传该旗、测试侧以 -DENABLE_BRSKI 编译，任何测试链接补件（-fcommon/safe 追加/FULL 集）都无法在库内凭空造出符号；*_s 缺件则是静态 libest.a 不内嵌 safe 归档而上游 test Makefile LIBS 无 -lsafe_lib（上游默认 shared 已内嵌），1b 虽补 safe 但同被 BRSKI 缺符号连带失败 | 新策略（库侧对齐，与上轮测试链接路线不同）：build() configure 追加 --enable-brski（无额外依赖，加 5 个 BRSKI 套件），使库与测试同以 ENABLE_BRSKI 编译，est_find_ser_num_in_subj 进入 libest.a；测试链接沿用 1b（make 原位对象 + safe 归档在 -lest 后）与单 FULL 回退，无需改动即可在库对齐后产出可执行文件；交付库功能为上游可选特性开关
| 16 | 上游真机仍 0/55（2026-10-19 预检第七轮：make 与 full 两档均链接失败；full 档报 us1864_test1 自引用未定义，make 档报 *_s 未定义） | 截断日志误导：us1864_test1 为静态函数不可能自引用缺失，实为其内部调用的 FIPS_mode_set（OpenSSL 3.0 已移除）被截断隐藏；库侧 0004/0005 已移植 FIPS API 但测试源码 US1864/us1864.c 仍调用旧 API；*_s 系静态 libest.a 不内嵌 safe 归档而上游 test Makefile LIBS 无 -lsafe_lib | 新策略（测试域兼容）：① build 内预编译 FIPS stub（FIPS_mode_set/FIPS_mode 恒返 0，走既有 skip 分支），测试域专用，不改上游文件与断言；② make 命令行 LIBS 覆盖追加 safe 与 stub 绝对归档；③ 1b 与单 FULL 手工链接同步追加 stub。交付库不动；待真机预检验证 |，非存根 |
| 17 | 真机 rule4 incomplete：上游 discovered 55 executed 3 passed 1 failed 0 skipped 25，passed+failed(1)!=executed(3)，gaps 残余 35 以 test_failure 填充（2026-10-19 预检第八轮） | 计数双源混合：_parse 用 Run Summary 的 ran(3) 配 verbose Suite:/Test: 分组的 passed(1)/failed(0)，两源不一致即恒等式破裂；另忽略 Summary failed 列(g4)、skipped 用 inactive+missing(25)而非 discovered-executed(52)、残余缺口以无证据 test_failure 填充 | 单源化：_parse 只读 Run Summary suites 行(total/ran/failed/inactive，passed=ran-failed，verbose 仅证据；缺行才回退 verbose 单源)；_save 统一分母 55，skipped=55-ran，gaps=已失败(test_failure)+已编译未跑 ohos_feature(含 Suite Init failed 证据)+缺编 CoAP 19 ohos_feature+其余缺编 ohos_feature，无残余填充；断言收紧为 passed+failed==executed、executed+skipped==discovered、gaps 和==discovered-passed |
| 18 | 真机 rule4 incomplete：上游 discovered 55 executed 3 passed 0 failed 3 skipped 52，恒等式已成立但通过数为 0（2026-10-19 预检第九轮） | 双根因：① GNU make 命令行 CFLAGS 覆盖致 Makefile 内 CFLAGS+=-DENABLE_BRSKI 被忽略（runtest.c 的 ENABLE_BRSKI 守卫未生效，二进制只注册 30 套件而非 35，5 个 BRSKI 缺席）；② 上游测试 PKI 已过期：test/UT/CA/estCA/cacert.crt 有效期至 2026-06-14，当前运行 2026-10-19，curl 助手全开 SSL_VERIFYPEER，凡走 TLS 的 enroll 断言必然失败 | 新策略（构建域，非计数）：① make 命令行改传 CFLAGS="-fcommon -DENABLE_BRSKI"，哨兵同步更新触发 make clean 重编，注册数 30→35；② _save 对 failed 提取 mid-log 的 FAILED/Assertion 行入 evidence，下轮定位真实失败套件；③ 若 BRSKI 套件仍全败，下轮走上游自带 test/UT/CA/createCA.sh 重建测试 PKI 路线 |
| 19 | 真机 rule4 incomplete：上游 discovered 55 executed 3 passed 0 failed 3 skipped 52，BRSKI 注册已恢复 35 但通过仍为 0（2026-10-19 预检第十轮） | 双证据链：① 全部 EST 测试 PKI 已过期：estCA/cacert.crt NotAfter 2026-06-14、estservercertandkey.pem 与 US901 explicit-cert 等同批 12 年有效期至 2026-06-14/15，而当前运行 2026-10-19；curl 助手全系 SSL_VERIFYPEER=1，凡走 TLS 校验的正向断言必然失败。MFG/SUDI PKI 有效期至 2030/2040 不受影响。② 证据提取大小写漏检：CUnit Basic 输出小写 failed，旧提取只搜大写 FAILED 致 failed lines 为空 | 新策略（测试 PKI 同密钥续期，断言/库源码零触碰）：① conanfile 新增 _renew_upstream_test_pki（build 内 runtest 构建前调用，整体 try 包裹永不抛错）：CA 证书用已提交的 cakey.pem 自续 10 年；server 证书同密钥重签发并补 IP SAN；过期叶证书同 subject/同密钥经 openssl x509 -req -CA 重签（仅 issuer 为 estExampleCA/estEXTERNALCA 且 90 天内到期者；revoked/selfsigned/expired 等负向夹具与 masa/mfg/sudi/coap_emu 目录永不触碰；新证书 openssl verify 校验后才替换）；信任束按相同公钥块替换（顺序/组成不变）；幂等且自愈（有效期充足时直接跳过）。② 证据提取改为大小写不敏感并附 ran_suites 名单 |
| 20 | 真机 rule4 incomplete:上游 discovered 55 executed 1 passed 1 failed 0 skipped 54,passed 状态与结果矛盾,且 runtest 在首个套件后 core dump(Signal 5)(2026-10-19 预检第十一轮) | 上一周期根因假设失效:bare `req -new -x509` 无 -extensions/-config,把上游 createCA.sh 以 `-extensions v3_ca -config` 铸造的 CA 续成 v1 证书(无 basicConstraints CA:TRUE),破坏链验证并在 server-init 路径崩溃;且旧状态门 `failed>0 else passed` 在 54 skipped 下仍报 passed,自相矛盾 | 新策略(与续签路线不同的实现路线):① CA 续签改用已提交上游 openssl 配置的 v3_ca 扩展续,无配置则跳过(永不签发 v1 证书);叶证书加同公钥密钥匹配守卫,非匹配密钥不动夹具;② 新增 run_one_suite 单套件隔离驱动(复刻 runtest main 流程,逐套件独立进程,断言零触碰),35 套件逐个 verdict,崩溃套件记 test_failure 并附 crash 证据,单进程 runtest 保留为回退;③ 状态门诚实化:仅 executed==55 且 failed==0 才 passed,否则 failed,崩溃致残余按 test_failure 归因 |

## 源码修改

见 patches/0001-0006（6 个补丁）：0001-0003 为 OHOS 平台适配（config.guess/config.sub 三元组识别、
configure 临时目录权限），0004-0006 为 OpenSSL 3.x 余量修复；无上游功能改动，不含 `__OHOS__` 平台宏。

## 依赖版本

- openssl/3.5.6.1（ohpcd 制品仓；libest 通过 --with-ssl-dir 指向 conan openssl 包；
  libcurl/libcoap/uriparser 均为上游可选特性，默认关闭，不引入）

## 上游测试清点 (R51)

- 上游测试位于 `test/UT/`：CUnit 框架的 runtest 主程序，共注册 **55 个测试套件**
  （去重统计 `*_add_suite`：US748/US893-US903/US1005 等 13 个基础套件 +
  US1060-US5418 等 42 个 BRSKI/CoAP/回归套件，含 us1060c/us5418c/us5418h/
  us5248coap/us5248http 变体）；另有 test/util/ 的 st_server/st_proxy/curl_utils 支撑代码。
- **配方内运行方式**：顶层 Makefile.am 的 SUBDIRS 未包含 test/，
  未注册 automake TESTS/make check 目标；配方以
  `test_requires(cunit/2.1.3)` + `test_requires(curl/8.15.0)` 在 build()
  内构建 test/UT/runtest（优先 `make -C test/UT`，回退手工 cc 链接
  test/UT + test/util 全部源文件 + libest.a + libsafe_lib.a
  `-lcunit -lcurl -lssl -lcrypto -ldl -lpthread 含 -DHAVE_CUNIT/-DHAVE_LIBCURL/-DNO_SSL_DL/-DENABLE_BRSKI 及 -I test/util/test/UT/源根`），从 test/UT 目录运行并解析 CUnit
  `Run Summary` suites 行（Total/Ran/Passed/Failed/Inactive），落盘
  `build_folder/hmbs_upstream.json` 并随包发布到 `res/`，由 test_package
  重发 `HMBS_UPSTREAM_TEST_RESULT`（wslay/1.1.1 + dcap/2.47.14 +
  bzrtp/5.3.105 模式）。
- 消费者视角验证由 test_package 独立完成（est_get_version/est_get_api_level/
  est_init_logger 3 项实质 API 断言，ctest 注册 1 个测试；discovered 取自
  `ctest -N`，verdicts 取自 ctest stdout `Test #N ... Passed|Failed` 单一源，
  LastTest.log 仅在 stdout 零 verdict 时作单源回退）。

## 验证结果

- 本轮聚焦修复真机两处证据门禁：① test_package ctest 解析（stdout
  `Test #N` 与 LastTest.log `Test Passed.` 格式混淆致 passedCount=0）；
  ② 上游 55 个 CUnit 套件 executed=0（缺 cunit+curl 接入，被判 incomplete）。
  工作树未提交，待 HMBS 真机预检复跑。
- 本地已完成的静态自检：`python -m py_compile` 通过主配方与 test_package；
  6 个补丁文件存在；conandata URL/sha256 与实测归档一致；test.c 调用的
  3 个 API 在 3.2.0 src/est/est.h 中均存在。

## 交付物

- 源码 + 配方 PR-only：conanfile.py / conandata.yml / patches/ (6) /
  test_package/（conanfile.py + CMakeLists.txt + test.c + MANIFEST.yml）/
  manifest.yaml / notes.md（Conan create 产物由制品仓发布流水线另行处理）

## 注意事项

- 库本体只构建安装 src/est（libest + include/est/est.h）；example/ 演示程序、
  java/jni（需 JDK）不在配方构建范围。
- 1.0.0 的 OpenSSL3 迁移知识草稿（DRAFT-libest-1.0.0-openssl3-*）不适用于本版本；
  本版本沿用其 OHOS 平台三件套补丁经验与 test_package 模式。
---

**编写**: 2026-10-18（首轮工作树，待真机验证）
**最终状态**: 待 HMBS 真机预检
