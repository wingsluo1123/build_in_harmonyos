#!/usr/bin/env python3
"""Conan recipe — json-glib 1.6.6 (Meson).

json-glib is a JSON parser/serializer library built on top of GLib/GObject.
Built shared to match the shared glib dependency (avoids the g_libintl_*
static-link symbol gap, E107/E123). The upstream Meson build needs no source
patch: gnome.mkenums runs fine once the meson python module is on PYTHONPATH,
and the project only special-cases host_system == 'windows' (no E090).
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class JsonglibConan(ConanFile):
    name = "json-glib"
    version = "1.6.6"
    description = "A library providing JSON serialization and deserialization support for GLib"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnome.pages.gitlab.gnome.org/json-glib/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # R26/R28: glib is published as a shared library on OHOS, and a static
    # json-glib against shared glib triggers the g_libintl_* undefined-symbol
    # gap (E107/E123). Default to shared to match the glib ABI.
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # json-glib is a C project; drop the C++ std setting.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib pulls in gio/gobject/gmodule/gthread + libintl/libffi/pcre2/zlib
        # transitively. json-glib only needs gio-2.0 directly.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: dependencies are provided via conan-generated pkg-config, not
        # shell env vars. PkgConfigDeps writes correct .pc files for all
        # transitive deps (glib's installed .pc use prefix=/, which conan
        # rewrites to the real package folder).
        PkgConfigDeps(self).generate()
        # Conan's PkgConfigDeps emits a minimal glib-2.0.pc that drops the
        # upstream tool variables (glib_mkenums/glib_genmarshal/gobject_query).
        # json-glib's gnome.mkenums queries `glib_mkenums` to locate the tool
        # and hard-fails without it. Patch the generated .pc to restore them.
        self._restore_glib_tool_vars()
        tc = MesonToolchain(self)
        # OHOS SDK's lld depends on libxml2.so.16 which is absent on CI
        # workers, causing meson's linker probe (clang -Wl,--version) to
        # crash. Use GNU ld (binutils) instead — it has no such dependency.
        tc.extra_ldflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        # Only pass --prefix (R1); let meson/conan drive the rest.
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Disable optional features that need unavailable native tools.
        tc.project_options["introspection"] = "disabled"  # g-ir-scanner needs ELF signing
        tc.project_options["gtk_doc"] = "disabled"        # gtk-doc
        tc.project_options["tests"] = "false"
        tc.project_options["man"] = "false"
        tc.generate()

        # gnome.mkenums runs `python3 -m mesonbuild.mesonmain` during the
        # build (captured by ninja). The HNP python cannot import the
        # mesonbuild module unless PYTHONPATH points at the meson install.
        # The meson wrapper sets it for `meson setup`, but ninja does not
        # inherit it. Expose PYTHONPATH via buildenv_info so conan's
        # generated conanbuild.sh (sourced before meson.compile()) exports
        # it into the ninja environment.
        self._expose_meson_pythonpath()

        # The CI profile only declares c/cpp under tools.build:compiler_executables;
        # MesonToolchain does not write ar/ranlib into the native file, so meson
        # probes `llvm-ar` by bare name and fails (clang toolchain is in
        # /data/service/hnp/bin). Inject the full ar/ranlib paths derived from
        # the c compiler's directory.
        self._inject_ar_ranlib()

    def _restore_glib_tool_vars(self):
        # Copy the upstream tool variables (glib_mkenums, glib_genmarshal,
        # gobject_query) from the glib package's own .pc into the conan
        # generated glib-2.0.pc, so gnome.mkenums can locate the tools.
        glib = self.dependencies["glib"]
        glib_pkg = glib.package_folder
        src_pc = os.path.join(glib_pkg, "lib", "pkgconfig", "glib-2.0.pc")
        dst_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not (os.path.isfile(src_pc) and os.path.isfile(dst_pc)):
            return
        import re
        with open(src_pc) as f:
            upstream = f.read()
        tool_vars = {}
        for key in ("glib_genmarshal", "gobject_query", "glib_mkenums"):
            m = re.search(r"^%s\s*=\s*(.+)$" % re.escape(key),
                          upstream, re.MULTILINE)
            if m:
                tool_vars[key] = m.group(1).strip()
        with open(dst_pc) as f:
            content = f.read()
        add = []
        for k, v in tool_vars.items():
            if re.search(r"^%s\s*=" % re.escape(k), content, re.MULTILINE):
                continue
            # upstream uses ${bindir}/tool ; keep as-is (bindir already set).
            add.append("%s=%s" % (k, v))
        if add:
            with open(dst_pc, "a") as f:
                f.write("\n# Restored upstream tool variables for gnome.mkenums\n")
                f.write("\n".join(add) + "\n")
        # Conan's PkgConfigDeps also drops -lintl from the glib component Libs.
        # glib's .so has g_libintl_* as undefined symbols (renamed gettext
        # macros from libintl.h) that are resolved by the shim libintl.so
        # shipped inside the glib package. Without -lintl on the link line,
        # executables linking glib (e.g. json-glib-validate/format) fail with
        # undefined symbol: g_libintl_* (E107/E123). Restore -lintl on the
        # glib components whose .so carries those undefined symbols.
        glib_libdir = os.path.join(glib_pkg, "lib")
        if os.path.isfile(os.path.join(glib_libdir, "libintl.so")):
            for comp in ("glib-2.0", "gio-2.0", "gobject-2.0"):
                pc = os.path.join(self.generators_folder, comp + ".pc")
                if not os.path.isfile(pc):
                    continue
                with open(pc) as f:
                    txt = f.read()
                if "-lintl" in txt:
                    continue
                m = re.search(r"^(Libs:\s*.+)$", txt, re.MULTILINE)
                if m:
                    new_libs = m.group(1) + " -lintl"
                    txt = txt.replace(m.group(1), new_libs, 1)
                    with open(pc, "w") as f:
                        f.write(txt)

    def _expose_meson_pythonpath(self):
        meson_bin = os.environ.get("MESON", "")
        if not meson_bin:
            for p in os.environ.get("PATH", "").split(os.pathsep):
                cand = os.path.join(p, "meson")
                if os.path.isfile(cand):
                    meson_bin = cand
                    break
        if not meson_bin:
            return
        try:
            with open(meson_bin) as f:
                head = f.read(512)
        except OSError:
            return
        # The meson wrapper exports PYTHONPATH=<dir>; reuse it so the build
        # python can import mesonbuild during gnome.mkenums.
        for line in head.splitlines():
            if "PYTHONPATH=" in line:
                pp = line.split("PYTHONPATH=", 1)[1].strip().strip('"').strip("'")
                if pp and os.path.isdir(pp):
                    self.buildenv_info.define_path("PYTHONPATH", pp)
                break

    def _inject_ar_ranlib(self):
        _ce = self.conf.get("tools.build:compiler_executables",
                            default={}, check_type=dict) or {}
        _ar = _ce.get("ar")
        _rl = _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and os.path.isfile(_nf):
            with open(_nf) as _f:
                _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl:
                    _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f:
                    _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        if self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        # meson install rewrites rpath -> linker self-sign invalidated; OHOS
        # XPM dlopen would reject it. Strip old .codesign + re-selfSign.
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                     .format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                     .format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["json-glib-1.0"]
        # Headers install under include/json-glib-1.0/json-glib/*.h ; consumers
        # #include <json-glib/json-glib.h> via -I.../include/json-glib-1.0.
        self.cpp_info.includedirs = ["include/json-glib-1.0", "include"]
        self.cpp_info.set_property("cmake_file_name", "json-glib")
        self.cpp_info.set_property("cmake_target_name", "json-glib::json-glib")
        self.cpp_info.set_property("pkg_config_name", "json-glib-1.0")
        # R32: treat OHOS like Linux for system libs.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
