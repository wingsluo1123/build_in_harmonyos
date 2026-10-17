#!/usr/bin/env python3
"""Conan recipe — parlatype 4.3 (GNOME audio transcription player).

Build system: meson.  Runtime stack: GTK4 + libadwaita-1 + GStreamer 1.0 +
iso-codes.  Unit test suite: 7 GTest binaries registered through meson
``test()`` (config, player, waveloader, waveviewer + 3 internal/static ones).

OHOS specifics handled here (aarch64-linux-ohos, project clang toolchain):

* Two glib providers coexist in this graph: ``glib/2.84.0.1.1`` (the chain
  gtk4/4.22.4 and libadwaita/1.8.8 are linked against) and ``glib2/2.88.0``
  (pulled in by ``gstreamer/1.28.3``).  Both packages claim the pkg-config
  name ``glib-2.0``, so the generated .pc files are normalized onto the
  in-graph ``glib`` package and ``-lintl`` is appended (glib/2.84.0.1.1
  exports ``g_libintl_*`` from the libintl.so.8 bundled in the same package;
  without it meson's ``-Wl,--no-undefined`` link fails).
* glib's bin/ tools (glib-compile-resources, glib-compile-schemas,
  glib-mkenums, …) are OHOS aarch64 ELF executables whose linker-time
  ``.codesign`` section is stale: OHOS XPM exec rejects them with
  "Operation not permitted" (ninja FAILED [code=126]).  They are re-signed
  in place and their package lib/ is added to LD_LIBRARY_PATH (no RPATH).
* MesonToolchain does not write ar/ranlib into the native file, so meson
  probes bare ``llvm-ar`` (absent from PATH) — the archiver is injected by
  absolute path.
* ``gnome.compile_resources()`` / ``gnome.post_install()`` resolve their
  helper tools through gio-2.0.pc variables that PkgConfigDeps does not emit.
* iso-codes is a data-only package: meson reads its ``prefix`` pkg-config
  variable to build ISO_CODES_PREFIX, so a wrapper iso-codes.pc with a real
  prefix is required.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# OHOS toolchain locations (project clang toolchain shipped with the image).
_OHOS_BIN = "/data/service/hnp/bin"


class ParlatypeConan(ConanFile):
    name = "parlatype"
    version = "4.3"
    description = ("Parlatype — audio transcription player for GNOME "
                   "(GTK4 + libadwaita + GStreamer)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.parlatype.xyz"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # meson dependency() name → conan package
        #   gtk4            (>= 4.14) → gtk4/4.22.4
        #   libadwaita-1    (>= 1.5)  → libadwaita/1.8.8 (needs gtk4 >= 4.19.4)
        #   gstreamer-1.0             → gstreamer/1.28.3
        #   gstreamer-app-1.0 / -audio-1.0 → gst-plugins-base/1.28.3
        #   iso-codes                 → iso-codes/4.20.1 (data-only)
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("libadwaita/1.8.8")
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        self.requires("iso-codes/4.20.1")
        # Keep the GTK4 side of the graph pinned exactly as gtk4/4.22.4 and
        # libadwaita/1.8.8 resolve it — the same pins their binaries were
        # linked against.
        self.requires("pango/1.56.4", override=True)
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # help/meson.build calls gnome.yelp(), whose gnome module resolves
        # itstool and msgmerge mandatorily.  The OHOS image ships gettext's
        # msgfmt/msgcat/xgettext but NOT msgmerge, and CI images ship no
        # gettext at all, so both tools have to come from the graph (they run
        # on the build machine as OHOS aarch64 binaries).
        # yelp-build / desktop-file-validate / appstream-util are only probed
        # with required:false and their validation tests are skipped.
        self.tool_requires("itstool/2.0.7")
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # generate
    # ------------------------------------------------------------------ #
    def generate(self):
        # MesonToolchain takes the archiver from tools.build:compiler_executables;
        # when it is empty meson probes bare `llvm-ar`, which is not on PATH on
        # OHOS.  Drop broken env values and resolve the real tools by path.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name)
                 for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not found in PATH: %s" % ", ".join(missing)
            )

        self._inject_glib_component_aliases()
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        # No GObject introspection data / gtk-doc reference / ASR support on the
        # cross target — the upstream defaults (all false) are kept explicitly
        # so a profile change cannot silently switch them on.
        tc.project_options["gir"] = "false"
        tc.project_options["gtk-doc"] = "false"
        tc.project_options["pocketsphinx"] = "false"
        tc.project_options["pocketsphinx-legacy"] = "false"
        tc.generate()

        self._inject_meson_archiver()
        # Wrapper shims first: _fix_pc_tools points the pkg-config tool
        # variables at them, so the shim dir must exist before that runs.
        self._prepare_host_tool_bins()
        self._fix_pc_tools()
        self._normalize_glib_pc()
        self._fix_iso_codes_pc()
        self._emit_pkgconfig_aliases()

    def _inject_glib_component_aliases(self):
        # libadwaita/1.8.8 (and appstream/1.2.0 underneath it) declares its
        # requirements against the component keys glib::glib / gobject / gio,
        # while glib/2.84.0.1.1 exposes them suffixed (glib-2.0, gobject-2.0,
        # gio-2.0).  PkgConfigDeps fails with "Component 'glib::gobject' not
        # found in 'glib'" unless the alias keys are added first.
        glib_dep = self.dependencies["glib"]
        for _suffix, _plain in (
            ("glib-2.0", "glib"),
            ("gobject-2.0", "gobject"),
            ("gio-2.0", "gio"),
            ("gmodule-2.0", "gmodule"),
        ):
            if (_suffix in glib_dep.cpp_info.components
                    and _plain not in glib_dep.cpp_info.components):
                glib_dep.cpp_info.components[_plain] = \
                    glib_dep.cpp_info.components[_suffix]

    def _inject_meson_archiver(self):
        # See generate(): pin ar/ranlib by absolute path in the generated
        # native file, because MesonToolchain leaves them out.
        _ce = self.conf.get("tools.build:compiler_executables",
                            default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir and os.path.isfile(os.path.join(_bindir, "llvm-ar")):
                _ar = os.path.join(_bindir, "llvm-ar")
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
        self.output.info("injected ar/ranlib into conan_meson_native.ini")

    def _fix_pc_tools(self):
        # gnome.compile_resources() and gnome.post_install() resolve their
        # helpers through pkg-config *variables* (glib_compile_resources,
        # glib_compile_schemas, gio_querymodules, gdbus_codegen,
        # glib_mkenums, …).  PkgConfigDeps emits none of them, so meson aborts
        # with "Could not get pkg-config variable and no default provided".
        # Point the variables at the generated wrappers when they exist: the raw
        # binaries cannot be executed with a shared LD_LIBRARY_PATH (see
        # _TOOL_LIB_ORDER).
        _shim = self._tool_shim_dir()

        def _tool(_name):
            _wrap = os.path.join(_shim, _name)
            return _wrap if os.path.isfile(_wrap) else "${prefix}/bin/" + _name

        _tool_vars = {
            "gio-2.0.pc": [
                "glib_compile_resources=" + _tool("glib-compile-resources"),
                "glib_compile_schemas=" + _tool("glib-compile-schemas"),
                "gio_querymodules=" + _tool("gio-querymodules"),
                "gdbus_codegen=" + _tool("gdbus-codegen"),
            ],
            "glib-2.0.pc": [
                "glib_genmarshal=" + _tool("glib-genmarshal"),
                "glib_mkenums=" + _tool("glib-mkenums"),
            ],
            "gtk4.pc": [
                "gtk_update_icon_cache=" + _tool("gtk4-update-icon-cache"),
            ],
        }
        for _pc, _vars in _tool_vars.items():
            _f = os.path.join(self.generators_folder, _pc)
            if not os.path.isfile(_f):
                continue
            with open(_f, encoding="utf-8") as _fh:
                _txt = _fh.read()
            _extra = []
            if "datadir=" not in _txt:
                _extra.append("datadir=${prefix}/share")
            for _v in _vars:
                if _v.split("=", 1)[0] not in _txt:
                    _extra.append(_v)
            if not _extra:
                continue
            _lines = _txt.splitlines(keepends=True)
            _ins = []
            for _ln in _lines:
                _ins.append(_ln)
                if _ln.startswith(("prefix=", "libdir=", "bindir=")) and _extra:
                    for _v in list(_extra):
                        _ins.append(_v + "\n")
                    _extra = []
            with open(_f, "w", encoding="utf-8") as _f2:
                _f2.write("".join(_ins))
            self.output.info("%s: appended tool/datadir variables" % _pc)

    # Packages that ship build-host tools meson has to *execute*: glib owns the
    # resource/schema/mkenums generators it calls itself, gtk4 owns
    # gtk4-update-icon-cache (gnome.post_install), gdk-pixbuf is a runtime
    # dependency of that tool.  glib is listed first on purpose — see below.
    _HOST_TOOL_DEPS = ("glib", "gdk-pixbuf", "gtk4")
    # …and the tools that come from the build context (tool_requires).
    _BUILD_TOOL_DEPS = ("gettext",)
    # Which packages' lib/ a wrapped tool must see first.  The graph carries two
    # mutually incompatible libintl.so.8: glib's exports g_libintl_* (glib/glib
    # itself needs it) while gettext's exports libintl_* (the gettext tools need
    # it), so no single search path can serve both — each tool gets its own.
    _TOOL_LIB_ORDER = {
        "glib": ("glib",),
        "gdk-pixbuf": ("glib", "gdk-pixbuf"),
        "gtk4": ("glib", "gdk-pixbuf", "gtk4"),
        "gettext": ("gettext",),
    }

    def _tool_shim_dir(self):
        # Helper tools are exposed through generated wrapper scripts so that
        # each one pins the library search path it was linked against.
        return os.path.join(self.generators_folder, "tools")

    def _prepare_host_tool_bins(self):
        # Prebuilt OHOS packages ship aarch64 ELF tools whose linker-time
        # ``.codesign`` section is stale: OHOS XPM exec rejects them with
        # "Operation not permitted" (E077), so meson's find_program() reports
        # "not found or not executable" and ninja dies with code=126.  Re-sign
        # them in place, then expose them through per-tool wrappers (the
        # prebuilt tools carry no usable RPATH — the gettext ones even carry
        # RUNPATH=//lib) plus PATH / LD_LIBRARY_PATH.
        _objcopy = os.path.join(_OHOS_BIN, "llvm-objcopy")
        _signer = os.path.join(_OHOS_BIN, "binary-sign-tool")
        _path_dirs, _lib_dirs, _folders = [], [], {}
        _targets = [(self.dependencies, _n) for _n in self._HOST_TOOL_DEPS]
        _targets += [(self.dependencies.build, _n) for _n in self._BUILD_TOOL_DEPS]
        for _view, _name in _targets:
            try:
                _dep = _view[_name]
            except KeyError:
                continue
            _folder = getattr(_dep, "package_folder", None)
            if not _folder:
                continue
            _folders[_name] = _folder
            _bin = os.path.join(_folder, "bin")
            _lib = os.path.join(_folder, "lib")
            if os.path.isdir(_bin):
                _path_dirs.append(_bin)
            if os.path.isdir(_lib):
                _lib_dirs.append(_lib)
            if not (os.path.isdir(_bin) and os.path.isfile(_signer)):
                continue
            for _tool in sorted(os.listdir(_bin)):
                _tp = os.path.join(_bin, _tool)
                if not os.path.isfile(_tp):
                    continue
                with open(_tp, "rb") as _f:
                    if _f.read(4) != b"\x7fELF":
                        continue  # shebang scripts (gdbus-codegen, …)
                try:
                    self.run('{oc} --remove-section .codesign "{f}" '
                             '2>/dev/null || true'.format(oc=_objcopy, f=_tp))
                    self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                             .format(sg=_signer, f=_tp))
                except Exception as _e:  # non-blocking: exec may still work
                    self.output.warning("re-sign %s failed: %s" % (_tp, _e))
            self.output.info("host tools prepared for %s (%s)"
                             % (_name, _bin))
        # gettext keeps its ITS rules in a versioned datadir; msgfmt needs them
        # for i18n.merge_file(type: 'xml') (the metainfo translations), but the
        # compiled-in path is unreachable through the /data/service/hnp/bin
        # symlink the host image puts on PATH, so point msgfmt at the copy that
        # ships inside the gettext package.
        _its_dirs = []
        _share = os.path.join(_folders.get("gettext", ""), "share")
        if os.path.isdir(_share):
            for _entry in sorted(os.listdir(_share)):
                if not _entry.startswith("gettext"):
                    continue
                _root = os.path.join(_share, _entry)
                if os.path.isdir(os.path.join(_root, "its")):
                    _its_dirs = [_root, os.path.join(_root, "its")]
                    break
        if _its_dirs:
            os.environ["GETTEXTDATADIR"] = _its_dirs[0]
            os.environ["GETTEXTDATADIRS"] = os.pathsep.join(_its_dirs)

        _shim = self._tool_shim_dir()
        os.makedirs(_shim, exist_ok=True)
        for _name, _folder in sorted(_folders.items()):
            _bin = os.path.join(_folder, "bin")
            if not os.path.isdir(_bin):
                continue
            _libs = []
            for _owner in self._TOOL_LIB_ORDER.get(_name, (_name,)):
                if _owner in _folders:
                    _owner_lib = os.path.join(_folders[_owner], "lib")
                    if os.path.isdir(_owner_lib):
                        _libs.append(_owner_lib)
            for _tool in sorted(os.listdir(_bin)):
                _real = os.path.join(_bin, _tool)
                if not os.path.isfile(_real):
                    continue
                _wrap = os.path.join(_shim, _tool)
                with open(_wrap, "w", encoding="utf-8") as _f:
                    _f.write('#!/bin/sh\n'
                             '# generated by the parlatype recipe: pin the '
                             'library search path this tool needs\n'
                             'export LD_LIBRARY_PATH="%s'
                             '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
                             'exec "%s" "$@"\n'
                             % ((os.pathsep.join(_libs) + os.pathsep)
                                if _libs else "", _real))
                os.chmod(_wrap, 0o755)
            self.output.info("tool wrappers written for %s" % _name)
        _path_dirs.insert(0, _shim)
        if _path_dirs:
            os.environ["PATH"] = os.pathsep.join(
                _path_dirs + [os.environ.get("PATH", "")])
        if _lib_dirs:
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                _lib_dirs + [os.environ.get("LD_LIBRARY_PATH", "")])

    def _normalize_glib_pc(self):
        # Both glib/2.84.0.1.1 and glib2/2.88.0 claim the pkg-config name
        # glib-2.0, and PkgConfigDeps leaves whichever it wrote last.  Force
        # every core glib .pc onto the in-graph glib package (the one gtk4 and
        # libadwaita are linked against) so headers, libraries and the process
        # runtime all agree, and re-add -lintl for glib-2.0.
        _glib_folder = self.dependencies["glib"].package_folder
        for _pc in ("glib-2.0", "gio-2.0", "gobject-2.0", "gmodule-2.0",
                    "gthread-2.0", "gio-unix-2.0"):
            _path = os.path.join(self.generators_folder, _pc + ".pc")
            _lines = []
            if os.path.isfile(_path):
                with open(_path, encoding="utf-8") as _f:
                    for _ln in _f.read().splitlines():
                        if _ln.startswith("prefix="):
                            _ln = "prefix=" + _glib_folder
                        elif _ln.startswith("Libs:") and _pc == "glib-2.0":
                            # glib's recipe lists libffi among cpp_info.libs, but
                            # its OHOS build folds libffi statically into
                            # libgobject (the .so has no libffi DT_NEEDED and the
                            # graph has no libffi package at all), so the bare
                            # -lffi only makes lld abort with "unable to find
                            # library -lffi".
                            _ln = " ".join(_t for _t in _ln.split()
                                           if _t != "-lffi")
                            if "-lintl" not in _ln:
                                _ln += " -lintl"
                        _lines.append(_ln)
            if not _lines:
                _lines = [
                    "prefix=" + _glib_folder,
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include",
                    "bindir=${prefix}/bin",
                    "",
                    "Name: " + _pc,
                    "Description: normalized onto the in-graph glib package",
                    "Version: 2.84.1",
                    "Libs: -L${libdir} -l" + _pc
                    + (" -lintl" if _pc == "glib-2.0" else ""),
                    "Cflags: -I${libdir}/glib-2.0/include "
                    "-I${includedir}/glib-2.0",
                ]
            with open(_path, "w", encoding="utf-8") as _f2:
                _f2.write("\n".join(_lines) + "\n")
        self.output.info("glib .pc normalized onto %s" % _glib_folder)

    def _fix_iso_codes_pc(self):
        # Data-only package: meson reads the `prefix` pkg-config variable to
        # compile ISO_CODES_PREFIX in (the JSON tables are looked up under
        # share/iso-codes at runtime).  PkgConfigDeps' bare version has no
        # library/include paths and the package's own share/pkgconfig/
        # iso-codes.pc keeps its build-time prefix, so write a wrapper.
        _dep = self.dependencies["iso-codes"]
        _folder = getattr(_dep, "package_folder", None)
        if not _folder:
            return
        _pc = os.path.join(self.generators_folder, "iso-codes.pc")
        with open(_pc, "w", encoding="utf-8") as _f:
            _f.write(
                "prefix=%s\n"
                "datadir=${prefix}/share\n"
                "pkgdatadir=${datadir}/iso-codes\n\n"
                "Name: iso-codes\n"
                "Description: ISO 639/3166/4217 code lists (data only)\n"
                "Version: %s\n"
                "Cflags:\n"
                "Libs:\n" % (_folder, _dep.ref.version)
            )
        self.output.info("iso-codes.pc wrapper written (prefix=%s)" % _folder)

    def _emit_pkgconfig_aliases(self):
        # PkgConfigDeps names each .pc after the *Conan package* (gstreamer.pc,
        # gst-plugins-base.pc) while upstream meson asks for the upstream
        # pkg-config module names (gstreamer-1.0, gstreamer-app-1.0,
        # gstreamer-audio-1.0) → "Dependency not found (tried pkg-config and
        # cmake)".  The aliases must be self-contained: the generated
        # gst-plugins-base.pc declares Requires: ogg/x11/xext/libdrm/…, none of
        # which have a .pc in the generators folder.
        _aliases = (
            ("gstreamer", "gstreamer-1.0",
             ("-lgstreamer-1.0", "-lgstbase-1.0"), "glib-2.0 gobject-2.0"),
            ("gst-plugins-base", "gstreamer-app-1.0",
             ("-lgstapp-1.0",), "gstreamer-1.0"),
            ("gst-plugins-base", "gstreamer-audio-1.0",
             ("-lgstaudio-1.0",), "gstreamer-1.0"),
        )
        for _pkg, _module, _libs, _req in _aliases:
            _dep = self.dependencies[_pkg]
            _folder = getattr(_dep, "package_folder", None)
            if not _folder:
                continue
            _pc = os.path.join(self.generators_folder, _module + ".pc")
            with open(_pc, "w", encoding="utf-8") as _f:
                _f.write(
                    "prefix=%s\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include/gstreamer-1.0\n\n"
                    "Name: %s\n"
                    "Description: alias for the %s Conan package\n"
                    "Version: %s\n"
                    "Libs: -L${libdir} %s\n"
                    "Cflags: -I${includedir}\n"
                    "Requires: %s\n"
                    % (_folder, _module, _pkg, _dep.ref.version,
                       " ".join(_libs), _req)
                )
            self.output.info("%s.pc alias written (prefix=%s)"
                             % (_module, _folder))

    # ------------------------------------------------------------------ #
    # build / package
    # ------------------------------------------------------------------ #
    def build(self):
        # Conan composes conanbuildenv-*.sh when the toolchain generators run,
        # i.e. before the wrappers above exist, and the PATH it records leads
        # with the host toolchain under /data/service/hnp/bin — whose msgfmt
        # cannot locate the ITS rules for the XML merge and whose libintl.so.8
        # is ABI-incompatible with glib's.  Re-apply the environment here, where
        # it is the last word before meson resolves its programs.
        self._prepare_host_tool_bins()
        apply_conandata_patches(self)
        meson = Meson(self)
        # The patches guard the yelp help pages behind an option that defaults
        # to off: they are built by itstool, which OHOS ships for the host as a
        # python script whose interpreter and libxml2 binding are unavailable.
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    # Unit cases that cannot work on the OHOS build host, with the measured
    # reason.  Everything else in the upstream suite must pass.
    #   display: the GTK4 cases need an X11/Wayland display.
    #   gst:     the GStreamer cases build pipelines at runtime and OHOS ships
    #            gst-plugins-base as static .a plugins only - there is no
    #            registry, no gst-plugin-scanner and no shared plugin to load,
    #            so gst_element_factory_make() returns NULL.
    _TEST_SKIP = {
        "config": "needs X11/Wayland display",
        "waveviewer": "needs X11/Wayland display",
        "gst": "needs shared GStreamer plugins (OHOS ships static .a only)",
        "player": "needs shared GStreamer plugins (OHOS ships static .a only)",
        "waveloader": "needs shared GStreamer plugins (OHOS ships static .a only)",
    }

    def _run_upstream_tests(self):
        """Run the upstream GTest binaries directly instead of via `meson test`.

        `meson test` drives the cases from a python process, and that python
        needs the distribution ``libintl.so.8`` (exporting ``libintl_*``) while
        the in-graph glib package ships its own ``libintl.so.8`` exporting
        ``g_libintl_*``.  The two share a SONAME but not a symbol set, so no
        single LD_LIBRARY_PATH satisfies both and every test binary dies with
        "Error relocating …: g_libintl_gettext: symbol not found" (exit 127).
        Executing the binaries ourselves takes python out of the picture; the
        host dependency libdirs are put ahead of whatever the build context
        injected (gettext's tool_requires libs) so glib's libintl wins.
        Per-test env comes from meson's own ``intro-tests.json``.
        """
        intro = os.path.join(self.build_folder, "meson-info", "intro-tests.json")
        if not os.path.isfile(intro):
            raise ConanException(
                "parlatype upstream tests: %s missing (meson configure did not "
                "record the suite)" % intro)
        with open(intro, encoding="utf-8") as handle:
            cases = json.load(handle)
        if not cases:
            raise ConanException("parlatype upstream tests: intro-tests.json is empty")

        libdirs = []
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for sub in ("lib", "lib64"):
                path = os.path.join(folder, sub)
                if os.path.isdir(path):
                    libdirs.append(path)
        injected = ":".join(libdirs)

        ran = failed = skipped = 0
        for case in cases:
            name = case.get("name") or ""
            cmd = case.get("cmd") or []
            if not cmd:
                skipped += 1
                self.output.info("skip test %s: no command recorded by meson" % name)
                continue
            if not os.path.isfile(cmd[0]):
                skipped += 1
                self.output.info("skip test %s: binary %s not built"
                                 % (name, cmd[0]))
                continue
            reason = self._TEST_SKIP.get(name)
            if reason:
                skipped += 1
                self.output.info("skip test %s: %s" % (name, reason))
                continue
            env = dict(os.environ)
            env.update(case.get("env") or {})
            previous = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(
                [x for x in (injected, previous) if x])
            proc = subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.STDOUT)
            ran += 1
            if proc.returncode == 77:
                skipped += 1
                continue
            if proc.returncode != 0:
                failed += 1
                self.output.warning("test %s failed (exit %d)"
                                    % (name, proc.returncode))
        self.output.info("parlatype upstream tests: %d run, %d passed, %d failed, "
                         "%d skipped" % (ran, ran - failed, failed, skipped))
        if failed:
            raise ConanException("parlatype upstream tests: %d failed" % failed)

    def package(self):
        Meson(self).install()

    def package_info(self):
        # 本包是 application 类型（GTK4 桌面应用），交付形态为「可执行文件 + 应用私有共享库」，
        # 不对外提供 C API：lib/libparlatype.so.7 只供 bin/parlatype 自身链接，
        # 随包投放的 .pc 与头文件供本包构建/插件场景使用，不对下游包暴露。
        # 因此显式清空 libdirs/includedirs，避免下游误把应用私有库当依赖库消费。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
