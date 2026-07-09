# actionlint 1.7.9 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-07-02
- 编译器: Go 1.24.0 (linux/arm64), clang/clang++ (系统默认)
- 状态: published

## 编译步骤

1. 使用 `ohc-run.py init-build actionlint 1.7.9 --url=...` 下载源码并初始化归档
2. 源码解压到 `/storage/Users/currentUser/tmp/builds/actionlint-1.7.9.work`
3. 执行 Go 编译命令:
```bash
cd $BUILD_SRC_DIR
export CGO_ENABLED=0
go build -trimpath -ldflags '-s -w -X github.com/rhysd/actionlint.version=1.7.9' -o actionlint ./cmd/actionlint
```
4. Go 自动下载依赖（go.mod 中声明的模块），编译生成静态 ELF 二进制
5. 复制二进制到 staging 目录: `$TEST_PREFIX$DEFAULT_PREFIX/bin/`
6. 使用 elfldr 测试 `--version` 输出
7. 运行 `ohc-run.py conan-init` 生成 Conan 配方
8. 手动适配 conanfile.py 为 Go 构建系统（模板默认为 autotools）
9. 运行 `ohc-run.py conan-verify` 验证配方（G1-G4 + L2/L4/L5 全部通过）
10. 运行 `ohc-run.py finish actionlint 1.7.9 published` 收尾归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | OHOS 平台缺少 CA 证书包 | 设置 `SSL_CERT_FILE` 指向 certifi 的 cacert.pem |
| 2 | GitHub 下载超时 | 网络限制 | 使用 ghfast.top 镜像 URL |
| 3 | conanfile.py 使用 Autotools 模板 | init-build 默认检测为 autotools | 手动重写为 Go 构建系统（参考 helm 经验） |
| 4 | test_package 使用 CMake 模板 | 模板默认为 CMake | 重写为 elfldr 运行 --version 测试 |
| 5 | conandata.yml SHA256 为占位符 | 模板生成时未计算 | 用 sha256sum 计算并填入实际值 |
| 6 | 版本注入变量路径 | version 变量在 actionlint 包而非 main 包 | 使用 `-X github.com/rhysd/actionlint.version=1.7.9` |

## 源码修改

无补丁。源码使用 release tag v1.7.9 原始代码，未做任何修改。

## 依赖版本

- Go 1.24.0 (linux/arm64)
- Conan 2.30.0 (OHOS 适配版)
- elfldr (OHOS ELF 加载器)
- 无 C/C++ 库依赖（CGO_ENABLED=0）

## 验证结果

```bash
# --version 测试
$ elfldr actionlint --version
1.7.9
installed by building from source
built with go1.24.0 compiler for linux/arm64

# 合法工作流测试
$ elfldr actionlint -no-color test-workflow.yml
(无输出, exit code 0)

# 非法工作流测试
$ elfldr actionlint -no-color test-bad-workflow.yml
test-bad-workflow.yml:8:15: specifying action "actions/checkout" in invalid format...
(exit code 1)

# Conan 验证
$ python3 ohc-run.py conan-verify actionlint 1.7.9
✅ 配方验证通过: actionlint 1.7.9
✅ 可标记 status: published
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| actionlint (二进制) | 5,243,064 bytes | 静态 ELF 可执行文件 (AArch64) |
| conanfile.py | Conan 配方 | Go 构建系统适配 |
| conandata.yml | 源码声明 | URL + SHA256 |
| test_package/conanfile.py | L1 测试 | elfldr --version 测试 |

## 注意事项

- Go 工具链在 OHOS 上已由 elfldr 包装，`go build` 可直接使用，无需额外 wrapper
- 版本注入变量路径为 `github.com/rhysd/actionlint.version`，不是 `main.version`（变量在 actionlint 包的 command.go 中定义）
- 二进制为纯静态（CGO_ENABLED=0），无动态段，运行时需 elfldr 加载
- `packaging/` 手动 tar.gz 打包已废弃（v3.0），由 Conan 体系替代
---

**编译结束**: 2026-07-03 15:07
**最终状态**: published
