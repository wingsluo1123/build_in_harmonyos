# checkmake 0.3.2 适配笔记

## 编译环境
- 构建系统: makefile (Go/Make)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (Go: go1.26.4 linux/arm64)
- 状态: built

## 编译步骤

checkmake 是一个用 Go 编写的 Makefile linter/分析器。构建系统为 Make + Go。

1. 设置环境变量：
```bash
export PATH="/storage/Users/currentUser/.harmonybrew/bin:$PATH"
export GOPROXY=https://goproxy.cn,direct
export BUILDER_NAME="OpenDesk"
export BUILDER_EMAIL="opendesk@ohos.dev"
export TMPDIR="/storage/Users/currentUser/tmp"
export GOFLAGS="-mod=mod"
```

2. 只编译二进制（跳过 lint 和 man page 生成）：
```bash
make binaries VERSION=0.3.2 BUILDER_NAME="OpenDesk" BUILDER_EMAIL="opendesk@ohos.dev"
```

3. 安装到 staging 目录：
```bash
mkdir -p $TEST_PREFIX/bin
cp checkmake $TEST_PREFIX/bin/
```

4. 运行测试：
```bash
go test ./...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go: Permission denied` | `/storage/Users/currentUser/usr/local/bin/go` 权限不足 | 使用 harmonybrew 的 go: `/storage/Users/currentUser/.harmonybrew/bin/go` |
| 2 | Go 模块下载失败 (`proxy.golang.org` EOF) | 网络无法访问 proxy.golang.org | 设置 `GOPROXY=https://goproxy.cn,direct` 使用国内镜像 |
| 3 | pandoc 缺失导致 `make all` 失败 | pandoc 仅用于生成 man page，不影响二进制 | 使用 `make binaries` 只编译二进制，跳过 man page |
| 4 | golangci-lint 需要网络下载 | `make all` 依赖 lint 目标 | 使用 `make binaries` 跳过 lint |

## 源码修改

无源码修改。所有编译通过环境变量和 make target 选择完成。

## 依赖版本

- Go: go1.26.4 linux/arm64 (harmonybrew)
- clang: clang version 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
$ ./checkmake --version
checkmake 0.3.2 built at 2026-07-02T12:28:31Z by OpenDesk <opendesk@ohos.dev> with go version go1.26.4 linux/arm64

$ go test ./...
ok  	github.com/checkmake/checkmake/cmd/checkmake	0.213s
ok  	github.com/checkmake/checkmake/config	0.145s
ok  	github.com/checkmake/checkmake/formatters	0.151s
?   	github.com/checkmake/checkmake/logger	[no test files]
ok  	github.com/checkmake/checkmake/parser	0.157s
?   	github.com/checkmake/checkmake/rules	[no test files]
ok  	github.com/checkmake/checkmake/rules/maxbodylength	0.129s
ok  	github.com/checkmake/checkmake/rules/minphony	0.152s
ok  	github.com/checkmake/checkmake/rules/phonydeclared	0.128s
ok  	github.com/checkmake/checkmake/rules/timestampexpanded	0.146s
ok  	github.com/checkmake/checkmake/rules/uniquetargets	0.127s
ok  	github.com/checkmake/checkmake/validator	0.133s

$ ./checkmake list-rules
       NAME                    DESCRIPTION            
 maxbodylength      Target bodies should be kept      
                    simple and short (no more than 8  
                    lines).                           
 minphony           Minimum required phony targets    
                    must be present (all,clean,test). 
 phonydeclared      Every target without a body needs 
                    to be marked PHONY                
 timestampexpanded  timestamp variables should be     
                    simply expanded                  
 uniquetargets      Targets should be uniquely        
                    defined; duplicates can cause     
                    recipe overrides or unintended    
                    merges.
```

## 注意事项

1. **pandoc 绕过**: pandoc 仅用于生成 man page (`.1` 文件)，不影响二进制编译。使用 `make binaries` 只编译二进制。
2. **GOPROXY 配置**: 必须设置 `GOPROXY=https://goproxy.cn,direct` 才能下载 Go 模块依赖。
3. **Go 路径**: 使用 harmonybrew 的 go (`/storage/Users/currentUser/.harmonybrew/bin/go`)，因为 `/storage/Users/currentUser/usr/local/bin/go` 存在权限问题。
4. **静态二进制**: Go 编译产生静态链接的 ELF 二进制，无需额外配置 RPATH 或共享库。
5. **LDFLAGS**: 版本信息通过 `-ldflags` 注入：version, buildTime, builder, goversion。
---

**编译结束**: 2026-07-02 20:48
**最终状态**: built
