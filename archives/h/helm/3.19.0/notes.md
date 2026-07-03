# helm 3.19.0 适配笔记

## 编译环境
- 构建系统: custom (Go build)
- 编译日期: 2026-07-01
- 编译器: clang/clang++ (未使用，CGO_ENABLED=0)
- Go 版本: go1.24.0 linux/arm64
- 状态: built

## 编译步骤

1. 下载源码包: `https://github.com/helm/helm/archive/refs/tags/v3.19.0.tar.gz`
2. 解压到 work 目录: `cp -rL helm-3.19.0.orig helm-3.19.0.work` (HMDFS 不支持硬链接)
3. 设置 Go 环境: Go 1.24.0 (需从 go.dev 下载，go.mod 要求 >= 1.24.0)
4. 为 Go 工具链子工具创建 elfldr wrapper 脚本
5. 编译: `CGO_ENABLED=0 go build -trimpath -ldflags '-w -s' -o bin/helm ./cmd/helm`
6. 安装到 staging: `cp bin/helm $TEST_PREFIX$DEFAULT_PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | OHOS Python (OpenSSL) 缺少 CA 证书 | 设置 SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 2 | copytree 硬链接失败 | HMDFS 不支持 os.link | 手动 `cp -rL` 复制，init-build 检测到 Makefile 存在跳过复制 |
| 3 | copytree 无效符号链接失败 | helm 源码含 broken symlinks | `cp -rL` 跟随符号链接，忽略 broken 的 |
| 4 | Go 1.23.5 版本过低 | go.mod 要求 go >= 1.24.0 | 从 go.dev 下载 Go 1.24.0，安装到 ~/.goenv/versions/1.24.0 |
| 5 | Go 子工具权限拒绝 | compile/link/asm 等是原始 ELF，需 elfldr | 将子工具移到 .real/ 目录，创建 wrapper 脚本 |
| 6 | Conan 不识别 OHOS | 标准 Conan 2.12.0 无 OHOS 枚举 | 升级到 Conan 2.30.0 + 手动在 settings.yml 添加 OHOS |
| 7 | Conan build 路径错误 | basic_layout 在 build-release 子目录运行 | conanfile.py 用 `cd {self.source_folder} &&` 定位源码 |
| 8 | test_package 执行失败 | 静态 Go 二进制需 elfldr 运行 | test_package 使用 elfldr 执行 helm version |

## 源码修改

无源码修改。helm 3.19.0 代码无需任何补丁即可在 OHOS 上编译。

## 依赖版本

- Go: 1.24.0 (linux/arm64, 从 go.dev 下载)
- Conan: 2.30.0 (从社区 PyPI 源安装)
- Python: 3.12.8
- clang: 15.0.4 (未用于编译，CGO_ENABLED=0)

## 验证结果

```bash
$ elfldr bin/helm version
version.BuildInfo{Version:"v3.19", GitCommit:"", GitTreeState:"", GoVersion:"go1.24.0"}

$ elfldr bin/helm help
The Kubernetes package manager
...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/helm | 57,737,400 bytes (55.1 MB) | 静态 ELF 二进制, aarch64 |
| helm-3.19.0-ohos-aarch64.tar.gz | ~14 MB | 打包发布 tar.gz |

## 注意事项

1. helm 是 Go 项目，不是 C/C++ 项目，conanfile.py 不使用 autotools/cmake
2. 二进制需通过 elfldr 运行，直接执行会报 Permission denied
3. Go 1.24.0 工具链子工具需要手动创建 elfldr wrapper 脚本
4. GitCommit 和 GitTreeState 为空，因为从 tarball 编译而非 git clone
---

**编译结束**: 2026-07-03 15:04
**最终状态**: published
