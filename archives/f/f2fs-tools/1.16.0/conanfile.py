from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import re
import shlex
import shutil
import stat
import subprocess


def _autotools_arch(settings):
    return {
        "armv8": "aarch64",
        "armv7": "armv7",
        "armv7hf": "armv7",
        "x86_64": "x86_64",
        "x86": "i686",
    }.get(str(settings.arch), str(settings.arch))


def _autotools_triplet(settings):
    """Return an explicit GNU triplet for supported build/host profiles."""
    arch = _autotools_arch(settings)
    os_name = str(settings.os)
    if os_name == "OHOS":
        return f"{arch}-unknown-linux-ohos"
    if os_name == "Linux":
        return f"{arch}-unknown-linux-gnu"
    return None


def _relax_configure_tmp_umask(configure_path, output):
    """Avoid owner-only Autoconf temp directories on the OHOS FUSE worker."""
    try:
        with open(configure_path, "rb") as source:
            configure = source.read()
    except OSError as error:
        output.warning(f"AUTOTOOLS-UMASK: could not read generated configure: {error}")
        return

    replacements = (
        (
            b'(umask 077 && mktemp -d "./confXXXXXX")',
            b'(umask 000 && mktemp -d "./confXXXXXX")',
        ),
        (b'(umask 077 && mkdir "$tmp")', b'(umask 000 && mkdir "$tmp")'),
    )
    changed = False
    for original, replacement in replacements:
        count = configure.count(original)
        if count:
            configure = configure.replace(original, replacement)
            output.info(
                f"AUTOTOOLS-UMASK: relaxed {count} generated configure temp-dir mode(s)"
            )
            changed = True
        else:
            output.warning(
                "AUTOTOOLS-UMASK: expected restrictive configure temp-dir pattern "
                "was absent; continuing with the scoped umask and writable TMPDIR"
            )

    if changed:
        try:
            with open(configure_path, "wb") as target:
                target.write(configure)
        except OSError as error:
            output.warning(f"AUTOTOOLS-UMASK: could not update generated configure: {error}")


