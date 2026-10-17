#!/usr/bin/env python3
"""Conan recipe - pdftk 3.3.3 (pdftk-java: PDF Toolkit, pure Java CLI tool).

Downloads the official GitLab source archive and builds with Apache Ant
(upstream build.xml + ivy.xml, same entry points as upstream CI):
  ant main              -> clean, ivy resolve, compile, assemble build/jar/pdftk.jar
  ant test-resolve/test -> fetch JUnit deps, run the official JUnit4 suite (70 tests)

Source: https://gitlab.com/pdftk-java/pdftk (tag v3.3.3)
License: GPL-2.0-or-later
Build system: Ant 1.10.15 (binary fetched from archive.apache.org, sha256-pinned;
              upstream ships no wrapper) + Apache Ivy 2.5.2 (Maven Central,
              sha256-pinned) for dependency retrieve. JDK 17 (bishengjdk, same
              logic as archives/j/jakarta-jmeter 2.13); sources target 1.8,
              accepted by JDK 17 javac without patches.
Runtime deps (ivy build conf): org.bouncycastle:bcprov-jdk18on:1.71,
              org.apache.commons:commons-lang3:3.12.0 (from Maven Central).
Upstream tests: 12 JUnit4 classes / 70 @Test methods under test/com
              (ant `test` target, batchtest **/*Test.java). They run inside
              conan build() and the real per-class "Tests run:" summaries are
              parsed into the HMBS_UPSTREAM_TEST_RESULT marker. Test assertion
              failures are recorded honestly (marker + warning) without failing
              the build; infrastructure failures (no parseable results) raise.
              Consumer verification inside CI is provided by test_package/.

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package/ runs the packaged CLI (--version) + a Java consumer program
     that creates a PDF with the bundled iText classes and round-trips it
     through pdftk (cat + dump_data) on-device
R38: CLI tool package (bin/pdftk launcher); commands.json at software level
"""

import hashlib
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get

ANT_VERSION = "1.10.15"
ANT_URL = ("https://archive.apache.org/dist/ant/binaries/"
           f"apache-ant-{ANT_VERSION}-bin.tar.gz")
ANT_SHA256 = "71334d7e5d98cfe53d6c429a648a5021137a967378667306c5f613dff5180506"

IVY_VERSION = "2.5.2"
IVY_URL = ("https://repo1.maven.org/maven2/org/apache/ivy/ivy/"
           f"{IVY_VERSION}/ivy-{IVY_VERSION}.jar")
IVY_SHA256 = "98428d545ea63cd9a0aaf255caf42cb8cb64fe430dbb5e709aed536d4daeed04"

JACOCO_ANT_VERSION = "0.8.4"
JACOCO_ANT_URL = ("https://repo1.maven.org/maven2/org/jacoco/org.jacoco.ant/"
                  f"{JACOCO_ANT_VERSION}/org.jacoco.ant-{JACOCO_ANT_VERSION}-nodeps.jar")
JACOCO_ANT_SHA256 = "d158d4d14f8425db86a8af9969cb7ec2e73f570afe292bac6556a671e87f80e6"

# Upstream test audit (v3.3.3 sources, test/com/gitlab/pdftk_java/):
# 12 *Test.java classes, 70 @Test methods (JUnit4, ant `test` batchtest).
# Tests calling BlackBox.assertPdfEqualsAsSVG shell out to `pdftocairo`
# (poppler) and fail with "pdftocairo error" when the binary is absent.
# True incidence is log-driven (preflight observed 18/70); do not hardcode 12.
UPSTREAM_TEST_TOTAL = 70


