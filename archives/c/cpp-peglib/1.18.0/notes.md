# notes.md — cpp-peglib 1.18.0 适配证据

## 1. 包与源码
- 上游：https://github.com/yhirose/cpp-peglib（本仓已有 1.15.0 / 1.17.0，本次是 **1.17.0 → 1.18.0 版本升级**）
- 源码归档：`https://github.com/yhirose/cpp-peglib/archive/refs/tags/v1.18.0.tar.gz`
  sha256 `35cfae68f6e828f066df3c3c9ecce53765a67f780133c96a39f6dc49c8973c62`
  （本机 `curl` + `sha256sum` + `tar tzf` 三重校验，顶层目录 `cpp-peglib-1.18.0/`）
- 类型：C++17 **header-only INTERFACE 库**（`package_type = "header-library"`），
  制品里只有 `include/peglib.h` + `licenses/LICENSE`（MIT）。
- 零源码补丁（`patches_applied: []`）。

## 2. 与 1.17.0 的差异（本次升级要动的地方）
| 差异 | 影响 |
|------|------|
| 新增 `CPPPEGLIB_VERSION "1.18.0"` / `CPPPEGLIB_VERSION_NUM "0x011200"` | 消费者用例可直接核对头文件版本（见 test_package.cpp 第 1/2 项） |
| `test/CMakeLists.txt` 注册 **两个** target（`peglib-test-main` + `peglib-test-blob-roundtrip`，后者把每条语法从序列化 blob 重新加载） | 上游 CTest 用例数从 1.17.0 的 520 涨到 **1176** |
| `PEGLIB_BUILD_BENCHMARK` 默认变 **ON** | 配方显式 `-DPEGLIB_BUILD_BENCHMARK=OFF`（否则 `benchmark/` 会额外拉依赖） |
| 其余（`install(FILES peglib.h DESTINATION include)`、`add_library(peglib INTERFACE)`、CMake ≥ 3.14、gtest 走 FetchContent 固定 commit）与 1.17.0 一致 | 配方结构沿用 1.17.0，只改版本/sha 与测试统计 |

## 3. OHOS 侧要点
| # | 事项 | 说明 |
|---|------|------|
| R1 | 无运行期产物 | header-only ⇒ 没有 ELF，签名（`.codesign`）/加载器/SONAME/RPATH/壳层这些平台约束**在结构上不适用**；本包在 OHOS 上的真实验证 = 消费者用例在 OHOS clang + C++17 下真编译真运行 + 上游 1176 用例在 worker 上真跑。`test_layout.py` 的 M4 反过来把「包内不得出现任何 ELF」当成交付形态契约来核对 |
| R2 | 上游套件是硬门禁 | `build()` 内 `ctest --output-on-failure`，解析 `N% tests passed, M tests failed out of K`；`M≠0`、`N≠100`、`rc≠0` 或 `K==0`（套件没真跑）一律 `ConanException` 中断构建 |
| R3 | `package_id()` 清空 | 包内只有一个头文件，与编译器/build_type/架构无关，避免重复构建 |
| R4 | gtest 由上游 FetchContent 拉取（需网络） | worker 可达 github.com；已合入的 1.17.0 就是这样跑完 520 用例的 |

## 4. 本机验证（这台机器是 x86_64 的 Linux，但 header-only 包可本机端到端）
1. **上游套件全量真跑**：`cmake -S . -B build -DBUILD_TESTS=ON -DPEGLIB_BUILD_BENCHMARK=OFF -DPEGLIB_BUILD_EXAMPLES=OFF -DPEGLIB_BUILD_LINT=OFF -DPEGLIB_BUILD_PL0=OFF -DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=<codeload 取回的 googletest>` → `cmake --build build` → `ctest`：
   ```
   100% tests passed, 0 tests failed out of 1176
   Total Test time (real) =   3.97 sec
   ```
   （本机 github.com 不可达，故用 codeload 取同一 commit 的 googletest 并让 FetchContent 用它 —— 这只是本机的网络绕行，CI 上仍走上游原有 FetchContent。）
