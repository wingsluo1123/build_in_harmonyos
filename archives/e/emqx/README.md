# emqx

## What is it?

EMQX is a distributed MQTT broker for IoT messaging, built on Erlang/OTP.

## OHOS/HarmonyOS Adaptation

- Build type: Erlang/rebar3 Makefile release build.
- Version: upstream EMQX `5.8.8`, following the Homebrew formula build entry point.
- The recipe follows the Homebrew formula by setting `PKG_VSN=5.8.8` and `BUILD_WITHOUT_QUIC=1`, then building `make emqx-rel`.
- This is a high-difficulty package because a fully functional OHOS build depends on the Erlang/OTP 26 runtime/toolchain, release generation via rebar3/relx, and large broker/runtime integration test coverage.

## Version 5.8.8

- Status: pending
- Build date: 2026-07-21
- Source: https://github.com/emqx/emqx/archive/refs/tags/v5.8.8.tar.gz
