# indi-nightscape 1.0.6-20221222181314 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, cmake_minimum_required 3.0, C++11/C++17)
- 编译日期: 2026-10-01
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, OHOS SDK)
- 状态: built (conan create + conan-verify 8 门禁全过)

## 编译步骤

```bash
# 1. 依赖获取 (全部已发布到 ohpcd):
#    libindi/2.2.2.1, cfitsio/4.6.4, libusb/1.0.27, libftdi/1.5

# 2. CMake 配置 (E092: CMake 不识别 HarmonyOS -> 显式 CMAKE_SYSTEM_NAME=Linux)
cmake -S nightscape-src -B build \
  -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_INSTALL_PREFIX=<prefix> \
  -DCMAKE_MODULE_PATH=nightscape-src/cmake_modules

# 3. 构建 (产物: indi_nightscape_ccd + nstest)
cmake --build build -j2

# 4. 安装 (bin/indi_nightscape_ccd + share/indi/indi_nightscape.xml; udev rules 已禁用)
cmake --install build
```

Conan 配方 (archives/i/indi-nightscape/1.0.6-20221222181314/)：
```bash
NIGHTSCAPE_SRC_TARBALL=<本地预打包源码包> \
conan create archives/i/indi-nightscape/1.0.6-20221222181314 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(3.0) 被新 CMake 拒绝 | CMake >=3.28 移除了 <3.5 兼容 | CMAKE_POLICY_VERSION_MINIMUM=3.5 (参考 libftdi) |
| 2 | find_package(CFITSIO) 走 config 模式，CFITSIO_INCLUDE_DIR 未定义，fitsio.h 找不到 | Conan CMakeToolchain 默认 PREFER_CONFIG=ON，cfitsio-config.cmake 恰好同名命中 | PreferConfigOffBlock 强制 OFF (libindi 同款) |
| 3 | FindINDI.cmake "failed to detect INDI version" | 正则 `.*INDI_VERSION ([0-9]+)...` 无法匹配带引号 `#define INDI_VERSION "2.2.2"` | patch 放宽正则 `.*INDI_VERSION[ ]*"?([0-9]+)[.]?...` |
| 4 | `no type named 'any' in namespace 'std'` | CMakeCommon.cmake 强制 C++14，libindi 2.x 头用 std::any (C++17) | patch 14->17 |
| 5 | `use of undeclared identifier 'TemperatureN'/'BayerT'`、`.s` 不存在、operator& protected | 2022 年源码用旧 INDI API，libindi 2.2.x 迁移到 PropertyNumber/PropertyText 类 | 按上游 master 适配: TemperatureNP/BayerTP/getState()/apply()/save()/setValue() |
| 6 | `secure_getenv` 未声明 | OHOS musl libc 无该 glibc 扩展 | 统一 `#define ___secure_getenv getenv` |
| 7 | `'libftdi1/ftdi.h' file not found` | FindFTDI1.cmake 未定义 FTDI1_INCLUDE_DIRS (CMakeLists 引用复数变量)，且路径在 include/libftdi1 子目录 | patch 用 get_filename_component 派生父目录 |
| 8 | install 到 /lib/udev/rules.d 失败 | OHOS 无 /lib/udev 可写目录 | CMakeLists 加 NIGHTSCAPE_INSTALL_UDEV_RULES 选项默认 OFF |
| 9 | INDI_DATA_DIR-NOTFOUND 安装到错误路径 | FindINDI.cmake 找不到 drivers.xml (libindi 包内 share/indi 存在但 find_path 需 PREFIX) | CMakeLists 回退 share/indi |
| 10 | ld.lld: warning: unknown -z value: nodump | CMakeCommon.cmake 硬化 flag 中 -Wl,-z,nodump 是 GNU ld 私有选项 | 仅 warning 不阻塞 |

## 源码修改 (patches/)

