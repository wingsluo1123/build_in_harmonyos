# DRAFT-tabixpp-1.1.2-install-shim-copy-cli-test-hardening
> 上游Makefile多源install被install_shim拒绝时改用copy直拷与CLI上游测试加固
## 问题特征（真实日志片段/标记）
- 平台能力位：`HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/f48e45d64092/runtime/tabixpp-1.1.2/tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}`，确认 `install_shim=true`、`chmod=0`。
- 打包失败：`make: *** [Makefile:80: install] Error 64`，前两行单源 `install` 成功，第三行 `install -c libtabix.a libtabix.so.1 .../p//lib` 多源形式后失败，对应 `ConanException Error 2`。
- 上游测试曾失败：真机 `build()` 执行 `RUN: ./tabix++ test/vcf_file.vcf.gz > upstream_test.log 2>&1 && cat upstream_test.log` 报 `ConanException Error 127` 且 `ERROR` 为空、上游计数为 0；修复后 `HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"make-test","command":"./tabix++ test/vcf_file.vcf.gz","discovered":1,"executed":1,"passed":1,"failed":0,"skipped":0}`，1/1 通过。
- 消费者测试失败：`RUN: ./test_tabixpp` 后 `FATAL - bgzip compression failed`，`sh: bgzip: inaccessible or not found`，`ERROR: tabixpp/1.1.2 (test package): Error in test() method, line 39`，`ConanException: Error 1 while executing`。
## 根因
- 平台差异类构建系统行为：上游 `Makefile install` 目标三行 `INSTALL` 调用中多源 `install -c` 不被 HarmonyOS `install_shim` 支持，与配方覆盖变量无关，沿用 `make install` 必然复现 `Error 64`。
- CLI 上游测试三项可确认缺陷：失败时不 `cat` 日志导致 `&&` 吞掉诊断；动态链接 `-lhts` 时未设 `LD_LIBRARY_PATH`；OHOS 上未自签新构建 `tabix++` 即执行；且曾以非空输出掩盖非零退出。
- `test_package` 对外部 CLI 隐式 `PATH` 依赖：`test_tabixpp.cpp` 用 `std::system` 调 `bgzip/tabix`，而远端 `htslib/1.24-r0` 以 `ohpcd` 二进制包下载不保证提供该工具，与测试逻辑本身无关。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/t/tabixpp/1.1.2/conanfile.py` 新增 `_dep_libdirs/_sign_binary` 辅助：收集全部依赖 `libdirs`，用 `binary-sign-tool` 对 ELF 最佳努力自签，缺工具仅警告，`HMBS_CAP_CHMOD=0` 下 `chmod` 失败已捕获警告。
2. 同文件重写 `_run_upstream_test`：`./tabix++ test/vcf_file.vcf.gz > upstream_test.log 2>&1; rc=$?; cat upstream_test.log; exit $rc` 常显日志，异常也生成 `HMBS_UPSTREAM_TEST_RESULT`；运行前注入 `LD_LIBRARY_PATH` 并自签 `tabix++`；非零退出即使日志非空也判 `failed` 并抛带原始异常的错误。
3. 同文件 `package()` 删除 `make install` 调用，改用 `conan copy()` 直拷与上游同布局：`tabix++` 到 `bin`、`*.hpp` 到 `include`、`libtabix.a`/`libtabix.so*` 到 `lib`、`LICENSE` 到 `licenses`，避免 `mkdir/install/strip` 工具链差异；复用 `_sign_binary` 对包内 `bin/tabix++` 自签。
4. `archives/t/tabixpp/1.1.2/patches/0001-tabixpp-link-external-htslib.patch` 保持链接外部 `htslib`，`conandata.yml/manifest.yaml/notes.md/README.md` 同步更新打包与测试说明。
5. `archives/t/tabixpp/1.1.2/test_package/test_tabixpp.cpp` 删除 `std::system("bgzip/tabix")`，改用 `bgzf_open/bgzf_write/bgzf_close` 建 `bgzf` 压缩 VCF，`tbx_index_build(&tbx_conf_vcf)` 建 `.tbi`，预设必须用 `tbx_conf_vcf` 以匹配 VCF 坐标语义；`test_package/conanfile.py/MANIFEST.yml/CMakeLists.txt` 同步描述，断言口径保持 8 不变。
6. 验证：真机 `HMBS_UPSTREAM_TEST_RESULT` 1/1 通过，打包无 `Error 64`，`test_package` 全过，`v2:compile:compiler_error` 清零、全部门禁通过。
## 禁止策略
- 禁止沿用 `install -c libtabix.a libtabix.so*` 多源形式或 `make install` 打包；违者复现 `make: *** [Makefile:80: install] Error 64`。
- 禁止以日志非空掩盖非零退出；禁止缺自签工具时伪造通过，仅允许警告继续。
## 与相近条目的边界（查重）
- 查重命中无覆盖 `install_shim Error 64`、CLI 测试自签加固及 C API 现场生成夹具，本条目增量成立。
- 引用 `htslib/1.24-r0` 同仓 `LD_LIBRARY_PATH` 做法与 `cronutils` 草稿 OHOS ELF 自签仅作证据，不替代本条目多源 `install` 改 `copy` 直拷的核心增量。
## 适用判断
- 当 `HMBS_PLATFORM_CAPABILITIES` 含 `install_shim=true` 且上游 `Makefile install` 用多源 `install -c` 时适用；需与上游同布局但希望避开工具链差异时优先 `copy`。
- 当 `raw Makefile` 在 `build()` 内直接执行新构建 CLI 且链接外部 Conan 共享库、目标为 HarmonyOS/OHOS 可能需自签时适用上游测试加固。
- 当消费者测试需现场制作 `bgzf+tabix` 夹具但依赖包不保证提供 `bgzip/tabix CLI`、且已链接 `libhts` 可直接用 C API 时适用 `BGZF/tbx` 替换；保持用例口径不变，仅替换夹具制作方式。
