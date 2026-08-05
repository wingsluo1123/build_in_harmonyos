# aliyun-cli

Alibaba Cloud CLI — universal command-line tool for Alibaba Cloud services.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 3.0.229 | built | 2026-08-05 |

## Build System

Go (custom). Uses `go build` with version injection via `-ldflags`.

## OHOS Adaptation

- **Go version**: 1.24.0+ (tested with go1.24.0)
- **CGO_ENABLED**: 0 (pure static)
- **Submodule**: aliyun-openapi-meta downloaded separately (not in GitHub tarball)
- **Linker output**: Must be on ext2 partition (HMDFS mmap issue)
- **ELF signing**: Required after build for HarmonyOS execution
