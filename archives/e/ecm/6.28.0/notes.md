# ecm 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `init-build ecm 6.28.0 --url=https://download.kde.org/stable/frameworks/6.28/extra-cmake-modules-6.28.0.tar.xz`
2. `lang-preflight ecm 6.28.0` → cpp 匹配通过
3. 本地探索编译（cmake 4.1.2）：
   - `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TESTING=OFF`
   - `make -j1`（需 `LD_LIBRARY_PATH=$SDK/llvm/lib/aarch64-linux-ohos:$SDK/llvm/lib`，否则 cmake/lld 符号缺失）
   - `make install DESTDIR=$TEST_PREFIX` → staging 验证 ECMConfig.cmake 落位
4. `conan-init` 生成配方 → 参照 6.26.0 修正 conanfile.py（build-scripts / BUILD_TESTING=OFF / package_id clear / ECM cmake_file_name）
5. `conan-verify`：
   - G1 配方完整性 PASS
   - G2 conan create PASS（配方 generate() 用 `_sdk_runtime_env().vars(self).save_script("sdk_runtime_env")` 将 SDK lib 目录前置 LD_LIBRARY_PATH，覆盖 build/package/test 全阶段）
   - G3 系统同名库隔离 PASS
   - G4 产物完整性 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake` 命令报 `Error relocating ... symbol not found` | harmonybrew cmake 4.4.3 二进制与 OHOS 运行库不兼容 | 用 `/data/service/hnp/bin/cmake`（4.1.2） |
| 2 | make 内 cmake_check_build_system 及 conan create 报 `Error loading shared library libc++_shared.so` | cmake/lld 二进制动态加载 SDK `llvm/lib/aarch64-linux-ohos/libc++_shared.so`，shell LD_LIBRARY_PATH 未包含该目录 | 配方 generate() 中 `_sdk_runtime_env()` 将 SDK lib 及 aarch64-linux-ohos 子目录 prepend 到 LD_LIBRARY_PATH，`save_script` 覆盖 build/package/test 全阶段（参照 prison 6.18.0 的 `_library_runtime_env` 模式） |
| 3 | make jobserver `mkfifo: Operation not permitted` | OHOS 权限限制 TMPDIR 下 mkfifo | `MAKEFLAGS=` + `make -j1`（CI 由 build_and_test.sh 处理） |
| 4 | 上游测试 10/87 失败（ExecuteKDEModules/KDEFetchTranslations/KDEInstallDirsTest.vars_in_sync_*/ecm_add_tests） | ECM 测试默认走 Qt5 路径（KDEInstallDirs5.cmake→ECMQueryQt.cmake 需 Qt5 qmake；ecm_add_tests 需 Qt5Core cmake 配置）；制品仓 qt5/5.15.19 的 Qt5CoreConfig.cmake 在 OHOS 上 mkspecs 路径缺陷（p/../b//mkspecs/linux-clang 不存在），注入 Qt6（qtbase）与 Qt5 后逐例实测仍无法配置通过 | 非"OHOS 无 Qt"，属依赖包 cmake 配置缺陷；与模块安装物无关；BUILD_TESTING=OFF 跳过构建期测试 |

## 依赖版本

- 无运行时依赖（纯 CMake 模块库，build-scripts）
- 构建工具: cmake 4.1.2（/data/service/hnp）、clang 15.0.4

## 验证结果

```bash
# conan create 主包
conan create archives/e/ecm/6.28.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → PASS（source/configure/build/install 全通过）

# test_package
# → CMake configure + build(test_ecm) + test() 运行 test_ecm 通过（版本断言 6.28.0、ECMFindModuleHelpers 加载成功）

# 上游测试实测（BUILD_TESTING=ON 单独构建）
ctest --output-on-failure → 77/87 passed（10 个需 Qt 环境失败）
```

## 注意事项

- ECM 是 KDE 框架的构建依赖（build-scripts），prison 6.28.0 要求 `find_package(ECM 6.28.0)`；制品仓此前 KDE ECM 最高仅 6.26.0，本包发布后可供 prison 6.28.0 及后续 KF 6.28+ 组件使用。
- 本配方 SDK 运行库路径修复（save_script 全阶段）为 OHOS 上所有 HNP cmake 工具链构建的 KDE 包共用范式。
---

**编译结束**: 2026-10-03 01:54
**最终状态**: published
