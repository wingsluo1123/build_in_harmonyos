# libcopp 2.2.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4 (LLVM) / OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`
- 状态: built（`conan create` 全绿，含上游单测与消费者测试）

## 软件定位

libcopp 是 C++ 协程库：协程上下文切换 + 协程任务调度器，同时支持 C++20
coroutine 与手写汇编双实现。上下文切换核心是 `src/libcopp/fcontext/asm/`
下的 **per-ABI 手写汇编共 72 个文件**（`jump/make/ontop` × 各架构 ABI），
aarch64 用 `*_arm64_aapcs_elf_gas.S`（callee-saved 寄存器成组保存恢复 +
栈指针切换 + 返回地址搬运，无法用 C 重写）。

## 编译步骤

```bash
conan create archives/l/libcopp/2.2.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -r=ohpcd
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 设备上编 x86_64 汇编，`jump_x86_64_sysv_elf_gas.S:138: error: invalid operand / jmp *%r8` | CMake 在 HarmonyOS 上报 `CMAKE_HOST_SYSTEM_PROCESSOR=unknown`；上游 `fcontext.detect.cmake` 的 `MATCHES "unknown\|i386\|i686\|x86_64\|amd64"` 分支按 `CMAKE_SIZEOF_VOID_P=8` 把 `unknown` 硬回退成 `x86_64` | 配方注入 `-DLIBCOPP_FCONTEXT_OS_PLATFORM=arm64`（armv8 ⇒ arm64）；探测输出随即恢复 `arm64/aapcs/elf/gas`，三个汇编文件正确选中 `*_arm64_aapcs_elf_gas.S` |
| 2 | configure 阶段 `include could not find requested file: IncludeDirectoryRecurse` / `EchoWithColor` | 上游 tag 归档**不含 git submodule**：`atframework/cmake-toolset` 是空目录；`.gitmodules` 钉在 commit `c911fe34`，且 v2.2.0 无 release 资产 | conandata 增加第二个源，按钉住 commit 取 codeload 快照，`source()` 里铺进 `atframework/cmake-toolset/` |
| 3 | 消费者 `find_package(libcopp)` 会命中上游自带的 `libcopp-config.cmake`（其内 `include(libcopp-targets.cmake)`，conan 不生成该文件） | 上游 `install` 规则把自用 CMake config 一并安装 | `package()` 里 `rmdir` 掉 `lib/cmake` 与 `share`，让 CMakeDeps 生成的 config 成为唯一权威 |
| 4 | `AttributeError: 'CMake' object has no attribute 'build_folder'` | 配方 `build()` 里误用 `cmake.build_folder` | 改用 `self.build_folder`（`CMake` 工具对象没有该属性） |
| 5 | 消费者只链 `-lcopp` 时 `ld.lld: error: undefined symbol: cotask::v2002::this_task::get_task()` | 包内同时交付 `libcopp.a` 与 `libcotask.a`，而 `package_info` 只报了 `copp` | `package_info.libs = ["cotask", "copp"]`（W4 审计 P1-1） |

## 源码修改

**零源码补丁**：唯一必要改动是 CMake 变量注入（`-DLIBCOPP_FCONTEXT_OS_PLATFORM=arm64`），
属配置期改动，不改上游任何一行源码与汇编。

## 验证结果

**上游单元测试（配方 build() 内 ctest 真实执行，`--no-tests=error` 防空跑假绿）**

- conan profile（`compiler.cppstd=17`）下：`100% tests passed, 0 tests failed out of 1`
  （ctest 注册 1 个聚合目标 `libcopp.unit_test`），二进制内部 **64/64 test case PASSED**。
- 同源码在原生 clang 默认配置下（`COMPILER_OPTIONS_TEST_STD_COROUTINE=1`，即 C++20
  coroutine 路径启用）：**144/144 test case PASSED**（38998 ms）。
- 两种配置**通过率均为 100%**，满足路径 C 的「≥90% 通过率」口径；差异只在
  C++20 coroutine 子集是否被 `cppstd=17` 的 profile 关闭。

**消费者测试（test_package）**

真实编译并运行一次协程上下文切换 `create -> start ->（runner 内 yield）-> resume -> 取返回码`：

```
LIBCOPP_STEP created
LIBCOPP_STEP inside-runner
LIBCOPP_STEP started-and-yielded
LIBCOPP_STEP resumed
LIBCOPP_STEP finished
LIBCOPP_TEST PASSED
```

这条路径必须经过打包进产物的 arm64 fcontext 汇编 ⇒ 同时证明：打包进去的确实是
arm64/aapcs 实现（不是被 `unknown => x86_64` 误选的 x86_64 汇编），且它在 OHOS 上
真的能切换栈并取回返回码。

## 依赖

- 运行期：仅 `Threads`（pthread），无其它外部库。
- 构建期：**无任何外部测试依赖**。上游 `test/` 用的是自带的 `test_manager`
  （`test/frame/test_manager.cpp`）；`test/CMakeLists.txt` 里的 `find_package(GTest)`
  是**非 REQUIRED** 的可选门，且代码真正检查的宏是 `UTILS_TEST_MACRO_TEST_ENABLE_GTEST`
  （`test/frame/test_macros.h:26`），而 CMake 定义的是 `COPP_MACRO_TEST_ENABLE_GTEST`
  ⇒ gtest 分支在上游就是死代码，缺 gtest 测试照跑（W4 审计实证：`link.txt` 无 gtest 库、
  `nm -C libcopp_unit_test | grep -c "testing::"` = 0）。**本版配方据此删除了 googletest 依赖。**
- 交付产物：`libcopp.a` + **`libcotask.a`**（协程任务调度器，依赖 copp）与两者头文件；
  `package_info.libs = ["cotask", "copp"]`（顺序不可反，静态库按命令行顺序解析符号）。
---

**编译结束**: 2026-10-15 03:33
**最终状态**: built
