# indi-nexdome 1.5+20221222183051 适配笔记

## 任务概述
- 软件: indi-nexdome（NexDome 个人天文台圆顶的 INDI 驱动，indi-3rdparty 的单个子项目）
- 版本: 1.5+20221222183051（Debian 源包 `indi-nexdome` 的版本；其 pristine upstream
  tarball 即 indi-3rdparty 该时刻的 `indi-nexdome/` 子树 + 共享 `cmake_modules/`，
  与官方 v1.9.9 tag 逐字节比对一致，见下）
- 源码 URL: https://deb.debian.org/debian/pool/main/i/indi-nexdome/indi-nexdome_1.5+20221222183051.orig.tar.gz
  （sha256 85bf08929fb031a4ed58439b95c85b24ac2fe159973b9bc59ca9207208d78e37）
- 上游仓库: https://github.com/indilib/indi-3rdparty
- 分支: feat/indi-nexdome-1.5+20221222183051
- 最终状态: published（W3 本地 CI 通过，.ci-result.json exit_code=0）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-13
- 编译器: clang 15.0.4（OHOS SDK，profile: ci/conan/profiles/ohos-aarch64，C++17）
- 构建命令: `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`

## 1. W0 依赖预检（conan download --only-recipe 实测）

| 依赖 | 版本 | 制品仓状态 |
|------|------|-----------|
| libindi | 2.2.2.1 | ✅ published |
| libnova | 0.16 | ✅ published |
| zlib | 1.3.1.1 | ✅ published |

libindi/2.2.2.1 同时也是本驱动唯一的“框架级”强依赖（本仓库已有归档）。

## 2. 源码核验（来源与内容）

Debian 源包 `indi-nexdome` 的 orig tarball 是 indi-3rdparty 仓库该时刻快照的
独立重打包：顶层即 `indi-nexdome/` 子项目内容 + 共享 `cmake_modules/`。与官方
GitHub tag `v1.9.9`（Debian changelog 明确 “based on indi-3rdparty release 1.9.9”）
内的 `indi-nexdome/` 子树逐文件比对：**内容完全一致**（cmake_modules 仅多一个
`FindAHPGT.cmake`）。因此本包使用该 pristine upstream tarball 作为官方来源，
与 `libapogee3/3.2+20221221183454` 同款模式。

## 3. 上游测试入口核验（R51 第一步：清点）

indi-nexdome 源码树内**不存在任何测试入口**：

```
$ find . -iname '*test*'        # 0 命中
$ grep -nE 'add_test|enable_testing' CMakeLists.txt   # 0 命中
$ cat ChangeLog                 # 仅 "[1.0.0] - 2017-09-12 Initial Release"
```

唯一的可执行入口是驱动进程本身：`indi_nexdome -h`（INDI 框架用法）以及与
indiserver 之间的 INDI XML 协议（stdin/stdout）报文握手。

## 4. OHOS 适配（4 个补丁，refresh-patch --auto 生成）

| 补丁 | 内容 | 原因 |
|------|------|------|
| 0001-CMakeLists.txt.patch | `cmake_minimum_required` 3.0→3.16；`set(CMAKE_FIND_LIBRARY_SUFFIXES ".a")`；`find_package(INDI REQUIRED)`→`COMPONENTS driver`；把驱动源码放进 STATIC 库并整体后置于 INDI 静态库链接 | CMake 4.x 移除 <3.5 兼容；本平台只能静态链接 INDI；libindi 无 `libindiAlignmentDriver.a`，align 组件无法静态满足；**链接顺序决定 .init_array 顺序**（见 §5） |
| 0002-cmake_modules-CMakeCommon.cmake.patch | `CMAKE_CXX_STANDARD` 14→17 | libindi 2.x 头文件使用 `std::any`（defaultdevice.h），C++14 下编译失败 |
| 0003-cmake_modules-FindINDI.cmake.patch | 版本探针正则兼容带引号的 `#define INDI_VERSION "2.2.2"` | 老式 FindINDI 只认无引号的 `INDI_VERSION x.y.z`，对当前 libindi 头报 “failed to detect INDI version” |
| 0004-nex_dome.cpp.patch | `DomeParamNP/DomeAbsPosNP/DomeShutterSP/ShutterParkPolicySP` 从 INDI 1.x 数组式旧名迁移到 INDI 2.x `INDI::Property` API（`isNameMatch/update/setState/apply/getValue`，共 24 行） | libindi 2.x 移除了这些旧属性名；该迁移与**上游 master 自己的移植逐行一致** |

