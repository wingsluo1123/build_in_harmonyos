# opennurbs 8.35 编译笔记（HarmonyOS PC / aarch64）

## 这是什么

OpenNURBS 是 Robert McNeel & Associates 开源的 **NURBS 几何内核**（Rhino 几何库
的开源版）：`ON_3dPoint` / `ON_Curve` / `ON_Brep` / `ON_Mesh` 等 C++ 类，
以及 3DM 文件读写。

在**本仓**里它是 **Trilinos `percept`（Monty）** 的可选几何 TPL
（源码直读：`packages/percept/cmake/Dependencies.cmake` 的
`LIB_OPTIONAL_TPLS OpenNURBS`），因此与 Trilinos 适配链相关，
但不是任何包的硬前置。

## 上游形态

- 仓库 `mcneel/opennurbs`；**没有 release / tag**，只有分支（本包取 `8.x`）；
- 版本号来自 `opennurbs_public_version.h`：`RMA_VERSION_MAJOR 8` +
  `RMA_VERSION_MINOR 35` ⇒ 包版本取 **8.35**；
- 构建入口：`cmake_minimum_required(VERSION 3.16)`、`project(opennurbs CXX)`。

## 构建面（实测自上游 CMakeLists.txt）

| 项 | 内容 |
|---|---|
| 库目标 | **两个**：`opennurbsStatic`（STATIC）与 `OpenNURBS`（SHARED），都被 `install()` 到 `lib/` |
| 公共头 | 装到 `include/opennurbsStatic`（STATIC 的 install 行）与 `include/OpenNURBS`（非 Apple 分支）——**两处内容相同**，上游布局如此 |
| 外部依赖 | **零**：`zlib` 与 `freetype263`/`android_uuid` 都是仓内 vendored（`if (ANDROID OR LINUX) add_subdirectory(freetype263)`、`add_subdirectory(zlib)`） |
| 编译定义 | `-DUNICODE -D_UNICODE -DON_CMAKE_BUILD`（上游自行 `add_definitions`） |
| 测试 | **无 `enable_testing()`/`add_test()`** —— 上游没有 CTest 套件（`BUILD_TESTING` 只控制一个测试头） |

## 源码固定的已知瑕疵（如实申报）

上游无 tag、本机又拿不到 GitHub 的 commit sha，故 conandata 钉的是
**分支归档 `refs/heads/8.x` + sha256**（74943888 字节）。分支归档会随上游推进
变化 ⇒ **将来可能出现 sha256 校验失败**。conandata.yml 里写了两条后续修法：
① 上游出 tag 就改 tag 归档；② 能访问 GitHub ref 时改钉 commit sha 归档。

## 打包与签名

- `cmake.install()` 落 `lib/` + 两个头目录；
- OHOS 侧对包内 **SHARED/E** ELF 做 E318 自签（`libOpenNURBS.so`）；
  `.a` 不是 ELF，签名助手按 ELF 魔数过滤，自然不会误签；
- 无陈旧路径审计问题（上游不装任何 CMake config / .pc / .prl）。

## 本地实测（2026-10-16）

- `conan create archives/o/opennurbs/8.35`（profile `ci/conan/profiles/ohos-aarch64`）**rc=0**
- 产物：`lib/libOpenNURBS.so`（已 E318 自签）、`lib/libopennurbsStatic.a`，
  以及随共享库一并构建的 vendored 静态库 `libzlib.a`、`libandroid_uuid.a`、
  `libopennurbs_public_freetype.a`；头 **896 个**（含补齐项）
- **消费测试：9/9 断言通过**（`OK (0 failure(s))`）——
  `ON_3dPoint::DistanceTo`、向量 `Length` 与点积、`ON_LineCurve` 合法性与
  `Domain`/`PointAt` 中点值、`ON_Xform::TranslationTransformation`、
  `ON_BoundingBox` 合法性与对角线

### 适配中挖出并修掉的 5 个上游缺口（均已写入配方注释）

| # | 现象 | 根因 | 处理 |
|---|---|---|---|
| 1 | `error: use of undeclared identifier 'fcloseall'` | `fcloseall()` 是 glibc 扩展，musl（OHOS）不提供 | 把上游**自带的** EOF 回退分支扩到 `__OHOS__` / `ON_RUNTIME_NO_FCLOSEALL`（源码单行替换；配方同时定义该宏作双保险） |
| 2 | `fatal error: 'android_uuid/uuid.h' file not found` | 该头**不在上游 install 规则**里（仅构建树可见） | `package()` 把 `android_uuid/*.h` 安装到两个头目录下 |
| 3 | `fatal error: 'opennurbs_cpp_base.h' file not found` | 上游 `OPENNURBS_PUBLIC_HEADERS` 清单**不完整**（源码 179 个头只装 169 个） | `package()` 把源码根目录的头整套补齐 |
| 4 | `ld.lld: undefined reference ... z_deflateInit_ / uuid_generate`（消费方链接 `libOpenNURBS.so` 时） | CMake **没有 HarmonyOS 平台文件** ⇒ `LINUX` 变量为假 ⇒ 上游 `if (LINUX AND NOT ANDROID)` 的 `target_link_libraries(OpenNURBS zlib …)` **不成立** ⇒ 共享库漏链 vendored zlib/freetype/android_uuid（`readelf -d` 只剩 libc/libc++ 两条 NEEDED） | 用 **`CMAKE_SYSTEM_NAME=Linux`**（cache var）把平台呈现为 Linux——与仓内 bliss/trilinos 注入 user_toolchain 的做法同源；本机编译器 target 本就是 aarch64-unknown-linux-ohos |
| 5 | `CMake Error: Compatibility with CMake < 3.5 has been removed`（`android_uuid/CMakeLists.txt:1`） | 缺口 4 修复后该 vendored 子目录被纳入配置，而它的 `cmake_minimum_required` 太老 | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（与 kdevelop-pg-qt 同坑） |

> 注：缺口 1–3 是**打包/可移植性**修复（不改上游算法），缺口 4–5 是**构建配置**修复。
> 上游源码仅一处单行改动（缺口 1），通过 `replace_in_file` 完成而**不用 .patch 文件**
> ——该文件是 2881 行、源自 Windows 的历史文件，逐行上下文对补丁格式过于敏感（实测
> hunk 无法命中），单行替换更稳。

### 消费侧注意

`package_info` 只默认暴露共享库 `OpenNURBS`（静态库 `opennurbsStatic` 与它符号重复，
一并列出会让消费方重复符号）；头同时装在 `include/OpenNURBS` 与
`include/opennurbsStatic` 两处（上游布局如此）。

## 上游测试申报（R51）

- **清点**：上游**没有注册任何 CTest 测试**（CMakeLists 无
  `enable_testing()`/`add_test()`；`BUILD_TESTING` 仅决定是否多装一个测试头）。
  仓库里的 `example_*` 目录是**示例程序**，不属于测试，且不在 `add_subdirectory`
  列表中（本配方不构建它们）。
- **实跑**：上游无套件可跑 ⇒ **N = 0**（原因即上，非"没环境"）。
- **补偿**：以**消费侧端到端测试**作为验证 —— 9 项断言，实测**全通过**（见上）。
