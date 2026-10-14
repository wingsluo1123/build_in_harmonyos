# Wumpus 1.12 adaptation notes

## Source and build

The pinned upstream tag 1.12 archive is 26,932 bytes, SHA-256
`af4111eff06195e5da7f89d8a413ae9ef4a018736266bf31761325cf65c962e8`.
Its default Makefile target builds wumpus and superhack without external
libraries. There is no check/test target or registered upstream test suite.
The optional install target generates manual pages using Asciidoctor; the
Conan recipe instead copies the two built executables and COPYING.

OHOS Clang rejected five old-style C definitions under upstream `-Werror`.
`0001-superhack.c.patch` converts getlet and move_hazard; `0002-wumpus.c.patch`
converts getnum, getlet, and main to ISO C prototypes. Both patches were
generated using the official refresh-patch --auto helper. They preserve
`-Werror` and introduce no platform-only guards or external dependencies.

## Conversation R14-R6: target validation, 2026-10-01

Earlier host-derived fixed room input failed on OHOS: seed 123 starts both
games in room 16 with exits 15, 17, and 20. The final consumer reads each
program's printed topology, checks attempted legal exits, proves a move to
one listed neighbor, and repeats it to check state and deterministic output.
The tests include title, stderr, EOF exit status, and invalid-move assertions.
They are two added gameplay smoke scenarios, 34 assertions per invocation;
repeated verification is not counted as additional scenarios.

R14-R6 ran once on native OpenHarmony aarch64 (OHOS Clang target
`aarch64-unknown-linux-ohos`, Conan 2.29.1). Actual framework baseline was
`d458d5ed4e4861a30b8d5c244b4f44dc603c1021`; reviewed official main was
`255e5069639b3be244f4988c966a5120bd5608f2`; the target candidate commit was
`843651cb7e3e5d76e92c2fd688ad22e632db2e01` with 11 candidate files.
`init-build` returned 0. Finish's Conan consumer and W3 L1 consumer each
passed 34 assertions, retaining separate sets of 24 raw stream/exit files.
Actual W3 exit_code was 0 with incremental scope of 11 files, JC_ERRORS=0,
L1 pass, L2 skip, L4 warn, and L5 pass. The R6 per-invocation evidence
directory fix avoided the prior collision. No upstream tests exist; their
pass rate is not applicable. Added consumer scenarios passed 2/2.

Complete `finish wumpus 1.12 built` and runner returned 1. Captured framework
code shows G0's unconditional unsupported `./configure` attempt is a warning,
and the `gen_summary` str.append exception is nonfatal. Actual failed steps
were global knowledge completeness (step5b: E219/E253/E305 fields) and submit
readiness (step8: report, packaging, staging). Wumpus's own knowledge check
passed. Current R19/R20 deprecate manual packaging/staging markers; no fake
marker, manual package, or framework change is included. The exact offending
global knowledge contents and summary trigger file were not established.
The full finish failure remains disclosed. Local test reports and raw logs
are retained as supporting evidence and excluded from the formal PR under
the current review-memory file policy.

Independent R6 W4 passed with P0=0/P1=0/P2=1. The P2 observation concerned
host fixture raw-log retention; real target raw streams are now retained.
Publication changes only README, notes and truthful manifest metadata; recipe,
source patches, commands and consumer bytes remain identical to R6.

Receipt SHA-256: `5e951691fab606ef12ff981514c27899ae233ace8b16fbf38268b582e62302dd`.
Raw archive: `e376318fdd49262c41010d4b3c8251d7d015a550bad6a45bad8d50239453ab39`.
Conan package archive: `c489c5e95e3fc76c43dfd90e7d5f4d4da6fa20127a8440e62bc11407f9c675c7`.
Wumpus ELF: `085d3459c60cfd5dd9b11667ed56e2a71cc1bca87d9579b98cca1c7518107644`.
Superhack ELF: `4e22cfed8e4c3d8a7b1e072cb688cb01c6a6741a3156d05fe964bb8fe7bc5231`.

The original PF9 check conflicts with the required software-level README and
commands.json paths. The specific internal decision permits the documented
create-pr --no-preflight option after separately running the entire original
preflight and checking branch/layout/commands. It skips the whole automatic
preflight, not just PF9; it is not an official waiver. Hosted CI, official
review, merge and points remain separate and unestablished by these results.
