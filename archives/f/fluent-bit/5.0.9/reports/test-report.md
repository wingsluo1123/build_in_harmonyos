# Test Report — fluent-bit 5.0.9

## L1 Official Test (test_package)
- **Method**: test_package builds a tiny C binary that invokes the installed
  `fluent-bit` executable (`--version`, `--help`) to verify the package works.
- **Why not link against the lib**: This is an APPLICATION recipe
  (`cpp_info.libs = []`); the test genuinely depends on the `fluent-bit`
  binary being present, which satisfies the R34 destructive negative test.
- **Result**: 1/1 Test #1: test_fluent_bit ... Passed (0.12 sec)

## L1e Destructive Negative Test (R34)
- **Method**: `bin/` and `include/` directories moved away (sabotage);
  test must then fail, proving it genuinely depends on the package.
- **Result**: PASS — test genuinely depends on fluent-bit

## L2 Smoke Test
- **Command**: `fluent-bit --version`
- **Result**: OK

## L0 / L4 / L5 Gates
- **L0**: pass — all checks passed
- **L4**: pass — patches clean (no dangerous functions)
- **L5**: pass — bin/ has content

## Build Environment
- **Target**: OpenHarmony aarch64 (musl)
- **Build**: cmake, clang 15, conan 2.29.1
- **Configure**: All optional subsystems disabled (TLS/HTTP/AWS/SQLDB/Kafka/
  Lua/WASM etc.) — zero external dependencies, bypassing R36.

