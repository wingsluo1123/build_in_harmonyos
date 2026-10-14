# Path B evidence — dill 0.4.1

## Actual controlled failure and diagnosis

This is a controlled reproduction, not a historical PR CI failure. In the official unmodified 0.4.1 sdist, `python3 -s -m dill.tests` with no installed dill/PYTHONPATH finds the parent runner in CWD, but all 30 script-mode children fail importing dill. Same source plus inherited source PYTHONPATH passes 30/30. The upstream documentation explicitly expects installation before tests; this is a package/environment integration failure, not a claimed upstream source bug.

The recipe privately builds the distribution with the published setuptools tool, then verifies staged module origin and executes the same 30 children from an independent verification directory. The installed consumer validates package origin and a fresh-interpreter serialization roundtrip. Payload removal gives consumer exit 1; restoration and relocation each pass 14 unittest cases. Relocated undill also succeeds with PYTHONPATH removed because the launcher resolves its own package.

## Reuse and deduplication

Main baseline: `f6a25613daaf1aec7170321c249d6ccf3f329593`. Search graph/doc/operations/drafts for PYTHONPATH, script-mode child, sys.path[0], python -m, installed origin, subprocess. Closest entries: E319, E512, DRAFT-pyjson5-0.15.0-unittest-pythonpath-recovery, DRAFT-pytest-9.1.1-negative-test-false-pass, DRAFT-pytest-rootdir-shadows-installed-package, and environment-overriding child-test drafts.

Path recovery, origin assertions and negative controls are already known and are not claimed as independent inventions. Candidate increment: a same-CWD startup-mode mismatch (parent -m versus child script sys.path[0]) with controlled evidence, plus installed execution accounting for a package-embedded standalone runner. It is related to prior drafts and may merit supplementing an existing entry instead of a separate entry; official review decides. The draft does not claim qualification, admission or awarded points. Formal draft-review suggests create, highest similarity E512=0.28, E319=0.19, E339=0.18; the scoring tool only compares formal entries, so the manually found close drafts are separately disclosed.

CLI launchers, writable TMPDIR, absolute command lookup for OHOS posix_spawn and Conan `core.download:parallel=0` reuse existing knowledge. Not separately scored.

## Scope limits

Thirty is the upstream runner's count of distinct script processes. NumPy/SymPy are absent and five original conditional branches are not exercised. graph/profile rendering requires optional objgraph/gprof2dot/Graphviz and is not validated. Default serialization, undill, helper help and installed metadata are the delivered scope. Python >=3.9 is upstream's floor, but this task validates CPython 3.12.9 only. No upstream test/source modified.

## Evidence hashes

Raw logs and generated receipts are retained outside committed files under the task evidence directory. The W3 receipt is original tool output and its log_sha256 matches the raw log bytes.

| File | SHA256 |
| --- | --- |
| baseline.log | `cceeb182b10188e028576eaea574c3a2817a2e8c3a98333e1e32f8c33e15eb4c` |
| baseline-with-path.log | `1af9dedb5acdc9f32a60c80c42d0270ee353f2724b225d74a82d4dc17ae9ec82` |
| consumer-red.log | `130de16bacee1f0843f2aa331c01de3b0eb81cb629e6002aec046a7467dfeb4a` |
| create-v3.log | `0fac68f1a4639b88a75f2f31ae640cf6b5f7ec1d091ff5950d9bba01abd96395` |
| consumer-green.log | `d6de133d4d18af6d258ed53915566ed6f17eb74de3f48d5ee6d94aa38a4663c6` |
| w3-local-ci.log | `3a116567bc09eb57566c1c17a8d5c8951dd5b238ad700587f9d1323f691ca6b6` |
| negative.log | `816cf5aef674ae6fa00cae4daccd484a6ee8cff9dd8c08b4aa92bbbc2d8c57aa` |
| restored.log | `4a9810f42e1ce0e2721b6201ec17bd09d8c2053a57a0f52bb7b941f2ee262ebe` |
| relocation.log | `13525260b29b54e924bf49ef1ade89b41289e2a442a04b90a2ce497938449878` |
| artifact-proof.log | `9040d724965d1c3b54c5cc2d4fb8000984f5a025e843a9c80b08ddedd5466b61` |

W3 package reference: `dill/0.4.1#15d82e5000b79903cac4ce5d0d7cec49:da39a3ee5e6b4b0d3255bfef95601890afd80709#130db12eb1f1319f1d0a1212f072976f`. Package ID `da39a3ee5e6b4b0d3255bfef95601890afd80709`; artifact inspection has 61 files including Conan metadata, no ELF/ABI objects, bytecode, pickled test residues or setuptools.

Final ConanVerifier overall PASS: G1/G2/G3 execute; G0 skips its unknown-build-system prequery and G4/L2/L4/L5 do not actually inspect the package due to legacy cache-ID parsing. Original W3 and direct artifact proof provide the corresponding real evidence. Its legacy verifier locally uses @ohpcd/stable; W3/consumer artifact proof uses the actual no-user/channel reference above. No alias is uploaded.
