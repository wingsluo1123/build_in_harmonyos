# qpack 0.0.21

Python QPack serializer/deserializer with its real C extension. Source:
https://github.com/cesbit/qpack/tree/e55af6e2e7c8071a8533f4395682ddfb0b3018ce.

The proposed repair normalizes the Python3 comparison result to an equality
predicate. It retains the C backend and supported encoding aliases. It does
not claim complete C/fallback parity for other codecs or integer boundaries.

The native Conan recipe requires the published Python3.12.9 package. Upstream
tests: 9 unchanged unittest methods; one added real C consumer with 4 groups.
The actual private OHOS native package passed all 9 original methods and all
4 groups in one consumer. Standalone verifier returned 0 with its documented
skips. Formal W3 on 2026-10-09 passed setup/build, the complete 13-file JC
prdiff, and L0/L1/L4/L5; L2 skipped because there is no bin directory.
The earlier full-scan JC failure is preserved in notes. Official PR CI,
AtomCode review, publication and acceptance remain pending.