| 补丁 | 内容 |
|------|------|
| 0001-CMakeLists-OHOS-install-cmake.patch | INDI_DATA_DIR 回退 share/indi; udev rules 安装加开关默认 OFF |
| 0002-nightscape-INDI2-API-migration.patch | nightscape.cpp 迁移到 libindi 2.2.x 新 Property API; secure_getenv->getenv |
| 0003-FindINDI-version-regex.patch | 版本正则兼容带引号 INDI_VERSION |
| 0004-FindFTDI1-include-dirs.patch | 定义 FTDI1_INCLUDE_DIRS 指向 ftdi.h 父目录 |
| 0005-CMakeCommon-cxx17.patch | C++ 标准 14->17 |

## 依赖版本

| 包 | 版本 | 说明 |
|----|------|------|
| libindi | 2.2.2.1 | INDI 驱动框架 (新 Property API) |
| cfitsio | 4.6.4 | FITS 读写 |
| libusb | 1.0.27 | USB 通信 (FTDI 通道) |
| libftdi | 1.5 | FTDI 芯片访问 |

## 验证结果

```bash
# conan create (含 test_package 实质测试)
indi-nightscape/1.0.6-20221222181314@ohpcd/stable (test package): RUN: /data/service/hnp/bin/bash test.sh <pkg>
--- indi-nightscape consumer verification ---
PASS 1: installed artifacts present (indi_nightscape_ccd, nstest, indi_nightscape.xml)
PASS 2: nstest runs and reaches FTDI/libusb init (expected without hardware)
test indi-nightscape 1.0.6-20221222181314: 2/2 checks PASS

# conan-verify 8 门禁: G0-G4 + L2/L4/L5 全过
✅ 配方验证通过: indi-nightscape 1.0.6-20221222181314

# nstest (上游测试工具) 实测: 无硬件时输出预期错误 (依赖链加载成功)
$ ./build/nstest
unable to init ftdi scan device: -3 (libusb_init() failed)
```

## 上游测试申报表 (R51)

| 项目 | 结论 |
|------|------|
| 上游测试目录 (tests/) | 无独立 tests/ 目录 (0 个) |
| CTest 注册 | 0 (CMakeLists.txt 无 enable_testing/add_test) |
| 测试程序 | nstest (nstest-main.cpp, FTDI/libusb 通道硬测): 编译成功 ✅, 无硬件条件下实测运行到 libusb_init() 失败 (预期, 依赖链加载成功) ✅; 完整硬件测试需真机 |
| test_package | test.sh: 产物完整性 + nstest 运行到 FTDI init (2/2 PASS) |

## 交付物

| 文件 | 说明 |
|------|------|
| bin/indi_nightscape_ccd | INDI 驱动可执行 (主产物) |
| bin/nstest | 上游测试工具 (随包交付, package() 复制) |
| share/indi/indi_nightscape.xml | 驱动注册 XML |

## 注意事项

- 本包是 CLI 工具/驱动 (application), 需要 commands.json (R38, 已创建 archives/i/indi-nightscape/commands.json)
- 官方整仓 tarball sha256 已获取并修正: 6a1ab7ae4d5c343adcc8212cd7795c84311953e59ea3d344c2a1f2e9ca64be8b (完整 168MB 下载实测; 曾误写截断文件哈希 fdc66a9d... 已修正)
  (codeload.github.com 下载成功, 与官方 github archive URL 同 commit 一致)
- 本地验证可用 NIGHTSCAPE_SRC_TARBALL 指向预打包源码包 (内容与官方 indi-nightscape/ 子目录一致)
- libindi 动态库在 OHOS 上运行时加载受限 (E537 教训), test_package 不直接运行 indi_nightscape_ccd, 改跑 nstest (仅依赖 libftdi/libusb)
- CMakeCommon.cmake 的 -Wl,-z,nodump 在 lld 下仅 warning, 不影响产物
---

**编译结束**: 2026-10-01 22:26
**最终状态**: built
