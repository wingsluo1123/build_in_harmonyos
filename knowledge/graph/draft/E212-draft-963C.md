# E212: Go 二进制项目 Conan 构建方法

## 基本信息
- **严重度**: 3
- **类别**: build_system
- **触发工具**: ohc-run.py conan-init
- **阶段**: build

## 错误特征
```
go: command not found
configure: not found
make: not found
AutotoolsToolchain is not Go
```

**关键词**: Go, golang, go build, binary tool, no configure

## 根因分析
`ohc-run.py conan-init` 默认使用 Autotools 模板生成 conanfile.py（configure + make），
但 Go 项目使用 `go build`，没有 configure 脚本和传统 Makefile。
生成的 Autotools 配方在 Go 项目上完全不可用。

**影响范围**: 所有 Go 语言二进制项目

## 推荐方案
- **方法**: 手动编写 Go 项目 conanfile.py
- **描述**: 
  1. `build()` 中使用 `self.run()` 调用 `go build`
  2. 去除 AutotoolsToolchain/Autotools 的 import
  3. `package()` 中从 `self.build_folder` 复制二进制
  4. `package_info()` 中清空 cpp_info，设置 runenv_info
  5. test_package 直接运行 `--version`

## 参考实现
详见 `archives/k/kopia/0.23.1/conanfile.py`

## 验证
```bash
python3 ohc-run.py conan-verify kopia 0.23.1
```
