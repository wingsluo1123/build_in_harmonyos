#!/usr/bin/env python3
"""Conan test_package for libksane — consumer-side verification.

Links the installed KSaneWidgets6 target, constructs the widget offscreen and
runs functional assertions on the public no-device API (no scanner hardware or
root access needed).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, save


class LibksaneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        # The installed KSaneWidgets6Config.cmake chains through
        # find_dependency(Qt6Widgets). The dependencies use
        # cmake_find_mode=none, so CMakeDeps does not add their lib/cmake
        # dirs; expose every dependency path manually (ksanecore 26.04.0
        # test_package precedent).
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _make_link_farm(self):
        """Mirror every dependency shared library into a farm directory.

        The published kconfig package ships libKF6ConfigGui.so with a
        build-tree-relative DT_NEEDED entry ("../../bin/libKF6ConfigCore.so")
        which the OHOS loader resolves against the process CWD; the referenced
        directory does not exist in the package. Provide both bin/ and lib/
        levels of the farm so that entry resolves (lokalize 26.04.0 /
        alligator 26.04.0 precedent).
        """
        farms = []
        for sub in ("bin", "lib"):
            farm = os.path.join(self.build_folder, "run-farm", sub)
            try:
                os.makedirs(farm, exist_ok=True)
                farms.append(farm)
            except OSError as exc:
                self.output.warning(f"link farm mkdir failed ({farm}): {exc}")
        if not farms:
            return []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for layout_dir in ("lib", "bin"):
                src_dir = os.path.join(dep.package_folder, layout_dir)
                if not os.path.isdir(src_dir):
                    continue
                for name in os.listdir(src_dir):
                    if not name.endswith(".so"):
                        continue
                    source = os.path.join(src_dir, name)
                    for farm in farms:
                        link = os.path.join(farm, name)
                        if os.path.lexists(link):
                            continue
                        try:
                            os.symlink(source, link)
                        except OSError as exc:
                            self.output.warning(
                                f"link farm entry {name} failed: {exc}"
                            )
        return farms

    def _sane_test_backend(self):
        """Locate the SANE virtual scanner backend used by the scan-flow test.

        The test backend (libsane-test) is the official SANE device simulator:
        it performs a real SANE transfer and returns a real image, so the
        end-to-end consumer flow runs without physical scanner hardware.
        """
        sane = self.dependencies.get("sane-backends")
        if not sane or not sane.package_folder:
            return None, None
        lib = os.path.join(sane.package_folder, "lib", "sane", "libsane-test.so.1")
        conf = os.path.join(sane.package_folder, "etc", "sane.d", "test.conf")
        return (lib if os.path.isfile(lib) else None,
                conf if os.path.isfile(conf) else None)

    def test(self):
        if not can_run(self):
            return
        # CWD two levels below run-farm so that the build-tree-relative
        # "../../bin/<lib>" DT_NEEDED entries of the published KF6 libraries
        # resolve into the farm.
        run_dir = os.path.join(self.build_folder, "run-farm", "x", "y")
        os.makedirs(run_dir, exist_ok=True)
        farm_dirs = self._make_link_farm()
        env = Environment()
        # Path semantics: append_path joins with os.pathsep. Plain append()
        # would join a list with a space and silently produce a single invalid
        # path entry.
        env.append_path("LD_LIBRARY_PATH", farm_dirs)
        env.append_path("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        env.append_path("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib", "sane")
            for p in self.dependencies.values()
            if p.package_folder
        ])

        # SANE virtual scanner for the end-to-end consumer flow.
        backend_lib, backend_conf = self._sane_test_backend()
        sane_conf_dir = os.path.join(self.build_folder, "sane.d")
        os.makedirs(sane_conf_dir, exist_ok=True)
        if backend_conf:
            copy(self, os.path.basename(backend_conf), src=os.path.dirname(backend_conf),
                 dst=sane_conf_dir)
        save(self, os.path.join(sane_conf_dir, "dll.conf"), "test\n")
        env.define("SANE_CONFIG_DIR", sane_conf_dir)
        if backend_lib:
            # The published sane-backends package hard-codes its backend search
            # path to /lib/sane, which does not exist on OHOS (the configured
            # prefix was "/"), so the dll loader cannot load any backend and no
            # device is ever enumerated. Preload the test backend instead: a
            # SANE backend is a complete libsane implementation exporting
            # sane_init()/sane_open()/sane_read(), so it interposes over the
            # staged libsane.so and drives a real transfer. Test-environment
            # only; no shipped artifact is modified.
            env.define("LD_PRELOAD", backend_lib)
            self.output.info(f"SANE test backend: {backend_lib}")
        else:
            self.output.warning(
                "libsane-test.so.1 not found in sane-backends: the scan-flow "
                "end-to-end test cannot open a virtual scanner"
            )
        env.define("KSANE_TEST_ARTIFACT_DIR", os.path.join(self.build_folder, "artifacts"))
        os.makedirs(os.path.join(self.build_folder, "artifacts"), exist_ok=True)
        # The Qt offscreen platform plugin lives in the qtbase package.
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            env.append_path("QT_PLUGIN_PATH", [
                os.path.join(qtbase.package_folder, "plugins"),
                os.path.join(qtbase.package_folder, "lib", "plugins"),
            ])
        env.define("QT_QPA_PLATFORM", "offscreen")
        # CI workers run inside the OHOS sandbox whose LD_LIBRARY_PATH
        # contains an incompatible libc++_shared.so shadowing the compatible
        # one; prepend /system/lib64 so test executables resolve the
        # compatible libc++ first (ksanecore 26.04.0 precedent).
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            # The OHOS SDK ships libxml2.so.16 needed by lld; the versioned
            # directory is discovered instead of pinned (ksanecore 26.04.0
            # precedent pins 26.0.0.18, which breaks on other worker SDKs).
            for sdk_lib in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                if os.path.isdir(sdk_lib):
                    env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        with env.vars(self).apply():
            bindir = self.cpp.build.bindirs[0]
            if not os.path.isabs(bindir):
                bindir = os.path.join(self.build_folder, bindir)
            # 1) no-device public API assertions
            self.run(os.path.join(bindir, "test_libksane"), cwd=run_dir, env="conanrun")
            # 2) end-to-end scanner workflow against the SANE virtual backend
            self.run(os.path.join(bindir, "test_scan_flow"), cwd=run_dir, env="conanrun")
