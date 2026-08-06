#!/usr/bin/env python3
"""Conan recipe -- gst-plugins-base 1.28.3 (Meson).

GStreamer base plugins and libraries. This recipe builds the gst-plugins-base
libraries (allocators, app, audio, fft, pbutils, riff, rtp, rtsp, sdp, tag,
video) and core plugins for OpenHarmony PC (aarch64).

Adaptation notes:
- Patch 0001 fixes Python script execution on HMDFS (meson-pkg-config-file-fixup.py,
  extract-release-date-from-doap-file.py)
- NLS disabled (no gettext on OHOS); _() macro stubbed via c_args
- All introspection, tests, examples, docs, orc, orc-compiler disabled
- gl, vorbis, theora, ogg, iso-codes disabled (no external deps on OHOS)
- tools disabled (executables not needed for library build)
- Wrapper .pc files created for glib2 sub-packages (same as gstreamer recipe)
- Wrapper .pc files created for gstreamer sub-packages (gstreamer-1.0, etc.)
"""
import os
import shutil
import pathlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins and libraries"
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
        self.requires("gstreamer/1.28.3@ohpcd/stable")
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
        tc.project_options["nls"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["orc-compiler"] = "disabled"
        tc.project_options["iso-codes"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["vorbis"] = "disabled"
        tc.project_options["theora"] = "disabled"
        tc.project_options["ogg"] = "disabled"
        tc.project_options["tools"] = "disabled"
        # Stub gettext/ngettext when NLS is disabled (OHOS has no gettext)
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Dgettext(x)=(x)")
        tc.c_args.append("-Dngettext(s,p,n)=((n)==1?(s):(p))")
        tc.generate()

        gen_dir = pathlib.Path(self.generators_folder)

        # PkgConfigDeps (class-level generator) creates a single glib2.pc
        # but gst-plugins-base's meson.build also needs gobject-2.0, gio-2.0,
        # gmodule-no-export-2.0, gio-unix-2.0 as separate pkg-config packages.
        # Create wrapper .pc files that point to the same glib2 package.
        glib2_prefix = self._get_dep_prefix("glib2")
        if glib2_prefix:
            self._create_glib_subpkg_pcs(gen_dir, glib2_prefix)

        # PkgConfigDeps creates a single gstreamer.pc but gst-plugins-base's
        # meson.build needs gstreamer-1.0, gstreamer-base-1.0, gstreamer-net-1.0,
        # gstreamer-controller-1.0, gstreamer-check-1.0 as separate packages.
        # Create wrapper .pc files that point to the same gstreamer package.
        gstreamer_prefix = self._get_dep_prefix("gstreamer")
        if gstreamer_prefix:
            self._create_gst_subpkg_pcs(gen_dir, gstreamer_prefix)

    def _get_dep_prefix(self, name):
        """Get a dependency's install prefix from conan deps."""
        for dep in self.dependencies.values():
            if dep.ref.name == name:
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
        # that gstreamer's meson.build queries via pkg-config.
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

        subpkgs = {
            "gobject-2.0.pc": ("GObject", "gobject-2.0", ["glib-2.0"]),
            "gio-2.0.pc": ("GIO", "gio-2.0", ["gobject-2.0"]),
            "gmodule-2.0.pc": ("GModule", "gmodule-2.0", ["glib-2.0"]),
            "gmodule-no-export-2.0.pc": ("GModule-no-export", "gmodule-2.0", ["glib-2.0"]),
            "gthread-2.0.pc": ("GThread", "gthread-2.0", ["glib-2.0"]),
            "gio-unix-2.0.pc": ("GIO-unix", None, ["gio-2.0"]),
        }
        for fname, (name, lib, requires) in subpkgs.items():
            req_str = ", ".join(requires)
            libs_line = f'Libs: -L"${{libdir}}" -l{lib}' if lib else ""
            extra_vars = ""
            if fname == "gio-2.0.pc":
                extra_vars = f"giomoduledir=${{libdir}}/gio/modules\n"
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include
{extra_vars}
Name: {name}
Description: GLib sub-package ({name})
Version: 2.88.0
Requires: {req_str}
{libs_line}
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
"""
            (gen_dir / fname).write_text(pc)

    def _create_gst_subpkg_pcs(self, gen_dir, prefix):
        """Create wrapper .pc files for gstreamer sub-packages.

        The gstreamer conan package provides these libraries:
          gstreamer-1.0, gstbase-1.0, gstcontroller-1.0, gstnet-1.0, gstcheck-1.0
        But meson looks for these pkg-config names:
          gstreamer-1.0, gstreamer-base-1.0, gstreamer-net-1.0,
          gstreamer-controller-1.0, gstreamer-check-1.0
        The Requires lines must include glib-2.0, gobject-2.0, etc. so that
        meson pulls in glib2's include paths when resolving gstreamer deps.
        """
        subpkgs = {
            "gstreamer-1.0.pc": (
                "GStreamer", "gstreamer-1.0",
                "glib-2.0 >= 2.64.0, gobject-2.0",
                "gmodule-2.0",
            ),
            "gstreamer-base-1.0.pc": (
                "GStreamer Base", "gstbase-1.0",
                "gstreamer-1.0, glib-2.0 >= 2.64.0, gobject-2.0, gmodule-no-export-2.0",
                "",
            ),
            "gstreamer-net-1.0.pc": (
                "GStreamer Net", "gstnet-1.0",
                "gstreamer-base-1.0, gstreamer-1.0, gio-2.0, gio-unix-2.0, glib-2.0 >= 2.64.0, gobject-2.0, gmodule-no-export-2.0",
                "",
            ),
            "gstreamer-controller-1.0.pc": (
                "GStreamer Controller", "gstcontroller-1.0",
                "gstreamer-1.0, glib-2.0 >= 2.64.0, gobject-2.0, gmodule-no-export-2.0",
                "",
            ),
            "gstreamer-check-1.0.pc": (
                "GStreamer Check", "gstcheck-1.0",
                "gstreamer-1.0, glib-2.0 >= 2.64.0, gobject-2.0, gmodule-no-export-2.0",
                "",
            ),
        }
        for fname, (name, lib, requires, requires_private) in subpkgs.items():
            req_line = f"Requires: {requires}" if requires else ""
            req_priv_line = f"Requires.private: {requires_private}" if requires_private else ""
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/gstreamer-1.0
pluginsdir=${{prefix}}/lib/gstreamer-1.0

Name: {name}
Description: GStreamer {name} library
Version: 1.28.3
{req_line}
{req_priv_line}
Libs: -L"${{libdir}}" -l{lib}
Cflags: -I"${{includedir}}" -DGST_STATIC_COMPILATION
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
            "gstallocators-1.0",
            "gstapp-1.0",
            "gstaudio-1.0",
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
        # gstreamer is a transitive dependency: consumers need gstreamer headers
        self.cpp_info.requires = ["gstreamer::gstreamer", "glib2::glib2"]