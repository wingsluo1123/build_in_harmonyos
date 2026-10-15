#!/usr/bin/env python3
"""Conan recipe — MPB 1.12.0 (MIT Photonic-Bands), autotools, OHOS native build=host.

Upstream: https://github.com/NanoComp/mpb (photonic crystal eigenmode solver).
Build:    autotools; the official release tarball ships a pre-generated
          `configure` (no system automake on the device, so no autoreconf).
Products: `libmpb` (+ public headers) and the CLI tools `mpb`, `mpb-data`,
          `mpb-split`.

Dependencies (all published in ohpcd):
  - fftw/3.3.10.3  : FFTW3 double precision (`-lfftw3`), required.
  - lapack/3.12.1  : LAPACK + reference BLAS (static, bundles -lblas), required
                     by mpb's AX_LAPACK/AX_BLAS (configure hard-errors without).
  - libctl/4.5.1   : guile-based control files, ships share/libctl/{base,utils}
                     (ctl.scm, main.c, geom.c, geom.scm) and bin/gen-ctl-io.

Optional upstream features intentionally disabled for this adaptation
(not needed by the core eigensolver; documented in notes.md/MANIFEST):
  --without-hdf5   : hdf5 output disabled (its Conan closure pulls the HDF5 C++
                     libraries into the C link line and breaks autoconf probes).
  --without-openmp : no OpenMP runtime required.
  --without-mpi    : single-node build.

OHOS notes (device native, build=host, never --build/--host/--target):
  - E011: tarball extraction may drop the +x bit on the autotools helper
    scripts; restored explicitly before configure.
  - HMDFS: autoconf's `umask 077 && mktemp -d ./confXXXXXX` scratch dir fails
    on the shared mount; the generated `configure` is rewritten in place
    (variable-form only, same fix as the fftw/libctl recipes).
  - HMDFS: make's depfiles pipe (`sed | make -f -`) tries to exec bash and is
    refused; `--disable-dependency-tracking` avoids it.
  - `make -j1` only: make's jobserver fifo is rejected on HMDFS.
  - libctl/guile are embedded interpreters: guile's `bin` and libctl's `bin`
    (gen-ctl-io) must be on PATH at configure time, and the built binaries need
    the dependency lib dirs plus guile/libctl scheme load paths at run time.
"""
import os
import shlex
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class MpbConan(ConanFile):
    name = "mpb"
    version = "1.12.0"
    description = ("MIT Photonic-Bands — computation of photonic band structures "
                   "and electromagnetic eigenmodes (guile/libctl driven)")
    license = "GPL-2.0-or-later"
    homepage = "https://mpb.readthedocs.io"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("fftw/3.3.10.3")
        self.requires("lapack/3.12.1")
        self.requires("libctl/4.5.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mpb {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ helpers
    def _gen_ctl_io_shim(self):
        """Rebuild libctl's gen-ctl-io with the current guile path.

        libctl's published ``bin/gen-ctl-io`` is a shell script generated from
        gen-ctl-io.in with ``@GUILE@`` substituted at *its* build time, so it
        hardcodes a stale cache path
        (``.../.cache/conan2/p/guile.../p/bin/guile``) that no longer exists.
        mpb's mpb/ subdir calls it to generate ctl-io.{h,c}. We drop a copy
        with the guile path rewritten into a build-private dir placed first on
        PATH (the Conan cache itself must not be modified).
        """
        import re
        libctl = self.dependencies["libctl"]
        real = os.path.join(libctl.package_folder, "bin", "gen-ctl-io")
        guile_bin = os.path.join(self.dependencies["guile"].package_folder, "bin", "guile")
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        os.makedirs(shim_dir, exist_ok=True)
        try:
            text = Path(real).read_text(encoding="utf-8", errors="replace")
        except OSError:
            self.output.warning(f"gen-ctl-io not found at {real}; shim skipped")
            return shim_dir
        fixed = re.sub(r"/[^\s()'\"]*bin/guile\b", guile_bin, text)
        dst = os.path.join(shim_dir, "gen-ctl-io")
        Path(dst).write_text(fixed, encoding="utf-8")
        os.chmod(dst, 0o755)
        self.output.info(f"gen-ctl-io shim: {dst} (guile -> {guile_bin})")
        return shim_dir

    def _dep_lib_dirs(self):
        """Collect runtime lib dirs of every host dependency (for make check / run)."""
        dirs = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                p = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
            for comp in getattr(dep.cpp_info, "components", {}).values():
                for libdir in comp.libdirs:
                    p = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                    if os.path.isdir(p) and p not in dirs:
                        dirs.append(p)
        return dirs

    def _interpreter_env(self):
        """PATH + GUILE_CONFIG + load paths for the guile/libctl interpreters."""
        guile = self.dependencies["guile"]
        libctl = self.dependencies["libctl"]
        guile_bin = os.path.join(guile.package_folder, "bin")
        guile_share = os.path.join(guile.package_folder, "share", "guile")
        guile_ccache = os.path.join(guile.package_folder, "lib", "guile", "2.2", "ccache")
        libctl_bin = os.path.join(libctl.package_folder, "bin")
        libctl_share = os.path.join(libctl.package_folder, "share", "libctl")

        env = Environment()
        if os.path.isdir(guile_bin):
            env.prepend_path("PATH", guile_bin)
            env.define("GUILE", os.path.join(guile_bin, "guile"))
            gc = os.path.join(guile_bin, "guile-config")
            if os.path.isfile(gc):
                # HMDFS may refuse direct script execution; run through the shell.
                env.define("GUILE_CONFIG", "sh " + shlex.quote(unix_path(self, gc)))
        if os.path.isdir(libctl_bin):
            env.prepend_path("PATH", libctl_bin)
        # The sanitized gen-ctl-io must win over libctl's own broken script;
        # prepend it last so it ends up first on PATH.
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        if os.path.isdir(shim_dir):
            env.prepend_path("PATH", shim_dir)
        for p in (guile_share, libctl_share):
            if os.path.isdir(p):
                env.prepend_path("GUILE_LOAD_PATH", p)
        if os.path.isdir(guile_ccache):
            env.prepend_path("GUILE_LOAD_COMPILED_PATH", guile_ccache)
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                for share in getattr(dep.cpp_info, "resdirs", []):
                    p = share if os.path.isabs(share) else os.path.join(dep.package_folder, share)
                    if os.path.isdir(p):
                        env.prepend_path("GUILE_LOAD_PATH", p)
        for p in self._dep_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", p)
        return env

    def _fix_exec_bits(self):
        for name in ("configure", "config.guess", "config.sub", "install-sh",
                     "missing", "depcomp", "compile", "ltmain.sh"):
            p = os.path.join(self.source_folder, name)
            if os.path.exists(p):
                os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _patch_configure(self):
        """E011: HMDFS rejects autoconf's `umask 077 && mktemp -d ./confXXXXXX`."""
        cfg = os.path.join(self.source_folder, "configure")
        try:
            text = Path(cfg).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        orig = text
        if "umask 077" in text:
            text = text.replace("umask 077", "umask 022")
        if text != orig:
            Path(cfg).write_text(text, encoding="utf-8")
            self.output.info("HMDFS configure umask patch applied")

    def _materialise_la_shadow(self):
        """E236/E522/E544: build-private Libtool shadow for the dependency closure.

        Packages from ohpcd were built with ``prefix=/`` so their ``.la`` files
        carry ``libdir='//lib'`` and ``dependency_libs`` entries such as
        ``//lib/libltdl.la`` (plus stale build-machine ``-L`` paths). Libtool
        opens those unrelocated archives while linking and aborts
        ("cannot find the library '//lib/libltdl.la'"). We never touch the
        Conan cache (Conan would restore it anyway): instead we copy the
        dependency shared objects into a build-private directory and write a
        sanitized ``.la`` per dependency there — ``libdir`` pinned to this
        directory, ``dependency_libs`` emptied (every dependency is a shared
        object, so link-time transitive metadata is unnecessary) — then put
        that directory first on the link line.
        """
        import glob
        import shutil
        priv = os.path.join(self.build_folder, "ohpcd-libs")
        shutil.rmtree(priv, ignore_errors=True)
        os.makedirs(priv)
        libdirs = self._dep_lib_dirs()
        # Materialise every shared object / archive by its published name so
        # the sanitized .la entries resolve inside `priv` (HMDFS symlinks are
        # not used by the loader).
        for d in libdirs:
            for pat in ("*.so", "*.so.*", "*.a"):
                for f in sorted(glob.glob(os.path.join(d, pat))):
                    dst = os.path.join(priv, os.path.basename(f))
                    try:
                        src = os.path.realpath(f) if os.path.islink(f) else f
                        if os.path.isfile(src) and not os.path.exists(dst):
                            shutil.copyfile(src, dst)
                    except OSError:
                        continue
        count = 0
        for d in libdirs:
            for la in sorted(glob.glob(os.path.join(d, "*.la"))):
                try:
                    lines = Path(la).read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                out = []
                for line in lines:
                    if line.startswith("libdir="):
                        out.append("libdir='%s'" % priv)
                    elif line.startswith("dependency_libs="):
                        out.append("dependency_libs=''")
                    else:
                        out.append(line)
                Path(os.path.join(priv, os.path.basename(la))).write_text(
                    "\n".join(out) + "\n", encoding="utf-8")
                count += 1
        self.output.info(f"libtool shadow: {count} .la sanitized into {priv}")
        return priv

    def _define_f77_wrappers(self):
        """Seed F77_FUNC/F77_FUNC_ after configure.

        mpb's configure.ac only runs AC_F77_WRAPPERS inside an
        ``if test x != x"$F77"`` guard; the device has no Fortran compiler, so
        ``config.h`` ends up with both macros undefined while
        ``src/matrices/blasglue.c`` declares every BLAS/LAPACK symbol through
        them. The reference BLAS/LAPACK shipped by lapack/3.12.1 (flang build)
        use lower-case symbols with a single trailing underscore, which is the
        standard mangling we seed here (harminv precedent).
        """
        block = (
            "\n/* OHOS: no Fortran compiler; seed the reference BLAS/LAPACK\n"
            "   symbol mangling (lower case + trailing underscore). */\n"
            "#ifndef F77_FUNC\n"
            "#  define F77_FUNC(name,NAME) name##_\n"
            "#endif\n"
            "#ifndef F77_FUNC_\n"
            "#  define F77_FUNC_(name,NAME) name##_\n"
            "#endif\n"
        )
        for base in (self.build_folder, self.source_folder):
            header = os.path.join(base, "config.h")
            if not os.path.isfile(header):
                continue
            text = Path(header).read_text(encoding="utf-8", errors="replace")
            if "F77_FUNC(name,NAME)" not in text:
                with open(header, "a", encoding="utf-8") as fh:
                    fh.write(block)
                self.output.info(f"seeded F77_FUNC wrappers into {header}")

    # ------------------------------------------------------------------ conan
    def generate(self):
        AutotoolsDeps(self).generate()
        # MPB bakes $(pkgdatadir)/mpb.scm and the libctl scheme paths into the
        # binary (CTL_DEFS/SPEC_SCM in mpb/Makefile.am). The prefix must equal the
        # final install root so those compiled-in paths stay valid at run time;
        # installation therefore goes straight to that prefix (no DESTDIR staging).
        tc = AutotoolsToolchain(self, prefix=self.package_folder)
        libctl_dir = os.path.join(self.dependencies["libctl"].package_folder, "share", "libctl")
        tc.configure_args += [
            "--disable-dependency-tracking",
            "--without-hdf5",
            "--without-openmp",
            "--without-mpi",
            "--with-libctl=%s" % libctl_dir,
        ]
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        self._fix_exec_bits()
        self._patch_configure()
        self._gen_ctl_io_shim()
        # E236/E522/E544: sanitize the dependency Libtool metadata into a
        # build-private dir and put it first on the link line.
        priv = self._materialise_la_shadow()
        os.environ["LDFLAGS"] = "-L%s %s" % (priv, os.environ.get("LDFLAGS", ""))
        # No Fortran compiler on the device (gfortran/flang absent), so autoconf's
        # AC_F77_FUNC name-mangling probe yields "unknown" and AX_BLAS/AX_LAPACK
        # then search for the symbol "unknown" and fail. Reference BLAS/LAPACK
        # (lapack/3.12.1, built with flang) use lower-case symbols with one
        # trailing underscore, so seed the standard autoconf cache variable.
        os.environ["ac_cv_f77_mangling"] = "lower case, underscore"
        autotools = Autotools(self)
        with self._interpreter_env().vars(self).apply():
            autotools.configure()
            self._define_f77_wrappers()
            autotools.make(args=["-j1"])
            # Upstream tests (tests/*.c + mpb/examples/check.ctl) — R51.
            autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        # Install directly into the configured prefix (== package_folder); no
        # DESTDIR staging, so the compiled-in scheme paths remain valid.
        autotools.install(args=["DESTDIR="])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mpb"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["res", "share"]
        guile = self.dependencies["guile"]
        libctl = self.dependencies["libctl"]
        env = self.runenv_info
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(guile.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(libctl.package_folder, "lib"))
        env.prepend_path("GUILE_LOAD_PATH", os.path.join(guile.package_folder, "share", "guile"))
        env.prepend_path("GUILE_LOAD_PATH", os.path.join(libctl.package_folder, "share", "libctl"))
        env.prepend_path("GUILE_LOAD_COMPILED_PATH",
                         os.path.join(guile.package_folder, "lib", "guile", "2.2", "ccache"))
        env.prepend_path("PATH", os.path.join(guile.package_folder, "bin"))
        # MPB's own spec file (mpb.scm) is found via the compiled-in SPEC_SCM path,
        # so the package directory must be kept stable by consumers.
