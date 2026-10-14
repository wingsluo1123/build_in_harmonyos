# tuning 1.1.0 适配笔记

## 编译环境
- 上游工程: **tuning-library**（Surge Synth Team Tuning Library，https://github.com/surge-synthesizer/tuning-library，tag `release_1.1.0`）
- 库类型: **header-only C++14**（CMake `add_library(tuning-library INTERFACE)`，2 个头文件）
- 构建系统: cmake（`cmake_minimum_required(VERSION 3.10)`）
- 编译日期: 2026-10-04
- 编译器: OHOS clang 15.0.4（`aarch64-unknown-linux-ohos`）+ libc++；CMake 4.1.2 / Ninja 1.13.1
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / Release）
- 状态: built
- 补丁: **无**（库本体零补丁）

## 源码核验
- 官方源（R39）: `https://github.com/surge-synthesizer/tuning-library/archive/refs/tags/release_1.1.0.tar.gz`
- sha256: `32b908494cd96fa7f92307df842356a5f3c9469d7ec7c14c8db063e70a41cf46`（实测 `sha256sum` 一致；HTTP 200，size=140050）
- tarball 内容: 52 个文件，含 `include/Tunings.h`、`include/TuningsImpl.h`、`tests/alltests.cpp`、
  `tests/data/`（28 正常样本 + 10 坏样本）、内置 `libs/catch2/catch2.hpp`（Catch2 2.9.2 单头）、
  `commands/showmapping.cpp`、`commands/parsecheck.cpp`
- R47 语言预检: task=cpp / detected=cpp（构建系统 cmake；源文件主体 100% cpp）→ 通过

## 编译步骤

1. `conan create archives/t/tuning/1.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
2. `generate()`:
   - OHOS 下 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`（E092）
   - OHOS 下前置 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` 到 `LD_LIBRARY_PATH`（E266）
3. `build()`: `cmake.configure()` → `cmake.build()`（默认构建 INTERFACE 库 + tests + symbolcheck + 2 个 CLI）→ `_run_upstream_tests()`
4. `package()`: 上游无 install 规则，手写 `copy("*.h", include/, package/include)` + `LICENSE.md` → `licenses/`
5. 上游测试（层 1，失败即 `conan create` 失败）：`tuning-library-tests`（18 TEST_CASE）+
   LANG 矩阵（es_ES/fr_FR/zh_CN/空）+ `symbolcheck` + `parsecheck`/`showmapping` CLI 样例
6. `test_package`（层 2）：`ctest` 跑 `test_tuning` + `test_tuning_harmonyos`（鸿蒙特有）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | E092：`-DCMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake 打印 `System is unknown to cmake, create: Platform/HarmonyOS`，且对象文件扩展名退化为 `.obj`（平台语义错误） | CMake 没有 HarmonyOS platform module，`CMAKE_SYSTEM_NAME` 匹配不到任何已知平台 | `generate()` 显式 `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"` + `["CMAKE_SYSTEM_PROCESSOR"]="aarch64"`（conan `arch=armv8` 不是合法 CMake processor 名）。复现/复验日志：`reports/upstream-test-logs/13_repro_E092_configure.log`、`14_repro_E092_build.log` |
| 2 | E266：OHOS SDK 的 lld 动态依赖 `libxml2.so.16`（二进制已 strip、无 RUNPATH），部分 worker 默认库搜索路径找不到 → 链接器启动失败 | SDK llvm/lib 不在默认搜索路径 | `generate()` 中 `Environment().prepend_path("LD_LIBRARY_PATH", ".../ohos-sdk_26.0.0.18/ohos/native/llvm/lib")`（expected-lite / aeolus 同方案）。本机实测该路径已可达，属预防性配置 |
| 3 | 上游测试样本以 `tests/data/...` 相对路径读取，`conan create` 下 build_folder ≠ source_folder 时会「找不到样本」 | 上游 `run-all-tests` 用 `WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}`，未在测试内 chdir | 配方测试执行统一以 `cwd = 源码根`（`_data_root()` 定位含 `tests/data` 的目录），与上游同口径 |
| 4 | Catch2 2.9.2 用 `-r junit::file.xml` 报 `Unrecognized reporter` | Catch2 v2 的 `-r` 不接受 `::output-file` 语法 | 改用 `-r junit -o upstream_junit.xml`（`-o` 单独指定输出文件）；`--list-reporters` 实测确认可用 reporter 为 compact/console/junit/xml |
| 5 | `test_package/test_tuning.cpp` 首轮 2 项断言失败：`parseSCLData` 的 `name` 不等于文件头描述；白键 KBM 的音符映射假设错误 | 上游 `parseSCLData()` 固定 `res.name = "Scale from patch"`（`TuningsImpl.h:202`），文件头文本进的是 `description`；KBM `middleNote=60` 起按 entries 顺序映射，白键为 60/62/64/65/67/69/71 | 断言改为 `name == "Scale from patch"` + `description` 校验；映射断言改为 60/62/64/65 mapped、61/63 unmapped。复验 28/28 通过（`reports/conan-create-console.log`） |
| 6 | `conan-verify` G2 首轮 FAIL：`Error in source() method` → `https://ghfast.top/...` SSL hostname mismatch + read timeout | 本地 `conan-verify` 会把 conandata 的 github.com 改写为 **ghfast.top** 镜像，该镜像当前不可达；改写后只剩单一 URL，无回退 | 配方 `source()` 在（可能被改写为镜像的）URL 之后**追加官方源**作为回退（与 CI `get_mirror_list` 的 `[mirror, url]` 口径一致），`sha256` 强校验不降低完整性。复验 G0-G4/L2/L4/L5 全 PASS。日志：`reports/conan-verify-run1-ghfast-down.log`（失败原文）、`reports/conan-verify-run2-pass.log`（通过） |

