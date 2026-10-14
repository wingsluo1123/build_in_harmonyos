#!/usr/bin/env python3
"""Conan test_package — libadwaita-1 1.9.2. Verifies the packaged libadwaita
recipe is consumable: builds a minimal C program against the package, links
against adwaita-1, and runs it. On OHOS (headless) the program does NOT call
adw_init() (would try to open a display); it exercises the libadwaita public
version API instead (adw_get_major/minor/micro_version)."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibAdwaitaTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # libxmlb (transitive dep of appstream/1.2.0, now a libadwaita-1
        # requirement) references glib component keys without the -2.0 suffix
        # (glib::glib/gobject/gio/gmodule); the ohpcd glib/2.84.0.1.1 keys are
        # suffixed. Inject plain aliases BEFORE PkgConfigDeps (same trick as
        # the main recipe's generate()).
        if getattr(self, "dependencies", None) and "glib" in self.dependencies:
            _g = self.dependencies["glib"]
            for _suffix, _plain in (
                ("glib-2.0", "glib"),
                ("gobject-2.0", "gobject"),
                ("gio-2.0", "gio"),
                ("gmodule-2.0", "gmodule"),
            ):
                if _suffix in _g.cpp_info.components and _plain not in _g.cpp_info.components:
                    _g.cpp_info.components[_plain] = _g.cpp_info.components[_suffix]
        PkgConfigDeps(self).generate()
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        from conan.tools.build import cross_building
        if cross_building(self):
            self.output.info("cross-building: skip test execution on build host")
            return
        # r03 (CI L1): libgtk-4.so.1 (gtk4/4.22.4 artifact) needs Pango >= 1.52
        # symbols pango_font_map_add_font_file / pango_font_map_reload_font.
        # The published pango/1.56.4 artifact on ohpcd exports both (verified via
        # nm -D/readelf), but a CI worker may expose an older system libpango
        # (< 1.52) through LD_LIBRARY_PATH / default paths. gtk4's .so has no
        # RUNPATH of its own, so resolution order is driven by LD_LIBRARY_PATH.
        # Explicitly prepend every conan dependency lib dir so the runtime always
        # resolves libpango-1.0.so.0 from the conan graph (pango/1.56.4).
        lib_dirs = []
        for dep in self.dependencies.values():
            pkg_folder = getattr(dep, "package_folder", None)
            if not pkg_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                full = libdir if os.path.isabs(libdir) else os.path.join(pkg_folder, libdir)
                if full not in lib_dirs:
                    lib_dirs.append(full)
        if lib_dirs:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs) + \
                (os.pathsep + old if old else "")
            self.output.info(
                "prepended %d dependency lib dir(s) to LD_LIBRARY_PATH "
                "(force pango/1.56.4 runtime resolution)" % len(lib_dirs))
        self.run("meson test -v -C \"%s\" --timeout-multiplier=16 --no-rebuild" % self.build_folder)