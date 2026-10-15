# test_package 在 Release/NDEBUG 下 assert 型断言是恒真空壳（R34）

**条目**: `DRAFT-cpp-member-accessor-1.0.0-test-package-ndebug-assert-shell-check`
**来源**: cpp-member-accessor 1.0.0 · PR #11988 赛事 Review R34 判定
**状态**: DRAFT

## 问题

Conan `test_package` 以 profile 的 `build_type`（本项目为 **Release**）构建。
CMake Release 默认编译选项含 `-DNDEBUG`，`<cassert>` 在定义 NDEBUG 时把
`assert(expr)` 展开为 `((void)0)`：

- 断言内表达式（连同被测 API 调用）整体被丢弃、**永不求值**；
- 若 test_package 的全部校验都写在 `assert()` 内，编译产物实际只剩
  「构造对象后 `return 0`」，任何核心功能回归都不会让测试失败，
  `conan create` 永远 G2 PASS —— 等效 **R34 禁止的恒真空壳**。

断言「存在」≠ 校验「有效」：必须保证被测 API 调用真实执行、且失败能
映射为进程非零退出码。

## 判定口径

- 不能因「写了 assert」或「API calls / asserts 计数」宣称校验有效；
- 必须能给出**受控失败变体**的非零退出码证据（failcap）；
- 不得通过移除/放宽 Release 口径、改 profile `build_type` 绕过；
- 不得删除或削弱原有断言语义。

## 落地做法（可直接复用）

1. **自计失败数 CHECK 宏**（推荐，任何 build_type 下校验恒真实）：

   ```cpp
   int g_failures = 0;
   #define CHECK(cond)                                                          \
       do {                                                                      \
           if (!(cond)) {                                                        \
               std::fprintf(stderr, "[test-package] CHECK FAILED: %s (line %d)\n", \
                            #cond, __LINE__);                                    \
               ++g_failures;                                                     \
           }                                                                     \
       } while (0)
   ```

2. 全部校验改 `CHECK(...)`，断言语义与参数校验等价或更强（不得削弱）；
3. `main()` 末尾按 `g_failures` 返回 0/非零（非零即失败）；
4. 可选路线：test_package 构建显式 `-UNDEBUG`（须证明真实生效）。

## 验证（cpp-member-accessor 1.0.0 实证）

1. **NDEBUG 丢弃证明**：对同一 `test.cpp` 加/不加 `-DNDEBUG` 分别 `clang++ -E` 预处理——
   不加时 `__assert_fail` 6 次且断言表达式完整保留（`expr || __assert_fail(...)`）；
   加 `-DNDEBUG` 后 `__assert_fail` 仅剩声明 1 次、断言展开为 `((void)0)`（6 处），
   断言内符号引用 3→2 次（断言内那次被丢弃）。
2. **修复**：5 处 `assert` → 自计失败数 `CHECK` 宏，`main` 返回 `g_failures`。
3. **failcap**：临时把期望值 100 改 999，Release/NDEBUG 口径运行输出
   `[test-package] CHECK FAILED: ... == 999 (line 62)` + `1 CHECK(s) FAILED`，**RC=1**；
   交付态无该变体。
4. **修复后**：`conan create`（Release）test_package 1/1 passed。

## 适用边界与反例

- 适用：任何 Conan `test_package` 用 `assert()` 做校验、且以 Release/NDEBUG
  构建的库（跨库可复用）。
- 不适用：上游源码内 `assert(副作用表达式)` 场景——那是 E259
  （`hoist-side-effect-out-of-assert`）的范畴，机制同源但修复路线不同。
- 反例（不得做）：移除 Release / 改 build_type 绕过；仅加 printf 不构成
  fix；删除或弱化原断言语义；`#define NDEBUG 0` 掩盖问题。

## 关系

- related: R34, R39
- similar_to: E259（机制同源：NDEBUG 使 assert 不求值；主体不同）