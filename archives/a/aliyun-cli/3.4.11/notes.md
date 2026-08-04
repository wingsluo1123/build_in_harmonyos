# aliyun-cli 3.4.11 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-08-05
- 编译器: Go 1.26.5 (Harmonybrew) / Go 1.24.0 (CI fallback SDK)
- 状态: built

## 编译步骤

1. Downloaded source tarball from GitHub (v3.4.11 tag)
2. Downloaded aliyun-openapi-meta git submodule separately (GitHub archive)
3. Set GOPROXY=https://goproxy.cn for Go module downloads
4. Set CGO_ENABLED=0 for static binary
5. Set GOTOOLCHAIN=local to prevent toolchain auto-download
6. Ran `go mod download` to fetch Go module dependencies
7. Built with: `go build -ldflags "-X 'github.com/aliyun/aliyun-cli/v3/cli.Version=3.4.11'" -o out/aliyun main/main.go`
8. ELF binary signed for OHOS using binary-sign-tool

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go not installed on system | HarmonyOS doesn't ship with Go | Installed via Harmonybrew (go 1.26.5) |
| 2 | aliyun-openapi-meta submodule empty | GitHub archive tarball doesn't include submodules | Downloaded submodule separately via gh-proxy.com mirror |
| 3 | Version shows "0.0.1" | Makefile uses wrong module path in ldflags | Used correct path: github.com/aliyun/aliyun-cli/v3/cli.Version |
| 4 | GitHub.com connectivity issues | HarmonyOS network restrictions | Used gh-proxy.com mirror for submodule download |

## 依赖版本

- Go SDK: 1.24.0 (CI fallback) / 1.26.5 (local)
- Go modules: managed via go.mod (Alibaba Cloud SDK packages)
- aliyun-openapi-meta: master branch

## 验证结果

```bash
$ ./out/aliyun version
3.4.11

$ file out/aliyun
ELF executable, 64-bit LSB arm64, static, not stripped
```

## 注意事项

- aliyun-cli is a Go project, not C/C++
- The conanfile.py includes Go SDK auto-download for CI environments
- ELF signing is required for OHOS (binary-sign-tool)
- The aliyun-openapi-meta submodule is downloaded in source() method
- GOTOOLCHAIN=local prevents Go from downloading a specific toolchain version
- GOPROXY=goproxy.cn ensures reliable module downloads in HarmonyOS environment
---

**编译结束**: 2026-08-05 02:07
**最终状态**: built
