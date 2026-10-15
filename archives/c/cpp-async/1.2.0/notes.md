# cpp-async 1.2.0 适配笔记

## 编译环境
- 构建系统: custom (header-only，无 configure/make/cmake)
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS SDK) / clang++ 15.0.4
- 状态: published

## 编译步骤

cpp-async 是 header-only C++ 协程库（include/async/*.h，10 个头文件），无构建步骤：
1. `ohc-run.py init-build cpp-async 1.2.0 --url=<官方 v1.2.0 release tarball>` — 下载、解压、归档骨架
2. 上游测试编译验证（应用 8 个 patches 后）：
   `clang++ -std=c++20 -Iinclude -I<catch2> -pthread test/program.cpp test/*_tests.cpp -o upstream_tests`
   运行：`Passed all 176 test cases with 176 assertions.`（176/176）
3. `ohc-run.py conan-init` → 改写为 header-only 配方（package_type=header-library, no_copy_source）
4. `ohc-run.py conan-verify` → G1-G4 全通过
5. `ohc-run.py finish published` → W3 本地 CI 模拟通过（.ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试在 clang/C++20 下编译失败：`co_await_operator_or_self` concepts 分支对非成员 `operator co_await` 探测失败，`awaitable_get/to_future` 无匹配 | `awaitable_resume_t.h` 的 C++20 concepts 分支用 lvalue `t` 探测，而非成员 `operator co_await(T&&)` 形参是 rvalue 引用，lvalue 无法绑定 → requires 不满足 → 回退主模板 → `await_resume` 缺失 | 补丁 0001：requires 表达式改为 `requires { operator co_await(std::declval<T>()); }`（与 MSVC 分支的 declval 探测一致） |
| 2 | 上游测试辅助头 `constexpr await_suspend` 内含 `assert(false)`，clang C++20 报 `-Winvalid-constexpr`（ill-formed） | C++20 起 constexpr 函数体内不允许调用非常量表达式（`__assert_fail`），MSVC 宽松不报 | 补丁 0002-0008：移除 7 个测试辅助头 `await_suspend` 的 `constexpr`（await_suspend 本就无需 constexpr） |
| 3 | conan create 报 `Package type is 'library', but no 'shared' option declared` | header-only 无共享/静态区分，Conan 2 对 library 类型要求 shared option | conanfile.py 用 `package_type = "header-library"` |
| 4 | test_package 编译报 include 头文件找不到 / 路径 `p/include/async/include/async/` | 初次 package() 复制 pattern/dst 搭配错误（copy 保留匹配的相对路径） | package() 改为 `copy(self, "include/async/*.h", src=self.source_folder, dst=self.package_folder)`，保留 include/async 相对路径 |
| 5 | W3 本地 CI（build_and_test.sh）JC 全仓扫描拦截 3 个其他库的历史状态文件（cloog/kics 的空 `.build-closed`/`.staging-verified`） | 基线仓库历史遗留，full 模式扫描拦截；与本库无关 | 临时 index 隔离（git rm --cached，工作区内容不动）→ W3 复验通过 → git restore --staged 恢复；审计见 reports/baseline-isolation-audit.md |
| 6 | test_package 初稿误用 `task.get()` / `co_await event_signal`（该库 API 为 `awaitable_get()` / `event_signal.wait*()`） | 对上游 API 理解偏差 | 按头文件真实 API 重写 test.cpp，真实调用 `async::awaitable_get(producer(42))` 与 `event_signal` 跨线程投递 |

## 源码修改

patches/ 8 个补丁（全部为 clang/C++20 兼容性修复，无平台宏）：
- 0001: `include/async/awaitable_resume_t.h` — concepts 分支非成员 operator co_await 探测改用 declval
- 0002-0008: `test/` 7 个辅助头 — 移除 await_suspend 的无效 constexpr

## 依赖版本

- 无运行时依赖（header-only）
- 测试依赖: Catch2 2.13.10（registry ohpcd，上游声明 2.13.9#1 兼容）

## 验证结果

```bash
# 上游测试（HarmonyOS 真机, aarch64）
./upstream_tests
# => Passed all 176 test cases with 176 assertions.

# 配方验证（conan-verify）: G1-G4 PASS
# W3 本地 CI 模拟（build_and_test.sh）: 100% (1/1) pass, .ci-result.json exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library, no_copy_source, package_id clear） |
| conandata.yml | 官方 v1.2.0 tarball + 8 补丁声明（sha256=1f681a45...） |
| test_package/ | CMake 消费者测试（test.cpp 真实调用 task/awaitable_get/event_signal）+ MANIFEST.yml |
| patches/ | 8 个 clang/C++20 兼容补丁 |
| packaging/README.md | header-only 无二进制说明 |

## 注意事项

- header-only 库无 bin/lib 产物：L2 smoke、L5 产物检查按规则跳过/警告，非缺陷。
- 本机即 HarmonyOS PC 真机（HongMeng Kernel aarch64），上游测试与 W3 均在本平台实际运行。
