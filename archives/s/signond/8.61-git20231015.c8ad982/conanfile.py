#!/usr/bin/env python3
"""Conan recipe — signond 8.61-git20231015.c8ad982 for HarmonyOS PC (aarch64).

signond is the accounts-sso Single Sign On daemon: a D-Bus service
(com.google.code.AccountsSSO.SingleSignOn) that stores online-account
credentials and drives per-provider authentication plugins.  This package
builds the *daemon half* of the upstream source tree:

    src/signond              -> bin/signond              (the daemon)
    src/remotepluginprocess  -> bin/signonpluginprocess  (plugin host process)
    src/plugins/password|example
                             -> lib/signon/lib<type>plugin.so (auth plugins)
    lib/plugins/signon-plugins, lib/plugins/signon-plugins-common,
    lib/signond/SignOn       -> plugin / extension SDK shared libraries

The client library half (lib/SignOn -> SignOnQt6, what libaccounts/KAccounts
consume) is published separately as the `libsignon-qt` package; rebuilding it
here would duplicate that artifact.

Build system: upstream is qmake-only (signon.pro + *.pri) and the ohpcd
qtbase package ships no OHOS mkspec, so qmake cannot cross-compile.  The
recipe distributes a hand-written CMakeLists.txt (plus the upstream *.pc.in /
*.service.in templates) through exports_sources and reproduces the qmake
targets, compile definitions and install semantics for the Qt6 flavour (the
non-identical install entries are listed in the archive's notes.md).  No
upstream source file is modified: patches/ is empty.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SignondConan(ConanFile):
    name = "signond"
    version = "8.61-git20231015.c8ad982"
    description = ("Single Sign On daemon (accounts-sso) with its authentication "
                   "plugin host and plugin/extension SDK")
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/accounts-sso/signond"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # Build assets shipped next to the upstream sources (recipe assets, not
    # upstream source modifications).
    _build_assets = (
        "CMakeLists.txt",
        "signond.pc.in",
        "signon-plugins.pc.in",
        "signon-plugins-common.pc.in",
        "SignOnExtension.pc.in",
        "com.google.code.AccountsSSO.SingleSignOn.service.in",
        "com.nokia.SingleSignOn.Backup.service.in",
    )

    exports_sources = _build_assets

    def export_sources(self):
        export_conandata_patches(self)
        for asset in self._build_assets:
            copy(self, asset, src=self.recipe_folder,
                 dst=self.export_sources_folder)

    def requirements(self):
        # Qt6 Core/DBus/Sql/Xml/Network plus the SQLite driver plugin
        # (plugins/sqldrivers/libqsqlite.so).  The plain `qtbase` package is
        # built with FEATURE_sql=OFF and has no Qt6Sql at all, so the
        # published `qtbase-sql-dbus` variant is the Qt6 provider
        # (ktextaddons / akonadi / qmmp precedent in this repository).
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # qtbase-sql-dbus sets cmake_find_mode=none, so CMakeDeps generates no
        # Qt6 config for it; point CMake at the Qt6Config.cmake shipped inside
        # that package instead (libsignon-qt 8.61 precedent).
        deps = CMakeDeps(self)
        deps.generate()

        qtbase = self.dependencies["qtbase-sql-dbus"]
        qt6_dir = os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6")
        if not os.path.isdir(qt6_dir):
            raise ConanException(
                "qtbase-sql-dbus does not provide lib/cmake/Qt6 at {}".format(
                    qtbase.package_folder)
            )

        tc = CMakeToolchain(self)
        tc.variables["Qt6_DIR"] = qt6_dir
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # The upstream tests/passwordplugintest suite drives the real
        # PasswordPlugin class through the public AuthPluginInterface and needs
        # no D-Bus session bus, so it is built and run here as upstream
        # regression evidence.
        tc.variables["SIGNOND_BUILD_UPSTREAM_TESTS"] = "ON"
        tc.generate()

    def _runtime_library_path(self):
        """Host dependency libdirs, for running the freshly built test binary.

        The build-tree executables have no RUNPATH (the SDK links the Qt6
        libraries from the conan cache), so the upstream test is executed with
        an explicit loader path instead of relying on the host environment.
        """
        paths = []
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.aggregated_components().libdirs:
                path = os.path.normpath(
                    os.path.join(dependency.package_folder, libdir)
                )
                if os.path.isdir(path) and path not in paths:
                    paths.append(path)
        return paths

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        library_paths = self._runtime_library_path()
        if not library_paths:
            raise ConanException("Could not resolve dependency library paths")
        # The freshly built shared libraries live in the CMake binary dir (the
        # test executable links libsignon-plugins.so from there) and carry no
        # RUNPATH, so both the build dir and the Qt6/dbus package libdirs must
        # be on the loader path.
        library_paths.insert(0, self.build_folder)
        env_prefix = 'LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" '.format(
            os.pathsep.join(library_paths)
        )
        # Upstream tests/passwordplugintest (tests/passwordplugintest.pro):
        # 7 test functions + init/cleanupTestCase.
        self.run("{} ctest --output-on-failure".format(env_prefix),
                 cwd=self.build_folder, env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # --- daemon + tools -------------------------------------------------
        self.cpp_info.bindirs = ["bin"]

        # The plugin SDK headers include the SignOn client types; those headers
        # are shipped inside this package (see CMakeLists.txt) so the SDK is
        # self-contained and `signon-plugins.pc` has no dangling Requires.  The
        # client *library* (SignOnQt6) remains the separate libsignon-qt
        # package; taking a dependency on it here would pull a second,
        # incompatible Qt6 provider (plain qtbase) into the graph alongside
        # qtbase-sql-dbus.

        # --- plugin / extension SDK ----------------------------------------
        # libsignon-plugins carries the AuthPluginInterface metaobject and
        # vtable that every authentication plugin resolves at load time;
        # libsignon-plugins-common provides the daemon<->plugin blob IPC and
        # libsignon-extension the extension interfaces.
        self.cpp_info.libs = [
            "signon-plugins",
            "signon-plugins-common",
            "signon-extension",
        ]
        self.cpp_info.libdirs = ["lib"]
        # The SDK headers live one level down (upstream install layout):
        # include/signon-plugins/SignOn (auth plugin SDK), include/signon-extension/SignOn
        # (extension SDK) and include/signond (service constants).  Consumers use
        # #include <SignOn/...>, so those two SDK roots are the include dirs.
        self.cpp_info.includedirs = [
            "include/signon-plugins",
            "include/signon-extension",
            "include/signond",
        ]
        self.cpp_info.set_property("cmake_file_name", "signond")
        self.cpp_info.set_property("cmake_target_name", "signond::signond")
        self.cpp_info.set_property("pkg_config_name", "signond")
