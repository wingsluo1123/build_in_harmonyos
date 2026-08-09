"""Conan recipe for libgsf 1.14.58 — GNOME Structured File Library, OHOS PC cross-compile.

Loaded by Conan via Python import machinery (no shebang). Wraps the upstream
autotools build and exposes ``libgsf-1.a`` as a CMake target ``gsf::gsf``.

Key invariants (inherited from the pidgin 2.14.14 recipe lessons):
  - Static-only on OHOS. ``_validate_os()`` accepts os=Linux/OHOS and
    forces shared=False on OHOS (R26: musl BIND_NOW; OHOS sysroot lacks
    libgsf-1.so).
  - zlib is REQUIRED in libgsf 1.14.58's configure.ac (cannot be turned
    off with --without-zlib). We require zlib/1.3.1 from the team registry.
  - intltool + gettext are build-time tools; not declared as Conan requires
    (they are host-installed, verified by ohc-run.py init-build env-check).
  - libxml2 dependency required by libgsf's libxml helper (xmlNanoHTTPOpen),
    not optional even though the main code path doesn't always use it.
  - No source patches yet — stock tarball builds clean on WSL/gcc-11.
    Patches will be added after first conan create failure on OHOS CI worker.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.build import cross_building


class GsfConan(ConanFile):
    name = "gsf"
    version = "1.14.58"
    description = "GNOME Structured File Library (read/write OLE2 compound documents)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgsf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def _validate_os(self):
        # R32: os must be Linux or OHOS (not == check)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gsf 1.14.58 only supports os=Linux/OHOS, got {self.settings.os}"
            )
        # R26: OHOS requires shared=False.
        # Same rationale as pidgin: glibc/musl + OHOS HMDFS static-only sysroot,
        # dlopen of prpl-style plugins blocked by musl BIND_NOW.
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "gsf 1.14.58 on OHOS requires shared=False (R26: "
                "OHOS sysroot has no libgsf-1.so; static-only build is "
                "the only viable path). Drop -o shared=True."
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Required by libgsf's PKG_CHECK_MODULES (configure.ac L86-90):
        #   - glib-2.0 + gobject-2.0 + gio-2.0 (>= 2.62.0)
        #   - libxml-2.0 (>= 2.4.16) — for xmlNanoHTTP* helpers
        #   - zlib (required, not optional; configure.ac L370-386 aborts
        #     with "*** zlib is required" if not found)
        #
        # Aligned with the team's ohpcd registry versions (per pidgin
        # maintainer hint 2026-07-31, applied uniformly across all recipes
        # in this repo):
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def configure(self):
        self._validate_os()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: Do NOT hardcode --host=<triplet>; AutotoolsToolchain auto-detects.
        # However, libgsf 1.14.58's config.guess 2018 (autotools shipped)
        # does NOT recognise HarmonyOS / HongMeng as a build system, so the
        # `@build@` autoconf substitution fails on OHOS workers with
        # "unable to guess build type; you must specify one" even though
        # host == build (aarch64 OHOS worker, compiling for aarch64 OHOS).
        #
        # Bypass config.guess by handing the build triplet explicitly.
        # Use `linux-gnu` as the build triplet: config.sub accepts it on
        # any vintage; @build@ resolves to aarch64-unknown-linux-gnu in
        # the generated Makefiles (harmless string, no effect on the build
        # artefact).
        #
        # R-NEW (mirroring pidgin 2.14.14 R-NEW 2026-08-04): gate the
        # `--build=` append with `cross_building` so we only override
        # config.guess when build machine actually IS aarch64 (native
        # build). If a future x86_64 OHOS worker uses an armv8 cross-
        # toolchain, AutotoolsToolchain auto-sets --host and our hard-
        # coded --build=aarch64-unknown-linux-gnu would make host==build
        # in configure's view, breaking conftests.
        if self.settings.os == "OHOS" and not cross_building(self):
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")

        # R26: Static-only on OHOS
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # libgsf has many optional features; we disable all the ones that
        # would pull additional runtime deps we don't ship on OHOS:
        #   --without-bz2         : skip libbzip2 (avoids bzip2 dep)
        #   --without-gdk_pixbuf  : skip gdk-pixbuf thumbnailer support
        #   --disable-introspection: skip gobject-introspection (g-i tools
        #                            not available on OHOS)
        #   --disable-gtk-doc     : skip gtkdoc (build-time only, harmless
        #                            but pulls in extra build deps)
        tc.configure_args.extend([
            "--without-bz2",
            "--without-gdk_pixbuf",
            "--disable-introspection",
            "--disable-gtk-doc",
        ])

        # R-NEW (mirroring pidgin 2.14.14 R-NEW 2026-08-06 / Pass 12):
        # set --prefix=/ and explicit --libdir=/lib, --bindir=/bin,
        # --includedir=/include to fix the libtool .la file paths.
        # See pidgin conanfile.py:227-263 for the full rationale.
        tc.update_configure_args({
            "--prefix": "/",
            "--libdir": "/lib",
            "--bindir": "/bin",
            "--includedir": "/include",
        })

        tc.generate()

    def build(self):
        # R-NEW (mirroring pidgin 2.14.14 R-NEW 2026-08-03): the .la libtool
        # files in transitive deps may carry libdir='/lib' (double-slash,
        # classic autoconf --prefix=/ artefact) that breaks the link stage.
        # Rewrite libdir + inst_prefix_dir + dependency_libs in any .la
        # files we receive from our requires(). See pidgin conanfile.py
        # L460-790 for the full Pass 1-5 algorithm.
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
        autotools = Autotools(self)

        # R-NEW (mirroring pidgin 2.14.14 R-NEW E011/E052/E129): on OHOS
        # HMDFS, configure's `umask 077` for temp dirs (configure L28963,
        # L28968 in autoconf 2.71) creates dirs owned by UID 20001006
        # while conan runs as UID 20020083, so ./confXXXX/subs1.awk
        # redirect hits EACCES. Patch umask 077 → umask 022.
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

        autotools.configure()

        # Honor -j parallel jobs from profile conf
        jobs = self.conf.get("tools.build:jobs",
                             default=os.cpu_count() or 2)
        autotools.make(args=[f"-j{jobs}"])

    def package(self):
        autotools = Autotools(self)
        # R-NEW (mirroring pidgin R-NEW 2026-08-06 / Pass 12): pass
        # DESTDIR explicitly to avoid double-nesting when --prefix=/.
        autotools.install(args=[f"DESTDIR={self.package_folder}"])

    def package_info(self):
        # libgsf installs libgsf-1.so/.a; upstream pkg-config name is
        # libgsf-1 (from libgsf-1.pc.in). cmake_file_name follows the
        # installed .pc name.
        self.cpp_info.libs = ["gsf-1"]
        self.cpp_info.set_property("cmake_file_name", "libgsf-1")
        self.cpp_info.set_property("cmake_target_name", "libgsf-1::libgsf-1")
        self.cpp_info.set_property("pkg_config_name", "libgsf-1")
        # libgsf installs headers to <pkg>/include/libgsf-1/gsf/ (note
        # the libgsf-1/ subdir), so consumers add this to their include path.
        self.cpp_info.includedirs = ["include/libgsf-1"]
        # Forward transitive deps for consumers linking only against
        # libgsf-1::libgsf-1 (canonical conan component name, NOT the
        # cmake_target_name — see pidgin conanfile.py L1100-1140 for the
        # rationale).
        self.cpp_info.requires = [
            "glib::glib",
            "libxml2::libxml2",
            "zlib::zlib",
        ]
        # musl/HMDFS behavior (mirroring pidgin rationale L1140-1160):
        # pthread/rt/dl are no-op in musl libc.so; forwarding them via
        # system_libs doesn't break OHOS (musl silently ignores) and
        # supports glibc profiles too.
        self.cpp_info.system_libs = ["m", "pthread", "rt", "dl"]
