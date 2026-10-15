#!/usr/bin/env python3
"""Conan recipe — jtreg6 6.2-1 (jtreg 6.2+1, JDK Regression Test Harness).

Builds the upstream jtreg source tarball (GitHub openjdk/jtreg tag
jtreg-6.2+1) with GNU make + BiShengJDK 17 (bootstrapped fully in-process
when the host has no JDK: conan download() + tarfile extraction, because
the cmd-pkgs install-jdk.sh helper dies with "tar: fork: Resource
temporarily unavailable" inside CI-worker sandboxes) and packages the
standard upstream image (bin/, lib/, doc/, legal/, release).

The build drives the upstream `make/build.sh` wrapper, which downloads and
checksum-verifies the upstream build dependencies (Ant, JT Harness,
AsmTools, JCov, JUnit, TestNG/Guice/JCommander).  Network adaptations baked
in for the China network:
  * Ant is fetched separately and cached under ~/apache-ant-1.10.8
    (archive.apache.org is throttled to ~20KB/s on the device; the cache
    also makes repeat builds fast) and passed via the ANT env var.
  * MAVEN_REPO_URL_BASE -> Aliyun Central mirror (repo1.maven.org resets
    from CI runners; same workaround as archives/j/jakarta-*-api).
  * TestNG LICENSE is fetched from the testng source tarball on GitHub
    (sha1-pinned), because raw.githubusercontent.com is unreachable
    (device-verified).
  * When the host has curl, a tiny wget->curl shim is generated because the
    OHOS toybox wget does not support the -q flag used by build.sh.

One source patch (0001-make-Defs.gmk.patch) excludes the JDK 9+
"removal" lint category so the upstream -Werror build works with
BiShengJDK 17 (JDK 17 marks java.applet.Applet for removal via JEP 398,
which upstream CI, building with JDK 11, never hits).  Another source
patch (0002-make-Platform.gmk.patch) teaches the upstream makefiles that
`uname -s` = HarmonyOS is a Linux-like platform; without it Platform.gmk
falls into the Windows branch and emits ';'-separated classpaths
(javac [path] errors under -Werror).

Upstream tests: the recipe runs the upstream `quick-test` target inside
build() with the same invocation as the upstream CI workflow
(MAKE_ARGS=quick-test HEADLESS=1).  The complete upstream self-test suite
was also executed on a HarmonyOS PC during adaptation; see notes.md.

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package/ runs the packaged jtreg against a real mini JDK test suite
R38: CLI package -> software-level commands.json declares bin/jtreg
"""
import hashlib
import os
import shutil
import stat
import tarfile
import time
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, download, save)

ANT_VERSION = "1.10.8"
ANT_ARCHIVE_URL = ("https://archive.apache.org/dist/ant/binaries/"
                   "apache-ant-1.10.8-bin.zip")
ANT_ARCHIVE_SHA1 = "dbe187ce2963f9df8a67de8aaff3b0a437d06978"

BISHENG_JDK_VERSION = "17.0.13"
BISHENG_JDK_URL = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                   "download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz")
BISHENG_JDK_SHA256 = ("ce074909ff5c13e7e7675eb243ee15424f0343610312c526552a1a"
                      "08d199e28f")

TESTNG_VERSION = "7.3.0"
TESTNG_SRC_URL = ("https://github.com/cbeust/testng/archive/refs/tags/"
                  "7.3.0.tar.gz")
TESTNG_LICENSE_SHA1 = "c646d2cd1433560a4b43cb98e7273b59aac4563c"


