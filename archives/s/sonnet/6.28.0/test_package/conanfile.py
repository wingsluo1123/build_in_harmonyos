#!/usr/bin/env python3
"""Conan test_package for sonnet 6.28.0.

Consumer-level verification of the published package:
  - KF6::SonnetCore / KF6::SonnetUi resolve through the installed
    KF6SonnetConfig.cmake (which pulls Qt6Core/Qt6Widgets and includes
    KF6SonnetTargets.cmake);
  - the Speller/Settings/GuessLanguage APIs work in the shipped
    no-backend configuration (the trigram language model is embedded in
    KF6SonnetCore by the in-tree parsetrigrams6 run);
  - the widgets Highlighter constructs over a QTextEdit;
  - the org.kde.sonnet QML module loads inside a QQmlEngine and its
    SpellcheckHighlighter / Settings types instantiate;
  - the packaged parsetrigrams6 CLI tool runs over a small word corpus.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SonnetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        # KF6SonnetConfig.cmake does find_dependency(Qt6Core/Qt6Widgets) and
        # the QML case imports QtQuick plus org.kde.sonnet from the runtime
        # tree; Qt6Quick pulls Qt6::ShaderTools from qtshadertools.
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtshadertools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)

        sn_pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qtbase = self.dependencies.get("qtbase")
        qtdeclarative = self.dependencies.get("qtdeclarative")
        qtshadertools = self.dependencies.get("qtshadertools")

        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        cmake_prefixes = []
        qt_prefixes = []
        if sn_pkg:
            cmake_prefixes.append(os.path.join(sn_pkg.package_folder, "lib", "cmake"))
        if qtbase:
            qt_pkg = qtbase.package_folder
            cmake_prefixes.append(os.path.join(qt_pkg, "lib", "cmake"))
            qt_prefixes.append(qt_pkg)
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        for dep in (qtdeclarative, qtshadertools):
            if dep:
                folder = dep.package_folder
                cmake_prefixes.append(os.path.join(folder, "lib", "cmake"))
                qt_prefixes.append(folder)
        for prefix in dict.fromkeys(cmake_prefixes):
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{prefix}")')
        if qt_prefixes:
            joined = ";".join(dict.fromkeys(qt_prefixes))
            # Qt6Config.cmake (from qtbase) resolves Qt6Qml/Qt6Quick
            # components relative to its own prefix only, so the split
            # package roots must be advertised as additional Qt prefixes.
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = joined
            lines.append(
                'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                f'"{joined}" CACHE STRING '
                '"Additional directories where find(Qt6 ...) components are searched" FORCE)'
            )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def _sdk_llvm_libdir(self):
        # The OHOS SDK root is environment specific, so prefer the llvm/lib
        # directory implied by the profile's compiler and fall back to globbing
        # the installed SDK. The version stays unpinned: a CI image ships
        # whatever SDK release it was built with.
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        for candidate in dict.fromkeys(candidates):
            if os.path.isdir(candidate):
                return candidate
        return ""

    def _build_env(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory and may not find it via the ambient
        # LD_LIBRARY_PATH. The dependency lib dirs are needed because the
        # build runs Qt tools (moc/rcc/qmltyperegistrar) packaged as binaries.
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        with self._build_env().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _locate_tool(self, prefix, name):
        candidates = [
            os.path.join(prefix, "bin", name),
            os.path.join(prefix, "lib", "libexec", "kf6", name),
            os.path.join(prefix, "libexec", "kf6", name),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        for root, _dirs, files in os.walk(prefix):
            if name in files:
                return os.path.join(root, name)
        raise ConanException(f"Cannot locate {name} inside {prefix}")

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefix = dep.package_folder
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "bin"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "lib", "plugins"))
                for rel in ("qml", "lib/qml", "share/qml"):
                    env.prepend_path("QML2_IMPORT_PATH", os.path.join(prefix, rel))
                    env.prepend_path("QML_IMPORT_PATH", os.path.join(prefix, rel))
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(qtbase.package_folder, "plugins", "platforms"),
            )

        # The OHOS sandbox is not writable for the test user, so isolate
        # HOME/XDG under the build folder (Sonnet reads/writes its settings
        # through QSettings below XDG_CONFIG_HOME; the CLI case writes its
        # corpus below HOME).
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(test_home, "runtime")
        xdg_config = os.path.join(test_home, "config")
        for directory in (test_home, xdg_runtime, xdg_config):
            os.makedirs(directory, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CONFIG_HOME", xdg_config)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, "cache"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, "data"))

        sn_pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if sn_pkg:
            env.define(
                "PARSETRIGRAMS6_BIN",
                self._locate_tool(sn_pkg.package_folder, "parsetrigrams6"),
            )

        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            executable = os.path.join(self.cpp.build.bindirs[0], "test_sonnet")
            self.run(executable, env="conanrun")
