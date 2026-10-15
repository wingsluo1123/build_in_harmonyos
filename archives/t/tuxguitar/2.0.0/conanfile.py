#!/usr/bin/env python3
"""Conan recipe — tuxguitar 2.0.0 (Java, HarmonyOS PC adaptation).

TuxGuitar is a Java (Maven multi-module) guitar tablature editor/engine.
This package builds the **portable, non-GUI Java core** of TuxGuitar — the
``common/*`` modules plus the headless ``tuxguitar`` app-core and
``tuxguitar-ui-toolkit`` (SWT/JFx/Qt GUI toolkits are excluded: HarmonyOS PC
ships no X11/GTK SWT port, so only the platform-independent engine is packaged).

Source: GitHub (helge17/tuxguitar tag 2.0.0)
License: LGPL-2.1-or-later (see LICENSE)
Build system: Maven 3.9.11 (binary fetched from repo1.maven.org, sha256-pinned;
              upstream repo ships no mvnw wrapper) — house pattern of
              archives/j/jakarta-authentication-api 3.0.0 and
              archives/t/typometer 1.0.1
Upstream tests: JUnit 5.9.2 — 58 cases in 13 classes, executed during
                `mvn package` (surefire XML parsed into upstream-test-result.json).

HarmonyOS adaptations (patches/):
  0002-desktop-pom.xml.patch — the aggregator parent POM activates its platform
    profile via Maven's OS-family matcher (linux/windows/macos/freebsd). On
    HarmonyOS ``os.name=HarmonyOS`` matches no family, ``org.eclipse.swt.groupId``
    stays undefined and Maven aborts with ProjectBuildingException before building
    anything. The patch adds an ``os.name=HarmonyOS`` activated profile.
  0001-...-TGUserFileUtils.java.patch — the HarmonyOS JVM reports ``user.home`` as
    an unusable non-absolute placeholder (literally "?"), which made TuxGuitar
    resolve its config/cache directory relative to the CWD ("?/.config/tuxguitar").
    The patch validates ``user.home`` and falls back to the POSIX ``HOME`` variable.

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package/ compiles and runs a Java consumer against the packaged JARs
R38: library package (JARs under libexec/, no commands.json)
"""
import glob
import hashlib
import json
import os
import time
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, save, apply_conandata_patches, export_conandata_patches

MAVEN_VERSION = "3.9.11"
MAVEN_URL = ("https://repo1.maven.org/maven2/org/apache/maven/apache-maven/"
             f"{MAVEN_VERSION}/apache-maven-{MAVEN_VERSION}-bin.tar.gz")
MAVEN_SHA256 = "4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac"

# Maven Central direct connections reset intermittently on the OHOS network;
# route `central` through the Aliyun mirror (China CDN) with a direct fallback.
MAVEN_SETTINGS = (
    "<settings><mirrors><mirror>"
    "<id>aliyun-central</id>"
    "<url>https://maven.aliyun.com/repository/central</url>"
    "<mirrorOf>central</mirrorOf>"
    "</mirror></mirrors></settings>"
)

# The portable (non-GUI, non-native) module set. Built from the upstream
# `desktop/build-scripts/tuxguitar-linux-swt` aggregator which is the only
# reactor carrying the common modules; -am pulls in tuxguitar / ui-toolkit.
MODULES = [
    ":tuxguitar-lib",
    ":tuxguitar-gm-utils",
    ":tuxguitar-editor-utils",
    ":tuxguitar-ascii",
    ":tuxguitar-compat",
    ":tuxguitar-gtp",
    ":tuxguitar-gpx",
    ":tuxguitar-lilypond",
    ":tuxguitar-midi",
    ":tuxguitar-ptb",
    ":tuxguitar-pdf",
]
AGGREGATOR = os.path.join("desktop", "build-scripts", "tuxguitar-linux-swt")


