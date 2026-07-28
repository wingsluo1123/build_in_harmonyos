# EMQX 5.8.8 adaptation notes

## Build scope

- Recipe directory: `5.8.8`, matching the upstream package version
- Build entry point: Homebrew formula `make emqx-rel` flow
- Upstream version: `5.8.8`
- Source URL: `https://github.com/emqx/emqx/archive/refs/tags/v5.8.8.tar.gz`
- SHA256: `5861d8d32c4934175ca3d01c691ea679ac1a7903a1faee72027f6484d3085c89`

The recipe follows the Homebrew formula build path:

```bash
CMAKE_POLICY_VERSION_MINIMUM=3.5 PKG_VSN=5.8.8 BUILD_WITHOUT_QUIC=1 SYSTEM=Linux PROFILE=emqx make emqx-rel
```

`SYSTEM=Linux` is set explicitly for the upstream distro detection script. The
OHOS CI shell enables unset-variable checks, and `scripts/get-distro.sh` reads
`SYSTEM` before assigning a default; using the Linux/Unix release path avoids
that early script abort while keeping the Homebrew-compatible build flow.

## High-difficulty reasons

EMQX is a BEAM/Erlang broker release rather than a small native library. The
build depends on Erlang/OTP 26, rebar3/relx release assembly, generated boot
scripts, and a large transitive Erlang application graph. Full validation also
needs MQTT broker startup, node data/log directories, and network/service
semantics that are expensive to reproduce in a cross-build CI job.

QUIC is disabled in the first OHOS pass with `BUILD_WITHOUT_QUIC=1`, matching
Homebrew, because the QUIC path pulls native `quicer` and TLS/transport
dependencies that should be handled as a follow-up after the base broker
release can be produced.

## Test scope

Source package test inventory counted from the official tarball:

- 396 Common Test suite files under `*/test/*_SUITE.erl`
- 52 EUnit-style `*_test.erl` or `*_tests.erl` files under `*/test/`
- 14 PropEr property files under `*/test/props/`
- 16 MQTT-SN integration helper/test files under `*/test/intergration_test/`

The Conan `test_package` validates that the installed release contains the
expected `bin/emqx`, `releases/5.8.8`, `etc`, and `lib` layout. When the target
binary can run locally, it also runs `emqx help` as a command smoke test.

## Local validation

The official source tarball hash was verified locally. The workstation used for
this PR does not have an OHOS Conan environment or Erlang/OTP 26 release toolchain,
so full `conan create emqx/5.8.8` is pending remote OHOS CI.
