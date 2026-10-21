# Conan-only finish readiness compatibility

2026-10-14. The actual native Conan recipe passed shared/static full upstream
37/37 and installed consumers1/1, with signed package artifacts and complete
released evidence. This does not constitute a finish PASS.

A read-only invocation of current-main FinishPipeline.step8_submit_readiness
against the actual archive reported:

    test-report.md: PASS
    packaging/: FAIL — requires legacy directory and packaging
    .staging-verified: FAIL — requests an empty marker
    build-closed marker: PASS (truthful notes record compilation complete)
    READINESS_PASS False

This was only the real readiness method, not a complete finish run. The
current-main Conan verifier uses the Conan cache and does not produce the
legacy directory/marker; close_archive also does not produce them. Finalize
checks old *-ohos-aarch64.tar.gz deliverables for built/published status.

Do not create dummy packaging files or declare finish PASS to satisfy these
existence checks. A Conan-only path should instead verify actual producer
outputs, package identities, artifact integrity and real logged build/consumer
success while retaining legacy validation for genuinely legacy archives.

The user subsequently authorized Conan-only compatibility repair and then
the two remaining W5 multiline-parser and W2 generated-summary isolation fixes.
All framework changes stay in an independent worktree/branch, not this recipe
PR; the installed global skill is not replaced. Offline directed tests29/29
passed, including genuinely empty/TODO multiline fields and root SUMMARY
modification rejection. These fixture checks are not native-build evidence.

Native finish r5 then completed with actual RC0, actual Conan verification and
local CI each37/37+consumer1/1, and all12 released transaction receipts. The
actual producer CI result and log were collected unchanged, independently
hash-checked, then copied as raw bytes for submission. No legacy markers were
invented. Earlier failed runs retain their original failures.

Recommendations: use current Conan artifacts/input hashes instead of legacy
packaging existence checks; resolve exact Conan2 RREV/PID/PREV; keep native
profiles separate from worker hardcoded paths; share graph's continuation-aware
KV parser; scope finish-generated summary to an archive report so W2 still
rejects genuine framework modifications. Use task-private lifecycle outputs.
The earlier r2/r3 unintended default shared lifecycle output remains disclosed
in the task checkpoint; it was not deleted because prior contents are unknown.
