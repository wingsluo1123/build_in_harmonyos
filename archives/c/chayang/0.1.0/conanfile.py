#!/usr/bin/env python3
"""Conan recipe for chayang 0.1.0 — Meson (C11).

chayang gradually dims the screen so it can be used as a grace period before
locking the session (`chayang && swaylock`). It is a single-file wlroots /
zwlr-layer-shell Wayland client (wayland-client only).

Requirements (meson.build):
  - `dependency('wayland-client')`        -> wayland/1.24.0
    (wayland-client.h + wayland-cursor.h + libwayland-client)
  - `dependency('wayland-protocols')`     -> wayland-protocols/1.36
    (stable/viewporter, stable/xdg-shell, staging/single-pixel-buffer-v1 XML)
  - `dependency('wayland-scanner', native: true, version: '>=1.14.91')`
    (protocol/meson.build turns the XML into client headers + marshalling code)

wayland-scanner: the `wayland` package ships such a binary, but on this device
it cannot be executed — its DT_NEEDED bakes the build machine's Conan cache
path for libexpat (`.../.cache/conan2/p/expat*/p/lib/libexpat.so`), so execve
fails with `Operation not permitted` (measured 2026-10-16, rc 126). A
statically linked scanner (libc only) is therefore compiled from the wayland
1.24.0 sources, following DRAFT-ohos-static-tool-bypass-dlopen-limit and the
archives/l/lavalauncher + archives/w/wayland-protocols/1.47 precedents.

Upstream ships no test suite: meson.build declares no `test()`. `meson test`
is still run in build() so the log carries the authoritative count
("No tests defined.").

OHOS ELF signature: the installed binary must carry a `.codesign` section or
the kernel refuses to execute it (E077). meson's install rewrites the ELF in place (it replaces the RUNPATH's
build-machine absolute paths with placeholders), which invalidates the
linker's `.codesign` placeholder (strip=False; any ELF rewrite does), so package() re-signs the
installed binary with `binary-sign-tool sign -selfSign 1` (E472 precedent).
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
# Must satisfy dependency('wayland-scanner', version: '>=1.14.91') and match
# the wayland dependency version.
SCANNER_WAYLAND_VERSION = "1.24.0"


class ChayangConan(ConanFile):
    name = "chayang"
    version = "0.1.0"
    description = "Gradually dim the screen (grace period before locking the session)"
    license = "MIT"
    homepage = "https://git.sr.ht/~emersion/chayang"
    url = "https://git.sr.ht/~emersion/chayang"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def build_requirements(self):
        # the build system is Meson; the device has no system meson, the
        # packaged one is registered in the registry (account-utils/c-list
        # precedent)
        self.tool_requires("meson/1.11.0")

    def requirements(self):
        # literal ref (not built from SCANNER_WAYLAND_VERSION) so that the CI
        # R36 registry check can read it: its AST extractor only sees constant
        # string arguments. Keep it in sync with SCANNER_WAYLAND_VERSION.
        self.requires("wayland/1.24.0")
        self.requires("wayland-protocols/1.36")
        # wayland-client.pc declares `Requires.private: libffi`, and pkg-config
        # resolves private requirements for --cflags. libffi is only a
        # transitive dependency of wayland, so Conan would treat it as a
        # "skipped binary" and never install its .pc -> meson fails to resolve
        # wayland-client. Promote it to a direct requirement (hyprpicker /
        # lavalauncher precedent).
        self.requires("libffi/3.4.4")

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
        # R26: terminal tool — build everything static, never ship a .so
        # (chayang itself builds no library; the option keeps the project's
        #  default_library off "shared").
        tc.project_options["default_library"] = "static"

        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        wayland_dep = self.dependencies["wayland"]
        wayland_base = wayland_dep.package_folder
        wp_base = self.dependencies["wayland-protocols"].package_folder
        # the embedded static scanner is compiled from the same wayland release
        # that is linked, otherwise the generated protocol code and the runtime
        # library could disagree
        if wayland_dep.ref.version != SCANNER_WAYLAND_VERSION:
            raise ConanException(
                f"chayang: wayland dependency is {wayland_dep.ref.version} but "
                f"the embedded static scanner uses {SCANNER_WAYLAND_VERSION}; "
                "keep them in sync (SCANNER_WAYLAND_VERSION / requires)")
        # the scanner source is required for the build
        if "scanner_sources" not in self.conan_data:
            raise ConanException(
                "chayang: conandata.yml must declare scanner_sources "
                "(wayland release used to build the static wayland-scanner)")

        # 1. wayland-scanner.pc — points at the static scanner built in build().
        #    MesonToolchain writes pkg_config_path into the native file's
        #    [built-in options], which is where a `native: true` dependency is
        #    resolved from (meson >= 1.11; the older [paths] section is
        #    deprecated), so fixed_pc_dir is on the lookup path on both sides.
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
            f.write(f"prefix={wp_base}\n"
                    f"datarootdir=${{prefix}}/share\n"
                    f"pkgdatadir=${{datarootdir}}/wayland-protocols\n\n"
                    f"Name: Wayland Protocols\n"
                    f"Description: Wayland protocol files\n"
                    f"Version: 1.36\n")

        # 3. every dependency .pc (wayland-client.pc, …): the packaged
        #    prefix= is "/" (meson root prefix), so -I${includedir} resolves to
        #    /include. Copy each .pc with the prefix/libdir/includedir
        #    rewritten to the real package folder and put that copy first on
        #    PKG_CONFIG_PATH (hyprpicker / lavalauncher precedent).
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
                    with open(os.path.join(fixed_pc_dir, pc_name), "w",
                              encoding="utf-8", newline="\n") as f:
                        f.write(content)
        if pc_paths:
            tc.pkg_config_path = os.pathsep.join([fixed_pc_dir] + pc_paths)
        else:
            tc.pkg_config_path = fixed_pc_dir
        tc.generate()

        # OHOS sandbox: meson cannot find llvm-ar/ranlib (wayland/zix/serd
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
        and any tool that rewrites the ELF (strip/objcopy/patchelf) invalidates
        it. The signing tool refuses to overwrite an existing section, so the
        old one is removed first.
        """
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            raise ConanException(
                "chayang: binary-sign-tool not found; an unsigned ELF cannot "
                "be executed on OHOS (E077)")
        objcopy = self._find_tool("llvm-objcopy")
        if objcopy:
            self.run(f'{objcopy} --remove-section .codesign "{path}" '
                     f"2>/dev/null || true")
        signed = path + ".signed"
        self.run(f'{signer} sign -inFile "{path}" -outFile "{signed}" '
                 f"-selfSign 1")
        if not os.path.isfile(signed):
            raise ConanException(
                f"chayang: binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)
        self.output.info(f"chayang: signed {path}")

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
                self.output.info(f"chayang: static expat -> {c}")
                return c
        raise ConanException(
            "chayang: no static libexpat.a found for the static "
            f"wayland-scanner link; tried: {candidates}")

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
                f"chayang: wayland scanner sources missing: {src}")

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
            f"chayang: built static wayland-scanner ({scanner_bin})")

    # ── build / package ──────────────────────────────────────────────────

    def build(self):
        # must happen before meson configure(): protocol/meson.build resolves
        # the scanner with find_program(), which only checks existence
        self._build_static_scanner()

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # Upstream has no test target; run the command anyway so the log
        # records the authoritative count ("No tests defined.").
        try:
            self.run("meson test", env="conanbuild")
        except Exception as e:
            self.output.warning(f"chayang: meson test reported: {e}")

    def package(self):
        meson = Meson(self)
        meson.install()
        # OHOS: an ELF must carry a valid `.codesign` section or the kernel
        # refuses to execve() it (E077). meson's install rewrites the ELF in place (RUNPATH absolute
        # paths -> placeholders), which invalidates the linker's `.codesign`
        # placeholder (strip=False; any ELF rewrite does) -> the
        # installed tool could not be executed ("Operation not permitted",
        # measured 2026-10-16). Re-sign after every ELF modification, i.e. as
        # the last step of package() (E077 four-step flow / E472 precedent).
        binary = os.path.join(self.package_folder, "bin", "chayang")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)
            self._sign_ohos_binary(binary)

    def package_info(self):
        # command line tool (R38: commands.json at the software level)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
