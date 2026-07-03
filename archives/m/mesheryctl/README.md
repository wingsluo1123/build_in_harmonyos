# mesheryctl

Meshery CLI tool — command-line interface for [Meshery](https://meshery.io), the cloud native management plane.

## Overview

mesheryctl is the command-line interface for Meshery, enabling users to:
- Design and operate cloud native infrastructure
- Manage cloud native designs, components, and connections
- Run performance tests
- Configure, deploy, and operate Meshery deployments
- Manage models, relationships, and workspaces

## Build System

- **Language**: Go
- **Build tool**: `go build` (Makefile wrapper)
- **Source**: https://github.com/meshery/meshery (mesheryctl/ subdirectory)
- **License**: Apache-2.0

## Versions

| Version | Status | Date |
|---------|--------|------|
| latest (v1.0.52) | published | 2026-07-03 |

## Key Notes

- mesheryctl is part of the meshery/meshery monorepo; it does not have its own go.mod
- The build requires both `mesheryctl/` and `server/` directories from the monorepo
- Go module proxy must be set to `https://goproxy.cn,direct` (proxy.golang.org unreachable in OHOS)
- Binary is a static ELF (CGO_ENABLED=0), ~108MB, stripped
