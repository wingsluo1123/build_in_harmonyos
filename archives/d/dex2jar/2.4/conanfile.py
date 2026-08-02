#!/usr/bin/env python3
"""Conan recipe — dex2jar 2.4 (JVM tool).

Tools to convert Android .dex files to .class files (JAR).
Build system: Gradle. OHOS 下需要 JDK + Gradle 兼容处理（参照 ktfmt 先例）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class Dex2JarConan(ConanFile):
    name = "dex2jar"
    version = "2.4"
    license = "Apache-2.0"
    url = "https://github.com/pxb1988/dex2jar"
    description = "Tools to convert Android .dex files to .class files (JAR)"
    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "build"
        self.folders.source = "."

    def source(self):
        # Pass sha256 for supply-chain integrity verification (R39)
        src_data = self.conan_data["sources"][self.version]
        get(self, src_data["url"], sha256=src_data["sha256"], strip_root=True)
        apply_conandata_patches(self)

    def _ensure_java(self):
        """Locate a usable JDK (bishengjdk) on the OHOS CI worker."""
        import shutil
        java = shutil.which("java")
        if java:
            java_home = os.path.dirname(os.path.dirname(java))
            if os.path.isdir(java_home):
                return java_home
        # Fallback: common install location used by install-jdk.sh
        for home in (
            os.path.expanduser("~/usr/local/jdk-17"),
            "/data/service/hnp/jdk-17",
        ):
            if os.path.isdir(home):
                return home
        raise ConanException(
            "dex2jar requires a JDK on OHOS; run install-jdk.sh first "
            "(see cmd-pkgs releases: install-jdk.sh -- 17.0.13)"
        )

    def build(self):
        apply_conandata_patches(self)

        # Ensure bishengjdk 17 is available (CI workers may not have it)
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")
        os.environ["GRADLE_OPTS"] = "-Xmx512m -Dos.name=Linux"
        # Gradle forks a daemon JVM that reads os.name from the actual system
        # (HarmonyOS) -> ExceptionInInitializerError. JAVA_TOOL_OPTIONS is
        # picked up by ALL JVM processes, overriding os.name to Linux.
        os.environ["JAVA_TOOL_OPTIONS"] = "-Dos.name=Linux"
        gradle_user_home = os.environ.get("GRADLE_USER_HOME") or os.path.expanduser("~/.gradle")
        os.environ["GRADLE_USER_HOME"] = gradle_user_home

        # Alias HarmonyOS as Linux for Gradle's OperatingSystem class
        gradle_props = os.path.join(self.source_folder, "gradle.properties")
        if os.path.isfile(gradle_props):
            with open(gradle_props, "a") as f:
                f.write("\norg.gradle.jvmargs=-Xmx512m -Dos.name=Linux\n")

        # Use system gradle if available, else gradlew wrapper JAR directly
        gradle_cmd = None
        for candidate in (
            os.path.expanduser("~/usr/local/bin/gradle"),
            "/usr/local/bin/gradle",
            "gradle",
        ):
            if os.path.isfile(candidate) or candidate == "gradle":
                if candidate == "gradle" and not self._which("gradle"):
                    continue
                gradle_cmd = candidate
                break

        if gradle_cmd:
            self.run(f'"{gradle_cmd}" clean distZip --no-daemon -Dorg.gradle.daemon=false',
                     cwd=self.source_folder)
        else:
            wrapper_jar = os.path.join(self.source_folder, "gradle", "wrapper", "gradle-wrapper.jar")
            if os.path.isfile(wrapper_jar):
                self.run(f'"{os.path.join(java_home, "bin", "java")}" -jar "{wrapper_jar}" '
                         f'clean distZip --no-daemon -Dorg.gradle.daemon=false',
                         cwd=self.source_folder)
            else:
                raise ConanException("No gradle binary or wrapper found for dex2jar build")

    @staticmethod
    def _which(cmd):
        import shutil
        return shutil.which(cmd)

    def package(self):
        # distZip produces build/distributions/dex2jar-<version>.zip
        dist_name = f"dex2jar-{self.version}"
        zip_path = os.path.join(self.source_folder, "build", "distributions", f"{dist_name}.zip")

        if not os.path.exists(zip_path):
            raise ConanException(f"Expected distribution zip not found: {zip_path}")

        # Extract the zip into the source folder
        self.run(f'cd "{self.source_folder}" && unzip -o "{zip_path}"')
        extract_dir = os.path.join(self.source_folder, dist_name)

        # Copy bin/ and lib/ into the package folder
        copy(self, "*", src=os.path.join(extract_dir, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.jar", src=os.path.join(extract_dir, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.buildenv_info.define("DEX2JAR_HOME", self.package_folder)
        self.runenv_info.define("DEX2JAR_HOME", self.package_folder)
        self.cpp_info.bindirs = ["bin"]
