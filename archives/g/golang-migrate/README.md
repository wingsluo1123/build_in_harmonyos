# golang-migrate

Database migrations CLI tool for Go.

## Description

golang-migrate is a database migration tool written in Go. It supports multiple
database drivers (PostgreSQL, MySQL, SQLite, etc.) and source formats (file,
Go bindata, GitHub, AWS S3, etc.). The CLI tool allows you to create, apply, and
roll back database migrations from the command line.

## Version

- **4.19.1**: v4.19.1 (latest from GitHub, Conan recipe)
- **homebrew**: v4.19.1 (legacy non-Conan build)

## Build System

- Go (CGO_ENABLED=0, static build for linux/arm64)

## Build Details

- Build command: `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags="-s -w -X main.Version=v4.19.1" -tags "postgres mysql redshift cassandra spanner cockroachdb yugabytedb clickhouse mongodb sqlserver firebird neo4j pgx pgx5 rqlite file go_bindata github github_ee bitbucket aws_s3 google_cloud_storage godoc_vfs gitlab sqlite" -o migrate ./cmd/migrate`
- Version injection: `-X main.Version=v4.19.1` via ldflags
- Build tags: All upstream DATABASE + SOURCE tags + sqlite (pure-Go)

## Sources

- GitHub: https://github.com/golang-migrate/migrate
