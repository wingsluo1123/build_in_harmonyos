# DRAFT-silk-3.24.2-profile-shell-selfclean-per-suite-reap-undiscovered-gap
> profile钉死SHELL/CONFIG_SHELL下configure脚本内自净与daemon分套件串行回收及声明发现差值归因
## 问题特征（真实日志片段/标记）
- `configure[147]: /data/service/hnp/bin/bash: inaccessible or not found`，退出码127，日志前一行已打印`[ohos] configure shell: /bin/sh`，证实进程env已对但RUN仍用坏shell。
- `HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","jobs":1,"install_shim":true,"hardlink":0}`，`HMBS_BUILD_TOOLS` cmake/make/ninja/python3均可用。
- 越过configure后出现 `configure: error: C compiler cannot create executables`、`make[2]: *** [Makefile:818: fake-cc.pmap] Error 1`、`Unrecognized character \\x7F`、`install-pkgincludeHEADERS Error 64`。
- `HMBS_UPSTREAM_TEST_RESULT={"status":"failed","framework":"automake","command":"make check -j1","discovered":15,"executed":15,"passed":14,"failed":1}`仅解析1个test-suite.log，与声明1574严重不符；`FAIL: tests/rwflowappend-append-bad.pl`、`# FAIL: 1`。
- 全量后 `discovered:1521/executed:1446/passed:1439/failed:7/skipped:75`，`discovered:1191/executed:1158/passed:1155/failed:3/skipped:33`，`discovered:1047/executed:1023/passed:1017/failed:6/skipped:24`多轮出现；`suite result: src/flowcap TOTAL=12 PASS=6 SKIP=6`、`src/rwtuc TOTAL=6 PASS=5 SKIP=1`；末段`Signal 9`、`conan create退出码137`、`discovered:0`无marker；`make install`期`can't fork - try again`、`Operation not permitted`、`Out of memory`、`Errno 12`。
- 关键词：`autotools_configure`、`configure failed`、`hmbs_upstream_test_result`、`hmbs_platform_capabilities`。
## 根因
- profile层钉死：`ci/conan/profiles/ohos-aarch64`的`[buildenv]`把`SHELL/CONFIG_SHELL`钉死为`/data/service/hnp/bin/bash`，每次`run()`经conanbuild重聚合覆盖配方进程`os.environ`修改与`generate()`的recipe buildenv覆盖，故`isfile+X_OK`排序、`[shell -c exit 0]`真实执行探测加黑名单、双保险均无法生效，autoconf configure经`$CONFIG_SHELL`重执行自身在147行失败。
- daemon累积与墙钟：单一顶层`make check`使`rwflowpack/flowcap/rwsender/rwreceiver`孤儿跨套件累积，前轮`797 discovered/772 passed/3 failed/22 skipped`后install报`can't fork`佐证；`SK_TESTS_TIMEOUT_FACTOR=3`使FAIL用例烧满225s把kill点从sendrcv提前到rwswapbytes/rwtotal，仅包装器回收不够；`rwflowpack TOTAL=56`单套件551s、`cleanup signalled=0`证伪孤儿假设，实为累计墙钟撞外层看门狗。
- 声明发现差值：`UPSTREAM_TEST_DISCOVERED=1574`与运行时聚合`discovered=1521`差53，系configure自动关闭可选特性（`Not building rwp*`、`Building without IPFIX/GnuTLS/MaxMindDB/IPA`，无pcap则无rwp*、无libfixbuf则无IPFIX）致对应TESTS从未注册，marker只覆盖`failed+skipped=82`，缺53 undiscovered项，故`1574-1439=135`对不上。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/s/silk/3.24.2/conanfile.py`新增`_patch_configure_shell()`：遍历source/base_source/build父目录下全部`configure`文件，shebang后插入CONFIG_SHELL自净块（坏路径与空值强制`/bin/sh`，其他值先真实执行探测再回退）并`export SHELL=/bin/sh`，替换脚本内硬编码坏路径；`build()`调用顺序改为`_patch_config_guess_sub→_patch_configure_mktemp→_patch_configure_shell`，与env优先级无关。
2. 编译器与上游笔误最小修补：新增`_resolve_compiler`对钉死CC/CXX先做`--version`实测、失败才经PATH/同目录回退并显式`CC=/ CXX=/`传入configure/make，失败转储config.log尾部80行；新增`_patch_upstream_perl_exec_bug`去掉`tests/Makefile`对C二进制`rwgeoip2ccmap`误加的`$(PERL)`前缀；`package()`接入mkdir/cp install垫片并重定向INSTALL/MKDIR_P，bare chmod改为最佳努力。
3. 全量收集与分套件串行回收：`UPSTREAM_TEST_COMMAND`与MANIFEST改为`make check -j1 -k`；新增`_discover_check_suites`直连glob `build/src/*/Makefile`加`build/tests/Makefile`（不足10回退顶层），逐套`make -C <suite> check -j1 -k`，套间调用瘦身后`_cleanup_test_daemons`（单次/proc扫描、仅有目标时1s宽限、覆盖perl/python包装器、豁免make/sh/conan），轻量文件型套件`-j4`、重套件rwflowpack/flowcap/sendrcv与libsilk/rwconvert保持`-j1`，轻量先行重套件延后，每套件输出suite result、suite done耗时与res资源行，失败用例名写入gaps detail。
4. 声明发现差值归因：`build()` marker在skipped gap后新增`undiscovered` environment gap（`declared-discovered`，文件加常量确定性来源）；`test_package/conanfile.py`新增`UPSTREAM_DECLARED=1574`，门禁改为`gaps合计==failed+skipped+undiscovered`且environment覆盖`skipped+undiscovered`，仍对`failed>0`抛错并校验恒等式；`_run_upstream_tests`起始处`/dev/null` dup2到fd0消除`rwbagtool-lone-command`无参数读stdin挂起。
5. 验证：真机`conan create`越过147行，`HMBS_UPSTREAM_TEST_RESULT`以test-suite.log聚合计数加environment gaps满足恒等式，`HMBS_TEST_PACKAGE_RESULT discovered:3 passedCount:3`，门禁passed。
## 禁止策略
- 禁止把`CONFIG_SHELL=/data/service/hnp/bin/bash`留在候选或回退尾部；禁止仅用`isfile`或`access(X_OK)`作唯一可执行判据，必须经`[shell -c exit 0]`真实执行探测或脚本内自净，否则147行以127复现。
- 禁止顶层单次`make check`无`-k`收集；禁止对`can't fork/Errno 12`加3x重试消耗窗口，失败须取证loadavg/meminfo/proc后原样抛出按infra路由。
- 禁止把`undiscovered`归为`test_failure`或凑数；禁止零证据`discovered:0`标passed放行。
## 与相近条目的边界（查重）
- 现有E165/E705/E1858/E888/E1922/E2225及crosstool草稿只覆盖相邻症状（单点shell回退、单套件超时加码、零SKIP门禁），无一覆盖profile覆盖自净、逐套件回收并发与声明发现差值口径，本条目为增量。
- libfixbuf同款install垫片只解决HMDFS头文件拷贝Error 64，本条目复用其垫片但新增自净加分套件加缺口归因，不重复立项。
## 适用判断
- 当autotools配方报某bash路径`inaccessible or not found`且配方曾覆盖`CONFIG_SHELL/SHELL`、HMBS已注入`SHELL=/bin/sh`，且日志已选`/bin/sh`仍同错复现时，判profile钉死，适用脚本内自净。
- 当automake多套件含daemon集成测试、末段被SIGKILL/exit137且此前多套件test-suite.log已产出、或曾出现EAGAIN daemon残留时，适用分套件串行加套间回收与轻重分级并发。
- 当MANIFEST声明总数大于运行时聚合discovered且差值对应configure自动禁用的可选套件时，适用undiscovered environment缺口归因；三者均适用于同类autotools/daemon库复用。
