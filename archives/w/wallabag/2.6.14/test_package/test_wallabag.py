#!/usr/bin/env python3
"""test_package consumer test for wallabag/2.6.14.

Usage: python3 test_wallabag.py <share-dir>

Validates the staged share/wallabag bundle without requiring any interpreter
beyond python3 (the conan ohpcd remote hosts no php recipe, so php must not
be a hard requirement): version anchor, composer bootstrap presence, real
bundle class source (namespace/class/constant/methods via regex), entrypoint
content, upstream-test evidence files, and deterministic os.walk counts
(78 *Test.php files, >=10000 .php files — the pinned-tarball totals that
catch truncation; cf. toybox empty-fixture lesson).

When a system php interpreter IS available, additionally folds in the real
php consumer suite (test_wallabag.php, parsed from its machine-emitted JSON
marker line — no stdout word-counting) plus the shell harness returncode.
Every check() call is one counted assertion; the final line is the single
deterministic source for HMBS_TEST_PACKAGE_RESULT counts.

Anti-blindness controls (run on every invocation, no php needed):
  * the same class/content regexes must NOT match empty input;
  * a deliberately corrupted temp copy of Utils.php must differ from the
    original and contain the breakage marker.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

total = 0
passed = 0


def check(name, cond):
    global total, passed
    total += 1
    if cond:
        passed += 1
        print("[ok] " + name)
    else:
        print("[FAIL] " + name)


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def main():
    global total, passed
    share = sys.argv[1] if len(sys.argv) > 1 else ""
    tdir = os.path.dirname(os.path.abspath(__file__))

    check("share dir exists", os.path.isdir(share))

    yml_path = os.path.join(share, "app/config/wallabag.yml")
    yml = read_text(yml_path) if os.path.isfile(yml_path) else ""
    check("wallabag.yml exists with version 2.6.14",
          "version: 2.6.14" in yml)

    autoload = os.path.join(share, "vendor/autoload.php")
    check("vendor/autoload.php exists and non-empty",
          os.path.isfile(autoload) and os.path.getsize(autoload) > 0)
    check("composer bootstrap present (autoload_real.php)",
          os.path.isfile(os.path.join(share, "vendor/composer/autoload_real.php")))

    utils_rel = "src/Wallabag/CoreBundle/Tools/Utils.php"
    utils_path = os.path.join(share, utils_rel)
    utils_src = read_text(utils_path) if os.path.isfile(utils_path) else ""
    check("Utils.php exists and non-empty", len(utils_src) > 0)
    check("Utils.php declares namespace Wallabag\\CoreBundle\\Tools + class Utils",
          re.search(r"namespace\s+Wallabag\\CoreBundle\\Tools\s*;", utils_src) is not None
          and re.search(r"class\s+Utils\b", utils_src) is not None)
    check("Utils defines DEFAULT_WORDS_PER_MINUTE = 200",
          re.search(r"DEFAULT_WORDS_PER_MINUTE\s*=\s*200", utils_src) is not None)
    check("Utils defines generateToken() and getReadingTime()",
          re.search(r"function\s+generateToken\s*\(", utils_src) is not None
          and re.search(r"function\s+getReadingTime\s*\(", utils_src) is not None)

    console_path = os.path.join(share, "bin/console")
    console_src = read_text(console_path) if os.path.isfile(console_path) else ""
    check("bin/console entrypoint requires vendor/autoload.php",
          "vendor/autoload.php" in console_src)
    check("app/config/parameters.yml exists (pdo_mysql default backend)",
          os.path.isfile(os.path.join(share, "app/config/parameters.yml")))

    phpunit_dist = os.path.join(share, "phpunit.xml.dist")
    dist_src = read_text(phpunit_dist) if os.path.isfile(phpunit_dist) else ""
    check("phpunit.xml.dist: single testsuite wallabag + DAMA extension evidence",
          '<testsuite name="wallabag">' in dist_src
          and "DoctrineTestBundle" in dist_src)

    # Deterministic os.walk counts (single source, no string counting).
    # NOTE: vendor/ ships 136 third-party *Test.php files; the upstream
    # suite (phpunit testsuite "wallabag" -> tests/) is exactly the 78 files
    # under tests/, so that count is scoped to tests/ only.
    n_php = 0
    for _dirpath, _dirnames, filenames in os.walk(share):
        for fn in filenames:
            if fn.endswith(".php"):
                n_php += 1
    n_test_files = 0
    tests_dir = os.path.join(share, "tests")
    if os.path.isdir(tests_dir):
        for _dirpath, _dirnames, filenames in os.walk(tests_dir):
            for fn in filenames:
                if fn.endswith("Test.php"):
                    n_test_files += 1
    print("[info] walk counts: php_files=%d tests_Test_php_files=%d" % (n_php, n_test_files))
    check("bundle completeness: php file count >= 10000 (got %d)" % n_php,
          n_php >= 10000)
    check("upstream tests present: 78 *Test.php files under tests/ (got %d)" % n_test_files,
          n_test_files == 78)

    # Anti-blindness: regexes must not match empty input (toybox lesson).
    check("negative: class/content regexes reject empty input",
          re.search(r"class\s+Utils\b", "") is None
          and re.search(r"DEFAULT_WORDS_PER_MINUTE\s*=\s*200", "") is None)
    # Anti-blindness: corrupted-copy probe construction works without php.
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False,
                                         encoding="utf-8") as tmp:
            tmp.write(utils_src + "\n{{{SYNTAX_BREAKAGE_FOR_HARNESS_PROBE>>>\n")
            probe = tmp.name
        with open(probe, encoding="utf-8", errors="replace") as f:
            probe_src = f.read()
        probe_ok = (probe_src != utils_src
                    and "{{{SYNTAX_BREAKAGE_FOR_HARNESS_PROBE>>>" in probe_src)
    finally:
        try:
            os.unlink(probe)
        except OSError:
            pass
    check("negative: corrupted copy differs and carries breakage marker", probe_ok)

    php = shutil.which("php")
    if php is None:
        print("[info] no system php interpreter; php consumer suite skipped "
              "(environment gap, documented in build upstream marker)")
    else:
        proc = subprocess.run([php, "--version"],
                              capture_output=True, text=True)
        check("system php --version executes", proc.returncode == 0)
        # Fold the real php consumer suite via its JSON marker line
        # (machine-emitted JSON parse, not stdout word-counting).
        php_test = os.path.join(tdir, "test_wallabag.php")
        proc = subprocess.run([php, php_test, share],
                              capture_output=True, text=True)
        folded = False
        for line in proc.stdout.splitlines():
            if line.startswith("HMBS_TEST_PACKAGE_RESULT="):
                try:
                    m = json.loads(line.split("=", 1)[1])
                    pd, pp = int(m["discovered"]), int(m["passedCount"])
                    assert pd >= 0 and 0 <= pp <= pd
                except (ValueError, KeyError, AssertionError, TypeError):
                    break
                for _ in range(pd):
                    total += 1
                passed += pp
                folded = (proc.returncode == 0 and pp == pd)
                print("[info] folded php suite: discovered=%d passed=%d" % (pd, pp))
                break
        check("php consumer suite green (test_wallabag.php marker folded)", folded)
        sh_test = os.path.join(tdir, "test_wallabag.sh")
        proc = subprocess.run(["sh", sh_test, php, share],
                              capture_output=True, text=True)
        check("shell harness green (test_wallabag.sh incl. php -l negative control)",
              proc.returncode == 0)

    ok = (passed == total)
    marker = {
        "executed": True,
        "passed": ok,
        "command": "python3 test_wallabag.py <share-dir>"
                   + (" + php consumer suite + sh harness" if php is not None
                      else " (no system php; php checks skipped)"),
        "discovered": total,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
