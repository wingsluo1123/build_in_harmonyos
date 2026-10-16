# indi-eqmod 1.0-20230126190232 适配笔记

## 任务概述
- 软件: indi-eqmod（INDI 天文望远镜 EQMod 驱动，含 EQMod/AZ GTi/Sky Adventurer GTi/Star Adventurer 2i 四个望远镜驱动）
- 版本: 1.0-20230126190232（Debian 打包转写 1.0+20230126190232，conan 版本号用 1.0-20230126190232）
- 源码 URL: https://deb.debian.org/debian/pool/main/i/indi-eqmod/indi-eqmod_1.0+20230126190232.orig.tar.gz（权威源）
- 分支: feat/indi-eqmod-1.0-20230126190232
- 最终状态: built（W3 本地 CI 通过，.ci-result.json exit_code=0；远端 CI/AI Review 未闭环，按 R3 如实标 built 而非 published）

## 编译环境
- 构建系统: cmake（PROJECT(indi-eqmod C CXX)）
- 编译日期: 2026-10-01
- 编译器: clang 15（OHOS SDK，profile: ci/conan/profiles/ohos-aarch64）
- 构建命令: `conan create . -pr:h=ohos-aarch64 -pr:b=... --build=missing`（ohc-run.py finish W3 同源）

## 1. W0 依赖检查（全部已发布，ohpcd 制品仓验证）

| 依赖 | 版本 | 状态 |
|------|------|------|
| libindi | 2.2.2.1 | ✅ 已发布（强参考：archives/l/libindi/2.2.2.1 同族适配配方） |
| libnova | 0.16 | ✅ 已发布 |
| zlib | 1.3.1.1 | ✅ 已发布 |
| gsl | 2.8 | ✅ 已发布 |
| AHPGT | — | ❌ 未发布 → WITH_AHP_GT=OFF（AHP GT 驱动为可选组件，不影响主驱动） |

## 2. 源码修改（3 处，refresh-patch --auto 生成补丁 + conanfile 配置）

### 2.1 cmake_modules/FindINDI.cmake（源码 patch）
- 问题: FindINDI.cmake 版本正则 `.*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)` 无法匹配 libindi 2.2.2 的 `#define INDI_VERSION "2.2.2"`（带引号）→ "failed to detect INDI version"
- 修复: 正则改为 `.*INDI_VERSION \"?([0-9]+)\.([0-9]+)\.([0-9]+)\"?`（兼容带/不带引号）

### 2.2 cmake_modules/CMakeCommon.cmake（源码 patch）
- 问题: 强制 `set(CMAKE_CXX_STANDARD 14)`，libindi 2.2.2 头文件 defaultdevice.h 用了 std::any（C++17）→ 编译报 "no type named 'any' in namespace 'std'"
- 修复: C++14 → C++17

### 2.3 eqmodbase.cpp（源码 patch，libindi 2.x API 迁移）
- 问题: indi-eqmod 2023-01 快照使用旧 Property API，libindi 2.2.2 已切换新 API
  - `SlewRateSP.nsp/sp[i]` → `SlewRateSP->nsp/sp[i]`（PropertyBasic::operator-> 兼容层，INDI_PROPERTY_BACKWARD_COMPATIBILE 宏已启用）
  - `IUFindNumber(&LocationNP,...)` / `&CoordSP` / `&TrackRateNP` / `IUFindOnSwitch(&TrackModeSP)` / `IUFindOnSwitch(&SlewRateSP)` → `XxxNP.operator->()` 显式取 PropertyView 指针（operator& 在新版为 protected）
  - `defineProperty(&GuideNSNP/&GuideWENP)` → `defineProperty(GuideNSNP/GuideWENP)`（新版重载接受 INDI::Property&）
  - `GuideNSNP.name/.s`、`EqNP.s`、`ParkSP.s` → `->name`/`->s`
  - `IDSetNumber(&GuideNSNP,&GuideWENP,&EqNP)` / `IDSetSwitch(&ParkSP)` → `.operator->()` 显式转换
  - `INDI::GuiderInterface::initGuiderProperties(dev, MOTION_TAB)` → `INDI::GuiderInterface::initProperties(MOTION_TAB)`（新版方法）
  - `processGuiderProperties(name,...)` → `processNumber(getDeviceName(), name,...)`（新版方法）
  - EQMod 构造器: 增加 `: INDI::GuiderInterface(this)`（新版 GuiderInterface 构造需要 DefaultDevice*）

