#!/usr/bin/env python3
"""Conan recipe — libadwaita-1 1.9.2 (Meson).

libadwaita-1 is the Adwaita GNOME UI library built on GTK4. On HarmonyOS PC
(aarch64) GTK4 is already published (gtk4/4.22.4, Broadway backend only), so
this recipe consumes it and adds the Adwaita widgets layer.

Platform adaptations in this round:
  * AppStream metadata support is compiled OUT (-Dappstream=disabled):
    AppStream is not published on ohpcd, and the upstream subproject wrap
    points at github.com, which is unreachable from the OHOS build
    environment. The meson dependency is now optional (feature 'appstream')
    and the appdata-parse code in adw-about-dialog.c / adw-about-window.c is
    guarded by HAVE_APPSTREAM (config.h). Mirrors the gtk4 HAVE_EGL guard.
  * glib bin-tools (glib-mkenums / glib-genmarshal / glib-compile-resources /
    gdbus-codegen) are re-signed and pinned into the meson native file so the
    generated enums / resources / marshalers can be built on OHOS (XPM exec
    rejects stale .codesign).
  * Output .so files are re-signed post-install (ML-0043).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibAdwaitaConan(ConanFile):
    name = "libadwaita-1"
    version = "1.9.2"
    description = "libadwaita — GNOME Adwaita widgets for GTK4 (OHOS adaptation, AppStream enabled)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libadwaita"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        # libadwaita's CSS (src/stylesheet/*.scss) is compiled to base.css by
        # sassc. The tarball has no prebuilt base.css and the upstream
        # subproject wrap points at github (unreachable on OHOS), so sassc is
        # provided as a conan tool_require (sassc/3.6.2 published on ohpcd,
        # built on libsass/3.6.5). meson's find_program('sassc') then finds it
        # via the tool_require's bin dir on PATH.
        self.tool_requires("sassc/3.6.2")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libadwaita meson dependency() names → conan package names:
        #   glib-2.0 / gio-2.0 → glib/2.84.0.1.1 (shared=True, override=True;
        #       same hard constraint as gtk4/4.22.4 — see that recipe's notes.
        #       libadwaita requires glib >= 2.84.0.)
        #   gtk4 → gtk4/4.22.4 (published on ohpcd, requires >= 4.21.1;
        #       transitively provides pango/cairo/harfbuzz/gdk-pixbuf etc.)
        #   fribidi → fribidi/1.0.16 (pkg-config fribidi)
        #   appstream → appstream/1.2.0 (published on ohpcd 2026-09-26;
        #       -Dappstream=enabled, HAVE_APPSTREAM config guard active,
        #       About dialog/window from_appdata paths compile in)
        # zlib / fontconfig overrides pin the whole graph to the same versions
        # the published gtk4/4.22.4 graph uses (avoid R1-style conflicts).
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        # pango: the published gtk4/4.22.4 binary is built against pango/1.56.4
        # (gtk4 meson requires pango >= 1.56); the published appstream/1.2.0
        # binary declares pango/1.50.14 for its compose chain. Unify the whole
        # graph on 1.56.4 so both dependencies resolve against ohpcd binaries.
        self.requires("pango/1.56.4", override=True)
        # zstd: appstream/1.2.0 declares zstd/1.5.7.1 for its dependency graph
        # while the published gtk4/4.22.4 graph carries zstd/1.5.7 — unify on
        # the gtk4-chain version so the published gtk/cairo/pango binaries stay
        # matched (appstream itself is rebuilt from source in this round).
        self.requires("zstd/1.5.7", override=True)
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("appstream/1.2.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Same tool pinning as gtk4/4.22.4: meson probes bare llvm-ar on OHOS
        # which is not on PATH; pin tools by absolute path.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        # libxmlb (transitive dep of appstream/1.2.0) references glib component
        # keys WITHOUT the -2.0 suffix (glib::glib/gobject/gio/gmodule, written
        # against glib/2.88.3); the ohpcd glib/2.84.0.1.1 keys are suffixed
        # (glib-2.0/gobject-2.0/...). Inject plain aliases BEFORE PkgConfigDeps
        # so it resolves libxmlb's component requires (same trick as the
        # appstream recipe's generate()).
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
        tc = MesonToolchain(self)
        self._tc = tc
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Don't allow meson to fetch network wraps; deps are all conan-provided.
        tc.project_options["wrap_mode"] = "nodownload"
        # AppStream is provided by the appstream/1.2.0 conan package
        # (published on ohpcd): meson resolves dependency('appstream') via
        # PkgConfigDeps, HAVE_APPSTREAM is defined, from_appdata paths compile in.
        tc.project_options["appstream"] = "enabled"
        # No g-ir-scanner / vapi / docs on the OHOS toolchain.
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "false"
        tc.project_options["documentation"] = "false"
        # Demo/examples need a full display stack and are not part of the lib.
        tc.project_options["examples"] = "false"
        # gdbus-codegen must be pinned before tc.generate() (native file).
        self._prepend_glib_bin_to_path()
        tc.generate()
        self._inject_meson_archiver()
        self._fix_glib_pcs()
        self._fix_fribidi_pc()
        self._fix_glib_intl_libs()

    def _fix_fribidi_pc(self):
        # fribidi's public headers live in include/fribidi/ but PkgConfigDeps
        # generates fribidi.pc with only -I${includedir} — the same issue gtk4
        # fixed. src/adw-bidi.c includes <fribidi.h>.
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as _f:
            text = _f.read()
        if "include/fribidi" in text:
            return
        if "Cflags:" in text:
            text = text.replace("Cflags:", "Cflags: -I${includedir}/fribidi", 1)
        else:
            text += "Cflags: -I${includedir}/fribidi\n"
        with open(pc, "w", encoding="utf-8") as _f:
            _f.write(text)
        self.output.info("fribidi.pc: appended -I${includedir}/fribidi to Cflags")

    def _prepend_glib_bin_to_path(self):
        # libadwaita's meson build uses gnome.mkenums_simple / genmarshal /
        # compile_resources; those glib tools are OHOS aarch64 ELF binaries
        # whose .codesign is stale — XPM exec rejects them. Re-sign in place
        # and pin gdbus-codegen into the native file (find_program consults
        # native/cross files before PATH).
        import os as _os
        if not getattr(self, "dependencies", None):
            return
        _g = self.dependencies.get("glib")
        if not _g or not getattr(_g, "package_folder", None):
            return
        _gbin = _os.path.join(_g.package_folder, "bin")
        _gdbus = _os.path.join(_gbin, "gdbus-codegen")
        if _os.path.isfile(_gdbus):
            self._tc.binaries["gdbus-codegen"] = _gdbus
        if _os.path.isdir(_gbin):
            _os.environ["PATH"] = _gbin + _os.pathsep + _os.environ.get("PATH", "")
            _os.environ["LD_LIBRARY_PATH"] = _os.path.join(_g.package_folder, "lib") + _os.pathsep + \
                _os.environ.get("LD_LIBRARY_PATH", "")
        _objcopy = "/data/service/hnp/bin/llvm-objcopy"
        _signer = "/data/service/hnp/bin/binary-sign-tool"
        for _tool in _os.listdir(_gbin):
            _tp = _os.path.join(_gbin, _tool)
            if not _os.path.isfile(_tp):
                continue
            with open(_tp, "rb") as _f:
                _magic = _f.read(4)
            if _magic[:4] != b"\x7fELF":
                continue
            try:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=_objcopy, f=_tp))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=_signer, f=_tp))
            except Exception as _e:  # pragma: no cover — non-blocking
                self.output.warning("re-sign %s failed: %s" % (_tool, _e))

    def _fix_glib_pcs(self):
        # Conan PkgConfigDeps 生成的 glib-2.0.pc/gio-2.0.pc 不带工具变量。
        # libadwaita 的 gnome.mkenums（src/meson.build）读 glib_mkenums；
        # gnome.compile_resources 读 glib_compile_resources（经 gio-2.0.pc）。
        # 缺失时报 "Could not get pkg-config variable and no default provided"。
        inject = {
            "glib-2.0.pc": {
                "glib_mkenums": "${bindir}/glib-mkenums",
                "glib_genmarshal": "${bindir}/glib-genmarshal",
                "gobject_query": "${bindir}/gobject-query",
            },
            "gio-2.0.pc": {
                "glib_compile_resources": "${bindir}/glib-compile-resources",
                "glib_compile_schemas": "${bindir}/glib-compile-schemas",
                "gdbus_codegen": "${bindir}/gdbus-codegen",
            },
        }
        for pc_name, vars_map in inject.items():
            pc = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc):
                self.output.warning("fix %s: file not generated, skip" % pc_name)
                continue
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if all(k + "=" in text for k in vars_map):
                continue
            lines = text.splitlines(True)
            out = []
            for line in lines:
                out.append(line)
                if line.startswith("bindir="):
                    for k, v in vars_map.items():
                        if k + "=" not in text:
                            out.append("%s=%s\n" % (k, v))
            with open(pc, "w", encoding="utf-8") as _f:
                _f.write("".join(out))
            self.output.info("%s: injected %d tool variables" % (pc_name, len(vars_map)))
        # glib-2.0.pc Cflags 缺 include/gio-unix-2.0 → gio/gunixfdmessage.h 找不到
        pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if "gio-unix-2.0" not in text:
                if "Cflags:" in text:
                    text = text.replace("Cflags:", "Cflags: -I${prefix}/include/gio-unix-2.0", 1)
                else:
                    text += "Cflags: -I${prefix}/include/gio-unix-2.0\n"
                with open(pc, "w", encoding="utf-8") as _f:
                    _f.write(text)
                self.output.info("gio-2.0.pc: appended -I${prefix}/include/gio-unix-2.0 to Cflags")

    def _fix_glib_intl_libs(self):
        # The ohpcd glib/2.84.0.1.1 binary variant used in this graph ships
        # libglib-2.0.so with g_libintl_* symbols UNRESOLVED (U) and provides
        # its own libintl.so.8 in the same lib dir; the official glib-2.0.pc
        # therefore lists `Libs: -L${libdir} -lglib-2.0 -lintl`. PkgConfigDeps
        # drops the -lintl, so libadwaita's shared link fails with
        # "undefined symbol: g_libintl_dngettext" once the AppStream code path
        # (r05, -Dappstream=enabled) compiles in (adw-about-*.c use ngettext/
        # dngettext through glib's proxy-libintl header). Re-inject -lintl into
        # the generated .pc Libs lines for the glib family.
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc", "gmodule-2.0.pc"):
            pc = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc):
                continue
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            out = []
            changed = False
            for line in text.splitlines(True):
                if line.startswith("Libs:") and "-lintl" not in line:
                    line = line.rstrip("\n") + " -lintl\n"
                    changed = True
                out.append(line)
            if changed:
                with open(pc, "w", encoding="utf-8") as _f:
                    _f.write("".join(out))
                self.output.info("%s: appended -lintl to Libs (g_libintl_* resolution)" % pc_name)

    def _inject_meson_archiver(self):
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
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
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # NOTE: the upstream meson test suite (tests/ — 67 GTK unit tests) is
        # intentionally NOT executed here. libadwaita's GTK tests call
        # gtk_init() and abort (SIGABRT) on the headless OHOS build host —
        # there is no display server and GDK has only the Broadway backend,
        # which requires a running broadwayd. Compilation/linking of every
        # test binary succeeds (they are part of `ninja`); execution is
        # reported separately in the test ledger (task 台账), matching the
        # gtk4/4.22.4 recipe precedent (build-tests=false there).
        # test_package (a real consumer linking + running against the package)
        # still runs in the test() phase and does not require a display.

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # meson install rewrites rpath and mutates .so post-link → the linker
        # self-sign breaks; OHOS XPM dlopen then reports Permission denied.
        # Strip old .codesign + binary-sign-tool -selfSign 1 re-sign (ML-0043).
        import glob as _glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # libadwaita public headers install under include/libadwaita-1
        # (package_api_name = 'libadwaita-1'; meson installs headers to
        # ${includedir}/libadwaita-1, NOT libadwaita-1.0).
        self.cpp_info.includedirs = ["include/libadwaita-1"]
        self.cpp_info.libs = ["adwaita-1"]
        self.cpp_info.set_property("cmake_file_name", "libadwaita-1")
        self.cpp_info.set_property("cmake_target_name", "libadwaita-1::libadwaita-1")
        self.cpp_info.set_property("pkg_config_name", "libadwaita-1")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]