#!/usr/bin/env python3
"""Conan recipe — jama 1.0.3 (JAMA: A Java Matrix Package).

Downloads the official NIST release tarball, compiles the pure-Java sources
with ``javac``, runs the upstream ``Jama.test.TestMatrix`` suite inside
``build()``, and packages ``jama-1.0.3.jar``.

* Source: https://math.nist.gov/javanumerics/jama/Jama-1.0.3.tar.gz
  (sha256 pinned in conandata.yml; Public Domain — NIST / The MathWorks)
* Build system: plain ``javac`` + ``jar``.  The 1.0.3 release ships no build
  script at all (no Makefile / pom.xml / build.xml, no README, no LICENSE),
  so the official way to build it is bare ``javac``; Debian's
  ``debian/build.xml`` only wraps the same two steps in Ant.
* Upstream tests: ``test/TestMatrix.java`` — one self-contained ``main()``
  with 6 sections (constructors / access / array-like / I-O / linear algebra /
  eigenvalue); executed in ``build()``, 74 checks, 0 failures, 0 warnings.
  The result is persisted into the package as
  ``share/jama/upstream_test_result.json`` so ``test_package`` can re-emit the
  ``HMBS_UPSTREAM_TEST_RESULT`` marker even on cached (build-skipping) runs.
* Artifact: ``libexec/jama-1.0.3.jar`` (platform-independent bytecode),
  published to consumers as ``JAMA_JAR`` through ``buildenv_info``.

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R33: the JDK is resolved to absolute paths — build() never relies on bare
     ${CC}/${CFLAGS}-style shell variables
R34: test_package calls the real JAMA API (Matrix / LU / QR / Cholesky / SVD /
     eigen), plus HarmonyOS consumer checks
R38: library package (JAR only, no bindirs) — no commands.json
R51: the upstream suite is counted, actually executed and reported
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

# Public classes of the 1.0.3 release (6 top level + util/Maths).  The tarball
# is sha256-pinned, so this list is exact: it documents the library surface and
# makes a silent change of the archive fail loudly instead of shipping a
# partially compiled JAR.
_LIBRARY_SOURCES = (
    "CholeskyDecomposition.java",
    "EigenvalueDecomposition.java",
    "LUDecomposition.java",
    "Matrix.java",
    "QRDecomposition.java",
    "SingularValueDecomposition.java",
    "util/Maths.java",
)

# Upstream code that is not part of the library (mirrors the <exclude> list of
# Debian's debian/build.xml): test/ holds the upstream suite, examples/ the
# MagicSquare demo.
_NON_LIBRARY_DIRS = ("test", "examples")

_UPSTREAM_MAIN = "Jama.test.TestMatrix"
_UPSTREAM_LOG = "upstream-test.log"
_UPSTREAM_RESULT = "upstream_test_result.json"


class JamaConan(ConanFile):
    name = "jama"
    version = "1.0.3"
    description = ("JAMA: A Java Matrix Package — LU/QR/Cholesky/SVD "
                   "decompositions and symmetric/general eigenproblems")
    license = "LicenseRef-Public-Domain"
    homepage = "https://math.nist.gov/javanumerics/jama/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS and its build host Linux, never an equality test on "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jama does not support OS: {self.settings.os}")

    def source(self):
        # The tarball has a single root directory (Jama/), so strip_root=True
        # leaves ChangeLog / *.java / test/ / examples/ directly in the
        # source folder.
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── JDK discovery / bootstrap ──────────────────────────────────────────
    @staticmethod
    def _is_jdk(java_home):
        return bool(java_home) and all(
            os.path.isfile(os.path.join(java_home, "bin", tool))
            for tool in ("java", "javac", "jar")
        )

    def _find_java_home(self):
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk"),
        ]
        on_path = shutil.which("java")
        if on_path:
            candidates.append(
                os.path.dirname(os.path.dirname(os.path.realpath(on_path))))
        for candidate in candidates:
            if candidate and self._is_jdk(candidate):
                home = os.path.abspath(os.path.expanduser(candidate))
                self.output.info("Using JDK: " + home)
                return home
        return None

    def _ensure_java(self):
        """Reuse the platform BiSheng JDK, installing the pinned one when the
        worker does not provide a JDK at all."""
        java_home = self._find_java_home()
        if java_home:
            return java_home

        tool = self.conan_data["build_tools"]["bisheng_jdk"]
        installed = os.path.expanduser("~/bishengjdk17")
        # Installed to the canonical home so the downstream test_package()
        # process discovers the very same JDK.
        self.output.info("No JDK found — downloading pinned BiSheng JDK "
                         + tool["version"])
        tool_url = "{}://{}{}".format(tool["scheme"], tool["host"], tool["path"])
        os.makedirs(installed, exist_ok=True)
        get(self, url=tool_url, filename=tool["filename"],
            sha256=tool["sha256"], destination=installed,
            strip_root=True, keep_permissions=True)
        if not self._is_jdk(installed):
            raise ConanInvalidConfiguration(
                "pinned BiSheng JDK has no bin/{java,javac,jar} at " + installed)
        return installed

    # ── build ──────────────────────────────────────────────────────────────
    def _library_sources(self):
        found = []
        for root, dirs, files in os.walk(self.source_folder):
            relative_root = os.path.relpath(root, self.source_folder)
            parts = [] if relative_root == "." else relative_root.split(os.sep)
            if parts and parts[0] in _NON_LIBRARY_DIRS:
                dirs[:] = []
                continue
            for name in files:
                if name.endswith(".java"):
                    found.append(
                        os.path.relpath(os.path.join(root, name),
                                        self.source_folder).replace(os.sep, "/"))
        found.sort()
        missing = [src for src in _LIBRARY_SOURCES if src not in found]
        unexpected = [src for src in found if src not in _LIBRARY_SOURCES]
        if missing or unexpected:
            raise ConanInvalidConfiguration(
                "jama 1.0.3 source tree does not match the audited library "
                "surface (missing={}, unexpected={})".format(missing, unexpected))
        return [os.path.join(self.source_folder, src.replace("/", os.sep))
                for src in _LIBRARY_SOURCES]

    def build(self):
        apply_conandata_patches(self)

        java_home = self._ensure_java()
        javac = os.path.join(java_home, "bin", "javac")
        jar = os.path.join(java_home, "bin", "jar")
        java = os.path.join(java_home, "bin", "java")

        classes = os.path.join(self.build_folder, "classes")
        os.makedirs(classes, exist_ok=True)

        sources = self._library_sources()
        sources_list = os.path.join(self.build_folder, "library-sources.list")
        with open(sources_list, "w", encoding="utf-8") as handle:
            handle.write("\n".join(sources) + "\n")

        self.output.info(f"Compiling {len(sources)} upstream sources with {javac}")
        self.run(f'"{javac}" -encoding UTF-8 -d "{classes}" @"{sources_list}"')

        output = os.path.join(self.build_folder, f"jama-{self.version}.jar")
        self.run(f'"{jar}" cf "{output}" -C "{classes}" .')
        self.output.info("Built " + output)

        marker = self._run_upstream_tests(javac, java, classes)

        # Persisted so test_package can re-emit the marker on cached runs
        # (`conan create` skips build() when the binary is already installed).
        result_path = os.path.join(self.build_folder, _UPSTREAM_RESULT)
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump(marker, handle, ensure_ascii=False)
        self.output.info("Persisted upstream test result to " + result_path)

    def _run_upstream_tests(self, javac, java, classes):
        """Compile and run the upstream ``Jama.test.TestMatrix`` suite.

        The suite is a single ``main()`` that walks six sections and prints one
        ``>    <name>... success`` / ``*** failure ***`` / ``*** warning ***``
        line per check, closed by ``TestMatrix completed.`` plus
        ``Total errors reported: N``.  Counts below are parsed from that real
        output, never hard coded.
        """
        test_source = os.path.join(self.source_folder, "test", "TestMatrix.java")
        if not os.path.isfile(test_source):
            raise ConanInvalidConfiguration(
                "upstream test suite missing from the source tree: " + test_source)

        test_classes = os.path.join(self.build_folder, "test-classes")
        os.makedirs(test_classes, exist_ok=True)
        self.run(f'"{javac}" -encoding UTF-8 -cp "{classes}" '
                 f'-d "{test_classes}" "{test_source}"')

        # TestMatrix writes JamaTestMatrix.out and TMPMATRIX.serial into the
        # process working directory, so give it a dedicated scratch folder.
        run_dir = os.path.join(self.build_folder, "upstream-test-run")
        os.makedirs(run_dir, exist_ok=True)
        classpath = os.pathsep.join([classes, test_classes])
        command = [java, "-cp", classpath, _UPSTREAM_MAIN]

        result = subprocess.run(command, cwd=run_dir, capture_output=True,
                                text=True, timeout=3600)
        output = (result.stdout or "") + (result.stderr or "")
        log_path = os.path.join(run_dir, _UPSTREAM_LOG)
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write("$ " + " ".join(command) + "\n")
            handle.write(f"# cwd={run_dir}\n")
            handle.write(output)
            handle.write(f"\n[EXIT CODE] {result.returncode}\n")
        self.output.info("Upstream test log: " + log_path)

        passed = len(re.findall(r"^>    .*success\s*$", output, re.M))
        failed = len(re.findall(r"^>    .*\*\*\* failure \*\*\*\s*$", output, re.M))
        warnings = len(re.findall(r"^>    .*\*\*\* warning \*\*\*\s*$", output, re.M))
        errors_match = re.search(r"Total errors reported:\s*(\d+)", output)
        errors = int(errors_match.group(1)) if errors_match else -1
        completed = "TestMatrix completed." in output

        status = "passed" if (completed and errors == 0 and failed == 0
                              and result.returncode == 0) else "failed"
        marker = {
            "status": status,
            "framework": "custom (Jama.test.TestMatrix)",
            "command": " ".join(command),
            "discovered": passed + failed + warnings,
            "executed": passed + failed + warnings,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("Upstream TestMatrix: passed={} failed={} warnings={} "
                         "errors_reported={} log={}".format(
                             passed, failed, warnings, errors, log_path))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))

        if status != "passed":
            raise ConanException(
                "upstream test suite did not pass (exit={}, errors_reported={}, "
                "failed={}) — see {}".format(result.returncode, errors, failed,
                                             log_path))
        return marker

    # ── package ────────────────────────────────────────────────────────────
    def package(self):
        copy(self, f"jama-{self.version}.jar", self.build_folder,
             os.path.join(self.package_folder, "libexec"), keep_path=False)
        # Upstream ships no LICENSE file (public domain); the ChangeLog is the
        # upstream release record, kept as provenance.
        copy(self, "ChangeLog", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, _UPSTREAM_RESULT, self.build_folder,
             os.path.join(self.package_folder, "share", "jama"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # Expose the JAR so consumers (notably test_package) locate it through
        # the Conan package layout instead of guessing paths.
        self.buildenv_info.define_path(
            "JAMA_JAR",
            os.path.join(self.package_folder, "libexec",
                         f"jama-{self.version}.jar"),
        )
