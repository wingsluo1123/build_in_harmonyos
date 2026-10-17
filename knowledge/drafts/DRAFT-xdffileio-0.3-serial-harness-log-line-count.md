# DRAFT-xdffileio-0.3-serial-harness-log-line-count
> 串行harness老automake无test-suite.log时落盘逐行计数替代新式汇总
## 问题特征（真实日志片段/标记）
- `make testbdf testedf testgdf1 testgdf2 readcheck errorcheck`后打印`PASS: errorcheck`、`PASS: readcheck`，证明测试已执行，但配方抛错：`HMBS_UPSTREAM_TEST_RESULT={"status": "failed", "framework": "automake", "command": "make check", "discovered": 0, "executed": 0}`，`reason`: `test-suite.log not found; searched: .../build-release/tests/test-suite.log; .../tests/test-suite.log; .../build-release/test-suite.log`。
- 修复落盘后如实计数：`xdffileio upstream counts from (serial harness) .../build-release/upstream-check.log: total=6 passed=6 failed=0 skipped=0`，与MANIFEST确认的6个automake TESTS口径一致。
- 同包下一失败域为全量`make install DESTDIR`倒在`doc/install-man3`：`install -c -m 644 <23个xdf_*.3> '<pkg>/share/man/man3'`后报`make[2]: *** [Makefile:530: install-man3] Error 64`，此前libtool单文件装库已成功。
## 根因
- xdffileio 0.3为2012年生成的serial-harness Makefile（前parallel-tests时代），`make check`只打印每TEST一行`PASS:`/`FAIL:`，设计上就不写`test-suite.log`；配方只认新式汇总块，与真机实际输出错配，直接抛`ConanException`导致构建失败。
- 同族老autotools形态问题：全量`make install`遍历到`doc/install-man3`，用多源文件形式一次调用设备`install(1)`安装23个手册页，该形态在本机实现下返回`EX_USAGE(64)`；man对Conan消费者是可选产物（test_package仅`#include <xdfio.h>`并链接`libxdffileio`）。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/x/xdffileio/0.3/conanfile.py`新增`_parse_serial_check_log`：单正则逐行匹配`PASS/FAIL/XFAIL/XPASS/SKIP/ERROR`并做恒等式自检，无字符串数数与算术修补。
2. 同文件`_run_upstream_tests`改用POSIX可移植重定向落盘`upstream-check.log`并回显保留预检日志，再保退出码；`test-suite.log`存在时仍优先使用它，不存在且串行日志一致时才采用串行计数，否则如实失败并列出搜索路径；0行匹配时宁缺毋假不凑数。
3. `manifest.yaml`/`notes.md`记录串行口径与6个TESTS来源（`testbdf/testedf/testgdf1/testgdf2/readcheck/errorcheck`）。
4. 回退/同包拆分（fallback）：`package()`改用`make install-exec DESTDIR="<package_folder>"`只安装库，不再进入`doc/install-man3`；用纯Python（`glob+shutil.copy2`，不经过`install(1)`）把源码/构建树顶层`xdf*.h`拷贝到`<package>/include`、把`doc/*.3`拷贝到`<package>/share/man/man3`，安装后断言`<package>/lib`下存在`libxdffileio.*`（除`.la`），真机证实`staged 4 headers/20 man pages/library artifact(s): libxdffileio.a`；另删除遗留`.la`清理块中`src==dst`的`copy()`自拷贝，仅保留删除循环。
## 禁止策略
- 禁止`HMBS_UPSTREAM_TEST_RESULT={..."discovered":0..."status":"passed"}`与`total=0 passed=0`串行凑数放行：无落盘文件、无恒等式自检不得标记通过；两源（`test-suite.log`与串行日志）不混用。
- 违则真机预检`evidence incomplete`，上游结果不可审计，任务退回修复循环。
## 与相近条目的边界（查重）
- 类别性成立：串行automake无`test-suite.log`与man多文件安装失败回退为跨老版本autotools可复用模式，非本库专有。
- 增量性成立：现有条目无串行日志计数与`install-man3 EX_USAGE64`拆分覆盖，相邻条目根因与解法均不同；本条目以落盘逐行计数替代新式汇总为rec、以`install-exec+Python拷贝`为fallback，保持`test-suite.log`优先与0行不凑数边界。
## 适用判断
- 适用：2012年前后生成的`configure/Makefile.in`且`make check`打印`PASS:/FAIL:`但无`test-suite.log`的老autotools包；全量`make install`倒在`install-man3 Error 64`而库安装已成功时用fallback拆分。
- 不适用：新式`parallel-tests` harness已生成`test-suite.log`时不得用串行计数替代；man缺失仅记日志跳过、头文件/主库缺失必须抛错拒绝打空包；重定向命令须POSIX可移植。
