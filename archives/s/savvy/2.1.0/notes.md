# savvy 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 header-only INTERFACE 库 + src/sav 生成 `sav` CLI）
- 适配日期: 2026-10-13
- 编译器: OHOS clang/clang++（aarch64-linux-ohos，DevEco Studio SDK llvm 15.0.4）
- 目标 profile: ci/conan/profiles/ohos-aarch64（os=OHOS, clang 15, libc++, cppstd=17, build_type=Release）
- 状态: built 待真机预检

## 上游信息（W0/W1）
- 上游仓库: https://github.com/statgen/savvy（Conan 包名 savvy）
- 官方 tag: v2.1.0，源码归档 sha256 83ebd88c097799b3bbf771dc8ebf6892797ca7a1f49c2d1665d52cfc1bf9e1de（本机下载实测复核）
- 许可证: MPL-2.0
- 性质: header-only C++11 库（`add_library(savvy INTERFACE)`，include/savvy/*.hpp），
  附带 `sav` 命令行工具（src/sav/：concat/export/head/import/index/rehead/sort/stat/
  stat-index/stat-merge 子命令）。无编译产物库（无 .a/.so）。
- 上游依赖（CMakeLists find_package + target_link_libraries）: shrinkwrap（INTERFACE），
  shrinkwrap 再依赖 xz / zlib / zstd；另有 find_package(Threads)。本适配沿用制品仓
  libshrinkwrap/1.2.0（其 requires xz/5.8.3.2、zlib/1.3.2.1、zstd/1.5.7.1）。
- 上游测试: `-DBUILD_TESTS=ON` → savvy-test（src/test/main.cpp），ctest 注册 5 个用例
  （convert-file / subset / random-access / stride-reduce / missing-headers）。
  fixture 为源码树根目录 test_file.vcf 与 test_file_missing_headers.vcf
  （经 -DSAVVYT_VCF_FILE 编译期绝对路径注入）；SAV 中间文件写进程 cwd。

## W0 依赖结论
- 依赖数量: 1（libshrinkwrap；规划同 PR 一并验证真机解析）
- 已满足依赖: libshrinkwrap/1.2.0（本仓库已归档；其 requires xz/5.8.3.2、zlib/1.3.2.1、
  zstd/1.5.7.1 均已发布）
- 缺失依赖: 无
- 是否需要拆分依赖适配: 否
- 阻塞点: 待真机验证 R36

## 编译步骤（配方设计，待真机执行）
1. conan create 按项目 CI 入口执行（build_and_test.sh 单包模式）。
2. source(): conandata.yml 官方 URL（R39 单值，走 CI 镜像改写 + 预下载重试）。
3. generate(): CMakeToolchain，
   - BUILD_TESTS=ON（打开上游官方测试，L1 证据）
   - BUILD_EVAL=OFF / BUILD_SLR_EXAMPLES=OFF / BUILD_SPARSE_REGRESSION=OFF
     （这三个特性需要 htslib / armadillo / OpenCL / xtensor-blas 系统库，非本包必要）
   - 真机编译器路径钉定（profile 指向可能已迁移的 /data/service/hnp/bin）
   - CMakeDeps 生成 libshrinkwrap 配置
4. build():
   - replace_in_file 若干 portability 改动（见「源码修改」）
   - 起始 `self.conf.define("tools.build:jobs", 1)`：显式串行，规避上游 5 个
     ctest 用例共用 savvy-test 二进制 + 共享 cwd 下 test_file_*.sav fixture 的
     并行写/读竞态（CI worker 未注入 tools.build:jobs 时 Conan 会自动
     `--parallel <cpu_count>`）
   - configure → build → `ctest --output-on-failure`（L1 上游官方测试），
     ctest 输出写入 build 目录 hmbs_ctest.log
   - 逐行解析 hmbs_ctest.log 的 `Test #N:` 进度行，作为 discovered/passed/
     failed/skipped 的唯一数据源，写入并打印 HMBS_UPSTREAM_TEST_RESULT
     （解析不到用例行则抛异常，不用猜测值凑数）
5. package(): include/savvy/*.hpp + LICENSE + bin/sav + res/hmbs_upstream.json
   （不跑上游 cmake install：install(EXPORT) 会烧录构建机路径，消费接口由
   cpp_info + CMakeDeps 提供，libshrinkwrap 同款判断）。
6. test_package(): CMake 消费者链接 savvy::savvy，varint 往返 + sav CLI 冒烟。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 find_package(shrinkwrap)+target_link_libraries(savvy INTERFACE shrinkwrap) 用裸目标名 | Conan CMakeDeps 只生成 shrinkwrap::shrinkwrap，裸名退化为 -lshrinkwrap 且无 include 目录 | build() 用 replace_in_file 把 target_link_libraries 改为 shrinkwrap::shrinkwrap（zydis Zycore 同款前例） |
| 2 | 上游测试全用 C assert()；CI profile 是 Release（NDEBUG）会把断言编译掉 → 静默通过 | NDEBUG 在 Release 下禁用 assert | build() 给有且仅有的测试目标 savvy-test 加 target_compile_options(-UNDEBUG)（c-algorithms R09 同款前例），生产 sav 不受影响 |
| 3 | 真机 /tmp 只读 | HMBS true-device 挂载 /tmp 只读 | 复用 _ensure_writable_tmp（TMPDIR/TMP/TEMP + HMBS 注入），只重定向临时根，不跳过测试 |
| 4 | profile 指向的编译器路径可能已迁移（/data/service/hnp/bin → ~/usr/local/bin） | 真机工具链迁移 | _resolve_compiler + _fix_generated_toolchain_compiler（zydis 同款） |
| 5 | 真机 CMake 4.1.2 报 `cmake_minimum_required`：Compatibility with CMake < 3.5 has been removed | 上游顶层 `cmake_minimum_required(VERSION 3.2)`，CMake 4.x 移除了对 <3.5 的兼容 | `_apply_cmake_fixes` 把上游 CMakeLists.txt 的 `cmake_minimum_required(VERSION 3.2)` 提升为 `3.5`（4.x 支持的最低值，工程仅 C++11 + 旧式 INTERFACE，语义完全覆盖） |
| 6 | random_access_test 失败：`reset_bounds` 后 `assert(rdr.good())`（main.cpp:614 触发），因为内嵌 S1R 索引加载失败 | 上游 SAV2 writer 把 s1r 索引临时文件硬编码到 `/tmp/tmpfileXXXXXX`（mkstemp）；HMBS 真机 `/tmp` 只读，mkstemp 失败 → 索引不追加回 SAV 文件 → reader 找不到内嵌索引 → `s1r_index_->good()` 为假 → `reset_bounds` 置 failbit。另有上游 bug：`if (!tmp_fd)` 判断错误（mkstemp 失败返回 -1 为真值，永远走不到错误分支） | `_apply_cmake_fixes` 把 writer.hpp 的临时索引路径改为优先用 TMPDIR/TMP（配方 `_ensure_writable_tmp` 已注入可写目录并导出到 build 环境），并修正为 `if (tmp_fd < 0)`。纯 portability，无 `__OHOS__` |
| 7 | test_package `generate()` 报 `CMakeToolchain is declared in the generators attribute, but was instantiated in the generate() method too`（test_package/conanfile.py:102） | test_package 在 `generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"` 里声明了 CMakeToolchain，又在 `generate()` 里手动 `CMakeToolchain(self)` + `tc.generate()`（为注入真机编译器路径并导出可写 TMPDIR），Conan 检测到 CMakeToolchain 被重复生成 | 移除 test_package 的 `generators` 声明（置空元组），全部生成器改由 `generate()` 手动实例化（与主配方一致） |
| 8 | test_package 编译失败：`fatal error: 'savvy/varint.hpp' file not found`（test_savvy.cpp:9） | **根因（第一版修复无效）**：savvy 包误用 `package_type="application"`，Conan 2 的 CMakeDeps 对 application 类型生成的 `*-data.cmake` 中 `INCLUDE_DIRS`/`LIBS` 为空（basisu/razercfg/pianobar 同款 E 级错误模式，见 feedback/SKILL_FEEDBACK_ce140da2.md）。仅靠 `package_info()` 声明 `cpp_info.includedirs=["include"]` **不够**——application 类型会让 CMakeDeps 直接丢弃 include 信息，消费者 `savvy::savvy` 编译路径仍无 include | **solution（二版，实测路线）**：把 `package_type` 从 `application` 改为 `header-library`（savvy 本质是 header-only INTERFACE 库，无 .a/.so，符合 header-library 语义）。header-library 的 CMakeDeps 默认把 `includedirs`（=include）挂到 `savvy::savvy`，消费者即可吃到 `<savvy/varint.hpp>`。`sav` CLI 仍经 bindirs + 软件级 commands.json（R38）交付，二者不冲突 |
| 9 | test_package 编译失败（header 找到后新一批 #include 期错误）：`utility.hpp:63 no member named 'typed_value' in namespace 'savvy'`、`utility.hpp:184 no member named 'cerr' in namespace 'std'`、`test_savvy.cpp:84 no member named 'has_extension' in namespace 'savvy::detail'` | 两个问题：(a) 上游 `utility.hpp` 未自包含——用 `savvy::typed_value::is_end_of_vector`、`std::cerr/std::endl` 却未 include `typed_value.hpp`/`<iostream>`，上游 test 靠传递包含碰巧编过，消费者独立 include 即挂；(b) 我的 test 把定义在 `savvy/savvy.hpp` 的 `has_extension` 错当成在 `utility.hpp`，且 `has_extension("sample.vcf.gz",".vcf")` 断言逻辑颠倒（`.vcf.gz` 不以 `.vcf` 结尾，应返回 false） | build() `_apply_cmake_fixes` 给 `utility.hpp` 补 `#include "typed_value.hpp"` + `#include <iostream>`（头自包含，任何消费者可用）；test 改 include `<savvy/savvy.hpp>` 拿 has_extension，并把该断言改为正确语义（`.vcf` 匹配、`.vcf.gz` 不匹配 `.vcf` 但匹配 `.gz`、`.txt` 不匹配 `.vcf`）；has_extension 检查从 3 增至 4，测试断言总数 28→29（同步 MANIFEST/notes/PR 草稿） |
| 10 | test_package 运行失败：`Savvy consumer checks: 29, failures: 8`，8 个失败全为 `varint(N) consumed all bytes`（roundtrip decode 与 byte width 全过） | 我的 test 对 `varint_decode` 返回迭代器的语义假设错误：上游 `varint_decode` 在命中无继续位的终止字节时 `break` 而不再 `++input_it`，返回「最后一个已消费字节」的迭代器（= `encoded.end() - 1`），不是 one-past-end；原断言 `decoded_end == encoded.end()` 恒为假。库本身编解码正确（decode 值、字节宽均对） | 把断言改为匹配真实语义：`decoded_end == encoded.end() - 1`（decode 恰好消费完整编码、定位到末字节），断言数仍为 29，不再有失败；同步更新 MANIFEST 描述 |
| 11 | 官方 CI（build #88326）`conan create` 中 ctest 以 `--parallel 20` 运行：`subset_test`（main.cpp:721 `assert(rdr.good())`）与 `random_access_test`（main.cpp:533 checksum 断言）双双 `Subprocess aborted`，stderr 均打印 `Unsupported file format`；`convert_file_test` / `stride_reduce_test` / `missing_headers_test` 通过（60% passed, 2 failed out of 5） | **并行竞态**：上游 5 个 ctest 用例共用一个测试二进制 `savvy-test`，且 `convert-file`/`subset`/`random-access` 都在进程 cwd 读写同一对 fixture 产物 `test_file_hard.sav`/`test_file_dose.sav`（main.cpp 的 `convert_file_test` + `file_exists()` 缓存判断）。ctest 并行时多个 `savvy-test` 进程同时写这些 .sav 文件，后启动的 reader 读到半写文件 → `reader::read_header()` 的 magic 判定失败打印 `Unsupported file format` → `rdr` 置 badbit → `assert(rdr.good())` 与 checksum 断言失败。CI worker 未注入 `tools.build:jobs`，Conan `CMake.ctest()` 自动追加 `--parallel <cpu_count>`（worker 20）；HMBS 真机注入 `tools.build:jobs=1` 恰好串行，故此前真机通过而 CI 失败 | `build()` 起始 `self.conf.define("tools.build:jobs", 1)`（librtpi/neko/objfw 同款 conf 前例），使 `CMake.ctest()` 传入 `--parallel 1`、`CMake.build()` 亦串行；同时改用 ctest 自身日志（`hmbs_ctest.log`）逐行解析 `Test #N:` 进度行作为 discovered/passed/failed/skipped 的唯一数据源，替代原先「按 CTestTestfile 的 add_test 数 + 回落 5」的非确定性计数 |

## 源码修改

patches_applied: []（用 build() 内 replace_in_file 落地，非独立补丁文件）：
1. CMakeLists.txt: `cmake_minimum_required(VERSION 3.2)` →
   `cmake_minimum_required(VERSION 3.5)`
   （portability：真机 CMake 4.1.2 已移除对 CMake<3.5 的兼容，3.5 是 4.x
   支持的最低值）
2. CMakeLists.txt: `target_link_libraries(savvy INTERFACE shrinkwrap)` →
   `target_link_libraries(savvy INTERFACE shrinkwrap::shrinkwrap)`
   （portability：适配 Conan CMakeDeps 的命名空间目标名）
3. CMakeLists.txt: 在 `target_link_libraries(savvy-test savvy)` 后追加
   `target_compile_options(savvy-test PRIVATE -UNDEBUG)`
   （portability：Release 下激活上游 assert 校验，避免静默通过）
4. include/savvy/writer.hpp: SAV2 writer 的 s1r 索引临时文件路径由硬编码
   `/tmp/tmpfileXXXXXX` 改为优先用 TMPDIR/TMP（配方 `_ensure_writable_tmp`
   已注入可写目录并导出到 build 环境），并把 `if (!tmp_fd)` 修正为
   `if (tmp_fd < 0)`（mkstemp 失败返回 -1 为真值，原判断永远走不到错误分支）。
   根因：HMBS 真机 /tmp 只读，mkstemp 失败 → 索引不追加回 SAV 文件 →
   reader 内嵌索引加载失败 → random_access_test 的 reset_bounds 置 failbit。
5. include/savvy/utility.hpp: 补全「未自包含」的两个 include——`#include
   "typed_value.hpp"` 与 `#include <iostream>`。上游 utility.hpp 用
   `savvy::typed_value::is_end_of_vector`（line 63）与 `std::cerr/std::endl`
   （line 184）却分别未 include 对应头，只有在上游 test 传递包含时碰巧能编过；
   consumer 独立 include `<savvy/utility.hpp>`/`<savvy/savvy.hpp>` 即报
   `no member named 'typed_value' in namespace 'savvy'` / `no member named
   'cerr' in namespace 'std'`。补全后头文件自包含，任何消费者可直接使用
   （typed_value.hpp 位于同目录自身已 include <iostream>）。

五处改动均无 __OHOS__，纯 POSIX/头自包含修复（R8 合规）。

## 依赖版本
- libshrinkwrap/1.2.0（制品仓，header-library；其 requires xz/5.8.3.2、zlib/1.3.2.1、
  zstd/1.5.7.1）

## 验证结果（W4 本机前置，2026-10-13）
```text
1. 配方静态检查（本机）
   - python -m py_compile conanfile.py / test_package/conanfile.py   → 待执行
   - PyYAML 解析 conandata.yml / manifest.yaml / MANIFEST.yml        → 待执行
   - CI L0 门禁逐项自查（L0a~L0k）                                   → 待执行
   - git diff --check                                                → 待执行
2. 源码归档 SHA256 复核
   - 本机实测官方 tag 下载 83ebd88c...bf9e1de == conandata 声明值      → 一致
3. 本机未执行项（如实申报）
   - conan create / test_package 的 Conan 全流程实跑：本机无 conan → 待真机
   - OHOS aarch64 上的上游测试与消费者测试运行：待真机预检
```

## 注意事项
- 上游 reader/writer 头文件大量使用 assert() 做内部不变量检查；Release 下这些
  assert 在 sav 生产二进制中为 no-op（上游本意），仅测试目标被 -UNDEBUG 激活。
- 包是 header-only 库 + CLI 工具：consumers 有两种用法——链接 savvy::savvy 用库，
  或直接跑 bin/sav 做 SAV/VCF/BCF 转换。commands.json 声明了 sav。
- 上游 manual target 依赖 help2man，非默认构建目标，conan create 不触发。
- libshrinkwrap 若制品仓有 R37 冲突（libshrinkwrap/1.2.0 已存在其他 revision），
  需先确认其版本；本配方按 1.2.0 依赖。
- 真机预检失败时按规则对齐 hmbs 返回的日志（失败含 `HMBS 平台诊断` 时按错误码
  最小适配，不跳过上游测试套件）。

## 下一步（W6）
- 真机预检（hmbs 调度）→ 通过后由 HMBS 提交推送并以标题
  `【积分赛】feat(savvy): 2.1.0 适配 HarmonyOS PC` 创建 PR。
- PR 描述按 rule1/rule4/rule12 模板字段填写，上游测试数（5/5 及通过率）以真机
  预检证据回填。
