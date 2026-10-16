# DRAFT：CMake add_test 带 CONFIGURATIONS 时 ctest 默认找不到测试

> Status: **Draft**（待审核 promote）| severity: `2` | category: `cmake|testing|ctest` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libvldmail-1.2.2-ctest-configurations-debug.kv`
> 来源: libvldmail 1.2.2 适配（https://github.com/dertuxmalwieder/libvldmail tag `release-1.2.2`，官方归档 sha256 `1cea5431b8c555959c2640faa64ed8d3e078044590f2c384b14f4db443ef8e0d`）
> 路径判定: 路径 B（无等价命中且候选可跨库复用）

---

**匹配关键词**：CONFIGURATIONS, Debug, add_test, ctest -C, No tests were found, ctest empty suite, single-config generator, CMake 测试注册

## 错误签名（error_signature）

```text
No tests were found!!!|ctest.*0 tests failed out of 0|add_test\([^)]*CONFIGURATIONS
```

## 预扫（prescan）

- `prescan_pattern`: `add_test\s*\(|CONFIGURATIONS\s+"Debug"|enable_testing\s*\(`
- `prescan_severity`: 2

> 触发面：工程 CMakeLists 用 `add_test` 且带 `CONFIGURATIONS` 参数即预扫命中。

## 问题

上游 CMakeLists.txt 用 `add_test(NAME xxx COMMAND xxx CONFIGURATIONS "Debug" ...)` 注册测试。
单配置生成器（Unix Makefiles / Ninja）下，默认构建配置是 Release，ctest 不带 `-C` 时
按当前配置过滤用例，`CONFIGURATIONS "Debug"` 的用例被全部过滤：

```text
Test project .../build-tests
No tests were found!!!
```

退出码仍是 0 —— 若据此判定"上游无测试"，会把真实存在的测试套件误判为 0 入口，
或把 0 结果当作通过统计，造成上游测试台账失实（R51 口径违规）。

## 根因（root_cause）

`add_test(NAME ... CONFIGURATIONS "Debug")` 把用例限定在 Debug 配置；
单配置生成器下 ctest 默认使用构建配置（Release），`-C` 未指定时两者不匹配，
用例被过滤 → ctest 报 "No tests were found!!!"（exit 0，不是失败，是空套件）。

## 方案（rec_approach）

1. 用 `ctest --test-dir build-tests -C Debug --output-on-failure` 命中 Debug 注册的用例；
2. 或直接运行测试二进制（如 `./build-tests/vldmailtest`），绕过 CTest 配置过滤，
   得到真实逐项结果（libvldmail 实测 `ok ×11, 1..11`）；
3. 台账按真实入口登记（此处 vldmailtest + autotest-cases 11 断言），不得登记为 0。

## 验证（verification_cmd）

```bash
# 复现错误形态
ctest --test-dir build-tests --output-on-failure        # → No tests were found!!!
# 正确运行
ctest --test-dir build-tests -C Debug --output-on-failure  # → 1/1 Passed
./build-tests/vldmailtest                                 # → 1..11 all ok
```

## 适用边界（affected_scope）

- 一切 `add_test` 带 `CONFIGURATIONS`（Debug/Release）注册测试的 CMake 工程；
- 影响面是上游测试台账与 W3/CI 中的测试统计，不是库编译本身。

## 反例与限制

- 多配置生成器（Visual Studio/Xcode）由 `-C` 语义不同，需按生成器实际配置处理；
- 若测试确实无条件注册（无 CONFIGURATIONS），默认 ctest 即可命中，本条目不适用；
- "No tests were found" 也可能来自真无测试的工程，需结合 `add_test` 是否带 CONFIGURATIONS 判断。
