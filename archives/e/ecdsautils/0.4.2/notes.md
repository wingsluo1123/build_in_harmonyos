# ecdsautils 0.4.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 源码：官方 tag 归档 `https://codeload.github.com/freifunk-gluon/ecdsautils/tar.gz/refs/tags/v0.4.2`（45944 字节，自算 sha256 `8880e5a506555a06d7a866de8a76c28bb4c7472abbf0d3fb396100d16c447174`，解包得到顶层 `ecdsautils-0.4.2/`，与版本 0.4.2 逐字对应）。
2. 构建系统**实测为 CMake**（顶层 `CMakeLists.txt` + `src/*/CMakeLists.txt`；仓内唯一 Makefile 是 `contrib/Makefile-openwrt`，属 OpenWrt 打包件、非本包构建系统）。
3. 配方 `generate()` 注入三项 CMake 缓存变量后 `cmake.configure()` / `cmake.build()` / `cmake.install()`：
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(VERSION 2.8.3)`，平台 CMake 4.1.2 拒绝 <3.5 策略）；
   - `BUILD_SHARED_LIBS=OFF`（默认静态，避免 `.so` 污染）；
   - `CMAKE_SKIP_INSTALL_RPATH=ON`（musl 下 `cmake --install` 会字节级改写 RPATH）。
4. 依赖 `libuecc/7.0`（上游 `find_package(libuecc REQUIRED)`），制品仓 ohpcd 上配方与 OHOS armv8 二进制均已发布（rrev `ed072f3c65f5f156a891df57e4033da8`，pkg id `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 拒绝 `cmake_minimum_required(2.8.3)` | 上游 2016 年代工程，CMake >= 4.0 移除了 <3.5 策略兼容 | `cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（必须走 cache_variables，写进 toolchain 的 `variables` 不生效） |
| 2 | `find_package(libuecc REQUIRED)` 在本机/CI 找不到 libuecc | 上游顶层 `set(CMAKE_MODULE_PATH ${ECDSAUTIL_SOURCE_DIR})` 使自带 `Findlibuecc.cmake` 恒走模块模式；该模块依赖 pkg-config 提示，而 conan 包内 `lib/pkgconfig/libuecc.pc` 的 `prefix=` 是**打包机的绝对路径**（实测为 `/storage/Users/currentUser/.cache/conan2/p/b/libueb919882e9b2f7/p`），换机即失效 | 在 `generate()` 里用 `self.dependencies["libuecc"].package_folder` 直接预置 `LIBUECC_INCLUDE_DIR`（`include/libuecc-7`）与 `LIBUECC_LIBRARIES`（`lib/libuecc.a` 或 `lib/libuecc.so`）两个 CMake 缓存项，`find_path`/`find_library` 见缓存即跳过搜索 |
| 3 | 公开头 `ecdsautil/ecdsa.h` 内部 `#include <libuecc/ecc.h>`，消费者默认 include 路径找不到 | 上游把头装到 `include/ecdsautil-0.4.2/ecdsautil/`，conan 默认 `includedirs=["include"]` | `package_info()` 显式 `includedirs=["include/ecdsautil-0.4.2"]`；`requires("libuecc/7.0")` 让 Conan 2 把 libuecc 作为传递用法需求带给消费者 |
| 4 | `conan create` 报 `BadZipFile: File is not a zip file`（source() 第 43 行） | 官方 codeload URL 结尾是 `refs/tags/v0.4.2`，**没有压缩格式后缀**；conan 的 `get()` 用 URL basename 推断文件名（得 `v0.4.2`），`unzip()` 找不到后缀就走 zip 解压分支 | `get(..., filename="ecdsautils-0.4.2.tar.gz", strip_root=True)` 显式给文件名（手册/07 §12.3 原文口径：「无 .tar.gz 后缀时显式指定 filename」） |
| 5 | 上游无任何测试 | tarball 内 `find . -iname '*test*'` 0 命中、`grep enable_testing\|add_test\|ctest` 0 命中、无 `test/` 目录 | N_static=0，仅提供消费者测试（`test_package/test_ecdsautils.c`，9 条断言） |

