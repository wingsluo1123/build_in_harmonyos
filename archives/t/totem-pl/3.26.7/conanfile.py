#!/usr/bin/env python3
"""Conan recipe -- totem-pl 3.26.7 (Meson).

Totem playlist parser (GNOME): m3u/pls/asf/xspf/rss/atom/qtl/smil/vcf/...
Two libraries: libtotem-plparser (full) / libtotem-plparser-mini (mini,
built from a reduced source set with -DTOTEM_PL_PARSER_MINI).

Adaptation notes:
- Official 2026-04 re-release (meson build), sha256 matches the upstream
  .sha256sum published on download.gnome.org
- zlib conflict: glib/2.88.3.1 requires zlib/1.3.2, libarchive/3.8.7
  requires zlib/1.3.1.1; pinned via override (102-recipe repo convention).
  1.3.x shares major.minor so all prebuilt dependents stay package_id-compatible.
- introspection disabled (no GI toolchain on CI workers)
- Optional features (uchardet/libarchive/libgcrypt) stay on 'auto':
  uchardet/libarchive resolve via pkg-config (PkgConfigDeps); libgcrypt is
  probed with cc.find_library and degrades silently if not on the -L path.
- po/ (103 catalogs) compiles with gettext tools from /data/service/hnp/bin
  (already on the profile buildenv PATH).
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class TotemPlConan(ConanFile):
    name = "totem-pl"
    version = "3.26.7"
    description = "Totem playlist parser (m3u/pls/asf/xspf/rss/atom/...) for GNOME"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/totem-pl-parser"
    url = "https://gitlab.gnome.org/GNOME/totem-pl-parser"

    package_type = "library"
    generators = ("PkgConfigDeps",)

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib/2.84.0.2: its OHOS binary was built against zlib/1.3.1.1, so its
        # package_id matches this graph exactly (2.88.3.x binaries pin zlib/1.3.2
        # and do not match the 1.3.1.1 override below). glib >= 2.56 is the
        # upstream minimum, 2.84 satisfies it.
        # totem-pl-parser.h exposes glib types (GType/GHashTable/...) in its
        # public API and the .so DT_NEEDEDs the glib family: propagate
        # headers+libs to consumers (they must see glib.h and link glib).
        self.requires("glib/2.84.0.2", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1")
        self.requires("libarchive/3.8.7")
        self.requires("uchardet/0.0.7")
        self.requires("libgcrypt/1.12.2")
        # glib->zlib/1.3.2 conflicts with libarchive->zlib/1.3.1.1; pin to the
        # repo-convention version (1.3.x == same major.minor, package_id stable)
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are NOT
        # on its PATH (same pattern as gstreamer 1.28.3). Pin real tools by
        # absolute path (resolved from PATH) and drop the broken env values.
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
        tc.project_options["introspection"] = "false"
        # uchardet/0.0.7 is published as a STATIC C++ archive; linking it into
        # the C shared library pulls in C++ runtime symbols
        # (__gxx_personality_v0, __cxa_pure_virtual, RTTI vtables). Append the
        # C++ standard library to every C link line so they resolve
        # (libc++.so ships in the SDK triple lib dir, found by the driver).
        tc.c_link_args.append("-lc++")
        # The uchardet/0.0.7 recipe exposes includedirs=["include"], but the
        # header is installed at include/uchardet/uchardet.h (its bundled real
        # uchardet.pc uses -I${includedir}/uchardet). Add the subdirectory so
        # that #include <uchardet.h> resolves.
        uchardet_inc = os.path.join(self.dependencies["uchardet"].package_folder,
                                    "include", "uchardet")
        if os.path.exists(os.path.join(uchardet_inc, "uchardet.h")):
            tc.c_args.append("-I" + uchardet_inc)
        tc.generate()
        # meson's gnome module locates glib tools (glib-mkenums, glib-genmarshal)
        # via pkg-config variables of glib-2.0 using UNDERSCORE names
        # (glib_mkenums / glib_genmarshal, as in the real glib .pc). The
        # PkgConfigDeps-generated .pc lacks those variables, so inject them;
        # the glib package's bindir already contains both tools.
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        with open(glib_pc, "r+") as f:
            content = f.read()
            if "glib_mkenums" not in content:
                anchor = "bindir=${prefix}/bin\n"
                if anchor not in content:
                    raise ConanInvalidConfiguration(
                        "glib-2.0.pc layout unexpected: cannot inject glib tool variables"
                    )
                content = content.replace(
                    anchor,
                    anchor
                    + "glib_mkenums=${bindir}/glib-mkenums\n"
                    + "glib_genmarshal=${bindir}/glib-genmarshal\n",
                )
            f.seek(0)
            f.write(content)
            f.truncate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # OHOS device workaround: meson's install-time rpath fixup rewrites the
        # built .so in place; on this hmdfs-backed device the rewrite corrupts
        # ~300 bytes (observed: 'X'-filled .dynstr region + damaged .dynamic),
        # leaving an ELF the dynamic loader refuses with EACCES. A plain copy
        # of the build-tree file writes cleanly and loads (verified on-device,
        # 2026-10-15). Re-copy and sha256-verify every installed
        # libtotem-plparser*.so; where the install copy is already intact the
        # hashes match and nothing changes.
        self._verify_shared_lib_integrity()

    @staticmethod
    def _sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()

    def _verify_shared_lib_integrity(self):
        pkg_lib = os.path.join(self.package_folder, "lib")
        built = {}
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if name.startswith("libtotem-plparser") and ".so." in name:
                    src = os.path.join(root, name)
                    if not os.path.islink(src):
                        built[name] = src
        for name, src in built.items():
            dst = os.path.join(pkg_lib, name)
            if os.path.islink(dst) or not os.path.isfile(dst):
                continue
            if self._sha256(src) == self._sha256(dst):
                continue
            shutil.copy2(src, dst)
            if self._sha256(src) != self._sha256(dst):
                raise ConanInvalidConfiguration(
                    f"shared library integrity check failed for {name}")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "totem-pl")
        includedirs = ["include/totem-pl-parser/1/plparser"]
        common_requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0",
                           "glib::gthread-2.0", "libxml2::libxml2"]

        plparser = self.cpp_info.components["plparser"]
        plparser.set_property("pkg_config_name", "totem-plparser")
        plparser.libs = ["totem-plparser"]
        plparser.includedirs = includedirs
        plparser.requires = common_requires + ["libarchive::libarchive",
                                               "uchardet::uchardet",
                                               "libgcrypt::libgcrypt"]

        mini = self.cpp_info.components["mini"]
        mini.set_property("pkg_config_name", "totem-plparser-mini")
        mini.libs = ["totem-plparser-mini"]
        mini.includedirs = includedirs
        mini.requires = common_requires