2. **消费者用例**：`g++ -std=c++17 -Wall -Wextra -I<src> test_package.cpp && ./a.out` ⇒ **10 checks, 0 failure(s)**，零告警。
   本地迭代修掉了 5 个真实的 API 误用（`sv[i].get<T>()` 不存在要用 `std::any_cast`、`sv.token()` 在 1.18 返回 `string_view` 需 `token_to_string()`、`parser.log` 在 1.18 是私有需改用 `set_logger()`、`~` 是**规则名前缀**而不是字面量前缀、带 void 动作的规则在括号分支里取不到语义值）—— 这 5 个如果直接推 CI 至少要 5 轮。
3. **交付形态自检**：`test_layout.py` 指向「只有 include/peglib.h + licenses/LICENSE」的真实目录跑 8/8 通过。

## 5. CI 第 1 轮（build #95115 / b109434，2026-10-16 17:33–17:46）暴露的问题与修法
- **现象（逐字）**：七步全跑到 `conan-build-test`，上游 1176 用例与消费者用例**都已通过**，卡在**交付形态自检**：
  ```
  [FAIL] M5 include/ 下只有 peglib.h (include/=['gmock', 'gtest', 'peglib.h'])
  [FAIL] M7 包内无 .o/.a/.la/.pyc/.so 残留、无隐藏文件（JC5）
         (stray=['lib/libgmock.a', 'lib/libgmock_main.a', 'lib/libgtest.a', 'lib/libgtest_main.a'] hidden=[])
  [layout] checks=8 passed=6 failed=2 skipped=0
  [layout] FAILED: M5 include/ 下只有 peglib.h, M7 包内无 .o/.a/.la/.pyc/.so 残留、无隐藏文件（JC5）
  ERROR: cpp-peglib/1.18.0 (test package): Error in test() method, line 41
  ```
- **根因**：`package()` 里的 `cmake.install()`。1.18.0 的 `test/CMakeLists.txt` 用 FetchContent 引入
  googletest，而 googletest 自己的安装规则默认 **`INSTALL_GTEST=ON`** ⇒ `cmake --install` 把
  `include/gtest`、`include/gmock` 与 4 个 `lib/lib{gtest,gmock}*.a` 装进了**这个 header-only 包**。
  1.17.0 沿用同样的 `cmake.install()` 写法，但当时没有 M5/M7 这两条判据，所以这个污染一直没暴露。
- **修法**（本包在这轮里唯一的改动）：
  1. `generate()` 显式 `tc.variables["INSTALL_GTEST"] = False` —— 从根上关掉 vendored googletest 的安装规则；
  2. `package()` 追加 `_purge_vendored_gtest()` 兜底清理 `include/gtest*`、`include/gmock*`、
     `lib/libgtest*`、`lib/libgmock*` 与清空后的空 `lib/`，保证即使在别的 googletest 版本/配置下
     也不会再漏。**没有放松任何判据**（M5/M7 保持原样），也没有引入任何断言 —— 修的是制品的真实内容。
- **修后本机端到端复跑**（`conan create <pkgdir> -pr default -nr`，x86_64 Linux；FetchContent 用本机
  googletest 源目录绕开 github 不可达）：
  ```
  cpp-peglib/1.18.0: [upstream] ctest: 100% passed, 0 failed out of 1176 (rc=0)
  cpp-peglib/1.18.0: [upstream] 1176 upstream CTest cases passed
  consumer use case: 10 checks, 0 failure(s)
  [layout] checks=8 passed=8 failed=0 skipped=0
  ```
  最终制品目录逐字为：
  ```
  p/include/peglib.h
  p/licenses/LICENSE
  p/conaninfo.txt  p/conanmanifest.txt
  ```
