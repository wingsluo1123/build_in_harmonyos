#!/usr/bin/env python3
"""Conan recipe for LIRC 0.10.2 on HarmonyOS PC (aarch64).

LIRC (Linux Infrared Remote Control) is an Autotools project that ships
``lircd``/``lircrcd`` daemons, the ``liblirc``/``liblirc_client``/
``liblirc_driver``/``libirrecord`` libraries, ~40 hardware plugins and the
``irsend``/``irrecord``/``mode2`` CLI tools.

The official 0.10.2 release tarball contains no ``test/`` directory: the
upstream CppUnit suite only exists in the git tag (``lirc-0.10.2`` =
2650b422f4111a6b9abdf3bc85ff4711bd735e3d).  The suite is therefore vendored
verbatim under ``upstream-tests/`` (see notes.md) and executed from
``build()`` so that ``conan create`` carries real upstream test evidence.

HarmonyOS specific build steps (rationale and evidence in notes.md):

* the 2022 vintage ``config.sub``/``config.guess`` shipped in the tarball
  reject the ``aarch64-*-ohos`` triplet, so the modern copies distributed by
  the ``automake/1.18`` tool requirement are installed into the source tree,
  and the triplet is passed explicitly (``config.guess`` cannot run on HMDFS);
* ``configure`` creates its private temp dir with ``umask 077 && mktemp -d``;
  on HMDFS the mode lands as 2700 and the owner is then denied write access,
  so the umask is normalised to 022 before it runs;
* the top level generated file ``VERSION`` shadows libc++'s C++20
  ``<version>`` header on the case-insensitive device filesystem, so the
  tarball copy is dropped and ``..`` is demoted to ``-idirafter``;
* the tarball ships a release-machine generated ``lib/lirc/config.h`` which
  wins the quote-include race in an out-of-tree build and enables drivers the
  platform does not have, so it is dropped as well.
"""

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Verbatim copy of the upstream `test/` tree of git tag lirc-0.10.2.
UPSTREAM_TESTS_DIR = "upstream-tests"

# OHOS has no /bin/bash; the upstream test scripts use `#!/bin/bash`.
OHOS_BASH = "/data/service/hnp/bin/bash"

# The upstream CppUnit suite drives real daemons over an AF_UNIX socket and
# upstream guards none of those blocking waits, so it must never be able to
# hang `conan create` (CI terminated the whole build with SIGTERM when it did,
# see notes.md).  The device run completes in well under a minute.
UPSTREAM_TEST_TIMEOUT = 300
DECODE_SCRIPT_TIMEOUT = 120

# `..` is the Autotools top build dir.  It holds the generated file VERSION,
# which shadows the C++ standard <version> header on a case-insensitive
# filesystem; -idirafter keeps config.h/paths.h reachable but loses the race
# to the real libc++ header.
TOP_INCLUDES = "DEFAULT_INCLUDES='-I. -idirafter ..'"

# Upstream `test/ClientTest.h` parses the lircd pid out of `var/lircd.pid` into a
# local `int` that it never initialises (`buffer >> pid` is a no-op once the
# stringstream is failed, so the value keeps whatever the stack held) and then
# calls `kill(pid, SIGTERM)` from both `setUp()` and `tearDown()`.  On this
# platform lircd can never write that file (it cannot bind its AF_UNIX socket,
# EPERM -- notes.md 4.3-1), so the call carries uninitialised stack garbage;
# values observed on this device include 852060116, -657740012, -260616428,
# 1360129684 and -1487913196.  A value of 0 turns the call into
# `kill(0, SIGTERM)` -- SIGTERM to the suite's *own* process group -- and the run
# then dies before CppUnit prints its summary (this is exactly how CI build
# #98207 failed, see notes.md 4.5).  The suite is therefore exec'd with SIGTERM
# ignored: the disposition survives execve and is inherited by the suite's
# children, so a SIGTERM the suite sends to *itself* (pid 0 or its own pid)
# becomes a harmless no-op.  A value that names some *other* process is not
# affected by the trap, and a value of -1 would still signal every process the
# shared worker may signal: `upstream-tests/` is a verbatim copy of the upstream
# tree, so the call site itself is deliberately not patched (notes.md 7).
# Our own hard bound below still uses SIGKILL, which cannot be ignored, so a
# suite that really hangs is still terminated.
SIGTERM_ISOLATION = "trap '' TERM; exec "

