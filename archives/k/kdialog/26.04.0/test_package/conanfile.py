#!/usr/bin/env python3
"""Conan test_package for kdialog 26.04.0 (application package).

kdialog ships two executables: bin/kdialog (the Qt6/KF6 Widgets dialog shell
tool) and bin/kdialog_progress_helper (the D-Bus service that carries the
--progressbar dialogs, generated via qt_add_dbus_adaptor). Upstream
registers **no** tests (0 tests: tests/ ships three interactive demo shell
scripts only, no CMake file uses add_test/enable_testing/BUILD_TESTING/
ecm_add_test/ctest, and .kde-ci.yml/.gitlab-ci.yml declare no test target —
full evidence in test_package/MANIFEST.yml), so the consumer cases below are
the whole verification surface (R34 — they must actually exercise the
shipped binaries, not print a placeholder).

Consumer verification:
  1. bin/kdialog and bin/kdialog_progress_helper exist and are executable
  2. kdialog --version prints the 26.04 version string and exits 0
     (KAboutData/QCommandLineParser handle --version before any dialog
     logic runs)
  3. kdialog --help exits 0 with the dialog-option surface intact
     (--passivepopup and --progressbar are both registered; neither branch
     is driven end to end on purpose — the passivepopup branch hangs
     without a session bus and the progressbar branch needs the helper on
     PATH plus a D-Bus client, see the recipe docstring)
  4. kdialog --author / --license expose the KAboutData metadata
     (KCoreAddons; author David Faure, GPL license text)
  5. an unknown option fails loudly: non-zero exit and QCommandLineParser's
     "Unknown option" diagnostic instead of a silent success
  6. [HarmonyOS-specific] (a) kdialog --msgbox enters a real modal event
     loop (KMessageBox::createKMessageBox + QDialog::exec in kdialog.cpp):
     the process must stay alive past a 3 s grace period (then it is
     killed), which also gates the binary's full DT_NEEDED closure;
     (b) the packaged kdialog_progress_helper is launched directly and
     must resolve its complete DT_NEEDED closure (bounded wait, judged by
     the absence of linker-resolution error patterns — not by matching any
     output text). Both cases trivially pass on glibc and are the real
     gate on OHOS.

The published KF6 libraries carry relative "../../bin/libX.so" entries
(OHOS resolves them from the symlink path, not the realpath) and
build-machine absolute entries; the helper methods below normalize both
(kcolorchooser 26.04.0 / kblocks 26.04.0 precedent), and the packaged
binaries themselves were already sanitized to basename-only DT_NEEDED in
the recipe's package() step.
"""
import os
import shlex
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment

OHOS_BIN_DIR = "/data/service/hnp/bin"


class KDialogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Mirror the kdialog 26.04.0 dependency matrix (same list as the
        # recipe): the consumer graph and the runtime library search paths
        # must be complete without relying on transitive activation
        # (kcolorchooser 26.04.0 / kcron 26.04.1 precedent).
        self.requires("qtbase/6.11.1.1", override=True)
        self.requires("qtsvg/6.11.1")
        self.requires("ktextwidgets/6.26.0")
        self.requires("knotifications/6.26.0")
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("kiconthemes/6.26.0")
        self.requires("kwindowsystem/6.26.0")
        self.requires("kio/6.26.0")
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kdbusaddons/6.18.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kcrash/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcompletion/6.26.0.1")
        self.requires("sonnet/6.26.0")
        self.requires("kservice/6.26.0")
        self.requires("karchive/6.26.0", override=True)
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("expat/2.8.2.1", override=True)
        self.requires("libxml2/2.15.3")

    # ── runtime helpers ────────────────────────────────────────────────

    def _libdirs(self):
        dirs = []
        seen = set()
        for dep in self.dependencies.values():
            if not (dep and dep.package_folder):
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if libdir not in seen and os.path.isdir(libdir):
                seen.add(libdir)
                dirs.append(libdir)
        return dirs

    def _package_binary(self):
        pkg = self.dependencies["kdialog"]
        return os.path.join(pkg.package_folder, "bin", "kdialog")

    def _package_helper(self):
        pkg = self.dependencies["kdialog"]
        return os.path.join(
            pkg.package_folder, "bin", "kdialog_progress_helper"
        )

    @staticmethod
    def _ohos_tool(name):
        candidate = os.path.join(OHOS_BIN_DIR, name)
        return candidate if os.path.isfile(candidate) else name

    @staticmethod
    def _elf_needed(path):
        """Return the DT_NEEDED strings of a 64-bit little/big-endian ELF."""
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return []
        if len(data) < 0x40 or data[:4] != b"\x7fELF" or data[4] != 2:
            return []
        little = data[5] == 1
        fmt_q = "<Q" if little else ">Q"
        fmt_h = "<H" if little else ">H"
        fmt_i = "<I" if little else ">I"
        fmt_dyn = "<qQ" if little else ">qQ"
        e_shoff = struct.unpack_from(fmt_q, data, 0x28)[0]
        e_shentsize = struct.unpack_from(fmt_h, data, 0x3A)[0]
        e_shnum = struct.unpack_from(fmt_h, data, 0x3C)[0]
        if not e_shoff or not e_shentsize:
            return []
        sections = []
        for index in range(e_shnum):
            off = e_shoff + index * e_shentsize
            if off + e_shentsize > len(data):
                break
            sections.append(
                (
                    struct.unpack_from(fmt_i, data, off + 4)[0],   # sh_type
                    struct.unpack_from(fmt_q, data, off + 16)[0],  # sh_addr
                    struct.unpack_from(fmt_q, data, off + 24)[0],  # sh_offset
                    struct.unpack_from(fmt_q, data, off + 32)[0],  # sh_size
                )
            )
        needed = []
        for sh_type, _sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or not sh_size:  # SHT_DYNAMIC
                continue
            strtab_addr = None
            entries = []
            pos = sh_offset
            end = min(sh_offset + sh_size, len(data))
            while pos + 16 <= end:
                tag, value = struct.unpack_from(fmt_dyn, data, pos)
                if tag == 0:
                    break
                if tag == 5:    # DT_STRTAB
                    strtab_addr = value
                elif tag == 1:  # DT_NEEDED
                    entries.append(value)
                pos += 16
            if strtab_addr is None or not entries:
                continue
            for _t, sh_addr, sh_off, sh_len in sections:
                if sh_addr <= strtab_addr < sh_addr + sh_len:
                    base = sh_off + (strtab_addr - sh_addr)
                    limit = sh_len - (strtab_addr - sh_addr)
                    break
            else:
                continue
            for rel in entries:
                if rel >= limit:
                    continue
                start = base + rel
                stop = data.find(b"\x00", start, base + limit)
                if stop < 0:
                    continue
                needed.append(data[start:stop].decode("utf-8", "replace"))
        return needed

    def _iter_elf_libs(self):
        for libdir in self._libdirs():
            for name in sorted(os.listdir(libdir)):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    yield full, name

    def _sign(self, path):
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def _prepare_runtime_links(self):
        """Symlink every dependency library into <build>/bin and
        <build>/../../bin so the relative "../../bin/libX.so" DT_NEEDED
        entries of the published KF6 libraries resolve from the test CWD
        (which stays the build folder)."""
        compat = {}
        for full, name in self._iter_elf_libs():
            compat.setdefault(name, full)
        for base in (
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, source in compat.items():
                link = os.path.join(base, name)
                if not os.path.lexists(link):
                    try:
                        os.symlink(source, link)
                    except OSError as error:
                        self.output.warning(f"link farm skip {name}: {error}")

    def _fix_relative_needed(self):
        """Rewrite relative DT_NEEDED entries of the published KF6 libraries
        to SONAME-only (patchelf --replace-needed) and re-sign afterwards.
        OHOS resolves such entries from the symlink path, not the realpath,
        which breaks the multi-package KF6 layout."""
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        patchelf = self._ohos_tool("patchelf")
        fixes = 0
        for full, name in self._iter_elf_libs():
            for entry in self._elf_needed(full):
                if not entry.startswith("../") and not entry.startswith("./"):
                    continue
                soname = os.path.basename(entry)
                self.output.info(
                    f"patching relative DT_NEEDED {entry} -> {soname} in {name}"
                )
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", full],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                subprocess.run(
                    [patchelf, "--replace-needed", entry, soname, full],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                subprocess.run(
                    [signer, "sign", "-inFile", full, "-outFile", full,
                     "-selfSign", "1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                fixes += 1
        if fixes:
            self.output.info(f"patched {fixes} relative DT_NEEDED entries")

    def _fix_absolute_needed(self):
        """Create the build-machine absolute DT_NEEDED paths as symlinks to
        the same library in the dependency packages (kgoldrunner 26.04.0
        precedent; they only exist on the machine that built the KF6
        artifacts). Both packaged executables are scanned as well; their
        own entries were already sanitized in the recipe's package()."""
        index = {}
        for full, name in self._iter_elf_libs():
            index.setdefault(name, full)
        scan = [full for full, _name in self._iter_elf_libs()]
        for candidate in (self._package_binary(), self._package_helper()):
            if os.path.isfile(candidate):
                scan.append(candidate)
        fixes = 0
        for full in scan:
            for entry in self._elf_needed(full):
                if not entry.startswith("/") or os.path.exists(entry):
                    continue
                source = index.get(os.path.basename(entry))
                if not source:
                    continue
                try:
                    os.makedirs(os.path.dirname(entry), exist_ok=True)
                    if not os.path.lexists(entry):
                        os.symlink(source, entry)
                        fixes += 1
                except OSError as error:
                    self.output.warning(
                        f"cannot create NEEDED fallback {entry}: {error}"
                    )
        if fixes:
            self.output.info(f"created {fixes} absolute-NEEDED fallback symlinks")

    # ── consumer test ──────────────────────────────────────────────────

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        # Keep the platform guard in sync with the recipe idiom
        # (str(self.settings.os) + ("OHOS", "HarmonyOS")): a bare
        # ``not in ("Linux", "OHOS")`` would silently skip the whole
        # consumer test under a HarmonyOS setting and turn it into a
        # no-op (R34). (R1 整改 2026-10-17 离线检视 #3; kcharselect
        # 26.04.0 precedent.)
        if str(self.settings.os) not in ("Linux", "OHOS", "HarmonyOS"):
            return

        binary = self._package_binary()
        helper = self._package_helper()
        if not os.path.isfile(binary):
            raise ConanException(f"kdialog binary not found: {binary}")
        if not os.path.isfile(helper):
            raise ConanException(
                f"kdialog_progress_helper not found: {helper}"
            )

        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._sign(binary)
            self._sign(helper)
            self._prepare_runtime_links()
            self._fix_relative_needed()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

        plugin_dirs = []
        platforms = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for rel in ("plugins", os.path.join("lib", "plugins")):
                directory = os.path.join(dep.package_folder, rel)
                if not os.path.isdir(directory):
                    continue
                if directory not in plugin_dirs:
                    plugin_dirs.append(directory)
                platform_dir = os.path.join(directory, "platforms")
                if os.path.isdir(platform_dir) and platform_dir not in platforms:
                    platforms.append(platform_dir)

        # NOTE: define() with an explicitly os.pathsep-joined value — Conan's
        # Environment.append() joins with a space, which makes Qt treat the
        # whole list as a single (invalid) plugin directory (kcolorchooser
        # 26.04.0 finding).
        env = Environment()
        env.define("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        if plugin_dirs:
            env.define("QT_PLUGIN_PATH", os.pathsep.join(plugin_dirs))
        if platforms:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH", os.pathsep.join(platforms)
            )
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)

        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(platforms)
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)

        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        with env.vars(self).apply():
            self.run(
                f"{shlex.quote(shell)} "
                f"{shlex.quote(os.path.join(self.source_folder, 'test.sh'))} "
                f"{shlex.quote(binary)}",
                cwd=self.build_folder,
            )
        self.output.info("kdialog consumer suite passed")
