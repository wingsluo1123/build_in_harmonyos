# Wumpus

Wumpus provides Hunt the Wumpus and Superhack, two terminal games.
The Conan package contains the `wumpus` and `superhack` executables with no
external runtime dependencies. The recipe builds the upstream Makefile default
target and copies the executables; the optional manual-page install target
requires Asciidoctor and is not used.

## OpenHarmony adaptation

Two portability patches convert five old-style C function definitions to ISO C
prototypes, preserving upstream `-Werror`. The R14-R6 candidate was built and
tested on native OpenHarmony aarch64 with OHOS Clang on 2026-10-01.
Conan consumer verification and local framework W3 passed. The consumer uses
seed 123, reads the printed room topology, moves to a listed legal neighbor,
and repeats the move to check the resulting state and deterministic output.
There are two gameplay smoke scenarios with 34 assertions per invocation;
this does not establish full interactive game coverage.

The complete framework `finish` command returned 1 because of global knowledge
and submit-readiness checks; see `1.12/notes.md` for the separate results.
Hosted CI, official review, merge, and points are not established by local W3.

## Source

- Upstream: <https://gitlab.com/esr/wumpus>
- Release: <https://gitlab.com/esr/wumpus/-/archive/1.12/wumpus-1.12.tar.gz>
- License: BSD-2-Clause (upstream `COPYING`)
