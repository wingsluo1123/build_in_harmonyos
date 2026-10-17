#!/usr/bin/env python3
"""Conan test_package for skladnik 26.04.2.

Consumer-side verification for an application package whose upstream
registers no test suite (N=0). The compiled test binary
(skladnik_consumer_test) asserts three groups of checks against the
installed package; see test_package/MANIFEST.yml for the full list and
the counting scheme.

This file only prepares the OHOS runtime environment the packaged game
needs before handing over to that binary:

* every dependency lib dir is collected onto LD_LIBRARY_PATH (the KF6 and
  Qt packages are built with cmake_find_mode=none and no usable RPATH);
* compatibility symlinks are created for the relative DT_NEEDED entries
  baked into the published KF6 packages (audiocd 26.04.3 / libkcddb /
  kgoldrunner 26.04.0 precedent);
* missing absolute DT_NEEDED paths recorded in the published KF6 binaries
  are materialised as symlinks to the real libraries - the OHOS musl
  loader resolves path-form NEEDED entries literally, with no
  LD_LIBRARY_PATH fallback (kgoldrunner 26.04.0 precedent);
* both the packaged game and this test's own binary are checked for a
  valid .codesign section, renewing it when absent - OHOS refuses to
  exec-map an ELF without one, and the failure surfaces as an unrelated
  EACCES that reads like a missing library (wmload 0.9.7 precedent).
"""
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class SkladnikTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        # libKDEGames6.so NEEDs libopenal.so.1 (openal-soft is a transitive
        # requirement of libkdegames); require it explicitly so its lib dir
        # lands in the runtime environment. Pinned to libkdegames' version.
        self.requires("openal-soft/1.25.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase uses cmake_find_mode=none: write conan_cmakedeps_paths
        # manually (kgoldrunner 26.04.0 precedent).
        lines = []
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        paths_file = os.path.join(self.generators_folder,
                                  "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        with self._lib_env().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _lib_env(self):
        build_env = Environment()
        for libdir in self._collect_libdirs():
            build_env.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _collect_libdirs(self):
        """Every package folder reachable in the test graph (direct and
        transitive) that carries a lib/ directory."""
        libdirs = []
        seen = set()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            lib = os.path.join(dep.package_folder, "lib")
            if lib not in seen and os.path.isdir(lib):
                seen.add(lib)
                libdirs.append(lib)
        return libdirs

    def _prepare_runtime_links(self):
        """Compatibility symlinks for the relative DT_NEEDED entries baked
        into the published KF6 packages (kconfig's libKF6ConfigGui.so needs
        '../../bin/libKF6ConfigCore.so' relative to the process cwd -
        audiocd 26.04.3 / libkcddb / kgoldrunner 26.04.0 precedent)."""
        compat_libs = {}
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if name.endswith(".so") or ".so." in name:
                    compat_libs[name] = os.path.join(libdir, name)
        exe_dir = os.path.dirname(
            os.path.join(self.build_folder, self.cpp.build.bindirs[0])
        )
        for base in (
            os.path.normpath(
                os.path.join(exe_dir, os.pardir, os.pardir, "bin")),
            os.path.normpath(os.path.join(exe_dir, os.pardir, "bin")),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, src in compat_libs.items():
                dst = os.path.join(base, name)
                if name.startswith("libKF6") and not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _fix_absolute_needed(self):
        """Materialise missing absolute DT_NEEDED paths recorded in the
        published KF6 binaries as symlinks to the real libraries. The OHOS
        musl loader resolves path-form NEEDED entries literally with no
        LD_LIBRARY_PATH fallback, and on a fresh worker those build-machine
        directories may not exist (kgoldrunner 26.04.0 precedent)."""
        import struct

        elf_magic = bytes([0x7F]) + b"ELF"

        def elf_needed(path):
            """Minimal ELF64 DT_NEEDED extractor (no readelf dependency)."""
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != elf_magic or data[4] != 2:
                return []
            fmt = "<" if data[5] == 1 else ">"
            e_shoff = struct.unpack_from(fmt + "Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from(fmt + "H", data, 0x3A)[0]
            e_shnum = struct.unpack_from(fmt + "H", data, 0x3C)[0]
            needed = []
            dynstr = None
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                if off + e_shentsize > len(data):
                    break
                sh_type = struct.unpack_from(fmt + "I", data, off + 4)[0]
                if sh_type == 3:  # SHT_STRTAB
                    dynstr = off
                elif sh_type == 6:  # SHT_DYNAMIC
                    d_off = struct.unpack_from(fmt + "Q", data, off + 0x18)[0]
                    d_size = struct.unpack_from(fmt + "Q", data, off + 0x20)[0]
                    if dynstr is None:
                        continue
                    str_off = struct.unpack_from(
                        fmt + "Q", data, dynstr + 0x18)[0]
                    p = d_off
                    end = d_off + d_size
                    while p + 16 <= end and p + 16 <= len(data):
                        tag, val = struct.unpack_from(fmt + "QQ", data, p)
                        if tag == 0:
                            break
                        if tag == 1:  # DT_NEEDED
                            s = str_off + val
                            e = data.index(0, s)
                            needed.append(
                                data[s:e].decode("utf-8", "replace"))
                        p += 16
            return needed

        index = {}
        libdirs = self._collect_libdirs()
        for libdir in libdirs:
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)

        fixes = 0
        for libdir in libdirs:
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if not os.path.isfile(full) or not (
                    name.endswith(".so") or ".so." in name
                ):
                    continue
                for entry in elf_needed(full):
                    if not entry.startswith("/"):
                        continue
                    if os.path.exists(entry):
                        continue
                    source = index.get(os.path.basename(entry))
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

    def _tool(self, name):
        found = shutil.which(name) or "/data/service/hnp/bin/" + name
        if not os.path.isfile(found):
            raise ConanException("required OHOS tool is missing: " + name)
        return found

    @staticmethod
    def _readelf(readelf, args):
        try:
            return subprocess.run(
                [readelf] + args, check=True, capture_output=True,
                text=True, timeout=60,
            ).stdout
        except (subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as error:
            raise ConanException(
                "readelf " + repr(args) + " failed: " + str(error)) from error

    def _ensure_codesign(self, path):
        """Verify the ELF carries exactly one .codesign section, renewing it
        when absent (wmload 0.9.7 precedent). Zero sections means OHOS will
        refuse to exec it, surfacing as an unrelated EACCES that reads like
        a missing library."""
        readelf = self._tool("llvm-readelf")
        existing = self._readelf(readelf, ["-SW", path]).count(".codesign")
        if existing not in (0, 1):
            raise ConanException(
                "invalid .codesign count on " + path + ": " + str(existing))
        if existing == 1:
            return
        signer = self._tool("binary-sign-tool")
        temporary = path + ".signed"
        if os.path.lexists(temporary):
            os.unlink(temporary)
        try:
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", temporary,
                 "-selfSign", "1"],
                check=True, stdout=sys.stderr, timeout=180,
            )
            if self._readelf(
                    readelf, ["-SW", temporary]).count(".codesign") != 1:
                raise ConanException(
                    "self-signed ELF has an invalid .codesign: " + path)
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)
        if self._readelf(readelf, ["-SW", path]).count(".codesign") != 1:
            raise ConanException("final .codesign validation failed: " + path)
        self.output.info("renewed codesign: " + os.path.basename(path))

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        pkg = self.dependencies.get(self.tested_reference_str)
        if not pkg or not pkg.package_folder:
            raise ConanException("tested package not in graph")
        exe = os.path.join(pkg.package_folder, "bin", "skladnik")
        # KDEInstallDirs puts the theme assets under share/skladnik/themes.
        data = os.path.join(pkg.package_folder, "share", "skladnik")
        if not os.path.isfile(exe):
            raise ConanException("installed binary missing: " + exe)
        if not os.path.isdir(os.path.join(data, "themes")):
            raise ConanException("installed theme data missing: " + data)

        ohos = str(self.settings.os) == "OHOS"
        if ohos:
            self._prepare_runtime_links()
            self._fix_absolute_needed()
            self._ensure_codesign(exe)

        libdirs = self._collect_libdirs()
        test_env = Environment()
        for libdir in libdirs:
            test_env.prepend_path("LD_LIBRARY_PATH", libdir)
        if ohos:
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        resolve_dirs = list(libdirs)
        if ohos:
            resolve_dirs.append("/system/lib64")
        test_env.define("SKLADNIK_TEST_BIN", exe)
        test_env.define("SKLADNIK_TEST_DATA_DIR", data)
        test_env.define("SKLADNIK_TEST_PLATFORM", str(self.settings.os))
        test_env.define("SKLADNIK_EXPECTED_VERSION", "0.5.26042")
        # Check 05 resolves DT_NEEDED against the dependency closure plus the
        # platform system lib dir: libc++_shared.so and libc.so come from OHOS
        # itself under /system/lib64, not from any conan package, and the
        # loader does find them there at runtime (build 92324 evidence:
        # without the system dir, check 05 reported both unresolved even
        # though the game started and printed its version string).
        test_env.define("SKLADNIK_TEST_LIBDIRS",
                        os.pathsep.join(resolve_dirs))
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        test_env.define("HOME", test_home)

        cmd = os.path.join(self.cpp.build.bindirs[0],
                           "skladnik_consumer_test")
        if ohos:
            self._ensure_codesign(cmd)
        with test_env.vars(self).apply():
            self.run(shlex.quote(cmd), env="conanrun")
            self.output.info("skladnik consumer test passed")
