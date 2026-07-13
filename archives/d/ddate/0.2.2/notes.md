# ddate 0.2.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_C_FLAGS="$CFLAGS" \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -DBUILD_SHARED_LIBS=OFF \
         -DCMAKE_EXE_LINKER_FLAGS="-static"
make -j1
make install DESTDIR=$TEST_PREFIX
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制无法直接访问 github.com | 使用 gh-proxy.com 镜像通过 urllib3 下载 |
| 2 | CMake 报错 cmake_minimum_required(2.8) 不兼容 | CMake 4.x 移除了 < 3.5 兼容性 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | conan-init 默认使用 autotools 模板 | 软件注册表未指定 build_system，默认 autotools | 手动将 conanfile.py 改为 CMake 模板 |
| 4 | make check 不存在 | CMakeLists.txt 无 CTest 定义 | 跳过，使用 test_package/test.sh 替代 |
| 5 | test_package 默认为库模式 | conan-init 检测到 cpp_info.libs | 改为 executable 模式 (VirtualRunEnv + test.sh) |

## 源码修改

无源码修改。仅使用 CMake 参数适配。

## 依赖版本

无外部依赖。ddate 是纯 C 程序，仅依赖 musl libc。

## 验证结果

```bash
$ file ddate
ddate: ELF executable, 64-bit LSB arm64, static, not stripped

$ readelf -d ddate
There is no dynamic section in this file.

$ ddate
Today is Sweetmorn, the 30th day of Confusion in the YOLD 3192
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (CMake, 静态链接) |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | 可执行文件测试 (VirtualRunEnv + test.sh) |

## 注意事项

- ddate 实际使用 CMake 构建系统，而非 autotools（任务描述有误）
- CMake 4.x 需要 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 参数
- 作为终端工具，使用 -static 实现完全静态链接 (R26)
- 可执行文件包的 test_package 应使用 VirtualRunEnv 而非 CMakeDeps
---

**编译结束**: 2026-06-26 14:35
**最终状态**: published
