# libcuckoo-acp 0.3.1.1 适配笔记

**日期**: 2026-10-03
**状态**: ✅ built（conan-verify 通过，W3 本地 CI 模拟通过）

## 背景

libcuckoo/0.3.1 曾于 2026-08-10 适配并发布（da1987fb2d）。本次在积分赛事质量复核中
发现配方存在需修复的问题，按 R37 递增版本号为 0.3.1.1。

### 0.3.1 旧配方遗留问题（本次修复）

1. **CMake 4.x 兼容性修复方式错误**：旧配方只在 `generate()` 设置
   `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`，但 CMake toolchain 文件
   在 `project()` 时才加载，而 `cmake_minimum_required(VERSION 3.1.0)` 在其之前
   解析，CACHE 变量来不及生效 → CMake 4.x 下必然失败。正确做法是打补丁把
   `cmake_minimum_required` 改为 `(VERSION 3.5.0...3.31)`。
2. **package_type 修正**：libcuckoo 是 header-only 库，无编译产物，
   `package_type = "library"` + 虚假的 `cpp_info.libs` 会误导消费者。
   改为 `package_type = "header-library"`、清空 libdirs/bindirs。
3. **上游测试被错误地申报为 0/80 无法运行**（详见下）——本次已真实构建并运行，
   修复两个平台兼容小补丁后 **80/80 全部通过**。

## 上游测试真相（本次复核修正）

> 旧 notes.md / test-report.md / MANIFEST.yml 声称："上游捆绑 Catch v3 single_header
> 使用 std::uniform_int_distribution 触发 OHOS libc++ concept check 编译失败，
> 0/80 无法编译运行"。**该声明不准确**，经独立复核：

- 上游 v0.3.1 捆绑的是 **Catch v1.5.9**（2016，非 v3）。
- `std::uniform_int_distribution` 实际只出现在 stress-tests 中，Catch 本身不依赖它。
- 真正阻碍 unit_tests 编译的是：OHOS libc++ 强制 C++11 `[rand.req.urng]` 的
  `result_type` 必须为**无符号**整数，而 Catch v1.5.9 `RandomNumberGenerator` 用
  有符号 `std::ptrdiff_t` → `__libcpp_random_is_valid_urng` static_assert 失败。
  **1 行补丁**（`ptrdiff_t`→`size_t`）即可编译。
- 另有 1 个用例因平台限制失败：`test_c_interface` read/write SECTION 用 `tmpfile()`，
  OHOS `/tmp` 只读（E002）且 musl `tmpfile()` 硬编码 `/tmp` → NULL → SIGABRT。
  改用 `TMPDIR` 下 `mkstemp()` 后通过（已单独验证序列化逻辑本身正确）。

**修复后真实结果**（conan create 内 build() 执行 ctest）：
- unit_tests：80/80 TEST_CASE、203962 断言，100% 通过
- stress_checked / stress_unchecked：上游默认参数（power=25, threads=4, time=10s）通过
- test_package（消费者）：1/1 通过

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 源码 https://github.com/efficient/libcuckoo/archive/refs/tags/v0.3.1.tar.gz, sha256=a87122b9... |
| Step 2 patches | ✅ | 0001 CMake4.x 兼容；0002 Catch URBG result_type；0003 tmpfile→mkstemp |
| Step 3 configure | ✅ | CMakeToolchain + HarmonyOS toolchain（CMAKE_SYSTEM_NAME=HarmonyOS） |
| Step 4 make | ✅ | Header-only + 全部测试目标构建成功 |
| Step 5 install | ✅ | 头文件安装到 include/libcuckoo/ 与 include/libcuckoo-c/ |
| Step 6 safety | ✅ | 无危险二进制 |
| Step 7 check | ✅ | ctest: unit_tests 80/80 + stress_checked + stress_unchecked 全通过 |
| Step 8 staging | ✅ | 消费者冒烟测试 test_package 1/1 通过 |
| Step 9 package | ✅ | conanfile.py（header-library） |
| Step 10 deploy | ✅ | conan-verify G0-G4/L2/L4/L5 全部 PASS |
| Step 11 finish | ✅ | W3 本地 CI 模拟通过（.ci-result.json exit_code=0） |

## 知识沉淀

- **K1（L2）**：CMakeToolchain 的 CACHE 变量无法修复 `cmake_minimum_required < 3.5`
  问题（toolchain 在 project() 之后才加载）——必须打补丁改 CMakeLists.txt。
  适用于所有 `cmake_minimum_required < 3.5` 的项目在 CMake 4.x 下的适配。
- **K2（L2）**：OHOS libc++（>= 某版本）强制 C++11 `[rand.req.urng]` 的
  `result_type` 必须无符号；老测试框架/自研 URBG 用 `ptrdiff_t`/`long` 会在
  `std::shuffle`/`uniform_int_distribution` 处 static_assert 失败。
  修复：URBG 的 `result_type` 改为 `std::size_t` 等无符号类型。
- **K3（L2）**：OHOS `/tmp` 只读（E002）且 musl `tmpfile()` 硬编码 `/tmp`，
  任何依赖 `tmpfile()`/`/tmp` 临时文件的上游测试会失败；
  适配方式：改用 `TMPDIR`（或当前目录）下 `mkstemp()`，保持测试语义。
- **K4（L3）**：libcuckoo 是 header-only 库，`package_type=header-library`，
  无 cpp_info.libs；上游测试可完整运行（Catch v1.5.9 + stress）。
---

**编译结束**: 2026-10-03 20:31
**最终状态**: built
