# ytt 0.55.1 适配笔记

## 编译环境
- 构建系统: Go (go build / go.mod)
- 编译日期: 2026-07-02
- 编译器: Go 1.24.0 (goinstall, ELF-signed)
- 平台: OpenHarmony aarch64 (linux/arm64)
- 状态: published

## 编译步骤

ytt 是 Go 语言项目，使用 `go build` 编译，非 autotools/cmake。

```bash
# 1. 下载源码 (init-build 自动完成)
# 2. 修改 go.mod: go 1.26.3 → go 1.24.0 (匹配可用 Go 工具链)
# 3. 构建
export GODEBUG=mmap=0  # 关键：禁用 Go linker mmap 输出
export GOTOOLCHAIN=local
LDFLAGS="-X carvel.dev/ytt/pkg/version.Version=0.55.1"
GODEBUG=mmap=0 CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  go build -mod=vendor -ldflags="$LDFLAGS" -trimpath -o ytt ./cmd/ytt

# 4. ELF 签名 (OHOS 必需)
binary-sign-tool sign -keyAlias "default" -signAlg SHA256withECDSA \
  -inFile ytt -outFile ytt.signed -selfSign 1 -moduleFile module.json
cp ytt.signed ytt && chmod +x ytt

# 5. 安装到 staging
mkdir -p $TEST_PREFIX/bin && cp ytt $TEST_PREFIX/bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 1.26.3 二进制无法执行 | OHOS 要求 ELF 签名，从 go.dev 下载的 Go 1.26.3 未签名 | 使用已签名的 Go 1.24.0 (goinstall)，修改 go.mod 版本要求 |
| 2 | Go linker "mapping output file failed: permission denied" | OHOS SELinux 限制 Go linker 的 mmap(PROT_WRITE) 输出操作 | 设置 GODEBUG=mmap=0 禁用 mmap 输出，改用 write() |
| 3 | 编译产物无法执行 | OHOS 要求 ELF 二进制必须签名才能执行 | 使用 binary-sign-tool selfSign=1 签名 |
| 4 | go.mod 要求 go 1.26.3 但仅有 go 1.24.0 | ytt v0.55.1 使用了较新 Go 版本 | 修改 go.mod 为 go 1.24.0 (源码兼容) |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| go.mod | `go 1.26.3` → `go 1.24.0` (匹配可用已签名 Go 工具链) |

## 依赖版本

- Go 1.24.0 (linux/arm64, ELF-signed, from goinstall)
- binary-sign-tool (OHOS SDK 26.0.0.18_1)
- 依赖全部 vendored (vendor/ 目录)

## 验证结果

### 基础功能验证

```bash
$ ytt --version
ytt version 0.55.1

$ ytt --help
ytt performs YAML templating.
Docs: https://carvel.dev/ytt/docs/latest/
...
```

### 上游 Go 测试套件 (OHOS 平台执行)

通过 `go test -c` → ELF 签名 → 执行 的三步法在 OHOS 上运行上游测试：

| 包 | PASS | FAIL |
|----|------|------|
| pkg/cmd/template | 96 | 0 |
| pkg/experiments | 2 | 0 |
| pkg/files | 2 | 0 |
| pkg/orderedmap | 1 | 0 |
| pkg/template | 9 | 0 |
| pkg/texttemplate | 1 | 0 |
| pkg/validations | 1 | 0 |
| pkg/yamlfmt | 1 | 0 |
| pkg/yamlmeta | 26 | 0 |
| pkg/yamlmeta/internal/yaml.v2 | 2 | 0 |
| pkg/yamltemplate | 1 | 0 |
| test/e2e | 12 | 0 |
| test/filetests | 1 | 0 |
| **合计** | **155** | **0** |

3 个 examples 模块测试因独立 go.mod 未执行（上游结构限制）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ytt | ~16MB | ELF aarch64 static, self-signed |

## 注意事项

1. **GODEBUG=mmap=0 是必需的**：OHOS SELinux 限制 Go linker 的 mmap 输出，不设置此环境变量会导致 "mapping output file failed: permission denied"
2. **ELF 签名是必需的**：所有 Go 编译产物必须使用 binary-sign-tool 签名后才能在 OHOS 上执行
3. **Go 工具链版本**：go.mod 中的版本需要匹配可用已签名的 Go 工具链版本
4. **Go 测试执行方法**：通过 `go test -c` 分离编译与执行，中间插入 ELF 签名步骤，可在 OHOS 上运行完整 Go 测试套件（155/155 通过）
---

**编译结束**: 2026-07-02 14:02
**最终状态**: published