### 4.1 INDI 1.x → 2.x 属性 API 迁移（核心）
源码（2022-12 快照，基于 INDI 1.9.9）使用已删除的旧标识符：
- `DomeParamNP.name` / `.s` → `getName()`/`isNameMatch()`、`setState()`
- `IUUpdateNumber(&DomeParamNP,...)` / `IDSetNumber(&DomeParamNP,...)` → `DomeParamNP.update(...)` / `.apply()`
- `DomeParamN[0].value` / `DomeAbsPosN[0].value` → `DomeParamNP[0].getValue()` / `DomeAbsPosNP[0].getValue()`
- `DomeAbsPosN[0].value = x` → `DomeAbsPosNP[0].setValue(x)`
- `DomeShutterS[i].s = v` → `DomeShutterSP[i].setState(v)`
- `ShutterParkPolicyS[i].s` → `ShutterParkPolicySP[i].getState()`

补丁中的写法与上游 master 现有实现完全对应（已逐行比对），非自定义补丁。

### 4.2 静态链接 INDI 与 .init_array 顺序（关键坑）
- 本 OHOS 目标上 libindi 的共享库 **无法加载**：`dlopen("libindidriver.so.2")` 与
  `libindiAlignmentDriver.so.2` 均返回 “Permission denied”（libindiclient.so.2、
  自建 .so、以及 NEED 了 libcurl/libgsl 的自建 .so 均可正常加载，已用最小复现隔离，
  与 gsl/codesign 无关），因此消费者必须静态链接 INDI。
- 静态链接后驱动在 `-h` 直接 **SIGSEGV**（无任何输出）。用最小复现程序定位：
  单独链接 INDI 静态库时正常；一旦存在 **全局 `INDI::Dome` 子类实例** 就崩溃，
  且崩溃发生在基类构造器（`INDI::Dome::Dome()`，派生类构造体尚未执行）。
  根因：链接器按**链接顺序**拼接各目标文件的 `.init_array`，可执行文件自身的
  目标文件永远排在静态库之前 → 驱动全局设备对象先于 INDI 自身的静态初始化
  （`defaultdevice.cpp.o` / `indilogger.cpp.o` / `sharedblob_parse.cpp.o` 均含
  init_array）运行。
- 修复：把驱动源码编成 STATIC 库，并用 `-Wl,--whole-archive <驱动库> -Wl,--no-whole-archive`
  将其放在 INDI 静态库**之后**链接（实测最小复现 `t6b` 由 SIGSEGV 变为正常打印
  usage；正式驱动由 SIGSEGV 变为正常应答 INDI 协议）。

### 4.3 OHOS ELF 代码签名与 RPATH
CMake install 会改写二进制 RPATH，而 lld 已在链接期写入 OHOS 的 `.codesign`
内容哈希；改写后签名失效，执行报误导性的 `Operation not permitted`。修复：同时
设置 `CMAKE_SKIP_BUILD_RPATH`/`CMAKE_SKIP_INSTALL_RPATH`，安装产物与构建树逐字节
一致（libapogee3 同款模式）；运行时依赖由 conanrun 的 `LD_LIBRARY_PATH` 解析。

## 5. 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...   # RC=0
  test.sh       7/7  PASS（INDI 协议握手/身份/版本/连接流程 + 用法退出码）
  test_ohos.sh 12/12 PASS（OHOS ELF/ABI、静态 INDI、设备描述文件、真机执行）
```

- 产物: `bin/indi_nexdome`（ELF64 AArch64 PIE，解释器 `/lib/ld-musl-aarch64.so.1`）、
  `share/indi/indi_nexdome.xml`（设备描述，version 1.6）
- NEEDED: `libusb-1.0.so.0 / libcurl.so / libgsl.so.28 / libgslcblas.so.0 /
  libfftw3.so.3 / libfftw3_threads.so.3 / libev.so / libc++_shared.so / libc.so`
  （**无任何 libindi*.so**，INDI 框架静态内嵌）
- 真实运行: `printf "<getProperties version='1.7'/>\n" | indi_nexdome`
  应答 `device='NexDome'` 的 `defSwitchVector`/`defTextVector` 等属性定义

## 6. 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（老式 FindINDI/FindNova 变量注入、静态 INDI、RPATH 策略） |
| conandata.yml | 官方 pristine upstream tarball + sha256 + 补丁声明 |
| patches/0001-0004 | 4 个适配补丁（refresh-patch --auto 生成） |
| test_package/ | 功能测试 7 条 + 鸿蒙特有测试 12 条（均真实执行包内二进制） |
| manifest.yaml | 版本级元数据（status: published） |
| ../../commands.json | 软件级 CLI 声明（R38） |
| .ci-result.json | W3 本地 CI 结果（finish 自动写入） |
| reports/ | conan-create / conan-verify / w3-local-ci 日志 |

## 注意事项
- INDI 框架在本平台只能静态链接：libindi 的共享对象在当前 OHOS 目标上无法 dlopen。
- 驱动的 NexDome 硬件交互（USB/串口）无法在 CI 构造；CONNECT 在无硬件时如实返回
  `CONNECTION state=Alert`，测试按此断言。
- 补丁中不含任何平台宏（R8/PF5 合规）；所有差异均基于 API 演进而非平台分支。
---

**编译结束**: 2026-10-13 15:51
**最终状态**: published
