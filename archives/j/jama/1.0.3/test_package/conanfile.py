#!/usr/bin/env python3
"""Conan test_package — jama 1.0.3 (Conan L1 consumer test on HarmonyOS PC).

* ``test.sh`` compiles and runs ``TestJama.java`` against the packaged
  ``libexec/jama-1.0.3.jar``: numeric assertions on the real JAMA API
  (Matrix / LU / QR / Cholesky / SVD / eigen, R34) plus the HarmonyOS consumer
  cases OHOS-1..OHOS-4 (HarmonyOS aarch64 JVM, Conan layout discovery, real
  file I/O without a writable ``/tmp``, platform-neutral bytecode).
* Afterwards the ``HMBS_UPSTREAM_TEST_RESULT`` marker is re-emitted from
  ``share/jama/upstream_test_result.json`` — the result of the *upstream*
  ``Jama.test.TestMatrix`` suite that the recipe ran inside ``build()``.
  Re-emitting it from the package keeps the marker present on cached runs
  (``conan create`` skips ``build()`` when the binary already exists).

Upstream suite: see test_package/MANIFEST.yml.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class JamaTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    # Same pinned toolchain the recipe uses (see conandata.yml build_tools).
    _JDK_URL = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                "releases/download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz")
    _JDK_SHA256 = "ce074909ff5c13e7e7675eb243ee15424f0343610312c526552a1a08d199e28f"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _is_jdk(java_home):
        return bool(java_home) and all(
            os.path.isfile(os.path.join(java_home, "bin", tool))
            for tool in ("java", "javac", "jar")
        )

    def _ensure_jdk(self):
        """Reuse the platform JDK (build() installs the pinned one into
        ``~/bishengjdk17``), downloading it only when the worker has none."""
        for candidate in (os.environ.get("JAVA_HOME", ""),
                          os.path.expanduser("~/bishengjdk17"),
                          os.path.expanduser("~/usr/local/bishengjdk17"),
                          "/usr/local/bishengjdk17",
                          "/data/service/hnp/bishengjdk17"):
            if self._is_jdk(candidate):
                return os.path.abspath(os.path.expanduser(candidate))

        jdk_dir = os.path.join(self.build_folder, "bishengjdk17")
        os.makedirs(jdk_dir, exist_ok=True)
        self.output.info("No JDK found — downloading pinned BiSheng JDK 17.0.13")
        get(self, url=self._JDK_URL,
            filename="bishengjdk-17.0.13-ohos-aarch64.tar.gz",
            sha256=self._JDK_SHA256, destination=jdk_dir,
            strip_root=True, keep_permissions=True)
        candidates = [jdk_dir]
        candidates.extend(
            os.path.join(jdk_dir, entry) for entry in sorted(os.listdir(jdk_dir))
            if os.path.isdir(os.path.join(jdk_dir, entry)))
        for candidate in candidates:
            if self._is_jdk(candidate):
                return candidate
        raise ConanException(
            f"BiSheng JDK downloaded but no JDK layout found under {jdk_dir}")

    @staticmethod
    def _find_bash():
        for candidate in (os.environ.get("CONFIG_SHELL", ""),
                          shutil.which("bash") or "",
                          "/data/service/hnp/bin/bash",
                          "/bin/bash", "/usr/bin/bash"):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def test(self):
        dep = self.dependencies["jama"]
        pkg_folder = dep.package_folder
        self.output.info(f"Testing package in: {pkg_folder}")

        # Locate the packaged JAR by scanning the Conan package layout — do NOT
        # rebuild its name from ``self.tested_reference_str``.  ``conan create``
        # without a user/channel (which is what CI and ``ci/conan/upload.sh``
        # use) hands the test_package a *timed* reference of the form
        # ``jama/1.0.3#<recipe-revision>%<timestamp>``; splitting on ``"@"``
        # only strips that suffix for ``@user/channel`` refs, so the revision
        # and timestamp leaked into the file name and the JAR was not found
        # (``libexec/jama-1.0.3#1fad…%1791976421.2002232.jar``).
        libexec = os.path.join(pkg_folder, "libexec")
        jars = sorted(
            name for name in os.listdir(libexec)
            if name.startswith("jama-") and name.endswith(".jar")
        ) if os.path.isdir(libexec) else []
        if len(jars) != 1:
            raise ConanException(
                "expected exactly one 'jama-*.jar' under "
                f"{libexec}, found {jars}")
        jar = os.path.join(libexec, jars[0])

        # Cross-check the layout against the version actually under test
        # (the reference's version, sanitised against the same rev/timestamp
        # suffix for robustness).
        version = str(dep.ref.version).split("#", 1)[0].split("%", 1)[0]
        if version not in jars[0]:
            raise ConanException(
                f"packaged JAR {jars[0]} does not carry the version under "
                f"test ({version})")
        self.output.info(f"Consuming packaged JAR: {jars[0]}")

        jdk = self._ensure_jdk()
        bash = self._find_bash()
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'JAVA_HOME="{jdk}" "{bash}" "{script}" "{jar}"')

        # Re-emit the upstream marker from the packaged evidence so the gate
        # always sees it, including on cached (build-skipping) runs.
        result_path = os.path.join(pkg_folder, "share", "jama",
                                   "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json missing from the package "
                f"({result_path}) — the upstream suite did not run in build(); "
                "refusing to report success silently")
        with open(result_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        print("HMBS_UPSTREAM_TEST_RESULT="
              + json.dumps(upstream, ensure_ascii=False), flush=True)
