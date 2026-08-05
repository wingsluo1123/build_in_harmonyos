# aliyun-cli homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-03
- 编译器: Go 1.26.3 (arm64), CGO with clang
- 状态: published

## 编译步骤

1. **init-build**: `python3 ohc-run.py init-build aliyun-cli homebrew --url=https://github.com/aliyun/aliyun-cli/archive/refs/tags/v3.0.229.tar.gz --no-download` (SSL下载失败，手动curl从ghfast.top镜像下载)
2. **修正manifest**: system=custom, build_system=go
3. **子模块处理**: 手动下载 aliyun-openapi-meta (git submodule) 从 ghfast.top 镜像，放入源码目录
4. **Go编译**: `CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct ~/usr/local/go1263/bin/go build -ldflags="-s -w -X 'github.com/aliyun/aliyun-cli/cli.Version=3.0.229'" -o aliyun ./main/`
5. **版本注入**: 通过 `-ldflags "-X 'github.com/aliyun/aliyun-cli/cli.Version=3.0.229'"` 注入版本号
6. **DESTDIR安装**: cp aliyun → $TEST_PREFIX/$DEFAULT_PREFIX/bin/aliyun
7. **ELF签名**: ohc-run.py sign-elf
8. **DEFAULT_PREFIX安装**: cp aliyun → $DEFAULT_PREFIX/bin/aliyun
9. **验证**: ~/usr/local/bin/aliyun version → 3.0.229
10. **finish**: ohc-run.py finish aliyun-cli homebrew published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载GitHub超时 | 鸿蒙平台SSL证书问题 | 使用ghfast.top镜像手动下载 |
| 2 | aliyun-openapi-meta目录为空 | tarball不含git submodule | 手动从ghfast.top下载子模块master分支 |
| 3 | G0 clean-verify失败 | Go项目无configure脚本 | 预期行为，custom build_system不适用G0验证 |

## 依赖版本

- Go 1.26.3 (~/usr/local/go1263/bin/go)
- CGO (clang 15.0.4)
- GOPROXY=goproxy.cn

## 验证结果

```bash
$ ~/usr/local/bin/aliyun version
3.0.229
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aliyun-cli-homebrew-ohos-aarch64.tar.gz | 77080KB | 预编译包(含ELF签名) |

## 注意事项

- Go项目版本注入路径: `github.com/aliyun/aliyun-cli/cli.Version` via ldflags -X
- G0验证不适用于Go/custom构建系统
- 子模块需单独下载（tarball不含git submodule）
- TMPDIR=/data/storage/el2/base/cache (R10铁律)
---

**编译结束**: 2026-08-05 19:18
**最终状态**: built
---

**编译结束**: 2026-08-05 19:27
**最终状态**: built

## Conan 适配 (2026-08-05)

### 变更内容
- 新增 conanfile.py — Go 项目 Conan 配方
- 新增 conandata.yml — 源码 URL + sha256
- 新增 test_package/ — 测试包 (conanfile.py + test.sh + MANIFEST.yml)
- 新增 commands.json — 软件级命令行工具声明 (R38)
- 新增 README.md — 软件级描述
- 更新 manifest.yaml — status 改为 published, 添加 sha256

### Conan 配方要点
- package_type = application (CLI 工具)
- Go SDK 自动检测和下载 (支持 OHOS ELF 签名)
- aliyun-openapi-meta 子模块作为 conandata.yml 中的 meta 源
- CGO_ENABLED=1, 版本注入 via -ldflags -X
- CI 镜像 fallback: conandata.yml 使用单值 url 格式, CI 自动添加镜像
- 测试: aliyun version 输出 3.0.229

### 验证结果
- conan-verify: G1-G4 + L2/L4/L5 全部 PASS
- W3 本地 CI 模拟: setup.sh + build_and_test.sh 全部 PASS
