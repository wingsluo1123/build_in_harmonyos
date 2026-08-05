# csvq 1.18.1 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-06-12 (原构建), 2026-08-06 (Conan 配方)
- 编译器: go1.26.5 linux/arm64 (Harmonybrew)
- 状态: built

## 编译步骤
```bash
# 1. 下载源码
wget https://github.com/mithrandie/csvq/archive/refs/tags/v1.18.1.tar.gz
tar -xzf v1.18.1.tar.gz
cd csvq-1.18.1

# 2. Go 编译 (CGO_ENABLED=0 静态编译)
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  go build -tags urfave_cli_no_docs -trimpath \
  -ldflags="-X github.com/mithrandie/csvq/lib/query.Version=v1.18.1 -s -w" \
  -o csvq .
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 链接器权限错误 | HMDFS 文件系统限制 | 首次编译成功（缓存复用），与 kustomize 等其他 Go 项目相同 |
| 2 | goenv 安装的 Go 无法执行 | E128: Go 二进制需要 ELF 签名，binary-sign-tool 签名 Go 失败 | 使用 Harmonybrew 安装预签名 Go 1.26.5 |

## 依赖版本
- Go 1.26.5 (via Harmonybrew)

## 验证结果
- csvq --version = "csvq version 1.18.1" ✅
- csvq --help ✅（显示 SQL-like query language for csv）
- SELECT * FROM people ✅（返回4行正确结果）
- SELECT * FROM people WHERE age > 28 ✅（返回2行正确结果）
- SELECT COUNT(*), AVG(age) FROM people ✅（cnt=4, avg_age=29.5）

## Conan 配方
- package_type: application (命令行工具)
- 无 conan 依赖 (Go 不是 conan 包)
- build() 方法直接调用 go build
- test_package/ 使用 test.sh 脚本测试 csvq 二进制功能
- commands.json 声明命令行工具 (R38)

## 注意事项
- 无正式测试套件（Go 项目无 make check）
- Go 编译器需要通过 Harmonybrew 安装，goenv 安装的 Go 无法在 OHOS 上执行 (E128)
- Conan CI 环境需要预装 Go 编译器
---

**编译结束**: 2026-08-06 05:27
**最终状态**: built

## 编译结束
status: closed
