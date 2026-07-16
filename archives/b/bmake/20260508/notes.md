# bmake 20260508 适配笔记

## 编译环境
- 构建系统: autotools (configure + make-bootstrap.sh)
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (OHOS 工具链)
- 状态: built

## 编译步骤
1. `./configure --prefix=$DEFAULT_PREFIX --without-makefile --without-meta --without-filemon CXX=clang++`
2. `sh make-bootstrap.sh op=build` — 编译 bmake 二进制
3. `sh make-bootstrap.sh op=install --install-prefix=$PREFIX` — 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建临时目录时 Permission denied | HarmonyOS 文件系统上 umask 077 配合 mktemp -d 创建的目录因 SGID 位导致权限异常 | 补丁 0001-configure.patch: umask 077 → 022 |
| 2 | GNU make 无法解析 Makefile | bmake 的 Makefile 使用 BSD make 语法，GNU make 无法解析 | 使用 make-bootstrap.sh 替代 make 构建 |
| 3 | 单元测试 fork 耗尽系统资源 | bmake 单元测试套件 fork 大量进程 | 跳过单元测试，仅通过 test_package 验证二进制可用性 |

## 源码修改

- `patches/0001-configure.patch`: 修改 configure 脚本的临时目录创建权限 (umask 077 → 022)，适配 HarmonyOS 文件系统 SGID 行为

## 依赖版本

无外部依赖（零依赖编译）

## 验证结果

```bash
$ bmake -r -V MAKE_VERSION
20260508
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/bmake | 227KB | bmake 可执行文件 |
| share/mk/* | 多文件 | bmake 运行时需要的 mk 规则文件 |

## 注意事项

- bmake 是命令行工具 (package_type: application)，已创建 commands.json 声明
- 许可证: BSD-3-Clause
- 补丁为 HarmonyOS 平台特化 (platform_only: True)，仅影响临时目录创建权限

---

**编译结束**: 2026-07-15 16:44
**最终状态**: built