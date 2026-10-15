#!/usr/bin/env python3
"""Conan recipe for exfatprogs 1.4.3 — exFAT filesystem utilities
(mkfs.exfat / fsck.exfat / tune.exfat / exfatlabel / dump.exfat / exfat2img).

Upstream: https://github.com/exfatprogs/exfatprogs (release 1.4.3, 2026-08-14),
Autotools, the release tarball ships a pre-generated configure.

HarmonyOS PC adaptations (all visible in this recipe or in patches/):

1. **Kernel-version gate (patches/0001, the substantive source change).**
   `lib/libexfat.c:exfat_cmp_kernel_ver()` parses `uname().release` with
   `sscanf("%hu.%hu.%hu")`, which expects the number in the *leading* field.
   Measured on this device: `release == "HongMeng Kernel 1.12.0"`, so the
   sscanf fails and every tool aborts with

       failed to get kernel version.
       failed to open <image>. -1

   Fixing the parse alone is not enough: `1.12.0` is numerically below the
   upstream `MIN_KERNEL_VER {2,6,0}`, so the second layer of the same gate
   would then reject the platform as "pre-2.6".  The patch therefore treats a
   release string that does not begin with a digit as "version not evaluable"
   and lets the caller proceed — the regular-file path this package supports
   does not touch `/sys/dev/block` at all.  The test is on the *shape* of the
   string, so Linux releases (`6.6.0-...`) keep the original gate unchanged
   and no platform macro is injected.

2. **libblkid (hard build dependency, `PKG_CHECK_MODULES([BLKID], [blkid >= 2.20])`).**
   `configure` needs `blkid.pc`; conan supplies it through `PkgConfigDeps`,
   and `PKG_CONFIG_PATH` is extended with the generators folder (E468).

3. **`#include <blkid.h>` needs the component sub-directory.**  The upstream
   util-linux `blkid.pc` ships `Cflags: -I${includedir}/blkid`, while conan's
   generated `blkid.pc` is built from `cpp_info.includedirs` and therefore
   only carries `-I${includedir}`.  `configure` succeeds either way, but
   `mkfs/mkfs.c` then dies with `fatal error: 'blkid.h' file not found`.
   The recipe appends `-I<libblkid package>/include/blkid` to `CPPFLAGS`.

4. **`config.guess` does not recognise the `HarmonyOS` uname** (E007 family);
   the build is native aarch64, so the canonical GNU build triple is passed.

5. **HMDFS `umask 077` temp dir** (E011): configure's
   `(umask 077 && mktemp -d ./confXXXXXX)` produces a directory the owner
   cannot write to, and `config.status` dies with `could not make
   ./config.status`.  Neutralised in the build copy, as in the merged
   dosfstools 4.2 / mbr 1.2.2 recipes.

6. **E386 shell routing**: the host profile pins `CONFIG_SHELL`/`SHELL` to the
   device hnp bash, which cannot `getcwd()` in HMDFS build directories, so
   configure/make/install run through `env -u CONFIG_SHELL SHELL=/bin/sh …`.

7. **Serial make** (R9/E074): a parallel jobserver fifo hits HMDFS EPERM
   (`make: jobserver mkfifo: … Operation not permitted`), so every make is
   `-j1`.

8. **Upstream tests are executed for real in `build()`** (see `_run_upstream_tests`).

Dependency / tool resolution was measured with a precise
`conan install . --build=never` (never a wildcard `conan list`):
`libblkid/2.42.2` — binary downloaded from `ohpcd`;
`xxd/9.1.0` (tool_requires) — binary downloaded from `ohpcd`.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class ExfatprogsConan(ConanFile):
    name = "exfatprogs"
    version = "1.4.3"
    description = "exFAT filesystem utilities (mkfs.exfat, fsck.exfat, tune.exfat, exfatlabel, dump.exfat, exfat2img)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/exfatprogs/exfatprogs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # W0 measured: `conan install . --build=never` downloads the binary from ohpcd.
        # Upstream configure.ac: PKG_CHECK_MODULES([BLKID], [blkid >= 2.20]) and
        # mkfs/mkfs.c does an unconditional `#include <blkid.h>`.
        self.requires("libblkid/2.42.2")

    def build_requirements(self):
        # Upstream tests/test_fsck.sh + the four tests/upcase_table/*.sh scripts
        # drive `xxd -r - <image>` (vim semantics: hex on stdin, seek+patch the
        # file).  The device's toybox xxd only accepts a single argument and
        # fails with "xxd: Max 1 argument (see \"xxd --help\")", so 4 of the 23
        # upstream cases ERROR without a real xxd.  Published on ohpcd, binary
        # resolution verified with --build=never.
        self.tool_requires("xxd/9.1.0")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"exfatprogs is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # configure arguments, shared by generate() and build()
    # ------------------------------------------------------------------
    def _toolchain(self) -> AutotoolsToolchain:
        tc = AutotoolsToolchain(self)

        # config.guess bails out on the HarmonyOS uname (E007 family); the
        # build is native aarch64, so pin the canonical GNU triple.
        if os.uname().sysname == "HarmonyOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")

        # Builds lib/tests/suite0000-bitmap (noinst_PROGRAMS behind
        # AM_CONDITIONAL([ENABLE_TESTS])); without it the built-in upstream
        # unit test is never compiled.
        tc.configure_args.append("--enable-tests")

        # R33: compiler from the Conan conf first, clang fallback (the device
        # has no gcc/cc and autoconf's AC_PROG_CC only probes those two).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        tc.configure_args.append(f"CC={compilers.get('c') or 'clang'}")
        tc.configure_args.append(f"CXX={compilers.get('cpp') or 'clang++'}")

        # Upstream include style is `#include <blkid.h>`; conan's generated
        # blkid.pc only adds <pkg>/include while the upstream util-linux
        # blkid.pc adds <pkg>/include/blkid.  Without this, configure passes
        # and mkfs/mkfs.c then dies with "'blkid.h' file not found".
        dep = self.dependencies["libblkid"]
        incdir = os.path.join(str(dep.package_folder), "include", "blkid")
        tc.configure_args.append(f"CPPFLAGS={shlex.quote('-I' + incdir)}")
        return tc

    def generate(self):
        self._toolchain().generate()
        PkgConfigDeps(self).generate()
        # E468: PkgConfigDeps writes blkid.pc into the generators folder but
        # does not add that folder to PKG_CONFIG_PATH.
        self.buildenv_info.append_path(
            "PKG_CONFIG_PATH", str(self.generators_folder)
        )
        # Must run last so the append above is picked up.
        VirtualBuildEnv(self).generate()

    # ------------------------------------------------------------------
    def _pin(self, cmd: str) -> str:
        """E386: the host profile's [buildenv] pins CONFIG_SHELL/SHELL to the
        device hnp bash, which cannot getcwd() in HMDFS directories; autoconf
        re-execs into CONFIG_SHELL and dies with "working directory cannot be
        determined".  Profile buildenv wins over os.environ, so the routing has
        to happen on the command line.  The command is handed to an explicit
        `sh -c` so that compound commands (`cd X && Y`) are not mistaken for
        the utility `env` should execute (measured: "env: 'cd': No such file
        or directory", exit 127)."""
        return f"env -u CONFIG_SHELL SHELL=/bin/sh sh -c {shlex.quote(cmd)}"

    def build(self):
        apply_conandata_patches(self)

        # E490: keep the generated autotools helpers executable (extraction
        # modes are reported as a G0 risk on this platform).
        for helper in (
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "compile", "depcomp", "ltmain.sh",
        ):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        for extra in ("build-aux/install-sh", "build-aux/missing",
                      "build-aux/compile", "build-aux/depcomp",
                      "build-aux/config.guess", "build-aux/config.sub"):
            path = os.path.join(self.source_folder, extra)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        # E011: HMDFS makes the configure `umask 077` scratch directory
        # unwritable for its owner, config.status then cannot create
        # ./confXXXXXX/subs1.awk and configure dies with "could not make
        # ./config.status".  Keep the real temp-dir creation intact.
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "(umask 077 && mktemp", "(umask 022 && mktemp")
        replace_in_file(self, configure, "(umask 077 && mkdir", "(umask 022 && mkdir")

        args = " ".join(shlex.quote(a) for a in self._toolchain().configure_args)
        self.run(self._pin(f"{shlex.quote(configure)} {args}"), env="conanbuild")

        # R9/E074: serial make (parallel jobserver fifo -> HMDFS EPERM).
        self.run(self._pin("make -j1"), env="conanbuild")
        # automake check: upstream registers no TESTS in any Makefile.am, so
        # this target is structurally empty here — it is run for completeness,
        # the real coverage comes from _run_upstream_tests().
        self.run(self._pin("make -j1 check"), env="conanbuild")

        self._run_upstream_tests()

    # ------------------------------------------------------------------
    def _run_upstream_tests(self) -> None:
        """Run both upstream test surfaces for real; a failure fails the build.

        1. `lib/tests/suite0000-bitmap` — the built-in C unit test compiled by
           `--enable-tests` (5 test functions, not registered with automake
           TESTS by upstream).
        2. `tests/test_fsck.sh` — the upstream data-driven corruption suite:
           19 fixture directories shipped as `exfat.img.tar.xz` plus the 4
           `tests/upcase_table/*.sh` image generators = 23 cases.  It is not
           in SUBDIRS and has no automake wiring at all, so `make check` alone
           would run 0 of them.  Cases run against a *regular file image*
           (the script only opens a loop device when its 2nd argument is set),
           which is the unprivileged surface this package supports on OHOS.
        """
        unit = os.path.join(self.build_folder, "lib", "tests", "suite0000-bitmap")
        if os.path.isfile(unit):
            self.run(self._pin(shlex.quote(unit)), env="conanbuild")
        else:
            raise ConanInvalidConfiguration(
                "upstream built-in unit test lib/tests/suite0000-bitmap was not "
                "built; check that configure received --enable-tests"
            )

        tests_src = os.path.join(self.source_folder, "tests")
        tests_run = os.path.join(self.build_folder, "upstream-tests")
        if os.path.isdir(tests_run):
            shutil.rmtree(tests_run)
        shutil.copytree(tests_src, tests_run)

        # The fixture scripts call mkfs.exfat / dump.exfat from PATH, the
        # driver drives fsck.exfat, and xxd comes from tool_requires via
        # conanbuild.sh.  Keep the conanbuild PATH and prepend build dirs.
        built_dirs = [
            os.path.join(self.build_folder, d)
            for d in ("mkfs", "fsck", "dump", "label", "tune", "exfat2img")
        ]
        cmd = (
            f"cd {shlex.quote(tests_run)} && "
            f"PATH={shlex.quote(os.pathsep.join(built_dirs))}:$PATH "
            f"bash ./test_fsck.sh"
        )
        self.run(self._pin(cmd), env="conanbuild")

        # Leave no multi-gigabyte sparse image behind in the build tree.
        img = os.path.join(tests_run, "exfat.img")
        if os.path.isfile(img):
            os.remove(img)

    def package(self):
        # conan's Autotools install semantics: make install with
        # DESTDIR=<package_folder> (configure ran with --prefix=/ and the
        # toolchain pinned --bindir/--sbindir to ${prefix}/bin, so the
        # sbin_PROGRAMS land in bin/).
        self.run(
            self._pin(
                f'make -j1 install DESTDIR={shlex.quote(str(self.package_folder))}'
            ),
            env="conanbuild",
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Standalone binaries only: libexfat.a is noinst (never installed).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
