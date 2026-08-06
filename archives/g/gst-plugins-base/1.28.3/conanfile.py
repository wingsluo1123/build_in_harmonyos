#!/usr/bin/env python3
"""Conan recipe -- gst-plugins-base 1.28.3 (Meson).

GStreamer base plugins and support libraries. This recipe builds the
support libraries (audio, video, app, tag, etc.) for OpenHarmony PC (aarch64).

Adaptation notes:
- Patch 0001 fixes Python script execution on HMDFS (find_program→files+python3)
- NLS disabled (no gettext on OHOS); _() macro stubbed via c_args
- orc disabled (not available); gl disabled (no OpenGL on OHOS PC)
- All introspection, tests, examples, docs, benchmarks disabled
- gettext/ngettext stubbed as macros (same approach as gstreamer recipe)
- glib2 sub-package .pc files created in generate() (same as gstreamer recipe)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins and support libraries"
    license = "LGPL"
    homepage = "https://gstreamer.freedesktop.org/"
    url = ""  # CI fills this

    package_type = "library"

    generators = ("PkgConfigDeps",)

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("glib2/2.88.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names
        # (llvm-ar, llvm-as, ...) that are NOT on its PATH. meson probes these
        # and aborts at configure. Pin the real tools by ABSOLUTE PATH (resolved
        # from PATH) and drop the broken env values.
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
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Disable features not available on OHOS
        tc.project_options["iso-codes"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["vorbis"] = "disabled"
        tc.project_options["theora"] = "disabled"
        tc.project_options["ogg"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["nls"] = "disabled"
        tc.project_options["tools"] = "disabled"
        # Stub gettext/ngettext when NLS is disabled (OHOS has no gettext)
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Dgettext(x)=(x)")
        tc.c_args.append("-Dngettext(s,p,n)=((n)==1?(s):(p))")
        tc.generate()

        # PkgConfigDeps (class-level generator) creates a single glib-2.0.pc
        # but gst-plugins-base's meson.build also needs gobject-2.0, gio-2.0,
        # gmodule-no-export-2.0, gio-unix-2.0 as separate pkg-config packages.
        # Create wrapper .pc files that point to the same glib2 package.
        glib2_pc = self._get_glib2_prefix()
        if glib2_pc:
            import pathlib
            gen_dir = pathlib.Path(self.generators_folder)
            self._create_glib_subpkg_pcs(gen_dir, glib2_pc)

        # Also create gstreamer .pc files if needed
        gstreamer_pc = self._get_gstreamer_prefix()
        if gstreamer_pc:
            import pathlib
            gen_dir = pathlib.Path(self.generators_folder)
            self._create_gstreamer_pcs(gen_dir, gstreamer_pc)

    def _get_glib2_prefix(self):
        """Get the glib2 package install prefix from conan deps."""
        for dep in self.dependencies.values():
            if dep.ref.name == "glib2":
                return str(dep.package_folder)
        return None

    def _get_gstreamer_prefix(self):
        """Get the gstreamer package install prefix from conan deps."""
        for dep in self.dependencies.values():
            if dep.ref.name == "gstreamer":
                return str(dep.package_folder)
        return None

    def _create_glib_subpkg_pcs(self, gen_dir, prefix):
        """Create wrapper .pc files for glib2 sub-packages."""
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/glib-2.0"
        incdir1 = f"{prefix}/lib/glib-2.0/include"
        bindir = f"{prefix}/bin"
        datadir = f"{prefix}/share"

        # Overwrite the conan-generated glib-2.0.pc with a version that
        # includes the variables (glib_genmarshal, gobject_query, glib_mkenums)
        # that gst-plugins-base's meson.build queries via pkg-config.
        glib_pc_content = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include
bindir=${{prefix}}/bin
datadir=${{prefix}}/share

glib_genmarshal=${{bindir}}/glib-genmarshal
gobject_query=${{bindir}}/gobject-query
glib_mkenums=${{bindir}}/glib-mkenums
glib_valgrind_suppressions=${{datadir}}/glib-2.0/valgrind/glib.supp

Name: GLib
Description: C Utility Library
Version: 2.88.0
Libs: -L"${{libdir}}" -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lgthread-2.0 -lffi -lintl -lm -lpthread -ldl -lrt
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
Requires: pcre2 zlib
"""
        (gen_dir / "glib-2.0.pc").write_text(glib_pc_content)

        # gio-2.0.pc needs giomoduledir variable (queried by meson.build)
        gio_pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include
