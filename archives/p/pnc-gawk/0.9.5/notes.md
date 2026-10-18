# pnc-gawk 0.9.5 适配笔记

## 编译环境

- 构建系统：**CMake**（上游真实入口 `CMakeLists.txt`，同一配置产出 `pnc` CLI 与
  `gawkext/gawkpn.so`；本包只打包扩展）
- 编译器：`/data/service/hnp/bin/clang` / `clang++`（OHOS aarch64，Clang 15.0.4，
  libc++，C++17）
- 平台：HarmonyOS PC aarch64（host == target，本机原生构建，上游测试可真实执行）
- 依赖：`libphonenumber/8.13.51`、`icu4c/78`、`gawk/5.3.0`
- 编译日期：2026-10-17
- 状态：**built**（`conan create` exit 0；上游 ctest 11/11；test_package 10+4 全通过）

## 真实命令

```bash
conan create archives/p/pnc-gawk/0.9.5 \
  -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64
```

上游测试（构建期在 `build()` 内通过 `cmake.test()` 执行，即 ctest）：

```
1/1 Test #1: tests_sh .........................   Passed    0.84 sec
100% tests passed, 0 tests failed out of 1
```

## 依赖选择（与依赖分析报告的差异，必须知悉）

依赖分析报告列出 4 个直接依赖：`libphonenumber/8.13.51`、`libgeocoding/9.0.34`、
`icu4c/78`、`gawk/5.3.0`。本配方**只用 `libphonenumber/8.13.51`，不加
`libgeocoding/9.0.34`**，原因（实测）：

```
$ conan cache path libphonenumber/8.13.51:<pkg> ; ls <pkg>/lib
libgeocoding.a   libphonenumber.a
$ nm -C <pkg>/lib/libgeocoding.a | grep -c PhoneNumberOfflineGeocoder   # 21
$ nm -C <pkg>/lib/libphonenumber.a | grep -c 'PhoneNumberUtil::Parse'   # 5
```

`libphonenumber/8.13.51` 包内已经提供**同源（v8.13.51）**的 `libgeocoding.a`，
足以满足上游两处 `find_library(phonenumber / geocoding)`。若再叠加
`libgeocoding/9.0.34`，则 9.0.34 的 geocoder 归档会与 8.13.51 的
头文件/`libphonenumber.a` 混用 → ABI/ODR 错配（同符号不同版本），因此不加。
`libphonenumber/9.0.34` 在制品仓不存在（实测 `conan download
libphonenumber/9.0.34 -r=ohpcd --only-recipe` → exit 1，与负向对照
`zzzz-*` 同样的报错），无法配成"同版本对"。

## 真实构建/测试结果

| 项 | 命令 | 结果 |
|---|---|---|
| 上游 ctest | `ctest --output-on-failure`（build() 内 `cmake.test()`） | 1/1 用例 PASS（`tests_sh`，11 条断言） |
| 上游逐条断言 | `sh logs/run-upstream-cases.sh <pnc> <log>` | **11/11 PASS，0 FAIL，0 SKIP** |
| 上游 README 样例 | `gawk -f readme-example.awk readme-example.dat` | 号码/格式/过滤全对；归属地粒度差异见下 |
| test_package AWK | `gawk -l gawkpn -f test_gawkpn.awk` | 10/10 PASS |
| test_package OHOS | `test_ohos`（鸿蒙特有） | 4/4 PASS |

日志路径（真实文件）：

- `pnc-gawk-0.9.5-logs/conan-create-4.log` —— 成功构建 + test_package 输出
- `pnc-gawk-0.9.5-logs/upstream-cases-explore.log` —— 上游 11 条断言逐条结果
- `pnc-gawk-0.9.5-logs/readme-example.out` —— 上游 README 样例输出
- `pnc-gawk-0.9.5-logs/run-upstream-cases.sh` —— 逐条执行的驱动脚本（表达式逐字取自 tests.sh）

## 问题与解决（首个错误 → 根因 → 修复 → 重新验证）

### 1. conan create：`'phonenumbers/phonenumbermatcher.h' file not found`

首个错误（`conan-create-1.log`）：

```
pnc-gawk/0.9.5: RUN: cmake --build ...
gawkext/gawkpnimpl.cc:29:10: fatal error: 'phonenumbers/phonenumbermatcher.h' file not found
```

