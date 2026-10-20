#!/usr/bin/env python3
"""Consumer test for the mm-common Conan package.

A C++ binding module uses mm-common in two ways:

* Meson modules run ``mm-common-get <buildscript_dir> <doctool_dir>`` to copy the
  shared build scripts and the Doxygen tool files into their own source tree.
* Autotools modules run ``mm-common-prepare <configure.ac>`` to copy the shared
  ``.am`` include files into ``AC_CONFIG_AUX_DIR`` and, when
  ``MM_CONFIG_DOCTOOL_DIR`` is used, the doctool files as well.

Both helpers locate their data relative to their own installation prefix, so
this test runs them for real and checks the resulting file trees and their
contents against the package's own ``share/mm-common`` directory.
"""

import os
import shutil
import subprocess
import sys
import tempfile

VERSION = "1.0.8"

MESON_BUILD_SCRIPTS = [
    "check-dllexport-usage.py",
    "dist-build-scripts.py",
    "dist-changelog.py",
    "doc-reference.py",
    "generate-binding.py",
]
# mm-common-get copies the Python doctool helpers (Meson modules).
MESON_DOCTOOL_FILES = [
    "doc_install.py",
    "doc_postprocess.py",
    "doxygen.css",
    "doxygen-extra.css",
    "tagfile-to-devhelp2.xsl",
]
# mm-common-prepare copies the Perl doctool helpers (Autotools modules).
AUTOTOOLS_DOCTOOL_FILES = [
    "doc-install.pl",
    "doc-postprocess.pl",
    "doxygen.css",
    "doxygen-extra.css",
    "tagfile-to-devhelp2.xsl",
]
AUTOTOOLS_INCLUDES = [
    "compile-binding.am",
    "dist-changelog.am",
    "doc-reference.am",
    "generate-binding.am",
]

CONFIGURE_AC = """\
AC_INIT([mm-probe], [0.1])
AC_CONFIG_AUX_DIR([build])
MM_CONFIG_DOCTOOL_DIR([doc/doctool])
AC_OUTPUT
"""

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    print(("ok   " if condition else "FAIL ") + message)
    if not condition:
        failures.append(message)
    return condition


def run(command, cwd=None):
    print("+ " + " ".join(command))
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def compare_with_package(copied_dir, package_dir, names):
    mismatched = []
    for name in names:
        copied = os.path.join(copied_dir, name)
        expected = os.path.join(package_dir, name)
        if not os.path.isfile(copied) or not os.path.isfile(expected):
            mismatched.append(name)
            continue
        with open(copied, "rb") as handle:
            copied_data = handle.read()
        with open(expected, "rb") as handle:
            expected_data = handle.read()
        if copied_data != expected_data:
            mismatched.append(name)
    return mismatched


