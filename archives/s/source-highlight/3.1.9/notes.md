# source-highlight 3.1.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 Conan AutotoolsToolchain 生成 configure 环境
2. autotools.configure() 执行 configure 脚本
3. autotools.make() 编译
4. autotools.install() 安装产物

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 找不到 boost_regex 库 | boost::regex 在 1.69+ 是 header-only，configure 仍尝试链接 | 创建空 libboost_regex.a 作为 stub，修改 configure 跳过链接检查 |
| 2 | config.status 的 mktemp -d 在 HMDFS 上失败 | HMDFS 不支持临时目录创建（E125） | 创建 mktemp wrapper 使用固定目录名 |
| 3 | configure 脚本 shebang 在 OHOS 上不兼容 | OHOS 的 bash 在 /data/service/hnp/bin/bash | sed 修复 shebang 路径 |
| 4 | C++17 兼容性警告 | 旧代码使用 dynamic-exception-spec 和 register 关键字 | 添加 -Wno-dynamic-exception-spec 和 -Wno-register |

## 源码修改

- `0001-build-aux-config.guess.patch`: 使 config.guess 识别 HarmonyOS 为 Linux+musl

## 依赖版本

- boost/1.90.0 (header-only)

## 验证结果

```bash
conan create . --profile:build=default --profile:host=ohos -tf test_package
# 编译通过，test_package 验证通过
```

## 注意事项

- boost::regex 是 header-only，configure 需要 stub 库绕过链接检查
- OHOS SDK 不包含 LLVM TableGen，不影响此库
---

**编译结束**: 2026-07-18 11:18
**最终状态**: built
