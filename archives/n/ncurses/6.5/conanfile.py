#!/usr/bin/env python3
"""Conan recipe — ncurses 6.5 (autotools).

Static-only build (R4): HarmonyOS zsh depends on libncursesw.so.6;
building a shared library risks hijacking the system shell via
LD_LIBRARY_PATH. Wide-char (--enable-widec) and top-level header
install (--enable-overwrite) are enabled for readline compatibility.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "Terminal handling library providing cursor movement, screen optimization, and window management"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = "https://invisible-island.net/ncurses/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "widec": [True, False],
    }
    default_options = {
        "shared": False,
        "widec": True,
    }

    def configure(self):
        # R4: HarmonyOS zsh links libncursesw.so.6; a shared build risks
        # hijacking the system shell via LD_LIBRARY_PATH.
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "ncurses on OHOS must be static (--shared=False); "
                "a shared build would hijack system libncursesw.so.6"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        # ncurses' configure does not support out-of-tree builds
        # (Makefile.in uses relative paths); build in-tree in source_folder.
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # In-tree build: configure runs in source_folder, not build_folder.
        tc.build_folder = "."

        # Disable C++ binding: ncurses C++ API is optional and avoids
        # pulling libc++ headers into the static archive.
        tc.configure_args.extend([
            "--without-shared" if not self.options.shared else "--with-shared",
            "--without-debug",
            "--without-ada",
            "--without-manpages",
            "--without-tests",
            "--without-cxx-binding",
            "--enable-overwrite",       # headers install to top-level include/
            "--with-normal",            # build libncursesw (non-terminfo)
        ])

        if self.options.widec:
            tc.configure_args.append("--enable-widec")
        else:
            tc.configure_args.append("--disable-widec")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Drop la files to avoid libtool cross-compile pollution.
        rm(self, "*.la", self.package_folder, recursive=True)

    def package_info(self):
        suffix = "w" if self.options.widec else ""
        # Core libraries (static, wide-char when enabled).
        # Conan emits `-l<name>` and the linker prepends `lib`, so entries must
        # be bare names matching the installed archive minus the `lib` prefix
        # and extension: `-lncursesw` -> `libncursesw.a`.
        self.cpp_info.libs = [
            f"ncurses{suffix}",
            f"panel{suffix}",
            f"menu{suffix}",
            f"form{suffix}",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
