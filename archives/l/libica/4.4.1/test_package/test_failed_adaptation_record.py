#!/usr/bin/env python3
"""Conan test_package for libica 4.4.1 — verifies the failed-adaptation record.

SCOPE (stated precisely): this is a consumer-side, really-executed check of the
*adaptation record package*.  It verifies the record is present, complete,
truthful (status: failed) and internally consistent — in particular that the
test accounting declared in manifest.yaml matches the numbers *recomputed from
the shipped raw logs*, and that every evidence path the manifest cites resolves
inside the package.

It does NOT — and cannot — verify that libica itself builds or functions on
aarch64: upstream libica does not compile there (see the shipped raw logs).
"""

import os
import pathlib
import re
import sys

# Must stay identical to EVIDENCE_REF_RE in the recipe's conanfile.py so that
# build() and this consumer-side test enforce the same invariant.
#
# Known limitation, stated plainly: only BARE `evidence:` / `raw_logs:` keys
# are treated as citations.  Prefixed keys such as `upstream_total_evidence:`
# or `host_triplet_evidence:` are NOT matched, so their values are NOT
# validated or resolved here -- they are as trustworthy as their own text.
# This is a deliberate trade-off (a looser pattern would match prose too), but
# it must not be mistaken for coverage.  Anything that must be validated has to
# use a bare key.
EVIDENCE_REF_RE = r'^[ \t]*(?:evidence|raw_logs):[ \t]*"?([^"\n]+?)"?[ \t]*$'


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main():
    if len(sys.argv) < 2:
        fail("usage: test_failed_adaptation_record.py <package_folder>")
    pkg = sys.argv[1]
    print(f"[test] verifying libica 4.4.1 failed-adaptation record in {pkg}")

    # 1) required record files must be packaged
    required = ["manifest.yaml", "notes.md", "conandata.yml"]
    for name in required:
        if not os.path.isfile(os.path.join(pkg, name)):
            fail(f"missing record file: {name}")
        print(f"[ok] present: {name}")

    manifest = read(os.path.join(pkg, "manifest.yaml"))

    # 2) manifest must truthfully declare the failed status and the cause class.
    #    Anchored to the actual YAML key -- a bare substring test would also
    #    match the literal text inside prose blocks (skipped_reason /
    #    failure_reason), i.e. it would pass even after `status:` was flipped.
    if not re.search(r'^status:[ \t]*failed[ \t]*$', manifest, re.M):
        fail("manifest does not declare a top-level 'status: failed'")
    print("[ok] manifest declares status: failed")

    if not re.search(r'^\s*class:[ \t]*env_unsupported[ \t]*$', manifest, re.M):
        fail("manifest does not declare failure class env_unsupported")
    print("[ok] failure class recorded: env_unsupported")

    if "software: libica" not in manifest:
        fail("manifest software field is not libica")
    if 'version: "4.4.1"' not in manifest:
        fail("manifest version is not 4.4.1")
    print("[ok] manifest identity: libica 4.4.1")

    # 3) every evidence path cited by the manifest must resolve inside the pkg
    #    (previously declared-but-unchecked: dangling paths went unnoticed)
    #    NOTE: EVIDENCE_REF_RE is deliberately identical to the one in the
    #    recipe's conanfile.py -- both guard the same invariant.
    cited = re.findall(EVIDENCE_REF_RE, manifest, re.M)
    cited = [c.strip().strip('"').strip() for c in cited]
    cited = [c for c in cited if c]
    if not cited:
        fail("manifest cites no evidence paths")
    for rel in cited:
        # The citation must be package-relative: an absolute path would make
        # os.path.join discard the package dir, and "../" would escape it.
        # Both would let os.path.exists() probe the HOST filesystem while we
        # still print "resolves in-package".
        if os.path.isabs(rel) or ".." in pathlib.PurePosixPath(rel).parts:
            fail(f"evidence citation must be package-relative: {rel}")
        target = os.path.normpath(os.path.join(pkg, rel))
        # realpath on BOTH sides: the `..`/absolute checks above leave symlinks
        # as the only remaining escape route, and comparing unresolved paths
        # would let a symlinked citation resolve outside the package unnoticed.
        pkg_root = os.path.realpath(pkg)
        if os.path.commonpath([pkg_root, os.path.realpath(target)]) != pkg_root:
            fail(f"evidence citation escapes the package: {rel}")
        if os.path.isdir(target):
            # a directory citation must be non-empty: an accidentally empty
            # evidence dir must not pass as "resolved"
            if not os.listdir(target):
                fail(f"manifest cites an EMPTY evidence directory: {rel}")
        elif not os.path.exists(target):
            fail(f"manifest cites evidence absent from package: {rel}")
    # One aggregate line (rather than one per path) so the runtime [ok] count --
    # and therefore the declared assertion_count -- does not drift when the
    # manifest gains or loses an evidence reference.
    print(f"[ok] all {len(cited)} cited evidence paths resolve in-package")

    # 4) test accounting must match the numbers RECOMPUTED from the shipped
    #    raw logs.  The recomputed values are only smoke-checked for sanity
    #    (non-zero) and then compared against the digest's *declared* values;
    #    no 39/51 literal is pinned here (see the note at the recomputation
    #    below for why).
    m_total = re.search(r"^\s*upstream_total:\s*(\d+)", manifest, re.M)
    m_exec = re.search(r"^\s*upstream_executable_on_aarch64:\s*(\d+)",
                       manifest, re.M)
    if not m_total or not m_exec:
        fail("manifest is missing test accounting fields")
    total, executable = int(m_total.group(1)), int(m_exec.group(1))
    make_log = os.path.join(pkg, "reports", "raw-logs", "ica_makeF.log")
    mp_log = os.path.join(pkg, "reports", "raw-logs", "ica_mps_aarch64.log")
    host_log = os.path.join(pkg, "reports", "raw-logs", "ica_mps_host.log")
    # Every raw log that some declared number depends on must be guarded here:
    # otherwise deleting one would silently drop its comparison and the record
    # would still pass while a headline claim lost its evidence.
    for log in (make_log, mp_log, host_log):
        if not os.path.isfile(log):
            fail(f"raw log required for recomputation is missing: {log}")

    # recompute the failure counts straight from the shipped raw logs.
    # These are compared against the DIGEST's declared values (below), not
    # against hardcoded constants: the exact counts are an artifact of this one
    # build (how many TUs include the header, warning level, etc.), so pinning
    # them here would make the record red for a misleading reason if the logs
    # were ever regenerated.  The declared values are the source of truth, and
    # they are cross-checked against the logs.
    # Count per LINE, matching the documented `grep -c` convention used in
    # unadaptable-assessment.md.  str.count() would count substring
    # occurrences, so a regenerated log with two "error:" on one line would
    # disagree with the digest and fail for a misleading reason.
    make_errs = sum(1 for ln in read(make_log).splitlines() if "error:" in ln)
    mp_errs = sum(1 for ln in read(mp_log).splitlines() if "error:" in ln)
    if make_errs == 0 or mp_errs == 0:
        fail(f"recomputed error counts are zero "
             f"(make={make_errs}, mp.S={mp_errs}) -- raw logs look wrong")
    print(f"[ok] recomputed from raw logs: {make_errs} make errors, "
          f"{mp_errs} mp.S errors")

    # The 36-lines / 18-sites decomposition must hold arithmetically, otherwise
    # the "18 x 2 = 36" explanation in notes.md and the digest would disagree.
    # Counted the same way the documents do: per log line, distinct header
    # line numbers for the deduplicated figure.
    make_text = read(make_log)
    constraint_lines = [ln for ln in make_text.splitlines()
                        if "invalid" in ln and "constraint" in ln]
    sites = {m for m in re.findall(r"s390_crypto\.h:(\d+):", make_text)}
    if len(constraint_lines) != 2 * len(sites):
        fail(f"constraint decomposition does not close: "
             f"{len(constraint_lines)} log lines vs {len(sites)} distinct sites "
             f"(expected exactly 2x)")
    print(f"[ok] constraint decomposition closes: {len(constraint_lines)} log "
          f"lines = 2 x {len(sites)} distinct sites")

    # the digest must agree with the raw logs it summarises.  Substring checks
    # alone would pass on stray digits elsewhere in the file, so the digest's
    # declared counts are extracted and asserted equal to the recomputed ones.
    digest = os.path.join(pkg, "reports", "raw-build-failure.txt")
    if not os.path.isfile(digest):
        fail("evidence digest is missing: reports/raw-build-failure.txt")
    digest_text = read(digest)

    # The digest declares two totals (SECTION A = make, SECTION B = mp.S).
    # Bound each search to its own section so a missing/renamed header cannot
    # silently make SECTION A's pattern capture SECTION B's number.
    if "SECTION A" not in digest_text or "SECTION B" not in digest_text:
        fail("evidence digest is missing its SECTION A / SECTION B headers")
    if digest_text.index("SECTION A") > digest_text.index("SECTION B"):
        fail("evidence digest has SECTION A after SECTION B -- "
             "refusing to parse a reordered digest")
    sec_a, sec_b = digest_text.split("SECTION B", 1)
    sec_a = sec_a.split("SECTION A", 1)[1]

    m = re.search(r"error:\s*总行数\s*=\s*(\d+)", sec_a)
    if not m:
        fail("evidence digest does not declare SECTION A (make) error count")
    if int(m.group(1)) != make_errs:
        fail(f"digest SECTION A declares {m.group(1)}, "
             f"but make raw log yields {make_errs}")
    print(f"[ok] digest SECTION A = {m.group(1)} matches recomputed make errors")

    m = re.search(r"error:\s*总行数\s*=\s*(\d+)", sec_b)
    if not m:
        fail("evidence digest does not declare SECTION B (mp.S) error count")
    if int(m.group(1)) != mp_errs:
        fail(f"digest SECTION B declares {m.group(1)}, "
             f"but mp.S raw log yields {mp_errs}")
    print(f"[ok] digest SECTION B = {m.group(1)} matches recomputed mp.S errors")

    # SECTION B2 declares the *host* (x86_64) assembler's rejection count for the
    # same mp.S -- the record's strongest independent argument that the failure is
    # architecture-specific assembly rather than a cross-toolchain misconfiguration.
    # It is recomputed from the shipped host log so that claim cannot rot silently.
    m = re.search(r"Error\s*行数\s*=\s*(\d+)", sec_b)
    if not m:
        fail("evidence digest does not declare SECTION B2 (host mp.S) count")
    host_errs = sum(1 for ln in read(host_log).splitlines() if "Error" in ln)
    if host_errs == 0:
        fail("recomputed host assembler error count is zero -- host log looks wrong")
    if int(m.group(1)) != host_errs:
        fail(f"digest SECTION B2 declares {m.group(1)}, "
             f"but host raw log yields {host_errs}")
    print(f"[ok] digest SECTION B2 = {m.group(1)} matches recomputed host errors")

    # total / executable must be recomputable from shipped evidence, not a bare
    # assertion.  The enumeration log is the source of truth for `total`; the
    # manifest's declared value is then asserted equal to it (the reverse of
    # pinning a literal here, which would go red for a misleading reason if the
    # upstream tree were ever re-enumerated).
    enum_log = os.path.join(pkg, "reports", "raw-logs", "ica_test_enum.log")
    if not os.path.isfile(enum_log):
        fail("upstream test enumeration evidence is missing: "
             "reports/raw-logs/ica_test_enum.log")
    enum_text = read(enum_log)
    # Tolerate whitespace/quote-style variation (same convention as the
    # ICA_FLAG probe below): a regenerated log must bind, not abort with the
    # misleading "does not contain a recomputable count" reason.
    m = re.search(r"ls test/\*\.c[ \t]*\|[ \t]*wc -l[ \t]*\n[ \t]*(\d+)", enum_text)
    if not m:
        fail("test enumeration log does not contain a recomputable count")
    enumerated = int(m.group(1))
    if enumerated != total:
        fail(f"enumeration log yields {enumerated} upstream tests, "
             f"but manifest declares {total}")
    if executable != 0:
        fail(f"declared executable count={executable}, expected 0 on aarch64 "
             "(no aarch64-usable libica exists)")
    print(f"[ok] upstream_total={total} recomputed from shipped "
          "ica_test_enum.log")

    # 5 / 43 split must also be recomputable, otherwise those fields could be
    # silently edited while every other count still ties out.
    # Anchor on the probe's SEMANTIC identity (the ICA_FLAG alternation + the
    # `wc -l` count that follows), not on the byte-exact command line: a
    # regenerated log that switches quote style or spacing must still bind
    # rather than abort.  This keeps it as tolerant as the `ls test/*.c`
    # probe above.
    m_hw = re.search(
        r"ICA_FLAG[^\n]*\|[ \t]*wc -l[ \t]*\n[ \t]*(\d+)", enum_text)
    if not m_hw:
        fail("enumeration log does not contain a recomputable hw-bound count")
    hw_bound = int(m_hw.group(1))
    m_nohw = re.search(r"^\s*upstream_no_hw_reference:\s*(\d+)", manifest, re.M)
    m_hwb = re.search(r"^\s*upstream_hw_bound:\s*(\d+)", manifest, re.M)
    if not (m_nohw and m_hwb):
        fail("manifest is missing the no_hw_reference / hw_bound split")
    no_hw, declared_hw = int(m_nohw.group(1)), int(m_hwb.group(1))
    if declared_hw != hw_bound:
        fail(f"manifest declares upstream_hw_bound={declared_hw}, "
             f"but ica_test_enum.log yields {hw_bound}")
    # no_hw_reference must ALSO be recomputable -- §4 of the enumeration log
    # lists those cases one per line.  Without this, no_hw could be changed to
    # any v while hw_bound was changed to total-v, and both the closure check
    # below and the hw_bound check above would still pass.
    listed_nohw = len(re.findall(
        r"^\s+\S+_test\.c\s+ica_\* calls = \d+", enum_text, re.M))
    if listed_nohw != no_hw:
        fail(f"manifest no_hw_reference={no_hw}, but ica_test_enum.log "
             f"section 4 lists {listed_nohw} such cases")
    if no_hw + declared_hw != total:
        fail(f"hw split does not close: {no_hw} + {declared_hw} != {total}")
    print(f"[ok] hw split closes: no_hw {no_hw} (listed in ica_test_enum.log) "
          f"+ hw_bound {declared_hw} (recomputed) = {total}")

    # The host-triplet provenance is the record's strongest single piece of
    # reproducibility evidence, so it is asserted literally rather than left to
    # a documentation-only prefixed key: the declared line number must exist AND
    # carry the declared text.  Without this, regenerating ica_confF.log could
    # move that line while every summary stayed green.
    m_ln = re.search(r"^\s*host_triplet_line:\s*(\d+)", manifest, re.M)
    m_tx = re.search(r'^\s*host_triplet_line_text:\s*"([^"\n]*)"', manifest, re.M)
    if not (m_ln and m_tx):
        fail("manifest is missing the host_triplet_line / _line_text citations")
    ln_no, ln_txt = int(m_ln.group(1)), m_tx.group(1)
    conf_lines = read(os.path.join(
        pkg, "reports", "raw-logs", "ica_confF.log")).splitlines()
    if ln_no < 1 or ln_no > len(conf_lines):
        fail(f"host_triplet_line {ln_no} is outside ica_confF.log "
             f"({len(conf_lines)} lines)")
    if conf_lines[ln_no - 1].strip() != ln_txt:
        fail(f"ica_confF.log line {ln_no} is "
             f"{conf_lines[ln_no - 1].strip()!r}, but the manifest declares "
             f"{ln_txt!r}")
    print(f"[ok] ica_confF.log line {ln_no} matches the declared host triplet")
    # The repo-standard accounting must close. Scope the search to the
    # `test_results:` block first: an unscoped `^\s*total:` is ambiguous in a
    # manifest with several blocks, and `passed/failed/skipped` matched
    # anywhere could silently bind to keys in another section.
    m_blk = re.search(r"^test_results:\s*$(.*?)(?=^\S|\Z)", manifest,
                      re.M | re.S)
    if not m_blk:
        fail("manifest has no top-level test_results block")
    blk = m_blk.group(1)

    def _field(name):
        mm = re.search(rf"^\s*{name}:\s*(\d+)\s*$", blk, re.M)
        return int(mm.group(1)) if mm else None

    s, p, f = _field("skipped"), _field("passed"), _field("failed")
    t_decl = _field("total")
    if None in (s, p, f, t_decl):
        fail("test_results must declare numeric total/passed/failed/skipped")
    if p + f + s != t_decl:
        fail(f"test_results does not close: {p}+{f}+{s} != {t_decl}")
    if t_decl != total:
        fail(f"test_results.total ({t_decl}) disagrees with "
             f"tests.upstream_total ({total})")
    print(f"[ok] test_results closes: passed {p} + failed {f} + skipped {s} "
          f"= {t_decl}, matching tests.upstream_total")

    # `total` is already validated against the enumeration log above and the
    # accounting closure here, so no literal 48 is pinned. `executable` was
    # asserted non-zero-safe above; only report it.
    print(f"[ok] test accounting truthful: {executable}/{total} executable "
          "on aarch64")
    # the configure exit code must be self-verifiable from the shipped log
    # itself, not merely asserted in prose: the whole causal chain rests on
    # "configure succeeded, so make's failure is attributable to libica's own
    # sources rather than a broken toolchain".
    conf_log = os.path.join(pkg, "reports", "raw-logs", "ica_confF.log")
    if not os.path.isfile(conf_log):
        fail("configure log is missing: reports/raw-logs/ica_confF.log")
    conf_text = read(conf_log)
    m_conf = re.search(r"^=== configure exit code: (\d+) ===$", conf_text, re.M)
    if not m_conf:
        fail("configure log does not mechanically record its exit code")
    if int(m_conf.group(1)) != 0:
        fail(f"configure exit code recorded as {m_conf.group(1)}, expected 0")
    # Anchored to a real `config.status: creating <file>` line. A bare
    # substring test would be satisfied by this log's own trailing note, which
    # quotes that phrase -- i.e. the assertion would pass even for a log that
    # never reached the config.status stage.
    if not re.search(r"^config\.status: creating \S+$", conf_text, re.M):
        fail("configure log lacks anchored config.status markers "
             "(did it really reach the config.status stage?)")
    n_created = len(re.findall(r"^config\.status: creating \S+$", conf_text,
                               re.M))
    if re.search(r"^configure: error", conf_text, re.I | re.M):
        fail("configure log contains a configure error line")
    print(f"[ok] configure exit code {m_conf.group(1)} recorded in-log, "
          f"{n_created} config.status markers, no configure error lines")

    # 5) notes must document the three architecture-level root causes
    notes = read(os.path.join(pkg, "notes.md"))
    for token in ("asm/zcrypt.h", "s390_crypto.h", "mp.S"):
        if token not in notes:
            fail(f"notes do not document root cause: {token}")
    print("[ok] notes document all three architecture-level root causes")

    # 6) no fake artifacts: the record package must not ship a library or
    #    headers (that would imply a faked successful adaptation)
    for stray in ("lib", "include"):
        if os.path.isdir(os.path.join(pkg, stray)):
            fail(f"record package must not ship a '{stray}' directory "
                 "(would imply a fake successful adaptation)")
    print("[ok] no fake library/header artifacts shipped")

    print("PASS: libica 4.4.1 failed-adaptation record verified end-to-end")


if __name__ == "__main__":
    main()
