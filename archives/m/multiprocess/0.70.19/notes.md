# multiprocess 0.70.19 adaptation

Task15170; account2301_79503900 (chenicia); team北京理工大学/天天开心; branchfeat/multiprocess-0.70.19.
Official sdist and matching CPython3.12.9 source SHA256 are in conandata.yml. Published dill/0.4.1 and setuptools/84.0.0 downloaded exactly with positive registry controls and device binaries.

## Fixes

1. Reuse the vendor interpreter's concrete default without committing global context; preserve explicit fork/spawn/forkserver contexts.
2. Delegate abstract-socket capability and actually select an abstract address for generated listeners. User-supplied pathname sockets remain subject to platform policy.
3. Bootstrap package-private spawn/resource-tracker/forkserver commands with inherited paths while retaining interpreter flags, including -E/-I.
4. Bind SharedMemoryManager destructor debug callables so interpreter shutdown does not call cleared globals.
5. Correct stray stdlib imports in three upstream test files; preserve original assertions, isolated flags and process-leak checks. Run the otherwise orphaned39-case main-handling module.

Only the CPython test namespace is exposed to testing; the full upstream Lib must not shadow vendor runtime modules. The installed primary package path alone is insufficient: verify runtime module origins too.

## Validation boundary

Consumer staged artifact14/14 passed after explicit RED/GREEN controls. Final full Conan/W3 and per-case pass/skip accounting are recorded in reports/validation-summary.md after completion; no blanket100% assertion is made here. Version family is fixed toCPython3.12.9 and remains in package ID. Remote CI/review/knowledge admission/merge/release are separate states.


CPython test support now uses the official GitHub v3.12.9 archive: all 1581 Lib/test files match the original python.org release byte-for-byte, while the existing CI mirror fallback completed a full SHA256-verified download in 113.21s. Full W3, artifact controls and verbose upstream regression were repeated after the source change; older receipts remain separate.

## 最终状态

本地Conan/W3通过；上游1057/1213，跳过156、失败0；消费者14/14；载荷负向/恢复/重定位通过。当前HEAD远端CI、审核、合并、发布与知识入库另列，未自动合并。
