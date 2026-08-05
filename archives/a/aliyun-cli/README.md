# aliyun-cli

Alibaba Cloud Command Line Interface — a Go-based CLI tool for managing Alibaba Cloud services.

## Versions

| Version | Upstream | Status |
|---------|----------|--------|
| homebrew | v3.0.229 | published |

## Build System

- **Language**: Go (module: github.com/aliyun/aliyun-cli)
- **Build**: `go build -ldflags "-s -w -X 'github.com/aliyun/aliyun-cli/cli.Version=3.0.229'" -o out/aliyun main/main.go`
- **Dependencies**: aliyun-openapi-meta submodule, Go SDK >= 1.18

## Homepage

https://github.com/aliyun/aliyun-cli
