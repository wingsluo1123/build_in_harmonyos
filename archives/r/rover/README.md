# Rover

## Description

Apollo Rover is a CLI tool for working with the Apollo GraphQL Registry. It provides commands for managing federated graphs, introspecting schemas, publishing subgraphs, and more.

- **Homepage**: https://github.com/apollographql/rover
- **Language**: Rust
- **License**: MIT
- **Build System**: Cargo

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 0.40.0 | published | 2026-07-03 |

## Build Notes

- aws-lc-sys (AWS-LC crypto) cannot build on OHOS due to assembly generation failures
- Solution: switched to ring crypto provider via reqwest "rustls-no-provider" feature
- Requires Rust 1.85+ (edition 2024)