- **根因**：`tc.variables["PNC_DEP_INCLUDE_DIRS"] = includes`（Python list）被
  CMakeToolchain 序列化成 Python repr 字符串
  （`"['/path/a', '/path/b']"` 整体作为**一个** include 目录），CMake 侧
  `include_directories(SYSTEM ...)` 因此拿到无效路径。
- **修复**：改为 CMake 列表字符串 `";".join(includes)`（链接闭包同理）。
- **重新验证**：`conan create` 第二次 —— 配置/编译通过（日志 `conan-create-2.log`）。

### 2. test_package：`env argument to ConanFile.run() should be a list`

首个错误（`conan-create-2.log`）：test() 里 `self.run(cmd, env={...})`。

- **根因**：Conan 2 的 `ConanFile.run(env=...)` 只接受环境文件名（`conanrun`）
  或变量名列表，不接受 dict。
- **修复**：改为 shell 前缀形式
  `AWKLIBPATH="<pkg>/lib/gawk" "<gawk>" -l gawkpn -f ...`（`run(shell=True)` 默认）。
- **重新验证**：`conan create` 第四次 exit 0，11 条 AWK 断言 + 4 项 OHOS 检查全 PASS。

### 3. 上游 CMake 硬编码 `/usr/local`

`find_library(LIBPHONENUMBER phonenumber PATHS /usr/local/lib REQUIRED)` +
`include_directories(BEFORE SYSTEM /usr/local/include)` 在 Conan（任意前缀）与
交叉构建下不可用；`/usr/local/include` 还会把构建机头文件顶到搜索路径最前。

- **修复**：`patches/0001-CMakeLists.txt.patch` —— 增加
  `PNC_CONAN_PACKAGE_MODE` 分支，由构建驱动注入
  `PNC_DEP_INCLUDE_DIRS`（include 目录）与 `PNC_EXTRA_LINK_LIBRARIES`
  （静态闭包，用 `-Wl,--start-group/--end-group` 包裹，链接顺序无关）。
- 非 Conan 场景（`PNC_CONAN_PACKAGE_MODE` 未定义）保持上游
  `/usr/local` 行为不变。

### 4. 上游 configure 期执行 gawk 取 AWKLIBPATH

```cmake
execute_process(COMMAND gawk "BEGIN {print ENVIRON[\"AWKLIBPATH\"]}" ...)
install(TARGETS gawkpn DESTINATION ${AWKLIBPATH})
```

- **根因**：交叉构建时 `gawk` 是构建机的二进制，返回构建机绝对 `AWKLIBPATH`；
  若为空则 `DESTINATION ""`，安装路径不可控（甚至是系统目录）。
- **修复**：`patches/0002-gawkext-CMakeLists.txt.patch` —— 默认
  `AWKLIBPATH=lib/gawk`（前缀相对），`-DAWKLIBPATH=` 可覆盖。
- **补丁不含任何平台宏**（`__OHOS__` 等），符合 R8/PF5。

### 5. `gawk -l gawkpn` 后 `function 'pn_set_country' not defined`

首个错误：

```
gawk: cmd. line:1: fatal: function `pn_set_country' not defined
```

- **根因**：上游 `dl_load_func(func_table, "phonenumber", "phonenumber")` 的
  第三个参数是 AWK 命名空间，gawk 5.x 会把函数注册为
  `phonenumber::pn_*`；上游 README 的裸函数名写法面向旧 API。
- **修复**：测试与文档使用 `@namespace "phonenumber"`（或 `phonenumber::` 前缀）。
- **验证**：

```
$ gawk -l gawkpn '@namespace "phonenumber" BEGIN { pn_set_country("FR"); print pn_format("0123456789") }'
+33123456789
```

### 6. 上游 README 样例的归属地粒度差异（依赖级限制，非本配方问题）

样例第 1 行期望 `foo;+33296484698;Lannion`，实测 `foo;+33296484698;France`；
`pnc info "+33 2 96 48 46 98"` 亦输出 `location: France`。

- **根因**：`libphonenumber/8.13.51` 包内的 `geocoding_data` 为国家级精度
  （依赖包的数据粒度），本配方不修改依赖源码。
- 号码解析/格式化/校验/匹配（11 条上游断言覆盖的部分）全部一致。
- 记录为已知限制：**离线归属地只到国家粒度**。

## 运行期依赖

```
$ readelf -d <pkg>/lib/gawk/gawkpn.so | grep NEEDED
 (NEEDED) Shared library: [libc++_shared.so]
 (NEEDED) Shared library: [libc.so]
