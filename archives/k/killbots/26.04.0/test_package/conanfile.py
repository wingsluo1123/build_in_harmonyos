#!/usr/bin/env python3
"""Conan test_package for killbots 26.04.0 (application package).

killbots is a Qt6/KF6 GUI game (QGraphics application). Upstream registers
no test suite (enginetest is gated behind BUILD_TESTING and requires KDE CI
infrastructure), so the consumer verification is a runtime smoke test
(klickety 26.04.0 / kfourinline 26.04.0 pattern):

  1. killbots binary exists in the package bin/ directory
  2. killbots --version prints the 26.04.0 version string and exits 0
     (QCommandLineParser/KAboutData handle --version before the GUI main
     window is created; QT_QPA_PLATFORM=offscreen keeps it headless-safe)

OHOS-specific consumer tests (rule12, 鸿蒙特有非断言):
  3. Shared library closure loading: use dlopen to load libQt6Core.so
     from the package's Qt dependency, verifying the consumer can resolve
     and load the core Qt shared library at runtime (non-assertion: verifies
     linkage sanity, not a value assertion).
  4. Binary signature check: the shipped killbots executable has a valid
     OHOS .codesign section (signed by binary-sign-tool during test
     preparation).

Runtime environment (klickety 26.04.0 precedent):
  - relative DT_NEEDED entries baked into the published KF6 packages
    ("../../bin/libKF6*.so") are resolved through compatibility symlinks
  - build-machine absolute DT_NEEDED entries get an absolute-NEEDED
    fallback layer
  - /system/lib64 for the compatible libc++_shared.so
  - the OHOS binary signature is refreshed before execution
The assertions live in test.sh (POSIX sh).
"""
import os
import shlex
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class KillbotsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive runtime DT_NEEDED (libkdegames requires set)
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("karchive/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0.1")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # libkdegames transitive runtime deps
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")
        self.requires("libiconv/1.17")

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

    def _prepare_runtime_links(self):
        """Compatibility symlinks for relative DT_NEEDED entries."""
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

    def _fix_absolute_needed(self):
        """Create symlinks for absolute DT_NEEDED entries."""
        def elf_needed(path):
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != b"\x7fELF" or data[4] != 2:
                return []
            is_le = data[5] == 1
            e_shoff = struct.unpack_from("<Q" if is_le else ">Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3A)[0]
            e_shnum = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3C)[0]
            needed = []
            dynstr = None
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                if off + e_shentsize > len(data):
                    break
                sh_type = struct.unpack_from(
                    "<I" if is_le else ">I", data, off + 4)[0]
                if sh_type == 3:
                    dynstr = off
                elif sh_type == 6:
                    d_off = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, off + 0x18)[0]
                    d_size = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, off + 0x20)[0]
                    if dynstr is None:
                        continue
                    str_off = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, dynstr + 0x18)[0]
                    p = d_off
                    end = d_off + d_size
                    while p + 16 <= end and p + 16 <= len(data):
                        tag, val = struct.unpack_from(
                            "<QQ" if is_le else ">QQ", data, p)
                        if tag == 0:
                            break
                        if tag == 1:
                            s = str_off + val
                            e = data.index(b"\x00", s)
                            needed.append(data[s:e].decode("utf-8", "replace"))
                        p += 16
            return needed

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
        pkg = self.dependencies.get("killbots")
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
                for entry in elf_needed(full):
                    if not entry.startswith("/"):
                        continue
                    if os.path.exists(entry):
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
                    except OSError as e:
                        self.output.warning(
                            f"cannot create NEEDED fallback {entry}: {e}")
        if fixes:
            self.output.info(
                f"created {fixes} absolute-NEEDED compatibility symlinks")

    def _sign(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)

    def _ohos_shared_library_closure_check(self):
        """OHOS-specific: verify core Qt shared library loads via dlopen.

        Non-assertion test (rule12): confirms the consumer can resolve and
        load libQt6Core.so from the package's Qt dependency, validating
        runtime linkage sanity without asserting a specific value.
        """
        qtbase = self.dependencies.get("qtbase")
        if not (qtbase and qtbase.package_folder):
            self.output.warning("qtbase package not available, skipping closure check")
            return
        qt_lib = os.path.join(qtbase.package_folder, "lib")
        libqtcore = None
        for name in os.listdir(qt_lib):
            if name == "libQt6Core.so" or name.startswith("libQt6Core.so."):
                libqtcore = os.path.join(qt_lib, name)
                break
        if not libqtcore:
            self.output.warning("libQt6Core.so not found, skipping closure check")
            return

        libdirs = self._libdirs()
        ld_path = os.pathsep.join(["/system/lib64"] + libdirs)

        probe = os.path.join(self.build_folder, "closure_probe")
        probe_src = (
            "#include <dlfcn.h>\n"
            "#include <stdio.h>\n"
            "int main() {\n"
            f'  void* h = dlopen("{libqtcore}", RTLD_NOW | RTLD_LOCAL);\n'
            "  if (!h) { printf(\"FAIL: %s\\n\", dlerror()); return 1; }\n"
            "  printf(\"OK: loaded %p\\n\", h);\n"
            "  dlclose(h);\n"
            "  return 0;\n"
            "}\n"
        )
        probe_c = os.path.join(self.build_folder, "closure_probe.c")
        with open(probe_c, "w") as f:
            f.write(probe_src)
        clang = "/data/service/hnp/bin/clang"
        ld_flags = ["-rdynamic"]
        for d in libdirs:
            ld_flags.extend(["-L", d])
        subprocess.run(
            [clang, "-o", probe, probe_c] + ld_flags,
            check=True, env={**os.environ, "LD_LIBRARY_PATH": ld_path}
        )
        # dlopen probe must run with LD_LIBRARY_PATH pointing to Qt libs
        result = subprocess.run(
            [probe],
            capture_output=True, text=True,
            env={**os.environ, "LD_LIBRARY_PATH": ld_path}
        )
        self.output.info(f"closure probe stdout: {result.stdout.strip()}")
        if result.returncode != 0:
            raise ConanException(
                f"shared library closure check failed: {result.stderr.strip()}"
            )
        self.output.info("✅ OHOS shared library closure check passed")

    def _ohos_signature_check(self, path):
        """OHOS-specific: verify binary has valid .codesign section."""
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            raise ConanException(f"cannot read binary for signature check: {e}")
        if data[:4] != b"\x7fELF":
            raise ConanException("not an ELF binary")
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        e_shstrndx = struct.unpack_from("<H", data, 0x3E)[0]
        shstrtab_off = e_shoff + e_shstrndx * e_shentsize
        shstrtab = struct.unpack_from("<Q", data, shstrtab_off + 0x18)[0]
        shstrtab_sz = struct.unpack_from("<Q", data, shstrtab_off + 0x20)[0]
        strtab = data[shstrtab:shstrtab + shstrtab_sz]
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            name_idx = struct.unpack_from("<I", data, off)[0]
            end = strtab.index(b"\x00", name_idx)
            name = strtab[name_idx:end].decode("utf-8", "replace")
            if name == ".codesign":
                self.output.info(f"✅ OHOS .codesign section present in {path}")
                return
        raise ConanException(f"OHOS .codesign section missing from {path}")

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["killbots"]
        gui = os.path.join(pkg.package_folder, "bin", "killbots")
        if not os.path.isfile(gui):
            raise ConanException(f"killbots binary not found: {gui}")

        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        if str(self.settings.os) == "OHOS":
            self._sign(gui)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        # OHOS-specific consumer tests (rule12): non-assertion checks
        self._ohos_shared_library_closure_check()
        self._ohos_signature_check(gui)

        lib_dirs = self._libdirs()
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

        plugin_dirs = []
        platforms = []
        for p in self.dependencies.values():
            if p.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    d = os.path.join(p.package_folder, rel)
                    if os.path.isdir(d):
                        plugin_dirs.append(d)
                    pd = os.path.join(d, "platforms")
                    if os.path.isdir(pd):
                        platforms.append(pd)

        env = Environment()
        env.append("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        for d in plugin_dirs:
            env.append("QT_PLUGIN_PATH", d)
        for d in platforms:
            env.append("QT_QPA_PLATFORM_PLUGIN_PATH", d)
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)

        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(
                platforms
            )
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)

        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        with env.vars(self).apply():
            self.run(
                f'{shlex.quote(shell)} '
                f'{shlex.quote(os.path.join(self.source_folder, "test.sh"))} '
                f'{shlex.quote(gui)}',
                cwd=self.build_folder,
            )
        self.output.info("killbots runtime smoke passed")
