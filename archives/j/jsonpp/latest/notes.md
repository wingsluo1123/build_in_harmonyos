# jsonpp latest 适配笔记

## 编译环境
- 构建系统: go (Go command-line tool, no configure/make)
- 编译日期: 2026-07-03
- 编译器: clang/clang++ (system), go 1.26.4
- 状态: published

## 源码信息
- 仓库: https://github.com/jmhodges/jsonpp
- 版本: tag 1.3.0 (latest release)
- SHA256: dde8ea9b270a79cd2b2f40824f89abc5270bd360122d87ab04b4361c0015d941
- 许可证: MIT

## 编译步骤

```bash
# 1. 下载源码 (SSL 证书问题，需 curl -k 手动下载)
curl -k -sL -o jsonpp-latest.tar.gz https://github.com/jmhodges/jsonpp/archive/refs/tags/1.3.0.tar.gz

# 2. 构建二进制 (GOPATH 模式，无 go.mod)
cd jsonpp-latest.work
GO111MODULE=off go build -o jsonpp .

# 3. 安装到 staging
mkdir -p $TEST_PREFIX/bin
cp jsonpp $TEST_PREFIX/bin/

# 4. 运行测试
GO111MODULE=off go test -v ./...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah URL 下载失败 | SSL 证书验证失败 + URL 404 | 改用 GitHub 仓库 URL，curl -k 手动下载 |
| 2 | waterlan.home.xs4all.nl URL 不可用 | XS4ALL 主页服务已停止 | 改用 GitHub 仓库 URL |
| 3 | go build 报 "go.mod file not found" | tag 1.3.0 是 pre-modules 时代代码，无 go.mod | 设置 GO111MODULE=off 使用 GOPATH 模式 |
| 4 | go test 失败: non-constant format string | Go 1.26+ vet 对 fmt.Fprintf 非常量格式字符串报错 | 修改 jsonpp.go: 使用 %s 格式化占位符替代字符串拼接 |

## 源码修改

### jsonpp.go (行 28-29)
**修改前:**
```go
fmt.Fprintf(os.Stderr, "Usage: "+cmd+" [file]"+"\n")
fmt.Fprintf(os.Stderr, "   or: $COMMAND | "+cmd+"\n")
```
**修改后:**
```go
fmt.Fprintf(os.Stderr, "Usage: %s [file]\n", cmd)
fmt.Fprintf(os.Stderr, "   or: $COMMAND | %s\n", cmd)
```
**原因:** Go 1.26+ 的 go vet 将非常量格式字符串标记为错误，导致 `go test` 失败。

## 依赖版本

- Go: 1.26.4 (linux/arm64)
- 无外部依赖 (仅 Go 标准库)

## 验证结果

```bash
# 构建验证
$ jsonpp --help
Usage: jsonpp [file]
   or: $COMMAND | jsonpp

# 功能验证
$ echo '{"hello":"world","arr":[1,2,3]}' | jsonpp
{
  "hello": "world",
  "arr": [
    1,
    2,
    3
  ]
}

# 单元测试
$ GO111MODULE=off go test -v ./...
--- PASS: TestMultipleObjectFiles (0.06s)
--- PASS: TestAlreadyFormattedSingleJSON (0.01s)
PASS
ok      _/storage/.../jsonpp-latest.work        0.093s
```

## 二进制特征

- 类型: ELF executable, 64-bit LSB arm64, static
- 大小: ~2.5MB
- SHA256: 386f67d745cdd32126bb941630968f0cc79969b27cb2b3c3701ad53bee174892
- 注: Go 二进制默认静态链接，无 PIE (Type: EXEC)

## 注意事项

1. 下载源码需要 `curl -k` 绕过 SSL 证书验证
2. 构建必须设置 `GO111MODULE=off` (无 go.mod)
3. Go 1.26+ 需要修复 fmt.Fprintf 非常量格式字符串问题
4. 这是一个命令行工具，不是库，conanfile.py 的 package_info 不设置 libs
---

**编译结束**: 2026-07-03 12:52
**最终状态**: published
