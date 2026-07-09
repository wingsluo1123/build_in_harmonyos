# sops 3.11.0 适配笔记

## 编译环境
- 构建系统: Go (module: github.com/getsops/sops/v3)
- 编译日期: 2026-07-02
- 编译器: Go 1.24.4 (linux/arm64), CGO_ENABLED=0
- Conan: 2.30.0 (OHOS 适配版)
- Profile: ohos-aarch64 (os=OHOS, arch=armv8, compiler=clang/15)
- 状态: published

## 编译步骤

1. 下载源码包: `https://github.com/getsops/sops/archive/refs/tags/v3.11.0.tar.gz`
2. 解压到工作目录
3. 设置 Go 环境: `CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct GOROOT=~/.goenv/versions/1.24.4`
4. 编译: `go build -trimpath -ldflags '-s -w -X github.com/getsops/sops/v3/version.Version=3.11.0' -o sops ./cmd/sops`
5. 安装: 复制 sops 二进制到 `$TEST_PREFIX$DEFAULT_PREFIX/bin/`
6. 测试: `elfldr sops --version` → `sops 3.11.0`
7. conan-init + conan-verify: 生成 Conan 配方并验证
8. finish: 标记为 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 (CERTIFICATE_VERIFY_FAILED) | OHOS 缺少 CA 证书 | 使用 `curl -kL` 通过 ghfast.top 镜像下载，手动放入 `~/tmp/builds/` |
| 2 | Conan 2.x `self.run()` env 参数类型错误 | Conan 2.x 要求 env 为 list 而非 dict | 将 `env={"K":"V"}` 改为 `env=["K=V"]` |
| 3 | `go build ./cmd/sops` 找不到目录 | Conan basic_layout 下 build_folder ≠ source_folder | 添加 `cwd=self.source_folder` 到 `self.run()` |
| 4 | test_package `deps_cpp_info` AttributeError | Conan 2.x 移除了 `deps_cpp_info` | 改用 `self.dependencies["sops"].package_folder` |
| 5 | OHOS 未签名 ELF 二进制无法直接执行 | OHOS 要求 ELF 签名 | conanfile.py 创建 shell wrapper (bin/sops → elfldr bin/sops.real) |
| 6 | conanrun 环境未将 bin/ 加入 PATH | package_info() 未设置 bindirs | 添加 `self.cpp_info.bindirs = ["bin"]` |

## 源码修改

无。sops 3.11.0 在 OHOS 上无需任何源码补丁，Go 交叉编译天然支持 aarch64。

## 依赖版本

- Go 1.24.4 (go.mod 要求 1.24.0+)
- 无 C/C++ 依赖 (CGO_ENABLED=0)
- Conan 2.30.0 (OHOS 适配版)
- GOPROXY: https://goproxy.cn,direct

## 验证结果

```bash
# 手动测试 (通过 elfldr)
$ elfldr sops --version
sops 3.11.0
(exit code: 0)

# Conan test_package
$ conan create ... (test_package)
sops/3.11.0@ohpcd/stable (test package): RUN: ".../bin/sops" --version
sops 3.11.0
(exit code: 0)

# conan-verify 全门禁通过
G1: PASS, G2: PASS, G3: PASS, G4: PASS, L2: PASS, L4: PASS, L5: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/sops | 55 bytes | Shell wrapper 脚本 (调用 elfldr) |
| bin/sops.real | 43,974,840 bytes | Go 静态二进制 (ELF64 AArch64) |
| packaging/sops-3.11.0-ohos-aarch64.tar.gz | ~42MB | Release 打包产物 |
| conanfile.py | 2,983 bytes | Conan 配方 (Go 构建系统) |
| conandata.yml | 274 bytes | 源码 URL + SHA256 |

## 注意事项

- OHOS 上未签名 ELF 需要 `elfldr` 包装器运行，conanfile.py 已自动处理
- `sops --version` 会尝试连接 GitHub API 检查更新，受限网络下产生警告（不影响功能）
- Go 静态二进制为 EXEC 类型（非 PIE），属 Go 编译器默认行为
- Conan 2.x API 变更较多，注意 env 参数类型和 dependencies 访问方式

---

**编译结束**: 2026-07-02 02:08
**最终状态**: published
