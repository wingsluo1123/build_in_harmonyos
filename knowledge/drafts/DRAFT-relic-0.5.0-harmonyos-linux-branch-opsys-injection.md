# DRAFT-relic-0.5.0-harmonyos-linux-branch-opsys-injection

> 症状：**零错误**的平台分支静默落空 ｜ 解法：配方层注入该分支唯一产出的派生 cache 变量（零补丁）
> 实证：relic 0.5.0 @ HarmonyOS PC（conan 2.29.1 + CMake 4.1.2 + clang 15.0.4 aarch64），2026-10-15

## 症状（可复现）

上游 configure **完全成功、退出码 0、无任何 error**，但输出里平台判定是空的：

```
-- Configured operating system:
```

对照产物侧的三条静默退化（同一份源码、同一套参数，只差一个 `-DOPSYS`）：

| 读数 | 不注入 | 注入 `-DOPSYS=LINUX` |
|---|---|---|
| `Configured operating system:` | （空） | `LINUX` |
| `CMakeCache.txt` 的 `TIMER` | `ANSI` | `HPROC` |
| `grep -rl _GNU_SOURCE --include=flags.make \| wc -l` | **0 / 36** | **36 / 36** |
| `relic.dir` / `test_*.dir` 的 `link.txt` 中 `-lrt` | 无 | 有 |
| 安装头 `include/relic_conf.h` 的 `#define TIMER` | `ANSI` | `HPROC` |

上游 18 个 ctest 目标在**两种配置下都能全绿**——所以这不是"编不过"，而是"编出来的
东西悄悄少了三样能力"，靠常规构建/测试信号永远发现不了。

## 根因

`relic-relic-toolkit-0.5.0/CMakeLists.txt:183`：

```cmake
# Discover the operating system.
if(CMAKE_SYSTEM_NAME STREQUAL Linux)
    set(OPSYS "LINUX" CACHE STRING "Operating system")
else()
    ... FreeBSD / Darwin ...
endif()
if(OPSYS STREQUAL LINUX)
    add_definitions(-D_GNU_SOURCE)          # ← ①
endif()
message(STATUS "Configured operating system: ${OPSYS}")
if(OPSYS STREQUAL LINUX)
    set(TIMER "HPROC" CACHE STRING "Timer") # ← ②
else()
    set(TIMER "ANSI" CACHE STRING "Timer")
endif()
```

以及 `src/CMakeLists.txt`：

```cmake
macro(LINK_LIBS LIBRARY)
    if(OPSYS STREQUAL LINUX)
        target_link_libraries(${LIBRARY} rt)  # ← ③
    endif(OPSYS STREQUAL LINUX)
```

Conan 的 OHOS profile 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`（设备
`uname -s` 也是 HarmonyOS，且没有 `Modules/Platform/HarmonyOS.cmake` ⇒ 平台文件不加载，
configure 同时打出 `System is unknown to cmake, create: Platform/HarmonyOS`）。
`"HarmonyOS"` 既不等于 `Linux` 也不等于 `FreeBSD`/`Darwin` ⇒ **第一个分支整体不执行，
派生变量 `OPSYS` 为空**，而 ①②③ 三处下游分支全部由 `OPSYS` 门控 ⇒ 同时静默退化。

**关键点（也是它比同族条目更隐蔽的原因）**：这里没有任何"漏编源文件/缺符号"，
所以没有 undefined symbol、没有编译错误，只有 `OPSYS` 这一个变量的值不对。
判定必须靠 A/B 对照输出，不能靠"能不能编过"。

## 已尝试方案

- ❌ **不动它（默认行为）**：configure 全绿、18/18 测试全过，但 TIMER 退化成 ANSI、
  `_GNU_SOURCE` 与 `-lrt` 丢失 —— 属"假绿"，交付面比上游 Linux 上的实际能力窄。
- ❌ **改上游分支条件**（`elseif(... STREQUAL "HarmonyOS")`）：可行，但要出补丁、
  与上游分叉；而本例分支的唯一副作用是 `set(... CACHE STRING ...)`，**可以从外部等价给定**
  ⇒ 出补丁不是最小面（该路线见 E607 / DRAFT-openxr-1.1.63，作为 fallback 保留）。
- ❌ **把 `CMAKE_SYSTEM_NAME` 覆写成 `Linux`**：会让 CMake 去加载 `Platform/Linux.cmake`，
  改变全部平台语义（`UNIX`、`find_package(Threads)`、SONAME 判定…），并让所有诊断建立在
  错误前提上；**比"缺一个派生变量"的问题面大得多**，禁用（见 `forbid_1`）。
- ❌ **直接改产物头 `relic_conf.h` 里 `#define TIMER`**：治标 —— `_GNU_SOURCE` 与 `-lrt`
  两处照样漏，且安装头文件与上游分叉（见 `forbid_2`）。

## 最终方案

Conan 配方 `generate()`：