### 2.4 scope-limits/scope-limits.cpp（源码 patch）
- 问题: `timestamp()` 未声明（在新版 libindi 中已移除/改名）
- 修复: `timestamp()` → `indi_timestamp()`（indicom.h 提供）

### 2.5 conanfile.py 配置
- CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（E092: CMake 不识别 HarmonyOS）
- CMAKE_POLICY_VERSION_MINIMUM=3.5（CMake ≥3.5 才能识别 cmake_minimum_required 3.0 的旧项目；cmake 4.x 直接 error）
- CMAKE_CXX_STANDARD=17（libindi 2.2.2 需要 std::any）
- WITH_AHP_GT=OFF（AHPGT 未发布）
- WITH_ALIGN=ON / WITH_ALIGN_GEEHALEL=ON / WITH_SCOPE_LIMITS=ON（保持上游默认）
- link_libraries(c++ c++abi)（libindi 2.2.2.1 配方的 OHOS libc++ 标准库经验）
- arm 处理器链接 rt 已由 CMakeLists `CMAKE_SYSTEM_PROCESSOR MATCHES "arm*"` 自动处理（OHOS sysroot 提供 librt.a，OK）

## 3. R51 上游测试申报表

### 清点（上游 indi-eqmod 测试）
| 测试类型 | 数量 | 来源 |
|---------|------|------|
| GTest 单测 | 1 个可执行（test_eqmod 8 个 TEST 用例） | test/CMakeLists.txt + test/test_eqmod.cpp |

### 实测结果
| 项 | 结果 | 说明 |
|----|------|------|
| 测试构建 | **构建（test_requires gtest/1.17.0.2，BUILD_TESTING=ON）** | 上游 test/ 依赖 GTest+GMock；配方 test_requires gtest/1.17.0.2（自带 gmock 库），generate() 注入 GTest_DIR/GTEST_* 变量 + 生成最小 GMockConfig.cmake，CMake 完整编译出 test_eqmod（8 用例全部链接） |
| 测试运行 | **8/8 PASS（真实执行）** | 审查 rule4 要求真实运行（0/8 不接受平台限制理由）。动态链接版运行期被 OHOS 平台拒绝（用户分区 .so 无法 dlopen，E537/R49），配方在 build() 中改用**全静态链接**重新链接 test_eqmod（libindidriver.a 的驱动 main 经 objcopy 改名；libindiAlignmentDriver.a 由 conandata libindi_src 源码编译；gsl_stub.o 满足 BuiltInMathPlugin 链接期 GSL 符号——8 用例不触达其变换路径；排除 eqmod.cpp.o 的静态 EQMod 全局构造），INDIPREFIX 指向 staged sk.xml 后真实执行：hemisphere_symmetry / encoders_north\|south / encoder_target_north\|south / scope_limits_properties\|empty\|altaz 全部 OK（本地与 CI 同为 OHOS aarch64） |
| 技术方案 | 静态链接规避 OHOS 动态加载限制 | 与 libindi/argp-standalone test_package 同款模式（静态 .a 链接），非"没有环境"：OHOS 对用户分区 .so 的 dlopen 返回 EACCES 为平台不可抗力，/data、/system 不可写无法放置 .so；静态 ELF 可直接执行（已实测） |

## 4. 产物
- 可执行文件: indi_eqmod_telescope / indi_azgti_telescope / indi_skyadventurergti_telescope / indi_staradventurer2i_telescope（4 个，安装到 bin/）
- 数据文件: share/indi/*.xml（driver 配置）
- **CLI 工具类型 → 软件级 commands.json 已创建（R38）**
- 库产物: 无（纯工具包，无 cpp_info.libs）

## 5. 遗留问题
- 上游 8 个 GTest 用例由配方静态链接真实运行（8/8 PASS）；开发机 CI 构建日志含完整 gtest 输出（每次 conan create 均执行）
- MathPlugin 的 GSL 变换路径不作为测试覆盖对象（8 用例不触达；gsl_stub 仅为链接期满足，见 assets/gsl_stub.c 说明）
- test_package 采用制品静态探针（53 断言）：驱动为常驻进程（运行时需 INDI server + 硬件），L2 smoke 用 ELF/DT_NEEDED/XML 注册探针 + build() 内静态 GTest 双通道验证
---

**编译结束**: 2026-10-01 22:57
**最终状态**: built
