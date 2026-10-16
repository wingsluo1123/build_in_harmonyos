#!/usr/bin/env python3
"""Conan test_package for kcharselect 26.04.0 (application package).

kcharselect ships a single Qt6/KF6 Widgets executable (bin/kcharselect) that
wraps the KCharSelect widget inside a KXmlGuiWindow. Upstream registers **no**
autotests (0 tests: no autotests/ or tests/ directory, no
add_test/enable_testing/BUILD_TESTING usage in CMakeLists.txt, no test job in
.kde-ci.yml/.gitlab-ci.yml), so the consumer cases below are the whole
verification surface (R34 — they must actually exercise the shipped binary,
not print a placeholder).

Consumer verification:
  1. bin/kcharselect exists and is executable
  2. kcharselect --version prints the 26.04.0 version string and exits 0
     (KAboutData/QCommandLineParser handle --version before the window is
     built; QT_QPA_PLATFORM=offscreen keeps it headless-safe)
  3. kcharselect --help prints the command-line interface (exercises the
     Qt6 + KF6 runtime link, incl. QCommandLineParser)
  4. kcharselect --author / --license expose the KAboutData metadata
     (KCoreAddons) — the GPL-2.0-or-later notice of this application
  5. [HarmonyOS-specific, non-assertion] shared-library closure load: launches
     the shipped binary through its real application path so the OHOS dynamic
     linker resolves the whole DT_NEEDED closure (KBookmarks/KCrash/KXmlGui
     and their transitive closure included). The published KF6 libraries carry
     relative "../../bin/libX.so" entries which OHOS resolves from the symlink
     path (not realpath) and build-machine absolute entries; the helper
     methods below normalize both. Judged by process runtime behaviour (linker
     resolve success), not by matching any output text — hence a non-assertion
     case that is trivially satisfied on glibc and a real gate on OHOS
     (kcolorchooser/kblocks 26.04.0 precedent).
"""
import os
import shlex
import struct
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment

OHOS_BIN_DIR = "/data/service/hnp/bin"


class KCharSelectTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Runtime DT_NEEDED closure of the shipped executable / of kxmlgui's
        # published artifacts, declared explicitly so the consumer graph and
        # the runtime library search paths are complete (kcolorchooser/kblocks 26.04.0
        # test_package precedent).
        self.requires("qtbase/6.11.1")
        self.requires("kbookmarks/6.18.0")
        self.requires("kcodecs/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")

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
        pkg = self.dependencies["kcharselect"]
        return os.path.join(pkg.package_folder, "bin", "kcharselect")

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
        entries of the published KF6 libraries resolve from the test CWD."""
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
        the same library in the dependency packages (kcolorchooser/kgoldrunner 26.04.0
        precedent; they only exist on the machine that built the KF6
        artifacts)."""
        index = {}
        for full, name in self._iter_elf_libs():
            index.setdefault(name, full)
        scan = [full for full, _name in self._iter_elf_libs()]
        binary = self._package_binary()
        if os.path.isfile(binary):
            scan.append(binary)
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
        # no-op (R34).
        if str(self.settings.os) not in ("Linux", "OHOS", "HarmonyOS"):
            return

        binary = self._package_binary()
        if not os.path.isfile(binary):
            raise ConanException(f"kcharselect binary not found: {binary}")

        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._sign(binary)
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
        # whole list as a single (invalid) plugin directory.
        env = Environment()
        env.define("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        if plugin_dirs:
            env.define("QT_PLUGIN_PATH", os.pathsep.join(plugin_dirs))
        if platforms:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH", os.pathsep.join(platforms)
            )
        # Runtime HOME/XDG directories are kept OUTSIDE the recipe tree:
        # kcharselect's main() calls KIconTheme::initTheme() and
        # KStyleManager::initStyle() before QApplication, which make Qt write
        # <HOME>/.local/state/kcharselectstaterc. Pointing HOME at
        # self.build_folder (== this test_package/ directory for a
        # test_type="explicit" package) would leave that Qt state file inside
        # the archive tree (junk/JC gates).
        runtime_home = os.path.join(
            os.environ.get("TMPDIR", tempfile.gettempdir()),
            "kcharselect-test-runtime",
        )
        os.makedirs(runtime_home, exist_ok=True)
        env.define("HOME", runtime_home)
        env.define("XDG_RUNTIME_DIR", runtime_home)
        env.define("XDG_STATE_HOME", os.path.join(runtime_home, "state"))
        env.define("XDG_CONFIG_HOME", os.path.join(runtime_home, "config"))
        env.define("XDG_DATA_HOME", os.path.join(runtime_home, "data"))
        env.define("XDG_CACHE_HOME", os.path.join(runtime_home, "cache"))

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
        self.output.info("kcharselect consumer smoke passed")