class PdftkConan(ConanFile):
    name = "pdftk"
    version = "3.3.3"
    description = ("pdftk-java 3.3.3 PDF Toolkit (cat/burst/stamp/fill_form/"
                   "dump_data CLI, pure Java)")
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/pdftk-java/pdftk"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R32/L0p: four settings (Java package does not consume compiler/build_type,
    # they only enter package_id)
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pdftk does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.
        (same logic as archives/j/jakarta-jmeter 2.13)

        Note: HNP bundled /data/service/hnp/bin/java fails to start in some
        environments (VM init failure), so prefer JAVA_HOME and ~/bishengjdk17
        (cmd-pkgs install)."""
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
        self.output.info("Java not found - installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
                       "/releases/download/pkgs/install-jdk.sh")
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))
        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home
        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def _ensure_ant(self):
        """Fetch Apache Ant binary tarball from archive.apache.org (sha256-pinned).
        Upstream ships no ant wrapper. Cached under ~/apache-ant-<ver>."""
        ant_home = os.path.expanduser("~/apache-ant-" + ANT_VERSION)
        ant_sh = os.path.join(ant_home, "bin", "ant")
        if os.path.isfile(ant_sh):
            self.output.info("Ant found at " + ant_home)
            return ant_home
        self.output.info("Ant not found - downloading apache-ant-" + ANT_VERSION + " ...")
        dest = os.path.expanduser("~/apache-ant-" + ANT_VERSION + "-bin.tar.gz")
        try:
            self.run('curl -fsSL --retry 3 --connect-timeout 30 -o "{}" "{}"'.format(dest, ANT_URL))
        except ConanException:
            # OHOS device may lack curl / python CA bundle: urllib without TLS
            # verify fallback, integrity covered by the sha256 pin below
            self.output.warning("curl unavailable/failed - python3 urllib fallback (no TLS verify; sha256 pin below)")
            py = (
                "import ssl,urllib.request,shutil;"
                "ctx=ssl._create_unverified_context();"
                "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                "r=o.open('{}',timeout=300);f=open('{}','wb');"
                "shutil.copyfileobj(r,f);f.close();r.close()"
            ).format(ANT_URL, dest)
            self.run('python3 -c "{}"'.format(py))
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != ANT_SHA256:
            raise ConanInvalidConfiguration(
                "apache-ant tarball sha256 mismatch: " + h.hexdigest()
            )
        os.makedirs(ant_home, exist_ok=True)
        self.run('tar -xzf "{}" -C "{}" --strip-components=1'.format(dest, ant_home))
        if not os.path.isfile(ant_sh):
            raise ConanInvalidConfiguration("Ant extraction failed: " + ant_sh)
        self.output.info("Ant installed at " + ant_home)
        return ant_home

    def _fetch_pinned_jar(self, url, sha256, dest):
        """Download one jar from Maven Central with curl (+urllib fallback),
        verified by the sha256 pin."""
        if os.path.isfile(dest) and os.path.getsize(dest) > 10000:
            h = hashlib.sha256()
            with open(dest, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            if h.hexdigest() == sha256:
                self.output.info("cached jar ok: " + dest)
                return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            self.run('curl -fsSL --retry 3 --connect-timeout 30 -o "{}" "{}"'.format(dest, url))
        except ConanException:
            self.output.warning("curl unavailable/failed - python3 urllib fallback (no TLS verify; sha256 pin below)")
            py = (
                "import ssl,urllib.request,shutil;"
                "ctx=ssl._create_unverified_context();"
                "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                "r=o.open('{}',timeout=300);f=open('{}','wb');"
                "shutil.copyfileobj(r,f);f.close();r.close()"
            ).format(url, dest)
            self.run('python3 -c "{}"'.format(py))
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != sha256:
            raise ConanInvalidConfiguration(
                "jar sha256 mismatch for {}: {}".format(url, h.hexdigest())
            )
        self.output.info("jar fetched (sha256 ok): " + dest)

    def _ensure_antlibs(self):
        """Provide Ant with the jars upstream build.xml needs but does not ship:
        Apache Ivy (ivy:retrieve) and JaCoCo Ant tasks (jacoco:coverage/report).
        Both pinned by sha256. Cached under ~/.cache-hmbs-pdftk-antlib/."""
        antlib = os.path.expanduser("~/.cache-hmbs-pdftk-antlib")
        os.makedirs(antlib, exist_ok=True)
        self._fetch_pinned_jar(
            IVY_URL, IVY_SHA256, os.path.join(antlib, "ivy-{}.jar".format(IVY_VERSION)))
        self._fetch_pinned_jar(
            JACOCO_ANT_URL, JACOCO_ANT_SHA256,
            os.path.join(antlib, "org.jacoco.ant-{}-nodeps.jar".format(JACOCO_ANT_VERSION)))
        return antlib

    def _emit_upstream_marker(self, log_path):
        """Parse Ant JUnit per-class summaries from the test log (single
        deterministic source) and emit the HMBS_UPSTREAM_TEST_RESULT marker.

        Ant junit plain formatter prints one line per test class:
          Tests run: N, Failures: F, Errors: E, Skipped: S
        Mapping: discovered = sum(N); skipped = sum(S);
                 failed = sum(F+E); executed = discovered - skipped;
                 passed = executed - failed.
        Returns True when results were parsed (even with failures), False when
        the log holds no parseable results (infrastructure failure)."""
        pattern = re.compile(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)")
        discovered = executed = passed = failed = skipped = 0
        searched = []
        full_content = ""
        for candidate in (log_path,
                          os.path.join(self.source_folder, "uptest.log")):
            searched.append(candidate)
            if os.path.isfile(candidate):
                with open(candidate, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                full_content = content
                for m in pattern.finditer(content):
                    n, fl, er, sk = (int(m.group(1)), int(m.group(2)),
                                    int(m.group(3)), int(m.group(4)))
                    discovered += n
                    failed += fl + er
                    skipped += sk
                if discovered > 0 or "Tests run:" in content:
                    break
                discovered = failed = skipped = 0
        if not searched or (discovered == 0 and failed == 0 and skipped == 0
                            and not any(os.path.isfile(p) for p in searched)):
            marker = {"status": "failed", "framework": "junit",
                      "command": "ant test", "discovered": 0, "executed": 0,
                      "passed": 0, "failed": 0, "skipped": 0,
                      "reason": "no test log found; searched: " + "; ".join(searched)}
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            return False
        if discovered == 0:
            marker = {"status": "failed", "framework": "junit",
                      "command": "ant test", "discovered": 0, "executed": 0,
                      "passed": 0, "failed": 0, "skipped": 0,
                      "reason": "no parseable 'Tests run:' summary in " + log_path}
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            return False
        executed = discovered - skipped
        passed = executed - failed
        # Self-check identities: passed + failed == executed,
        # executed + skipped <= discovered. Repair the source, never the numbers.
        assert passed + failed == executed and executed + skipped <= discovered
        assert all(v >= 0 for v in (discovered, executed, passed, failed, skipped))
        status = "passed" if failed == 0 else "failed"
        marker = {"status": status, "framework": "junit", "command": "ant test",
                  "discovered": discovered, "executed": executed,
                  "passed": passed, "failed": failed, "skipped": skipped}
        if failed > 0:
            # rule4: every non-passing item needs a technical cause + evidence.
            # All observed failures print "pdftocairo error" from
            # BlackBox.assertPdfEqualsAsSVG (BlackBox.java pdfToSVG shells out
            # to external poppler `pdftocairo -svg - -`; IOException -> fail).
            # JaCoCo "Unsupported class file major version 61" lines are
            # coverage-agent noise, not test verdicts (tests still execute).
            cairo_hits = full_content.count("pdftocairo error")
            if cairo_hits > 0:
                gap_count = failed
                marker["gaps"] = [{
                    "count": gap_count,
                    "category": "environment",
                    "detail": ("SVG-comparison tests require external poppler "
                               "pdftocairo (BlackBox.assertPdfEqualsAsSVG: "
                               "Runtime.exec pdftocairo -svg; IOException -> "
                               "fail('pdftocairo error')); binary absent on "
                               "HarmonyOS preflight, so PDF rendering "
                               "comparison cannot run"),
                    "evidence": ("uptest.log shows %d 'pdftocairo error' "
                                 "assertions (e.g. StampTest 8/8 FAILED) + "
                                 "BlackBox.java pdfToSVG/assertPdfEqualsAsSVG "
                                 "source; upstream CI provides it via "
                                 "apt install poppler-utils" % cairo_hits),
                }]
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        return True

    def build(self):
        java_home = self._ensure_java()
        ant_home = self._ensure_ant()
        antlib = self._ensure_antlibs()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + ":" +
                              os.environ.get("PATH", ""))
        src = self.source_folder
        ant_sh = os.path.join(ant_home, "bin", "ant")
        # Official build entry (upstream CI `ant -lib ...` + `main` target:
        # clean, ivy resolve from Maven Central, compile, assemble pdftk.jar).
        # `sh` invocation avoids HMDFS noexec-bit issues on freshly written files.
        self.run(
            'sh -c "cd \'{src}\' && sh \'{ant}\' -lib \'{lib}\' main"'.format(
                src=src, ant=ant_sh, lib=antlib),
            env="conanbuild",
        )
        # Official upstream test suite (JUnit4, 70 @Test in 12 classes).
        # Log is kept so the marker counts come from the framework output.
        uptest_log = os.path.join(src, "uptest.log")
        self.run(
            'sh -c "cd \'{src}\' && sh \'{ant}\' -lib \'{lib}\' -lib ./lib test-resolve"'.format(
                src=src, ant=ant_sh, lib=antlib),
            env="conanbuild",
        )
        self.run(
            'sh -c "cd \'{src}\' && sh \'{ant}\' -lib \'{lib}\' -lib ./lib test >uptest.log 2>&1; rc=$?; cat uptest.log; exit $rc"'.format(
                src=src, ant=ant_sh, lib=antlib),
            env="conanbuild",
            ignore_errors=True,
        )
        if not self._emit_upstream_marker(uptest_log):
            raise ConanException(
                "pdftk upstream test produced no parseable results - see uptest.log "
                "(infrastructure/dependency failure, not a test verdict)")
        # NOTE: assertion failures inside `ant test` are recorded honestly via
        # the marker above (including environment gaps for missing external
        # `pdftocairo`) and do not fail the build here; each non-passing
        # item carries its technical cause + evidence in the marker gaps.

    def package(self):
        # Runnable pdftk home layout under libexec/pdftk/:
        # bin/pdftk.jar (built) + bin/pdftk (launcher) + lib/<runtime jars>.
        src = self.source_folder
        home = os.path.join(self.package_folder, "libexec", "pdftk")
        bin_dst = os.path.join(home, "bin")
        copy(self, "pdftk.jar", os.path.join(src, "build", "jar"), bin_dst)
        copy(self, "*.jar", os.path.join(src, "lib"), os.path.join(home, "lib"))
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src, os.path.join(self.package_folder, "licenses"))
        copy(self, "CHANGELOG.md", src, os.path.join(self.package_folder, "licenses"))
        copy(self, "pdftk.1", src, os.path.join(self.package_folder, "share", "man", "man1"))
        launcher = os.path.join(bin_dst, "pdftk")
        with open(launcher, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n"
                    "# pdftk launcher - runs the packaged pdftk.jar with its runtime jars.\n"
                    "# Invoke via `sh <this file>` where the noexec bit is restricted.\n"
                    "set -e\n"
                    'BIN_DIR=$(dirname "$0")\n'
                    'exec java -cp "$BIN_DIR/pdftk.jar:$BIN_DIR/../lib/*"'
                    " com.gitlab.pdftk_java.pdftk \"$@\"\n")
        os.chmod(launcher, 0o755)

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.bindirs = ["libexec/pdftk/bin"]