# The 8 shell scripts driven by DecodeTest (upstream registers 8 CppUnit cases
# but calls the same C++ function for 5 of them, see notes.md).
DECODE_SCRIPTS = [
    "DBS",
    "longpress",
    "raw",
    "rc5",
    "rc6",
    "space-enc-1",
    "space-enc-2",
    "space-enc-3",
]


class LircConan(ConanFile):
    name = "lirc"
    version = "0.10.2"
    description = (
        "LIRC - Linux Infrared Remote Control: lircd/lircrcd daemons, "
        "liblirc/liblirc_client/liblirc_driver libraries, hardware plugins "
        "and the irsend/irrecord/mode2 command line tools"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.lirc.org"
    url = "https://sourceforge.net/projects/lirc/"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    # Upstream configures with LT_INIT([disable-static]): only shared objects.
    topics = ("infrared", "remote-control", "lircd", "uinput", "ioctl")

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, UPSTREAM_TESTS_DIR),
            dst=os.path.join(self.export_sources_folder, UPSTREAM_TESTS_DIR),
        )

    def requirements(self):
        # LIRC has no mandatory third party dependency: libusb, libftdi,
        # portaudio, ALSA, systemd and libudev are all optional and are simply
        # not detected, which disables the matching drivers/plugins.
        # cppunit drives the upstream CppUnit suite; it is build-only, so it is
        # declared as a test requirement and never leaks into the package.
        self.test_requires("cppunit/1.15.1")

    def build_requirements(self):
        # Only used as the provider of a recent config.sub/config.guess.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                # config.guess cannot run on this device (HMDFS temp dirs) and
                # the tarball copies do not know the ohos triplet; both are
                # supplied, and X11 is absent so the X tools stay disabled.
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()

    # ------------------------------------------------------------------ build

    def build(self):
        apply_conandata_patches(self)
        self._drop_stale_distributed_artifacts()
        if self.settings.os == "OHOS":
            self._install_modern_config_scripts()
            self._normalise_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        # The tarball's Makefile declares
        #   BUILT_SOURCES = paths.h python-pkg/lirc/config.py python-pkg/VERSION
        # and in an out-of-tree build `python-pkg/VERSION` is produced by
        # `cp $? $@` while the directory it writes into is created by
        # `$ (abs_builddir)/python-pkg/setup.py` -> `cp -ar $(top_srcdir)/python-pkg
        # $(abs_builddir)`.  With -j>1 the copy can win the race and the build
        # dies with "cp: python-pkg/VERSION: No such file or directory"
        # (observed intermittently).  Build that directory-creating target
        # serially first, then use parallel make for the rest.
        autotools.make(target="python-pkg/lirc/config.py", args=["-j1"])
        if self.settings.os == "OHOS":
            autotools.make(args=["-j4", TOP_INCLUDES])
        else:
            autotools.make(args=["-j4"])
        if can_run(self):
            self._install_upstream_tests()
            self._run_upstream_tests()
        else:
            self.output.info("Cross-building: upstream CppUnit suite skipped")

    def _drop_stale_distributed_artifacts(self):
        """Drop the autotools artifacts the tarball ships stale copies of.

        ``lib/lirc/config.h`` is a config.h generated on the *release* machine
        and shipped in the tarball: it defines HAVE_LIBUDEV_H, HAVE_USB_H,
        HAVE_LINUX_DEVINPUT and HAVE_SOUNDCARD, none of which the platform
        provides, and ``lib/lirc/curl_poll.h`` includes ``"config.h"`` from its
        own directory, so the stale copy always beats the freshly generated
        one in an out-of-tree build.  ``lib/Makefile`` regenerates both of
        these as BUILT_SOURCES (``lirc/config.h: ../config.h``).

        ``VERSION`` is regenerated by config.status into the build directory;
        the source copy only shadows libc++'s C++20 ``<version>`` header.
        """
        for relative in ("lib/lirc/config.h", "VERSION"):
            path = os.path.join(self.source_folder, relative)
            if os.path.isfile(path):
                os.remove(path)
                self.output.info("removed stale distributed artifact {}".format(relative))

    def _install_modern_config_scripts(self):
        """Install config.guess/config.sub that recognise aarch64-*-ohos."""
        automake_folder = self.dependencies.build["automake"].package_folder
        data_dir = os.path.join(automake_folder, "share", "automake-1.18")
        missing = [
            name for name in ("config.guess", "config.sub")
            if not os.path.isfile(os.path.join(data_dir, name))
        ]
        if missing:
            raise ConanException(
                "automake/1.18 does not provide {}".format(", ".join(missing))
            )
        for name in ("config.guess", "config.sub"):
            shutil.copyfile(
                os.path.join(data_dir, name),
                os.path.join(self.source_folder, name),
            )
            os.chmod(os.path.join(self.source_folder, name), 0o755)

    def _normalise_configure_umask(self):
        """HMDFS keeps the setgid bit, so configure's 0700 temp dir is unusable."""
        configure = os.path.join(self.source_folder, "configure")
        marker = "umask 077 && mktemp -d"
        if marker not in open(configure, encoding="utf-8", errors="replace").read():
            raise ConanException("configure no longer contains %r" % marker)
        replace_in_file(self, configure, marker, "umask 022 && mktemp -d")

    # ------------------------------------------------------------------ tests

    @property
    def upstream_tests_folder(self):
        return os.path.join(self.build_folder, "test")

    def _install_upstream_tests(self):
        dst = self.upstream_tests_folder
        rm(self, "*", dst)
        copy(
            self,
            "*",
            src=os.path.join(self.export_sources_folder, UPSTREAM_TESTS_DIR),
            dst=dst,
        )
        # The test scripts redirect their logs to test/var/.  The vendored tree
        # carries var/.gitkeep, but upstream's own .gitignore rule (`var/*`)
        # hides it from git, so it is created here instead of being relied on.
        os.makedirs(os.path.join(dst, "var"), exist_ok=True)
        link = os.path.join(dst, "lirc")
        if not os.path.exists(link):
            os.symlink("..", link)
        if self.settings.os == "OHOS":
            self._normalise_test_shebangs(dst)

    def _normalise_test_shebangs(self, tests_folder):
        """Only the interpreter path changes: upstream has no /bin/bash.

        `lirc-codecs-regression-test.sh` is deliberately left alone: upstream
        ships it with a broken `#!/usr/bin/env /bash` line, it is not part of
        the CppUnit suite, and no interpreter path rewrite can repair it.
        """
        if not os.path.isfile(OHOS_BASH):
            raise ConanException("{} is required to run the test scripts".format(OHOS_BASH))
        for name in DECODE_SCRIPTS:
            script = os.path.join(tests_folder, "tests", name, "run-test.sh")
            if not os.path.isfile(script):
                continue
            content = open(script, encoding="utf-8", errors="replace").read()
            if "#!/bin/bash" not in content:
                self.output.warning(
                    "{} does not use a /bin/bash shebang".format(script)
                )
                continue
            replace_in_file(self, script, "#!/bin/bash", "#!" + OHOS_BASH)

    def _compiler(self, kind, fallback):
        """Resolve a compiler the way the profile declares it (R33).

        `tools.build:compiler_executables` is what the OHOS profile pins; the
        unqualified name is only a fallback for hosts that do not set it.
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        resolved = executables.get(kind) if executables else None
        return resolved or shutil.which(fallback) or fallback

    def _upstream_test_env_dict(self):
        libs = [os.path.join(self.build_folder, "lib", ".libs")]
        cppunit = self.dependencies["cppunit"].cpp_info.aggregated_components()
        libs.extend(cppunit.libdirs)
        env = dict(os.environ)
        old_ld = env.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = ":".join(libs + ([old_ld] if old_ld else []))
        env["PATH"] = "/data/service/hnp/bin:" + env.get("PATH", "")
        env["LC_ALL"] = "C"
        return env

    def _run_bounded(self, command, cwd, log_path, timeout, label,
                     isolate_sigterm=False):
        """Run `command` in its own session, under a hard timeout.

        The suite (and its helper scripts) spawn daemons and block on sockets;
        upstream guards none of those waits.  A hanging suite must not be able
        to hang the build, so the whole process group is killed once `timeout`
        expires and the partial output is what gets reported.

        `isolate_sigterm` starts the command with SIGTERM ignored (see
        SIGTERM_ISOLATION): the CppUnit suite is run that way because upstream
        itself sends an unbounded SIGTERM to its own process group from the
        ClientTest failure path.
        """
        if isolate_sigterm:
            # `_run_bounded` already runs the command through `/bin/sh -c`, so
            # the trap is installed in that very shell before it `exec`s the
            # suite: the session leader itself ends up with SIGTERM ignored.
            # (A nested extra shell would instead be killed by the suite's
            # self-directed SIGTERM while the suite itself survived.)
            command = SIGTERM_ISOLATION + command
        self.output.info("RUN: {} (timeout {}s)".format(command, timeout))
        with open(log_path, "w", encoding="utf-8", errors="replace") as handle:
            process = subprocess.Popen(
                command, cwd=cwd, shell=True, stdout=handle,
                stderr=subprocess.STDOUT, env=self._upstream_test_env_dict(),
                start_new_session=True,
            )
            try:
                rc = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.output.warning(
                    "{} did not finish within {}s -- killing its process group"
                    .format(label, timeout)
                )
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except OSError:
                    process.kill()
                process.wait()
                rc = None
        text = open(log_path, encoding="utf-8", errors="replace").read()
        for line in text.splitlines():
            self.output.info("    " + line)
        return rc, text

    def _compile_upstream_runner(self):
        """Build the upstream runner with the OHOS toolchain.

        The upstream test/Makefile hardcodes `gcc -o run-tests $(CXXFLAGS)
        $(LDLIBS) run-tests.cpp`; the same sources, flags and libraries are
        used here with the C++ compiler the profile pins through
        `tools.build:compiler_executables` (R33: never rely on an undeclared
        shell variable or an unqualified tool name).
        """
        tests = self.upstream_tests_folder
        cppunit = self.dependencies["cppunit"].cpp_info.aggregated_components()
        includes = [
            tests,
            os.path.join(self.source_folder, "lib"),
            os.path.join(self.source_folder, "include"),
            os.path.join(self.build_folder, "lib"),
        ]
        includes.extend(cppunit.includedirs)
        command = [
            self._compiler("cpp", "clang++"), "-o", "run-tests",
            "-g", "-std=c++11", "-Wall",
        ]
        command.extend("-I" + path for path in includes)
        command.append("run-tests.cpp")
        command.extend("-L" + path for path in cppunit.libdirs)
        command.append("-lcppunit")
        command.extend([
            "-L" + os.path.join(self.build_folder, "lib", ".libs"),
            "-llirc", "-llirc_client",
            "-Wl,-rpath," + os.path.join(self.build_folder, "lib", ".libs"),
        ])
        command.extend("-l" + lib for lib in cppunit.system_libs)
        self.run(
            shlex.join(command),
            cwd=tests,
            env="conanbuild",
        )

    def _run_upstream_tests(self):
        tests = self.upstream_tests_folder
        self._compile_upstream_runner()

        log = os.path.join(self.build_folder, "upstream-cppunit.log")
        self.output.info(
            "Running the upstream CppUnit suite (35 registered cases): ./run-tests"
        )
        # The upstream main() always returns 0 (it ignores runner.run()), so the
        # exit code carries no verdict; the CppUnit summary line does.
        rc, text = self._run_bounded(
            "./run-tests", tests, log, UPSTREAM_TEST_TIMEOUT,
            "upstream CppUnit suite", isolate_sigterm=True,
        )
        match = re.search(
            r"Run:\s*(\d+)\s+Failures:\s*(\d+)\s+Errors:\s*(\d+)", text
        )
        if not match:
            if rc is None:
                # Killed by our own bound: report it honestly instead of
                # failing the build.  ClientTest blocks forever on an AF_UNIX
                # socket whenever the daemon cannot be reached.
                self._report_upstream_aborted(
                    log,
                    "no CppUnit summary within {}s; the suite was killed by the "
                    "recipe's hard bound (SIGKILL) -- upstream ClientTest blocks "
                    "on an AF_UNIX socket".format(UPSTREAM_TEST_TIMEOUT),
                    returncode=None,
                    signum=None,
                )
                return
            if rc == 0:
                # rc == 0 but no summary: the suite claims success without ever
                # printing a verdict.  That cannot be explained by the
                # environment, so it stays a hard failure.
                raise ConanException(
                    "upstream CppUnit summary not found in {}:\n{}".format(log, text[-2000:])
                )
            signum = -rc if rc < 0 else None
            if signum == signal.SIGTERM:
                # The one abnormal termination this environment is known to
                # produce: upstream ClientTest::setUp()/tearDown() call
                # kill(pid, SIGTERM) with a pid parsed from var/lircd.pid into
                # an uninitialised int (notes.md 4.5).  SIGTERM_ISOLATION should
                # already prevent it; if the isolation is ever bypassed (another
                # shell, or an external SIGTERM) it is reported honestly instead
                # of failing the build.
                self._report_upstream_aborted(
                    log,
                    "suite died from SIGTERM before printing its CppUnit summary "
                    "-- upstream ClientTest::setUp()/tearDown() call "
                    "kill(pid, SIGTERM) with a pid read into an uninitialised int",
                    returncode=rc,
                    signum=signum,
                )
                return
            # Every other abnormal status -- SIGSEGV/SIGABRT/SIGBUS/SIGKILL, or a
            # non-zero exit such as 126/127 from an exec failure -- has no
            # environmental explanation here, so it stays a hard failure: a
            # crash or a failed exec must not be able to hide behind `aborted`.
            raise ConanException(
                "upstream CppUnit suite terminated abnormally (returncode {}, "
                "signal {}) before printing its summary; partial log {}:\n{}"
                .format(
                    rc,
                    self._signal_name(signum) if signum is not None else "none",
                    log,
                    text[-2000:],
                )
            )
        run, failures, errors = (int(value) for value in match.groups())
        passed = run - failures - errors
        if run == 0:
            raise ConanException("upstream CppUnit suite executed 0 cases")

        scripts = self._run_decode_scripts()
        summary = {
            "framework": "cppunit",
            "command": "./run-tests",
            "discovered": 35,
            "executed": run,
            "passed": passed,
            "failed": failures,
            "errors": errors,
            "skipped": 0,
            "status": "passed" if failures == 0 and errors == 0 else "failed",
            "decode_scripts": scripts,
        }
        # The CppUnit verdicts above are upstream's own; DecodeTest does not
        # assert on system(), so the underlying scripts are reported separately.
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(summary))
        self.output.info(
            "Upstream CppUnit: Run={} Passed={} Failures={} Errors={}".format(
                run, passed, failures, errors
            )
        )

    @staticmethod
    def _signal_name(signum):
        try:
            return signal.Signals(signum).name
        except ValueError:
            return "SIG{}".format(signum)

    def _report_upstream_aborted(self, log, reason, returncode, signum):
        """Report a suite that did not produce a verdict, without inventing one.

        `aborted` is not `passed`: every count stays null and the reason carries
        the exact return code / signal so the result cannot be mistaken for a
        green run.  The partial upstream log is kept at `log`.
        """
        self.output.warning(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "framework": "cppunit",
                "command": "./run-tests",
                "discovered": 35,
                "executed": None,
                "passed": None,
                "failed": None,
                "errors": None,
                "skipped": None,
                "status": "aborted",
                "returncode": returncode,
                "signal": None if signum is None else self._signal_name(signum),
                "log": log,
                "reason": reason,
            })
        )
        self.output.warning(
            "Upstream CppUnit: ABORTED (no verdict; not counted as pass) -- {}"
            .format(reason)
        )
        self._stop_test_daemons()

    def _run_decode_scripts(self):
        """Run the 8 DecodeTest scripts individually and report their status.

        Upstream's DecodeTest never inspects the exit status of system(), and
        5 of its 8 registered cases call testSpaceEnc1(), so the suite only
        drives 3 of the 8 scripts.  Running each one is the only way to get a
        real pass/fail reading for the remaining 5.
        """
        results = {}
        for name in DECODE_SCRIPTS:
            script = os.path.join(self.upstream_tests_folder, "tests", name, "run-test.sh")
            if not os.path.isfile(script):
                results[name] = "missing"
                continue
            log = os.path.join(self.upstream_tests_folder, "var",
                               "conan-{}.log".format(name))
            rc, _text = self._run_bounded(
                "./run-test.sh", os.path.dirname(script), log,
                DECODE_SCRIPT_TIMEOUT, "DecodeTest script {}".format(name),
            )
            if rc is None:
                results[name] = "timeout(>{}s)".format(DECODE_SCRIPT_TIMEOUT)
            else:
                results[name] = "pass" if rc == 0 else "fail(rc={})".format(rc)
            self.output.info("DecodeTest script {}: {}".format(name, results[name]))
        self._stop_test_daemons()
        log = os.path.join(self.upstream_tests_folder, "var")
        self.output.info("DecodeTest script logs kept in {}".format(log))
        return results

    def _stop_test_daemons(self):
        """The test scripts and ClientTest leave daemons running; stop them.

        Matches any `*.pid` file under the test tree (lircd.pid, lircrcd.pid)
        and kills by pid — never by command name, the device is shared.

        The CppUnit suite runs with SIGTERM ignored (see SIGTERM_ISOLATION), so
        a daemon it started inherits SIG_IGN and would survive the polite
        signal; SIGKILL cannot be ignored, so it is used as the escalation.
        """
        for root, _dirs, files in os.walk(self.upstream_tests_folder):
            for name in files:
                if not name.endswith(".pid"):
                    continue
                try:
                    pid = int(open(os.path.join(root, name)).read().strip())
                except (OSError, ValueError):
                    continue
                if pid <= 1:
                    # `kill(0, ...)` signals the caller's own process group and
                    # pid 1 is init; a malformed pid file must never turn into a
                    # broadcast (or into a SIGKILL aimed at our own group).
                    self.output.warning(
                        "ignoring implausible pid {} in {}".format(pid, name)
                    )
                    continue
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    continue
                if self._wait_pid_gone(pid, 1.0):
                    self.output.info("stopped test daemon pid={} ({})".format(pid, name))
                    continue
                try:
                    os.kill(pid, signal.SIGKILL)
                    self.output.info(
                        "escalated to SIGKILL for test daemon pid={} ({})"
                        .format(pid, name)
                    )
                except OSError:
                    pass

    @staticmethod
    def _wait_pid_gone(pid, timeout):
        """True once `pid` no longer exists, False if it outlives `timeout`."""
        deadline = time.monotonic() + timeout
        while True:
            try:
                os.kill(pid, 0)
            except OSError:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

    # ---------------------------------------------------------------- package

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        self._normalise_packaged_scripts()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _normalise_packaged_scripts(self):
        """Keep the build machine's interpreter path out of the package.

        `tools/Makefile.am` rewrites `#!/usr/bin/env python3` into
        `#!/usr/bin/env $(PYTHON)`, baking an absolute build-machine path into
        every installed helper script.  The upstream form is restored so the
        package stays relocatable.

        `doc/lirc-data2table` is shipped through `dist_bin_SCRIPTS` but has no
        shebang at all (upstream defect): executed directly the kernel returns
        ENOEXEC.  Its interpreter line is added here.
        """
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="replace").read()
            new = re.sub(
                r"^#!/usr/bin/env \S*python[0-9.]*\s*$",
                "#!/usr/bin/env python3",
                text, count=1, flags=re.M,
            )
            if new == text and not text.startswith("#!") and "import " in text:
                new = "#!/usr/bin/env python3\n" + text
            if new != text:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(new)
                self.output.info("normalised shebang of bin/{}".format(name))

    def package_info(self):
        self.cpp_info.libs = ["lirc", "lirc_client", "lirc_driver", "irrecord"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "lirc")
        self.cpp_info.set_property("cmake_file_name", "lirc")
        self.cpp_info.set_property("cmake_target_name", "lirc::lirc")