class TuxGuitarConan(ConanFile):
    name = "tuxguitar"
    version = "2.0.0"
    description = "TuxGuitar — guitar tablature editor/engine, portable Java core"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/helge17/tuxguitar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # Pure-Java JARs have no shared/static distinction; the option exists only to
    # satisfy Conan's library package-type validation and has no build effect
    # (same house pattern as archives/t/t-digest 3.0 and archives/v/vecmath 1.5.2).
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tuxguitar does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── toolchain bootstrap ────────────────────────────────────────────────
    def _ensure_java(self):
        """Find BiShengJDK 17 in the environment, or auto-install via cmd-pkgs."""
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "javac")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home
        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/usr/lib/jvm/bishengjdk-17",
            "/usr/lib/jvm/java-17-openjdk",
            "/usr/lib/jvm/java-17-openjdk-arm64",
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "javac")):
                self.output.info("Java found at " + candidate)
                return candidate
        self.output.info("Java not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
                       "/releases/download/pkgs/install-jdk.sh")
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))
        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "javac")):
            return java_home
        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def _ensure_maven(self):
        """Fetch the Apache Maven binary tarball from repo1.maven.org (sha256-pinned)."""
        maven_home = os.path.expanduser("~/apache-maven-" + MAVEN_VERSION)
        mvn = os.path.join(maven_home, "bin", "mvn")
        if os.path.isfile(mvn):
            self.output.info("Maven found at " + maven_home)
            return maven_home
        self.output.info("Maven not found — downloading apache-maven-" + MAVEN_VERSION + " ...")
        dest = os.path.expanduser("~/apache-maven-" + MAVEN_VERSION + "-bin.tar.gz")
        try:
            self.run('curl -fsSL -o "{}" "{}"'.format(dest, MAVEN_URL))
        except ConanException:
            self.output.warning("curl failed — python3 urllib fallback (no TLS verify; sha256 pin below)")
            py = (
                "import ssl,urllib.request,shutil;"
                "ctx=ssl._create_unverified_context();"
                "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                "r=o.open('{}',timeout=300);f=open('{}','wb');"
                "shutil.copyfileobj(r,f);f.close();r.close()"
            ).format(MAVEN_URL, dest)
            self.run('python3 -c "{}"'.format(py))
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != MAVEN_SHA256:
            raise ConanInvalidConfiguration(
                "apache-maven tarball sha256 mismatch: " + h.hexdigest()
            )
        os.makedirs(maven_home, exist_ok=True)
        self.run('tar -xzf "{}" -C "{}" --strip-components=1'.format(dest, maven_home))
        if not os.path.isfile(mvn):
            raise ConanInvalidConfiguration("Maven extraction failed: " + mvn)
        self.output.info("Maven installed at " + maven_home)
        return maven_home

    # ── build ──────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        java_home = self._ensure_java()
        maven_home = self._ensure_maven()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + ":" +
                              os.path.join(maven_home, "bin") + ":" +
                              os.environ.get("PATH", ""))

        settings_xml = os.path.join(self.build_folder, "maven-settings.xml")
        save(self, settings_xml, MAVEN_SETTINGS)
        mvn = "sh {}/bin/mvn".format(maven_home)
        reactor = os.path.join(self.source_folder, AGGREGATOR)

        # 1) build + upstream test suite (surefire runs during `package`)
        cmd = ('bash -c "cd {} && {} -s {} -B -pl {} -am clean package"'
               .format(reactor, mvn, settings_xml, ",".join(MODULES)))
        built = False
        for attempt in range(3):
            try:
                self.run(cmd, env="conanbuild")
                built = True
                break
            except ConanException:
                self.output.warn(
                    "Maven build attempt {}/3 failed, retrying after 20s...".format(attempt + 1))
                time.sleep(20)
        if not built:
            # Final attempt straight against Maven Central (no mirror) for the log trail.
            self.run('bash -c "cd {} && {} -B -pl {} -am clean package"'
                     .format(reactor, mvn, ",".join(MODULES)), env="conanbuild")

        jars = self._collect_jars()
        if not jars:
            raise ConanInvalidConfiguration(
                "No JAR artifacts produced under " + self.source_folder)

        # 2) gather the runtime dependency JARs (commons-compress / commons-io)
        deps_dir = os.path.join(self.build_folder, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        dep_cmd = ('bash -c "cd {} && {} -s {} -B -pl :tuxguitar-lib '
                   'dependency:copy-dependencies -DincludeScope=runtime '
                   '-DoutputDirectory={}"'.format(reactor, mvn, settings_xml, deps_dir))
        try:
            self.run(dep_cmd, env="conanbuild")
        except ConanException:
            self.output.warn("dependency:copy-dependencies failed — package will contain "
                             "TuxGuitar JARs only (runtime deps must be supplied by consumer)")

        self._collect_upstream_tests()

    def _collect_jars(self):
        out = []
        for jar in sorted(glob.glob(os.path.join(self.source_folder, "**", "target", "*.jar"),
                                    recursive=True)):
            base = os.path.basename(jar)
            if base.startswith("original-") or base.endswith(("-sources.jar", "-javadoc.jar")):
                continue
            out.append(jar)
        return out

    def _collect_upstream_tests(self):
        """Parse the Maven Surefire XML reports produced by `mvn package`."""
        cases, total, failed, errors, skipped = [], 0, 0, 0, 0
        for xml in sorted(glob.glob(os.path.join(self.source_folder, "**", "target",
                                                 "surefire-reports", "TEST-*.xml"),
                                    recursive=True)):
            try:
                root = ET.parse(xml).getroot()
            except ET.ParseError:
                continue
            t = int(root.get("tests", 0))
            fa = int(root.get("failures", 0))
            er = int(root.get("errors", 0))
            sk = int(root.get("skipped", 0))
            total += t
            failed += fa
            errors += er
            skipped += sk
            cases.append({
                "module": os.path.relpath(xml, self.source_folder).split(os.sep + "target" + os.sep)[0],
                "class": root.get("name"),
                "tests": t, "failures": fa, "errors": er, "skipped": sk,
                "cases": [c.get("name") for c in root.findall("testcase")],
            })
        result = {
            "status": "executed" if total else "no_tests",
            "framework": "junit5",
            "command": "mvn -pl <common modules> -am clean package",
            "discovered": total,
            "executed": total,
            "passed": total - failed - errors - skipped,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "classes": len(cases),
            "cases": cases,
        }
        save(self, os.path.join(self.build_folder, "upstream-test-result.json"),
             json.dumps(result, ensure_ascii=False, indent=2))
        marker = json.dumps({k: v for k, v in result.items() if k != "cases"},
                            ensure_ascii=False)
        # Evidence line for review/audit tooling (machine-readable, repo-wide convention).
        print("HMBS_UPSTREAM_TEST_RESULT=" + marker)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + marker)

    # ── package ────────────────────────────────────────────────────────────
    def package(self):
        libexec = os.path.join(self.package_folder, "libexec")
        for jar in self._collect_jars():
            copy(self, os.path.basename(jar), os.path.dirname(jar), libexec)
        deps_dir = os.path.join(self.build_folder, "deps")
        if os.path.isdir(deps_dir):
            copy(self, "*.jar", deps_dir, libexec)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "upstream-test-result.json", self.build_folder, libexec)

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
