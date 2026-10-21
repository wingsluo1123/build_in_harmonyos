#!/usr/bin/env python3
"""Conan test_package for kmines 26.04.0.

Consumer-side verification for an application package (upstream registers
no test suite - N=0). The consumer executor drives the installed
deliverable end to end:

* Part 1 (R34): execute the installed kmines binary with --version under
  QT_QPA_PLATFORM=offscreen and require the 4.0.26040 version string.
* Part 2: KGameThemeProvider::discoverThemes("themes") must discover the
  six themes installed into share/kmines/themes, and every theme's
  graphicsPath must resolve to a valid gzip-compressed SVGZ file (the
  exact files the game's scene loads at startup).
* Part 3: KGameRenderer renders the "mainWidget" sprite from the default
  theme through the real SVGZ -> QSvgRenderer -> QPixmap pipeline used by
  KMines' QGraphicsScene.
* Part 4: boot the installed kmines GUI offscreen with an isolated HOME
  and require startup progress: the process survives five seconds, or on
  a bus-less image it exits with the exact KDBusAddons "DBus session bus
  not found" diagnostic (proving the ELF/Qt/KF6 loader chain completed;
  any other early exit fails).

The runtime environment mirrors the kgoldrunner 26.04.0 precedent:
relative DT_NEEDED entries baked into the published KF6 packages are
resolved through a compatibility symlink/copy farm, the OHOS loader gets
/system/lib64 for libc++_shared.so, and openal-soft/libsndfile
(transitive requirements of libkdegames behind libKDEGames6.so) are
located through the dependency graph and appended to LD_LIBRARY_PATH.
XDG_DATA_DIRS points at the tested package's share/ so QStandardPaths
resolves AppDataLocation to share/kmines.

On OHOS the tested executable is signed by the recipe's package() (a
DT_NEEDED rewrite invalidates .codesign, so the signed artifact is
produced there, not here). This test only builds the runtime shims and
keeps the tested package folder read-only; absolute-NEEDED fallbacks are
bounded to Conan cache roots and the test build tree.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class KminesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        # openal-soft is required by libKDEGames6.so (NEEDED libopenal.so.1)
        # but is not surfaced through the tested package's direct dependency
        # view; require it explicitly so its lib dir lands in the runtime
        # environment (version pinned to libkdegames' requirement).
        self.requires("openal-soft/1.25.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase/KF6/libkdegames packages use cmake_find_mode=none: write
        # conan_cmakedeps_paths manually (kgoldrunner 26.04.0 precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            pkg = dep.package_folder
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
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with build_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _collect_transitive_libdirs(self):
        """Every package folder reachable in the test graph (direct +
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
        """Compatibility symlinks for relative DT_NEEDED entries baked into
        the published KF6 packages (kconfig's libKF6ConfigGui.so needs
        '../../bin/libKF6ConfigCore.so' relative to the process cwd -
        audiocd 26.04.3 / libkcddb precedent)."""
        compat_libs = {}
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if name.endswith(".so") or name.endswith(".so.6"):
                    compat_libs[name] = os.path.join(libdir, name)
        # the relative path is resolved from cwd; the test runs from the
        # build folder, so provide <build>/../../bin and <build>/bin
        exe_dir = os.path.dirname(
            os.path.join(self.build_folder, self.cpp.build.bindirs[0])
        )
        for base in (
            os.path.normpath(os.path.join(exe_dir, os.pardir, os.pardir, "bin")),
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

    def _fallback_root_allowed(self, target):
        """Only create absolute-NEEDED compatibility paths inside a Conan
        cache or the test build tree. The entries come from third-party
        binaries' DT_NEEDED strings, so an unbounded makedirs()/symlink()
        would write wherever those metadata strings point; anything outside
        these roots is skipped with a warning instead."""
        roots = []
        conan_home = os.environ.get("CONAN_HOME")
        if conan_home:
            roots.append(conan_home)
        home = os.path.expanduser("~")
        roots.append(os.path.join(home, ".conan2"))
        roots.append(os.path.join(home, ".cache", "conan2"))
        roots.append(self.build_folder)
        target_abs = os.path.abspath(target)
        for root in roots:
            root_abs = os.path.abspath(root)
            if target_abs == root_abs or target_abs.startswith(
                root_abs + os.sep
            ):
                return True
        return False

    def _fix_absolute_needed(self):
        """The published KF6 binaries carry build-machine absolute paths in
        DT_NEEDED (e.g. libKF6XmlGui.so needs .../p/kicon<hash>/p/lib/
        libKF6IconThemes.so, libKDEGames6.so needs .../p/b/kicon<hash>/...).
        The OHOS musl loader resolves path-style NEEDED entries literally
        with no LD_LIBRARY_PATH fallback, and on a fresh worker those
        directories do not exist (kiconthemes may be rebuilt from source
        with a different build-folder hash). Create the missing paths from
        the real libraries found in the dependency packages (a symlink, or
        a plain copy when the filesystem rejects symlink(2) - HMDFS on the
        device does).
        """
        import struct

        def elf_needed(path):
            """Minimal ELF DT_NEEDED extractor (no readelf dependency)."""
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
            e_shnum = struct.unpack_from("<H" if is_le else ">H", data, 0x3C)[0]
            needed = []
            dynstr = None
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                if off + e_shentsize > len(data):
                    break
                sh_type = struct.unpack_from(
                    "<I" if is_le else ">I", data, off + 4)[0]
                if sh_type == 3:  # SHT_STRTAB
                    dynstr = off
                elif sh_type == 6:  # SHT_DYNAMIC
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
                        if tag == 1:  # DT_NEEDED
                            s = str_off + val
                            e = data.index(b"\x00", s)
                            needed.append(data[s:e].decode("utf-8", "replace"))
                        p += 16
            return needed

        # index: soname -> real file, from every dependency package libdir
        index = {}
        libdirs = []
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir) and libdir not in libdirs:
                libdirs.append(libdir)
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
                    base = os.path.basename(entry)
                    source = index.get(base)
                    if not source:
                        continue
                    if not self._fallback_root_allowed(entry):
                        self.output.warning(
                            "absolute-NEEDED fallback outside the conan "
                            f"cache/build tree, skipped: {entry}"
                        )
                        continue
                    try:
                        os.makedirs(os.path.dirname(entry), exist_ok=True)
                    except OSError as e:
                        self.output.warning(
                            f"cannot create NEEDED fallback dir for {entry}: {e}")
                        continue
                    try:
                        if not os.path.lexists(entry):
                            os.symlink(source, entry)
                            fixes += 1
                    except OSError:
                        # HMDFS (device $HOME) rejects symlink(2); the OHOS
                        # musl loader only needs a file at the baked path,
                        # so a real copy is equivalent (ktextwidgets 6.18.0
                        # device precedent).
                        try:
                            if not os.path.lexists(entry):
                                shutil.copy2(source, entry)
                                fixes += 1
                        except OSError as e:
                            self.output.warning(
                                f"cannot create NEEDED fallback {entry}: {e}")
        if fixes:
            self.output.info(
                f"created {fixes} absolute-NEEDED compatibility fallbacks")

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        pkg = self.dependencies.get(self.tested_reference_str)
        if not pkg or not pkg.package_folder:
            raise ConanException("tested package not in graph")
        exe = os.path.join(pkg.package_folder, "bin", "kmines")
        data = os.path.join(pkg.package_folder, "share", "kmines")
        themes = os.path.join(data, "themes")
        if not os.path.isfile(exe):
            raise ConanException(f"installed binary missing: {exe}")
        if not os.path.isdir(themes):
            raise ConanException(f"installed themes missing: {themes}")

        if str(self.settings.os) == "OHOS":
            # bin/kmines is already signed inside package(): a DT_NEEDED
            # rewrite invalidates .codesign, so signing belongs to the
            # recipe and the tested package folder stays read-only here.
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        xdg_data_home = os.path.join(test_home, ".local", "share")
        xdg_config_home = os.path.join(test_home, ".config")
        xdg_cache_home = os.path.join(test_home, ".cache")
        for d in (xdg_data_home, xdg_config_home, xdg_cache_home):
            os.makedirs(d, exist_ok=True)

        test_env = Environment()
        for libdir in self._collect_transitive_libdirs():
            test_env.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("KMINES_TEST_BIN", exe)
        test_env.define("KMINES_TEST_DATA", data)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("HOME", test_home)
        test_env.define("XDG_DATA_HOME", xdg_data_home)
        test_env.define("XDG_CONFIG_HOME", xdg_config_home)
        test_env.define("XDG_CACHE_HOME", xdg_cache_home)
        # QStandardPaths AppDataLocation = <XDG_DATA_DIRS>/*/kmines
        test_env.define("XDG_DATA_DIRS", os.path.join(pkg.package_folder, "share"))
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            plugins = os.path.join(dep.package_folder, "plugins")
            if os.path.isdir(plugins):
                test_env.prepend_path("QT_PLUGIN_PATH", plugins)
                test_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(plugins, "platforms"),
                )

        cmd = os.path.join(self.cpp.build.bindirs[0],
                           "kmines_consumer_test")
        with test_env.vars(self).apply():
            self.run(f"{shlex.quote(cmd)}", env="conanrun")
            self.output.info("consumer test passed")

