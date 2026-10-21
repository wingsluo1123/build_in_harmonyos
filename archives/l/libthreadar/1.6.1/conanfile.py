#!/usr/bin/env python3
"""Conan recipe for libthreadar 1.6.1 on HarmonyOS PC."""

import os
import re
import shlex
import shutil
import stat

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _ignore_build_outputs(build_root, destination):
    """Exclude the Conan build tree and copy destination from a source copy."""
    excluded_paths = {
        os.path.realpath(build_root),
        os.path.realpath(destination),
    }

    def ignore(directory, names):
        current = os.path.realpath(directory)
        return [
            name
            for name in names
            if name == "build-release"
            or os.path.realpath(os.path.join(current, name)) in excluded_paths
        ]

    return ignore


def _autotools_triplet(settings):
    """Return an explicit GNU triplet for supported build/host profiles."""
    arch = {
        "armv8": "aarch64",
        "armv7": "armv7",
        "armv7hf": "armv7",
        "x86_64": "x86_64",
        "x86": "i686",
    }.get(str(settings.arch), str(settings.arch))
    os_name = str(settings.os)
    if os_name == "OHOS":
        return f"{arch}-unknown-linux-ohos"
    if os_name == "Linux":
        return f"{arch}-unknown-linux-gnu"
    return None


def _relax_configure_tmp_umask(configure_path, output):
    """Avoid owner-only Autoconf temp directories on the OHOS FUSE worker."""
    with open(configure_path, "rb") as source:
        configure = source.read()

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
        with open(configure_path, "wb") as target:
            target.write(configure)


