#!/usr/bin/env python3
"""Conan recipe — xdriinfo 1.0.8 (query configuration information of X11 DRI drivers).

x.org official release tarball. Build system: autotools. The release ships a
pre-generated autoconf 2.73 `configure` (and `Makefile.in`), so no autoreconf
is needed and the missing automake on the worker is irrelevant.

The whole program is a single C file (xdriinfo.c). It resolves two DRI-config
entry points through glXGetProcAddressARB before it parses argv, then opens an
X display to query the DRI driver of a screen.

Dependencies (all published on the `ohpcd` registry as OHOS/armv8 binaries):

* libx11/6.4.0        Xlib (configure.ac: PKG_CHECK_MODULES(XDRIINFO, x11 glproto))
* glproto/1.4.17      GL/glx* protocol headers reached from <GL/glx.h>
* mesa/24.3.4.1.1.1   libGL.so.1 + GL/glx.h + GL/glxext.h + gl.pc
* llvm/20.1.0         runtime only: libGL.so.1 -> libgallium-24.3.4.so has a
                      DT_NEEDED on libLLVM.so.20.1

Why mesa and not libglvnd (the dependency set suggested by the claim
reconnaissance): libglvnd/1.7.0 as published builds with x11 and glx disabled,
so it ships no libGL.so, no libGLX.so, no `gl.pc` and no GL/glx.h. configure.ac
links GL through AC_SEARCH_LIBS([glXGetProcAddressARB], [GL]) which libglvnd
cannot satisfy, and the hidden DRI entry points are absent too. mesa is the
only published package that provides libGL.so.1 exporting glXGetProcAddressARB,
glXGetScreenDriver and glXGetDriverConfig plus the GLX headers, and it is also
the semantically correct provider for a DRI/GLX query tool.

mesa's own binary package records the LLVM libdir it was built against in a
`mesa_llvm_lib_dir` marker that points at the *builder's* conan home, so its
runenv hint cannot be resolved on a consumer machine. libLLVM.so.20.1 is not
part of the OHOS SDK either. The dependency is therefore declared here
explicitly (runtime only) so the loader can resolve libgallium's DT_NEEDED.
"""
import glob as _glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XdriinfoConan(ConanFile):
    name = "xdriinfo"
    version = "1.0.8"
    description = ("Query configuration information of X11 DRI drivers "
                   "(glXGetScreenDriver / glXGetDriverConfig)")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xdriinfo"
    url = "https://gitlab.freedesktop.org/xorg/app/xdriinfo"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Build/link requirements.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("glproto/1.4.17", transitive_headers=True)
        self.requires("mesa/24.3.4.1.1.1", transitive_headers=True, transitive_libs=True)
        # Runtime-only requirement: mesa's libGL.so.1 needs libgallium-24.3.4.so,
        # which needs libLLVM.so.20.1. Declaring it here makes the LLVM libdir
        # visible at run time (conanrun environment) because mesa's own hint is
        # stale (see module docstring).
        self.requires("llvm/20.1.0", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _pkg_config_dirs(self):
        """pkg-config search path for `PKG_CHECK_MODULES(XDRIINFO, x11 glproto)`.

        libx11/libxcb/libxext/... install their .pc under lib/pkgconfig, while
        xorgproto's protocol .pc files live under share/pkgconfig; collect both
        from every host dependency so configure resolves `x11` and `glproto`.
        """
        out = []
        for dep in self.dependencies.host.values():
            for sub in (os.path.join("lib", "pkgconfig"),
                        os.path.join("share", "pkgconfig")):
                directory = os.path.join(dep.package_folder, sub)
                if os.path.isdir(directory) and directory not in out:
                    out.append(directory)
        return out

    def _prepend_toolchain_path(self):
        """Make the compiler's own bin directory reachable through PATH.

        The OHOS profile names clang by absolute path; clang then resolves its
        internal ld.lld/nm from its own bin directory, but worker shells that
        lack that directory make configure report "C compiler cannot create
        executables" (same mitigation as xev/xeyes/flint).
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or compilers.get("cpp") or os.environ.get("CC")
        if not cc:
            return
        toolchain_dir = os.path.dirname(cc)
        if not toolchain_dir:
            return
        current = os.environ.get("PATH", "")
        if toolchain_dir in (current.split(os.pathsep) if current else []):
            return
        os.environ["PATH"] = toolchain_dir + os.pathsep + current

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Native build=host: no --build/--host/--target (iron rule #0). The
        # triplet is resolved by the patched config.guess instead.
        pkg_config_path = ":".join(self._pkg_config_dirs())
        current = os.environ.get("PKG_CONFIG_PATH", "").strip()
        if current:
            pkg_config_path = pkg_config_path + ":" + current
        tc.configure_args.append(f"PKG_CONFIG_PATH={pkg_config_path}")
        tc.generate()
        AutotoolsDeps(self).generate()
        # Conan-cached shared libraries are not on the OHOS loader's default
        # search path. AutotoolsDeps only contributes -I/-L/-l, so configure's
        # AC_RUN_IFELSE conftest (which now links -lGL, -lX11, ...) fails to
        # start with "Error loading shared library libGL.so.1: (needed by
        # ./conftest)" and autoconf misreads that as "cannot run C compiled
        # programs", flipping the build into cross-compiling mode. Prepending
        # the dependency libdirs to LD_LIBRARY_PATH in the conanbuild
        # environment is the fix recorded for this signature (aaphoto/0.45,
        # dirb/2.22).
        env = Environment()
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def _sign_elf(self, path):
        """Sign the installed ELF: the OHOS loader refuses unsigned objects."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def build(self):
        apply_conandata_patches(self)
        self._prepend_toolchain_path()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in sorted(_glob.glob(os.path.join(bin_dir, "*"))):
                if os.path.isfile(name) and not os.path.islink(name):
                    self._sign_elf(name)

    def package_info(self):
        # Command line tool: expose bin/ only (R38), no libraries or headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
