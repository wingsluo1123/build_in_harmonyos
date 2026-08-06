# incus 7.1.0 适配笔记

## 编译环境
- 构建系统: custom (Go + Make)
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 (OHOS SDK) + Go 1.26.5 (Harmonybrew)
- 状态: built

## 编译步骤

### 1. 环境准备
```bash
# Install Go via Harmonybrew
brew install go
# Install ACL and libcap for CGO builds
brew install acl libcap
# Install binutils for GNU ld (OHOS lld has libxml2 dependency issue)
brew install binutils
```

### 2. 设置环境变量
```bash
export GOTOOLCHAIN=local
export GOOS=linux GOARCH=arm64
export GOPROXY=https://goproxy.cn,direct
export GOPATH=~/go
export CC=clang
export CGO_CFLAGS="-D__MUSL__ -I~/.harmonybrew/include -Wno-macro-redefined"
export CGO_LDFLAGS="-L~/.harmonybrew/lib"
# Use sandbox tmp for Go linker (HMDFS doesn't support mmap)
export TMPDIR=GOTMPDIR=TMP=TEMP=/data/storage/el2/base/files/tmp
```

### 3. 下载依赖
```bash
go mod download
```

### 4. 构建 CGO_ENABLED=0 二进制
```bash
CGO_ENABLED=0 go install -v ./cmd/incus
CGO_ENABLED=0 go install -v -tags netgo ./cmd/incus-migrate
CGO_ENABLED=0 go install -v ./cmd/incus-simplestreams
CGO_ENABLED=0 go install -v ./cmd/incus-user
CGO_ENABLED=0 go install -v -tags agent,netgo ./cmd/incus-agent
```

### 5. 构建 CGO_ENABLED=1 二进制
```bash
GNU_LD=~/.harmonybrew/opt/binutils/bin/ld
SANDBOX_TMP=/data/storage/el2/base/files/tmp

CGO_ENABLED=1 go build -ldflags="-tmpdir $SANDBOX_TMP" -o $SANDBOX_TMP/fuidshift ./cmd/fuidshift
CGO_ENABLED=1 go build -ldflags="-tmpdir $SANDBOX_TMP" -o $SANDBOX_TMP/incus-benchmark ./cmd/incus-benchmark
CGO_ENABLED=1 go build -ldflags="-tmpdir $SANDBOX_TMP" -o $SANDBOX_TMP/lxd-to-incus ./cmd/lxd-to-incus
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义错误 | OHOS SDK 未定义 __MUSL__，导致 sys/socket.h 和 linux/socket.h 都定义 sockaddr_storage | CGO_CFLAGS 添加 -D__MUSL__ |
| 2 | sys/acl.h 未找到 | OHOS SDK 无 ACL 开发文件 | brew install acl，CGO_CFLAGS 添加 -I~/.harmonybrew/include |
| 3 | ACL_UNDEFINED_ID 宏重定义 | sys/acl.h 和 incus_posix_acl_xattr.h 定义不同 | CGO_CFLAGS 添加 -Wno-macro-redefined |
| 4 | Go linker "mapping output file failed" | HMDFS 不支持 mmap 写输出文件 | TMPDIR 设为 /data/storage/el2/base/files/tmp (沙箱路径) |
| 5 | Go linker "mkdir /tmp: read-only" | /tmp 在 OHOS 上只读 | -ldflags="-tmpdir /data/storage/el2/base/files/tmp" |
| 6 | lld 无法加载 libxml2.so.16 | OHOS SDK lld 依赖 libxml2 但不在搜索路径 | 使用 GNU ld: --ld-path=~/.harmonybrew/opt/binutils/bin/ld |
| 7 | autotools config.status 失败 | HMDFS 文件系统限制 | 在沙箱路径构建 + 伪装交叉编译 |
| 8 | incusd/lxc-to-incus 无法构建 | 需要 cowsql, liblxc, libudev，均不可用且 GitHub 不可达 | 待转专家分析 |

## 源码修改

无源码修改，无补丁文件。所有修复通过编译参数和环境变量实现。

## 依赖版本

- Go 1.26.5 (Harmonybrew)
- clang 15.0.4 (OHOS SDK)
- libacl 2.4.0 (Harmonybrew)
- libcap 2.78 (Harmonybrew)
- gettext 1.0 (Harmonybrew)
- binutils 2.47 (Harmonybrew, for GNU ld)

## 验证结果

```bash
$ incus version
Client version: 7.1
Server version: unreachable
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| incus | 31M | 客户端CLI |
| incus-migrate | 22M | 迁移工具 |
| incus-simplestreams | 20M | SimpleStreams工具 |
| incus-user | 21M | 用户代理 |
| incus-agent | 25M | 虚拟机代理 |
| fuidshift | 15M | UID/GID映射工具 |
| incus-benchmark | 31M | 基准测试工具 |
| lxd-to-incus | 29M | LXD迁移工具 |

## 注意事项

- incusd (服务端守护进程) 需要 cowsql + liblxc + libudev，这些依赖在 OHOS 上不可用且 Conan 制品仓无对应包
- lxc-to-incus 需要 liblxc 开发文件，Harmonybrew 的 lxc 包仅含 CLI 二进制
- GitHub 从 OHOS 设备不可达，无法下载 C 依赖源码
- 8/10 用户可见二进制已成功构建（相比之前4个）
---

**编译结束**: 2026-08-06 19:40
**最终状态**: built
