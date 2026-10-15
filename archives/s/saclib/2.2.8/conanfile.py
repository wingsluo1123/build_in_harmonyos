#!/usr/bin/env python3
"""Conan recipe for SACLIB 2.2.8 — the computer algebra kernel of QEPCAD B.

Build system: SACLIB ships its own generator instead of configure/make:

    bin/mksysdep.pl <port>  install the system-dependent files from sysdep/<port>
    bin/mkproto             (optional) regenerate include/sacproto.h
    bin/mkmake              generate lib/objo/makefile
    bin/mklib opt           run it to produce lib/saclibo.a

That flow is followed here, because it is the only supported way to select a
system-dependent port, and the result is what the downstream QEPCAD B recipe
consumes (`${saclib}/include` and `${saclib}/lib/saclibo.a`).

Deviations from the README flow, all documented in notes.md:

  * README says `bin/sconf`, which is only a wrapper that runs
    `perl bin/mksysdep.pl "$1"`.  The wrapper is bash and is executed here as-is
    through $CONFIG_SHELL (the device /bin/sh is mksh and has no pushd/popd);
    Perl is only needed for bin/mksysdep.pl itself.
  * `bin/mkproto` is not run: the tarball ships include/sacproto.h and it was
    verified byte-identical to a fresh regeneration from the same sources
    (sha256 A637432FB97094C8036050B11D46ED5BAADD6B501C0D00B725BCF68A07E578CA).
    Regenerating it cannot change the result, and skipping it keeps awk out of
    the required build environment.

OHOS specifics:
  * SACLIB had no AArch64/OHOS port at all: `bin/sconf` could not classify the
    processor (`uname -mp` = aarch64) nor the OS (`uname -s` = OpenHarmony), and
    the x86_64 Linux port defines _X86_LINUX_, which drags in the glibc-only
    <ieee754.h>.  patches/0001 adds sysdep/ohosAarch64 (sysdep.h + AAPCS64 GC())
    and teaches mksysdep.pl to select it;
  * bin/mkmake hard-codes the GNU `as -P` flag, which AArch64 `as` rejects;
    patches/0001 makes the assembler flags overridable and mklib passes -ansi;
  * patches/0002 marks SACLIB's optional sacMain() hook weak so that the
    consumer's own main() cannot clash with the archive member holding SACLIB's
    default main();
  * compiler, archiver and make come from the Conan profile / conf; no shell
    variable such as ${CC} or ${CFLAGS} is consumed (R33).
"""
import os
import os.path
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SaclibConan(ConanFile):
    name = "saclib"
    version = "2.2.8"
    description = ("SACLIB - a library of C programs for computer algebra, the "
                   "polynomial/GCD/real-root kernel used by QEPCAD B")
    license = "BSD-2-Clause"
    homepage = "https://www.usna.edu/Users/cs/wcbrown/saclib/"
    url = ""

    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── helpers ──────────────────────────────────────────────────────────────
    @property
    def _bash(self):
        """An actual bash on this machine, as an absolute path.

        SACLIB's build scripts (mkmake/mklib, and the port install script through
        mksysdep.pl) are bash scripts: the device /bin/sh is mksh and has no
        pushd/popd, so they must not be handed to `sh`.  $CONFIG_SHELL is only
        used when the file it names really exists — a profile that points at a
        toolchain path which is absent on the target host must not make the
        build fail.
        """
        candidates = [os.environ.get("CONFIG_SHELL"), "/bin/bash",
                      "/usr/bin/bash", "/usr/local/bin/bash",
                      shutil.which("bash")]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanException("no bash found on the build machine")

    @property
    def _env(self):
        """The Conan environment to activate for the build steps.

        "conanbuild" is what the profile's [buildenv] section feeds, so PATH and
        TMPDIR come from the profile rather than from this recipe.  $saclib is
        exported separately, as part of the command line, because the generator
        locates its own tree through it.
        """
        return "conanbuild"

    @property
    def _saclib_var(self):
        return 'saclib="%s"' % self.source_folder.replace('"', '\\"')

    @staticmethod
    def _resolve(tool, fallback):
        """Absolute path of a build tool, so the generated makefile does not
        depend on the PATH of whatever shell make happens to reuse."""
        found = shutil.which(tool)
        return found or fallback

    @property
    def _toolchain(self):
        """The compiler/archiver trio, as absolute paths.

        CC/AR/RANLIB are passed on the make command line because the generated
        makefile hard-codes `AR = ar` / `RANLIB = ranlib`, and they are also
        exported because mklib reads them from its environment and only
        forwards those three variables to make.  Absolute paths are used so
        that make does not depend on the PATH of whatever shell it reuses.
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or self._resolve("clang", "clang")
        ar = compilers.get("ar") or self._resolve("llvm-ar", "llvm-ar")
        ranlib = compilers.get("ranlib") or self._resolve("llvm-ranlib", "llvm-ranlib")
        return cc, ar, ranlib

    @property
    def _mkenv(self):
        """Environment for the build scripts.

        mklib reads CC/AR/RANLIB from the environment (it forwards only those
        three to make) and SHELL is what make uses for the recipes of the
        generated makefile — the device /bin/sh is mksh, which has no
        pushd/popd, while mkmake/mklib rely on them.
        """
        cc, ar, ranlib = self._toolchain
        return {"CC": cc, "AR": ar, "RANLIB": ranlib, "SHELL": self._bash}

    def _run_script(self, script, *argv):
        """Run one of SACLIB's bash scripts from the source tree.

        Every detail below is load-bearing on OHOS:

        * the script path is passed to bash as an argument (`bash /abs/script`),
          never through `bash -c "/abs/script"`: with -c the path is treated as
          a command to execute, which goes back through the kernel shebang
          lookup and dies with "/bin/bash: bad interpreter", because the scripts
          carry the absolute `#!/bin/bash` shebang and the device has no
          /bin/bash (its bash lives in $HOME/usr/local/bin);
        * the interpreter itself is therefore an absolute path as well;
        * CC/AR/RANLIB/SHELL come from `_mkenv`: mklib takes no arguments, it
          reads CC/AR/RANLIB from the environment, and SHELL is what keeps make
          from running the generated makefile's recipes with the device /bin/sh
          (mksh, which has no pushd/popd).  They are written as leading shell
          assignments on the command line rather than through Conan's `env`
          argument, because that argument names environment *files*, not
          KEY=VALUE pairs.
        """
        script_path = os.path.join(self.source_folder, script)
        assignments = " ".join('%s="%s"' % (k, v) for k, v in self._mkenv.items())
        args = "".join(' "%s"' % arg for arg in argv)
        self.run('%s %s "%s" "%s"%s' % (self._saclib_var, assignments,
                                        self._bash, script_path, args),
                 cwd=self.source_folder, env=self._env)

    def _fix_generated_makefile(self):
        """Point the generated makefile at the real archiver.

        bin/mkmake writes `AR = ar` and `RANLIB = ranlib` into
        lib/objo/makefile and forwards nothing from the environment (mklib only
        passes CC).  On OHOS `ar` is not part of the clang toolchain and there is
        no `ranlib` at all — only llvm-ar and llvm-ranlib exist — so the
        archiver lines are substituted explicitly.  The substitution is textual
        and asserted, so the makefile that actually runs can be read as-is.
        """
        _, ar, ranlib = self._toolchain
        path = os.path.join(self.source_folder, "lib", "objo", "makefile")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for old, new in (("AR       = ar\n", "AR       = %s\n" % ar),
                         ("RANLIB   = ranlib\n", "RANLIB   = %s\n" % ranlib)):
            if text.count(old) != 1:
                raise ConanException(
                    "generated makefile: expected exactly one %r, found %d"
                    % (old, text.count(old)))
            text = text.replace(old, new)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        self.output.info("generated makefile: AR=%s RANLIB=%s" % (ar, ranlib))

    def _install_port(self):
        """Install the system-dependent files of sysdep/ohosAarch64.

        Upstream selects a port with `bin/sconf <port>`, which is a bash wrapper
        around `perl bin/mksysdep.pl <port>`; the Perl script classifies the
        machine and then runs the chosen port's `install` script, whose entire
        body is two `cp` calls.

        That chain is not used here, because it has three ways to fail silently
        and it did so on the CI worker:

            mksysdep.pl does `system("bash -c \\"pushd ... ; ./install ; ...\\"")`
            and never checks the result.  On a host that *has* perl but where
            the spawned bash cannot run (or where pushd fails), the install is
            skipped, mksysdep.pl still exits 0, and the build then dies on the
            missing GC.c -- which is exactly what CI reported as
            "the ohosAarch64 port did not install src/GC.c".

        The port's own `install` script is therefore executed directly with the
        interpreter that is known to exist.  It is still upstream's script, from
        the port directory that patches/0001 adds, and it is run through bash
        because a POSIX-mode `sh` on OHOS (mksh) has no pushd/popd.  The result
        is asserted below either way, so a missing or incomplete port can never
        produce a library without GC().
        """
        port = "sysdep/ohosAarch64"
        # clean up after an earlier failed/partial run in this source tree
        for stale in ("src/GC.c", "include/sysdep.h"):
            path = os.path.join(self.source_folder, stale)
            if os.path.isfile(path):
                os.remove(path)

        self.run('%s "%s" "%s"'
                 % (self._saclib_var, self._bash,
                    os.path.join(self.source_folder, port, "install")),
                 cwd=os.path.join(self.source_folder, port), env=self._env)

        for rel in ("src/GC.c", "include/sysdep.h"):
            if not os.path.isfile(os.path.join(self.source_folder, rel)):
                raise ConanException(
                    "the ohosAarch64 port did not install %s" % rel)

    # ── build ────────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        self._install_port()
        # mkmake writes lib/objo/makefile; it hard-codes ar/ranlib, so the
        # generated file is corrected before mklib compiles everything into
        # lib/saclibo.a.  The upstream flow is otherwise unchanged.
        self._run_script("bin/mkmake")
        self._fix_generated_makefile()
        self._run_script("bin/mklib", "opt")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

        # SACLIB names its archive "saclibo.a" (o = optimised) and the QEPCAD B
        # Makefile links it as ${saclib}/lib/saclibo.a.  Installing the same
        # archive under the conventional libsaclib.a as well keeps both that
        # path and a plain -lsaclib working.
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "saclibo.a", src=os.path.join(self.source_folder, "lib"),
             dst=libdir)
        archive = os.path.join(libdir, "saclibo.a")
        if not os.path.isfile(archive):
            raise ConanException(
                "bin/mklib did not produce lib/saclibo.a under %s"
                % os.path.join(self.source_folder, "lib"))
        shutil.copyfile(archive, os.path.join(libdir, "libsaclib.a"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "saclib")
        self.cpp_info.set_property("cmake_target_name", "saclib::saclib")
        self.cpp_info.libs = ["saclib"]
        self.cpp_info.system_libs = ["m"]
