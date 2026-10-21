# indi-starbook 0.8-20221222163625 测试报告（MateBook 第 4 轮）

> **项目**: indi-starbook  
> **测试日期**: 2026-10-15  
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **测试类型**: 官方测试套件（上游 indi-3rdparty test_starbook.cpp）+ 本地 CI 门禁  
> **分支 HEAD**: 816788077a fix(indi-starbook): resolve find_package(CURL) via CMakeDeps config mode (CI L0o hard gate)

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 5 | 100% |
| 通过 (PASS) | 4 | 80% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 1 | 20% |

**核心功能通过率**: ✅ **100%（实跑 4/4 全过）**

> 跳过的 1 项为 W3 内置 L2 version/help 冒烟：conan 包内未签名二进制 exec 受 EPERM 限制（已知环境行为，第 1 轮即了结的前置结论）。等价的 --help 冒烟已在签名后的 staging 包上实跑通过（见 3.1）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过。** 官方测试 2/2 PASSED；W3 本地 CI 模拟全链通过（L0/L1/L4/L5 PASS、KC/JC PASS、L2 skip 属未签名 exec 环境行为）；L1e 破坏性负向测试判真实；verify-build 质量报告 PASS；staging 闭包重打包后签名包 --help 可执行。第 3 轮的 G2 AttributeError（属性式 dependencies.curl）与 W3 硬闸 L0o（conanfile 引号字面量）两个根因均已消除。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| W3 首遍被 JC 拦截（533 包 + libdazzle/.staging-verified） | 门禁基线陈旧，非本包缺陷 | 🟢 已按排障表处置（刷新 origin/main 引用后 JC 全过） |
| 主包构建侧 CURL 实际经内建 FindCURL 模块命中（详见四/问题2） | 不阻塞：编译链接/测试/L0o 全过 | 🟢 记录性发现 |

### 2.3 可用功能清单

```
✅ StarBook 命令协议解析（starbook_types：CommandResponse OK/ERROR/payload，含前导空白容错——0004 补丁）
✅ INDI 驱动框架加载（Telescope 基类，libindidriver/libindiAlignmentDriver/libindiclient 2.2.2）
✅ HTTP 传输编译链接（connectioncurl.cpp，libcurl 8.15.0）
✅ 签名包可执行（--help 输出 Usage 横幅，rc=1，dsi/gpsd 先例口径）
⚠️ 对真实 StarBook 赤道仪硬件的遥控需设备在场（本轮无硬件，超出可验证范围）
```

### 2.4 已知限制

1. 未签名二进制 exec 返回 126/EPERM——环境行为，打包 ELF 签名后消失（前置结论①，本轮复现并再次验证）。
2. W3 内置 L2 冒烟在 conan 未签名产物上判 skip（同上；签名包 --help 冒烟已覆盖）。
3. libnova/cfitsio/openssl/zlib 等未以独立 .so 出现在 NEEDED：libnova/cfitsio 静态吸入，openssl/zlib 被静态链入 libcurl.so——staging 闭包按 NEEDED 实测收集，不以配方依赖表臆测。
4. INDI/Nova 无同名 CMake config，仍走驱动自带 Find 模块 + conanfile 注入（设计如此）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| test_starbook.cpp（Layer1 官方 gtest，2 tests from StarbookDriver） | 命令协议解析（含 "    OK" 前导空白 → starbook::OK） | ✅ PASS |
| L1e 破坏性负向测试（[sabotage] bin/ moved away） | 验证测试真实依赖被测库，非假测试 | ✅ PASS（判真实） |
| 签名 staging 包 exec --help | 产物可执行冒烟 | ✅ PASS（Usage 横幅，rc=1） |
| 门禁套件（conan-verify G0-G4 / W3 L0i、L0j、L0k、L0m 及 L0c、L0o 静默项 / KC / JC / W2） | 配方完整性、依赖在库、版本查重、commands.json、目录结构、知识库、杂项文件、PR 原子性 | ✅ PASS |

Layer1 gtest 原文（reports/conan-create.log）：

```
[==========] Running 2 tests from 1 test suite.
[----------] 2 tests from StarbookDriver
[----------] 2 tests from StarbookDriver (0 ms total)
[==========] 2 tests from 1 test suite ran. (0 ms total)
[  PASSED  ] 2 tests.
```

L1e 原文（reports/w3-local-ci.log）：

```
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on indi-starbook
```

staging exec 原文：

```
$ ~/tmp/starbook-signed/bin/indi_starbook_telescope --help; echo "rc=$?"
Usage: indi_starbook_telescope [options]
Purpose: INDI Device driver framework.
Options:
 -v    : more verbose to stderr
rc=1
```

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| W3 L2 平台功能矩阵（version/help 冒烟） | conan 包内未签名二进制 exec EPERM（环境行为）；签名包等价冒烟已 PASS，见 3.1 |

