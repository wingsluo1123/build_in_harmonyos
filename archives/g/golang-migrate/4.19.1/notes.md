# golang-migrate 4.19.1 — 适配笔记

## 编译信息

- **软件**: golang-migrate
- **版本**: 4.19.1 (上游 tag v4.19.1)
- **构建系统**: Go (custom, CGO_ENABLED=0)
- **日期**: 2026-08-06

## 编译过程

### Step 1: init-build
- 下载源码: https://codeload.github.com/golang-migrate/migrate/tar.gz/refs/tags/v4.19.1
- SHA256: 677bf03c19d684dc5bef47e981ec1b4564482cbf5f9b190cb48e110183fd6d25
- 源码路径: ~/tmp/builds/golang-migrate-4.19.1.work

### Step 2: Go 编译
- 构建系统: Go 1.24.0 (自动下载 SDK)
- CGO_ENABLED=0 (匹配上游 Makefile `build` 目标)
- 构建标签: postgres mysql redshift cassandra spanner cockroachdb yugabytedb clickhouse mongodb sqlserver firebird neo4j pgx pgx5 rqlite file go_bindata github github_ee bitbucket aws_s3 google_cloud_storage godoc_vfs gitlab sqlite
- 版本注入: -X main.Version=v4.19.1 (cmd/migrate/version.go 中 var Version = "dev")
- 入口: ./cmd/migrate
- GOPROXY: https://goproxy.cn,direct

### 关键发现

1. **上游 Makefile**: `CGO_ENABLED=0 go build -ldflags='-X main.Version=$(VERSION)' -tags '$(DATABASE) $(SOURCE)' ./cmd/migrate`
2. **DATABASE 标签**: postgres mysql redshift cassandra spanner cockroachdb yugabytedb clickhouse mongodb sqlserver firebird neo4j pgx pgx5 rqlite
3. **SOURCE 标签**: file go_bindata github github_ee bitbucket aws_s3 google_cloud_storage godoc_vfs gitlab
4. **sqlite 标签**: 纯 Go 实现 (modernc.org/sqlite)，无需 CGO
5. **sqlite3/sqlcipher 标签**: 需要 CGO (github.com/mattn/go-sqlite3)，仅在上游测试目标中使用
6. **版本注入**: 变量名为 `Version`（大写 V），ldflags 用 `-X main.Version=v4.19.1`
7. **HMDFS**: Go 链接器在 OHOS 上需要 tmpfs 工作区避免 mmap 失败
8. **ELF 签名**: OHOS 上 Go 产物需要 binary-sign-tool 签名后才能执行

## 铁律遵循

- R10: 使用 $TMPDIR（非 /tmp，只读）
- R26: 不适用（无系统同名库）
- R27: 无 Conan 依赖
- R32: settings.os 判断使用 `in ("Linux", "OHOS")`
- R34: test_package 实质测试 migrate -help 输出
- R38: 声明 commands.json（CLI 工具）

## 历史对比

- **homebrew 版本** (2026-06-03): 使用 CGO_ENABLED=1 + 部分标签 (postgres mysql sqlite sqlite3 file)，状态 built
- **4.19.1 版本** (本次): 使用 CGO_ENABLED=0 + 全部标签 (DATABASE+SOURCE+sqlite)，状态待验证
- 改进: 匹配上游 Makefile 默认构建，包含全部驱动，无需 CGO
---

**编译结束**: 2026-08-06 14:55
**最终状态**: built
