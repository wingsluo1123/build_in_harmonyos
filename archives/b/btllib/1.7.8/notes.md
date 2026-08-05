# btllib 1.7.8 适配笔记

## 编译环境
- 构建系统: meson (with CMake subprojects)
- 编译日期: 2026-08-05
- 编译器: clang/clang++ 15.0.4
- 状态: published (conan-verify all gates passed)

## 构建步骤

1. `ohc-run.py init-build btllib 1.7.8`
2. Source tarball from GitHub releases
3. Git submodules cloned in conanfile.py source() method
4. `conan create` builds via Meson + Ninja
5. Patches applied via conandata.yml

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cpptoml/sdsl-lite/googletest/libdivsufsort CMakeLists.txt cmake_minimum_required | CMake 4.x 不支持 VERSION < 3.5 | conanfile.py source() 中 re.sub 替换为 3.5...4.1 |
| 2 | scripts/*.sh 使用 /bin/bash shebang | 鸿蒙系统 /bin/bash 不存在 | 13 个脚本补丁修改为 #!/usr/bin/env bash |
| 3 | meson.build 包含 tests 和 wrappers 子目录 | 测试需要 samtools 不可用 | 补丁禁用 tests 和 wrappers |
| 4 | strerror_r 在 OHOS (musl) 返回 int 而非 char* | OHOS 使用 musl libc，_GNU_SOURCE 已定义但 strerror_r 仍返回 int | 补丁使用 !defined(__GLIBC__) 检测非 glibc 系统 |
| 5 | Meson 找不到 llvm-ar | Meson 自动检测 clang 后默认用 llvm-ar，但不在 PATH | conanfile.py generate() 向 Meson native file 添加 ar 路径 |
| 6 | test_package 运行时找不到 libomp.so | 编译器路径未传入 subprocess | test_package conanfile.py 使用完整编译器路径 |
| 7 | git clone 子模块网络超时 | GitHub 连接不稳定 | 使用 git -c url.insteadOf 配置 ghfast.top 镜像 |

## 补丁列表 (15 个)

1. 0001-meson.build.patch - 禁用 tests 和 wrappers 子目录
2. 0002-0014 scripts/*.patch - bash shebang 修复 (13 个脚本)
3. 0015-src-btllib-status.cpp.patch - strerror_r POSIX/GNU 检测 (使用 !defined(__GLIBC__))

注: 子项目 CMake 版本修复 (0015-0018) 已从静态补丁迁移到 conanfile.py source() 中的运行时 re.sub 替换。

## Conan 配方

- conanfile.py: Meson 构建系统，source() 中克隆 git 子模块
- conandata.yml: 官方 GitHub 源码 URL + sha256
- test_package/: NtHash 烟雾测试 (创建 NtHash 对象，验证 roll/hashs/get_hash_num)
- commands.json: 软件级声明 (library 类型)

## 验证结果

- conan-verify: G0-G4 + L2/L4/L5 全部通过
- W3 本地 CI 模拟: setup.sh + build_and_test.sh 通过
- W4 Pre-PR 审计: PASS (P0=0, P1=0)

## 交付物

| 文件 | 说明 |
|------|------|
| libbtllib.a | 静态库 |
| indexlr | 可执行文件 |
| randseq | 可执行文件 |
| mi_bf_generate | 可执行文件 |

## 注意事项

- 测试被禁用（缺少 samtools），无法进行完整的上游测试验证
- 子项目 CMake 版本修复通过 conanfile.py source() 运行时处理（非静态补丁）
- OpenMP 由系统 clang 提供，无 conan 依赖

## 编译结束

**最终状态**: published (conan-verify all gates passed)
COMPLETED
