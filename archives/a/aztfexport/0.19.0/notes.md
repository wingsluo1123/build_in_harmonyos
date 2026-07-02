# aztfexport 0.19.0 适配笔记

## 编译环境
- 构建系统: go (Go 1.26.4 linux/arm64)
- 编译日期: 2026-07-02
- 编译器: go toolchain
- 状态: published

## 编译步骤

1. 进入源码目录: `cd /storage/Users/currentUser/tmp/aztfexport-src`
2. 设置 Go 环境变量: `export GOPATH=/storage/Users/currentUser/tmp/gopath GOPROXY=https://goproxy.cn,https://goproxy.io,direct`
3. 交叉编译: `GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -ldflags "-X 'main.version=0.19.0'" -o aztfexport .`
4. 验证: `./aztfexport --version` → `aztfexport version 0.19.0`
5. 测试: `go test ./...` → 7 packages ok, 12 packages no test files

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go build 下载依赖时 i/o timeout | proxy.golang.org 在 OHOS 环境不可达 | 设置 `GOPROXY=https://goproxy.cn,https://goproxy.io,direct` |
| 2 | conan create sha256 校验失败 | 本地 tar.gz (git archive) 与 GitHub release tar.gz 哈希不同 | 使用 Conan 实际下载得到的 sha256: `ccd5550dcf9a860afb6e12381cd351b44b3da58d6a3aaa78370126752ee3e3b4` |

## 依赖版本

Go 依赖通过 go.mod/go.sum 管理，主要依赖：
- github.com/Azure/azure-sdk-for-go/sdk/azcore v1.18.0
- github.com/Azure/azure-sdk-for-go/sdk/azidentity v1.9.0
- github.com/hashicorp/hcl/v2 v2.23.0
- github.com/zclconf/go-cty v1.16.2
- github.com/urfave/cli/v2 v2.27.6
- github.com/magodo/tfadd v0.10.1
- github.com/charmbracelet/bubbletea v0.22.1

## 验证结果

```bash
$ ./aztfexport --version
aztfexport version 0.19.0

$ go test ./...
ok  	github.com/Azure/aztfexport	0.836s
ok  	github.com/Azure/aztfexport/internal/cfgfile	0.447s
ok  	github.com/Azure/aztfexport/internal/meta	0.957s
ok  	github.com/Azure/aztfexport/internal/test/query	0.818s
ok  	github.com/Azure/aztfexport/internal/test/resmap	0.854s
ok  	github.com/Azure/aztfexport/internal/test/resource	0.947s
ok  	github.com/Azure/aztfexport/internal/test/resourcegroup	0.802s
ok  	github.com/Azure/aztfexport/pkg/meta	1.398s
```

## Conan 验证

```
conan-verify aztfexport 0.19.0 → PASS
G0 ✅ (知识图谱预查询)
G1 ✅ (配方完整性)
G2 ✅ (conan create 干净构建)
G3 ✅ (系统同名库隔离)
G4 ✅ (产物完整性)
L2 ✅ (smoke test)
L4 ✅ (静态安全扫描)
L5 ✅ (产物基线)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aztfexport (binary) | ~87MB | Azure 资源导入 Terraform CLI 工具 |

## 注意事项

- 纯二进制工具，无共享库输出，不污染系统 lib 目录
- Go 项目交叉编译使用 GOOS=linux GOARCH=arm64，与 OHOS 兼容
- Conan 配方中 build() 方法需设置 GOPROXY 环境变量，因为 conan create 在干净环境中运行
- conanfile.py 的 settings.os 判断使用 `in ("Linux", "OHOS")` 符合 R32 规范
