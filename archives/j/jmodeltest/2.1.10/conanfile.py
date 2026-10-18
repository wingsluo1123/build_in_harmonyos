#!/usr/bin/env python3
"""Conan recipe — jmodeltest 2.1.10 (JVM application, ant source build).

jmodeltest is the reference tool for statistical selection of models of DNA
and protein evolution (ModelTest). The source is an Ant workspace that uses
``javac`` to compile ``src/main/java`` against the vendor jars bundled in
``lib/`` and ``jar`` to assemble ``dist/jModelTest.jar`` (manifest:
``es.uvigo.darwin.jmodeltest.ModelTest``).

Build system: ant (javac + jar, reproduced manually with subprocess, the
aladin pattern — no Gradle/Maven bootstrap needed)
Runtime: bishengjdk 17+ (JVM, system tool, auto-detected like aladin/alloy)
Upstream tests: none (no src/test); consumer validation uses the CLI
``-d <alignment> -getPhylip`` path on the bundled example-data, which runs
fully headless and needs no external phyml binary.
"""
import glob
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class JModelTestConan(ConanFile):
    name = "jmodeltest"
    version = "2.1.10"
    description = "ModelTest statistical selection of models of nucleotide and protein evolution"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ddarriba/jmodeltest2"
    url = "https://github.com/ddarriba/jmodeltest2"

    # JVM application tool — compiler/build_type not used by the build,
    # but declared to satisfy the CI L0p gate (OHOS profile requires all four).
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── JDK discovery (bishengjdk 17, the aladin/alloy pattern) ────────────
    @staticmethod
    def _is_jdk(java_home):
        return all(
            os.path.isfile(os.path.join(java_home, "bin", tool))
            for tool in ("java", "javac", "jar")
        )

    def _find_jdk(self):
        """Return a usable JAVA_HOME, downloading bishengjdk 17 if needed."""
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/usr/local/bishengjdk17",
            "/data/service/hnp/bishengjdk17",
        ]
        for candidate in candidates:
            if candidate and self._is_jdk(candidate):
                self.output.info("JDK found at " + candidate)
                return candidate

        import shutil
        javac_in_path = shutil.which("javac")
        if javac_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(javac_in_path)))
            if self._is_jdk(candidate):
                self.output.info("JDK found in PATH at " + candidate)
                return candidate

        version = "17.0.13"
        download_dir = os.path.join(self.build_folder, "bishengjdk17")
        os.makedirs(download_dir, exist_ok=True)
        self.output.info("JDK not found — downloading bishengjdk " + version)
        get(
            self,
            url=(
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                f"download/pkgs/bishengjdk-{version}-ohos-aarch64.tar.gz"
            ),
            destination=download_dir,
        )
        for entry in os.listdir(download_dir):
            candidate = os.path.join(download_dir, entry)
            if self._is_jdk(candidate):
                self.output.info("JDK downloaded at " + candidate)
                return candidate
        raise ConanException(
            "Could not find BiShengJDK 17 after downloading it. Set JAVA_HOME "
            "or check the bishengjdk package layout."
        )

    def build(self):
        apply_conandata_patches(self)

        jdk = self._find_jdk()
        javac = os.path.join(jdk, "bin", "javac")
        jar = os.path.join(jdk, "bin", "jar")

        src = self.source_folder
        lib_dir = os.path.join(src, "lib")
        lib_jars = sorted(glob.glob(os.path.join(lib_dir, "*.jar")))
        if not lib_jars:
            raise ConanException("No vendor jars found under lib/")

        classpath = os.pathsep.join(lib_jars)

        # ── compile: javac all sources under src/main/java ──
        java_src = os.path.join(src, "src", "main", "java")
        java_files = []
        for root, _dirs, files in os.walk(java_src):
            for f in files:
                if f.endswith(".java"):
                    java_files.append(os.path.join(root, f))

        bin_dir = os.path.join(self.build_folder, "classes")
        os.makedirs(bin_dir, exist_ok=True)

        # upstream targets 1.6 (removed in JDK 17) → compile at 1.8
        cmd = [javac, "-encoding", "UTF-8",
               "-source", "1.8", "-target", "1.8",
               "-d", bin_dir, "-classpath", classpath] + java_files
        self.output.info("javac: {} files".format(len(java_files)))
        subprocess.run(cmd, check=True)

        # ── jar: assemble dist/jModelTest.jar (build.xml 'jar' target) ──
        dist_dir = os.path.join(self.build_folder, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        jar_path = os.path.join(dist_dir, "jModelTest.jar")

        # manifest with Class-Path to the sibling lib dir
        manifest = os.path.join(self.build_folder, "MANIFEST.MF")
        with open(manifest, "w") as f:
            f.write(
                "Manifest-Version: 1.0\n"
                "Main-Class: es.uvigo.darwin.jmodeltest.ModelTest\n"
                "Class-Path: lib/mpj.jar lib/pal.jar lib/alter.jar "
                "lib/freemarker.jar lib/BrowserLauncher2-all-1_3.jar "
                "lib/jfreechart-1.0.14.jar lib/jcommon-1.0.17.jar\n\n"
            )

        # resources merged into the jar (same fileset as build.xml)
        res_dir = os.path.join(src, "src", "main", "resources")
        subprocess.run(
            [jar, "cfm", jar_path, manifest,
             "-C", bin_dir, ".",
             "-C", res_dir, "conf",
             "-C", res_dir, "resources",
             "-C", res_dir, "extra",
             "-C", res_dir, "example-data",
             "-C", res_dir, "trees"],
            check=True,
        )

        self.output.info("jModelTest.jar built at " + jar_path)

    def package(self):
        # Grab the built jar + the vendor libs (needed for the Class-Path).
        lib_dst = os.path.join(self.package_folder, "libexec")
        os.makedirs(lib_dst, exist_ok=True)
        jar_src = os.path.join(self.build_folder, "dist", "jModelTest.jar")
        if os.path.isfile(jar_src):
            copy_one(jar_src, os.path.join(lib_dst, "jModelTest.jar"))
        # Vendor libs live in the source tree's lib/ (build.xml compiles
        # against them but never copies them into the dist output).
        for j in sorted(glob.glob(os.path.join(self.source_folder, "lib", "*.jar"))):
            copy_one(j, os.path.join(lib_dst, os.path.basename(j)))

        # HarmonyOS-aware launcher (aladin wrapper pattern).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper_path = os.path.join(bin_dir, "jmodeltest")
        wrapper = (
            '#!/bin/sh\n'
            '# HarmonyOS-aware jmodeltest launcher\n'
            '# Locates JAVA_HOME (bishengjdk) then runs jModelTest.jar.\n'
            '# os.name overridden to Linux so PAL/AWT resolve the platform.\n'
            '\n'
            'if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then\n'
            '  for candidate in "$HOME/bishengjdk17" "$HOME/usr/local/bishengjdk17" /usr/local/bishengjdk17; do\n'
            '    if [ -f "$candidate/bin/java" ]; then\n'
            '      JAVA_HOME="$candidate"\n'
            '      break\n'
            '    fi\n'
            '  done\n'
            'fi\n'
            '\n'
            'if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then\n'
            '  echo "Error: JAVA_HOME not found. Set JAVA_HOME or install bishengjdk 17." >&2\n'
            '  exit 1\n'
            'fi\n'
            '\n'
            'export JAVA_HOME\n'
            'export PATH="$JAVA_HOME/bin:$PATH"\n'
            'export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-Dos.name=Linux"\n'
            '\n'
            'BIN_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'LIBEXEC="$(cd "$BIN_DIR/.." && pwd)/libexec"\n'
            '\n'
            # Use an explicit -cp (wildcard) instead of `-jar` so that the
            # manifest's Class-Path (lib/*.jar) does not have to be resolved
            # relative to the jar location. Vendor jars are in the same libexec/.
            'exec "$JAVA_HOME/bin/java" -cp "$LIBEXEC/jModelTest.jar:$LIBEXEC/*" \\\n'
            '  es.uvigo.darwin.jmodeltest.ModelTest "$@"\n'
        )
        with open(wrapper_path, "w") as f:
            f.write(wrapper)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["libexec"]


def copy_one(src, dst):
    import shutil
    shutil.copyfile(src, dst)
    os.chmod(dst, 0o644)