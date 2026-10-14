#!/usr/bin/env python3
"""Conan recipe — libica 4.4.1 (failed OHOS adaptation record).

libica is IBM Z (s390x) mainframe-only hardware crypto library.  Its entire
implementation is bound to s390 general-purpose-register inline assembly,
the s390-only kernel UAPI header <asm/zcrypt.h>, and the mainframe crypto
card device /dev/zcrypt.  Upstream ships no architecture-neutral or software
backend, so there is no adaptation path for aarch64 / OpenHarmony.

Following the established repository pattern for structurally unadaptable
packages (see archives/b/bltool, archives/a/abx, ...), this recipe does NOT
attempt to fake a build.  Instead it builds a *failed-adaptation record*:
`conan create` succeeds, CI stays green, and `status: failed` in
manifest.yaml records the truthful outcome.  The full technical evidence
lives under reports/ and is shipped inside the package.

NOTE ON SCOPE: the packaged `test_package` verifies that this *record* is
present, complete and internally consistent.  It does NOT verify that the
libica library itself builds or works on aarch64 — it cannot, because upstream
libica does not compile there.  See notes.md for the evidence.
"""
import os
import pathlib
import re

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout

# Files that make up, and prove, the adaptation record.
RECORD_FILES = ("manifest.yaml", "notes.md", "conandata.yml")
# Evidence is exported wholesale; the *validation* of which paths are cited is
# driven by parsing manifest.yaml, not by a hardcoded list.
EVIDENCE_DIR = "reports"

# Single source of truth for "which manifest fields cite evidence".
# test_package/test_failed_adaptation_record.py uses the SAME pattern (kept in
# sync deliberately): both guard the invariant that every cited evidence path
# resolves inside the package, so the two must not diverge.
#
# Only BARE `evidence:` / `raw_logs:` keys are treated as citations, matched at
# line start (leading indent allowed).
#
# Known limitation, stated plainly: this pattern does NOT match prefixed keys
# such as `upstream_total_evidence:` or `host_triplet_evidence:`, so their
# values are NOT validated and NOT resolved by this check.  That is a
# deliberate trade-off -- a looser pattern would also match arbitrary prose --
# but it must not be mistaken for coverage.  Where a prefixed key carries a
# real path it is therefore only as trustworthy as its own text; the bare
# `failure.evidence` / `failure.raw_logs` keys are the ones actually guarded.
# Any citation that MUST be validated has to use a bare key.
EVIDENCE_REF_RE = r'^[ \t]*(?:evidence|raw_logs):[ \t]*"?([^"\n]+?)"?[ \t]*$'


class LibicaConan(ConanFile):
    name = "libica"
    version = "4.4.1"
    description = ("Failed OHOS adaptation record for libica - "
                   "IBM Z (s390x) hardware-bound crypto library")
    # Upstream libica is released under the Common Public License V1.0
    # (see upstream LICENSE and libica.spec "License: CPL").
    license = "CPL-1.0"
    homepage = "https://github.com/opencryptoki/libica"

    # Four-part settings matrix is required by the repository's PF8 recipe gate
    # (L0p) -- it is the precondition for the cross-compilation matrix.
    settings = "os", "compiler", "build_type", "arch"

    # The raw logs under reports/raw-logs/ are a *deliverable*, not build
    # residue: test_package recomputes the record's counts from them.  Conan's
    # globbing is fnmatch-based so `reports/*` does span `/`, but we list the
    # nested logs explicitly anyway so this invariant does not silently depend
    # on glob-engine behaviour.
    exports_sources = (
        *RECORD_FILES,
        f"{EVIDENCE_DIR}/*",
        f"{EVIDENCE_DIR}/raw-logs/*.log",
    )

    def layout(self):
        basic_layout(self)

    def _read(self, name):
        path = os.path.join(self.source_folder, name)
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def build(self):
        # Build the "failure record package": validate that the record and its
        # evidence are complete and self-consistent.  This deliberately does
        # NOT raise on the adaptation failure itself -- the failure is the
        # subject of the record, and must stay truthful in manifest.yaml.
        for fname in RECORD_FILES:
            if not os.path.isfile(os.path.join(self.source_folder, fname)):
                raise RuntimeError(
                    f"failed adaptation record incomplete: missing {fname}")

        manifest = self._read("manifest.yaml")

        # The record must truthfully declare the failed status.  Anchored to the
        # actual YAML key (at line start) -- a bare substring test would also
        # match the literal text inside prose blocks such as `skipped_reason`
        # or `failure_reason`, i.e. it would silently pass after someone flipped
        # `status:` to something else while a comment still said "status: failed".
        if not re.search(r'^status:[ \t]*failed[ \t]*$', manifest, re.M):
            raise RuntimeError(
                "adaptation record must declare a top-level 'status: failed'")

        # Every path that manifest.yaml cites as evidence must actually be
        # shipped.  Parsed straight from manifest.yaml (not from a hardcoded
        # tuple) so that adding a new citation cannot silently dangle.
        # NOTE: this pattern is intentionally identical to the one used by
        # test_package/test_failed_adaptation_record.py -- both guard the same
        # invariant, so a divergence would let build() pass while the consumer
        # test fails.
        # Guard against a field being present but empty (e.g. `evidence: ""`),
        # which would otherwise make this loop a no-op.
        cited = re.findall(EVIDENCE_REF_RE, manifest, re.M)
        cited = [c.strip().strip('"').strip() for c in cited]
        cited = [c for c in cited if c]
        if not cited:
            raise RuntimeError(
                "adaptation record cites no usable evidence paths "
                "(every evidence/raw_logs field is missing or empty)")
        for rel in cited:
            # The citation must be package-relative: an absolute path would make
            # os.path.join discard the package dir, and "../" would escape it.
            # Both would let os.path.exists() probe the HOST filesystem while we
            # still claim "resolves in-package".
            if os.path.isabs(rel) or ".." in pathlib.PurePosixPath(rel).parts:
                raise RuntimeError(
                    f"evidence citation must be package-relative: {rel}")
            full = os.path.normpath(os.path.join(self.source_folder, rel))
            # realpath (not abspath) on BOTH sides: the `..`/absolute checks
            # above leave symlinks as the only remaining escape route, and
            # comparing unresolved paths would let a symlinked citation resolve
            # to a HOST path outside the package while still "passing".
            src_root = os.path.realpath(self.source_folder)
            if os.path.commonpath([src_root, os.path.realpath(full)]) != src_root:
                raise RuntimeError(
                    f"evidence citation escapes the package: {rel}")
            # a directory-typed citation must be non-empty, otherwise a
            # silently-empty evidence dir would still "resolve".
            if os.path.isdir(full):
                if not os.listdir(full):
                    raise RuntimeError(
                        f"record cites an EMPTY evidence directory: {rel}")
            elif not os.path.exists(full):
                raise RuntimeError(
                    f"record cites evidence that is not shipped: {rel}")
            self.output.info(f"evidence OK: {rel}")

    def package(self):
        # Ship the adaptation record and its evidence: this is the deliverable
        # of a failed-adaptation package, and the consumer-side test verifies
        # the whole thing end-to-end.
        for fname in RECORD_FILES:
            copy(self, fname, src=self.source_folder, dst=self.package_folder)
        copy(self, f"{EVIDENCE_DIR}/*", src=self.source_folder,
             dst=self.package_folder)
        # explicit recursion for the nested raw logs (see exports_sources note)
        copy(self, f"{EVIDENCE_DIR}/raw-logs/*.log", src=self.source_folder,
             dst=self.package_folder)

    def package_info(self):
        # Nothing is produced for consumers: the library cannot be built.
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
