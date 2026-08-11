#!/usr/bin/env python3
"""Conan recipe for ffms2 5.0 — FFmpegSource wrapper library.

ffms2 is a wrapper library around FFmpeg that provides frame-accurate
media access for video and audio.  It builds a shared library
(libffms2.so) and a command-line indexing tool (ffmsindex).

Dependencies (published on ohpcd):
  - ffmpeg/7.1.5   (provides libavformat/libavcodec/libswscale/libavutil/libswresample)
  - zlib/1.3.1.1   (compression, transitive via ffmpeg)

OHOS adaptations:
  - E011/E114: patch generated configure to remove `umask 077` from
    config.status temp-dir creation (HMDFS setgid + umask 077 produces
    unwritable drwx--S--- directory).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout
import os


class Ffms2Conan(ConanFile):
    name = "ffms2"
    version = "5.0"
    description = "FFmpegSource wrapper library for frame-accurate media access"
    license = "MIT"
    homepage = "https://github.com/FFMS/ffms2"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ffmpeg/7.1.5")
        self.requires("zlib/1.3.1.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ffms2 is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: generate .pc files for ffmpeg/zlib so configure's
        # PKG_CHECK_MODULES can find them (R33: flags from Conan, not shell vars)
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # AutotoolsDeps: feed -I/-L/-l into configure/make env
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries should use static; ffms2 is not a
        # system-name library, so default shared is fine.  But honour the
        # conan option.
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable avisynth plugin (Windows-only, not relevant on OHOS)
        tc.configure_args.append("--disable-avisynth")
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared
        # libs. configure's conftest runs compiled programs, which fail
        # unless LD_LIBRARY_PATH points at the dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        # On this OHOS build host, /usr/local/bin/aclocal and automake are
        # version 1.17 but only the 1.16 Automake perl modules are installed,
        # causing "Can't locate Automake/Config.pm" during autoreconf.
        # Pin ACLOCAL/AUTOMAKE to the working 1.16 binaries.
        env.define("ACLOCAL", "aclocal-1.16")
        env.define("AUTOMAKE", "automake-1.16")
        # Ensure aclocal finds pkg.m4 and other system macros
        env.prepend_path("ACLOCAL_PATH", "/storage/Users/currentUser/usr/local/share/aclocal")
        # PkgConfigDeps generates .pc files with Version: 7.1.5 (the conan
        # package version) instead of the actual library version (e.g.
        # 61.7.103 for libavformat). ffms2's configure checks
        # "libavformat >= 60.16.0" which fails.  Work around by setting
        # FFMPEG_CFLAGS / FFMPEG_LIBS directly so configure skips the
        # pkg-config version check (as suggested by configure.ac itself).
        ffmpeg = self.dependencies["ffmpeg"]
        ffmpeg_inc = " ".join(f"-I{d}" for d in ffmpeg.cpp_info.includedirs)
        ffmpeg_lib = " ".join(f"-L{d}" for d in ffmpeg.cpp_info.libdirs)
        ffmpeg_libs = " ".join(f"-l{l}" for l in ffmpeg.cpp_info.libs)
        # If components are defined, use the specific lib names
        if ffmpeg.cpp_info.components:
            comp_libs = []
            for comp_name in ("avformat", "avcodec", "swscale", "avutil", "swresample"):
                comp = ffmpeg.cpp_info.components.get(comp_name)
                if comp:
                    comp_libs.append(f"-l{comp_name}")
            if comp_libs:
                ffmpeg_libs = " ".join(comp_libs)
        env.define("FFMPEG_CFLAGS", ffmpeg_inc)
        env.define("FFMPEG_LIBS", f"{ffmpeg_lib} {ffmpeg_libs}")
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        # Create src/config dir (autoheader needs it, but it's not in the tarball)
        config_dir = os.path.join(self.source_folder, "src", "config")
        os.makedirs(config_dir, exist_ok=True)
        # Copy pkg.m4 into m4/ if missing (needed by PKG_PROG_PKG_CONFIG macro)
        m4_dir = os.path.join(self.source_folder, "m4")
        pkg_m4 = os.path.join(m4_dir, "pkg.m4")
        if not os.path.isfile(pkg_m4):
            import shutil
            system_pkg_m4 = "/storage/Users/currentUser/usr/local/share/aclocal/pkg.m4"
            if os.path.isfile(system_pkg_m4):
                shutil.copy2(system_pkg_m4, pkg_m4)
                self.output.info("Copied pkg.m4 into m4/ directory")
        autotools = Autotools(self)
        # autoreconf is needed: source tarball ships configure.ac but no configure
        autotools.autoreconf()
        # E011: patch generated configure to remove umask 077 (HMDFS workaround)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(configure_path, "w") as f:
                    f.write(content)
                self.output.info("Patched configure: umask 077 -> umask 022 (E011 HMDFS workaround)")
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ffms2"]
        self.cpp_info.includedirs = ["include"]
        # ffms2.pc Requires.private: libavformat libavcodec libswscale
        # libavutil libswresample — all provided by ffmpeg conan package
