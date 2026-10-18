#!/usr/bin/env python3
"""Conan recipe — typometer 1.0.1 (Java/Swing typing-latency analyzer).

Downloads the upstream source tarball, compiles it with Maven (JDK 17) and
runs the upstream JUnit suite, then packages the runnable uber-JAR under
libexec/ (same house pattern as archives/j/jakarta-authentication-api 3.0.0).

Source: GitHub (pavelfatin/typometer tag v1.0.1)
License: Apache-2.0
Build system: Maven 3.9.11 (binary fetched from repo1.maven.org, sha256-pinned;
              upstream repo ships no mvnw wrapper)
Upstream tests: JUnit 4.12 — 89 cases (CsvDataTest 2, MetricsTest 37,
                RecognitionTest 49, HeapTest 1); executed during `mvn package`.

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package/ compiles and runs a Java consumer program on-device
R38: library package (JAR under libexec/, no commands.json needed)
"""
import hashlib
import json
import os
import re
import time
from glob import glob

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


class TypometerConan(ConanFile):
    name = "typometer"
    version = "1.0.1"
    description = "Text / code editor typing latency analyzer (Java/Swing)"
    license = "Apache-2.0"
    homepage = "https://github.com/pavelfatin/typometer"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"typometer does not support OS: {self.settings.os}"
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
        cmd = 'bash -c "cd {} && {} -s {} clean package -B -DskipTests=false"'.format(
            self.source_folder, mvn, settings_xml)

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
            self.run('bash -c "cd {} && {} clean package -B -DskipTests=false"'.format(
                self.source_folder, mvn), env="conanbuild")

        jar_path = os.path.join(self.source_folder, "target",
                                "typometer-{}.jar".format(self.version))
        if not os.path.exists(jar_path):
            raise ConanInvalidConfiguration(f"Build artifact not found: {jar_path}")

        self._collect_upstream_tests()

    def _collect_upstream_tests(self):
        """Parse the Maven Surefire reports produced by `mvn package`."""
        reports_dir = os.path.join(self.source_folder, "target", "surefire-reports")
        pattern = re.compile(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)")
        cases, total = [], 0
        failed = errors = skipped = 0
        for txt in sorted(glob(os.path.join(reports_dir, "*.txt"))):
            cls = os.path.basename(txt)[:-4]
            with open(txt, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            m = pattern.search(content)
            if not m:
                continue
            t, fa, er, sk = (int(x) for x in m.groups())
            total += t
            failed += fa
            errors += er
            skipped += sk
            cases.append({"class": cls, "tests": t, "failures": fa,
                          "errors": er, "skipped": sk})
        result = {
            "status": "executed" if total else "no_tests",
            "framework": "junit",
            "command": "mvn clean package -B -DskipTests=false",
            "discovered": total,
            "executed": total,
            "passed": total - failed - errors - skipped,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "cases": cases,
        }
        save(self, os.path.join(self.build_folder, "upstream-test-result.json"),
             json.dumps(result, ensure_ascii=False, indent=2))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    # ── package ────────────────────────────────────────────────────────────
    def package(self):
        jar_name = "typometer-{}.jar".format(self.version)
        copy(self, jar_name, os.path.join(self.source_folder, "target"),
             os.path.join(self.package_folder, "libexec"))
        copy(self, "typometer-{}-bin.zip".format(self.version),
             os.path.join(self.source_folder, "target"),
             os.path.join(self.package_folder, "libexec"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "upstream-test-result.json", self.build_folder,
             os.path.join(self.package_folder, "libexec"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
