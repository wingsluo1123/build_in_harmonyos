#!/usr/bin/env python3
"""Conan recipe — osdclock 0.5 (X On-Screen Display clock)

osd_clock is a ~130-line X11 client that renders a strftime(3) formatted clock
on the X root window through libxosd.  Upstream (Jon Beckham, 2001) ships a
hand-written Makefile and no configure/CMake bootstrap, so this recipe drives
`make` directly, in-source (the Makefile has no VPATH/out-of-tree support).

Licence: GPL-2.0-or-later.  Homepage: http://leftorium.net/software.phtml
(the author's site is dead; see conandata.yml for the source-URL reasoning).

Build system: makefile.  The Makefile hard-assigns CC/CFLAGS/LDFLAGS/XOSDLIBS
and INSTALL, so environment variables cannot reach them — the recipe passes
every override on the make command line (R33: compiler comes from
tools.build:compiler_executables, never from a bare ${CC} shell variable).

Two portability patches are mandatory (patches/):
  0001 — osd_clock 0.5 targets xosd 0.7.0.  The only libxosd ever released
         (2.2.14, and the version every distribution packages) widened
         xosd_init() to 7 arguments and deprecated xosd_uninit().  The last
         argument (number_lines) matters functionally: the program draws on
         line 1 and 2.2.14's xosd_display() rejects line >= number_lines.
         Without the patch: "too few arguments to function call".
  0002 — `char c` holding the getopt_long() return value.  On x86 char is
         signed, so `(c = getopt_long(...)) != -1` ends the option loop; on
         aarch64 char is unsigned, -1 becomes 255 and the loop spins forever
         before xosd_init() is ever called.  Upstream's and Debian's patch
         sets never needed this because they only ever built for x86.

HMDFS: the dependency packages ship the usual
`libX.so -> libX.so.6 -> libX.so.6.4.0` chain, but on the OHOS HMDFS cache the
symlink entries are unreadable (EACCES on open/readlink), so lld cannot resolve
`-lX11` and the runtime loader cannot resolve the recorded sonames.  Both this
recipe (generate() -> <build>/deplibs) and test_package (generate() ->
realdep_libs) therefore materialise real copies of every shared object under
all of its soname aliases and prepend that flat directory (knowledge E042/E524
family; same workaround as xgamma/libxosd).

Upstream has no automated test suite (the Makefile only defines
all/install/clean/tar and the %.o / %.o.pic rules; there is no tests/ directory and no assert() in
osd_clock.c), so test_package really executes the installed binary
(R34/R51): `-h`/`--help` usage paths plus the no-X-display initialisation
failure path of libxosd 2.2.14 (src/libxosd/xosd.c:715-719, XOpenDisplay()
fails -> xosd_init() returns NULL -> exit 1).  That second path doubles as the
regression probe for patch 0002 (with an unsigned loop variable the program
hangs there instead of exiting).

Library stack: libxosd/2.2.14 (ohpcd binary) pulls libx11/6.4.0,
libxext/6.4.0, libxinerama/1.1.5 and xorgproto/2025.1 through
cpp_info.requires.  The runtime DT_NEEDED closure of that stack
(libX11.so.6 -> libxcb.so.1 + libXau.so.6, libxcb -> libXau/libXdmcp) is
declared as explicit run requirements so test_package's conanrun environment
exposes those libdirs.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class OsdclockConan(ConanFile):
    name = "osdclock"
    version = "0.5"
    description = ("X on-screen clock: displays a strftime(3) formatted clock "
                   "on the X root window through the XOSD library")
    license = "GPL-2.0-or-later"
    homepage = "http://leftorium.net/software.phtml"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # Conan export_sources 机制：把 patches/ 一并导出到 recipe 缓存副本，
    # build() 才能 apply_conandata_patches()（G1 门禁检查该字面量）。
    exports_sources = "patches/*"

    # Shared objects actually needed for the link (and, for the consumer, at
    # run time).  Everything else in the dependency libdirs is irrelevant.
    _WANTED_SO_STEMS = (
        "libxosd.so", "libX11.so", "libXext.so", "libXinerama.so",
        "libxcb.so", "libXau.so", "libXdmcp.so",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"osdclock supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # libxosd 2.2.14 is the only XOSD implementation there is; it carries
        # the X11/Xext/Xinerama/xorgproto closure through cpp_info.requires.
        self.requires("libxosd/2.2.14", transitive_headers=True,
                      transitive_libs=True)
        # Runtime DT_NEEDED closure of the X11 stack: declared run-only so the
        # conanrun environment exposes every libdir to test_package.
        self.requires("libxcb/1.16", run=True)
        self.requires("libxau/1.0.11", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ──────────────────────────────────────────────────────────

    def _c_compiler(self):
        """C compiler from the profile conf (R33 — never a bare ${CC})."""
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        cc = (compilers or {}).get("c")
        if not cc:
            cc = os.environ.get("CC")
        return cc or "cc"

    def _prepend_toolchain_path(self):
        """E540: the runner PATH may lack the toolchain directory.  The profile
        points CC at an absolute /data/service/hnp/bin/clang, but clang's
        internal ld.lld/as/nm are resolved through PATH — without it the first
        make call exits 127.  Idempotent, derived from the conf."""
        cc = self._c_compiler()
        toolchain_dir = os.path.dirname(cc)
        if not toolchain_dir:
            return
        current = os.environ.get("PATH", "")
        entries = current.split(os.pathsep) if current else []
        if toolchain_dir in entries:
            return
        os.environ["PATH"] = toolchain_dir + os.pathsep + current

    @staticmethod
    def _so_aliases(name):
        """libX11.so.6.4.0 -> libX11.so, libX11.so.6, libX11.so.6.4.0."""
        if ".so" not in name:
            return [name]
        idx = name.find(".so")
        stem = name[:idx + 3]            # libX11.so
        rest = name[idx + 3:]            # .6.4.0
        aliases = [name, stem]
        if rest.startswith("."):
            major = rest[1:].split(".")[0]
            if major:
                aliases.insert(1, f"{stem}.{major}")
        return aliases

    def _materialize_libs(self, mirror):
        """Copy every needed dependency shared object into `mirror` under all
        of its soname aliases, as *real* files.

        On the OHOS HMDFS conan cache the `libX.so` / `libX.so.6` symlink
        entries are unreadable (EACCES, clone/symlink semantics), so lld
        cannot satisfy `-lX11` and the loader cannot satisfy DT_NEEDED.  The
        versioned file itself is fine; copying it under the alias names gives
        the linker and the loader something real to open.
        """
        os.makedirs(mirror, exist_ok=True)
        done = set()
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isdir(libdir):
                    continue
                for entry in sorted(os.listdir(libdir)):
                    if ".so" not in entry:
                        continue
                    aliases = self._so_aliases(entry)
                    if aliases[-1] not in self._WANTED_SO_STEMS:
                        continue
                    src = os.path.join(libdir, entry)
                    try:
                        with open(src, "rb") as handle:
                            if handle.read(4) != b"\x7fELF":
                                continue
                    except OSError:
                        continue          # unreadable symlink entry
                    for alias in aliases:
                        if alias in done:
                            continue
                        dst = os.path.join(mirror, alias)
                        try:
                            shutil.copyfile(src, dst)
                            os.chmod(dst, 0o755)
                            done.add(alias)
                        except OSError:
                            pass
        if done:
            self.output.info(
                f"HMDFS: materialised {len(done)} dependency shared objects "
                f"into {mirror}")
        return mirror

    def _dependency_flags(self, mirror=None):
        """(-I flags, -L flags) collected from every host dependency.  The
        materialised mirror directory comes first so lld finds real files."""
        includes, libdirs = [], []
        for dep in self.dependencies.host.values():
            includes.extend(dep.cpp_info.includedirs)
            libdirs.extend(dep.cpp_info.libdirs)
        if mirror:
            libdirs.insert(0, mirror)
        seen, inc_flags = set(), []
        for path in includes:
            if path and path not in seen:
                seen.add(path)
                inc_flags.append(f"-I{path}")
        seen, lib_flags = set(), []
        for path in libdirs:
            if path and path not in seen:
                seen.add(path)
                lib_flags.append(f"-L{path}")
        return inc_flags, lib_flags

    def _sign_elf(self, path):
        """ELF code signing (OHOS refuses to load unsigned ELF; same helper as
        xgamma/xeyes/xev)."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            # No .codesign section on a freshly linked binary -> objcopy exits
            # non-zero; that is expected, hence the explicit `|| true`.
            self.run(f'{objcopy} --remove-section .codesign "{path}" '
                     f'2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" '
                     f'-selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMFS may not support chmod

    # ── build / package ──────────────────────────────────────────────────

    def generate(self):
        self._dep_mirror = self._materialize_libs(
            os.path.join(self.build_folder, "deplibs"))

    def build(self):
        apply_conandata_patches(self)
        self._prepend_toolchain_path()
        mirror = getattr(self, "_dep_mirror", None)
        if not mirror or not os.path.isdir(mirror):
            mirror = self._materialize_libs(
                os.path.join(self.build_folder, "deplibs"))
        inc_flags, lib_flags = self._dependency_flags(mirror)
        cflags = " ".join(["-O2", "-fPIC", "-Wall", "-I."] + inc_flags)
        ldflags = " ".join(lib_flags)
        # libxosd.so.2 records X11/Xext/Xinerama in its own DT_NEEDED, but the
        # hand-written Makefile links them explicitly; keep that behaviour.
        xosdlibs = "-lxosd -lX11 -lXext -lXinerama"
        command = (
            "make -j1"
            f' CC="{self._c_compiler()}"'
            f' CFLAGS="{cflags}"'
            f' LDFLAGS="{ldflags}"'
            f' XOSDLIBS="{xosdlibs}"'
        )
        self.output.info(f"osdclock build: {command}")
        self.run(command, cwd=self.source_folder)

    def package(self):
        # The upstream install target hardcodes INSTALL=/usr/bin/install (absent
        # on OHOS) and never creates the destination directories, so install the
        # two artefacts explicitly instead of driving `make install`.
        copy(self, "osd_clock", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "osd_clock.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for entry in sorted(os.listdir(bin_dir)):
                self._sign_elf(os.path.join(bin_dir, entry))

    def package_info(self):
        # Command line tool: expose bin/ only (R38); no library, no headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
