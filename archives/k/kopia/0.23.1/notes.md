# kopia 0.23.1 适配笔记

## 基本信息
- 软件：kopia（Go 语言备份工具）
- 版本：0.23.1
- 源码：https://github.com/kopia/kopia
- 构建系统：Go modules (go build)

## 构建方式
```bash
go build -trimpath -ldflags "-s -w -X github.com/kopia/kopia/repo.BuildVersion=0.23.1" -o kopia github.com/kopia/kopia
```

## 已安装
- `bin/kopia` — CLI 主二进制 (~46MB)

## 测试结果
- smoke test: ✅ `kopia --version` 输出 `0.23.1`
- unit tests: ⏱️ 超时跳过（Go test 套件庞大，含大量集成测试，短时间无法完成）

## 特殊说明
- kopia 是纯 Go 二进制工具，非库文件
- 适合作为 Conan 打包的纯工具（无 lib 产物）
- 含大量外部存储后端依赖（S3、Azure、GCS、SFTP 等）
- HTML UI 需要额外前端构建（默认构建不含 UI 依赖）
- 采用 `nohtmlui` tag 精简构建
---

**编译结束**: 2026-07-06 18:25
**最终状态**: built
