# indi-shelyak 1.0-20221222171819 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-01
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## 编译步骤
1. 源码获取：savannah 发布镜像（download.savannah.nongnu.org/releases/indi-shelyak/）全部 404，不可用。
   官方源码在 GitHub indilib/indi-3rdparty 仓库的 indi-shelyak/ 子目录（位于官方 tag v2.2.5）。
   因全仓 tarball 约 3.3GB 不可行，采用 libfishcamp 先例：从官方 raw host
   （raw.githubusercontent.com/indilib/indi-3rdparty/v2.2.5/...）逐文件拉取构建所需的
   9 个驱动源文件 + 4 个 cmake_modules 文件（FindINDI 依赖链），打包为源码 tar.gz。
2. init-build --url=file://... 本地路径初始化（.build-context-indi-shelyak-1.0-20221222171819）。
3. lang-preflight: task=cpp, detected=cpp 匹配通过。
4. Step 2 手动编译验证（cmake）：
   ```
   source .build-context-indi-shelyak-1.0-20221222171819
   cd $BUILD_SRC_DIR && mkdir -p build && cd build
   cmake .. -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> \
     -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
     -DINDI_ROOT=<libindi package> -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF
   make -j2   # ✓ 两个可执行文件构建成功
   make install DESTDIR=$TEST_PREFIX  # ✓ bin/ 2 个驱动 + indi_shelyak.xml
   ```
   make check/test：上游 CMakeLists.txt 未注册任何测试目标（无 add_test），N/A。
5. conan-init 生成配方，人工修正：
   - requirements: libindi/2.2.2.1（W0 预检已发布到 ohpcd 制品仓）
   - source(): 逐文件 download()（非 get()，因源为裸文件非归档）
   - generate(): CMAKE_SYSTEM_NAME=Linux (E092), INDI_ROOT 指向 libindi 包,
     INDI_DATA_DIR=share/indi（防止 xml 装进依赖包绝对目录）,
     CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF（vendored FindINDI.cmake 优先）
   - build(): -DINDI_DATA_DIR=share/indi 以 cache 变量传入（find_path 不覆盖）
   - package_type=application, cpp_info.bindirs=["bin"]
6. R38: 产物含 2 个可执行文件 → 软件级 commands.json（tool 类型）。
7. test_package（R34 实质测试，非空壳）：test_shelyak.py 消费者探针——
   ELF64/AArch64 身份 + DT_NEEDED 链接 libindidriver/libindiAlignmentDriver/
   libc++_shared + indi_shelyak.xml 注册文件解析校验（17 项断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | savannah 镜像 404 | 上游已停用 savannah 发布 | 官方 GitHub indi-3rdparty 子目录 + raw 文件拉取 |
| 2 | 全仓 tarball 3.3GB 下载不可行 | indi-3rdparty monorepo 巨大 | libfishcamp 先例：仅拉取构建所需文件的 raw URL |
| 3 | CMake 不识别 HarmonyOS | E092 已知模式 | CMAKE_SYSTEM_NAME=Linux + PROCESSOR=aarch64 |
| 4 | find_package(INDI) 找不到 | 需 vendored FindINDI.cmake + INDI_ROOT | 下载 cmake_modules/FindINDI.cmake 依赖链 + INDI_ROOT=libindi 包 |
| 5 | indi_shelyak.xml 装到依赖包绝对目录 | FindINDI 的 INDI_DATA_DIR 默认解析为 libindi share/indi | -DINDI_DATA_DIR=share/indi cache 变量 |
| 6 | 驱动二进制无法在构建宿主执行 | E537/R49: HMDFS 无法对 OHOS 共享库 mmap PROT_EXEC（libindi/libfli 同款限制） | test_package 用 ELF 解析探针实质验证制品（非执行二进制） |

## 依赖版本

- libindi/2.2.2.1 (ohpcd 制品仓，已发布)
  - 传递依赖: cfitsio/4.6.4, libnova/0.16, libusb/1.0.27, curl/8.15.0.1,
    gsl/2.8, libjpeg/10, zlib/1.3.1.1, fftw/3.3.11, libev/4.33

## 验证结果

```bash
# ELF 身份 + 动态链接验证（test_shelyak.py 探针，17 项断言全部通过）
SHELYAK_PKG_DIR=<pkg> python3 test_shelyak.py
# 输出: == 17 checks, 0 failures ==; RESULT: PASSED

# 上游 make check：上游未注册测试目标，N/A（已记录于 MANIFEST.yml）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CMake + libindi 依赖） |
| conandata.yml | 官方 GitHub raw URL 源（R39/PF7 合规）+ sha256 |
| test_package/ | 消费者探针（17 项断言，非空壳） |
| commands.json | 软件级命令声明（R38, 2 个命令行驱动） |

## 注意事项

- 源码 URL 用官方 GitHub raw host（raw.githubusercontent.com），符合 R39/PF7，
  无镜像域名、无 file:// 泄漏（conandata 内均为 https 官方源）。
- 版本号 1.0-20221222171819 按 R37 首次适配规则原样使用。
- 分支名：feat/indi-shelyak-1.0-20221222171819（PF9 pkg-version 形式）。
---

**编译结束**: 2026-10-01 23:02
**最终状态**: built
