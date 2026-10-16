
"""Conan recipe — libhinoko 1.0.3 (Meson).

The library to operate 1394 OHCI hardware for isochronous communication
in IEEE 1394 bus (GObject-based; builds on top of libhinawa).

OHOS adaptation notes:
- Build system is meson (>=0.58) using gnome.genmarshal / gnome.mkenums.
  glib2/2.88.0 ships glib-genmarshal + glib-mkenums in its bin/, so
  generate() prepends that bin dir to PATH (build context only, R49:
  dependency package_folder, never a shared /usr/local) and appends the
  glib_genmarshal / glib_mkenums variables to the PkgConfigDeps-generated
  glib-2.0.pc (meson >=1.10 gnome module resolves the tools via pkg-config
  variables).
- glib's package_info only exposes the "glib-2.0" component to the
  PkgConfigDeps layout used by this recipe family, while src/meson.build
  hard-codes `dependency('gobject-2.0')`; generate() writes a
  gobject-2.0.pc wrapper into generators_folder — same pattern as the
  libhinawa 4.0.2 / gobject-introspection 1.80.1 recipes.
- src/meson.build uses `dependency('hinawa', version: '>=4.0.0')`.
  libhinawa/4.0.2's *installed* lib/pkgconfig/hinawa.pc carries the broken
  prefix=/ from its own meson install (see libhinawa notes.md), so
  generate() additionally writes a hinawa.pc wrapper into generators_folder
  (prefix = libhinawa package_folder, Requires: gobject-2.0, Cflags
  -I${includedir}/hinawa -I${includedir}); otherwise meson cannot resolve
  the hinawa dependency.
- Upstream src/meson.build calls gnome.generate_gir() unconditionally
  (Hinoko-1.0.gir/typelib, includes 'Hinawa-4.0'). Same trade-off as
  libhinawa: GIR is not the deliverable for this small peripheral library,
  so the `gir` option defaults to False and build() rewrites src/meson.build
  inline to drop the generate_gir call (non-greedy re.sub, warning +
  keep-original on anchor miss). See notes.md for the rationale.
- OHOS sysroot (/storage/Users/currentUser/usr/local/sysroot/usr/include)
  ships linux/firewire-cdev.h + linux/firewire-constants.h with every
  struct/ioctl/constant libhinoko 1.0.3 uses (fw_cdev_get_info,
  fw_cdev_create_iso_context, FW_CDEV_IOC_SET_ISO_CHANNELS,
  FW_CDEV_ISO_CONTEXT_*, SCODE_*, ...), so no backport-header patch is
  needed — left as "verify in main-task conan create" in notes.md.
- settings.os checks use `in ("Linux", "OHOS")` (R32); no bare ${CC}/
  ${CFLAGS} shell vars anywhere (R33), compiler comes from the Conan
  Toolchain via tools.build:compiler_executables.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment


class LibHinokoConan(ConanFile):
    name = "libhinoko"
    version = "1.0.3"
    description = ("The library to operate 1394 OHCI hardware for isochronous "
                   "communication in IEEE 1394 bus (GObject)")
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/libhinawa/libhinoko"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "gir": [True, False]}
    default_options = {"shared": True, "gir": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        
        
        
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        
        
        
        
        
        self.requires("libhinawa/4.0.2", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        
        
        
        self.tool_requires("meson/1.11.0")

    def validate(self):
        
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libhinoko is a Linux(1394 OHCI) library; unsupported os=%s" % self.settings.os)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        """Inject ar/ranlib into conan_meson_*.ini (meson cannot find llvm-ar
        by default on OHOS; same technique as libhinawa/pygobject/libgudev)."""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if bindir:
            for name in ("llvm-ar", "ar"):
                cand = os.path.join(bindir, name)
                if os.path.isfile(cand):
                    ar = cand
                    break
            for name in ("llvm-ranlib", "ranlib"):
                cand = os.path.join(bindir, name)
                if os.path.isfile(cand):
                    rl = cand
                    break
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_lines = []
            for line in content.splitlines(True):
                new_lines.append(line)
                if line.strip() == "[binaries]":
                    if ar and "\nar =" not in content:
                        new_lines.append("ar = '%s'\n" % ar)
                    if rl and "\nranlib =" not in content:
                        new_lines.append("ranlib = '%s'\n" % rl)
            new_content = "".join(new_lines)
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)
                self.output.info("libhinoko: injected ar/ranlib into %s" % nf_name)

    def _write_wrapper_pc(self):
        """glib 包只对外声明 glib-2.0 组件；meson.build 需
        dependency('gobject-2.0')。仿 libhinawa/4.0.2 与
        gobject-introspection/1.80.1 配方，在 generators_folder 写
        wrapper .pc（与 PkgConfigDeps 产物同目录）。
        """
        glib_root = self.dependencies["glib2"].package_folder
        ver = "2.88.0"
        with open(os.path.join(self.generators_folder, "gobject-2.0.pc"), "w") as f:
            f.write("prefix=%s\n" % glib_root)
            f.write("libdir=${prefix}/lib\n")
            f.write("includedir=${prefix}/include\n\n")
            f.write("Name: GObject\n")
            f.write("Description: GObject (wrapper for glib)\n")
            f.write("Version: %s\n" % ver)
            f.write("Requires: glib-2.0\n")
            f.write("Libs: -L${libdir} -lgobject-2.0\n")
            f.write("Cflags: -I${includedir}\n")

    def _write_hinawa_pc(self):
        """libhinawa/4.0.2 安装到 lib/pkgconfig 的 hinawa.pc prefix=/
        （其 meson install 阶段未做 prefix 重写），直接引用会解析到
        /include、/lib。本配方在 generators_folder 覆写一份正确 prefix
        的 hinawa.pc（prefix = libhinawa package_folder），使顶层
        meson.build 的 dependency('hinawa', version: '>=4.0.0') 可命中。
        Requires: gobject-2.0 与本配方 gobject-2.0.pc wrapper 配套。
        """
        hinawa_root = self.dependencies["libhinawa"].package_folder
        with open(os.path.join(self.generators_folder, "hinawa.pc"), "w") as f:
            f.write("prefix=%s\n" % hinawa_root)
            f.write("libdir=${prefix}/lib\n")
            f.write("includedir=${prefix}/include\n\n")
            f.write("Name: hinawa\n")
            f.write("Description: The library to operate 1394 OHCI hardware for "
                    "asynchronous communication in IEEE 1394 bus (wrapper)\n")
            f.write("Version: 4.0.2\n")
            f.write("Requires: gobject-2.0\n")
            f.write("Libs: -L${libdir} -lhinawa\n")
            f.write("Cflags: -I${includedir}/hinawa -I${includedir}\n")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["doc"] = False  
        tc.project_options["wrap_mode"] = "nofallback"
        tc.generate()

        PkgConfigDeps(self).generate()
        self._write_wrapper_pc()
        self._write_hinawa_pc()

        
        
        
        
        glib_root = self.dependencies["glib2"].package_folder
        _glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(_glib_pc):
            with open(_glib_pc, "a", encoding="utf-8") as f:
                f.write("glib_genmarshal=%s\n" % os.path.join(glib_root, "bin", "glib-genmarshal"))
                f.write("glib_mkenums=%s\n" % os.path.join(glib_root, "bin", "glib-mkenums"))
        self._inject_meson_binaries()

        
        
        
        glib_bin = os.path.join(glib_root, "bin")
        glib_lib = os.path.join(glib_root, "lib")
        env = Environment()
        env.prepend_path("PATH", glib_bin)
        
        env.prepend_path("LIBRARY_PATH", glib_lib)
        envvars = env.vars(self, scope="build")
        envvars.save_script("conan_hinoko_buildenv")

    def build(self):
        apply_conandata_patches(self)
        if not self.options.gir:
            
            
            
            
            
            
            
            src = os.path.join(self.source_folder, "src", "meson.build")
            with open(src, "r", encoding="utf-8") as f:
                content = f.read()
            new_content, n = re.subn(
                r"hinoko_gir = gnome\.generate_gir\(.*?\n\)\n",
                "hinoko_gir = []  # GIR generation disabled by recipe (gir=False)\n",
                content, flags=re.S)
            if n != 1:
                self.output.warning("libhinoko: gir rewrite anchor not found (%d); "
                                    "keeping original src/meson.build" % n)
            else:
                with open(src, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.output.info("libhinoko: GIR generation disabled (gir=False)")

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        
        
        
        
        
        
        
        _build_lib = os.path.join(self.build_folder, "src")
        _pkg_lib = os.path.join(self.package_folder, "lib")
        if os.path.isdir(_build_lib) and os.path.isdir(_pkg_lib):
            for _name in ("libhinoko.so.1.0.3", "libhinoko.so.1", "libhinoko.so"):
                _src = os.path.join(_build_lib, _name)
                if os.path.isfile(_src):
                    shutil.copy2(_src, os.path.join(_pkg_lib, _name))
                    self.output.info("libhinoko: refreshed %s from build dir (HMDFS safety)" % _name)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "hinoko")
        self.cpp_info.includedirs = ["include", os.path.join("include", "hinoko")]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["hinoko"]
        
        
