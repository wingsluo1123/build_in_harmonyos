#!/usr/bin/env python3
"""Conan recipe for kunitconversion5 5.116.0 (KDE Frameworks 5 / Qt5) on
HarmonyOS PC.

kunitconversion5 is the KDE Frameworks unit conversion library (builds
libKF5UnitConversion): Converter / Value / UnitCategory plus 27 unit
category tables (length, area, volume, temperature, velocity, mass,
pressure, energy, currency, power, time, fuel efficiency, density,
acceleration, force, angle, frequency, thermal x3, voltage, electrical
current, electrical resistance, permeability, binary data).

OHOS-specific adaptations (validated on the sibling kitemviews5 /
ki18n5 / kpeople5 KF5 skeletons):

  - QT_MAJOR_VERSION=5 so the project selects Qt5 (Core + Network).
  - CMAKE_SYSTEM_NAME=Linux: the OHOS Conan toolchain maps os=OHOS to
    CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake defines neither UNIX nor a
    platform module.  ECM only registers the upstream ctest cases when the
    build is not cross-compiling; OHOS is POSIX so forcing the Linux
    platform keeps everything intact (chain-wide convention).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON: the po/ -> .mo processing is skipped
    (chain-wide convention; Qt5LinguistTools is not published on ohpcd).
  - qt5-qtbase is consumed through its native Qt5 configs
    (lib/cmake/Qt5/Qt5Config.cmake aggregates the per-module configs:
    Core/Network/Test); CMakeDeps shadowing is suppressed with
    cmake_find_mode=none and the prefix is wired via the paths file
    (kitemviews5 / kconfig5 precedent).
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export Qt5::moc/rcc;
    the autotests are QTEST objects and need moc).
  - Qt5CoreConfigExtrasMkspecDir.cmake hard-codes a build-tree path
    <prefix>/../b/mkspecs/linux-clang which the packaged cache entry never
    has; generate() recreates the mkspecs tree there (kitemviews5
    precedent).
  - BUILD_TESTING=ON: the upstream QTEST targets are really executed from
    build() through ctest.  valuetest (5 functions), categorytest (5),
    convertertest (6) and currencytableinittest (1) register as 4 CTest
    entries.  Three of the 17 upstream test functions assert a live ECB
    currency-table HTTPS download (ConverterTest::testCurrency,
    ConverterTest::testCurrencyConversionTableUpdate,
    CategoryTest::testCurrencyTableUpdate); Qt5Network from the
    qt5-qtbase/5.15.2.2 supply is built with -no-openssl (no TLS backend)
    and the CI sandbox has no outbound network route, so those three are
    QSKIP-guarded through patches/0001 (kmbox / kservice QSKIP precedent)
    instead of being dropped.  currencytableinittest really runs: the
    packaged currency.xml snapshot is deployed into the per-test
    QStandardPaths test-mode data dir ($HOME/.qttest/share/
    libkunitconversion/) so Converter parses the table offline and the
    EUR->USD rate math is asserted against the real data.
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE +
    CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname," -> relocatable,
    unversioned DT_SONAME (W3 CI L5 soname gate).
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap PROT_EXEC
    a shared library whose ELF was rewritten after linking.
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache filesystem refuses the
    make jobserver fifo (EPERM).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while running the Qt host
    tools and the upstream tests so the loader resolves the compatible
    libc++ first (kcoreaddons5 / kitemviews5 precedent).
  - package(): the installed libKF5UnitConversion.so is re-signed with
    binary-sign-tool (E077 four-step flow; CMake install strips the
    build-tree RPATH, which rewrites the ELF and invalidates the link-time
    .codesign section - kcolorpicker precedent).
"""
import glob
import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KUnitConversion5Conan(ConanFile):
    name = "kunitconversion5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - Unit conversion library (libKF5UnitConversion)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kunitconversion"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        # KF5I18n: the upstream find_package(KF5I18n 5.116.0 REQUIRED) plus
        # the i18nc()/ki18ncp() catalog calls all over the unit tables.
        self.requires("ki18n5/5.116.0")

    def build_requirements(self):
        # ECM 6.26.0 satisfies find_package(ECM 5.116.0 NO_MODULE)
        # (minimum-version semantics, same pattern as attica5/ki18n5).
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase: they
        # provide the aggregated Qt5Config (Core/Network/Test components)
        # and the per-module imported targets the project relies on.  The
        # CMakeDeps-generated lowercase configs would shadow them, so
        # suppress them (cmake_find_mode=none) and add the Qt prefix to
        # CMAKE_PREFIX_PATH through the paths file below (kitemviews5 /
        # kconfig5 precedent).  ki18n5 also installs its own
        # KF5I18nConfig.cmake (find_dependency on Qt5Core), consumed the
        # same way.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.set_property("ki18n5", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Treat OHOS as a Linux-like target so CMake defines UNIX and does
        # not report a cross build (see module docstring): ECM then registers
        # the upstream ctest cases and applies the POSIX flags/rpath
        # settings.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # HMDFS cannot create the make jobserver fifo (EPERM).
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # E537: link with the final install RPATH so the install step does
        # not rewrite the ELF in place (see module docstring).
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        # Relocatable, unversioned DT_SONAME (W3 CI L5 soname gate).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qt5 = self.dependencies["qt5-qtbase"]
        # Recreate the mkspecs tree Qt5CoreConfigExtrasMkspecDir.cmake
        # expects next to the package prefix (kitemviews5 precedent).
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        qbin = os.path.join(qt5.package_folder, "bin")
        for tool, cmake_var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
        ):
            tool_path = os.path.join(qbin, tool)
            if not os.path.isfile(tool_path):
                raise ConanInvalidConfiguration(
                    "qt5-qtbase/5.15.2.2 does not provide the required "
                    "bin/{} tool".format(tool)
                )
            tc.variables[cmake_var] = tool_path

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        # KF5I18n's ki18n_install(po) registers a pofiles build target that
        # runs msgfmt on every po/ catalog (gettext reaches this graph
        # transitively through ki18n5); the sandbox PATH has no msgfmt, so
        # pass the tools explicitly when the package provides them
        # (kpeople5 precedent; harmless with KF_SKIP_PO_PROCESSING=ON).
        gettext = self.dependencies.get("gettext")
        if gettext:
            for tool, cmake_var in (
                ("msgfmt", "GETTEXT_MSGFMT_EXECUTABLE"),
                ("msgmerge", "GETTEXT_MSGMERGE_EXECUTABLE"),
            ):
                tool_path = os.path.join(gettext.package_folder, "bin", tool)
                if os.path.isfile(tool_path):
                    tc.variables[cmake_var] = tool_path

        tc.generate()

        # Wire the paths that CMakeDeps cannot provide:
        #  * qt5-qtbase is consumed in "none" find-mode, so its install
        #    prefix must be added manually for find_package(Qt5 ... CONFIG)
        #    to resolve the native Qt5 configs.
        #  * ki18n5 likewise consumes its project-installed KF5I18nConfig.
        #  * ECM is a build-context requirement, so its config-mode
        #    directory must be added for find_package(ECM 5.116.0 NO_MODULE).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        qt_pkg = qt5.package_folder
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        for dep_name, subdirs in (
            ("ki18n5", ("KF5I18n",)),
        ):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(dep.package_folder)
                )
                for sub in subdirs:
                    cfg = os.path.join(dep.package_folder, "lib", "cmake", sub)
                    if os.path.isdir(cfg):
                        lines.append(
                            'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(cfg)
                        )
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "{}")'.format(ecm_cmake))
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(ecm_cmake))
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The whole mkspecs tree is needed: <qplatformdefs.h> is included
        # from the mkspec include dir, and Qt5CoreConfigExtras.cmake
        # resolves it as <package_folder>/../b/mkspecs (the build tree of
        # the original build), which the packaged cache entry never has.
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if not os.path.isdir(source):
            return
        os.makedirs(expected, exist_ok=True)
        for name in os.listdir(source):
            src_entry = os.path.join(source, name)
            dst_entry = os.path.join(expected, name)
            if os.path.exists(dst_entry):
                continue
            if os.path.isdir(src_entry):
                shutil.copytree(src_entry, dst_entry)
            else:
                shutil.copy2(src_entry, dst_entry)

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _runtime_env(self):
        runtime_env = Environment()
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            runtime_env.prepend_path(
                "PATH", os.path.join(qt5.package_folder, "bin")
            )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        if str(self.settings.os) == "OHOS":
            # The sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so; prepend /system/lib64 so the Qt host tools
            # and the test executables resolve the compatible libc++ first
            # (kcoreaddons5 / kitemviews5 precedent).
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _run_upstream_tests(self):
        if not can_run(self):
            return
        test_env = self._runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        try:
            os.chmod(xdg_runtime, 0o700)
        except OSError:
            pass
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._deploy_currency_table_test_data(test_home)
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _deploy_currency_table_test_data(self, test_home):
        # currencytableinittest enables QStandardPaths::setTestModeEnabled(
        # true), which pins GenericDataLocation to <HOME>/.qttest/share
        # regardless of XDG_DATA_HOME.  The test copies the qrc-embedded
        # currency.xml snapshot to <that>/libkunitconversion/currency.xml
        # and asserts the EUR->USD conversion against the real table; the
        # parent directory must pre-exist because QFile::copy does not
        # create it.  With the cache present and fresh, Converter's
        # syncConversionTable(24h) parses the local file and never touches
        # the network.
        cache_dir = os.path.join(test_home, ".qttest", "share", "libkunitconversion")
        os.makedirs(cache_dir, exist_ok=True)
        self.output.info(
            "Prepared QStandardPaths test-mode currency cache dir: {}".format(
                cache_dir
            )
        )

    def _prepare_ctest_runtime_links(self):
        # CTest discovers executables in <build>/bin; their
        # libKF5UnitConversion and Qt5 runtime deps live in the build tree
        # / conan package folders.  Symlink them next to the test binaries
        # so the loader resolves.
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        # The host cmake (and the OHOS signing tools below) live under
        # /data/service/hnp and need the compatible libc++ on
        # LD_LIBRARY_PATH; without the wrapper the loader fails with
        # "Error relocating cmake: symbol not found" (same env as build()).
        with self._runtime_env().vars(self).apply():
            cmake.install()
            if str(self.settings.os) == "OHOS":
                self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF files (E077 four-step flow).

        CMake install strips the build-tree RPATH, which rewrites the ELF
        and invalidates the link-time .codesign section; altered/unsigned
        ELF files fail to load with "operation not permitted" (E077/E135).
        Flow: remove old signature -> (re)sign -> restore permissions.
        """
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                    prefix=".conan-sign-", dir=os.path.dirname(binary)) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        "remove the old code signature from {}".format(binary))
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    "sign {}".format(binary))
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        "Signing did not produce a runnable ELF file for {}".format(
                            binary))
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        "Signing did not add a .codesign section to {}".format(
                            binary))
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], "inspect ELF sections in {}".format(path))
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(
                "Unable to {}: {}".format(action, error)) from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanException(
                "Unable to {}: {}".format(action, detail or "tool exited unsuccessfully")
            )
        return result.stdout

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                "Required tool {} was not found; set {} or add it to PATH".format(
                    executable, environment_variable)
            )
        return os.path.abspath(resolved)

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError:
            return None
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            return None
        return int.from_bytes(header[16:18], byte_order)

    def package_info(self):
        # The project installs its own KF5UnitConversionConfig.cmake with
        # proper dependency tracking (find_dependency on Qt5Core); use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5UnitConversion"]
