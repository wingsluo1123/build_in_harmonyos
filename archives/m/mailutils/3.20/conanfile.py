#!/usr/bin/env python3
"""Conan recipe — GNU Mailutils 3.20 for HarmonyOS PC (aarch64-linux-ohos).

GNU Mailutils is a protocol-independent mail framework: the libmailutils
library family (mailbox, URL, message and MIME handling, Sieve, auth), the
POSIX `mailx` client plus the `frm`/`from`/`readmsg`/`sieve`/`mimeview`/
`movemail` utilities, and the `imap4d`/`pop3d`/`comsatd`/`mda`/`lmtpd`
servers.

The upstream Autotest suites are executed through `make check` inside build()
so the CI L1 gate observes a real upstream test run.

OHOS adaptations (see notes.md and patches/):
  * config.guess / config.sub: teach the `aarch64-unknown-linux-ohos` triplet.
  * configure / config.status: temporary-dir umask 077 -> 022 because HMDFS
    maps the directory owner to a UID different from the running process.
  * configure: probe getspnam()/getutxent(), which the OHOS libc lacks.
  * doc/texinfo/Makefile.in: neutralise the stamp-vti rule (toybox `ls` output
    breaks mdate-sh and the worker ships no makeinfo).
  * libmailutils/base/locker.c: dotlock falls back to an O_EXCL lock file
    because HMDFS rejects link(2) with EPERM.
  * testsuite/cwdrepl.c: tolerate an unset PWD and a failed getcwd() in the
    isolated HarmonyOS test environment.
  * Run the OHOS build and upstream tests from native cache storage: HMDFS
    masks permission-mode changes and rejects the FIFO used by make's
    parallel jobserver.
  * Upstream optional test integrations are supplied as explicit Conan
    dependencies so their tests execute instead of being skipped.
"""

import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import tempfile
import uuid

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


PAYLOAD_DIRS = ("bin", "sbin", "libexec", "lib", "include", "share")

MUTILS_LIBS = [
    "mailutils", "muaux", "mu_auth", "mu_dotmail", "mu_imap", "mu_maildir",
    "mu_mailer", "mu_mbox", "mu_mh", "mu_pop", "mu_sieve",
]

