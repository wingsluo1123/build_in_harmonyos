# test-report — gofumpt/0.10.0-r0

## 测试摘要

| 项目 | 结果 |
|------|------|
| Go 编译 | ✅ 通过 |
| ELF 签名 | ✅ 通过 |
| gofumpt -version | ✅ 通过 (devel, go1.25.0) |
| gofumpt --help | ✅ 通过 |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS |
| G3 系统同名库隔离 | ✅ PASS (application, no libs) |
| G4 产物完整性 | ✅ PASS |
| L4 安全扫描 (checksec) | ✅ PASS |

## 产物

- Binary: gofumpt (静态 ELF arm64, ~3.0MB, stripped, signed)
- 路径: bin/gofumpt

## 测试结果

smoke test: gofumpt -version → (devel) (go1.25.0)
smoke test: gofumpt -h → Usage: gofumpt [flags] [path ...]