def main():
    get_tool = shutil.which("mm-common-get")
    prepare_tool = shutil.which("mm-common-prepare")
    check(get_tool is not None, "mm-common-get is available on PATH")
    check(prepare_tool is not None, "mm-common-prepare is available on PATH")
    if not get_tool or not prepare_tool:
        return

    package_dir = os.path.dirname(os.path.dirname(os.path.realpath(get_tool)))
    pkgdata_dir = os.path.join(package_dir, "share", "mm-common")
    check(os.path.isdir(pkgdata_dir),
          f"package data directory exists next to the helper: {pkgdata_dir}")

    result = run([get_tool, "--version"])
    check(result.returncode == 0 and VERSION in result.stdout,
          f"mm-common-get --version reports {VERSION} "
          f"(rc={result.returncode}, out={result.stdout.strip()!r})")

    result = run([prepare_tool, "--version"])
    check(result.returncode == 0 and VERSION in result.stdout,
          f"mm-common-prepare --version reports {VERSION} "
          f"(rc={result.returncode}, out={result.stdout.strip()!r})")

    workdir = tempfile.mkdtemp(prefix="mm-common-test-")
    try:
        # --- Meson modules: mm-common-get ------------------------------------
        buildscripts = os.path.join(workdir, "build-support")
        doctool = os.path.join(workdir, "doctool")
        result = run([get_tool, buildscripts, doctool])
        check(result.returncode == 0,
              f"mm-common-get filled {buildscripts} and {doctool} (rc={result.returncode})")

        missing = [n for n in MESON_BUILD_SCRIPTS if not os.path.isfile(os.path.join(buildscripts, n))]
        check(not missing, f"Meson build scripts copied (missing: {missing})")

        missing = [n for n in MESON_DOCTOOL_FILES if not os.path.isfile(os.path.join(doctool, n))]
        check(not missing, f"doctool files copied (missing: {missing})")

        empty = [n for n in MESON_BUILD_SCRIPTS
                 if os.path.isfile(os.path.join(buildscripts, n))
                 and os.path.getsize(os.path.join(buildscripts, n)) == 0]
        empty += [n for n in MESON_DOCTOOL_FILES
                  if os.path.isfile(os.path.join(doctool, n))
                  and os.path.getsize(os.path.join(doctool, n)) == 0]
        check(not empty, f"copied files are not empty (empty: {empty})")

        mismatched = compare_with_package(buildscripts, os.path.join(pkgdata_dir, "build"),
                                          MESON_BUILD_SCRIPTS)
        mismatched += compare_with_package(doctool, os.path.join(pkgdata_dir, "doctool"),
                                           MESON_DOCTOOL_FILES)
        check(not mismatched,
              f"copied files are byte-identical to the package data (differs: {mismatched})")

        # --- Autotools modules: mm-common-prepare ----------------------------
        module = os.path.join(workdir, "binding")
        # Binding modules always ship doc/; mm-common-prepare only creates the
        # last directory level of MM_CONFIG_DOCTOOL_DIR (upstream behaviour).
        os.makedirs(os.path.join(module, "doc"))
        configure_ac = os.path.join(module, "configure.ac")
        with open(configure_ac, "w", encoding="utf-8") as handle:
            handle.write(CONFIGURE_AC)

        result = run([prepare_tool, "-c", "-f", configure_ac])
        check(result.returncode == 0,
              f"mm-common-prepare filled the binding tree from {pkgdata_dir} "
              f"(rc={result.returncode}, err={result.stderr.strip()!r})")

        aux_dir = os.path.join(module, "build")
        missing = [n for n in AUTOTOOLS_INCLUDES if not os.path.isfile(os.path.join(aux_dir, n))]
        check(not missing, f"AC_CONFIG_AUX_DIR includes copied (missing: {missing})")

        module_doctool = os.path.join(module, "doc", "doctool")
        missing = [n for n in AUTOTOOLS_DOCTOOL_FILES if not os.path.isfile(os.path.join(module_doctool, n))]
        check(not missing, f"MM_CONFIG_DOCTOOL_DIR files copied (missing: {missing})")

        mismatched = compare_with_package(aux_dir, os.path.join(pkgdata_dir, "build"),
                                          AUTOTOOLS_INCLUDES)
        check(not mismatched,
              f"Autotools includes are byte-identical to the package data (differs: {mismatched})")

        # --- pkg-config metadata (only when it is resolvable) ----------------
        pkg_config = shutil.which("pkg-config")
        if not pkg_config:
            print("skip pkg-config check: pkg-config is not available")
        else:
            result = run([pkg_config, "--variable=doctooldir", "mm-common-util"])
            doctooldir = result.stdout.strip()
            if result.returncode != 0 or not doctooldir:
                print("skip pkg-config check: mm-common-util is not visible to pkg-config")
            else:
                check(os.path.isfile(os.path.join(doctooldir, "doxygen.css")),
                      f"pkg-config doctooldir resolves inside the package: {doctooldir}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("failures:")
        for message in failures:
            print("  - " + message)
        sys.exit(1)
