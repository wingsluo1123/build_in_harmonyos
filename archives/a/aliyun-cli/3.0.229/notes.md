# aliyun-cli 3.0.229 适配笔记

## 编译环境

- 构建系统: custom (Go)
- 编译日期: 2026-08-05
- 编译器: Go 1.24.0 (linux/arm64), CGO_ENABLED=0
- 状态: built

## 编译步骤

1. **init-build**: `ohc-run.py init-build aliyun-cli 3.0.229 --url=...`
2. **源码下载**: GitHub tarball (v3.0.229) + aliyun-openapi-meta submodule (master)
3. **子模块处理**: aliyun-openapi-meta 目录为空 (git submodule)，从 GitHub 镜像下载 master 分支
4. **Go编译**:
   ```bash
   CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
   GOPROXY=https://goproxy.cn,direct \
   GOTOOLCHAIN=local \
   GOCACHE=<ext2_path> GOPATH=<ext2_path> TMPDIR=<ext2_path> \
   go build -ldflags="-s -w -X 'github.com/aliyun/aliyun-cli/cli.Version=3.0.229'" \
     -o <ext2_link_out>/aliyun main/main.go
   ```
5. **ELF签名**: binary-sign-tool sign (HarmonyOS 执行前必须签名)
6. **验证**: aliyun version → 3.0.229

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aliyun-openapi-meta 为空 | tarball 不含 git submodule | 从 GitHub 下载 master 分支单独填充 |
| 2 | Go linker mmap 失败 | HMDFS 不支持 mmap 写操作 | 输出文件放在 ext2 分区 |
| 3 | 构建产物无法执行 | 未签名 ELF 不可执行 | 使用 binary-sign-tool 签名 |
| 4 | Go 二进制不可执行 | HMDFS 文件权限/SELinux 限制 | 使用已签名的 Go SDK 或 ext2 路径 |

## 依赖

- Go 1.18+ (go.mod 要求), 实际使用 1.24.0
- 无 C/C++ 依赖 (CGO_ENABLED=0)
- GOPROXY=goproxy.cn (国内加速)

## 验证结果

```bash
$ aliyun version
3.0.229
```

## Conan 配方要点

- `package_type = "application"` (CLI 工具)
- `build()` 方法处理 Go 编译 + 子模块下载 + ELF 签名
- `test_package/` 运行 `aliyun version` 验证
- `commands.json` 声明命令行工具 (R38)
- ext2 路径用于 GOCACHE/GOPATH/TMPDIR/链接输出
---

**编译结束**: 2026-08-05 21:30
**最终状态**: built
