#!/usr/bin/env python3
"""Conan recipe for libosmo-cc 0.0-git20240818.7864594 — Osmocom call-control
library (signalling, SDP/RTP helpers, G.711) used by the Osmocom MSC/BTS stack.

Why this recipe compiles the sources directly instead of running ./configure:
  the Debian snapshot of this release ships only `configure.ac` + `Makefile.am`
  (no pre-generated `configure`), and the HarmonyOS host provides autoconf 2.72
  but **no automake / aclocal / libtoolize**, so `autoreconf -fi` aborts with
  `Can't exec "aclocal"`.  Upstream has no release/tag tarball with `configure`.
  The library is small (11 C files) and has no config.h or generated headers
  (the two AC_DEFINEs in configure.ac are ortp-only and unused by src/), so the
  recipe compiles `src/*.c` with the OHOS clang and installs the same artefacts
  the autotools build would: libosmocc.so.2.0.0 (+ symlinks), the public
  include/osmocom/cc headers and libosmocc.pc (same fields as upstream
  libosmocc.pc.in).  See notes.md for the full rationale.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save


class LibosmoCCConan(ConanFile):
    name = "libosmo-cc"
    version = "0.0-git20240818.7864594"
    description = "Osmocom call-control library (signalling, SDP/RTP, G.711)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitea.osmocom.org/cc/libosmo-cc"
    url = "https://gitea.osmocom.org/cc/libosmo-cc"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libosmo-cc is only supported on Linux/OHOS, not {self.settings.os}")

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES(LIBOSMOCORE, libosmocore >= 1.6.0)
        self.requires("libosmocore/1.11.0")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        # The snapshot.debian.org content URL ends in a sha1 (no file extension),
        # so the archive format has to be given explicitly or Conan assumes zip.
        get(self, **self.conan_data["sources"], filename="libosmo-cc.tar.xz",
            strip_root=True)

    def _core_flags(self):
        """Include/link flags for libosmocore and its transitive closure.

        libosmocore's public headers include <talloc.h> and friends, and its
        link line needs the same closure the .pc file declares via
        `Requires:`; collecting it from the dependency graph keeps the recipe
        free of hardcoded paths.
        """
        incs, libdirs, libs = [], [], []
        for dep in self.dependencies.host.values():
            for d in dep.cpp_info.includedirs:
                p = os.path.join(dep.package_folder, d)
                if p not in incs:
                    incs.append(p)
            for d in dep.cpp_info.libdirs:
                p = os.path.join(dep.package_folder, d)
                if p not in libdirs:
                    libdirs.append(p)
            for n in list(dep.cpp_info.libs or []) + list(dep.cpp_info.system_libs or []):
                if n not in libs:
                    libs.append(n)
        # The published libosmocore package reports its *dependency* libs
        # (talloc/mnl/pcsclite/usb-1.0) but not the libosmocore archive itself;
        # link it explicitly, mirroring upstream's LIBOSMOCORE_LIBS.
        for n in ("osmocore",):
            if n not in libs:
                libs.append(n)
        return incs, libdirs, libs

    def build(self):
        incs, libdirs, libs = self._core_flags()
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        srcs = sorted(glob.glob(os.path.join(self.source_folder, "src", "*.c")))
        if len(srcs) != 11:
            raise ConanInvalidConfiguration(
                "expected 11 libosmo-cc sources, found %d" % len(srcs))
        os.makedirs(self.build_folder, exist_ok=True)
        cmd = [f'"{cc}"', "-shared", "-fPIC", "-O2", "-Wall", "-Wextra",
               # message.c uses struct timeval without including <sys/time.h>;
               # on glibc it arrives through another header, on musl it does not.
               "-include", "sys/time.h",
               f'-I"{os.path.join(self.source_folder, "include")}"']
        cmd += [f'-I"{d}"' for d in incs]
        cmd += [f'-L"{d}"' for d in libdirs]
        # Upstream libtool LDFLAGS use -no-undefined: fail here instead of
        # shipping a shared object with unresolved symbols.
        cmd += ["-Wl,-soname,libosmocc.so.2", "-Wl,--no-undefined",
                "-o", "libosmocc.so.2.0.0"]
        cmd += ['"%s"' % s for s in srcs]
        cmd += ["-l%s" % n for n in libs]
        cmd += ["-lm", "-lpthread", "-ldl"]
        self.output.info("libosmo-cc link: %s" % " ".join(cmd))
        self.run(" ".join(cmd), cwd=self.build_folder, env="conanbuild")

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        copy(self, "libosmocc.so*", self.build_folder, libdir)
        copy(self, "*.h", os.path.join(self.source_folder, "include", "osmocom", "cc"),
             os.path.join(self.package_folder, "include", "osmocom", "cc"))
        # The autotools/libtool build installs libtool's .so.2 / .so symlinks;
        # reproduce them so `-losmocc` works for consumers.  (Conan packages are
        # extracted as plain trees, so fall back to copies if symlinks fail.)
        target = os.path.join(libdir, "libosmocc.so.2.0.0")
        for name in ("libosmocc.so.2", "libosmocc.so"):
            path = os.path.join(libdir, name)
            try:
                if os.path.lexists(path):
                    os.remove(path)
                os.symlink("libosmocc.so.2.0.0", path)
            except OSError:
                copy(self, "libosmocc.so.2.0.0", libdir, libdir)
                os.replace(os.path.join(libdir, "libosmocc.so.2.0.0"), path)
        # pkg-config file with the same fields as upstream libosmocc.pc.in
        pc_dir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        save(self, os.path.join(pc_dir, "libosmocc.pc"), "\n".join([
            "prefix=%s" % self.package_folder,
            "exec_prefix=${prefix}",
            "libdir=${prefix}/lib",
            "includedir=${prefix}/include",
            "",
            "Name: Osmo CC Library",
            "Description: C Utility Library",
            "Version: %s" % self.version,
            "Libs: -L${libdir} -losmocc",
            "Cflags: -I${includedir}/",
            "Requires: libosmocore",
            "",
        ]))

    def package_info(self):
        self.cpp_info.libs = ["osmocc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libosmo-cc")
        self.cpp_info.set_property("cmake_target_name", "libosmo-cc::libosmo-cc")
