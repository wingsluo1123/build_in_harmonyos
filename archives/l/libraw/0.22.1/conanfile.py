#!/usr/bin/env python3
"""Conan recipe — LibRaw 0.22.1: RAW image processing library.

LibRaw is a library for reading RAW files from digital photo cameras
(CR2, NEF, ARW, DNG, ...).  It provides a C++ API (class LibRaw) and a C
API (libraw_open_file / libraw_dcraw_process / ...).  Two libraries are
built:
  - libraw    — non-thread-safe (single-threaded)
  - libraw_r  — reentrant / thread-safe (compiled with -pthread)

Build system: GNU Autotools (configure.ac + Makefile.am).  The upstream
release tarball ships configure.ac/Makefile.am but NOT a pre-generated
`configure` script, so `autoreconf --install` must run in build().

Dependencies (Conan, published on ohpcd):
  - zlib/1.3.1.1   — deflate-compressed DNG support (static lib)
  - libjpeg/10     — lossy-compressed DNG / JPEG thumbnail support (shared lib)

OHOS adaptations:
  - config.guess already recognises aarch64-unknown-linux-ohos (libtool 2.4.7
    bundled copy), so no config.guess/config.sub patch is required.
  - The mktemp(1) on HarmonyOS creates temp dirs with drwx--S--- perms
    (HMDFS setgid + hmmac MAC), which makes config.status fail writing
    subs*.awk ("Permission denied").  generate() installs a tiny mktemp
    wrapper on PATH that returns failure, forcing autoconf's AS_TMPDIR to
    fall back to mkdir (which produces correct perms).  This mirrors the
    pattern used by the acct/6.6.4 recipe (E114).
"""
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class LibrawConan(ConanFile):
    name = "libraw"
    version = "0.22.1"
    description = "LibRaw — library for reading and processing RAW image files"
    license = "LGPL-2.1"
    homepage = "https://www.libraw.org/"
    url = ""  # CI fills this

    # Library (libraw.so/libraw.a + libraw_r.so/libraw_r.a).  When examples
    # are enabled, CLI tools (dcraw_emu, raw-identify, ...) are also built
    # and installed to bin/ (R38: commands.json declared at software level).
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "enable_jpeg": [True, False],
        "enable_zlib": [True, False],
        "enable_examples": [True, False],
    }
    default_options = {
        "shared": True,
        "enable_jpeg": True,
        "enable_zlib": True,
        "enable_examples": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.enable_zlib:
            self.requires("zlib/1.3.1.1")
        if self.options.enable_jpeg:
            self.requires("libjpeg/10")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libraw is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps feeds -I/-L/-l from zlib/libjpeg into configure & make.
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        if self.options.enable_examples:
            tc.configure_args.append("--enable-examples")
        else:
            tc.configure_args.append("--disable-examples")
        tc.configure_args.append("--disable-openmp")
        if not self.options.enable_jpeg:
            tc.configure_args.append("--disable-jpeg")
        if not self.options.enable_zlib:
            tc.configure_args.append("--disable-zlib")
        # R26: static build → disable shared (Conan manages the dependency
        # chain; avoids polluting system /lib with a same-name libraw.so).
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        tc.generate()

        # HarmonyOS mktemp fix (E114): mktemp -d creates dirs with broken
        # group perms (drwx--S---) under HMDFS+hmmac, breaking config.status
        # temp-file writes.  Install a wrapper returning failure so autoconf
        # AS_TMPDIR falls back to mkdir (correct perms).
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            "#!/bin/sh\n"
            "# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n"
            "# Return failure to force autoconf AS_TMPDIR mkdir fallback.\n"
            "exit 1\n"
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        # Ensure conan-cached shared deps (libjpeg.so) are found by conftest
        # programs at configure time (OHOS loader has no default search path).
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        # OHOS profile PATH prepends /usr/local/bin which holds a broken
        # aclocal/automake (1.17 binaries without the 1.17 share data →
        # "Can't locate Automake/Config.pm").  The working automake 1.16.5
        # lives in ~/.local/bin.  Point ACLOCAL/AUTOMAKE at the correct,
        # self-consistent toolset so autoreconf succeeds.
        tool_path = (f"{Path.home()}/.local/bin:/data/service/hnp/bin:"
                     "/storage/Users/currentUser/usr/local/bin")
        for tool in ("aclocal", "automake", "autoconf", "autoheader"):
            local_bin = shutil.which(tool, path=tool_path)
            if local_bin:
                env.define(tool.upper(), local_bin)
        env.vars(self, scope="build").save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # The upstream tarball ships configure.ac but no `configure`, so
        # autoreconf must regenerate the autotools machinery first.
        autotools.autoreconf()
        autotools.configure()
        # R9: -j1 — parallel make hits HMDFS jobserver fifo EPERM (E074).
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Both the single-threaded (raw) and reentrant (raw_r) libs.
        self.cpp_info.libs = ["raw", "raw_r"]
        # libraw_r needs pthread
        self.cpp_info.system_libs = ["pthread", "m"]
        if self.options.enable_examples:
            self.cpp_info.bindirs = ["bin"]