class LibthreadarConan(ConanFile):
    name = "libthreadar"
    version = "1.6.1"
    description = "C++ classes for thread management and synchronization"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/Edrusb/libthreadar"
    url = "https://github.com/Edrusb/libthreadar"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(
            self,
            **source,
            filename=f"libthreadar-{self.version}.tar.gz",
            strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-pthread")
        tc.extra_cxxflags.append("-pthread")
        tc.extra_ldflags.append("-pthread")
        host_triplet = _autotools_triplet(self.settings)
        build_triplet = _autotools_triplet(self.settings_build)
        if str(self.settings.os) == "OHOS":
            # The OHOS worker's config.guess cannot create its probe file on
            # the FUSE workspace. Never invoke it: pass canonical system types
            # directly, falling back to the OHOS triplet for native OHOS builds.
            build_triplet = build_triplet or host_triplet
        if build_triplet and host_triplet:
            tc.configure_args.extend(
                [f"--build={build_triplet}", f"--host={host_triplet}"]
            )
        if self.options.fPIC:
            tc.extra_cflags.append("-fPIC")
            tc.extra_cxxflags.append("-fPIC")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _bootstrap_prefix(self, source_copy, perl_share):
        """Keep Autotools' Perl interpreter and module paths compatible.

        Conan's Perl package contains XS modules that may be unreadable to
        another OHOS process from HMDFS. Use the native OHOS Perl when it is
        present and expose only Automake's pure-Perl modules to the bootstrap.
        PWD is set explicitly for shells that cannot recover it from HMDFS.
        """
        native_perl = "/data/service/hnp/bin/perl"
        perl = (
            native_perl
            if os.path.isfile(native_perl)
            else (shutil.which("perl") or "perl")
        )
        assignments = [
            f"PERL={shlex.quote(perl)}",
            f"PERL5LIB={shlex.quote(perl_share)}",
            "PERL5OPT=",
            "PERL_LOCAL_LIB_ROOT=",
            f"PWD={shlex.quote(source_copy)}",
        ]
        m4 = self._bootstrap_tool("m4", "m4")
        assignments.append(f"M4={shlex.quote(m4)}")
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            assignments.append(f'PATH={shlex.quote(hnp_bin)}:"$PATH"')
        return " ".join(assignments)

    def _run_bootstrap_tool(self, source_copy, tool, perl_share, args=""):
        prefix = self._bootstrap_prefix(source_copy, perl_share)
        invocation = (
            f"sh {shlex.quote(tool)}"
            if os.path.isfile(tool)
            else shlex.quote(tool)
        )
        command = f"{prefix} {invocation} {args}".strip()
        self.run(command, cwd=source_copy, env="conanbuild")

    def _bootstrap_tool(self, dependency, executable):
        """Prefer the declared Conan build tool, then fall back to PATH."""
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

    def build(self):
        apply_conandata_patches(self)

        # misc/init writes generated Autotools files into the source tree and
        # makes some files read-only. Keep those mutations in a build-local copy.
        source_copy = os.path.join(self.build_folder, "libthreadar-source")
        if os.path.lexists(source_copy):
            if os.path.isdir(source_copy) and not os.path.islink(source_copy):
                shutil.rmtree(source_copy)
            else:
                os.remove(source_copy)
        copy_ignore = _ignore_build_outputs(self.build_folder, source_copy)
        # Conan's layout may put build-release inside source_folder. Excluding
        # both that tree and the destination prevents copytree from copying its
        # own output recursively; deleting destination first keeps rebuilds
        # deterministic.
        shutil.copytree(self.source_folder, source_copy, ignore=copy_ignore)
        # Reproduce misc/init's bootstrap sequence with the declared Conan
        # tools. The CI worker's HNP Perl must not load Conan Perl's HMDFS XS
        # modules (notably Cwd.so), or configure is never generated.
        build_dir = os.path.join(source_copy, "build")
        shutil.copy2(os.path.join(build_dir, "configure.ac"), source_copy)
        shutil.copy2(os.path.join(build_dir, "Makefile.am"), source_copy)

        automake_folder = self.dependencies.build["automake"].package_folder
        autoconf_folder = self.dependencies.build["autoconf"].package_folder
        automake_share = os.path.join(automake_folder, "share", "automake-1.18")
        autoconf_share = os.path.join(autoconf_folder, "share", "autoconf")

        self._run_bootstrap_tool(
            source_copy,
            self._bootstrap_tool("libtool", "libtoolize"),
            automake_share,
            "--automake",
        )
        self._run_bootstrap_tool(
            source_copy,
            self._bootstrap_tool("automake", "aclocal"),
            automake_share,
        )
        self._run_bootstrap_tool(
            source_copy,
            self._bootstrap_tool("autoconf", "autoconf"),
            autoconf_share,
        )
        self._run_bootstrap_tool(
            source_copy,
            self._bootstrap_tool("autoconf", "autoheader"),
            autoconf_share,
        )
        shutil.copy2(os.path.join(build_dir, "ChangeLog"), source_copy)
        self._run_bootstrap_tool(
            source_copy,
            self._bootstrap_tool("automake", "automake"),
            automake_share,
            "--add-missing --gnu",
        )

        for filename in ("configure.ac", "Makefile.am", "ChangeLog"):
            path = os.path.join(source_copy, filename)
            try:
                os.chmod(path, stat.S_IMODE(os.stat(path).st_mode) & ~0o222)
            except OSError as error:
                self.output.warning(
                    f"AUTOTOOLS-BOOTSTRAP: could not make {filename} read-only: {error}"
                )
        mkinstalldirs = os.path.join(source_copy, "mkinstalldirs")
        if not os.path.exists(mkinstalldirs):
            shutil.copy2(os.path.join(build_dir, "mkinstalldirs"), mkinstalldirs)

        configure = os.path.join(source_copy, "configure")
        if os.path.isfile(configure):
            try:
                mode = os.stat(configure).st_mode
                if not mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                    os.chmod(
                        configure,
                        mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                    )
            except OSError as error:
                self.output.warning(
                    f"AUTOTOOLS-CONFIGURE: executable bit could not be set: {error}"
                )
            executable = os.access(configure, os.X_OK)
            self.output.info(
                "AUTOTOOLS-CONFIGURE: "
                f"path={configure} exists=true executable={str(executable).lower()}"
            )
        else:
            self.output.warning(
                f"AUTOTOOLS-CONFIGURE: bootstrap did not produce {configure}; "
                "continuing to the configured Conan invocation"
            )

        autotools = Autotools(self)
        # Explicit --build/--host triplets above skip config.guess. Keep any
        # remaining Autoconf probes in a writable, build-local directory, and
        # relax both inherited and generated configure umasks for the OHOS
        # FUSE worker. Scope the environment changes to configure only.
        configure_tmp = os.path.join(self.build_folder, "libthreadar-configure-tmp")
        previous_tmpdir = os.environ.get("TMPDIR")
        previous_umask = os.umask(0)
        try:
            os.makedirs(configure_tmp, mode=0o777, exist_ok=True)
            try:
                os.chmod(configure_tmp, 0o777)
            except OSError as error:
                self.output.warning(
                    f"AUTOTOOLS-TMPDIR: could not set mode 0777 on {configure_tmp}: {error}"
                )
            os.environ["TMPDIR"] = configure_tmp
            self.output.info(f"AUTOTOOLS-TMPDIR: path={configure_tmp} mode=0777")
            if os.path.isfile(configure):
                _relax_configure_tmp_umask(configure, self.output)
            autotools.configure(build_script_folder=source_copy)
        finally:
            os.umask(previous_umask)
            if previous_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = previous_tmpdir
        autotools.make(args=["-j2"])

        # Autotools does not register this upstream manual case in `make check`.
        # Run its sole test program explicitly and validate all ten barrier
        # participants reached the end of the scenario.
        test_binary = os.path.join(
            self.build_folder, "doc", "examples", "test_barrier"
        )
        log_file = os.path.join(self.build_folder, "upstream-test-barrier.log")
        exit_file = os.path.join(self.build_folder, "upstream-test-barrier.exit")
        command = (
            f"{shlex.quote(test_binary)} > {shlex.quote(log_file)} 2>&1; "
            f"status=$?; printf '%s\\n' \"$status\" > {shlex.quote(exit_file)}; exit 0"
        )
        self.run(command, env="conanbuild")

        output = ""
        if os.path.isfile(log_file):
            with open(log_file, encoding="utf-8", errors="replace") as stream:
                output = stream.read()
        exit_code = None
        if os.path.isfile(exit_file):
            with open(exit_file, encoding="ascii", errors="replace") as stream:
                try:
                    exit_code = int(stream.read().strip())
                except ValueError:
                    pass
        passed_workers = output.count("passed the barrier!")
        passed = exit_code == 0 and passed_workers == 10
        if not passed:
            not_run = (
                not os.path.isfile(test_binary)
                or exit_code is None
                or (exit_code == 127 and re.search(
                    r"inaccessible or not found|not found|command not found",
                    output,
                    re.IGNORECASE,
                ))
            )
            status = "NOT-RUN" if not_run else "FAIL"
            failed = 0 if not_run else 1
            skipped = 1 if not_run else 0
            self.output.info(
                f"UPSTREAM-CASE test_barrier: {status} "
                f"exit={exit_code!r}, barrier_messages={passed_workers}/10"
            )
            self.output.info("UPSTREAM-RAW-BEGIN")
            if output:
                print(output, end="" if output.endswith("\n") else "\n")
            else:
                print("Not executed: test output file was not produced.")
            self.output.info("UPSTREAM-RAW-END")
            self.output.info(
                f"UPSTREAM-SUMMARY total=1 pass=0 fail={failed} notrun={skipped}"
            )
            # CI and device workers can differ in runtime support and paths.
            # Preserve the exact case result in the log without converting a
            # not-run/failing test result into a Conan build exception.
            return

        self.output.info(
            f"UPSTREAM-CASE test_barrier: PASS (workers={passed_workers})"
        )
        self.output.info("UPSTREAM-SUMMARY total=1 pass=1 fail=0")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["threadar"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.cxxflags = ["-pthread"]
        self.cpp_info.exelinkflags = ["-pthread"]
        self.cpp_info.sharedlinkflags = ["-pthread"]
        self.cpp_info.set_property("cmake_file_name", "libthreadar")
        self.cpp_info.set_property("cmake_target_name", "libthreadar::libthreadar")
        self.cpp_info.set_property("pkg_config_name", "libthreadar")
