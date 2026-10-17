# kamailio-tlsa 6.0.6 adaptation

## Identity and scope

Official source: https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz
SHA256: `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48`.
Tag 6.0.6 commit: `9b4746db7278eece2f693f54a238106449b8cff6`.
License: GPL-2.0-or-later. This package installs TLSA, not the full SIP server.
Runtime requires a matching 6.0.6 core; the existing 6.1.3 core is not ABI-compatible.

Dependency: published `openssl/3.5.8.1`, PIC static archives. Its recipe and
OHOS binary were downloaded before adaptation. No additional dependency package
is bundled into this PR. Platform macros reuse the existing Kamailio-family
knowledge; `DEFS=-UHAVE_RESOLV_RES` selects upstream public-resolver behavior
instead of glibc `_res` internals. Source paths are supplied explicitly through
the nonempty `SSL_BUILDER=source` branch, with no host pkg-config resolution.

## Actual failures and fixes

1. Function-only binding left embedded OpenSSL data preemptible. A preloaded
   static OpenSSL peer caused real native TLSA allocator errors. Limit symbol
   visibility to the two OpenSSL archives, preserving Kamailio ABI exports.
2. Symbol hiding alone left the upstream fork callback clearing unrelated
   pthread keys by numeric range. Native child sentinels reported `preserved=0`.
   Wrap key creation/deletion references linked into TLSA, track opaque live
   keys and detach only owned values at fork under a registry mutex. The
   `KSR_TLSA_OWNED_KEYS` feature guard leaves the legacy `tls` path unchanged.
3. The OHOS runtime owns descriptors that core's blanket foreground cleanup
   closes. Plain TCP reproduced the subsequent `Bad file descriptor` worker
   failure without TLSA. Preserve descriptors when running in foreground;
   retain normal daemon cleanup. The companion core patch is shipped as source
   with explicit integration instructions. Run the patched core with `-DD`.

Three patches were generated with `refresh-patch --auto`; added key-registry
sources are exported from `compat/`. This avoids the E254/E484 new-file patch
dry-run behavior without changing the framework. No generated source files
were edited. The independent symbol probe also reproduced the boundary outside
Kamailio: ordinary linking rejected the allocator hook, function binding failed
SSL_CTX initialization, and archive hiding allowed both SSL users to retain
their allocators. Knowledge: `knowledge/drafts/E429-draft-TL60.{kv,md}` (candidate).

## Native verification

2026-10-05: OHOS AArch64, HNP SDK 26.0.0.18, Clang 15, Conan 2.29.1.
The native `conan-verify kamailio-tlsa 6.0.6` exited 0. Its `conan create`
downloaded the official source, applied three patches and exported sources, built the package and
compiled a matching real core plus `sl` solely inside the consumer test tree.
The test loaded the **installed** TLSA and passed **33/33 assertions**:

- 7 ELF/install checks: module type/architecture, static SSL dependency closure,
  local SSL APIs, retained module ABI, no runtime search paths, license/config.
- 6 checks with TLSA alone: TLS 1.2 and 1.3 SIP OPTIONS, 12 connections from four
  clients with two TCP workers, client certificate-trust rejection, orderly
  exit and absence of allocator-corruption diagnostics.
- 10 checks each with a preinitialized external static OpenSSL and with 64
  earlier foreign keys: the preceding checks plus external initialization,
  preserved keys, working SSL_CTX in observed children and unchanged allocator.

The 12 connections in each mode are one concurrency assertion, not 12 tests.
Certificate generation and helper compilation are checked prerequisites, not
extra counted assertions. The earlier development run passed 26/26 functional
assertions and is not added to the formal test denominator.

Command (native OHOS, repository root):

```sh
python3 scripts/ohc-run.py conan-verify kamailio-tlsa 6.0.6
python3 scripts/ohc-run.py finish kamailio-tlsa 6.0.6 built
```

The first command has passed; finish/W3 and the independent audit are recorded
separately in the final delivery summary. Official CI, publication and C/B2
recognition require the subsequent participant submission and external review.

## Upstream test audit and limits

The official release tarball has no `test/` tree. The same-tag Git checkout
contains 49 numbered `test/unit/*.sh` scripts; they target core or other modules
and none defines an active TLSA test. TLS mentions in `5.cfg` are commented out.
Neither TLSA build entry point registers a test. Native `make check` was actually
run and exited 2 because the core Makefile has no check target.

The 49 scripts are inventoried. Two applicable core scripts (`1.sh`, `18.sh`)
are executed by `run_upstream.py`; the other 47 require unrelated modules or
fixtures, with per-file reasons in `test_package/upstream-audit.json`. Other
upstream test directories are listed separately rather than hidden in this count.
The checked-in scripts retain their upstream content (LF normalized). Runtime
copies use foreground supervision and a private loopback port. `18.sh` also
replaces conflicting `-T -N 0` with `-N 1`, uses numeric POSIX uid/gid, and omits
same-identity switching only when that UID has no passwd entry. Account-switching
coverage is excluded. A same-version Linux control also rejects `-T -N 0`;
this is not an OHOS-only parser failure. An added negative assertion preserves
the rejection contract and checks its diagnostic.

TLSA-specific upstream automated denominator: 0 (N/A). Applicable adapted
upstream startup cases: 2. New assertions: 34 (33 package/transport assertions
plus one invalid-option check). Native Conan verification passed all 36 checks;
the development 26 and earlier 33 are prior runs, not additional test cases.
Initial foreground/port-adapted startup control: 1 pass and 1 original CLI-conflict failure. Fully adapted
results do not imply all 49 scripts or all Kamailio modules passed. W3 evidence
and the independent audit are recorded separately in the delivery summary.

The tested scope is the default provider's SIP/TLS server transport and
multi-process coexistence. This is not a claim of complete Kamailio coverage.
Outbound SIP/TLS routing, mutual TLS, SNI domain selection, RPC certificate
reload, WSS routing, external providers, FIPS and PKCS#11 are not validated.
C remains a candidate; its final acceptance scope and upstream denominator
must be confirmed by the reviewers. See `integration.md` for runtime setup.

## Execution record

### 对话 #1 — Task scope and native validation

The participant requested C investigation, with A+B2 as fallback, and retained
commit/push/PR actions. Native Conan and W3 passed on 2026-10-05. The source PR
contains one module and its knowledge draft; matching core/sl are test fixtures.
No adaptation commit, PR, registry upload or official review has occurred.

### 对话 #2 — Framework checks and inherited diagnostics

The generic G0 command invokes ./configure for this Makefile project and exits
127; the real clean Conan build passes. Global W5 reports block-scalar values
in existing E219/E253/E305 as empty, while graph validate passes. Those official
knowledge files are byte-identical to origin/main and outside this patch.
SUMMARY generation also reports a pre-existing schema error. These diagnostics
remain visible; finish returned 1 despite W3 success. Target metadata and
packaging are finalized separately, with no gate override or infrastructure edit.
---

**编译结束**: 2026-10-05 01:54
**最终状态**: built

### Submission authorization and metadata clarification

The participant subsequently requested direct submission and task association.
The original native test results and code remain unchanged. The contest table
classifies the existing normal-mode 12-connection/4-client/2-worker assertion
as the OHOS foreground descriptor regression. The portable -T/-N negative
case is general coverage. Counts remain 2 upstream + 34 new = 36.
The manifest build_date records the actual 2026-10-05 native build.
