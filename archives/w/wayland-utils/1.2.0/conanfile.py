#!/usr/bin/env python3
"""Conan recipe for wayland-utils 1.2.0 — Meson.

wayland-info: CLI tool that connects to a Wayland compositor and prints the
advertised protocol globals (interfaces, versions, shm formats, outputs,
seats, and DRM lease/modifier info with libdrm enabled).

Upstream: https://gitlab.freedesktop.org/wayland/wayland-utils

OHOS workarounds (all following in-repo precedents):

1. wayland-scanner: the wayland/1.24.0 package ships bin/wayland-scanner,
   but OHOS refuses to execve that binary ("operation not permitted" —
   empirically, binaries extracted by conan's tarball handling into the
   cache are blocked, while freshly compiled ones are not). Following the
   proven precedent (archives/w/wayland-protocols/1.36.1 + 1.48,
   archives/w/wayneko/0_git20260326) a STATICALLY linked scanner that
   depends only on libc is compiled from the wayland 1.24.0 sources into
   the generators folder, and a synthesized wayland-scanner.pc points
   meson at it (upstream resolves the scanner through
   dependency('wayland-scanner', native: true) +
   get_pkgconfig_variable('wayland_scanner')).

2. Dependency .pc fixes (consumer side): the published wayland / libdrm
   packages carry prefix=/ and wayland-protocols carries
   pkgdatadir=${pc_sysrootdir}${datarootdir}/..., none of which resolves
   correctly for this build. Rewritten copies are placed in
   <generators>/fixed_pkgconfig, which is put first on PKG_CONFIG_PATH
   (meson dependency() resolves through pkg-config). This is the first
   pure-consumer instance of the fix (the library/data packages fixed
   their own .pc at package() time; a consumer cannot, so it must shadow
   them at generate() time).

3. meson native file: inject the llvm-ar path (OHOS sandbox hides it from
   meson subprocesses — zix/serd/wayland precedent) and make sure the
   native side resolves the synthesized wayland-scanner.pc.

4. RUNPATH: OHOS has no ld.so.conf entry for the Conan package cache, and
   CI's L2 smoke test runs the installed binary bare (no conanrun env).
   patchelf therefore embeds a DT_RUNPATH to the wayland package libdir
   after meson install — the inverse of the wmcdplay "drop build rpath"
   move, because here the cache path is exactly what must be kept —
   followed by the OHOS self-signing pass (binary-sign-tool,
   wayneko/wmcdplay precedent).

Upstream test suite: NONE — the 1.2.0 tarball ships no tests/ directory
and no meson test target (tar listing: meson.build, meson_options.txt,
wayland-info/, man/, COPYING, README.md, .gitlab-ci.yml only). wayland-info
also has NO --version option (parse_cmdline only knows -h/--help and
-i/--interface). Functional verification is the port-provided three-layer
test_package (see test_package/MANIFEST.yml) plus ci/config/no_official_test.txt.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# version of the wayland source used to build the embedded static scanner
SCANNER_WAYLAND_VERSION = "1.24.0"


class WaylandUtilsConan(ConanFile):
    name = "wayland-utils"
    version = "1.2.0"
    description = "wayland-info: Wayland compositor information tool"
    license = "MIT"
    homepage = "https://wayland.freedesktop.org/"
    url = "https://gitlab.freedesktop.org/wayland/wayland-utils"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # meson.build: dependency('wayland-client', version: '>= 1.20.0')
        #              dependency('libdrm', version: '>= 2.4.109') (drm feature)
        # wayland-info/meson.build:
        #              dependency('wayland-protocols', version: '>= 1.24')
        #              dependency('wayland-scanner', native: true)
        self.requires("wayland/1.24.0")
        self.requires("wayland-protocols/1.48")
        self.requires("libdrm/2.4.133")

    def validate(self):
        # R32: OHOS must be accepted, never require strictly "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is a Wayland client tool and only builds for "
                f"Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # wayland 源码，用于编译静态 wayland-scanner
        # （wayland-protocols 1.48 / wayneko 同款方案；scanner 版本须 >= 1.14.91，
        #  上游 wayland-info/meson.build 以 version_compare 判定 private-code 模式）
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _fix_pc(src, dst, prefix, version=None, strip_private=False):
        """Copy a dependency .pc with a rewritten prefix (shipped files say
        prefix=/, which pkg-config cannot resolve to the real package).

        strip_private: drop Requires.private lines — needed when the
        referenced packages (e.g. libffi behind wayland-client) are
        transitive deps whose .pc is not on this build's PKG_CONFIG_PATH;
        for a dynamic link against the shared library the private
        requirement is irrelevant to the consumer.
        """
        with open(src, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", content)
        if version is not None:
            content = re.sub(r"(?m)^Version:.*$", f"Version: {version}", content)
        if strip_private:
            content = re.sub(r"(?m)^Requires(\.private)?:.*$", "", content)
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def _find_expat_static(self):
        """Locate a static libexpat.a for the fully static scanner link.

        The scanner is linked with -static so it depends only on libc (the
        conan-cache scanner cannot be execve'd on OHOS). Preference order:
        the SDK-bundled copy used by the wayland-protocols/wayneko recipes,
        then any static libexpat shipped by dependencies.
        """
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder,
                                               "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                self.output.info(f"wayland-utils: static expat -> {c}")
                return c
        raise ConanException(
            "no static libexpat.a found for the static wayland-scanner link; "
            f"tried: {candidates}")

    def _find_expat_include(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/include",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_static_scanner(self):
        """Build a statically-linked wayland-scanner from wayland source.

        Mirrors archives/w/wayland-protocols/1.48 (device-proven): write the
        config/version headers by hand, embed wayland.dtd.h via embed.py,
        then compile scanner.c + wayland-util.c with -static against the
        static libexpat.
        """
        scanner_src = os.path.join(self.source_folder, "wayland-scanner-src")

        # Generate config.h
        config_h = os.path.join(scanner_src, "config.h")
        with open(config_h, "w", encoding="utf-8") as f:
            f.write('#define HAVE_EXPAT 1\n'
                    '#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        # Generate wayland-version.h from template
        version_in = os.path.join(scanner_src, "src", "wayland-version.h.in")
        version_h = os.path.join(scanner_src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)]:
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8") as f:
            f.write(content)

        # Generate wayland.dtd.h using embed.py
        dtd_h = os.path.join(scanner_src, "src", "wayland.dtd.h")
        self.run(
            f'python3 {scanner_src}/src/embed.py '
            f'{scanner_src}/protocol/wayland.dtd wayland_dtd > {dtd_h}',
            env="conanbuild",
        )

        # Compile static scanner (only depends on libc.so)
        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{scanner_src} -I{scanner_src}/src -I{scanner_src}/protocol '
            f'{scanner_src}/src/scanner.c {scanner_src}/src/wayland-util.c '
            f'{inc_flag}{expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild",
        )
        self.output.info("wayland-utils: built static wayland-scanner")

    @staticmethod
    def _sdk_lib_dirs():
        """Directories carrying the OHOS SDK / system C++ runtimes.

        libc++_shared.so (std::__n1 libc++ ABI) lives in
        $SDK/llvm/lib/aarch64-linux-ohos and /system/lib64 — NOT in
        $SDK/llvm/lib. Derived from the clang binary so it tracks the SDK
        version instead of a hard-coded path.
        """
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        sdk = os.path.dirname(os.path.dirname(os.path.realpath(cc)))
        # /system/lib64 MUST come first: binary-sign-tool needs the system
        # libc++.so (std::__h ABI) and the SDK's
        # lib/aarch64-linux-ohos/libc++.so is only a linker script
        # ("INPUT(-lc++_shared)") — if the SDK dir were searched first the
        # loader would latch onto that non-ELF file and die with "86 __h
        # symbols not found" (exit 127). /system/lib64 also carries
        # libc++_shared.so (std::__n1) for patchelf, so it satisfies both
        # tools; the SDK dir follows as a fallback for libc++_shared.so.
        return ["/system/lib64",
                os.path.join(sdk, "lib", "aarch64-linux-ohos"),
                os.path.join(sdk, "lib")]

    def _tool_env(self):
        """Environment for invoking the OHOS SDK host tools (patchelf /
        llvm-objcopy / binary-sign-tool).

        These are dynamically-linked OHOS binaries. A bare subprocess.run
        inherits the caller's LD_LIBRARY_PATH, which on the build worker does
        not resolve their runtimes (measured: patchelf exits 127 with
        "Error loading shared library libc++_shared.so ... _ZNSt4__n1 ...
        symbol not found" — the worker's LD_LIBRARY_PATH carries a malformed
        "         /system/lib64" entry with leading spaces, so the bare path
        is never searched). The conan build env is not sufficient either: the
        CI profile's [buildenv] lists only $SDK/llvm/lib, which does not
        contain libc++_shared.so. So we prepend the real SDK/system lib dirs.
        """
        env = dict(os.environ)
        dirs = self._sdk_lib_dirs()
        cur = env.get("LD_LIBRARY_PATH", "")
        if cur:
            dirs.append(cur)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(dirs)
        return env

    def _sign_ohos_elf(self, path):
        """Self-sign the freshly built OHOS binary (wayneko/wmcdplay
        precedent). Freshly compiled binaries usually execute fine
        unsigned, but signing removes the doubt on stricter workers; if the
        signing tools are absent we run unsigned.
        """
        if not os.path.isfile(path):
            raise ConanException(f"Missing installed binary: {path}")
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or \
            "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            return
        env = self._tool_env()
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True, timeout=30, env=env)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True, timeout=60, env=env)
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o555)

    # ── conan lifecycle ──────────────────────────────────────────────────

    def generate(self):
        tc = MesonToolchain(self)
        # Full feature parity: DRM info printing (libdrm/2.4.133 in repo).
        # All DRM code in wayland-info.c is guarded by #if HAVE_LIBDRM.
        tc.project_options["drm"] = "enabled"

        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)

        # 1) wayland-scanner.pc — points at the static scanner built in
        #    build(). Version must satisfy the upstream scanner>=1.14.91
        #    private-code mode check (wayland-info/meson.build).
        with open(os.path.join(fixed_pc_dir, "wayland-scanner.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"prefix={self.generators_folder}\n"
                    f"bindir=${{prefix}}\n"
                    f"wayland_scanner=${{bindir}}/wayland-scanner\n\n"
                    f"Name: Wayland Scanner\n"
                    f"Description: Wayland scanner\n"
                    f"Version: {SCANNER_WAYLAND_VERSION}\n")
        self.output.info("wayland-utils: created wayland-scanner.pc "
                         "(static scanner)")

        # 2) wayland-client.pc — the shipped file says prefix=/ (and an
        #    older Version); rewrite prefix to the real package and state
        #    the true 1.24.0 version (upstream requires >= 1.20.0).
        #    Requires.private (libffi) is dropped: libffi is a transitive
        #    dep whose .pc is not on this build's PKG_CONFIG_PATH, and for
        #    a dynamic link against the shared library it is irrelevant.
        wayland_base = self.dependencies["wayland"].package_folder
        self._fix_pc(
            os.path.join(wayland_base, "lib", "pkgconfig",
                         "wayland-client.pc"),
            os.path.join(fixed_pc_dir, "wayland-client.pc"),
            wayland_base,
            version=SCANNER_WAYLAND_VERSION,
            strip_private=True)
        self.output.info("wayland-utils: fixed wayland-client.pc prefix")

        # 3) libdrm.pc — shipped prefix=/ rewrite
        drm_base = self.dependencies["libdrm"].package_folder
        self._fix_pc(
            os.path.join(drm_base, "lib", "pkgconfig", "libdrm.pc"),
            os.path.join(fixed_pc_dir, "libdrm.pc"),
            drm_base)
        self.output.info("wayland-utils: fixed libdrm.pc prefix")

        # 4) wayland-protocols.pc — rewrite prefix AND make pkgdatadir an
        #    absolute path (the shipped file writes
        #    pkgdatadir=${pc_sysrootdir}${datarootdir}/wayland-protocols,
        #    which does not resolve here; meson reads pkgdatadir to locate
        #    the protocol XML files).
        wp_base = self.dependencies["wayland-protocols"].package_folder
        wp_pc = os.path.join(wp_base, "share", "pkgconfig",
                             "wayland-protocols.pc")
        if not os.path.isfile(wp_pc):
            wp_pc = os.path.join(wp_base, "lib", "pkgconfig",
                                 "wayland-protocols.pc")
        with open(wp_pc, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"(?m)^prefix=.*$", f"prefix={wp_base}", content)
        content = re.sub(
            r"(?m)^pkgdatadir=.*$",
            f"pkgdatadir={wp_base}/share/wayland-protocols",
            content)
        with open(os.path.join(fixed_pc_dir, "wayland-protocols.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("wayland-utils: fixed wayland-protocols.pc "
                         "(prefix + absolute pkgdatadir)")

        tc.pkg_config_path = os.pathsep.join(
            [fixed_pc_dir, tc.pkg_config_path or ""])
        tc.generate()

        # OHOS sandbox: meson cannot find llvm-ar (zix/serd/wayland
        # precedent) — inject an `ar` line into the generated native file.
        # Also make sure the native side resolves the synthesized
        # wayland-scanner.pc (upstream looks the scanner up with
        # native: true, which searches the native [paths]).
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc =")
        if "[paths]" in content:
            content = content.replace(
                "[paths]",
                f"[paths]\npkg_config_path = '{fixed_pc_dir}'")
        else:
            content += f"\n[paths]\npkg_config_path = '{fixed_pc_dir}'\n"
        with open(native_file, "w") as f:
            f.write(content)

    def build(self):
        # 静态 scanner 必须在 meson configure 之前构建
        # （wayland-info/meson.build 的 find_program() 检查二进制是否存在）
        self._build_static_scanner()

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

        binary = os.path.join(self.package_folder, "bin", "wayland-info")
        if not os.path.isfile(binary):
            raise ConanException(
                f"wayland-info was not installed: {binary}")

        # Embed a DT_RUNPATH to the wayland package libdir. OHOS has no
        # ld.so.conf entry for the Conan cache and CI's L2 smoke test runs
        # the installed binary bare (no conanrun env); verified on device
        # that a RUNPATH-carrying aarch64 ELF against the cached .so
        # executes fine. (Inverse of wmcdplay's drop-rpath move: here the
        # cache path is exactly what must be kept.)
        wayland_base = self.dependencies["wayland"].package_folder
        wayland_libdir = os.path.join(wayland_base, "lib")
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        if os.path.isfile(patchelf):
            # patchelf is itself a dynamically-linked OHOS binary needing the
            # SDK libc++_shared.so; run it with an explicit LD_LIBRARY_PATH
            # (see _tool_env). Without this the worker's inherited
            # LD_LIBRARY_PATH fails to resolve the runtime and patchelf dies
            # with exit 127.
            subprocess.run(
                [patchelf, "--set-rpath", wayland_libdir, binary],
                check=True, capture_output=True, text=True, timeout=120,
                env=self._tool_env())
            self.output.info(
                f"wayland-utils: embedded RUNPATH -> {wayland_libdir}")
        else:
            self.output.warning(
                "wayland-utils: patchelf not found — RUNPATH not embedded")

        # OHOS self-sign (after patchelf: objcopy/sign must not be followed
        # by another ELF rewrite)
        self._sign_ohos_elf(binary)

    def package_info(self):
        # Command-line tool: nothing to link against, but the executable
        # must be exported on PATH for the consumer test and downstream use.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
