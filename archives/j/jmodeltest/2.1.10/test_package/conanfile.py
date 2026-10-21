#!/usr/bin/env python3
"""Conan test_package — jmodeltest 2.1.10 (L1 test).

Consumes the packaged ``jmodeltest`` launcher end-to-end on HarmonyOS:
  1. package structure (launcher + jModelTest.jar + vendor libs)
  2. ``jmodeltest -help`` prints usage and exits (JVM + jar + classpath OK)
  3. ``jmodeltest -d <nexus> -getPhylip`` reads the bundled alignment, converts
     it to Phylip and writes ``<input>.phy`` — a real, headless model-test
     data-conversion path that needs no external phyml binary.

This is the L1 test in the five-level test system. CI runs it automatically
via ``conan create`` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class JModelTestTestConan(ConanFile):
    """L1 test for jmodeltest — delegates to test.sh for consumer validation."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _is_jdk(java_home):
        return all(
            os.path.isfile(os.path.join(java_home, "bin", tool))
            for tool in ("java", "jar")
        )

    def _ensure_jdk(self):
        # CI workers have no preinstalled JDK: the host build() downloads
        # bishengjdk into its own (ephemeral) build folder, which is gone by
        # test time. Fall back to downloading it here (aladin pattern), so the
        # launcher and test.sh can locate java/jar.
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/usr/local/bishengjdk17",
            "/data/service/hnp/bishengjdk17",
        ]
        for candidate in candidates:
            if candidate and self._is_jdk(candidate):
                return candidate

        jdk_dir = os.path.join(self.build_folder, "bishengjdk17")
        os.makedirs(jdk_dir, exist_ok=True)
        get(
            self,
            url=(
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                "download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz"
            ),
            destination=jdk_dir,
        )
        candidates = [jdk_dir]
        candidates.extend(
            os.path.join(jdk_dir, entry)
            for entry in os.listdir(jdk_dir)
            if os.path.isdir(os.path.join(jdk_dir, entry))
        )
        for candidate in candidates:
            if self._is_jdk(candidate):
                return candidate
        raise ConanException(
            f"BiShengJDK 17 was downloaded but not found under {jdk_dir}"
        )

    def test(self):
        # Ensure a JDK is available for the wrapper and test.sh (bishengjdk 17+).
        java_home = self._ensure_jdk()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        # Locate the installed jmodeltest launcher.
        jmt_bin = os.path.join(
            self.dependencies["jmodeltest"].package_folder, "bin", "jmodeltest"
        )
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{jmt_bin}" "{self.build_folder}"',
                 env="conanrun")