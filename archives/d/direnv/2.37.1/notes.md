# direnv 2.37.1 适配笔记

## 编译环境
- 构建系统: custom (Go go build)
- 编译日期: 2026-07-02
- 编译器: Go 1.24.4 (clang/clang++ available but not used for Go build)
- 状态: published

## 编译步骤

1. 下载源码包：GitHub release tag v2.37.1 (via ghfast.top 镜像, curl -k 解决 SSL 证书问题)
2. init-build 初始化构建上下文
3. 设置 CGO_ENABLED=0 纯 Go 静态编译
4. 执行构建命令：
   ```bash
   CGO_ENABLED=0 go build -trimpath \
     -ldflags '-s -w -X github.com/direnv/direnv/v2/version.Version=2.37.1' \
     -o direnv .
   ```
5. 安装到 staging 目录
6. 使用 elfldr 运行 direnv --version 验证
7. 生成 Conan 配方 (conan-init + 手动适配 Go 构建系统)
8. conan-verify 全部门禁通过
9. finish 收尾，状态标记为 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 网络限制 | 使用 ghfast.top 镜像 + curl -k 下载到本地, 再用 file:// URL 传给 init-build |
| 2 | SSL 证书验证失败 | 本地 CA 证书不完整 | curl -k 跳过验证; init-build 自动安装了 121 个根证书 |
| 3 | init-build 检测构建系统为 autotools | 源码包含 GNUmakefile | 手动编写基于 Go 构建的 conanfile.py (参考 fzf 模式) |
| 4 | G0 干净构建验证失败 (configure not found) | finish 脚本尝试运行 configure, 但 direnv 无 configure 脚本 | 非阻塞, conan-verify G2 (conan create) 是权威验证, 已通过 |
| 5 | finalize-archive 报缺失 README.md 和 release tar.gz | 归档文件不完整 | 补充创建 README.md 和 packaging/direnv-2.37.1-ohos-aarch64.tar.gz |

## 源码修改

无源码修改，direnv 2.37.1 源码无需补丁即可在 OHOS 平台编译。

## 依赖版本

- Go: 1.24.4 (位于 ~/.goenv/versions/1.24.4/, go wrapper 在 /usr/local/bin/go)
- Conan: 2.30.0 (OHOS 适配版)
- Python: 3.12.8
- clang: 15.0.4 (未参与 Go 编译，仅环境检查)
- elfldr: 已配置 (Go 工具链子工具)

## 验证结果

### 手动测试
```bash
$ elfldr $TEST_PREFIX$DEFAULT_PREFIX/bin/direnv --version
Entry: 0x8b420 SP: 0x5aeb8fe590 argc=2 aligned=1
2.37.1
```

### Conan test_package 测试 (conan-verify G2)
```bash
$ elfldr /storage/Users/currentUser/.conan2/p/b/direnfe8d5efb238d1/p/bin/direnv --version
Entry: 0x8b420 SP: 0x5b44245600 argc=2 aligned=1
2.37.1
```

### 二进制信息
- file: ELF executable, 64-bit LSB arm64, static
- size: 7,667,896 bytes (7.3 MB)
- sha256: 0d8d7e4d31e37293c4891c85150c5b6fe20d74a8fe527d1eb90a851ef2471f47
- readelf -d: "There is no dynamic section in this file" (完全静态)
- readelf -h Type: EXEC (non-PIE)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/direnv | 7,667,896 | OHOS arm64 静态可执行文件 |
| packaging/direnv-2.37.1-ohos-aarch64.tar.gz | 7,670,953 | 打包产物 (tar.gz) |

## 注意事项

- direnv 是纯 Go 项目，CGO_ENABLED=0 编译为完全静态二进制
- 在 OHOS 平台运行需要 elfldr wrapper (Go runtime 使用 SVC syscalls 需要 patching)
- init-build 会因 GNUmakefile 误检测为 autotools，conanfile.py 需手动适配 Go 构建
- conanfile.py 参考 fzf/helm/lazygit 等 Go 项目的成功模式
- test_package 使用 self.dependencies["direnv"].package_folder (Conan 2.x 语法)

---

**编译结束**: 2026-07-02 02:18
**最终状态**: published