giomoduledir=${{libdir}}/gio/modules

Name: GIO
Description: GLib sub-package (GIO)
Version: 2.88.0
Requires: gobject-2.0
Libs: -L"${{libdir}}" -lgio-2.0
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
"""
        (gen_dir / "gio-2.0.pc").write_text(gio_pc)

        subpkgs = {
            "gobject-2.0.pc": ("GObject", "gobject-2.0", ["glib-2.0"]),
            "gmodule-2.0.pc": ("GModule", "gmodule-2.0", ["glib-2.0"]),
            "gmodule-no-export-2.0.pc": ("GModule-no-export", "gmodule-2.0", ["glib-2.0"]),
            "gthread-2.0.pc": ("GThread", "gthread-2.0", ["glib-2.0"]),
            "gio-unix-2.0.pc": ("GIO-unix", None, ["gio-2.0"]),
        }
        for fname, (name, lib, requires) in subpkgs.items():
            req_str = ", ".join(requires)
            libs_line = f'Libs: -L"${{libdir}}" -l{lib}' if lib else ""
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include

Name: {name}
Description: GLib sub-package ({name})
Version: 2.88.0
Requires: {req_str}
{libs_line}
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
"""
            (gen_dir / fname).write_text(pc)

    def _create_gstreamer_pcs(self, gen_dir, prefix):
        """Create wrapper .pc files for gstreamer sub-packages."""
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/gstreamer-1.0"

        gst_pc_content = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/gstreamer-1.0
pluginsdir=${{libdir}}/gstreamer-1.0

Name: GStreamer
Description: Streaming media framework
Version: 1.28.3
Libs: -L"${{libdir}}" -lgstreamer-1.0 -lgstbase-1.0 -lgstcontroller-1.0 -lgstnet-1.0
Cflags: -I"${{includedir}}"
Requires: glib-2.0 gobject-2.0
"""
        (gen_dir / "gstreamer-1.0.pc").write_text(gst_pc_content)

        subpkgs = {
            "gstreamer-base-1.0.pc": ("GStreamer Base", "gstbase-1.0", ["gstreamer-1.0"]),
            "gstreamer-controller-1.0.pc": ("GStreamer Controller", "gstcontroller-1.0", ["gstreamer-1.0"]),
            "gstreamer-net-1.0.pc": ("GStreamer Net", "gstnet-1.0", ["gstreamer-1.0"]),
            "gstreamer-check-1.0.pc": ("GStreamer Check", "gstcheck-1.0", ["gstreamer-1.0"]),
        }
        for fname, (name, lib, requires) in subpkgs.items():
            req_str = ", ".join(requires)
            libs_line = f'Libs: -L"${{libdir}}" -l{lib}' if lib else ""
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/gstreamer-1.0

Name: {name}
Description: GStreamer sub-package ({name})
Version: 1.28.3
Requires: {req_str}
{libs_line}
Cflags: -I"${{includedir}}"
"""
            (gen_dir / fname).write_text(pc)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "gstapp-1.0",
            "gstaudio-1.0",
            "gstallocators-1.0",
            "gstfft-1.0",
            "gstpbutils-1.0",
            "gstriff-1.0",
            "gstrtp-1.0",
            "gstrtsp-1.0",
            "gstsdp-1.0",
            "gsttag-1.0",
            "gstvideo-1.0",
        ]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        # gstreamer and glib2 are transitive dependencies: consumers need their headers
        self.cpp_info.requires = ["gstreamer::gstreamer", "glib2::glib2"]
