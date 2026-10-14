#!/usr/bin/env python3
"""Conan recipe — zt-exec 1.12 (Java source compilation).

Downloads the upstream source tarball, compiles it with Maven 3.9.11
(self-fetched, sha256-pinned), runs the upstream JUnit 4 tests in build()
(surefire, `test` phase of `mvn package`), and packages the resulting JAR
together with its mandatory runtime dependency slf4j-api.

Source: GitHub (zeroturnaround/zt-exec tag zt-exec-1.12)
License: Apache-2.0 (see LICENSE + NOTICE.txt; the code contains fragments
of Apache Commons Exec)
Build system: Maven. The upstream mvnw wrapper pins Maven 3.5.4 hosted on
repo.maven.apache.org — neither JDK 17-safe nor a verified network path on
this device — so the recipe self-fetches a pinned Maven 3.9.11 binary
distribution from repo1.maven.org and reuses it across builds.
Upstream tests: 21 test classes, 96 @Test methods (JUnit 4.11). They spawn
real child JVMs (java -cp target/test-classes ...) plus /bin/true and sleep.

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package calls zt-exec API (spawn/read/async/timeout)
R38: library package (no commands.json)
"""
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


MAVEN_VERSION = "3.9.11"
MAVEN_URL = (
    "https://repo1.maven.org/maven2/org/apache/maven/apache-maven/"
    + MAVEN_VERSION + "/apache-maven-" + MAVEN_VERSION + "-bin.tar.gz"
)
MAVEN_SHA256 = "4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac"
SLF4J_VERSION = "1.7.2"


class ZtExecConan(ConanFile):
    name = "zt-exec"
    version = "1.12"
    description = "ZT Process Executor: a lightweight library to execute external processes from Java"
    license = "Apache-2.0"
    homepage = "https://github.com/zeroturnaround/zt-exec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zt-exec does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sha256(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.

        Checks (in order):
          1. JAVA_HOME environment variable
          2. ~/bishengjdk17 and ~/usr/local/bishengjdk17 (standard cmd-pkgs paths)
          3. java on PATH
          4. Auto-install via cmd-pkgs install-jdk.sh (CI workers may lack JDK)
        """
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        import shutil
        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

        self.output.info("Java not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh"
        )
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))

        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home

        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def _ensure_maven(self):
        """Return a usable MAVEN_HOME, self-fetching a pinned Maven 3.9.11.

        Why not the upstream mvnw wrapper: it pins Maven 3.5.4 (2018, not
        validated on JDK 17) and downloads it from repo.maven.apache.org,
        which is not a verified path on the OHOS device. Maven 3.9.11 from
        repo1.maven.org is sha256-pinned here; the extracted distribution is
        cached in the home directory and reused across builds.
        """
        maven_home = os.path.expanduser("~/apache-maven-" + MAVEN_VERSION)
        if os.path.isfile(os.path.join(maven_home, "bin", "mvn")):
            self.output.info("Maven found at " + maven_home)
            return maven_home

        archive = os.path.join(
            os.path.expanduser("~"),
            "apache-maven-{}-bin.tar.gz".format(MAVEN_VERSION),
        )
        if not os.path.isfile(archive) or self._sha256(archive) != MAVEN_SHA256:
            try:
                self.run(
                    'curl -fsSL --retry 3 --retry-delay 5 --connect-timeout 30 '
                    '--max-time 600 -o "{dest}" "{url}"'.format(dest=archive, url=MAVEN_URL)
                )
            except ConanException:
                self.output.warning(
                    "curl unavailable/failed — python3 urllib fallback "
                    "(no TLS verify; sha256 pin below)"
                )
                # Single logical line: multi-line -c payloads break when passed
                # through /system/bin/sh on HMDFS (newlines become literal \n).
                py = (
                    "import ssl,urllib.request,shutil;"
                    "ctx=ssl._create_unverified_context();"
                    "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                    "r=o.open('{}',timeout=600);f=open('{}','wb');"
                    "shutil.copyfileobj(r,f);f.close();r.close()"
                ).format(MAVEN_URL, archive)
                self.run('python3 -c "{}"'.format(py))

        digest = self._sha256(archive)
        if digest != MAVEN_SHA256:
            raise ConanInvalidConfiguration(
                "Maven distribution sha256 mismatch: expected {}, got {}".format(
                    MAVEN_SHA256, digest
                )
            )
        self.run('tar -xzf "{}" -C ~'.format(archive))
        if not os.path.isfile(os.path.join(maven_home, "bin", "mvn")):
            raise ConanInvalidConfiguration(
                "Maven extraction failed, bin/mvn not found at " + maven_home
            )
        self.output.info("Maven " + MAVEN_VERSION + " installed at " + maven_home)
        return maven_home

    def build(self):
        apply_conandata_patches(self)

        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        # bisheng JDK on HarmonyOS resolves user.home to a literal "?" (no
        # passwd entry for the device uid), which would scatter the Maven
        # local repo into "<builddir>/?/.m2". Set HOME explicitly for child
        # processes AND pin the repo with -Dmaven.repo.local so both the
        # build and package() see the same absolute location.
        home = os.path.expanduser("~")
        os.environ["HOME"] = home
        maven_repo = os.path.join(home, ".m2", "repository")

        maven_home = self._ensure_maven()

        # HMDFS forbids exec() of shebang scripts, so mvn is invoked via `sh`
        # explicitly. `mvn package` runs the upstream surefire tests in the
        # `test` phase first (96 @Test methods, R34/L1c), then produces
        # target/zt-exec-1.12.jar. -B: batch mode. The javadoc jar (bound to
        # `package` by maven-javadoc-plugin 3.0.1) is not part of this package
        # and JDK 17 doclint on this 2013-era pom is noise, so it is skipped.
        self.run(
            'bash -c "cd {src} && sh {maven_home}/bin/mvn -B clean package '
            '-DskipTests=false -Dmaven.javadoc.skip=true '
            '-Dmaven.repo.local={maven_repo}"'.format(
                src=self.source_folder,
                maven_home=maven_home,
                maven_repo=maven_repo,
            ),
            env="conanbuild",
        )

    def package(self):
        src = self.source_folder

        jar_name = "zt-exec-{}.jar".format(self.version)
        jar_path = os.path.join(src, "target", jar_name)
        if not os.path.isfile(jar_path):
            raise ConanInvalidConfiguration(
                "Build artifact not found: {}. "
                "Ensure the Maven build completed successfully.".format(jar_path)
            )
        copy(self, jar_name, os.path.join(src, "target"),
             os.path.join(self.package_folder, "libexec"))

        # slf4j-api is a mandatory runtime dependency (compile scope in the
        # upstream pom): ProcessExecutor touches SLF4J at class-init time.
        # It was resolved into the local Maven repo during the build; bundle
        # it so the packaged jar is runnable as-is (leakcanary-shark bundles
        # kotlin-stdlib/okio the same way).
        slf4j_name = "slf4j-api-{}.jar".format(SLF4J_VERSION)
        slf4j_dir = os.path.join(
            os.path.expanduser("~"), ".m2", "repository", "org", "slf4j",
            "slf4j-api", SLF4J_VERSION,
        )
        if not os.path.isfile(os.path.join(slf4j_dir, slf4j_name)):
            raise ConanInvalidConfiguration(
                "slf4j-api jar not found in local Maven repo: "
                + os.path.join(slf4j_dir, slf4j_name)
            )
        copy(self, slf4j_name, slf4j_dir,
             os.path.join(self.package_folder, "libexec"))

        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE.txt", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