---

## 四、关键问题分析

### 问题1: finish 首遍在 Step5 W3 被 JC gate 拦截（Junk Files: 3）

**现象**：
```
[FAIL] JC1: 1 个运行时状态文件被跟踪: archives/l/libdazzle/3.44.0/.staging-verified
[FAIL] JC5: 1 个 archives 下未登记的隐藏文件: archives/l/libdazzle/3.44.0/.staging-verified
[FAIL] JC6: 本 PR 涉及 533 个软件包，违反 W2 单软件原子性
```

**根因分析**：
junk_check 增量模式取 `git diff origin/main...HEAD` 为基线。本机 origin 指向 Sy444 Fork，其 origin/main（2026-10-10）与 gcw 分支血统的 merge-base 陈旧，导致 HEAD 侧差异包含其他成员血统的 533 个包及上游已合并的 libdazzle 提交（排障表 JC6 条目口径：本地 origin/main 落后）。

**解决方案**：
按排障表处置：从真实上游 `gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos` fetch main（b544378a4e），`git update-ref refs/remotes/origin/main` 仅刷新引用（工作区零改动）。刷新后预览差异 17 文件、全部位于 archives/i/indi-starbook；复跑 finish：JC_RESULT=pass，Junk Files: 0，W3 本地 CI 模拟通过。

### 问题2: CURL 解析路径取证（第 4 轮修复复核）

**现象**（reports/conan-create.log）：
```
RUN: cmake ... -DCMAKE_FIND_PACKAGE_PREFER_CONFIG="ON" ...
-- Found CURL: /storage/Users/currentUser/.conan2/p/curlab79f980aa031/p/lib/libcurl.so (found version "8.15.0")
```

**取证结论**：
- 配方按 816788077a 设计仅设 cache 变量 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，conanfile.py 不含 "curl" 引号字面量（CI L0o 硬闸 grep 结构性 clean，本轮 W3 复判通过）。
- 消费端（test_package）CMakeDeps 正常产出 config 家族：generators 目录存在 CURLConfig.cmake / CURLConfigVersion.cmake / CURLTargets.cmake / CURL-Target-release.cmake / CURL-release-armv8-data.cmake（及 indi-starbook/GTest/gsl/fftw/libev 等同名家族）。
- 主包（被构建包）generators 目录仅 CMakeToolchain 产物（conan 2 create 不为被构建包运行 CMakeDeps），且 curl 包内 lib/ 仅 libcurl.so + pkgconfig、无自带 cmake config——故主包 configure 的 CURL 命中走 CMake 内建 FindCURL 模块在 conan 注入路径下的解析（Found 指向 conan curl 包内 libcurl.so、版本 8.15.0，经包内 curl-config 报版本），命中物与 config 模式目标同为 `CURL::libcurl`，connectioncurl.cpp.o 编译、链接均通过。
- 判定：G2 全链绿、L0o clean、测试全过，无阻塞；该取证仅澄清"主包侧命中方式为模块回退"，供 PR 描述与后续审查对齐事实。

---

## 五、测试环境

```
分支: feat/indi-starbook-0.8-20221222163625 @ 816788077a（队员 Fork gcw_caeRdY6E 已推送）
Conan: 2.29.1; profile: ohos-aarch64（os=OHOS 6.0, arch=armv8, clang 15, cppstd=17, libc++）
依赖（ohpcd 制品仓实下复核）: libindi/2.2.2.1, libnova/0.16, curl/8.15.0.1(shared), gtest/1.17.0.2
补丁: 4 个（0001 FindINDI 版本正则 / 0002 C++17 / 0003 TimeT→TimeTP master 回移 / 0004 CommandResponse 前导空白）
staging 闭包（lib/external/, cp -aL 保 SONAME, depth≤3 实测收敛）:
  libindidriver.so.2, libindiAlignmentDriver.so.2, libindiclient.so.2（libindi 包）
  libcurl.so（curl 包）, libusb-1.0.so.0（libusb 包）, libfftw3.so.3（fftw 包）,
  libgsl.so.28, libgslcblas.so.0（gsl 包）
  系统库不复制: libc.so, libc++_shared.so（OHOS 运行时提供）
打包产物: packaging/indi-starbook-0.8-20221222163625-ohos-aarch64.tar.gz (18093791 B)
         packaging/indi-starbook-0.8-20221222163625-ohos-aarch64-debug.tar.gz (8412439 B)
```

---

*报告生成时间: 2026-10-15（MateBook 第 4 轮真机验证）*
