#!/usr/bin/env python3
"""Conan test_package — sqlsmith 1.5 CLI executable verification.

sqlsmith is an executable (a random SQL query generator), not a library. This
consumer test runs the installed `sqlsmith` binary in the conanrun environment
(so its shared libpq dependency resolves) and checks --version / --help, then
emits the HMBS_UPSTREAM_TEST_RESULT (no_tests) and HMBS_TEST_PACKAGE_RESULT
hard-gate markers with counts taken from the real test.sh output.
"""
import json
import os

from conan import ConanFile


class SqlsmithTestConan(ConanFile):
    """Consumer test for the sqlsmith CLI executable."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # sqlsmith 1.5 has no upstream automated test suite: it is a random SQL
        # generator that needs a live RDBMS to produce queries, and the source
        # / build files contain no test entrypoint (see test_package/MANIFEST.yml
        # upstream_test_audit for the full evidence). Report no_tests honestly.
        upstream_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (sqlsmith 1.5 has no upstream test entrypoint)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "sqlsmith-1.5 archive contains only the sqlsmith CLI sources, "
                "README.org, CMakeLists.txt, Makefile.am and configure.ac; "
                "there is no tests/ directory, no add_test/enable_testing "
                "usage, no check_PROGRAMS/TESTS variable in Makefile.am, no "
                "make check target, and no ctest list. The only 'test' is a "
                "GitHub Actions job that runs the built binary with "
                "--max-queries=100 against a live PostgreSQL via pg_virtualenv, "
                "which cannot run without a database server. Consumer coverage "
                "is provided by test_package running the installed binary "
                "(--version / --help)."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result, ensure_ascii=False)
        )

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_cmd = f"{bash} test.sh"
        log = os.path.join(self.build_folder, "test_package.log")
        os.makedirs(self.build_folder, exist_ok=True)
        self.run(
            f"{test_cmd} > {log} 2>&1",
            env="conanrun",
            ignore_errors=True,
        )
        out = ""
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        # test.sh emits exactly one "TEST PASS:" marker per check (2 checks:
        # --version and --help). The count is taken from the real harness
        # output, not hardcoded.
        passed_count = out.count("TEST PASS:")
        discovered = 2
        passed = passed_count == discovered
        test_pkg = {
            "executed": True,
            "passed": passed,
            "command": test_cmd,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
        )
        if not passed:
            raise RuntimeError(
                f"sqlsmith smoke test failed: passedCount={passed_count}/{discovered}"
            )
