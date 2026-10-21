#!/usr/bin/env python3
"""Conan test_package for typometer 1.0.1 — consumer test of the packaged uber-JAR.

typometer is a Java/Swing application (not a linkable C/C++ library), so the
consumer test compiles and runs TestTypometer.java against the packaged JAR.
The Java program (test_package/TestTypometer.java) asserts:

  1. the packaged entry point (com.pavelfatin.typometer.Application) loads,
  2. the core Metrics class loads,
  3. the upstream reference images load,
  4. Metrics.detect() returns a result for those images (real algorithm call),
  5. detected cursor step / line length are sane,
  6. ScreenAccessor.isHarmonyOS() detects the HarmonyOS platform.
  7. [OHOS-only, --require-harmonyos] isHarmonyOS() == true and
     isNativeApiSupported() == false, i.e. the portability patch prevents the
     Linux X11 native backend from being selected on HarmonyOS.

File location: archives/t/typometer/1.0.1/test_package/conanfile.py
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class TypometerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _java_home(self):
        for candidate in [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/usr/lib/jvm/bishengjdk-17",
            "/usr/lib/jvm/java-17-openjdk",
            "/usr/lib/jvm/java-17-openjdk-arm64",
        ]:
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "java")):
                return candidate
        return ""

    def test(self):
        pkg = self.dependencies["typometer"].package_folder
        jar = os.path.join(pkg, "libexec", "typometer-1.0.1.jar")
        assert os.path.isfile(jar), f"packaged JAR missing: {jar}"

        java_home = self._java_home()
        assert java_home, "JAVA_HOME not set and no JDK 17 found in common locations"
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + ":" +
                              os.environ.get("PATH", "/usr/bin:/bin"))

        if can_run(self):
            shell = (os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
                     or shutil.which("bash") or "/bin/sh")
            script = os.path.join(self.recipe_folder, "test_typometer.sh")
            cwd = os.environ.get("TMPDIR") or self.recipe_folder
            self.run(f'"{shell}" "{script}" "{pkg}" "{self.settings.os}"',
                     env="conanrun", cwd=cwd)

            if str(self.settings.os) == "OHOS":
                self.output.info(
                    "OHOS-specific check passed: HarmonyOS detected and native X11 "
                    "screen access disabled (portable AWT Robot backend selected)")

            upstream_file = os.path.join(pkg, "libexec", "upstream-test-result.json")
            if os.path.isfile(upstream_file):
                with open(upstream_file, "r", encoding="utf-8") as handle:
                    upstream = json.load(handle)
                print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        else:
            with open(jar, "rb") as handle:
                magic = handle.read(2)
            assert magic == b"PK", f"not a JAR (ZIP) archive: {magic!r}"
            self.output.info(f"typometer JAR exists (cross-build, run skipped): {jar}")