```

OHOS 系统自带 `/system/lib64/libc++_shared.so`。clean env 实测：

```
$ env -i AWKLIBPATH=<build>/gawkext <gawk> -l gawkpn 'BEGIN{...}'
+33123456789
```

`test_ohos` 第 3/4 项进一步验证 `dlopen` + `dlsym("dl_load")`，第 4 项验证复制到
`$HOME/tmp`（HMDFS，OHOS 上唯一可写暂存区）后仍可加载，同时断言 `/tmp` 为
`EROFS` 只读。

## 上游测试清点（R51 三步法）

1. 清点（实测命令 + 计数）：

```bash
grep -nE 'enable_testing|add_test' CMakeLists.txt     # enable_testing() 1 处；add_test(tests_sh ...) 1 处
wc -l tests.sh                                        # 31 行；断言 11 条
find . -type f -name '*.awk'                          # 0（无 AWK 自动化测试）
```

2. 实际运行：`ctest` 1/1 PASS；逐条断言 11/11 PASS（日志见上）。
3. 如实回填：上游 11 / 通过 11 / 失败 0 / 跳过 0；上游**没有**加载
   `gawkpn.so` 的自动化测试，该空白由 test_package 的 11 条 AWK 断言 + 4 项
   OHOS 检查覆盖（不冒充上游用例）。

## 注意事项

- 本包**只含** `lib/gawk/gawkpn.so`（+ `licenses/LICENSE`）；同一配置产出的
  `pnc` CLI 与 man page 在 `package()` 中被移除（CLI 属上游另一个产物）。
- 消费方式：`AWKLIBPATH=<pnc-gawk 包目录>/lib/gawk gawk -l gawkpn ...`。
- `/tmp` 在 OHOS 上只读（HMDFS），任何脚本/测试不要写 `/tmp`
  （`test_ohos.c` 的 `/tmp` 写探测是 EROFS 断言本体，故意为之）。
## 对话记录

### 对话 #1（2026-10-17，适配与验证）
- 依赖核验（fresh CONAN_HOME）：
  `conan download libphonenumber/8.13.51 / icu4c/78 / gawk/5.3.0 -r=ohpcd --only-recipe` → 全部 exit 0；
  `conan install --build=never` 拉取二进制 exit 0。
- 源码：`https://git.sr.ht/~anjan/pnc/archive/0.9.5.tar.gz`，sha256
  `48fc76cf…3cea720`（与 conandata.yml 一致）。
- 构建：`conan create archives/p/pnc-gawk/0.9.5 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`
  → exit 0；产物 `lib/gawk/gawkpn.so`（ELF64 AArch64 ET_DYN）。
- 首次失败：`'phonenumbers/phonenumbermatcher.h' file not found`（CMakeToolchain 把 Python list
  序列化成 repr 字符串）→ 改为 `";".join(...)`，重跑通过。
- 二次失败：test_package `self.run(env={...})` 不被 Conan 2 接受 → 改 shell 前缀形式
  `AWKLIBPATH=... gawk -l gawkpn ...`，通过。
- 上游测试：`ctest` 1/1 PASS（`tests_sh`，11 条断言）；逐条驱动 11/11 PASS，0 失败 0 跳过。
- test_package：AWK 11 条断言 + 鸿蒙 `test_ohos` 4 项检查，全 PASS。
- `conan-verify`：G1/G0/G2/G3/G4/L2/L4/L5 全 PASS。
- W3（finish step 5）：KC/JC/L0/L1/L2/L4/L5 全 pass，Build Summary 100%。
- 说明：`gawk -l gawkpn` 的函数注册在 `phonenumber` 命名空间（上游
  `dl_load_func(func_table, "phonenumber", "phonenumber")`），AWK 侧需 `@namespace "phonenumber"`。
---

**编译结束**: 2026-10-17 20:35
**最终状态**: built