```python
tc = CMakeToolchain(self)
tc.cache_variables["OPSYS"] = "LINUX"   # ← 命令行 -D 形态
tc.generate()
```

**为什么必须是 `cache_variables` 而不是 `variables`**：`cache_variables` 走命令行 `-D`，
在解析任何 `CMakeLists.txt` **之前**就建立 cache 项；上游 `set(OPSYS "LINUX" CACHE STRING ...)`
没有 `FORCE`，不会覆盖已存在的 cache 项（实测 B 侧 `CMakeCache.txt` 为
`OPSYS:UNINITIALIZED=LINUX`），且该 `set()` 位于 `if()` 判定**之前**执行 —— 所以**一行注入
即同时恢复 ①②③ 三处**。写进 `tc.variables` 则落在 `conan_toolchain.cmake` 里，属普通变量，
与上游的 CACHE 项不是同一条语义路径（同族机理见 DRAFT-E321 / DRAFT-cpputest-4.0-cmake4-policy-flag）。

## 真实验证

- A/B 探针（同源同参数，仅差一个 `-DOPSYS`，各约 10s、不编译）：见上表，5 项读数全部翻转。
- 官方门禁：`conan-verify` **G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS**（G2 = 干净 `conan create`）。
- 测试：`100% tests passed, 0 tests failed out of 18`（`Total Test time 159.58 sec`，
  TESTS=1，含 `test_bn` 159.5s），**18/18 = 100%**。
- 消费者测试：`test_package` 以库使用者身份编译、链接并调用 `bn_*` 公开 API，
  **3 断言全过**（`relic consumer PASSED: 3 assertions`），退出码 0。

## 适用范围 / 反例 / 解除条件

- **适用**：上游"用 `if(CMAKE_SYSTEM_NAME STREQUAL "<平台>")` 产出一个**派生 CACHE 变量**，
  再用该变量扇出多处下游分支"的 CMake 工程，在 HarmonyOS/OHOS 默认系统名下都命中。
- **必须先证等效性**：目标平台确实提供该分支启用的 Linux/POSIX 能力（relic 实证：
  HarmonyOS aarch64/musl 有 `clock_gettime`/`getrusage` 与 `librt.a`，18/18 + 消费者 3/3 全过）。
  若分支启用的是目标平台真没有的能力，注入会把失败推迟到运行期 ⇒ 应改用 fallback 补丁路线
  并逐项验证。
- **不覆盖**：平台文件缺失本身（`System is unknown to cmake`、`UNIX` 未定义）不因本注入而解决，
  那属 `DRAFT-E577-cmake-ohos-unix-guard-silent-drop` 家族，两者要一起看。
- **解除条件**：上游改用 `if(UNIX)` 之类布尔判定、或补上 `HarmonyOS`/`OHOS` 分支后可移除注入。

## 查重与新增价值（按 §1.1 反证检索结果）

检索式：`grep -rilE "CMAKE_POLICY_VERSION_MINIMUM|STREQUAL .Linux.|OPSYS" knowledge/ 经验文档/B草稿库/`

- **同族已有 4 条**（根因同源：`CMAKE_SYSTEM_NAME=HarmonyOS` 使上游 Linux 分支落空）：
  `E543`（zycore-c，解法 = 配方 `package_info` 补 `system_libs=pthread`）、
  `E607`（osqp，解法 = **改分支条件**加 HarmonyOS/OHOS）、
  `DRAFT-openxr-1.1.63-harmonyos-must-join-linux-branch…`（解法 = **改分支条件**并入 Linux + 哨兵文件）、
  `DRAFT-E577-cmake-ohos-unix-guard-silent-drop`（`if(UNIX)` 守卫 + 平台文件缺失）。
- **本条的新增点**：① **解法不同** —— 三条同族给的都是"改上游分支/改 package_info"，
  没有一条给"配方层注入该分支唯一产出的派生 cache 变量"这条**零补丁**路径；
  ② **症状不同** —— 同族症状都带错误签名（undefined symbol / 编译失败 / API 缺失），
  本条是**零错误静默退化**（configure 与 18/18 测试全绿），必须 A/B 才可见；
  ③ **给出扇出链的定量对照**：一处 miss 同时造成 `0/36 → 36/36` 处 `_GNU_SOURCE`、
  `ANSI → HPROC`、`-lrt` 丢失三处退化，以及"cache_variables vs variables"的通道约束。
- 同条还顺带复用 `DRAFT-E321-cmake4-policy-version-minimum`（CMake 4 与
  `cmake_minimum_required(VERSION 3.1)` 不兼容 → 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`），
  该机制已完整在库 ⇒ 本包判 `hit`，不另开草稿（见 PR「使用知识库」）。

## 触发实例

- relic/0.5.0 @ HarmonyOS PC，任务 #15255，2026-10-15；探针脚本与 A/B 原始日志
  `probe/a.cfg.log` / `probe/b.cfg.log`（同源同参数）。
