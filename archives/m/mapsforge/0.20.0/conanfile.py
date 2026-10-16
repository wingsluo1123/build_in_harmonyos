#!/usr/bin/env python3
"""Conan recipe — mapsforge 0.20.0 (JVM library, Gradle multi-module build).

mapsforge is a Java library for rendering / reading / writing OpenStreetMap
binary vector maps. Upstream is a Gradle multi-module project (13 modules).

HarmonyOS PC has no Android SDK, so the three Android-only Gradle modules
(mapsforge-map-android / mapsforge-poi-android / mapsforge-samples-android)
are excluded by patch, together with the Android-only `google()` Maven
repository (which is unreachable from the OHOS build network and would abort
dependency resolution). The ten remaining desktop/JVM modules are built with
Gradle and packaged as JARs.

R32: validate() accepts settings.os in ("Linux", "OHOS")
R34: test_package compiles and runs a real Java program against the packaged JARs
R38: library package (no commands.json needed)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MapsforgeConan(ConanFile):
    name = "mapsforge"
    version = "0.20.0"
    description = ("mapsforge — OpenStreetMap binary vector map rendering / "
                   "reading library (pure Java, Gradle multi-module)")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/mapsforge/mapsforge"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    # `compiler`/`build_type` are declared because the OHOS CI gate (L0p)
    # requires all four settings; they are not used (the packaged artifact is a
    # set of platform-independent JARs). `shared` satisfies the library
    # package_type contract only.
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mapsforge does not support OS: {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # No Conan requirements. Every third-party Java dependency of mapsforge
        # is a Maven coordinate (kxml2, svgSalamander, guava, trove4j, jts-core,
        # osmosis-core, sqlite-jdbc, activation, jaxb-runtime, junit, ...) and is
        # resolved by Gradle from Maven Central during build().
        pass

    def build_requirements(self):
        # Gradle is provided by the ohpcd prebuilt package (published artifact),
        # so the build is reproducible without a system Gradle install.
        self.tool_requires("gradle/8.12")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # JDK bootstrap (same policy as archives/v/vecmath/1.5.2)            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_java_home(java_home):
        java_home = os.path.abspath(os.path.expanduser(java_home))
        java = os.path.join(java_home, "bin", "java")
        javac = os.path.join(java_home, "bin", "javac")
        if not os.path.isfile(java) or not os.path.isfile(javac):
            return None
        return java_home

    def _find_java_home(self):
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]
        java = shutil.which("java")
        if java:
            candidates.append(os.path.dirname(os.path.dirname(os.path.realpath(java))))
        for candidate in candidates:
            if candidate:
                verified = self._validate_java_home(candidate)
                if verified:
                    self.output.info("Using JDK: " + verified)
                    return verified
        return None

    def _ensure_java(self):
        java_home = self._find_java_home()
        if java_home:
            return java_home
        tool = self.conan_data["build_tools"]["bisheng_jdk"]
        installed = os.path.expanduser("~/bishengjdk17")
        self.output.info("Downloading pinned BiSheng JDK " + tool["version"])
        tool_url = "{}://{}{}".format(tool["scheme"], tool["host"], tool["path"])
        os.makedirs(installed, exist_ok=True)
        get(
            self,
            url=tool_url,
            filename=tool["filename"],
            sha256=tool["sha256"],
            destination=installed,
            strip_root=True,
            keep_permissions=True,
        )
        verified = self._validate_java_home(installed)
        if not verified:
            raise ConanInvalidConfiguration(
                "Pinned JDK missing bin/java or bin/javac at " + installed
            )
        return verified

    def build(self):
        apply_conandata_patches(self)
        java_home = self._ensure_java()

        # Keep all build state inside the source folder of the Conan build
        # (R49 spirit: never write to shared prefixes or the user home).
        gradle_user_home = os.path.join(self.source_folder, ".gradle-home")
        os.makedirs(gradle_user_home, exist_ok=True)

        # Gradle needs JAVA_HOME and, on HarmonyOS, os.name overridden for the
        # forked JVM as well (HarmonyOS is not recognised by Gradle's
        # OperatingSystem class).
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + os.pathsep + os.environ.get("PATH", "")
        os.environ["GRADLE_USER_HOME"] = gradle_user_home
        if "-Dos.name=" not in os.environ.get("JAVA_TOOL_OPTIONS", ""):
            os.environ["JAVA_TOOL_OPTIONS"] = (
                os.environ.get("JAVA_TOOL_OPTIONS", "") + " -Dos.name=Linux"
            ).strip()

        self.output.info("JAVA_HOME=" + java_home)
        # `gradle` comes from tool_requires("gradle/8.12"); Conan injects its
        # bindir into the build environment used by self.run(). The project root
        # (settings.gradle) lives in the source folder, not in the build folder.
        self.run(f'gradle -p "{self.source_folder}" clean build --no-daemon --console=plain')

    def package(self):
        for sub in ("COPYING", "COPYING.LESSER"):
            copy(self, sub, self.source_folder,
                 os.path.join(self.package_folder, "licenses"))
        jar_dir = os.path.join(self.package_folder, "lib", "jar")
        for module in sorted(os.listdir(self.source_folder)):
            libs = os.path.join(self.source_folder, module, "build", "libs")
            if os.path.isdir(libs):
                copy(self, "*.jar", libs, jar_dir)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        jar_dir = os.path.join(self.package_folder, "lib", "jar")
        jars = sorted(
            os.path.join(jar_dir, f) for f in os.listdir(jar_dir)
        ) if os.path.isdir(jar_dir) else []
        classpath = os.pathsep.join(jars)
        for info in (self.buildenv_info, self.runenv_info):
            info.define_path("MAPSFORGE_JAR_DIR", jar_dir)
            info.define("MAPSFORGE_CLASSPATH", classpath)
