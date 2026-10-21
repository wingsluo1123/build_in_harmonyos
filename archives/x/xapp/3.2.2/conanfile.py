#!/usr/bin/env python3
"""Conan recipe — xapp 3.2.2 (Meson).

X-Apps platform library (libxapp) from Linux Mint — the GTK3 service library
consumed by xed / xreader / Pix and friends (favorites, gtk-window hints,
status icons, style managers). Adapted to HarmonyOS PC (aarch64): built
against the conan-published gtk/3.24.43 OHOS shared binary (broadway-only).

3.2.2 delta vs the 2.8.9 baseline recipe: the only upstream changes are
the root meson.build version line and internal GVariant logic inside
xapp-gpu-offload-helper.c (a "Discrete" key parsed into a private hash
table). libxapp/meson.build, xapp-gtk-window.c and meson_options.txt are
byte-identical, so the whole adaptation surface — dependency pins, meson
switches, the GDK_WINDOWING_X11 guard patch and the intl / alias-.pc
closure handling — carries over unchanged.

Disabled on OHOS (all upstream first-class meson switches, meson_options.txt):
  -Dapp-lib-only=true      core library only: drops xapp-kbd-layout-controller
                            (needs libgnomekbdui — X11/XKB stack, no OHOS
                            recipe), gtk3-module, icons, applets, scripts,
                            data and xapp-sn-watcher (needs dbusmenu-gtk3 —
                            recipe dir exists upstream-side but is not
                            published on ohpcd). Still installs libxapp.so +
                            xapp.pc + headers + gsettings schemas.
  -Dintrospection=false     g-ir-scanner cannot run (E179: OHOS refuses to
                            exec unsigned custom ELFs / load C extensions;
                            pygobject-3.0 also has no OHOS recipe).
  -Dvapi=false              must be paired with introspection (upstream
                            assert at libxapp/meson.build:149-150).
  -Dstatus-notifier=false   redundant under app-lib-only, pinned explicitly.
  -Ddocs=false              gtk-doc (default off upstream, pinned explicitly).

Platform facts this recipe absorbs (see notes.md for the evidence):
  - gtk/3.24.43 is broadway-only: no gdk/gdkx.h, gdkconfig.h has
    "#undef GDK_WINDOWING_X11", libgtk-3.so DT_NEEDED has no libX11.
    Upstream xapp-gtk-window.c uses gdkx/Xlib unconditionally → patched
    behind GTK's own GDK_WINDOWING_X11 window-system guard.
  - glib >= 2.84 routes gettext through proxy-libintl (g_libintl_* live in
    glib/lib/libintl.so, libglib-2.0.so only imports them) → -lintl must be
    appended to every link-bearing .pc (same fix as gtksourceview4/4.8.4,
    gtkspell3/3.0.10-r3 and gtk/3.24.43).
  - meson resolves dependency('gio-unix-2.0') / dependency('dbus-1') by .pc
    file name; the conan graph ships neither name verbatim (glib has no
    gio-unix-2.0 component, dbus recipe registers as "dbus") → both alias
    .pc files are synthesized in generate().
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class XappConan(ConanFile):
    name = "xapp"
    version = "3.2.2"
    description = "X-Apps platform library (libxapp) — OHOS adaptation"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/linuxmint/xapp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: platform check accepts os=OHOS (CI profile) and Linux (dev runs).
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xapp requires Linux or OHOS, got {self.settings.os}")

    def requirements(self):
        # xapp meson dependency() → conan package mapping:
        #   glib-2.0 / gobject-2.0 / gio-2.0 / gio-unix-2.0 / gmodule-2.0
        #                                     → transitive via gtk (shared glib,
        #                                       2.84.0.1 pin — gtk/3.24.43
        #                                       conanfile.py:78-85; glib2/2.88
        #                                       is a different family, do not mix)
        #   gtk+-3.0 (>= 3.22)                → gtk/3.24.43 (broadway-only OHOS
        #                                       shared binary, R36/PF4 gated)
        #   gdk-pixbuf-2.0 / cairo            → transitive via gtk (identical pins)
        #   x11                               → libx11/6.4.0 (OHOS-published
        #                                       binary; only the meson configure
        #                                       probe and pc need it — the X11
        #                                       code paths are compiled out by
        #                                       the GDK_WINDOWING_X11 guard)
        #   xkbfile (xapp.pc Requires.private) → libxkbfile/1.1.3 (consumers'
        #                                       pkg-config must resolve it)
        #   dbus-1 (session_bus_services_dir) → dbus/1.14.10.1 (pc variable only;
        #                                       libxapp itself uses GDBus, not
        #                                       libdbus; NOTE: .2 pulls
        #                                       glib/2.88.3 (conflicts with the
        #                                       gtk glib/2.84.0.1 pin, CI run-1)
        #                                       and .0 pins expat/2.8.2
        #                                       (conflicts with the fontconfig
        #                                       expat/2.8.2.1 pin, CI run-2);
        #                                       .1 is the gtk3-ecosystem-aligned
        #                                       revision — it requires exactly
        #                                       expat/2.8.2.1 and nothing else)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True)
        self.requires("libxkbfile/1.1.3")
        self.requires("dbus/1.14.10.1")

    def layout(self):
        # meson_layout() was removed in conan 2.29.x — replicate its folders:
        # builddir/ holds the meson build root, generators/ the .pc files.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI/worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are not
        # on PATH; pin the real toolchain binaries by ABSOLUTE PATH (gtk4 /
        # glib2 recipe precedent, otherwise meson picks nonexistent tools).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}")

        PkgConfigDeps(self).generate()
        self._synthesize_alias_pcs()
        tc = MesonToolchain(self)
        self._tc = tc
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # NEVER strip shared libs: the OHOS loader validates the .codesign hash,
        # strip rewrites the .so → dlopen Permission denied (libsoup3 lesson).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # No network wraps: every dependency is conan-provided.
        tc.project_options["wrap_mode"] = "nodownload"
        # Upstream first-class switches (meson_options.txt) — see module docstring.
        tc.project_options["app-lib-only"] = "true"
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["status-notifier"] = "false"
        tc.project_options["docs"] = "false"
        self._pin_build_env()
        tc.generate()
        self._patch_conanbuildenv()
        self._fix_glib_pcs()
        self._augment_pcs_intl()

    # ------------------------------------------------------------------
    # Build-time environment / glib host tools (OHOS specifics)
    # ------------------------------------------------------------------

    def _pin_build_env(self):
        """Pin meson's probe targets and the glib host tools by absolute path.

        OHOS measured facts (gtk4 / gtksourceview5 recipe precedents):
        * meson's ``detect_ninja`` runs ``ninja --version``; the hnp ninja ELF
          needs libc++_shared.so which the conan-rewritten environment drops →
          the probe fails ("Could not detect Ninja v1.8.2 or newer"). Inject the
          NINJA variable (meson's first probe candidate) plus /system/lib64 and
          the SDK llvm lib dir on LD_LIBRARY_PATH.
        * gdbus-codegen / glib-mkenums must come from the conan glib package
          (the hnp copies are stale and their shebangs are broken), and those
          ELFs need glib's own libs on LD_LIBRARY_PATH to exec at all.
        """
        _ninja = "/data/service/hnp/bin/ninja"
        if not os.path.isfile(_ninja):
            _ninja = shutil.which("ninja") or _ninja
        os.environ["NINJA"] = _ninja
        self.buildenv_info.define_path("NINJA", _ninja)

        for _p in ("/system/lib64",
                   "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"):
            if os.path.isdir(_p):
                os.environ["LD_LIBRARY_PATH"] = (
                    _p + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _p)

        gbin, glib_lib = self._glib_tool_dirs()
        if not gbin:
            self.output.warning("no dependency ships glib build-time tools "
                                "(gdbus-codegen / glib-mkenums)")
            return
        os.environ["PATH"] = gbin + os.pathsep + os.environ.get("PATH", "")
        self.buildenv_info.prepend_path("PATH", gbin)
        if glib_lib:
            os.environ["LD_LIBRARY_PATH"] = (
                glib_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", glib_lib)
        # gnome.gdbus_codegen()/mkenums_simple() resolve these from the meson
        # native file [binaries] section when present.
        for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                     "glib-compile-resources", "glib-compile-schemas"):
            tool_path = os.path.join(gbin, tool)
            if os.path.isfile(tool_path):
                self._tc.binaries[tool] = tool_path
        self.output.info("glib build-time tools pinned from %s" % gbin)

    def _glib_tool_dirs(self):
        """Return (bindir, libdir) of the dependency shipping glib's build-time
        tools — the graph may name that package glib or glib2."""
        for _ref, dep in self.dependencies.items():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            bdir = os.path.join(folder, "bin")
            if (os.path.isfile(os.path.join(bdir, "gdbus-codegen"))
                    or os.path.isfile(os.path.join(bdir, "glib-mkenums"))):
                return bdir, os.path.join(folder, "lib")
        return None, None

    def _patch_conanbuildenv(self):
        # ConanFile.run() wraps every command with `source conanbuild.sh`, and
        # the conanbuildenv-{settings}.sh file is (re)written after generate()
        # → the only working injection point is appending to the generated file
        # from build(), before the first meson call. NINJA + the two extra lib
        # dirs must be re-declared there because conan's env rebuild discards
        # the os.environ mutations made in generate().
        _sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        for envf in glob.glob(os.path.join(self.generators_folder, "conanbuildenv-*.sh")):
            with open(envf, encoding="utf-8") as handle:
                text = handle.read()
            append = ""
            if "NINJA=" not in text:
                append += '\nexport NINJA="/data/service/hnp/bin/ninja"\n'
            if 'export LD_LIBRARY_PATH="/system/lib64' not in text:
                append += ('export LD_LIBRARY_PATH="/system/lib64:%s'
                           '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n' % _sdk_lib)
            if append:
                if not text.endswith("\n"):
                    text += "\n"
                with open(envf, "w", encoding="utf-8") as handle:
                    handle.write(text + append)
                self.output.info("conanbuildenv patched: NINJA + /system/lib64 (%s)"
                                 % os.path.basename(envf))

    def _sign_glib_tools(self):
        """E077/E486: sign the glib package's host tool ELFs in place.

        OHOS refuses to exec an ELF carrying no valid ``.codesign`` section
        ("Operation not permitted", code 126). glib ships unsigned
        gdbus-codegen / glib-mkenums tools in its ``bin/`` and meson drives
        them through gnome.gdbus_codegen() / mkenums_simple() custom targets,
        so without signing every one of those targets dies
        (vte 0.74.2 / gtksourceview5 recipe precedent).
        """
        if self.settings.os != "OHOS":
            return
        gbin, _glib_lib = self._glib_tool_dirs()
        if not gbin or not os.path.isdir(gbin):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        signed = 0
        for name in os.listdir(gbin):
            binpath = os.path.join(gbin, name)
            if not os.path.isfile(binpath) or os.path.islink(binpath):
                continue
            try:
                with open(binpath, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run(f'{objcopy} --remove-section .codesign "{binpath}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{binpath}" -outFile "{binpath}" '
                     f'-selfSign 1 2>/dev/null || true')
            self.run(f'chmod a+x "{binpath}" 2>/dev/null || true')
            signed += 1
        self.output.info("signed %d glib host tool ELF(s) in place" % signed)

    def _fix_glib_pcs(self):
        # PkgConfigDeps generates glib-2.0.pc / gio-2.0.pc WITHOUT the tool
        # variables; meson's gnome module reads glib_mkenums (glib-2.0.pc) and
        # gdbus_codegen (gio-2.0.pc) → "Could not get pkg-config variable and
        # no default provided". Inject ABSOLUTE paths (the .pc's ${bindir} may
        # point at a different package than the one shipping the tools).
        gbin, _glib_lib = self._glib_tool_dirs()
        if gbin:
            inject = {
                "glib-2.0.pc": ("glib_mkenums", "glib_genmarshal", "gobject_query"),
                "gio-2.0.pc": ("glib_compile_resources", "glib_compile_schemas",
                               "gdbus_codegen"),
            }
            for pc_name, varnames in inject.items():
                pc = os.path.join(self.generators_folder, pc_name)
                if not os.path.isfile(pc):
                    self.output.warning("%s not generated, skip" % pc_name)
                    continue
                with open(pc, encoding="utf-8") as handle:
                    text = handle.read()
                add = []
                for var in varnames:
                    if var + "=" in text:
                        continue
                    tool = os.path.join(gbin, var.replace("_", "-"))
                    if os.path.isfile(tool):
                        add.append("%s=%s\n" % (var, tool))
                if not add:
                    continue
                out, inserted = [], False
                for line in text.splitlines(True):
                    out.append(line)
                    if not inserted and line.startswith("prefix="):
                        out.extend(add)
                        inserted = True
                if not inserted:
                    out.extend(add)
                with open(pc, "w", encoding="utf-8") as handle:
                    handle.write("".join(out))
                self.output.info("%s: injected glib tool variables" % pc_name)

    def _synthesize_alias_pcs(self):
        """Synthesize the .pc aliases meson resolves by FILE NAME.

        * dependency('gio-unix-2.0') (libxapp/meson.build:4): the glib recipe
          has no gio-unix-2.0 component (its gio-2.0 component already exposes
          include/gio-unix-2.0 and links the same libgio-2.0) → clone the
          generated gio-2.0.pc under the gio-unix-2.0 name.
        * dependency('dbus-1') (root meson.build:13, unconditional): the dbus
          recipe registers pkg_config_name "dbus", not "dbus-1" → clone
          dbus.pc as dbus-1.pc and add the session_bus_services_dir variable
          xapp reads via get_variable(pkgconfig:...) (no upstream default).
        """
        gen = self.generators_folder

        gio_pc = os.path.join(gen, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            with open(gio_pc, encoding="utf-8") as handle:
                text = handle.read()
            text = text.replace("Name: gio-2.0", "Name: gio-unix-2.0", 1)
            with open(os.path.join(gen, "gio-unix-2.0.pc"), "w",
                      encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            self.output.info("synthesized gio-unix-2.0.pc from gio-2.0.pc")
        else:
            self.output.warning("gio-2.0.pc not generated; cannot synthesize gio-unix-2.0.pc")

        dbus_pc = os.path.join(gen, "dbus.pc")
        if os.path.isfile(dbus_pc):
            with open(dbus_pc, encoding="utf-8") as handle:
                text = handle.read()
            text = text.replace("Name: dbus\n", "Name: dbus-1\n", 1)
            if "session_bus_services_dir=" not in text:
                out, inserted = [], False
                for line in text.splitlines(True):
                    out.append(line)
                    if not inserted and line.startswith("prefix="):
                        if "datadir=" not in text:
                            out.append("datadir=${prefix}/share\n")
                        out.append("session_bus_services_dir=${datadir}/dbus-1/services\n")
                        inserted = True
                if not inserted:
                    out.append("session_bus_services_dir=${prefix}/share/dbus-1/services\n")
                text = "".join(out)
            with open(os.path.join(gen, "dbus-1.pc"), "w",
                      encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            self.output.info("synthesized dbus-1.pc from dbus.pc (+session_bus_services_dir)")
        else:
            # Fallback: synthesize from the known dbus package layout
            # (include/dbus-1.0/dbus, lib/libdbus-1) — keeps meson's
            # dependency('dbus-1') probe working even if the generated
            # dbus.pc naming ever changes.
            for _ref, dep in self.dependencies.items():
                if getattr(dep, "ref", None) is None or dep.ref.name != "dbus":
                    continue
                folder = dep.package_folder
                if not folder:
                    break
                text = (
                    "prefix=%s\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n"
                    "datadir=${prefix}/share\n"
                    "\n"
                    "Name: dbus-1\n"
                    "Description: D-Bus message bus system (conan-synthesized alias)\n"
                    "Version: %s\n"
                    "Libs: -L${libdir} -ldbus-1\n"
                    "Cflags: -I${includedir} -I${includedir}/dbus-1.0\n"
                    "session_bus_services_dir=${datadir}/dbus-1/services\n"
                    % (folder, dep.ref.version)
                )
                with open(os.path.join(gen, "dbus-1.pc"), "w",
                          encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
                self.output.info("synthesized dbus-1.pc from dbus cpp_info layout")
                break

    def _augment_pcs_intl(self):
        """Append the proxy-libintl link input to every generated .pc whose
        libs participate in linking.

        glib's OHOS package routes gettext through proxy-libintl: its
        include/libintl.h remaps dgettext/bindtextdomain/... to g_libintl_*
        (see glib/include/libintl.h:49), and those are implemented in
        glib/lib/libintl.so — libglib-2.0.so itself only *imports* them.
        PkgConfigDeps regenerates the .pc files from cpp_info and therefore
        drops the -lintl that the packaged glib-2.0.pc carries, so linking
        the shared library (meson defaults to b_lundef=true) fails:

            ld.lld: error: undefined symbol: g_libintl_bindtextdomain
            >>> referenced by xapp-favorites.c

        libxapp includes glib/gi18n-lib.h and calls bindtextdomain()/dgettext()
        unconditionally (xapp-favorites.c:15 and friends), so the link always
        needs libintl. Same fix as the gtksourceview4/4.8.4, gtkspell3/3.0.10-r3
        and gtk/3.24.43 recipes — with one xapp-specific hardening: the token
        appended is the ABSOLUTE PATH of the glib package's lib/libintl.so
        (libido3 precedent), not a bare "-lintl". Reason (CI run-3 evidence):
        pkg-config/meson expand each .pc independently, and a bare -lintl
        appended to e.g. cairo.pc lands AFTER the cairo/pixman/fontconfig/
        expat/freetype/libpng/zlib -L dirs, where lld cannot locate any
        libintl ("unable to find library -lintl"). An absolute path input is
        position-independent.
        """
        _gbin, glib_lib = self._glib_tool_dirs()
        intl_token = "-lintl"
        if glib_lib:
            cand = os.path.join(glib_lib, "libintl.so")
            if os.path.isfile(cand) and " " not in cand:
                intl_token = cand
            else:
                intl_token = "-L%s -lintl" % glib_lib
        for name in ("glib-2.0.pc", "gio-2.0.pc", "gio-unix-2.0.pc",
                     "gobject-2.0.pc", "gmodule-2.0.pc", "gthread-2.0.pc",
                     "gtk+-3.0.pc", "gdk-3.0.pc", "gdk-pixbuf-2.0.pc",
                     "atk.pc", "pango-1.0.pc", "pangocairo-1.0.pc",
                     "cairo-gobject.pc", "cairo.pc"):
            pc = os.path.join(self.generators_folder, name)
            if not os.path.isfile(pc):
                continue
            with open(pc, encoding="utf-8") as handle:
                text = handle.read()
            out, changed = [], False
            for line in text.splitlines(True):
                if line.startswith("Libs:") and intl_token not in line:
                    line = line.rstrip("\r\n") + " " + intl_token + "\n"
                    changed = True
                out.append(line)
            if changed:
                with open(pc, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("".join(out))
                self.output.info("%s: appended intl link input" % name)

    # ------------------------------------------------------------------
    # Build / upstream tests / package
    # ------------------------------------------------------------------

    def build(self):
        # ConanFile.run() re-sources conanbuild.sh for every command, so the
        # NINJA / LD_LIBRARY_PATH injection must be re-applied to the already
        # generated conanbuildenv file from here (see _patch_conanbuildenv).
        self._patch_conanbuildenv()
        # E077: sign the glib host tools BEFORE the first meson custom command.
        self._sign_glib_tools()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._report_upstream_tests()

    def _report_upstream_tests(self):
        """NO_UPSTREAM_TESTS — full discovery, recorded for the audit trail.

        xapp 3.2.2 ships NO automated test suite (evidence, upstream tree):
        * all 13 meson.build files contain zero test() calls;
        * there is no tests/ directory anywhere in the tree;
        * test-scripts/ holds 7 manual interactive GUI demos (Python + gi,
          need a real display/desktop session) and is not wired into any
          meson target;
        * the only CI workflow (.github/workflows/build.yml) is build/package
          only, no test step;
        * meson_options.txt has no test-related switch.
        Therefore nothing upstream can be executed here — the platform
        assertions live in test_package/test_xapp.c (OHOS-specific, TAP).
        """
        self.output.info("UPSTREAM-TESTS: registered=0 (NO_UPSTREAM_TESTS: upstream xapp "
                         "3.2.2 has no meson test() suite — 13 meson.build files, no "
                         "tests/ dir, test-scripts/ are manual GUI demos not wired "
                         "into the build; discovery EVIDENCE_COMPLETE)")
        self.output.info("UPSTREAM-TEST-NONE: no upstream automated case exists to run; "
                         "OHOS-specific consumer assertions are in the test_package")

    def package(self):
        Meson(self).install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._restore_unstripped_so()
        self._sign_shared_libs()

    def _restore_unstripped_so(self):
        # meson install rewrites the rpath and mutates the .so after linking →
        # the linker's self-signature is invalidated and OHOS dlopen then
        # reports "Permission denied". Overwrite the installed library with the
        # pristine builddir artifact (libsoup3 / gtksourceview5 precedent) and
        # sign AFTER the overwrite (order matters, see _sign_shared_libs).
        src_dir_cands = [os.path.join(self.build_folder, "libxapp"),
                         os.path.join(self.source_folder, "builddir", "libxapp")]
        src_dir = next((d for d in src_dir_cands if os.path.isdir(d)), None)
        if not src_dir:
            self.output.warning("pristine builddir libxapp/ not found; skip restore")
            return
        for src in glob.glob(os.path.join(src_dir, "libxapp.so*")):
            if os.path.islink(src):
                continue
            dst = os.path.join(self.package_folder, "lib", os.path.basename(src))
            if os.path.isfile(dst):
                shutil.copy2(src, dst)
                self.output.info("restored pristine %s from the build dir"
                                 % os.path.basename(src))

    def _sign_shared_libs(self):
        # Strip any stale .codesign section and re-sign in place with
        # binary-sign-tool -selfSign 1 (ML-0043). Runs after
        # _restore_unstripped_so so the final artifact is the signed one.
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
        self.cpp_info.libs = ["xapp"]
        # meson layout: include/xapp/libxapp/*.h, xapp.pc Cflags -I${includedir}/xapp
        incs = [d for d in ("include/xapp", "include")
                if os.path.isdir(os.path.join(self.package_folder, d))]
        self.cpp_info.includedirs = incs or ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "xapp")
        self.cpp_info.set_property("cmake_target_name", "xapp::xapp")
        self.cpp_info.set_property("pkg_config_name", "xapp")
        # No cpp_info.requires: gtk/glib define components while cairo /
        # libx11 / libxkbfile are flat packages — the mixed refs are rejected
        # by CMakeDeps (gtk/3.24.43 recipe precedent, same rationale). Link
        # order and dependency closure ride the graph and each package's .pc.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
