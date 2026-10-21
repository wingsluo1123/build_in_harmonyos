#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-printers 23.10.1 (CMake, daemon binary).

Ayatana System Indicators' printers indicator: listens to the CUPS notification
D-Bus interface (org.cups.cupsd.Notifier), tracks the printer state and exports
an Ayatana indicator menu (actions + menu models) on the session bus under the
name org.ayatana.indicator.printers.

Product: the daemon binary `ayatana-indicator-printers-service`
(libexec/ayatana-indicator-printers/) plus the data files
(org.ayatana.indicator.printers indicator descriptor and the autostart
.desktop entry).

Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class AyatanaIndicatorPrintersConan(ConanFile):
    name = "ayatana-indicator-printers"
    version = "23.10.1"
    description = "Ayatana printers indicator (daemon): CUPS notifier backed printer status indicator"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-printers"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        # glib/2.84.0.1 is the newest glib whose zlib requirement
        # (zlib/1.3.1.1) matches cups/2.4.19; ayatana-common/0.9.11 is the
        # matching libayatana-common track and requires the same glib.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("ayatana-common/0.9.11", transitive_headers=True, transitive_libs=True)
        self.requires("cups/2.4.19", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # tar_format in conandata.yml is documentation/CI metadata only; get()
        # does not accept it, so pass url/sha256 explicitly.
        source_data = self.conan_data["sources"]
        get(
            self,
            url=source_data["url"],
            sha256=source_data.get("sha256", ""),
            strip_root=True,
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._provide_gio_unix_pkg_config()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        # The daemon is a libexec binary (upstream uses
        # CMAKE_INSTALL_FULL_LIBEXECDIR); force the canonical layout so it lands
        # under libexec/ayatana-indicator-printers/ instead of bin/.
        toolchain.variables["CMAKE_INSTALL_LIBEXECDIR"] = "libexec"
        # The upstream test/ suite is a single GDBus mock (mock-cups-notifier)
        # whose only build dependency is the gdbus-codegen tool coming from the
        # glib package, so the upstream tests are built and executed here.
        toolchain.variables["ENABLE_TESTS"] = "ON"
        toolchain.variables["ENABLE_WERROR"] = "OFF"
        # The SDK ships a dangling /data/service/hnp/bin/gdbus-codegen symlink,
        # which find_program() resolves before the working copy provided by the
        # glib package; pin the program search path to the package tools.
        program_paths = []
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        if os.path.isdir(glib_bin):
            program_paths.append(glib_bin)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir) and bin_dir not in program_paths:
                program_paths.append(bin_dir)
        if program_paths:
            toolchain.variables["CMAKE_PROGRAM_PATH"] = ";".join(
                path.replace(os.sep, "/") for path in program_paths
            )
        toolchain.generate()

    def _augment_glib_pkg_config(self):
        # main.c includes <glib/gi18n.h>, which maps gettext() to the
        # g_libintl_* API implemented by the libintl.so shipped inside the glib
        # package. The PkgConfigDeps-generated glib-2.0.pc does not list -lintl,
        # so the daemon would keep undefined g_libintl_* symbols at link time.
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            libs_line = next(
                (line for line in content.splitlines() if line.startswith("Libs:")),
                None,
            )
            if libs_line is None or "-lintl" in libs_line.split():
                continue
            updated = content.replace(libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)

    def _provide_gio_unix_pkg_config(self):
        # The glib recipe exports glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0
        # components but no gio-unix-2.0 one, so PkgConfigDeps does not generate
        # gio-unix-2.0.pc even though the upstream CMakeLists requires it via
        # pkg_check_modules. Copy the .pc shipped inside the glib package and
        # rewrite its absolute prefix so its Cflags point at that package.
        glib_folder = self.dependencies["glib"].package_folder
        source = os.path.join(glib_folder, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(source):
            return
        target = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        prefix = glib_folder.replace(os.sep, "/")
        with open(source, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("prefix=/", f"prefix={prefix}")
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            # Upstream test suite (test/CTest): mock-cups-notifier. Driven
            # through ctest directly so the per-test result list is printed.
            self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # The daemon installs under libexec/ayatana-indicator-printers/; the data
        # files (indicator descriptor, autostart .desktop) land under
        # share//etc. There is no library and no PATH tool to expose.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "ayatana-indicator-printers")
        self.cpp_info.set_property(
            "cmake_target_name", "ayatana-indicator-printers::ayatana-indicator-printers"
        )

    def _build_environment(self):
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                # gdbus-codegen comes from the glib package (the SDK one may be
                # unusable); the CUPS tools come from the cups package.
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "libexec", "**", "*"),
            os.path.join(self.package_folder, "bin", "**", "*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target) or os.path.isdir(target):
                continue
            with open(target, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
