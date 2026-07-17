# gofumpt 0.10.0-r0 适配笔记

## 编译环境
- 构建系统: Go (1.25.0)
- 编译日期: 2026-07-13
- 编译器: Go (CGO_ENABLED=0, 静态编译)
- 状态: built

## 编译步骤

1. 安装 Go 1.25.0 (arm64) 并 ELF 签名所有 Go 工具链二进制
2. 下载源码: https://github.com/mvdan/gofumpt/archive/refs/tags/v0.10.0.tar.gz
3. 编译命令:
```bash
cd $BUILD_SRC_DIR
CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w" -o gofumpt .
```
4. **关键发现**: Go linker 在 HMDFS 上 mmap 失败（permission denied），
   需要在 hmfs 文件系统上编译（/data/storage/el2/base/cache/）
5. Go 输出的 ELF 格式非标准（SHT_STRTAB 未 null-terminated），需要 strip 后再 ELF 签名
6. 安装到 staging: cp gofumpt $TEST_PREFIX/bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 二进制无法执行 | HMDFS 需要 ELF 签名 | 使用 binary-sign-tool 签名 |
| 2 | Go linker mmap 失败 | HMDFS 不支持 mmap(PROT_EXEC) | 在 /data/storage/el2/base/cache/ 上编译 |
| 3 | file 报 "bad shdr" | Go ELF 格式非标准 | strip 后恢复正常 ELF 格式 |

## 依赖版本
- Go 1.25.0 (自安装，已签名)

## 验证结果
```bash
$ gofumpt -version
(devel) (go1.25.0)
$ gofumpt -h
Usage: gofumpt [flags] [path ...]
```

## 交付物
| 文件 | 说明 |
|------|------|
| gofumpt-0.10.0-r0-ohos-aarch64 | 静态编译 ELF arm64 (3.0MB) |

## 注意事项
- 无补丁，Go 项目直接编译
- CGO_ENABLED=0 确保纯静态编译
- gofumpt 是纯 Go CLI 工具，无 configure/make

---

**编译结束**: 2026-07-13 20:56
**最终状态**: built