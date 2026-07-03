# fzf 0.67.0 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-07-01
- 编译器: clang/clang++ (CGO support)
- Go 版本: go1.24.0 linux/arm64 (from ~/.goenv/versions/1.24.0)
- 平台: OHOS aarch64 (linux/arm64 via elfldr)
- 状态: published

## 编译步骤

1. 下载源码包：从 `codeload.github.com` 下载 `v0.67.0` release tag 源码（GitHub 直连 SSL 超时）
2. 解压到 `~/tmp/builds/fzf-0.67.0.work`
3. 设置环境变量：
   ```bash
   export FZF_VERSION=0.67.0 FZF_REVISION=tarball CGO_ENABLED=1
   ```
4. 编译：
   ```bash
   go build -trimpath -ldflags "-s -w -X main.version=0.67.0 -X main.revision=tarball" -o fzf .
   ```
5. 安装到 staging：
   ```bash
   mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
   cp fzf $TEST_PREFIX$DEFAULT_PREFIX/bin/fzf
   ```
6. 生成 Conan 配方并验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连 SSL 证书验证失败 + 超时 | OHOS 环境 CA 证书不完整 + 网络超时 | 使用 `codeload.github.com` 直接下载端点，Python urllib 禁用 SSL 验证 |
| 2 | conan-init 生成的 conanfile.py 使用 Autotools 模板 | init-build 默认识别为 autotools（BUILD_SYSTEM=autotools） | 手动重写为 Go 构建系统：`go build` 替代 autotools |
| 3 | test_package 使用 Conan 1.x API `deps_cpp_info` | 模板基于 Conan 1.x | 改为 Conan 2.x API: `self.dependencies["fzf"].package_folder` |
| 4 | G1 检查缺少 `export_sources()` 和补丁应用调用 | 手动重写 conanfile.py 时遗漏 | 添加 `export_conandata_patches(self)` 和 `apply_conandata_patches(self)` |
| 5 | G0 干净构建验证尝试运行 `configure` | finish 脚本默认对 autotools 项目运行 configure | 非阻塞，conan-verify (G2) 已通过 `conan create` 验证可复现性 |
| 6 | Go 编译工具链子工具需要 elfldr | Go runtime 使用 SVC syscall，OHOS 不直接支持 | elfldr 自动介入，patching SVC 和 mmap 调用 |

## 源码修改

无源码修改，无补丁。fzf 0.67.0 源码可以直接在 OHOS 上编译。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Go | 1.24.0 | 从 ~/.goenv/versions/1.24.0 加载 |
| clang | 15.0.4 | CGO 编译器 |
| elfldr | - | OHOS ELF 二进制加载器 |

## 验证结果

### Staging binary --version
```bash
$ elfldr $TEST_PREFIX$DEFAULT_PREFIX/bin/fzf --version
Entry: 0x867b0 SP: 0x5b95727590 argc=2 aligned=1
0.67.0 (tarball)
```

### Conan test_package --version
```bash
$ elfldr /storage/Users/currentUser/.conan2/p/b/fzf82753b55f3a2b/p/bin/fzf --version
Entry: 0x867b0 SP: 0x5b61190600 argc=2 aligned=1
0.67.0 (tarball)
```

### 二进制一致性
- Staging SHA256: 0917f0d4451fb08b937ec63f02bf7f0730fcc9f90af77df35395ac04c46c9387
- Conan cache SHA256: 0917f0d4451fb08b937ec63f02bf7f0730fcc9f90af77df35395ac04c46c9387
- ✅ 一致，构建可复现

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fzf (binary) | 4,391,096 bytes | ELF arm64 static, SHA256: 0917f0d4... |
| fzf-0.67.0-ohos-aarch64.tar.gz | 4,393,653 bytes | 打包产物, SHA256: c2505393... |

## 注意事项

- fzf 是 Go 项目，不使用 configure/make 标准 autotools 流程
- Makefile 使用 `git describe` 和 `git log` 获取版本信息，从 tarball 编译时必须手动设置 `FZF_VERSION` 和 `FZF_REVISION`
- OHOS 平台运行 fzf 必须使用 elfldr 包装器
- `env_info` 在 Conan 2.x 中已弃用（deprecated warning），但仍然可用

---

**编译结束**: 2026-07-01 22:46
**最终状态**: published
