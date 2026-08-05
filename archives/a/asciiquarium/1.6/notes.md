# Asciiquarium 1.6 编译笔记

## 软件信息
- **名称**: asciiquarium
- **版本**: 1.6
- **类型**: 纯 Perl 脚本（无 C/C++ 编译）
- **来源**: https://github.com/nothub/asciiquarium/archive/refs/tags/v1.6.tar.gz
- **SHA256**: 5fecaba770eee75eb4124c520d9d63dc4af4e69da116f86abcf1edccfde0e71d

## Conan 适配过程

### 适配概述
asciiquarium 是一个纯 Perl 脚本，不需要编译。Conan 配方的作用是：
1. 下载源码 tarball
2. 验证脚本是有效的 Perl 脚本
3. 将脚本打包到 bin/ 目录
4. 通过 test_package 验证脚本的正确打包

### 构建系统
- **类型**: script (纯脚本，无构建系统)
- **无 configure/make 步骤**
- **build() 方法**: 仅验证脚本存在且 shebang 正确

### Conan 配方
- `package_type = "application"` (命令行工具)
- `settings = "os", "compiler", "build_type", "arch"` (兼容 OHOS profile)
- `validate()`: R32 平台检查 `("Linux", "OHOS")`
- 无 conan 依赖（Perl 模块不是 conan 包）
- `package()`: 复制脚本到 bin/，文档到 share/doc/
- `package_info()`: `bindirs = ["bin"]`，无 libs

### Test Package
- **test.sh**: 验证脚本存在、shebang 正确、版本字符串、尝试执行
- 由于 CI 环境无 Perl 模块依赖（Term::Animation, Curses），测试接受模块缺失错误

### 运行时依赖（非 conan 包）
1. **Perl >= 5.42.0** - 系统已安装
2. **Term::Animation >= 2.0** - Perl 模块，需 cpan 安装
3. **Curses** - Perl 模块，需 cpan 安装

### commands.json (R38)
- 软件级别声明为 tool 类型

---

**Conan 适配完成**: 2026-08-05
**最终状态**: published
**质量门禁**: G1-G4 + L2/L4/L5 全部通过