class MailutilsConan(ConanFile):
    name = "mailutils"
    version = "3.20"
    description = ("GNU Mailutils: protocol-independent mail framework "
                   "(libmailutils family, mailx client, IMAP4/POP3 servers)")
    license = "GPL-3.0-or-later AND LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/mailutils/"
    url = "https://www.gnu.org/software/mailutils/"
    topics = ("mail", "imap", "pop3", "smtp", "sieve", "mailbox", "gnu")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mailutils is only adapted for Linux/OHOS")

    def requirements(self):
        # These upstream-optional libraries enable suites and cases that would
        # otherwise be skipped.
        self.requires("gnutls/3.8.10")
        self.requires("libunistring/1.0")
        self.requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        try:
            apply_conandata_patches(self)
        except Exception as exc:
            self.output.warning(
                "Conan patch helper could not apply every patch; "
                "using the context-based fallback: %s" % exc)
        # Conan's patch helper can silently leave a patch unapplied on the
        # device's Toybox/patch stack. The fallback is idempotent so it can
        # finish any partial application here and be checked again in build().
        self._apply_patches()

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # Optional integrations are disabled explicitly below; SQL remains off by
        # upstream default because no SQL module is selected.
        AutotoolsDeps(self).generate()

        # Autoconf executes linked probe binaries on the HarmonyOS device.
        # Make host dependency libraries visible to the dynamic loader during
        # configure, build, and upstream tests.
        for dep in self.dependencies.host.values():
            for bindir in dep.cpp_info.bindirs:
                if not os.path.isabs(bindir) or bindir.lstrip(os.sep) == "bin":
                    bindir = os.path.join(dep.package_folder, bindir.lstrip(os.sep))
                if os.path.isfile(os.path.join(bindir, "certtool")):
                    # GNU Mailutils' TLS Autotest needs GnuTLS' certtool to
                    # generate its local test certificate. Conan's build env
                    # does not add host dependency executables to PATH.
                    self.buildenv.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir) or libdir.lstrip(os.sep) == "lib":
                    libdir = os.path.join(dep.package_folder, libdir.lstrip(os.sep))
                if os.path.isdir(libdir):
                    self.buildenv.prepend_path("LD_LIBRARY_PATH", libdir)

        if str(self.settings.os) == "OHOS":
            workspace, tmp_base = self._new_native_workspace()
            self._mailutils_native_workspace = workspace
            marker = self._native_workspace_marker()
            with open(marker, "w", encoding="utf-8") as handle:
                json.dump({"workspace": workspace, "base": tmp_base}, handle)
            tmpdir = os.path.join(workspace, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            self.output.info(
                "using native HarmonyOS workspace %s; mkfifo probe passed in %s"
                % (workspace, tmp_base))
        else:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        self.buildenv.define("TMPDIR", tmpdir)
        self.buildenv.define("TMP", tmpdir)
        self.buildenv.define("TEMP", tmpdir)
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        self.buildenv.define("SHELL", "/bin/sh")
        # OHOS developer shells can lack a passwd database entry for their
        # effective UID. Supply a test/package identity for programs that
        # fall back to LOGNAME/USER when getpwuid() returns no record.
        self.buildenv.define("LOGNAME", "mailutils-test")
        self.buildenv.define("USER", "mailutils-test")
        # Harmonybrew exposes netcat as `netcat`, but the upstream mockmta
        # test invokes `nc`. Add a build-local alias so it executes rather
        # than reporting a missing-tool skip.
        test_bin = os.path.join(self.build_folder, ".mailutils-test-bin")
        os.makedirs(test_bin, exist_ok=True)
        nc_shim = os.path.join(test_bin, "nc")
        with open(nc_shim, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\nexec netcat \"$@\"\n")
        os.chmod(nc_shim, 0o755)
        self.buildenv.prepend_path("PATH", test_bin)

    # ── helpers ────────────────────────────────────────────────────────────
    def _native_workspace_marker(self):
        return os.path.join(self.build_folder, ".mailutils-native-workspace.json")

    def _new_native_workspace(self):
        """Find a filesystem that supports both POSIX modes and GNU make FIFOs."""
        candidates = []
        worker_tmp = os.environ.get("TMPDIR")
        if worker_tmp:
            candidates.append(worker_tmp)
        candidates.append("/data/storage/el2/base/cache")

        for base in dict.fromkeys(candidates):
            if not os.path.isdir(base) or not os.access(base, os.W_OK):
                continue
            fifo = os.path.join(base, ".mailutils-mkfifo-probe-" + uuid.uuid4().hex)
            try:
                os.mkfifo(fifo)
            except OSError:
                continue
            try:
                os.unlink(fifo)
            except OSError:
                self.output.warning("could not remove temporary FIFO probe %s" % fifo)
                continue
            workspace = tempfile.mkdtemp(prefix="mailutils-3.20-", dir=base)
            return workspace, os.path.realpath(base)

        raise ConanInvalidConfiguration(
            "HarmonyOS Mailutils needs a writable temporary filesystem that "
            "supports GNU make jobserver FIFOs; checked TMPDIR and "
            "/data/storage/el2/base/cache")

    def _cleanup_native_workspace(self):
        marker = self._native_workspace_marker()
        if not os.path.isfile(marker):
            return
        try:
            with open(marker, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            base = os.path.realpath(data["base"])
            workspace = os.path.realpath(data["workspace"])
            if (os.path.commonpath((base, workspace)) != base
                    or not os.path.basename(workspace).startswith("mailutils-3.20-")):
                self.output.warning("refusing to clean an unexpected workspace: %s" % workspace)
                return
            shutil.rmtree(workspace)
            os.unlink(marker)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.output.warning("could not clean native Mailutils workspace: %s" % exc)

    def _restore_helper_modes(self, source_dir=None):
        """HMDFS extraction can lose the executable bit of Autotools helpers."""
        source_dir = source_dir or self.source_folder
        for rel in ("configure", "build-aux/config.guess", "build-aux/config.sub",
                    "build-aux/install-sh", "build-aux/missing",
                    "build-aux/depcomp", "build-aux/compile", "config.guess",
                    "config.sub", "install-sh", "missing"):
            path = os.path.join(source_dir, rel)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    @staticmethod
    def _summarise_autotest(log):
        """Aggregate the Autotest summaries of every suite in the log.

        Failing suites report "N tests were run, M failed unexpectedly" while
        fully passing suites report "N tests were successful".  The latter
        count excludes skipped tests, whereas the former's run count includes
        them, so parse each result block before aggregating.
        """
        markers = list(re.finditer(r"##\s*Test results\.\s*##", log))
        passed = skipped = failed = 0

        for index, marker in enumerate(markers):
            end = markers[index + 1].start() if index + 1 < len(markers) else len(log)
            block = log[marker.end():end]
            block = re.sub(r"^\s*##[ -]+##\s*", "", block, count=1)

            run_match = re.search(
                r"^(?:ERROR:\s*)?(?:All\s+)?(\d+) tests? were run,\s*$",
                block, re.MULTILINE)
            failed_match = re.search(
                r"^(\d+) failed unexpectedly\.|^(\d+) tests? (?:was|were) unsuccessful\.",
                block, re.MULTILINE)
            skipped_match = re.search(
                r"^(\d+) tests? (?:was|were) skipped\.", block, re.MULTILINE)
            suite_failed = int(next((value for value in failed_match.groups()
                                     if value is not None), 0)) if failed_match else 0
            suite_skipped = int(skipped_match.group(1)) if skipped_match else 0

            if run_match:
                suite_total = int(run_match.group(1))
                failed += suite_failed
                skipped += suite_skipped
                passed += max(0, suite_total - suite_failed - suite_skipped)
                continue

            success_match = re.search(
                r"^(?:All\s+)?(\d+) tests? (?:was|were) successful\.",
                block, re.MULTILINE)
            if success_match:
                passed += int(success_match.group(1))
                skipped += suite_skipped

        return passed, skipped, failed, len(markers)

    def _report_failed_autotest_cases(self, source_dir=None):
        """Print concise failing case names from Autotest suite logs.

        Conan's CI summary keeps the aggregate count but not the six case
        names. Autotest writes those names into each suite-level
        ``testsuite.log``; report the failure table without dumping the full
        logs or per-test ``testsuite.dir`` artifacts.
        """
        # HarmonyOS checks use a native-storage source copy; Linux keeps the
        # Conan source tree. Walk the actual test tree to report failure logs.
        scan_root = source_dir or os.path.dirname(self.build_folder) or self.build_folder
        for root, dirs, files in os.walk(scan_root):
            dirs[:] = [name for name in dirs if name != "testsuite.dir"]
            if "testsuite.log" not in files:
                continue
            path = os.path.join(root, "testsuite.log")
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    log = handle.read()
            except OSError as exc:
                self.output.warning("cannot read Autotest log %s: %s" % (path, exc))
                continue

            start = log.find("Failed tests:")
            if start < 0:
                continue
            end = log.find("## Detailed failed tests.", start)
            summary = log[start:end if end >= 0 else start + 12000]
            case_rows = re.findall(r"^\s*\d+:\s+.+$", summary, re.MULTILINE)
            relative = os.path.relpath(path, scan_root)
            self.output.error("Autotest failure details from %s:" % relative)
            if case_rows:
                for row in case_rows[:80]:
                    self.output.error(row.strip())
                if len(case_rows) > 80:
                    self.output.error("... %d additional case rows omitted" %
                                      (len(case_rows) - 80))
            else:
                for line in summary.splitlines()[:80]:
                    if line.strip():
                        self.output.error(line.strip())

    def _run_make(self, command, cwd):
        """Run make with the writable temp directory from the build environment."""
        self.run(command, env="conanbuild", cwd=cwd)

    def _run_upstream_tests(self, source_dir):
        log_file = os.path.join(self.build_folder, "upstream-make-check.log")
        command_failed = False
        try:
            self._run_make(
                "make -j2 -k check > %s 2>&1" % shlex.quote(log_file),
                source_dir)
        except Exception:
            # Preserve the complete run and aggregate its real summaries
            # before enforcing the test gate below.
            command_failed = True

        with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
            log = handle.read()
        autotest_passed, autotest_skipped, autotest_failed, suite_count = \
            self._summarise_autotest(log)
        passed = autotest_passed
        skipped = autotest_skipped
        failed = autotest_failed
        expected_suites = 21
        expected_cases = 1389
        self.output.info("upstream make check: passed=%d failed=%d skipped=%d (log: %s)"
                         % (passed, failed, skipped, log_file))
        summary = {"suite": "make check (Autotest)",
                   "total": passed + failed + skipped,
                   "passed": passed, "failed": failed, "skipped": skipped,
                   "suite_count": suite_count,
                   "expected_suites": expected_suites,
                   "expected_cases": expected_cases,
                   "log": log_file}
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)
        if (command_failed or failed or skipped or suite_count != expected_suites
                or passed + failed + skipped != expected_cases):
            if command_failed or failed:
                self._report_failed_autotest_cases(source_dir)
            raise RuntimeError(
                "all %d upstream make-check Autotest cases in %d suites must pass "
                "without skips; passed=%d failed=%d skipped=%d suites=%d "
                "(see %s)"
                % (expected_cases, expected_suites, passed, failed, skipped,
                   suite_count, log_file))

    def _apply_one_unified_diff(self, patch_file, base):
        """Apply a unified diff by content.

        The device `patch` is Toybox 0.8.12. It exits 0 without editing a file
        when a hunk count is wrong, and it rejects some otherwise exact hunks.
        `str.splitlines()` is also unsafe here: GNU sources contain form-feed
        section separators, which splitlines() treats as line breaks.
        """
        with open(patch_file, "r", encoding="utf-8", errors="surrogateescape") as handle:
            text = handle.read().split("\n")
        files = []
        current = None
        hunk = None
        for line in text:
            if line.startswith("--- "):
                current = {"hunks": []}
                files.append(current)
                hunk = None
                continue
            if line.startswith("+++ ") and current is not None:
                rel = line[4:].split("\t", 1)[0].strip()
                if rel.startswith("b/"):
                    rel = rel[2:]
                current["path"] = rel
                continue
            if line.startswith("@@") and current is not None:
                hunk = {"old": [], "new": []}
                current["hunks"].append(hunk)
                continue
            # A real blank context line is " ", not "". An empty string is the
            # trailing split from the patch file's final newline.
            if line == "" or hunk is None or line.startswith("\\"):
                continue
            if line.startswith("+"):
                hunk["new"].append(line[1:])
            elif line.startswith("-"):
                hunk["old"].append(line[1:])
            else:
                ctx = line[1:] if line.startswith(" ") else line
                hunk["old"].append(ctx)
                hunk["new"].append(ctx)

        changed_paths = []
        already_applied = False
        for entry in files:
            rel = entry.get("path")
            if not rel or rel == "/dev/null":
                continue
            path = os.path.join(base, rel)
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as handle:
                raw = handle.read()
            newline_at_end = raw.endswith("\n")
            lines = raw.split("\n")
            if newline_at_end:
                lines = lines[:-1]
            for hunk in entry["hunks"]:
                old = hunk["old"]
                found = None
                limit = len(lines) - len(old) + 1
                for index in range(max(0, limit)):
                    if lines[index:index + len(old)] == old:
                        found = index
                        break
                if found is None:
                    new = hunk["new"]
                    new_limit = len(lines) - len(new) + 1
                    if any(lines[index:index + len(new)] == new
                           for index in range(max(0, new_limit))):
                        already_applied = True
                        continue
                    raise RuntimeError(
                        "hunk context not found in %s while applying %s"
                        % (path, patch_file))
                lines[found:found + len(old)] = hunk["new"]
            updated = "\n".join(lines)
            if newline_at_end:
                updated += "\n"
            if updated != raw:
                with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as handle:
                    handle.write(updated)
                changed_paths.append(path)
        if files and not changed_paths and not already_applied:
            raise RuntimeError("patch did not modify its target files: %s" % patch_file)

    def _apply_patches(self):
        """Apply the conandata patches.

        `apply_conandata_patches()` relies on patch_ng, which rejects hunks
        whose `@@` header line numbers are slightly off (the repository patch
        generator indexes lines with str.splitlines(), which also splits on the
        form-feed section separators used throughout the GNU sources).
        """
        for entry in self.conan_data.get("patches", []) or []:
            patch_file = os.path.join(self.export_sources_folder, entry["patch_file"])
            base = os.path.join(self.source_folder, entry.get("base_path", ""))
            self._apply_one_unified_diff(patch_file, base)

    def _repair_dependency_libtool_metadata(self):
        """Temporarily repair relocated .la paths in the isolated Conan cache.

        Several prebuilt OHOS dependencies were packaged with libtool metadata
        that still points at `/usr/local/lib` or contains `//lib`. Those stale
        paths make libtool treat a shared dependency as a missing absolute
        `.la` file. The files are restored after this build, so the cached
        dependency packages themselves remain unchanged.
        """
        dependencies = list(self.dependencies.host.values())
        package_libdirs = {}
        libtool_files = []

        for dep in dependencies:
            package_folder = os.path.abspath(dep.package_folder)
            package_id = os.path.basename(os.path.dirname(package_folder))
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir) or libdir.lstrip(os.sep) == "lib":
                    libdir = os.path.join(package_folder, libdir.lstrip(os.sep))
                libdir = os.path.abspath(libdir)
                if not os.path.isdir(libdir):
                    continue
                package_libdirs[package_id] = libdir
                libtool_files.extend(
                    os.path.join(libdir, name)
                    for name in os.listdir(libdir)
                    if name.endswith(".la") and os.path.isfile(os.path.join(libdir, name)))

        libtool_files = list(dict.fromkeys(libtool_files))
        la_by_name = {os.path.basename(path): path for path in libtool_files}
        originals = {}

        def map_library_path(path):
            basename = os.path.basename(path)
            if basename.endswith(".la") and basename in la_by_name:
                return la_by_name[basename]
            match = re.search(r"/\.conan2/p/([^/]+)/p/lib$", path)
            if match and match.group(1) in package_libdirs:
                return package_libdirs[match.group(1)]
            return path

        try:
            for path in libtool_files:
                with open(path, "rb") as handle:
                    original = handle.read()
                text = original.decode("utf-8", errors="surrogateescape")
                containing_libdir = os.path.dirname(path)
                text = re.sub(
                    r"^libdir='[^']*'$",
                    "libdir='%s'" % containing_libdir,
                    text,
                    flags=re.MULTILINE)

                def repair_dependency_libs(match):
                    tokens = shlex.split(match.group(1))
                    repaired = []
                    for token in tokens:
                        if token == "-L//lib" or token.endswith("/usr/local/lib"):
                            continue
                        if token.startswith("-L"):
                            token = "-L" + map_library_path(token[2:])
                        elif token.endswith(".la"):
                            token = map_library_path(token)
                        repaired.append(token)
                    return "dependency_libs='%s'" % shlex.join(repaired)

                text = re.sub(
                    r"^dependency_libs='([^']*)'$",
                    repair_dependency_libs,
                    text,
                    flags=re.MULTILINE)
                repaired = text.encode("utf-8", errors="surrogateescape")
                if repaired != original:
                    originals[path] = original
                    with open(path, "wb") as handle:
                        handle.write(repaired)
        except Exception:
            self._restore_dependency_libtool_metadata(originals)
            raise

        return originals

    @staticmethod
    def _restore_dependency_libtool_metadata(originals):
        for path, content in originals.items():
            with open(path, "wb") as handle:
                handle.write(content)

    # ── build ──────────────────────────────────────────────────────────────
    def build(self):
        self._apply_patches()
        src = self.source_folder
        workspace = getattr(self, "_mailutils_native_workspace", None)
        if workspace is None and os.path.isfile(self._native_workspace_marker()):
            with open(self._native_workspace_marker(), "r", encoding="utf-8") as handle:
                workspace = json.load(handle).get("workspace")

        if workspace:
            src = os.path.join(workspace, "src")
            build_folder = os.path.abspath(self.build_folder)

            def ignore_conan_build_folder(directory, names):
                return [name for name in names
                        if os.path.abspath(os.path.join(directory, name)) == build_folder]

            shutil.copytree(self.source_folder, src, symlinks=True,
                            ignore=ignore_conan_build_folder)
        self._restore_helper_modes(src)

        configure_options = [
            "--prefix=/usr/local",
            "--disable-python",
            "--disable-pam",
            "--without-readline",
            "--without-guile",
            "--without-gsasl",
            "--without-gssapi",
            "--without-tcp-wrappers",
            "--without-fribidi",
            "--without-dbm",
            "--without-gdbm",
            "--without-berkeley-db",
            "--without-ndbm",
            "--without-tokyocabinet",
            "--without-kyotocabinet",
            "--without-mysql",
            "--without-postgres",
            "--without-odbc",
            "--without-ldap",
        ]
        configure_options.append(
            "--enable-shared" if self.options.shared else "--disable-shared")
        dependency_metadata = self._repair_dependency_libtool_metadata()
        try:
            self.run("sh ./configure %s" % " ".join(configure_options),
                     env="conanbuild", cwd=src)
            self._run_make("make -j2", src)
            self._run_upstream_tests(src)

            staging = os.path.join(self.build_folder, "install-staging")
            shutil.rmtree(staging, ignore_errors=True)
            os.makedirs(staging, exist_ok=True)
            self._run_make(
                "make -j1 install DESTDIR=%s prefix=/usr/local" % shlex.quote(staging),
                src)
        finally:
            self._restore_dependency_libtool_metadata(dependency_metadata)

    def package(self):
        root = os.path.join(self.build_folder, "install-staging", "usr", "local")
        for subdir in PAYLOAD_DIRS:
            src = os.path.join(root, subdir)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(self.package_folder, subdir))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LESSER", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Keep the linker-produced OHOS ELF bytes intact.  Post-link RUNPATH
        # rewriting is unavailable on the device and can invalidate its code
        # signature; Conan's run environment supplies package/lib via
        # LD_LIBRARY_PATH for consumers and test_package.
        self._cleanup_native_workspace()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mailutils")
        self.cpp_info.set_property("pkg_config_name", "mailutils")
        self.cpp_info.libs = MUTILS_LIBS
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = ["share"]