class F2fsToolsConan(ConanFile):
    name = "f2fs-tools"
    version = "1.16.0"
    description = "Utilities for creating, checking, resizing, and inspecting F2FS filesystems"
    license = "GPL-2.0-only AND LGPL-2.0-only"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def build_requirements(self):
        # GitHub source archives omit configure; the build worker must not
        # depend on whichever Autotools happen to be installed on its PATH.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")

    def requirements(self):
        # These are the libraries probed by configure.ac / linked from mkfs and fsck.
        self.requires("libuuid/2.42.2")
        self.requires("libblkid/2.42.2")
        self.requires("libselinux/3.10.1")
        self.requires("lzo2/2.10")
        self.requires("lz4/1.10.0.3")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        host_triplet = _autotools_triplet(self.settings)
        build_triplet = _autotools_triplet(self.settings_build)
        if str(self.settings.os) == "OHOS":
            build_triplet = build_triplet or host_triplet
            if build_triplet == host_triplet:
                # The CI Conan build profile is also OHOS/AArch64. Equal
                # triplets make Autoconf try to execute conftest from the
                # worker's FUSE-backed package tree. Keep the real OHOS host
                # triplet but use the GNU/Linux build alias to select the
                # cross-compile path and skip target-program probes.
                arch = _autotools_arch(self.settings_build)
                build_triplet = f"{arch}-unknown-linux-gnu"
        if build_triplet and host_triplet:
            tc.configure_args.extend(
                [f"--build={build_triplet}", f"--host={host_triplet}"]
            )
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
            "--with-blkid",
            "--with-selinux",
            "--with-lzo2",
            "--with-lz4",
        ])
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _bootstrap_tool(self, dependency, executable):
        """Prefer the declared build tool package, then the generated PATH."""
        package_folder = None
        try:
            package_folder = self.dependencies.build[dependency].package_folder
        except (AttributeError, KeyError, TypeError):
            pass
        if package_folder:
            candidate = os.path.join(package_folder, "bin", executable)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(executable) or executable

    def _bootstrap_environment(self):
        """Use native Perl and only the pure-Perl Autotools module trees.

        The Conan Perl package can carry XS modules that fail to load from an
        HMDFS build directory. Prefer the device HNP Perl and clear inherited
        Perl overrides before exposing the modules shipped by Autoconf and
        Automake.
        """
        automake_folder = self.dependencies.build["automake"].package_folder
        autoconf_folder = self.dependencies.build["autoconf"].package_folder
        libtool_folder = self.dependencies.build["libtool"].package_folder
        automake_share = os.path.join(automake_folder, "share", "automake-1.18")
        autoconf_share = os.path.join(autoconf_folder, "share", "autoconf")
        perl_modules = f"{automake_share}:{autoconf_share}"

        native_perl = "/data/service/hnp/bin/perl"
        perl = native_perl if os.path.isfile(native_perl) else (shutil.which("perl") or "perl")
        m4 = self._bootstrap_tool("m4", "m4")
        aclocal_dirs = [
            os.path.join(automake_folder, "share", "aclocal"),
            os.path.join(libtool_folder, "share", "aclocal"),
        ]
        assignments = [
            f"PERL={shlex.quote(perl)}",
            f"PERL5LIB={shlex.quote(perl_modules)}",
            "PERL5OPT=",
            "PERL_LOCAL_LIB_ROOT=",
            f"M4={shlex.quote(m4)}",
            f"ACLOCAL_PATH={shlex.quote(':'.join(aclocal_dirs))}",
        ]
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            assignments.append(f"PATH={shlex.quote(hnp_bin)}:\"$PATH\"")
        return " ".join(assignments)

    def _report_sha512_tests(self):
        """Report every upstream KAT without turning environment gaps into raises."""
        sha_source = os.path.join(self.source_folder, "tools", "sha512.c")
        test_bin = os.path.join(self.build_folder, "f2fs-sha512-unittest")
        cases = {index: None for index in range(3)}

        if not os.path.isfile(sha_source):
            raw = f"未执行：upstream test source is absent: {sha_source}"
            for index in cases:
                cases[index] = ("SKIP", raw)
        else:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = str(executables.get("c", "cc"))
            compile_log = os.path.join(self.build_folder, "upstream-sha512-compile.log")
            compile_exit = os.path.join(self.build_folder, "upstream-sha512-compile.exit")
            command = (
                f"{shlex.quote(cc)} -DUNITTEST {shlex.quote(sha_source)} "
                f"-o {shlex.quote(test_bin)} > {shlex.quote(compile_log)} 2>&1; "
                f"status=$?; printf '%s\\n' \"$status\" > {shlex.quote(compile_exit)}; exit 0"
            )
            try:
                self.run(command, cwd=self.build_folder, env="conanbuild", quiet=True)
            except Exception as error:
                raw = f"not executed: Conan build environment could not start the compiler check: {error}"
                for index in cases:
                    cases[index] = ("SKIP", raw)
                self._print_sha512_results(cases)
                return

            try:
                with open(compile_exit, "r", encoding="utf-8") as stream:
                    compile_status = int(stream.read().strip())
            except (OSError, ValueError) as error:
                compile_status = 127
                compile_raw = f"compiler result unavailable: {error}"
            else:
                try:
                    with open(compile_log, "r", encoding="utf-8", errors="replace") as stream:
                        compile_raw = stream.read().strip()
                except OSError as error:
                    compile_raw = f"compiler log unavailable: {error}"

            if compile_status:
                status = "SKIP" if compile_status in (126, 127) else "FAIL"
                raw = compile_raw or f"compiler exited with status {compile_status}"
                for index in cases:
                    cases[index] = (status, raw)
            else:
                try:
                    result = subprocess.run(
                        [test_bin], cwd=self.build_folder, capture_output=True,
                        text=True, check=False,
                    )
                except OSError as error:
                    raw = f"test executable could not run: {error}"
                    for index in cases:
                        cases[index] = ("SKIP", raw)
                else:
                    combined = result.stdout + result.stderr
                    found = {
                        int(index): status
                        for index, status in re.findall(
                            r"SHA512 test message (\d+): (OK|FAILED)", combined
                        )
                    }
                    for index in cases:
                        state = found.get(index)
                        if state == "OK" and result.returncode == 0:
                            cases[index] = ("PASS", "")
                        elif state == "FAILED" or result.returncode != 0:
                            cases[index] = ("FAIL", combined.strip() or "SHA-512 vector reported FAILED")
                        else:
                            raw = combined.strip() or f"test executable exited {result.returncode} without vector output"
                            cases[index] = ("FAIL", raw)

        self._print_sha512_results(cases)

    @staticmethod
    def _print_sha512_results(cases):
        passed = failed = notrun = 0
        for index, (status, raw) in cases.items():
            print(f"UPSTREAM-CASE SHA512-KAT-{index:02d} {status}")
            if raw:
                print(f"UPSTREAM-RAW-OUTPUT SHA512-KAT-{index:02d}: {raw}")
            passed += status == "PASS"
            failed += status == "FAIL"
            notrun += status == "SKIP"
        print(
            f"UPSTREAM-SUMMARY total={len(cases)} pass={passed} "
            f"fail={failed} notrun={notrun}"
        )

    def build(self):
        apply_conandata_patches(self)
        # This release archive has configure.ac but no generated configure.
        # Run the declared Autotools stack rather than relying on host aclocal.
        autoreconf = self._bootstrap_tool("autoconf", "autoreconf")
        self.run(
            f"{self._bootstrap_environment()} {shlex.quote(autoreconf)} -fiv",
            cwd=self.source_folder,
            env="conanbuild",
        )

        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            try:
                mode = os.stat(configure).st_mode
                if not mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                    os.chmod(configure, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError as error:
                self.output.warning(f"AUTOTOOLS-CONFIGURE: could not set executable bit: {error}")
            executable = os.access(configure, os.X_OK)
            self.output.info(
                f"AUTOTOOLS-CONFIGURE: path={configure} exists=true "
                f"executable={str(executable).lower()}"
            )
        else:
            self.output.warning(
                f"AUTOTOOLS-CONFIGURE: generated configure is absent at {configure}; "
                "continuing so Conan reports the actual configure invocation outcome"
            )

        autotools = Autotools(self)
        # Autoconf's generated temporary directories inherit a restrictive
        # umask and the worker's shared TMPDIR can be unwritable on FUSE.
        # Scope a permissive umask and a writable, build-local TMPDIR to this
        # configure call only, restoring both before build/package steps.
        configure_tmp = os.path.join(self.build_folder, "f2fs-tools-configure-tmp")
        previous_tmpdir = os.environ.get("TMPDIR")
        previous_umask = os.umask(0)
        try:
            try:
                os.makedirs(configure_tmp, mode=0o777, exist_ok=True)
                os.chmod(configure_tmp, 0o777)
            except OSError as error:
                self.output.warning(
                    f"AUTOTOOLS-TMPDIR: could not prepare {configure_tmp}: {error}"
                )
            os.environ["TMPDIR"] = configure_tmp
            self.output.info(f"AUTOTOOLS-TMPDIR: path={configure_tmp} mode=0777")
            if os.path.isfile(configure):
                _relax_configure_tmp_umask(configure, self.output)
            autotools.configure()
        finally:
            os.umask(previous_umask)
            if previous_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = previous_tmpdir
        autotools.make(args=["-j2"])

        # The upstream source contains three SHA-512 known-answer vectors behind
        # UNITTEST, but does not register them in Automake/CI. Run that exact
        # upstream self-test explicitly and preserve a per-vector result line.
        self._report_sha512_tests()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