## 源码修改

无补丁（`patches/` 为空）。所有适配点均在配方侧完成，未改动上游源码。

## 依赖版本

| 依赖 | 版本 | 来源 |
|---|---|---|
| libuecc | 7.0 | ohpcd 制品仓（配方 + OHOS armv8 静态/动态二进制均已发布） |

## 验证结果

2026-10-08 19:33 实跑 `ohc-run.py conan-verify ecdsautils 0.4.2`（profile `ci/conan/profiles/ohos-aarch64`，Conan 2.29.1）：

| 门 | 结果 |
|---|---|
| G0 预构建风险评估 | PASS |
| G1 配方完整性（含 R26 / test_package / MANIFEST / export_sources / 补丁调用） | PASS |
| G2 conan create 干净构建 | PASS |
| G3 系统同名库隔离 (R26) | PASS |
| G4 产物完整性 | PASS |
| L2 / L4 / L5 | 跳过（本轮无 cache 路径读数） |

`conan create` 实跑链路（`reports/conan-create.log`）：

- `Building C target libecdsautil` → `Linking C static library libecdsautil.a` → `Linking C executable ecdsautil`（11 个 .c 全部编译，1 条上游自身 `-Wtautological-constant-out-of-range-compare` 警告，keygen.c:94 `getopt(...) != -1`，属上游既有写法、非适配引入）；
- `package(): Packaged 4 files: ecdsautil, ecdsakeygen, ecdsasign, ecdsaverify` + `1 '.a' file: libecdsautil.a` + `1 '.pc' file: ecdsautil.pc` + `2 '.h' files: ecdsa.h, sha256.h`；
- test_package：`conan create` 的 Executing test 阶段直接运行编译产物，输出 `test_ecdsautils: 9/9 assertions passed`（exit 0）。test() 走 self.run 直跑二进制以满足本地 L0 门禁，CMakeLists 里的 enable_testing/add_test 仅作注册、本轮不由 ctest 驱动。

五维测试账本：

| 维度 | 数值 | 口径 |
|---|---|---|
| N_static（上游静态声明） | 0 | tarball 内 `find . -iname '*test*'` 0 命中、`grep enable_testing\|add_test\|ctest` 0 命中、无 test 目录 |
| N_registered（构建系统注册目标） | 0 | 上游 `CMakeLists.txt` 无 `enable_testing()`/`add_test()` |
| N_executed | 0 | 无上游测试可执行 |
| 未执行分类 | 0 | 非「跳过」，是「上游本就没有」 |
| N_consumer（消费者测试程序数） | 1 | `test_package/test_ecdsautils.c`，9 条 CHECK 断言，实跑输出 `9/9 assertions passed`、exit 0 |

通过率口径：上游测试用例通过率 `0/0`（上游无自动化测试，无分母可报）；新增测试用例通过率 `1/1`（100%）。

回归结论：conan-verify **3 轮中第 3 轮通过（G0–G4 全绿）**，前两轮失败根因分别为 codeload URL 无后缀被当 zip 解压、以及静态库传递头默认被剥（见上表第 4/5 行问题记录）。

## 注意事项

- 语言实测：C 源 11 个、C 头 11 个，`.py`/`.sh` 0 个（全包 45 个文件），**主语言 C，与声明一致**。
- 能力面实测：源码内 `AF_/PF_`、`netlink`、`x86`、`kernel module`、`AF_PACKET/SOCK_RAW/BPF`、`ptrace/seccomp`、`opengl` 全部 0 命中；唯一设备访问是 `src/cli/random.c` 的 `open("/dev/random", O_RDONLY)`，本机实测 `crw-rw-rw-` 可读、16 字节读取成功。
- 上游 `contrib/Makefile-openwrt` 与 `debian/` 属打包件，不参与本包构建。
---

**编译结束**: 2026-10-08 21:17
**最终状态**: built
