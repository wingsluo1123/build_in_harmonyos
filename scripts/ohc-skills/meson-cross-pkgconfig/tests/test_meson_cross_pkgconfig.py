#!/usr/bin/env python3
"""meson-cross-pkgconfig guard — 单元测试.

覆盖：L1 日志六特征逐条命中 / L2 配方三反模式逐条命中 / L3 环境钉源检测 /
JSON 报告完整性 / SIGPIPE 防护（-o 文件输出）。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "..", "scripts", "meson_cross_pkgconfig_guard.py")


def run_guard(*argv):
    proc = subprocess.run([sys.executable, GUARD, *argv],
                          capture_output=True, text=True, timeout=60)
    return proc


class TestLogSignatures(unittest.TestCase):
    CASES = [
        ('ERROR: Unknown option: "shared"', "meson-no-shared-option"),
        ("meson setup: error: argument --default-library: invalid choice:"
         " 'false'", "meson-default-library-choice"),
        ("Package lv2 was not found in the pkg-config search path.",
         "pkgconfig-pc-missing"),
        ("ld.lld: error: unable to find library -lzix",
         "linker-lib-not-found"),
        ("Error loading shared library liblilv-0.so.0: (needed by ...)",
         "hmdfs-shared-load-fail"),
        ("NotFoundException: Sources for https://x/y.tar.xz not found in "
         "remote backup http://127.0.0.1:8731/",
         "conan-source-backup-block"),
    ]

    def test_each_signature_hits(self):
        for evidence, sig in self.CASES:
            with tempfile.NamedTemporaryFile("w", suffix=".log",
                                             delete=False) as fh:
                fh.write("prefix line\n" + evidence + "\n")
                log = fh.name
            try:
                proc = run_guard("--log", log, "--json")
                hits = json.loads(proc.stdout)["hits"]
                self.assertTrue(
                    any(h["signature"] == sig for h in hits),
                    f"{sig} not hit by evidence: {evidence!r}")
            finally:
                os.unlink(log)

    def test_clean_log_zero_hits(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("meson compile -C build\n[130/130] all ok\n")
            log = fh.name
        try:
            proc = run_guard("--log", log, "--json")
            self.assertEqual(json.loads(proc.stdout)["hit_count"], 0)
        finally:
            os.unlink(log)


class TestRecipeAntiPatterns(unittest.TestCase):
    def test_nested_substitution_hits(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py",
                                         delete=False) as fh:
            fh.write('self.run(f\'{cc} {src} -o {exe} '
                     '"$(PKG_CONFIG_PATH={gen} pkg-config --cflags '
                     '--libs lilv-0)"\')\n')
            recipe = fh.name
        try:
            proc = run_guard("--recipe", recipe, "--json")
            hits = json.loads(proc.stdout)["hits"]
            self.assertTrue(any(
                h["signature"] == "nested-pkgconfig-substitution"
                for h in hits))
        finally:
            os.unlink(recipe)

    def test_dash_d_shared_hits(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py",
                                         delete=False) as fh:
            fh.write('self.run("meson setup build src -Dshared=false")\n')
            recipe = fh.name
        try:
            proc = run_guard("--recipe", recipe, "--json")
            hits = json.loads(proc.stdout)["hits"]
            self.assertTrue(any(h["signature"] == "dash-d-shared-option"
                                for h in hits))
        finally:
            os.unlink(recipe)

    def test_hardcoded_fallback_hits(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py",
                                         delete=False) as fh:
            fh.write('self.run(f"{cc} {src} -o {exe} {flags} -lzix")\n')
            recipe = fh.name
        try:
            proc = run_guard("--recipe", recipe, "--json")
            hits = json.loads(proc.stdout)["hits"]
            self.assertTrue(any(
                h["signature"] == "hardcoded-fallback-lib" for h in hits))
        finally:
            os.unlink(recipe)

    def test_clean_recipe_zero_hits(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py",
                                         delete=False) as fh:
            fh.write('flags_file = os.path.join(bld, "pc-flags.txt")\n'
                     'self.run(f"pkg-config --cflags --libs lilv-0 > '
                     '{flags_file}")\n'
                     'self.run(f"{cc} {src} -o {exe} {flags}")\n')
            recipe = fh.name
        try:
            proc = run_guard("--recipe", recipe, "--json")
            self.assertEqual(json.loads(proc.stdout)["hit_count"], 0)
        finally:
            os.unlink(recipe)


class TestEnvAndOutput(unittest.TestCase):
    def test_pinned_download_urls_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf_dir = os.path.join(tmp, "conan")
            os.makedirs(conf_dir)
            conf = os.path.join(conf_dir, "global.conf")
            with open(conf, "w") as fh:
                fh.write('core.sources:download_urls='
                         '["http://127.0.0.1:8731/"]\n')
            proc = run_guard("--env", "--conan-home", conf_dir, "--json")
            hits = json.loads(proc.stdout)["hits"]
            self.assertTrue(any(
                h["signature"] == "source-download-urls-pinned"
                for h in hits))

    def test_commented_download_urls_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf_dir = os.path.join(tmp, "conan")
            os.makedirs(conf_dir)
            conf = os.path.join(conf_dir, "global.conf")
            with open(conf, "w") as fh:
                fh.write('#core.sources:download_urls='
                         '["http://127.0.0.1:8731/"]\n')
            proc = run_guard("--env", "--conan-home", conf_dir, "--json")
            self.assertEqual(json.loads(proc.stdout)["hit_count"], 0)

    def test_file_output_no_sigpipe(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write('ERROR: Unknown option: "shared"\n')
            log = fh.name
        out = os.path.join(os.path.dirname(log), "report.json")
        try:
            proc = run_guard("--log", log, "--json", "-o", out)
            self.assertIn("report written", proc.stdout)
            with open(out) as fh:
                self.assertEqual(json.load(fh)["hit_count"], 1)
        finally:
            os.unlink(log)
            os.unlink(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
