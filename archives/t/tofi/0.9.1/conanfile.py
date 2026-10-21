#!/usr/bin/env python3
"""Conan recipe for tofi 0.9.1 — Meson (C2x).

tofi is a minimal, highly configurable launcher for wlroots-based Wayland
compositors (`tofi`, with `tofi-run` / `tofi-drun` symlinks and the internal
`tofi-compgen` helper).

Build inputs declared by upstream meson.build:
    dependency('freetype2')            -> freetype/2.14.3
    dependency('harfbuzz')             -> harfbuzz/14.4.0
    dependency('cairo')                -> cairo/1.18.4.2
    dependency('pangocairo')           -> pango/1.58.2
    dependency('wayland-client')       -> wayland/1.24.0
    dependency('wayland-protocols', native: true) -> wayland-protocols/1.48
    dependency('wayland-scanner', native: true)   -> see below
    dependency('xkbcommon')            -> libxkbcommon/1.13.1
    dependency('glib-2.0')             -> glib/2.84.0.1
    dependency('gio-unix-2.0')         -> glib/2.84.0.1
Protocol XMLs compiled by wayland-scanner: stable/xdg-shell, stable/viewporter
(from wayland-protocols) plus the in-tree protocols/wlr-layer-shell-unstable-v1
and protocols/fractional-scale-v1.

Local adaptations (all inside the recipe, upstream sources unpatched):
  1. Static wayland-scanner. The scanner shipped by the registry `wayland`
     package cannot be executed here: its DT_NEEDED embeds the build machine's
     Conan cache path for libexpat, and the meson install step invalidated its
     `.codesign` section (two independent defects, measured 2026-10-16).
     A scanner that links against libc only is compiled from the same wayland
     release instead (DRAFT-ohos-static-tool-bypass-dlopen-limit; chayang /
     lavalauncher / wayland-protocols 1.47 precedents) and advertised through a
     self-authored wayland-scanner.pc.
  2. wayland-protocols.pc ships a build-machine prefix, so `pkgdatadir` would
     not resolve to the XMLs -> rewritten against the real package prefix.
  3. Every dependency .pc is copied with prefix/libdir/includedir rewritten to
     the actual package folder; pure transitive dependencies that conan marks
     as "Skipped binaries" (no binary installed, hence no .pc) are promoted to
     direct requirements.
  4. meson cannot find llvm-ar/ranlib on OHOS -> injected into the native file.
  5. An OHOS ELF needs a valid `.codesign` section to be execve-able (E077) and
     meson's install step rewrites the ELF, invalidating the linker's
     placeholder -> bin/tofi is re-signed as the last step of package().
Upstream test suite: test/{config.c,utf8.c} registered through
test/meson.build (`meson test`, TAP protocol). It is executed in build().
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# wayland release whose sources are used to build the embedded static scanner.
# Must match the wayland dependency version (checked in generate()).
SCANNER_WAYLAND_VERSION = "1.24.0"


class TofiConan(ConanFile):
    name = "tofi"
    version = "0.9.1"
    description = "A minimal, highly configurable launcher for wlroots-based Wayland compositors"
    license = "MIT"
    homepage = "https://github.com/philj56/tofi"
    url = "https://github.com/philj56/tofi"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def build_requirements(self):
        # the build system is Meson; the device has no system meson, the
        # packaged one is registered in the registry (chayang precedent)
        self.tool_requires("meson/1.11.0")

    def requirements(self):
        # direct dependencies of meson.build (literal refs so that the CI R36
        # registry check can read them from the AST)
        self.requires("freetype/2.14.3")
        self.requires("harfbuzz/14.4.0")
        self.requires("cairo/1.18.4.2")
        self.requires("pango/1.58.2")
        self.requires("wayland/1.24.0")
        self.requires("wayland-protocols/1.48")
        self.requires("libxkbcommon/1.13.1")
        self.requires("glib/2.84.0.1")

        # expat version conflict: wayland/1.24.0 asks for expat/2.8.2 (whose .so
        # has no SONAME — its absolute path would leak into DT_NEEDED) while
        # fontconfig/2.18.1.1 uses the clean rebuild 2.8.2.1. Unify on 2.8.2.1
        # (libwayland-*.so do not link expat; only the scanner does).
        self.requires("expat/2.8.2.1", override=True)

        # pkg-config visibility for pure transitive dependencies: conan marks
        # them "Skipped binaries" (no binary installed) so their .pc would be
        # missing and meson's dependency() lookups would fail
        # (hyprpicker / chayang precedent).
        self.requires("libffi/3.4.4")          # wayland-client.pc Requires.private
        self.requires("zlib/1.3.1.1")          # cairo.pc / glib-2.0.pc
        self.requires("pcre2/10.45")           # glib-2.0.pc Requires.private
        self.requires("pixman/0.46.4")         # cairo.pc
        self.requires("libpng/1.6.58")         # cairo.pc
        self.requires("fontconfig/2.18.1.1")   # cairo.pc / pangocairo.pc
        self.requires("fribidi/1.0.16")        # pango.pc
        self.requires("libthai/0.1.29")        # pango.pc
        self.requires("libdatrie/0.2.13")      # libthai.pc

        # libfts: musl (OHOS) provides neither fts.h nor fts_read(), and tofi's
        # drun backend walks the desktop-entry tree with fts(3)
        # (`cc.find_library('fts', required: not cc.has_function('fts_read'))`).
        # musl-fts/1.2.7 ships both the header and libfts.so.
        self.requires("musl-fts/1.2.7")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # wayland sources, used only to build the static wayland-scanner
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    # ── generate ─────────────────────────────────────────────────────────

    def _c_compiler(self):
        """The C compiler the profile actually uses (fallback: PATH/SDK)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if cc and os.path.isfile(cc):
            return cc
        return shutil.which("clang") or "/data/service/hnp/bin/clang"

    def _llvm_tool(self, name):
        """Locate an LLVM binutil next to the profile compiler, then PATH, then SDK."""
        tool_dir = os.path.dirname(self._c_compiler())
        candidate = os.path.join(tool_dir, name)
        if os.path.isfile(candidate):
            return candidate
        return shutil.which(name) or f"/data/service/hnp/bin/{name}"

    def generate(self):
        tc = MesonToolchain(self)
        # tofi builds executables only; keep the project default off "shared"
        tc.project_options["default_library"] = "static"

        # libfts is resolved by upstream with cc.find_library(), not through
        # pkg-config, so its -L has to be part of the global link flags
        # (MesonToolchain only forwards dependency .pc files otherwise).
        fts_dep = self.dependencies["musl-fts"]
        fts_base = fts_dep.package_folder
        tc.extra_ldflags = [f"-L{os.path.join(fts_base, 'lib')}"]

        # cairo.pc / pangocairo.pc / harfbuzz.pc / freetype2.pc only advertise
        # -I${includedir}/<subdir>, while upstream sources include
        # <cairo/cairo.h>, <cairo/cairo-ft.h>, <harfbuzz/hb.h>,
        # <freetype/fterrors.h>: the package prefix itself must be on the
        # include path. That is implicit for /usr/include on a distro but not
        # for a Conan package folder, so add every dependency's include root.
        dep_includes = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc) and inc not in dep_includes:
                dep_includes.append(inc)
        tc.extra_cflags = [f"-I{inc}" for inc in dep_includes]

        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        wayland_dep = self.dependencies["wayland"]
        wp_dep = self.dependencies["wayland-protocols"]
        # the embedded static scanner is compiled from the same wayland release
        # that is linked, otherwise generated protocol code and the runtime
        # library could disagree
        if wayland_dep.ref.version != SCANNER_WAYLAND_VERSION:
            raise ConanException(
                f"tofi: wayland dependency is {wayland_dep.ref.version} but the "
                f"embedded static scanner uses {SCANNER_WAYLAND_VERSION}; keep "
                "them in sync (SCANNER_WAYLAND_VERSION / requires)")
        if "scanner_sources" not in self.conan_data:
            raise ConanException(
                "tofi: conandata.yml must declare scanner_sources (wayland "
                "release used to build the static wayland-scanner)")

        # 1. wayland-scanner.pc — points at the static scanner built in build().
        #    MesonToolchain writes pkg_config_path into the native file's
        #    [built-in options], which is where a `native: true` dependency is
        #    resolved from, so fixed_pc_dir is on the lookup path on both sides.
        with open(os.path.join(fixed_pc_dir, "wayland-scanner.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={self.generators_folder}\n"
                    f"bindir=${{prefix}}\n"
                    f"wayland_scanner=${{bindir}}/wayland-scanner\n\n"
                    f"Name: Wayland Scanner\n"
                    f"Description: Wayland scanner (static, OHOS)\n"
                    f"Version: {SCANNER_WAYLAND_VERSION}\n")

        # 2. wayland-protocols.pc — upstream ships prefix=<build machine cache>,
        #    so pkgdatadir resolves to a directory that does not exist. Rewrite
        #    the whole file against the real package prefix (kwayland precedent).
        with open(os.path.join(fixed_pc_dir, "wayland-protocols.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={wp_dep.package_folder}\n"
                    f"datarootdir=${{prefix}}/share\n"
                    f"pkgdatadir=${{datarootdir}}/wayland-protocols\n\n"
                    f"Name: Wayland Protocols\n"
                    f"Description: Wayland protocol files\n"
                    f"Version: {wp_dep.ref.version}\n")

        # 3. every dependency .pc (wayland-client.pc, cairo.pc, …): the packaged
        #    prefix= may be "/" or a build-machine cache path, so
        #    -I${includedir} would resolve outside the package. Copy each .pc
        #    with prefix/libdir/includedir rewritten to the real package folder
        #    and put that copy first on PKG_CONFIG_PATH (hyprpicker / chayang).
        pc_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for pc_dir in ("lib", "share"):
                pc = os.path.join(dep.package_folder, pc_dir, "pkgconfig")
                if not os.path.isdir(pc):
                    continue
                pc_paths.append(pc)
                for pc_name in os.listdir(pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    # the two .pc files this recipe authors itself (above) must
                    # win: wayland-scanner.pc has to point at the static
                    # scanner, not at the packaged (non-executable) one
                    if pc_name in ("wayland-scanner.pc",
                                   "wayland-protocols.pc"):
                        continue
                    base = dep.package_folder
                    with open(os.path.join(pc, pc_name), "r",
                              encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
                    content = re.sub(r"(?m)^exec_prefix=.*$",
                                     f"exec_prefix={base}", content)
                    content = re.sub(r"(?m)^libdir=.*$", f"libdir={base}/lib", content)
                    content = re.sub(r"(?m)^includedir=.*$",
                                     f"includedir={base}/include", content)
                    # a packaged .pc may hardcode the build machine's cache path
                    content = re.sub(r"/[^\"\s]*/p/b/[^/\s]+/p", base, content)
                    # …or a root-relative prefix (freetype2.pc ships
                    # `Libs: -L//lib -lfreetype`, i.e. the packaging prefix was
                    # "/"): such -L/-I options point at the build machine's
                    # filesystem, not at this package folder.
                    for opt, sub in (("L", "lib"), ("I", "include")):
                        opt_re = re.compile(
                            rf"-{opt}(?://?{sub}|/usr(?:/local)?/{sub})(?=\s|$)",
                            re.MULTILINE)
                        content = opt_re.sub(f"-{opt}{base}/{sub}", content)
                    with open(os.path.join(fixed_pc_dir, pc_name), "w",
                              encoding="utf-8", newline="\n") as f:
                        f.write(content)
        if pc_paths:
            tc.pkg_config_path = os.pathsep.join([fixed_pc_dir] + pc_paths)
        else:
            tc.pkg_config_path = fixed_pc_dir
        tc.generate()

        # OHOS sandbox: meson cannot find llvm-ar/ranlib (chayang/wayland
        # precedent), so inject them into the native file's [binaries].
        ar_path = self._llvm_tool("llvm-ar")
        ranlib_path = self._llvm_tool("llvm-ranlib")
        native_file = os.path.join(self.generators_folder,
                                   "conan_meson_native.ini")
        with open(native_file, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nranlib = '{ranlib_path}'\nc =")
        with open(native_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    # ── OHOS ELF signing ─────────────────────────────────────────────────

    def _find_tool(self, name):
        """Locate an OHOS SDK tool (env override -> PATH -> SDK bin)."""
        env_name = "OHOS_" + name.upper().replace("-", "_")
        candidates = [
            os.environ.get(env_name),
            shutil.which(name),
            f"/data/service/hnp/bin/{name}",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_binary(self, path):
        """Give `path` a valid `.codesign` section (OHOS exec precondition).

        E077: HarmonyOS only loads ELF files that carry a `.codesign` section,
        and any tool that rewrites the ELF (strip/objcopy/patchelf, or meson's
        install-time RUNPATH rewrite) invalidates it. The signing tool refuses
        to overwrite an existing section, so the old one is removed first.
        """
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            raise ConanException(
                "tofi: binary-sign-tool not found; an unsigned ELF cannot be "
                "executed on OHOS (E077)")
        objcopy = self._find_tool("llvm-objcopy")
        if objcopy:
            self.run(f'{objcopy} --remove-section .codesign "{path}" '
                     f"2>/dev/null || true")
        signed = path + ".signed"
        self.run(f'{signer} sign -inFile "{path}" -outFile "{signed}" '
                 f"-selfSign 1")
        if not os.path.isfile(signed):
            raise ConanException(
                f"tofi: binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)
        self.output.info(f"tofi: signed {path}")

    # ── static wayland-scanner ───────────────────────────────────────────

    def _find_expat_static(self):
        """Locate a static libexpat.a for the fully static scanner link.

        The scanner is linked with `-static` so that it depends on libc only.
        Preference order: the SDK-bundled copy, then any static libexpat
        shipped by the dependencies. Fail loudly instead of degrading quietly.
        """
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder,
                                               "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                self.output.info(f"tofi: static expat -> {c}")
                return c
        raise ConanException(
            "tofi: no static libexpat.a found for the static wayland-scanner "
            f"link; tried: {candidates}")

    def _find_expat_include(self):
        candidates = ["/data/service/hnp/expat.org/expat_2.7.3/include"]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_static_scanner(self):
        """Build a statically linked wayland-scanner from the wayland sources."""
        src = os.path.join(self.source_folder, "wayland-scanner-src")
        if not os.path.isdir(src):
            raise ConanException(
                f"tofi: wayland scanner sources missing: {src}")

        # config.h + wayland-version.h are normally produced by the wayland
        # build system; generate the minimal forms by hand.
        config_h = os.path.join(src, "config.h")
        with open(config_h, "w", encoding="utf-8", newline="\n") as f:
            f.write('#define HAVE_EXPAT 1\n'
                    '#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        version_in = os.path.join(src, "src", "wayland-version.h.in")
        version_h = os.path.join(src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)]:
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        # the DTD is embedded into wayland.dtd.h by the upstream embed.py
        dtd_h = os.path.join(src, "src", "wayland.dtd.h")
        self.run(f'python3 {src}/src/embed.py {src}/protocol/wayland.dtd '
                 f'wayland_dtd > {dtd_h}', env="conanbuild")

        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = self._c_compiler()
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{src} -I{src}/src -I{src}/protocol '
            f'{src}/src/scanner.c {src}/src/wayland-util.c '
            f'{inc_flag}{expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild")
        self.output.info(
            f"tofi: built static wayland-scanner ({scanner_bin})")

    # ── build / package ──────────────────────────────────────────────────

    def build(self):
        # must happen before meson configure(): wayland-scanner is resolved
        # through find_program()/pkg-config, which only checks existence
        self._build_static_scanner()

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # upstream registers two TAP test executables in test/meson.build
        # (config, utf8) — run them for real; a failure fails the build
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # OHOS: an ELF must carry a valid `.codesign` section or the kernel
        # refuses to execve() it (E077). meson's install rewrites the ELF in
        # place (absolute RUNPATH -> placeholders), which invalidates the
        # linker's `.codesign` placeholder, so re-sign as the last step of
        # package(). bin/tofi-run / bin/tofi-drun are symlinks — skip them.
        binary = os.path.join(self.package_folder, "bin", "tofi")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)
            self._sign_ohos_binary(binary)

    def package_info(self):
        # command line tool (R38: commands.json at the software level)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # tofi links libfts.so (musl has no fts(3)); an application's transitive
        # shared dependency is not guaranteed to be propagated to consumers
        # (E1085/E2068), so publish its runtime path explicitly
        fts = self.dependencies.get("musl-fts")
        if fts and fts.package_folder:
            libdir = fts.cpp_info.libdirs[0] if fts.cpp_info.libdirs else "lib"
            self.runenv_info.append_path(
                "LD_LIBRARY_PATH", os.path.join(fts.package_folder, libdir))
