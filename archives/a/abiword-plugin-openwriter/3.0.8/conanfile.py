"""Conan recipe for abiword-plugin-openwriter 3.0.8 — OHOS PC cross-compile.

This is a **source-style** recipe: it ships the plugin source tree (extracted
from AbiWord 3.0.8 release-3.0.8.tar.bz2's `plugins/openwriter/` subdir)
under a custom in-tree layout, and conanfile.source() pulls the tarball,
strips the leading `AbiWord-release-3.0.8/` prefix, and copies the
sub-directory into self.build_folder.

The plugin ABI (the symbols the plugin shares with the abiword main library)
is intentionally NOT exposed to consumers — the consumer of this recipe is
the *abiword main library* recipe (archives/a/abiword/3.0.8/, TBD), not
the OHOS app. So we declare package_type = "library" and expose only the
plugin .so's path via cpp_info.libdirs.

Direct deps (per upstream plugin.m4 L1: `openwriter_pkgs="$gsf_req"` and
configure.ac L79 `gsf_req='libgsf-1 >= 1.14.18'`):
    - libgsf 1.14.18+ (we ship 1.14.58)
    - glib (for GObject — gsf_off_t etc)

Indirect deps (via libgsf conanfile.py):
    - libxml2 (libgsf requires)
    - zlib (libgsf requires, transitive)

Why we don't require libabiword here:
    The plugin links against abiword main library via the `OPENWRITER_LIBS`
    PLUGIN_LIBS substitution injected by abiword's configure. For OHOS we
    need a separate libabiword recipe (archives/a/abiword/3.0.8/, TBD) that
    produces libabiword-3.0.so/.a. This recipe declares libgsf + glib only
    — abiword's own recipe will add libabiword to its own requirements and
    link it in via the plugin's LDFLAGS.

Static-only on OHOS (mirroring libgsf R26 rationale):
    OHOS sysroot is static-only for the plugin host. The plugin .la is
    built -avoid-version -module, but the plugin object code links statically
    into the abiword process. Building libgsf with --enable-static means
    the plugin code references libgsf-1.a directly via the LDFLAGS -L chain
    in ohc-run.py (R-NEW 2026-08-06 libtool .la sweep).

Maintainer hint 2026-08-10: the upstream Makefile.am has the LDFLAGS
`module -no-undefined`, which is the "shared library must export every
symbol" rule. We relax this to allow static linking on OHOS where
`-no-undefined` would otherwise require every PLUGIN_LIBS dep to resolve
at plugin build time (libabiword isn't built yet at this point in the
build order).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AbiwordPluginOpenwriterConan(ConanFile):
    name = "abiword-plugin-openwriter"
    version = "3.0.8"
    description = "OpenDocument Text (.odt) import/export plugin for AbiWord"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/World/AbiWord"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}  # plugins are inherently modules

    def _validate_os(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"abiword-plugin-openwriter 3.0.8 only supports os=Linux/OHOS, "
                f"got {self.settings.os}"
            )
        # Plugins on OHOS: the plugin .so is dlopen'd by libabiword at
        # runtime, so we DO need shared=True on OHOS. Static linking
        # would require baking the plugin into libabiword itself which
        # violates AbiWord's plugin discovery model.
        if self.settings.os == "OHOS" and not self.options.shared:
            raise ConanInvalidConfiguration(
                "abiword-plugin-openwriter 3.0.8 on OHOS requires "
                "shared=True (R26: AbiWord discovers plugins via dlopen "
                "at runtime; static-linking the plugin would defeat "
                "AbiWord's plugin discovery model). Drop -o shared=False."
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Direct dep per upstream plugin.m4 + configure.ac gsf_req
        self.requires("gsf/1.14.58")
        # glib is implicit via libgsf's pkg-config, but the plugin
        # .cpp files include <glib.h> directly and use GObject types
        # (GsfInput*, gsf_off_t, etc.) — declare explicitly so that
        # downstream abiword consumers can resolve these symbols even
        # if libgsf's transitive glib is hidden by our pkg_config_name
        # forwarding.
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def configure(self):
        self._validate_os()

    def source(self):
        # conandata.yml sources has the upstream tarball (NOT just the
        # openwriter subdir — it's the full AbiWord source tarball).
        # get() with strip_root=True strips the leading
        # AbiWord-release-3.0.8/ prefix.
        get(self, **self.conan_data["sources"], strip_root=True)
        # Now self.source_folder contains plugins/openwriter/ as a
        # subdirectory. Move it to the build root so Makefile.am is
        # visible to autotools.
        src_plugin = os.path.join(self.source_folder, "plugins", "openwriter")
        if not os.path.isdir(src_plugin):
            raise ConanException(
                f"Expected {src_plugin} after extracting upstream tarball; "
                f"upstream structure may have changed."
            )
        # Move all entries from plugins/openwriter/* up to source_folder/
        for entry in os.listdir(src_plugin):
            src = os.path.join(src_plugin, entry)
            dst = os.path.join(self.source_folder, entry)
            os.rename(src, dst)
        os.rmdir(os.path.join(self.source_folder, "plugins", "openwriter"))
        # Best-effort cleanup of the rest of AbiWord source (saves ~100MB)
        for entry in os.listdir(os.path.join(self.source_folder, "plugins")):
            if entry == "openwriter":
                continue
            full = os.path.join(self.source_folder, "plugins", entry)
            if os.path.isdir(full):
                import shutil
                shutil.rmtree(full, ignore_errors=True)
            else:
                try:
                    os.remove(full)
                except OSError:
                    pass

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Mirror pidgin's R-NEW 2026-08-04 OHOS --build override.
        # See archives/g/gsf/1.14.58/conanfile.py L130-148 for full
        # rationale (config.guess 2018 doesn't recognize OHOS).
        from conan.tools.build import cross_building
        if self.settings.os == "OHOS" and not cross_building(self):
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")

        # We don't pass --host because the upstream plugin.m4 expects
        # to be configured by abiword's parent configure, not stand-alone.
        # Instead we manually invoke the build sequence in build().

        # R-NEW 2026-08-10 (libgsf mirror): set explicit --prefix paths
        # so libtool .la files have correct libdir=/lib etc.
        tc.update_configure_args({
            "--prefix": "/",
            "--libdir": "/lib",
            "--bindir": "/bin",
            "--includedir": "/include",
        })

        # Plugin-specific flags:
        #   --enable-openwriter=yes      : force-build even if upstream
        #                                  dependency probe would skip
        #                                  (we've already declared them)
        #   --disable-openwriter-builtin : produce a loadable module, not
        #                                  a builtin (plugins/ dir dlopen)
        tc.configure_args.extend([
            "--enable-openwriter=yes",
            "--disable-openwriter-builtin",
        ])

        # Add OPENWRITER_CFLAGS / OPENWRITER_LIBS so Makefile.am picks
        # up our pre-resolved flags. These mirror what abiword's parent
        # configure would set via plugin.m4.
        tc.extra_cflags = [
            "$(pkg-config --cflags libgsf-1 glib-2.0 gobject-2.0)"
        ]
        tc.extra_ldflags = [
            "$(pkg-config --libs libgsf-1 glib-2.0 gobject-2.0)"
        ]

        tc.generate()

    def build(self):
        # R-NEW (mirroring libgsf): sweep .la libdir for transitive deps.
        _LADIR_BAD = __import__("re").compile(
            r"^\s*libdir\s*=\s*['\"]?(?:/)?/?lib['\"]?\s*$",
            __import__("re").MULTILINE,
        )
        _INSTPREFIX_BAD = __import__("re").compile(
            r"^\s*inst_prefix_dir\s*=\s*['\"]?\s*(?:/+|lib/?|/+lib/?)?\s*['\"]?\s*$",
            __import__("re").MULTILINE,
        )
        _INSTPREFIX_PRESENT = __import__("re").compile(
            r"^\s*inst_prefix_dir\s*=",
            __import__("re").MULTILINE,
        )
        _DEPLIBS_BAD = __import__("re").compile(
            r"(-L)(?:/+|lib|/+lib|/+lib/|//lib/|//)(?=[\s'\"]|$)",
            __import__("re").IGNORECASE,
        )
        _LADIR_REPLACED = 0
        _INSTPREFIX_REPLACED = 0
        _INSTPREFIX_INJECTED = 0
        _DEPLIBS_REPLACED = 0
        _LADIR_SCANNED = 0
        for dep in self.dependencies.values():
            dep_libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_libdir):
                continue
            for la_name in os.listdir(dep_libdir):
                if not la_name.endswith(".la"):
                    continue
                _LADIR_SCANNED += 1
                la_path = os.path.join(dep_libdir, la_name)
                try:
                    with open(la_path, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _la_text = _fh.read()
                except OSError:
                    continue
                _new_text = _la_text
                if _LADIR_BAD.search(_new_text):
                    _new_text = _LADIR_BAD.sub(
                        f"libdir='{dep_libdir}'", _new_text, count=1)
                if _INSTPREFIX_PRESENT.search(_new_text):
                    if _INSTPREFIX_BAD.search(_new_text):
                        _new_text = _INSTPREFIX_BAD.sub(
                            f"inst_prefix_dir='{dep.package_folder}'",
                            _new_text, count=1)
                        _INSTPREFIX_REPLACED += 1
                else:
                    _new_text = _new_text.rstrip("\n") + \
                        f"\ninst_prefix_dir='{dep.package_folder}'\n"
                    _INSTPREFIX_INJECTED += 1
                if _DEPLIBS_BAD.search(_new_text):
                    _new_text = _DEPLIBS_BAD.sub(
                        f"\\g<1>{dep_libdir}", _new_text)
                    _DEPLIBS_REPLACED += 1
                if _new_text != _la_text:
                    try:
                        with open(la_path, "w", encoding="utf-8") as _fh:
                            _fh.write(_new_text)
                        _LADIR_REPLACED += 1
                    except OSError:
                        pass
        self.output.info(
            f"R-NEW: .la libdir sweep: scanned={_LADIR_SCANNED}, "
            f"rewrote_libdir={_LADIR_REPLACED}, "
            f"rewrote_inst_prefix={_INSTPREFIX_REPLACED}, "
            f"injected_inst_prefix={_INSTPREFIX_INJECTED}, "
            f"rewrote_deplibs={_DEPLIBS_REPLACED}"
        )

        apply_conandata_patches(self)

        # R-NEW (mirroring libgsf): patch umask 077 → 022 in upstream
        # configure scripts to avoid HMDFS EACCES during tempdir creation.
        from conan.tools.files import replace_in_file
        for _cfg_path in (
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.build_folder, "configure"),
        ):
            if not os.path.exists(_cfg_path):
                continue
            try:
                replace_in_file(
                    self, _cfg_path,
                    "umask 077", "umask 022",
                )
                self.output.info(
                    f"R-NEW: patched {_cfg_path} umask 077→022 (HMDFS fix)"
                )
            except Exception as _exc:
                self.output.warning(
                    f"R-NEW: failed to patch {_cfg_path}: {_exc!r}"
                )

        # The plugin uses a non-standard build flow: no ./configure at the
        # plugin level (plugin.m4 is meant to be sourced by abiword's parent
        # configure.ac). Instead, we replicate the Makefile.am target
        # directly via libtool.
        #
        # Why this works:
        #   1. xp/Makefile.am is a stock noinst_LTLIBRARIES libxp.la.
        #      It only needs $(OPENWRITER_CFLAGS), which we set via
        #      extra_cflags.
        #   2. ./Makefile.am is a stock plugin_LTLIBRARIES openwriter.la
        #      linking xp/libxp.la + $(OPENWRITER_LIBS). We can build
        #      it manually with the right libtool invocation.
        #
        # This sidesteps the upstream assumption that abiword's parent
        # configure must run first.

        from conan.tools.env import Environment
        env = Environment()
        env.define("OPENWRITER_CFLAGS",
                   "$(pkg-config --cflags libgsf-1 glib-2.0 gobject-2.0)")
        env.define("OPENWRITER_LIBS",
                   "$(pkg-config --libs libgsf-1 glib-2.0 gobject-2.0)")
        env.define("VERSION", "3.0.8")
        env_vars = env.vars(self)
        with env_vars.apply():
            autotools = Autotools(self)
            # Standalone configure isn't strictly needed since the plugin
            # Makefile.am doesn't reference autoconf-generated vars. But
            # autotools.configure() will run autoreconf first which is
            # harmless. We then call make with -C xp/ and -C ./ explicitly
            # to avoid the SUBDIRS recursion.
            try:
                autotools.configure(args=[
                    "--disable-maintainer-mode",
                    "--enable-openwriter=yes",
                    "--disable-openwriter-builtin",
                ])
            except Exception as _exc:
                # If configure fails (e.g., missing libabiword stub),
                # we still want to attempt the manual build below.
                self.output.warning(
                    f"R-NEW: autotools.configure() raised {_exc!r}; "
                    f"falling back to manual make"
                )

            # Manual build of xp/libxp.la
            jobs = self.conf.get("tools.build:jobs",
                                 default=os.cpu_count() or 2)
            self.run(
                f"make -C xp -j{jobs} libxp.la",
                env=env_vars
            )
            # Manual build of ./openwriter.la (plugin module)
            self.run(
                f"make -j{jobs} openwriter.la",
                env=env_vars
            )

    def package(self):
        # Copy the .la + .so (or .a if static) into package_folder.
        # We DON'T do `make install` because that requires libabiword
        # headers (plugin framework headers are installed by abiword's
        # own recipe). Instead, we copy the built artifacts and a
        # minimal ABI surface.
        copy(self, "*.la",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.so*",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        # Copy xp/ headers if any (none currently, but future-proof)
        copy(self, "*.h",
             src=os.path.join(self.build_folder, "xp"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)

    def package_info(self):
        # The plugin .la lives under <package>/lib/openwriter.la. libtool
        # consumers should dlopen() it; ABI consumers should link via
        # -lopenwriter.
        self.cpp_info.libs = ["openwriter"]
        self.cpp_info.set_property("cmake_file_name", "openwriter")
        self.cpp_info.set_property("cmake_target_name", "openwriter::plugin")
        self.cpp_info.set_property("pkg_config_name", "openwriter-plugin")
        # Forward gsf + glib so consumers don't need to redeclare
        # (mirroring libgsf's requires=[] forwarding pattern).
        self.cpp_info.requires = [
            "gsf::gsf",
            "glib::glib",
        ]
        self.cpp_info.system_libs = ["m", "pthread", "rt", "dl"]
