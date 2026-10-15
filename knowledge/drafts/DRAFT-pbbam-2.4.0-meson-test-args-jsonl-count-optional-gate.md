# DRAFT-pbbam-2.4.0-meson-test-args-jsonl-count-optional-gate
> Conan2 Meson测试兼容与计数：直调meson test替代test(args)、testlog.json JSONL单源计数与外部工具可选门控
## 问题特征（真实日志片段/标记）
- 300/300编译成功后零执行：`pbbam/2.4.0: HMBS_UPSTREAM_TEST_RESULT={"status": "failed", "framework": "meson", "command": "meson test --print-errorlogs", "discovered": 3, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "reason": "meson-logs/testlog.txt not found; searched build/meson-logs/testlog.txt"}`，且无任何meson test输出。
- 外部工具硬失败：`../tools/meson.build:222:24: ERROR: Program 'samtools' not found or not executable`，`conan create`退出码1，0测试执行。
- JSONL误判回退漏计：`testlog.json unreadable (Extra data: line 2 column 1)`被迫回退txt漏计，marker报discovered 8/executed 2/passed 0与meson实跑7项矛盾。
- 标准覆盖：`../src/BamHeader.cpp:131:32: error: no member named 'contains' in 'std::set<std::string>'`，编译行实测`-std=c++17`。
- 补丁校验：`patches/0001-samtools-optional.patch: error: patch stream is incomplete!`，`Failed to parse patch`；0002报`source file is different - tests/src/test_PacBioIndex.cpp`。
## 根因
- 31114核对conan develop2源码证实：Conan 2.x `Meson.test(self)`无args形参，配方`meson.test(args=[--print-errorlogs])`抛TypeError被except吞掉，meson test从未执行故无日志。
- 31277证实：meson 1.11的testlog.json是每行一个对象的JSONL而非数组，整文档`json.load`必报Extra data，须整文档/逐行双模式解码但仍以testlog.json逐条name/result为唯一单源计数。
- 31168证实：上游pbbamify与ccs-kinetics的cram用例经`samtools view -h`管道，`tools/meson.build`用无`required:false`的`find_program`，OHOS无samtools制品即configure硬失败。
- 31070证实：上游meson.build默认`cpp_std=c++20`并用`std::set::contains`，ohos profile下发c++17使MesonToolchain覆盖上游默认，须工具链恢复标准而非逐文件补丁。
- 31360证实：手写补丁hunk头`-80,6/+80,15`与`-193,5/+200,10`偏离标准，git apply容忍offset通过但Conan `apply_conandata_patches`严格校验拒绝，须按difflib标准重生成。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/p/pbbam/2.4.0/conanfile.py:build()`改走`self.run(meson test -v --print-errorlogs, cwd=build_folder)`，删除`meson.test(args=[...])`；缺日志时marker如实报discovered 0加真实searched路径与目录清单。
2. `archives/p/pbbam/2.4.0/conanfile.py:generate()`设`tc.cpp_std=c++20`恢复上游标准，并经`tc.c_args/tc.cpp_args`全局注入`BOOST_SP_NO_PTHREAD_SETCANCELSTATE`；同步`tool_requires(meson/1.11.0)`与`wrap_mode=nodownload`离线vendor。
3. 新增`archives/p/pbbam/2.4.0/patches/0001-samtools-optional.patch`：`find_program('samtools', required:false)`并用`if found()`包裹`test(pbbamify_CramTests)`与`ccs-kinetics`注册，在`conandata.yml`登记；缺失时marker以testlog是否含对应名加meson-log samtools记录为确定源记excluded而非skipped。
4. `_emit_upstream_marker`改以`meson-logs/testlog.json`为唯一计数源，做整文档加逐行JSONL双模式解码，txt仅作尾部证据；gtest失败名从`pbbam-gtest-unittests.xml`采样透出message截断600字符；恒等式破坏如实fail拒发。
5. 以官方tarball解包为orig、LF归一化为new，用`difflib.unified_diff`重生成0002标准头`-80,8/+80,17`与`-191,9/+200,14`整体替换，`git apply --check`无offset通过后再登记`conandata.yml/MANIFEST/manifest.yaml/notes.md`。
## 禁止策略
- 禁止`meson.test(args=`：Conan2签名无args，TypeError被吞致零执行；须直调`meson test`。
- 禁止为通过改写hardcoded压缩金数据断言语义，仅允许压缩栈证实后刷新数值；禁止把缺外部二进制的未注册测试计为skipped掩盖passed硬门禁，须记excluded并附具名与总数审计。
- 禁止手写hunk头行号计数，必须脚本校验一致。
## 与相近条目的边界（查重）
- 机械查重关键词`compile_error/hmbs_platform_capabilities/hmbs_build_tools`等均为预检样板行误命中，不构成覆盖。
- 具名条目E672/daw/gcc9/bisheng、ali/parlay、libnxt、ndpi、buildtorrent/darts均与本任务错误域不同，无现有条目覆盖上述Meson行为类问题，本条目为Meson库可复用的行为类增量。
## 适用判断
- 适用：Conan 2 Meson配方需向meson test传参；meson testlog.json报Extra data；meson find_program对仅测试需的外部二进制硬查找；上游声明cpp_std=c++20但profile下发c++17；Conan报patch stream incomplete或source file is different而git apply容忍offset通过。
- 不适用：CMake/Catch/autotools测试栈、裸soname缺失、fork压力重试场景。
- 证据：真机`discovered 5/executed 5/passed 5/skipped 0/excluded 3`与`HMBS_TEST_PACKAGE_RESULT`全过为准。
