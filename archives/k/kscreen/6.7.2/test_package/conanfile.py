#!/usr/bin/env python3
"""Conan test_package for kscreen 6.7.2.

Real consumer assertions (no stub test), executed on device inside
`conan create`:

1. test_kscreen_plugin (consumer C++, real API usage): dlopens the packaged
   kded plugin through QPluginLoader at the exact install layout the kded
   daemon consumes (lib/plugins/kf6/kded/kscreen.so) and asserts load(),
   factory instantiation and the embedded JSON metadata
   (IID org.kde.KPluginFactory, KPlugin.Version 6.7.2,
   X-KDE-Kded-autoload true). This exercises the real Qt plugin ABI and the
   SONAME-less KF6 dependency resolution (libKF6Screen/libKF6DBusAddons/
   libKF6CoreAddons/libKF6I18n) at runtime.
2. The same binary executes the packaged kscreen-console (--help) with the
   offscreen QPA platform and asserts exit 0 plus usage output — the
   executable E2E of the package (no display, no session bus needed).
3. _elf_artifact_checks (OHOS host only, readelf): both shipped ELFs have
   only bare-basename DT_NEEDED (no absolute Conan cache paths, E537); the
   plugin DT_NEEDED carries the expected KF6 components and none of the
   gated ones (no XmlGui / KCMUtils / Svg / Crash / Plasma / LayerShellQt /
   WaylandClient); the console keeps KF6::WindowSystem; the gated
   artifacts (HDR calibrator, KCM/plasma plugin files) are absent.
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KscreenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt6::Core (QPluginLoader/QProcess); pin the exact Qt build the
        # package links against so plugin and host share one Qt ABI.
        self.requires("qtbase/6.11.1.2", override=True)

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.generate()

        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # OHOS SDK lld depends on libxml2.so.16 shipped in the SDK llvm/lib
        # directory; prepend it so CMake TryCompile can link
        # (kcrash/kconfig 6.26.0 precedent). /system/lib64 is prepended
        # last so it wins over the ambient sandbox libc++_shared.so, same
        # relative order as the main recipe's _cmake_build_env().
        env = Environment()
        for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                # prepend_path, not append: Conan 2 append() joins with a
                # blank space by default; only *_path variants join with
                # os.pathsep (same call as the main recipe's
                # _library_runtime_env()).
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                # The offscreen QPA plugin (qtbase plugins/) and the
                # packaged plugin's KF6 runtime both resolve through the
                # recorded dependency directories.
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        tested = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if tested and tested.package_folder:
            env.define("KS_TESTED_PACKAGE_FOLDER", tested.package_folder)
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH can shadow the compatible
            # libc++_shared.so; /system/lib64 must win (kconfig/kcrash
            # 6.26.0 precedent). Prepend it AFTER the llvm dirs so it
            # stays leftmost, matching the main recipe's
            # _cmake_build_env() order.
            for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def _elf_artifact_checks(self):
        """OHOS-specific artifact assertions: patch 0001 gating (Plasma/HDR
        off), patch 0002 relocatable link + XmlGui drop, real install
        layout."""
        tested = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if not tested or not tested.package_folder:
            self.output.warning("tested package folder not found; skipping ELF artifact checks")
            return
        pkg = tested.package_folder

        readelf = None
        candidates = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/llvm-readelf"))
        candidates += ["/data/service/hnp/bin/llvm-readelf", "/storage/Users/currentUser/.harmonybrew/bin/readelf"]
        for cand in candidates:
            if os.path.isfile(cand):
                readelf = cand
                break
        assert readelf, "no readelf/llvm-readelf found on this worker"

        def needed_of(path):
            proc = subprocess.run([readelf, "-d", path], capture_output=True, text=True)
            # A readelf tool failure must not surface as a phantom
            # "missing DT_NEEDED" packaging defect.
            assert proc.returncode == 0,                 f"readelf -d failed on {path} (rc={proc.returncode}): {proc.stderr.strip()}"
            return [line.split("[")[-1].rstrip("]") for line in proc.stdout.splitlines() if "(NEEDED)" in line]

        plugin = next((p for p in (os.path.join(pkg, "lib", "plugins", "kf6", "kded", "kscreen.so"),
                                   os.path.join(pkg, "plugins", "kf6", "kded", "kscreen.so"))
                       if os.path.isfile(p)), None)
        assert plugin, "packaged kded plugin kscreen.so not found"
        p_needed = needed_of(plugin)
        expected = ("libKF6Screen", "libKF6CoreAddons", "libKF6DBusAddons", "libKF6I18n")
        missing = [e for e in expected if not any(n.startswith(e) for n in p_needed)]
        assert not missing, f"plugin DT_NEEDED missing expected KF6 libs: {missing} (needed={p_needed})"
        abs_needed = [n for n in p_needed if n.startswith(("/", "../"))]
        assert not abs_needed, f"plugin absolute-path DT_NEEDED leak: {abs_needed}"
        gated = ("libKF6XmlGui", "libKF6KCMUtils", "libKF6Svg", "libKF6Crash",
                 "libPlasma", "libLayerShellQt", "libQt6WaylandClient")
        bad = [n for n in p_needed if n.startswith(gated)]
        assert not bad, f"gated components leaked into plugin DT_NEEDED: {bad}"

        console = next((p for p in (os.path.join(pkg, "bin", "kscreen-console"),
                                    os.path.join(pkg, "libexec", "kscreen-console"))
                        if os.path.isfile(p)), None)
        assert console, "kscreen-console binary missing (expected in bin/)"
        c_needed = needed_of(console)
        assert any(n.startswith("libKF6WindowSystem") for n in c_needed), \
            f"console DT_NEEDED missing libKF6WindowSystem: {c_needed}"
        abs_c = [n for n in c_needed if n.startswith(("/", "../"))]
        assert not abs_c, f"console absolute-path DT_NEEDED leak: {abs_c}"

        # share/locale is upstream translation data: ki18n_install(po)
        # installs every catalog present in po/ (including the gated
        # components' catalogs) regardless of the build options, so the
        # gating checks below cover build artifacts only, not locale data.
        def _non_locale_files():
            for root, _, files in os.walk(pkg):
                if os.sep + "locale" + os.sep in root + os.sep:
                    continue
                for name in files:
                    yield os.path.join(root, name), name

        packaged = list(_non_locale_files())
        hdr = [p for p, name in packaged if "hdrcalibrator" in name]
        assert not hdr, f"HDR calibrator artifacts unexpectedly packaged: {hdr}"
        assert not os.path.isdir(os.path.join(pkg, "lib", "plugins", "plasma")), \
            "Plasma plugin directory unexpectedly packaged"
        kcm = [p for p, name in packaged if name.startswith(("kcm_", "plasma_"))]
        assert not kcm, f"Plasma/KCM plugin artifacts unexpectedly packaged: {kcm}"
        self.output.info("OHOS artifact assertions passed: relocatable DT_NEEDED, KF6 component set, gated artifacts absent")

    def test(self):
        env = self._runtime_env()
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kscreen_plugin"),
                env="conanrun",
            )
        if self.settings.os == "OHOS":
            self._elf_artifact_checks()
