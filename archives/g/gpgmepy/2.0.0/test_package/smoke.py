#!/usr/bin/env python3
"""gpgmepy 2.0.0 test_package smoke test (R34 — real API usage, no GnuPG engine).

Assertions:
  1. import gpg (SWIG extension `_gpgme...so` loads against conan libgpgme)
  2. gpg.version.versionstr == "2.0.0"        (binding version)
  3. gpg.version.gpgme_versionstr == "1.24.0" (linked against conan gpgme)
  4. gpg.Data() can be constructed            (C API round-trip)

These do NOT require a `gpg` binary; they only exercise the binding/library
linkage. (Upstream tests that need the GnuPG engine are all blocked — see
reports/test-report.md.)
"""
import sys

failures = []

try:
    import gpg
    print("PASS import gpg from", gpg.__file__)
except Exception as exc:  # pragma: no cover
    failures.append("import gpg failed: %s" % exc)
    sys.exit(1)

if getattr(gpg.version, "versionstr", "") == "2.0.0":
    print("PASS gpg.version.versionstr ==", gpg.version.versionstr)
else:
    failures.append("gpg.version.versionstr = %r" %
                    getattr(gpg.version, "versionstr", None))

gme = getattr(gpg.version, "gpgme_versionstr", "")
if gme.startswith("1.24"):
    print("PASS gpg.version.gpgme_versionstr ==", gme)
else:
    failures.append("gpg.version.gpgme_versionstr = %r" % gme)

try:
    d = gpg.Data()
    print("PASS gpg.Data() ->", type(d).__name__)
except Exception as exc:  # pragma: no cover
    failures.append("gpg.Data() failed: %s" % exc)

if failures:
    for item in failures:
        print("FAIL:", item)
    sys.exit(1)
print("ALL test_package assertions passed")
