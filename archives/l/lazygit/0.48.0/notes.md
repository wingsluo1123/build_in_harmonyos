# lazygit 0.48.0 适配笔记

## 编译环境
- 构建系统: custom (Go — go build)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (OHOS 平台)
- Go 版本: go1.24.4 linux/arm64
- 状态: published

## 编译步骤

1. **初始化**: `ohc-run.py init-build lazygit 0.48.0 --url=https://github.com/jesseduffield/lazygit/archive/refs/tags/v0.48.0.tar.gz`
   - 下载源码包 (4.8MB tar.gz)
   - 解压到 work 目录，创建归档骨架
   - 生成 `.build-context-lazygit-0.48.0`

2. **编译**: 在源码目录执行 Go 编译
   ```bash
   source .build-context-lazygit-0.48.0
   cd $BUILD_SRC_DIR
   export CGO_ENABLED=1
   export GOFLAGS=-mod=vendor
   go build -trimpath -ldflags '-s -w -X main.commit=v0.48.0 -X main.version=0.48.0 -X main.date=2025-01-01' -o lazygit .
   ```
   - 编译成功，无错误
   - 产物: lazygit (19,333,304 bytes, ELF64 AArch64 静态二进制)

3. **安装到 staging**:
   ```bash
   mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
   cp lazygit $TEST_PREFIX$DEFAULT_PREFIX/bin/
   ```

4. **生成 Conan 配方**: `ohc-run.py conan-init lazygit 0.48.0`
   - 自动生成的模板基于 autotools，需手动适配为 Go 构建系统
   - 参考 fzf 项目的 conanfile.py 模式重写

5. **验证 Conan 配方**: `ohc-run.py conan-verify lazygit 0.48.0`
   - G1-G4, L2, L4, L5 全部通过
   - conan create 成功，test_package 通过 elfldr 运行 --version

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载失败: SSL_CERTIFICATE_VERIFY_FAILED | OHOS 平台缺少 CA 证书 | 设置 `SSL_CERT_FILE` 指向 certifi 的 cacert.pem |
| 2 | conanfile.py 模板为 autotools | ohc-run.py conan-init 默认按 BUILD_SYSTEM=autotools 生成模板 | 参考 fzf (同为 Go 项目) 的 conanfile.py，重写为 Go 构建系统适配版 |
| 3 | conandata.yml SHA256 为占位符 | 自动生成时未计算 SHA256 | 手动执行 `sha256sum` 计算并填入 |
| 4 | test_package/ 使用 CMake 模板 | conan-init 默认生成 CMake test_package 模板 | 重写为使用 elfldr 运行 `lazygit --version` 的测试模式 |

## 源码修改

无。lazygit 源码未做任何修改，使用 vendor 目录中的依赖直接编译。

## 依赖版本

- Go: go1.24.4 linux/arm64 (位于 /storage/Users/currentUser/usr/local/bin/go)
- CGO 编译器: clang 15.0.4 (OHOS 平台)
- 无外部 C/C++ 库依赖 (Go 静态二进制)

## 验证结果

### 源码目录二进制
```bash
$ elfldr lazygit --version
Entry: 0x905d0 SP: 0x5bc35c6610 argc=2 aligned=1
commit=v0.48.0, build date=2025-01-01, build source=unknown, version=0.48.0, os=linux, arch=arm64, git version=2.45.2
exit code: 0
```

### Conan 缓存二进制 (conan create 产物)
```bash
$ elfldr /storage/Users/currentUser/.conan2/p/b/lazyga240cb331a5d8/p/bin/lazygit --version
Entry: 0x905d0 SP: 0x5a4710a610 argc=2 aligned=1
commit=v0.48.0, build date=2025-01-01, build source=unknown, version=0.48.0, os=linux, arch=arm64, git version=2.45.2
exit code: 0
```

### Staging 二进制
```bash
$ elfldr $TEST_PREFIX$DEFAULT_PREFIX/bin/lazygit --version
Entry: 0x905d0 SP: 0x5a83a05610 argc=2 aligned=1
commit=v0.48.0, build date=2025-01-01, build source=unknown, version=0.48.0, os=linux, arch=arm64, git version=2.45.2
exit code: 0
```

### ELF 信息
```
ELF64, AArch64, EXEC (Executable file), static (no dynamic section)
Entry point: 0x905d0
SHA256: a72848776d8435d8b76176a0a890d48e7f7a785a4f6424ffeee7270f753cfcd2
Size: 19,333,304 bytes
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lazygit (二进制) | 19,333,304 bytes | ELF64 AArch64 静态可执行文件 |
| lazygit-0.48.0-ohos-aarch64.tar.gz | ~19.3MB | Release 制品包 (bin/lazygit) |

## 注意事项

- lazygit 是 Go 项目，需要 Go 工具链 (go 1.22+)
- 需要 CGO_ENABLED=1 (tcell 终端 UI 库依赖)
- 使用 vendor 模式 (-mod=vendor) 避免网络下载依赖
- 在 OHOS 上通过 elfldr 运行，不需要 ELF 签名 (elfldr 兼容)
