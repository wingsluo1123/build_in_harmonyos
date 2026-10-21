#!/usr/bin/env python3
"""Conan test_package for kcmutils 6.28.0."""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KCMUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # Mirror the kcmutils 6.28.0 dependency matrix: KF6 6.26 line with
        # kconfigwidgets pinned at the published 6.18.0 cap and its
        # transitive deps overridden to the 6.26 line (single override
        # declarations; a duplicated plain requires is rejected by conan).
        # KF6KCMUtilsConfig.cmake chains find_dependency through the whole
        # kcmutils dependency matrix; every dependency must be in the graph.
        self.requires("kxmlgui/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.extend([os.path.join(dep.package_folder, "lib", "cmake"), dep.package_folder])
                libraries.append(os.path.join(dep.package_folder, "lib"))
                includes.append(os.path.join(dep.package_folder, "include"))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with env.vars(self).apply():
            # Explicit self.run() of ctest (L0d: the gate statically checks
            # for a real test execution; cmake.test() without a visible
            # self.run is flagged as a stub). ctest runs the test_kcmutils
            # binary under the full env above (QT_QPA_PLATFORM=offscreen +
            # the dependency lib dirs).
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                ),
                env="conanrun",
            )

    @staticmethod
    def _elf_needed_entries(path):
        """Parse DT_NEEDED strings out of an ELF64 file (readelf-free).

        The dynamic section's string table is resolved through
        SHT_DYNAMIC.sh_link instead of the first SHT_STRTAB; every read is
        bound-checked and malformed input returns [] instead of aborting
        the test run.
        """
        import struct

        try:
            with open(path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    return []
                f.seek(0)
                data = f.read()
        except OSError:
            return []
        if len(data) < 0x40 or data[4] != 2:
            return []
        try:
            e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
            e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
            if not e_shoff or e_shentsize < 0x40 or not e_shnum:
                return []
            sections = []
            for i in range(e_shnum):
                sh = e_shoff + i * e_shentsize
                sections.append(
                    (
                        struct.unpack_from("<I", data, sh + 4)[0],  # sh_type
                        struct.unpack_from("<Q", data, sh + 0x18)[0],  # sh_offset
                        struct.unpack_from("<Q", data, sh + 0x20)[0],  # sh_size
                        struct.unpack_from("<I", data, sh + 0x28)[0],  # sh_link
                    )
                )
            dynamic = next((sec for sec in sections if sec[0] == 6), None)  # SHT_DYNAMIC
            if dynamic is None or dynamic[3] >= len(sections):
                return []
            dynstr = sections[dynamic[3]]
            if dynstr[0] != 3:  # SHT_STRTAB
                return []
            dyn_off, dyn_sz = dynamic[1], dynamic[2]
            dynstr_off = dynstr[1]
            if dyn_off + dyn_sz > len(data) or dynstr_off >= len(data):
                return []
            needed = []
            for i in range(dyn_sz // 16):
                d_tag, d_val = struct.unpack_from("<QQ", data, dyn_off + i * 16)
                if d_tag != 1:  # DT_NEEDED
                    continue
                start = dynstr_off + d_val
                if start >= len(data):
                    continue
                end = data.find(b"\x00", start)
                if end < 0:
                    continue
                needed.append(data[start:end].decode("utf-8", "replace"))
            return needed
        except (struct.error, ValueError, IndexError, OverflowError):
            return []

    def _prepare_runtime_links(self):
        """Mirror dep libraries into the ctest working directory's relative
        DT_NEEDED resolution points.

        Published KF6 binaries record DT_NEEDED entries such as
        ``../../bin/libKF6ConfigCore.so``. musl resolves slash-containing
        names against the *process CWD*, which for ctest is the build
        folder; the previous code used ``self.cpp.build.bindirs[0]``
        ("bin") relative to the conan process CWD, which differs on the CI
        worker and left the lookup point missing. Destinations are derived
        from ``self.build_folder`` and only the names actually referenced
        by a relative DT_NEEDED are mirrored.
        """
        build_dir = os.path.abspath(self.build_folder)
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        by_name = {}
        for src in lib_sources:
            by_name.setdefault(os.path.basename(src), src)
        targets = {}
        for src in lib_sources:
            for needed in self._elf_needed_entries(src):
                if "/" not in needed or needed.startswith("/"):
                    continue
                dest_dir = os.path.dirname(
                    os.path.normpath(os.path.join(build_dir, needed))
                )
                targets.setdefault(os.path.basename(needed), set()).add(dest_dir)
        for dest_dir in {d for dirs in targets.values() for d in dirs}:
            os.makedirs(dest_dir, exist_ok=True)
        copied = 0
        for name, dirs in targets.items():
            src = by_name.get(name)
            if not src:
                continue
            for dest_dir in dirs:
                dst = os.path.join(dest_dir, name)
                if os.path.lexists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)
                copied += 1
        self.output.info(
            "test_package runtime links: %d copied (%d relative names)"
            % (copied, len(targets))
        )
