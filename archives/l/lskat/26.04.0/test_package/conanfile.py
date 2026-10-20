#!/usr/bin/env python3
"""Conan test_package for lskat 26.04.0 (application package).

lskat is a KDE Breakout GUI game whose board is a QML scene
(src/qml/*.qml, org.kde.games.core) rendered through a QQuickWidget, built
on KDEGames6. Upstream ships no test suite (R51 inventory: no tests/,
autotests/, enable_testing() or add_test() anywhere in the tarball), so
consumer-side verification is the verification path.

Consumer verification (R34 - must actually exercise the shipped binary):
  1. bin/lskat exists in the package and is executable
  2. bin/lskat --version prints the 26.04.0 version string and exits 0
     (KAboutData handles --version before the GUI is created;
     QT_QPA_PLATFORM=offscreen keeps it headless-safe)
  3. bin/lskat --help prints the command-line interface (proves the Qt
     and KDE runtime link completed)
  4. bin/lskat --author / --license expose the KAboutData metadata
  5. [HarmonyOS-specific, non-assertion] shared-library closure load:
     launches the shipped binary so the OHOS dynamic linker resolves the
     whole DT_NEEDED closure (Qt6 Qml/Quick/QuickWidgets + KF6 + KDEGames6
     and its org.kde.games.core QML module). Judged by process runtime
     behaviour (linker resolution success), not by matching output text.

Runtime environment follows kblocks 26.04.0 / kgoldrunner 26.04.0 precedent:
  - relative DT_NEEDED entries baked into the published KF6 packages
    ("../../bin/libKF6*.so") are patched to SONAME-only via patchelf
    (OHOS resolves relative DT_NEEDED from the symlink path, not realpath)
  - build-machine absolute DT_NEEDED entries get an absolute-NEEDED
    fallback layer
  - /system/lib64 for the compatible libc++_shared.so
  - OHOS binary signature refreshed before execution
"""
import os
import shlex
import shutil
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class LskatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive runtime DT_NEEDED closure of libKDEGames6 (libkdegames
        # does not propagate a runenv into the consumer graph - libkdegames
        # test_package precedent):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("karchive/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("knewstuff/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # openal-soft: libKDEGames6.so links OpenAL (sound engine) - not in
        # the published libkdegames runenv, must be declared explicitly in
        # the consumer graph (kgoldrunner 26.04.0 precedent).
        self.requires("openal-soft/1.25.2")
        # lskat-specific DT_NEEDED not covered above: the QML/Quick stack
        # (qtdeclarative) and the KF6 services used by main.cpp
        # (kcrash/kdbusaddons) plus the libKDEGames6 DNSSD runtime.
        self.requires("qtdeclarative/6.11.1")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("kdnssd/6.29.0")

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

    @staticmethod
    def _elf_needed(path):
        """DT_NEEDED strings of an ELF64 little-endian file."""
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return []
        if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return []
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        needed = []
        dynstr_off = None
        dynstr_size = None
        for index in range(e_shnum):
            off = e_shoff + index * e_shentsize
            if off + e_shentsize > len(data):
                break
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            sh_offset = struct.unpack_from("<Q", data, off + 24)[0]
            sh_size = struct.unpack_from("<Q", data, off + 32)[0]
            if sh_type == 3:
                dynstr_off, dynstr_size = sh_offset, sh_size
            elif sh_type == 6:
                if dynstr_off is None or sh_offset + sh_size > len(data):
                    continue
                for pos in range(sh_offset, sh_offset + sh_size, 16):
                    if pos + 16 > len(data):
                        break
                    d_tag, d_val = struct.unpack_from("<qQ", data, pos)
                    if d_tag == 0:
                        break
                    if d_tag == 1:
                        start = dynstr_off + d_val
                        end = data.find(b"\x00", start)
                        if 0 <= start < len(data) and end > 0:
                            needed.append(
                                data[start:end].decode("utf-8", "replace")
                            )
        return needed

    def _prepare_runtime_links(self):
        """Compatibility symlinks for relative DT_NEEDED entries baked into
        the published KF6 packages (kgoldrunner 26.04.0 precedent)."""
        compat_libs = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                if name.startswith("lib") and (
                    name.endswith(".so") or ".so." in name
                ):
                    compat_libs.setdefault(name, os.path.join(libdir, name))
        for base in (
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, src in compat_libs.items():
                dst = os.path.join(base, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _fix_relative_needed(self):
        """OHOS resolves relative DT_NEEDED entries from the symlink path
        (not the realpath), which breaks the published KF6 convention of
        "../../bin/libKF6*.so". Patch them to SONAME-only so the OHOS
        dynamic linker resolves them via LD_LIBRARY_PATH."""
        import subprocess

        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"

        fixes = 0
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if not os.path.isfile(full):
                    continue
                if not (name.endswith(".so") or ".so." in name):
                    continue
                for entry in self._elf_needed(full):
                    if not entry.startswith("../"):
                        continue
                    soname = os.path.basename(entry)
                    self.output.info(
                        f"patching relative DT_NEEDED {entry} -> {soname} "
                        f"in {name}"
                    )
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", full],
                        check=True,
                    )
                    subprocess.run(
                        [patchelf, "--replace-needed", entry, soname, full],
                        check=True,
                    )
                    subprocess.run(
                        [signer, "sign", "-inFile", full, "-outFile", full,
                         "-selfSign", "1"],
                        check=True,
                    )
                    fixes += 1
        if fixes:
            self.output.info(f"patched {fixes} relative DT_NEEDED entries")

    def _fix_absolute_needed(self):
        """The published KF6/KDEGames6 binaries carry build-machine absolute
        paths in DT_NEEDED. Create the missing paths as symlinks
        (kgoldrunner 26.04.0 precedent)."""
        index = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)

        fixes = 0
        scan_roots = list(self._libdirs())
        pkg = self.dependencies.get("lskat")
        pkg_bin = None
        if pkg and pkg.package_folder:
            pkg_bin = os.path.join(pkg.package_folder, "bin")
            if os.path.isdir(pkg_bin):
                scan_roots.append(pkg_bin)
        for root in scan_roots:
            for name in os.listdir(root):
                full = os.path.join(root, name)
                if not os.path.isfile(full):
                    continue
                is_elfish = name.endswith(".so") or ".so." in name
                if root != pkg_bin and not is_elfish:
                    continue
                for entry in self._elf_needed(full):
                    if not entry.startswith("/") or os.path.exists(entry):
                        continue
                    base = os.path.basename(entry)
                    source = index.get(base)
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

    def _sign(self, path):
        import subprocess

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=False)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["lskat"]
        binary = os.path.join(pkg.package_folder, "bin", "lskat")
        if not os.path.isfile(binary):
            raise ConanException(f"lskat binary not found: {binary}")

        if str(self.settings.os) == "OHOS":
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
            if dep.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    folder = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(folder):
                        plugin_dirs.append(folder)
                    platform_dir = os.path.join(folder, "platforms")
                    if os.path.isdir(platform_dir):
                        platforms.append(platform_dir)

        # QStandardPaths must find the game's own share/lskat tree
        # (qml/main.qml, themes/, levelsets/) and the KDEGames6 QML module.
        data_dirs = []
        for dep in list(self.dependencies.values()):
            if dep and dep.package_folder:
                share = os.path.join(dep.package_folder, "share")
                if os.path.isdir(share):
                    data_dirs.append(share)

        env = Environment()
        env.append("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        for folder in plugin_dirs:
            env.append("QT_PLUGIN_PATH", folder)
        for folder in platforms:
            env.append("QT_QPA_PLATFORM_PLUGIN_PATH", folder)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                qml_dir = os.path.join(dep.package_folder, "qml")
                if os.path.isdir(qml_dir):
                    env.append("QML2_IMPORT_PATH", qml_dir)
        if data_dirs:
            env.append("XDG_DATA_DIRS", os.pathsep.join(data_dirs))
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)
        # test.sh decides whether the OHOS-specific cases (signature/arch gate)
        # apply; the platform comes from settings.os, not from uname guessing.
        env.define("LSKAT_TEST_OS", str(self.settings.os))

        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["LSKAT_TEST_OS"] = str(self.settings.os)
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(platforms)
        if plugin_dirs:
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)
        if data_dirs:
            os.environ["XDG_DATA_DIRS"] = os.pathsep.join(data_dirs)

        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        with env.vars(self).apply():
            self.run(
                f"{shlex.quote(shell)} "
                f"{shlex.quote(os.path.join(self.source_folder, 'test.sh'))} "
                f"{shlex.quote(binary)}",
                cwd=self.build_folder,
            )
        self.output.info("lskat consumer smoke passed")