**首轮真实构建结果**：源码 configure + build **零错误零警告失败**（`reports/upstream-test-logs/10_explore_configure.log`、
`11_explore_build.log`）；上方第 1/2 项是**平台适配项**（在 conan 配方中落地并复现取证），第 3-6 项是本流程中真实踩到并修复的错误。

## 依赖版本

- 库本体第三方依赖: **无**（头文件只 `#include` `<string> <vector> <iostream> <memory> <array> <iomanip> <fstream> <cstdlib> <math.h> <sstream> <cctype>`）
- 上游测试框架: **源码包内置** `libs/catch2/catch2.hpp`（Catch2 2.9.2 单头）→ 配方不需要 `catch2` conan 包
- W0 预检（R35，`conan download -r=ohpcd`）: `catch2/2.13.10` rc=0 可消费（若将来改用 conan catch2 可直接引用）；
  上游内置版本号 `catch2/2.9.2` 在 ohpcd 缺失（rc=1），故采用内置单头，零依赖

## 验证结果

```bash
# ① 真实构建（探索性，OHOS clang 15）
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++   # rc=0
cmake --build build -j4                                                                                    # rc=0（9/9 目标）

# ② 上游测试（cwd=源码根）
./build/tuning-library-tests                       # rc=0 → All tests passed (242371 assertions in 18 test cases)
LANG=es_ES|fr_FR|zh_CN|"" ./build/tuning-library-tests   # 4 次 rc=0，各 18/18
./build/tuning-library-symbolcheck                 # rc=0 → 100 and 200 are 100 and 200
./build/parsecheck tests/data/*.scl tests/data/*.kbm tests/data/bad/*   # 31 PASSED / 7 FAILED(坏样本预期) / 0 SKIPPED
./build/showmapping tests/data/12-intune.scl [tests/data/mapping-whitekeys-a440.kbm]   # rc=0，128 音符映射表

# ③ conan create（CI 同口径）
conan create archives/t/tuning/1.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64   # rc=0
#   [upstream] 18/18 TEST_CASEs passed, 242371 assertions, 61/62 sections executed
#   HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 2, "passedCount": 2}
#   100% tests passed, 0 tests failed out of 2

# ④ conan-verify
python3 scripts/ohc-run.py conan-verify tuning 1.1.0   # G0-G4 + L2/L4/L5 全 PASS，可标记 published
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | header-only 配方（含上游测试集成 + OHOS 平台映射 + 源回退） |
| `conandata.yml` | 官方源 URL + sha256（无补丁） |
| `test_package/` | `test_tuning.cpp`（28 断言）+ `test_tuning_harmonyos.cpp`（9 断言，**鸿蒙特有**） |
| `test_package/MANIFEST.yml` | 上游测试声明（R51 申报表） |
| `reports/test-report.md` | 测试报告（逐用例 + 断言 + 日志路径） |
| `reports/upstream-test-logs/` | 上游测试原始日志 + junit XML + LANG 矩阵 + locale 实测 |

## 注意事项

- 任务给定名为 `tuning`，真实上游工程名为 **`tuning-library`**（Debian 源码包 `tuning-library 1.1.0+ds-4` / 二进制包 `libtuning-library-dev`；PyPI/crates.io 的 `tuning` 与本库无关）。Conan 包名沿用任务给定名 `tuning`，`package_info` 的 CMake 文件/目标名为 `tuning` / `tuning::tuning`。
- 库本体 header-only、零第三方运行时依赖；`package_type = "header-library"`，无 `bin/` 产物 → 依据 R38 **不需要** `commands.json`（`showmapping`/`parsecheck` 为上游源码树内样例，上游未安装、包内不导出）。
- OHOS 目标机缺 es_ES / fr_FR locale 数据，上游 1 个 SECTION 按设计跳过；**未改动上游测试源码**，仅如实记录。
- 本笔记中所有命令与日志路径均为真实执行记录；`reports/upstream-test-logs/` 内的日志由探索构建与 `conan create` 两轮真实运行产生。
## 对话记录

### 对话 #1 — 2026-10-04 任务下发与适配执行

- 任务：适配 `tuning` 1.1.0 到 HarmonyOS PC（OHOS aarch64），要求上游测试实际执行并逐用例汇报。
- 依赖结论（前置批次已产出）：唯一第三方触点是测试框架 Catch2，且上游源码包**内置** `libs/catch2/catch2.hpp`；
  库本体零第三方运行时依赖 → 无 R36 阻塞，无需先发布依赖。
- 处置：
  1. worktree 从 `origin/main`（1262b4ac24，2026-10-04 06:36）切出，分支 `feat/tuning-1.1.0`；
  2. 源码取官方 GitHub release archive，sha256 实测 = `32b90849…cf46`；
  3. 探索构建（cmake + OHOS clang 15）首轮 configure/build **零错误**；
  4. `conan-verify` 首轮 G2 失败（ghfast.top 镜像不可达）→ 配方 `source()` 增加官方源回退 → 次轮 G0-G4/L2/L4/L5 全 PASS；
  5. `conan create` rc=0：上游 18/18 TEST_CASE 通过（242371 断言），test_package 2/2 通过；
  6. `finish tuning 1.1.0 built` → W2/W3 通过，`.ci-result.json` exit_code=0。
- 遗留（如实记录）：
  - `finalize-archive` 的 “补丁数不一致: manifest=1 vs disk=0” 是工具对 `patches_applied: []` 的 `str()` 解析问题
    （空列表被算成 1 项），本包**确实零补丁**，语义以 `patches_applied: []` 为准；
  - 本仓以 Conan 包分发（header-only → 无 `bin/`、无 `release/debug tar.gz`），
    `finalize` 的 “缺少 release/debug tar.gz” 属分发形态差异，见 `packaging/README.md`；
  - `G0 干净构建验证` 是 autotools 专用（固定执行 `./configure --prefix=…`），对 CMake 包必然 exit 127；
    权威干净构建验证由 G2 `conan create` 承担（PASS）。
- 未执行（按用户要求停在此处等待确认）：`commit` / `push` / `Issue` / `PR` / 上传制品 / 远端 Review。
---

**编译结束**: 2026-10-11 20:02
**最终状态**: built
