#!/usr/bin/env python3
"""Conan test_package for juk 26.04.0.

juk is an application package (no exported library or headers), so the L1 test
has two halves:

  * a real CMake consumer target (test.cpp) that exercises the library chain
    juk is linked against - the KF6 config layer - proving the published
    dependency graph is consumable from a fresh project;
  * artefact-level checks in test(): the installed `juk` binary must exist and
    actually run (--version), and its DT_NEEDED must contain libKF6KIOWidgets.so
    and libKF6KIOCore.so, which is what forces the kio/6.14.0 choice recorded in
    the recipe docstring (kio/6.26.0 is KIOCORE_ONLY and ships no KIOWidgets).

Runtime-linking notes (E537, accessibility 26.04.3 / alligator 26.04.0
precedent): the published KF6 libraries carry DT_NEEDED entries recorded while
they were linked, of two shapes the OHOS loader cannot resolve as-is:

  * build-tree-relative entries ("../../bin/libKF6ConfigCore.so") resolve
    against the process CWD, so the binary is started from a scratch directory
    whose ../../bin reaches a link farm of every dependency shared library;
  * absolute entries pointing into another builder's conan home are symlinked
    back to the real library of the matching package before the run.
"""
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class JukTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")

    def layout(self):
        cmake_layout(self)

    def _env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("lib", "bin"):
                    env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, rel))
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, rel))
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

        # KF6ConfigConfig.cmake chains find_dependency() into the other KF6
        # packages and Qt6; expose every dependency's cmake dirs (kio 6.26.0
        # test_package precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(dep.package_folder)
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(dep.package_folder)
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(dep.package_folder)
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _find_readelf(self):
        for cand in (
            "readelf",
            "/data/service/hnp/bin/readelf",
            "/usr/bin/readelf",
            "/bin/readelf",
        ):
            exe = shutil.which(cand) or cand
            try:
                subprocess.run([exe, "--version"], capture_output=True, timeout=20)
                return exe
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _collect_libs(self):
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for layout_dir in ("lib", "bin"):
                    lib_dir = os.path.join(dep.package_folder, layout_dir)
                    if os.path.isdir(lib_dir):
                        lib_dirs.append(lib_dir)
        return lib_dirs

    def _make_scratch(self, lib_dirs):
        """Fresh CWD + link farm for the run (kept out of the recipe sources).

        Layout: <scratch>/a/b is the run CWD and <scratch>/bin is the farm, so a
        ../../bin/... DT_NEEDED entry from the CWD reaches the farm.
        """
        scratch = tempfile.mkdtemp(prefix="juk-test-")
        farm = os.path.join(scratch, "bin")
        cwd = os.path.join(scratch, "a", "b")
        os.makedirs(farm, exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        for lib_dir in lib_dirs:
            for name in os.listdir(lib_dir):
                if not name.endswith(".so"):
                    continue
                link = os.path.join(farm, name)
                if not os.path.lexists(link):
                    try:
                        os.symlink(os.path.join(lib_dir, name), link)
                    except OSError as exc:
                        self.output.warning("link farm entry {} failed: {}".format(name, exc))
        return cwd, farm

    def _materialize_abs_deps(self, lib_dirs, readelf):
        """Symlink every missing absolute dependency path back to its library."""
        if not readelf:
            self.output.warning("readelf not found; absolute DT_NEEDED materialization skipped")
            return
        seen = set()
        for lib_dir in lib_dirs:
            for name in sorted(os.listdir(lib_dir)):
                if not name.endswith(".so") or name in seen:
                    continue
                seen.add(name)
                lib_path = os.path.join(lib_dir, name)
                try:
                    rd = subprocess.run(
                        [readelf, "-d", lib_path],
                        capture_output=True, text=True, timeout=60,
                    ).stdout
                except (OSError, subprocess.SubprocessError):
                    continue
                for match in re.finditer(r"Shared library: \[(/[^]]+\.so)\]", rd):
                    abs_path = match.group(1)
                    if os.path.exists(abs_path):
                        continue
                    fname = os.path.basename(abs_path)
                    for cand_dir in lib_dirs:
                        cand = os.path.join(cand_dir, fname)
                        if os.path.exists(cand):
                            try:
                                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                                if not os.path.lexists(abs_path):
                                    os.symlink(cand, abs_path)
                            except OSError as exc:
                                self.output.warning(
                                    "DT_NEEDED symlink fail {}: {}".format(abs_path, exc)
                                )
                            break

    def build(self):
        cmake = CMake(self)
        with self._env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(pkg, "bin", "juk")
        assert os.path.isfile(binary), "missing artifact: bin/juk"

        desktop_dir = os.path.join(pkg, "share", "applications")
        assert os.path.isdir(desktop_dir), "missing artifact: share/applications"
        assert any(name.startswith("org.kde.juk") for name in os.listdir(desktop_dir)), (
            "missing desktop entry org.kde.juk.desktop"
        )

        lib_dirs = self._collect_libs()
        readelf = self._find_readelf()
        self._materialize_abs_deps(lib_dirs, readelf)
        scratch_cwd, farm = self._make_scratch(lib_dirs)

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(lib_dirs + [farm] + [
            "/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk",
        ]))
        plugin_paths = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                    plugins_path = os.path.join(dep.package_folder, plugins_dir)
                    if os.path.isdir(plugins_path):
                        plugin_paths.append(plugins_path)
        if plugin_paths:
            env.define("QT_PLUGIN_PATH", ":".join(plugin_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        home = os.path.join(scratch_cwd, "test-home")
        xdg_runtime = os.path.join(scratch_cwd, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

        with env.vars(self).apply():
            # R34: real execution of the packaged application. CWD is the
            # scratch tree so build-tree-relative DT_NEEDED entries (E537)
            # resolve against the link farm.
            self.run('"{}" --version'.format(binary), cwd=scratch_cwd)
            # The KIO widget libraries must be recorded in DT_NEEDED: this is
            # the machine-checkable proof that the full kio build was needed.
            for symbol in ("libKF6KIOWidgets", "libKF6KIOCore", "libKF6KIOFileWidgets"):
                self.run(
                    '"{}" -d "{}" | grep -q {}'.format(readelf or "readelf", binary, symbol)
                )