class Jtreg6Conan(ConanFile):
    name = "jtreg6"
    version = "6.2-1"
    description = "jtreg: the Regression Test Harness for the JDK (OpenJDK) 6.2+1"
    license = "GPL-2.0-only WITH Classpath-exception-2.0"
    homepage = "https://github.com/openjdk/jtreg"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # L0p: OHOS profile requires all four settings (Java build does not
    # consume compiler/build_type; they only feed the package_id).
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jtreg6 does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # JDK resolution (same policy as archives/j/jackson-core 2.14.1 and
    # archives/j/jakarta-validation-api 3.0.2)
    # ------------------------------------------------------------------
    def _ensure_java(self):
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
        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate
        # Bootstrap BiShengJDK entirely in-process. The cmd-pkgs install-jdk.sh
        # helper fails on CI workers (AppSpawn sandbox, per-uid process limit):
        # its `tar xzf` forks a gzip child and gets
        # "tar: fork: Resource temporarily unavailable".
        # conan download() + tarfile (zlib in-process) needs no fork at all.
        self.output.info("Java not found - bootstrapping BiShengJDK 17.0.13 in-process...")
        home = os.path.expanduser("~")
        target = os.path.join(home, "bishengjdk17")
        tarball = os.path.join(home, ".jdk-download-17.0.13.tar.gz")
        staging = os.path.join(home, ".bishengjdk17.staging-%d" % os.getpid())
        try:
            download(self, BISHENG_JDK_URL, tarball, sha256=BISHENG_JDK_SHA256,
                     retry=3, retry_wait=15)
        except ConanException:
            self.output.warning("conan download failed - curl/urllib fallback (sha256 pinned)")
            self._fetch(BISHENG_JDK_URL, tarball)
            h = hashlib.sha256()
            with open(tarball, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != BISHENG_JDK_SHA256:
                raise ConanInvalidConfiguration(
                    "bishengjdk tarball sha256 mismatch: " + h.hexdigest())
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging, exist_ok=True)
        with tarfile.open(tarball) as tf:
            try:
                tf.extractall(staging, filter="data")
            except TypeError:  # Python < 3.12 has no filter parameter
                tf.extractall(staging)
        root = staging
        nested = os.path.join(staging, "bishengjdk17")
        if os.path.isdir(nested):
            root = nested
        if not os.path.isfile(os.path.join(root, "bin", "java")):
            shutil.rmtree(staging, ignore_errors=True)
            raise ConanInvalidConfiguration(
                "bishengjdk tarball layout unexpected (no bin/java)")
        if os.path.isfile(os.path.join(target, "bin", "java")):
            # a concurrent build won the install race - reuse its result
            shutil.rmtree(staging, ignore_errors=True)
        else:
            try:
                os.rename(root, target)  # atomic publish on the same filesystem
            except OSError:
                if not os.path.isfile(os.path.join(target, "bin", "java")):
                    shutil.rmtree(staging, ignore_errors=True)
                    raise
            shutil.rmtree(staging, ignore_errors=True)
        try:
            os.remove(tarball)
        except OSError:
            pass
        if os.path.isfile(os.path.join(target, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + target)
            return target
        raise ConanInvalidConfiguration(
            "Failed to bootstrap bishengjdk 17.0.13 from " + BISHENG_JDK_URL)

    # ------------------------------------------------------------------
    # Ant resolution, cached under ~/apache-ant-1.10.8 (mirrors the
    # ~/apache-maven cache of the jakarta recipes)
    # ------------------------------------------------------------------
    def _fetch(self, url, dest):
        """Fetch url -> dest: curl first (resilient on both OHOS and CI),
        then python-urllib fallback with a long timeout for slow archives."""
        try:
            self.run('curl -fL --retry 3 --retry-delay 10 -o "{}" "{}"'.format(dest, url))
            return
        except ConanException:
            self.output.warning("curl failed for " + url + " - python urllib fallback")
        py = (
            "import ssl,urllib.request,shutil;"
            "ctx=ssl._create_unverified_context();"
            "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
            "r=o.open('{}',timeout=1800);f=open('{}','wb');"
            "shutil.copyfileobj(r,f);f.close();r.close()"
        ).format(url, dest)
        self.run('python3 -c "{}"'.format(py))

    def _ensure_ant(self):
        ant_home = os.path.expanduser("~/apache-ant-" + ANT_VERSION)
        ant = os.path.join(ant_home, "bin", "ant")
        if os.path.isfile(ant):
            self.output.info("Ant found at " + ant_home)
            return ant
        self.output.info("Ant not found - downloading apache-ant-" + ANT_VERSION + "...")
        dest = os.path.expanduser("~/apache-ant-" + ANT_VERSION + "-bin.zip")
        # archive.apache.org throttles to ~20KB/s on the device; curl+retry with
        # a long urllib fallback is far more reliable than wget/conan download.
        self._fetch(ANT_ARCHIVE_URL, dest)
        h = hashlib.sha1()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != ANT_ARCHIVE_SHA1:
            raise ConanInvalidConfiguration(
                "apache-ant tarball sha1 mismatch: " + h.hexdigest())
        os.makedirs(ant_home, exist_ok=True)
        with zipfile.ZipFile(dest) as zf:
            for member in zf.namelist():
                parts = member.split("/", 1)
                if len(parts) < 2 or not parts[1]:
                    continue
                target = os.path.join(ant_home, parts[1])
                if member.endswith("/"):
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as out:
                        shutil.copyfileobj(src, out)
        if not os.path.isfile(ant):
            raise ConanInvalidConfiguration("Ant extraction failed: " + ant)
        os.chmod(ant, os.stat(ant).st_mode | stat.S_IEXEC)
        self.output.info("Ant installed at " + ant_home)
        return ant

    # ------------------------------------------------------------------
    # TestNG LICENSE (raw.githubusercontent.com is unreachable; the same
    # file ships inside the official testng source tarball on GitHub)
    # ------------------------------------------------------------------
    def _prepare_testng_license(self):
        out = os.path.join(self.build_folder, "testng-LICENSE.txt")
        tarball = os.path.join(self.build_folder, "testng-src.tar.gz")
        self._fetch(TESTNG_SRC_URL, tarball)
        with tarfile.open(tarball) as tf:
            member = None
            for m in tf.getmembers():
                if m.name.endswith("/LICENSE.txt") and m.isfile():
                    member = m
                    break
            if member is None:
                raise ConanInvalidConfiguration(
                    "LICENSE.txt not found in testng source tarball")
            with tf.extractfile(member) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
        h = hashlib.sha1()
        with open(out, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != TESTNG_LICENSE_SHA1:
            raise ConanInvalidConfiguration(
                "testng LICENSE.txt sha1 mismatch: " + h.hexdigest())
        return out

    # ------------------------------------------------------------------
    # The OHOS toybox wget does not support -q; build.sh prefers wget over
    # curl. Provide a minimal wget->curl shim when curl is available.
    # ------------------------------------------------------------------
    def _prepare_wget_shim(self):
        try:
            self.run('curl --version >/dev/null 2>&1')
        except ConanException:
            return None
        shim = os.path.join(self.build_folder, "wget-shim")
        save(self, shim, "#!/bin/sh\n"
                         "url=\"\"\n"
                         "dest=\"\"\n"
                         "while [ $# -gt 0 ]; do\n"
                         "  case \"$1\" in\n"
                         "    -O) dest=\"$2\"; shift 2 ;;\n"
                         "    -*) shift ;;\n"
                         "    *) url=\"$1\"; shift ;;\n"
                         "  esac\n"
                         "done\n"
                         "exec curl -fsSL -o \"$dest\" \"$url\"\n")
        os.chmod(shim, 0o755)
        return shim

    def build(self):
        apply_conandata_patches(self)
        java_home = self._ensure_java()
        ant = self._ensure_ant()
        testng_license = self._prepare_testng_license()
        wget_shim = self._prepare_wget_shim()

        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + os.pathsep +
                              os.environ.get("PATH", ""))
        os.environ["ANT"] = ant
        os.environ["JTREG_VERSION_STRING"] = "6.2+1"
        # git.openjdk.org 302-redirects to GitHub and the redirect chain is
        # unreliable from the device; GitHub is the canonical source anyway.
        os.environ["CODE_TOOLS_URL_BASE"] = "https://github.com/openjdk"
        os.environ["MAVEN_REPO_URL_BASE"] = ("https://maven.aliyun.com/"
                                             "repository/central")
        os.environ["TESTNG_LICENSE"] = testng_license
        if wget_shim:
            os.environ["WGET"] = wget_shim
            os.environ["WGET_OPTIONS"] = " "

        # Upstream build wrapper (downloads + builds JT Harness/AsmTools/JCov,
        # fetches JUnit/TestNG/Guice/JCommander, builds jtreg + jtdiff).
        build_cmd = ('bash -c "cd \\"%s\\" && bash make/build.sh --jdk \\"%s\\" -- -j2"'
                     % (self.source_folder, java_home))
        built = False
        for attempt in range(3):
            try:
                self.run(build_cmd, env="conanbuild")
                built = True
                break
            except ConanException:
                self.output.warning(f"jtreg build attempt {attempt + 1}/3 failed, retrying after 30s...")
                time.sleep(30)
        if not built:
            self.run(build_cmd, env="conanbuild")

        # Upstream self-tests (the upstream CI workflow runs the same
        # invocation with MAKE_ARGS=quick-test HEADLESS=1).
        test_cmd = ('bash -c "cd \\"%s\\" && MAKE_ARGS=quick-test HEADLESS=1 '
                    'bash make/build.sh --jdk \\"%s\\" --skip-download"'
                    % (self.source_folder, java_home))
        self.run(test_cmd, env="conanbuild")

    def package(self):
        image = os.path.join(self.source_folder, "build", "images", "jtreg")
        if not os.path.isdir(image):
            raise ConanInvalidConfiguration(
                "Build image not found: " + image)
        copy(self, "*", src=image, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
