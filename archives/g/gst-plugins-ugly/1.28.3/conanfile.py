#!/usr/bin/env python3
"""Conan recipe -- gst-plugins-ugly 1.28.3 (Meson).

GStreamer plugins that have licensing issues or are potentially
patent-encumbered. This recipe builds the non-GPL plugins (asfdemux,
dvdlpcmdec, dvdsub, realmedia) for OpenHarmony PC (aarch64).

Adaptation notes:
- Patch 0001 fixes Python script execution on HMDFS (find_program->files+python3)
- NLS disabled (no gettext on OHOS); _() macro stubbed via c_args
- orc disabled (not available on OHOS)
- GPL-licensed plugins (x264, cdio, dvdread, mpeg2dec, sidplay, a52dec) disabled
- All introspection, tests, examples, docs disabled
- gettext/ngettext stubbed as macros (same approach as gstreamer recipe)
- glib2 sub-package .pc files created in generate() (same as gstreamer recipe)
- gstreamer and gst-plugins-base .pc files created in generate()
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GstPluginsUglyConan(ConanFile):
    name = "gst-plugins-ugly"
    version = "1.28.3"
    description = "GStreamer plugins with licensing issues or patent-encumbered codecs"
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
        self.requires("gst-plugins-base/1.28.3")

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
        tc.project_options["nls"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["orc-compiler"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["glib_assert"] = "false"
        tc.project_options["glib_checks"] = "false"
        # GPL plugins are disabled by default (gpl=disabled)
        # This means x264, cdio, dvdread, mpeg2dec, sidplay, a52dec are not built
        tc.project_options["gpl"] = "disabled"
        # Stub gettext/ngettext when NLS is disabled (OHOS has no gettext)
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Dgettext(x)=(x)")
        tc.c_args.append("-Dngettext(s,p,n)=((n)==1?(s):(p))")
        tc.generate()

        # PkgConfigDeps (class-level generator) creates .pc files for
        # gstreamer, gst-plugins-base, and glib2, but the meson.build also
        # needs sub-package .pc files that Conan doesn't generate.
        # Create wrapper .pc files for all needed sub-packages.
        import pathlib
        gen_dir = pathlib.Path(self.generators_folder)

        glib2_prefix = self._get_dep_prefix("glib2")
        if glib2_prefix:
            self._create_glib_subpkg_pcs(gen_dir, glib2_prefix)

        gstreamer_prefix = self._get_dep_prefix("gstreamer")
        if gstreamer_prefix:
            self._create_gstreamer_pcs(gen_dir, gstreamer_prefix)

        gstbase_prefix = self._get_dep_prefix("gst-plugins-base")
        if gstbase_prefix:
            self._create_gst_plugins_base_pcs(gen_dir, gstbase_prefix)

    def _get_dep_prefix(self, dep_name):
        """Get the install prefix for a conan dependency by name."""
        for dep in self.dependencies.values():
            if dep.ref.name == dep_name:
                return str(dep.package_folder)
        return None

    def _create_glib_subpkg_pcs(self, gen_dir, prefix):
        """Create wrapper .pc files for glib2 sub-packages."""
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/glib-2.0"
        incdir1 = f"{prefix}/lib/glib-2.0/include"
        bindir = f"{prefix}/bin"
        datadir = f"{prefix}/share"

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

    def _create_gst_plugins_base_pcs(self, gen_dir, prefix):
        """Create wrapper .pc files for gst-plugins-base sub-packages."""
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/gstreamer-1.0"

        subpkgs = {
            "gstreamer-app-1.0.pc": ("GStreamer Application", "gstapp-1.0", ["gstreamer-1.0", "gstreamer-base-1.0"]),
            "gstreamer-audio-1.0.pc": ("GStreamer Audio", "gstaudio-1.0", ["gstreamer-base-1.0", "gstreamer-tag-1.0"]),
            "gstreamer-fft-1.0.pc": ("GStreamer FFT", "gstfft-1.0", ["gstreamer-1.0"]),
            "gstreamer-pbutils-1.0.pc": ("GStreamer Base Utils", "gstpbutils-1.0", ["gstreamer-audio-1.0", "gstreamer-video-1.0", "gstreamer-tag-1.0"]),
            "gstreamer-riff-1.0.pc": ("GStreamer RIFF", "gstriff-1.0", ["gstreamer-audio-1.0", "gstreamer-tag-1.0"]),
            "gstreamer-rtp-1.0.pc": ("GStreamer RTP", "gstrtp-1.0", ["gstreamer-base-1.0", "gstreamer-audio-1.0", "gstreamer-tag-1.0"]),
            "gstreamer-rtsp-1.0.pc": ("GStreamer RTSP", "gstrtsp-1.0", ["gstreamer-sdp-1.0", "gstreamer-rtp-1.0"]),
            "gstreamer-sdp-1.0.pc": ("GStreamer SDP", "gstsdp-1.0", ["gstreamer-rtp-1.0"]),
            "gstreamer-tag-1.0.pc": ("GStreamer Tag", "gsttag-1.0", ["gstreamer-base-1.0"]),
            "gstreamer-video-1.0.pc": ("GStreamer Video", "gstvideo-1.0", ["gstreamer-base-1.0", "gstreamer-tag-1.0"]),
        }
        for fname, (name, lib, requires) in subpkgs.items():
            req_str = ", ".join(requires)
            libs_line = f'Libs: -L"${{libdir}}" -l{lib}' if lib else ""
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/gstreamer-1.0

Name: {name}
Description: GStreamer base plugins sub-package ({name})
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
        # gst-plugins-ugly installs GStreamer plugins (.so/.a) to lib/gstreamer-1.0/
        # In static build, these are static archives that can be linked directly.
        self.cpp_info.libs = [
            "gstasf",
            "gstdvdlpcmdec",
            "gstdvdsub",
            "gstrealmedia",
        ]
        # Plugins are installed to lib/gstreamer-1.0/, not lib/
        self.cpp_info.libdirs = ["lib", "lib/gstreamer-1.0"]
        # gst-plugins-ugly does not install any headers
        self.cpp_info.includedirs = []
        # gstreamer and gst-plugins-base are transitive dependencies
        self.cpp_info.requires = [
            "gstreamer::gstreamer",
            "gst-plugins-base::gst-plugins-base",
        ]
