# DRAFT-libest-3.2.0-vendored-noinst-pki-renew-suite-isolation
> Autotools vendored noinst归档静态悬空补交付与过期测试PKI保扩展续期加单套件隔离计数
## 问题特征（真实日志片段/标记）
- `configure[159]: /data/service/hnp/bin/bash: inaccessible or not found`，`autotools.configure()` Exit 127；后转为 `C compiler cannot create executables`。
- `ld.lld: error: undefined symbol: memcpy_s/memzero_s/strnlen_s/strcasecmp_s/strcpy_s/strcspn_s`，引用方均为`libest.a`；`test_package` cmake.build rc=2。
- `duplicate symbol: client_cert/client_priv_key` 于US3646/US4710/US4778；`undefined symbol: est_find_ser_num_in_subj referenced by st_server.c`；`undefined symbol: us1864_test1`。
- `HMBS_UPSTREAM_TEST_RESULT={"status":"failed","command":"test/UT/runtest (55 CUnit suites)","discovered":55,"executed":0}`；后 `total=35 ran=3 passed=0 failed=3`，续期后 `total=1 ran=1 passed=1 skipped=54 but status=passed` 自相矛盾伴Signal 5崩溃。
- `WARN: libest PKI: CA renew failed estCA/cacert.crt: subject name is expected to be in the format /type0=value0/...`，`CN = estExampleCA` 非法。
## 根因
- `safe_c_stub/lib/Makefile.am: noinst_LIBRARIES=libsafe_lib.a` 不被`make install`安装，`configure.ac: LIBS+=-lsafe_lib` 使主库建成但符号悬空，配方仅`make -C src install`且`libs=[est]`，消费者缺`-lsafe_lib`。
- OHOS profile `[buildenv] CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash` 在预检不可执行，`configure: exec $CONFIG_SHELL` 重执行失败；`os.environ`与`buildenv_info`覆盖被`conanbuild.sh`覆盖而无效。
- 3.2.0残留`FIPS_mode`、非extern全局、`X509_ATTRIBUTE_free`双重释放与OpenSSL 3.5.6.1不兼容；`--enable-brski`库侧缺失与测试侧`-DENABLE_BRSKI`失配；`CFLAGS=-fcommon`命令行丢弃Makefile内`CFLAGS+=-DENABLE_BRSKI`。
- 测试PKI `estCA/cacert.crt NotAfter 2026-06-14`过期，裸`openssl req -new -x509`续签丢弃上游`createCA.sh -extensions v3_ca -config`的`CA:TRUE`，变v1 CA破坏链验证致server-init崩溃，单进程runtest掩盖计数。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 换用制品仓`openssl/3.5.6.1`二进制避开CCI 1.1.1w源码构建OOM，新增0004-0006补丁：`FIPS_mode`改`EVP_default_properties_is_fips_enabled`、删`X509_ATTRIBUTE_free`、头加`extern`。
2. `archives/l/libest/3.2.0/conanfile.py:build()` 改写`conanbuild.sh`与`configure`硬编码hnp bash为`/bin/sh`，`CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh ./configure --enable-static --disable-shared --with-ssl-dir --enable-brski`，恢复工具链参数并用`Environment`固化`SHELL/TMPDIR/CC`。
3. `package():_install_safe_stub`搜索`safe_c_stub/lib[/.libs]/libsafe_lib.a`拷贝为`package/lib/libsafe_lib.a`，`package_info libs=[est,safe_lib]`保静态顺序；`test_requires cunit/2.1.3` ohpcd独有版避开conancenter m4链。
4. 测试域预编译FIPS stub恒返0走skip分支，`make LIBS="<safe.a> <fips_stub.a>" CFLAGS="-fcommon -DENABLE_BRSKI"`与手工链接单FULL集60对象追加同序归档。
5. `_renew_upstream_test_pki`：CA用`_req_subj`转`/CN=`斜杠格式后`req -new -x509 -extensions v3_ca`自续3650天，叶证书同密钥`x509 -req -CA`重签1825天补IP SAN，负向夹具与masa/mfg/sudi永不触碰；`run_one_suite`复刻runtest启动逐套件独立进程120s timeout，诚实门仅`executed==55 && failed==0`才passed。
## 禁止策略
- 禁止`HMBS_UPSTREAM_TEST_RESULT={"status":"passed"..."skipped":54}`零证据放行；禁止裸`req -new -x509`签v1 CA；禁止手动拼装configure丢弃host/ssl-dir；禁止交付库加`-fcommon`，仅限runtest作用域。
## 与相近条目的边界（查重）
- 机械查重仅命中autotools/tmpdir/chmod/编译器探针等邻域条目，无覆盖本链路noinst补交付、安全函数悬空补链接、HNP不可执行SHELL改写驱动、FIPS移除桩、过期PKI保扩展续期与崩溃隔离；修复轮命中既有条目后仍3轮失败，靠自研单FULL集与隔离计数才通过门禁，构成Autotools+TLS测试夹具通类解法可跨库复用。
## 适用判断
- 当Autotools库vendored noinst归档致下游`*_s`未定义、profile SHELL不可执行、`FIPS_mode_set/us1864`缺符号、BRSKI宏失配、测试PKI过期且CUnit单进程崩溃时适用；无vendored归档或无自带PKI/CUnit时不适用。
