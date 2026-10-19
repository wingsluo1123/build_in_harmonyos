#!/usr/bin/env python3
"""Conan recipe for kdoctools 6.28.0 on HarmonyOS PC.

kdoctools provides the DocBook tooling of KDE Frameworks 6: the KF6DocTools
shared library, the meinproc6 DocBook transformer, the checkXML6 validator and
the KDocTools customization data (DTD/entities/XSL).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE for the KDE platform check (OHOS is not in
    KDE's platform list) and KDE_SKIP_UNINSTALL_TARGET=TRUE because the ECM
    package ships no ecm_uninstall.cmake.in template
  - KF_DEP_VERSION lowered 6.28.0 -> 6.26.0 by patch 0003: the ohpcd registry
    publishes karchive only up to the 6.26.0 line, and KF6Archive is the only
    consumer of that variable (kbookmarks 6.28.0 precedent)
  - DocBook XML 4.5 DTD / DocBook XSL data are optional (patch 0002); when
    absent the upstream autotests are not registered (patch 0006, capability
    guard), docbookl10nhelper output is replaced by a minimal catalog
    (patch 0004), and the kde-include XSL templates are configured without
    the unavailable DocBookXSL_DIR imports (patch 0007)
  - SONAME-only shared-library rules: OHOS CMake ships no Platform module, so
    CMAKE_SHARED_LIBRARY_SONAME_* stays unset and lld emits no DT_SONAME;
    HMDFS additionally rejects the versioned-symlink chain CMake creates for
    VERSION/SOVERSION libraries (libKF6DocTools is versioned upstream)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project's CMakeLists relies on
  - Qt6_DIR/Qt6Core_DIR/KF6Archive_DIR cached explicitly plus a paths file
    because qtbase uses cmake_find_mode=none (CMakeDeps generates nothing)
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class KDocToolsConan(ConanFile):
    name = "kdoctools"
    version = "6.28.0"
    description = "KDE Frameworks 6 DocBook documentation processing tools"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdoctools"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # KF6Archive backs the meinproc6 document cache and is REQUIRED
        # upstream. karchive/6.28.0 is not published to the ohpcd registry
        # yet; the 6.26.0 line is, and patch 0003 lowers KF_DEP_VERSION so the
        # versioned find_package accepts it.
        self.requires("karchive/6.26.0")
        # karchive's KF6ArchiveConfig.cmake does find_dependency(OpenSSL)
        self.requires("openssl/3.5.6.1")
        # libxml2 pinned to the version libxslt/1.1.45.1 already depends on
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.28.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _cmake_dir(package_folder, *candidates):
        for relative in candidates:
            path = os.path.join(package_folder, relative)
            if os.path.isdir(path):
                return path
        return os.path.join(package_folder, candidates[0])

    def generate(self):
        qtbase = self.dependencies["qtbase"]
        karchive = self.dependencies["karchive"]
        xml = self.dependencies["libxml2"]
        xslt = self.dependencies["libxslt"]
        openssl = self.dependencies["openssl"]
        ecm = self.dependencies.build["ecm"]
        ecm_root = os.path.join(ecm.package_folder, "share", "ECM")

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # the ECM package ships no ecm_uninstall.cmake.in, so ECMUninstallTarget
        # would fail its configure_file; KDE's official switch skips the target
        tc.variables["KDE_SKIP_UNINSTALL_TARGET"] = "TRUE"
        # keep the real KF6Archive-backed document cache in meinproc6
        tc.variables["MEINPROC_NO_KARCHIVE"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_LIBEXECDIR"] = "libexec"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        # ECM's installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not; set ECM_DIR and ECM_MODULE_PATH
        # manually so find_package(ECM 6.28.0 NO_MODULE) and the KDE cmake
        # modules (KDEInstallDirs, FindDocBookXML4, FindDocBookXSL, ...)
        # resolve.
        tc.variables["ECM_DIR"] = os.path.join(ecm_root, "cmake")
        tc.variables["ECM_MODULE_PATH"] = ";".join(
            os.path.join(ecm_root, path)
            for path in ("modules", "find-modules", "kde-modules")
        )

        # qtbase is cmake_find_mode=none, so CMakeDeps generates nothing for
        # it and the real Qt6Config.cmake/Qt6CoreConfig.cmake in the package
        # are the only providers. Point the direct lookups at their config
        # dirs (kdoctools 6.19.0 device-verified pattern).
        tc.cache_variables["Qt6_DIR"] = self._cmake_dir(
            qtbase.package_folder, "lib/cmake/Qt6", "share/cmake/Qt6"
        )
        tc.cache_variables["Qt6Core_DIR"] = self._cmake_dir(
            qtbase.package_folder, "lib/cmake/Qt6Core", "share/cmake/Qt6Core"
        )
        tc.cache_variables["KF6Archive_DIR"] = self._cmake_dir(
            karchive.package_folder, "lib/cmake/KF6Archive", "share/cmake/KF6Archive"
        )
        # the project requires an xmllint binary at configure time
        tc.cache_variables["LIBXML2_XMLLINT_EXECUTABLE"] = (
            shutil.which("xmllint") or "xmllint"
        )

        # Optional site DocBook data: the bundled FindDocBookXML4 /
        # FindDocBookXSL modules only scan CMAKE_SYSTEM_PREFIX_PATH, which has
        # no DocBook tree on OHOS. When these env vars point at unpacked
        # official data trees, feed the module result variables directly;
        # when unset the recipe stays on the optional-data path and the
        # DocBook-dependent targets stay disabled.
        for _env_name, _var_name in (
            ("KDOCTOOLS_DOCBOOK_XML4_DIR", "DocBookXML4_DTD_DIR"),
            ("KDOCTOOLS_DOCBOOK_XSL_DIR", "DocBookXSL_DIR"),
        ):
            _data_dir = os.environ.get(_env_name)
            if _data_dir and os.path.isdir(_data_dir):
                tc.cache_variables[_var_name] = _data_dir

        # Paths file injected into the top-level project(): prepend the
        # dependency package roots so config-mode Qt6/KF6Archive search and
        # module-mode FindLibXml2/FindLibXslt/FindOpenSSL resolve, while the
        # ECM find-modules stay authoritative for the DocBook data lookups.
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)",
            'set(ECM_DIR "{}")'.format(os.path.join(ecm_root, "cmake")),
            'set(ECM_MODULE_PATH "{}")'.format(tc.variables["ECM_MODULE_PATH"]),
        ]
        for root in (
            qtbase.package_folder,
            karchive.package_folder,
            xml.package_folder,
            xslt.package_folder,
            openssl.package_folder,
        ):
            lines.extend(
                (
                    'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(root),
                    'list(PREPEND CMAKE_LIBRARY_PATH "{}")'.format(
                        os.path.join(root, "lib")
                    ),
                    'list(PREPEND CMAKE_INCLUDE_PATH "{}")'.format(
                        os.path.join(root, "include")
                    ),
                )
            )
        lines.append(
            'list(PREPEND CMAKE_INCLUDE_PATH "{}")'.format(
                os.path.join(xml.package_folder, "include", "libxml2")
            )
        )
        lines.append('set(OPENSSL_ROOT_DIR "{}")'.format(openssl.package_folder))
        paths_file = os.path.join(
            self.generators_folder, "kdoctools-cmake-paths.cmake"
        )
        save(self, paths_file, "\n".join(lines) + "\n")
        tc.variables["CMAKE_PROJECT_INCLUDE"] = paths_file

        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake ships no Platform/HarmonyOS module, so
        CMAKE_SHARED_LIBRARY_SONAME_* stays unset and lld emits no DT_SONAME.
        Consumers then record the absolute build-machine path of this library
        in DT_NEEDED and fail to load it on CI workers or any clean cache.
        Restore the soname flags through the user make-rules override
        (kitemviews 6.28.0 / kirigami 6.18.0 precedent). HMDFS additionally
        rejects symlink(2) with EPERM, so the versioned-symlink chain CMake
        creates for a versioned library (libKF6DocTools.so.6 ->
        .so.6.28.0) can never be materialized; NO_VERSIONED_SONAME keeps the
        unversioned DT_SONAME and drops the chain.

        The CMAKE_SHARED_LIBRARY_RUNTIME_* (rpath) flags are deliberately not
        defined here. With them defined, CMake bakes the build-tree library
        directories into a RUNPATH, and cmake install() then rewrites the ELF
        in place to strip it; this device's loader rejects the rewritten
        library on dlopen (EACCES while the untouched linker output loads).
        Without the flags CMake emits no RUNPATH and install() is a pure
        copy."""
        rules = os.path.join(
            self.generators_folder, "ohos-shared-library-rules.cmake"
        )
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
            )) + "\n",
        )
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _runtime_env(self):
        env = Environment()
        # The sandbox LD_LIBRARY_PATH contains an incompatible
        # libc++_shared.so under /data/storage/el1/bundle/libs/arm64 which
        # shadows the compatible one; prepend /system/lib64 so the loader
        # resolves the compatible libc++ first (kconfig 6.26.0 / kitemviews
        # 6.28.0 precedent).
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        prefix_paths = []
        seen_folders = set()
        # self.dependencies.values() covers the host-context runtime closure
        # (qtbase, karchive, libxml2, libxslt, openssl and their transitive
        # library dependencies such as zstd); merge the build-context view
        # explicitly so the ecm tool_requires root also lands in
        # CMAKE_PREFIX_PATH on Conan versions whose values() view omits it.
        dependency_views = (
            list(self.dependencies.values())
            + list(self.dependencies.build.values())
        )
        for dependency in dependency_views:
            if not dependency or not dependency.package_folder:
                continue
            if dependency.package_folder in seen_folders:
                continue
            seen_folders.add(dependency.package_folder)
            prefix_paths.append(dependency.package_folder)
            lib_dir = os.path.join(dependency.package_folder, "lib")
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(lib_dir):
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
            if os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)
        for relative in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, relative)
            )
        env.prepend_path("PATH", os.path.join(self.build_folder, "bin"))
        env.prepend_path("PATH", os.path.join(self.build_folder, "src"))
        # The kdoctools_install autotest configures a nested consumer project
        # with a clean cache (cmake --build-and-test); export the dependency
        # prefixes so its find_package(ECM/Qt6Core/KF6DocTools) resolve the
        # same way as the outer build. The device CMake splits the
        # CMAKE_PREFIX_PATH environment variable on the platform path
        # separator, so a semicolon-joined value is treated as one
        # (nonexistent) prefix and the nested configure cannot find
        # ECMConfig.cmake; join with os.pathsep instead.
        env.define("CMAKE_PREFIX_PATH", os.pathsep.join(prefix_paths))
        return env

    def build(self):
        # portability patches only; no platform conditionals inside them
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if can_run(self):
            test_env = self._runtime_env()
            test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
            test_env.define("CTEST_PARALLEL_LEVEL", "1")
            # --no-tests=ignore: the upstream tests register only when the
            # system DocBook DTD/XSL data is present (patch 0006); a runner
            # without the data has a legitimately empty suite.
            with test_env.vars(self).apply():
                self.run(
                    'ctest --test-dir "{}" --output-on-failure '
                    "--no-tests=ignore".format(self.build_folder)
                )
        else:
            self.output.info(
                "cross build: the DocBook autotests execute on the HarmonyOS "
                "device where the DocBook data is installed"
            )

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "KF6DocTools")
        self.cpp_info.set_property("cmake_target_name", "KF6::DocTools")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
