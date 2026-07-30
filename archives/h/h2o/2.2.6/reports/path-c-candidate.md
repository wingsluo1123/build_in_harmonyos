# H2O 2.2.6 Path C Candidate Evidence

## Scope

This is a request to assess H2O 2.2.6 as a Path C candidate. It is not a
claim of an approved Path C score. The normal adaptation and upstream-test
requirements remain mandatory.

## High-difficulty dimensions

1. H2O combines a standalone HTTP/2 server with embeddable libraries,
   libuv/event-loop variants, OpenSSL, zlib, picotls, Brotli, YAML and optional
   MRuby. The package boundary must retain the upstream feature matrix without
   introducing a Linux-only runtime assumption.
2. Its upstream validation is a custom CMake `check` target that builds unit
   binaries and executes the Perl `prove -v t/*.t` integration suite. This
   spans target binaries and host-side test tooling rather than a simple CTest
   list.
3. The OpenHarmony port must keep asynchronous sockets, TLS and HTTP protocol
   behavior aligned while running against the platform toolchain and libc.

## Evidence and boundary

- Release source and SHA-256 are in `conandata.yml`.
- The recipe uses external OpenSSL and Conan-provided libuv/zlib, keeps picotls
  enabled, and invokes the upstream `check` target.
- MRuby is intentionally disabled because the target environment lacks the
  required Ruby/Bison host-tool chain. This is configuration scope, not a
  replacement for the selected upstream test entry.
- The consumer test executes the installed `h2o -v` binary through Conan.

## Requested review

Please determine whether this multi-runtime, multi-toolchain validation path
meets the contest's Path C candidate criteria. The final classification and
score are for the review committee to decide.
