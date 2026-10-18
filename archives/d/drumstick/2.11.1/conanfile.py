#!/usr/bin/env python3
"""Conan recipe for drumstick 2.11.1 on HarmonyOS PC.

Drumstick is a set of MIDI C++ libraries for Qt:
  - Drumstick::ALSA     Linux-only C++/Qt wrapper around the ALSA Sequencer API
  - Drumstick::File     multiplatform SMF (.mid/.kar), RIFF RMID (.rmi) and
                        Cakewalk (.wrk) file I/O
  - Drumstick::RT       realtime MIDI I/O library with pluggable backends
  - Drumstick::Widgets  MIDI GUI widgets (virtual piano keyboard, dialogs)

Key adaptations (see notes.md / knowledge):
  - The upstream CMake gates the ALSA sequencer support on
    ${CMAKE_SYSTEM} MATCHES "Linux".  On HarmonyOS CMake reports
    CMAKE_SYSTEM_NAME=HarmonyOS, so without a patch the libdrumstick-alsa
    target (kmetronome's dependency) would silently be skipped.  Patch 0001
    makes the two ALSA gates also accept CMAKE_SYSTEM_NAME=HarmonyOS
    (build-system portability condition, no __OHOS__ platform macro).
  - Qt6 is consumed from the published qtbase/6.11.1 package (Core, Gui,
    Widgets, Network, Test, Xml), plus qt5compat/6.11.1 for Qt6::Core5Compat
    (QTextCodec used by the File library). The widgets .qm translations are
    skipped on HarmonyOS (see patch 0004), so qttools is not required.
  - ALSA is resolved through pkg-config (alsa-lib/1.2.16.1 ships a relocatable
    alsa.pc); PKG_CONFIG_PATH is pointed at the alsa-lib package folder.
  - Optional backends (PulseAudio, PipeWire, FluidSynth, Sonivox, DBus) are
    disabled: they are not needed by consumers (kmetronome only needs
    Drumstick::ALSA) and would require additional unpublished dependencies.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class DrumstickConan(ConanFile):
    name = "drumstick"
    version = "2.11.1"
    description = (
        "MIDI C++ libraries for Qt: ALSA sequencer wrapper (Drumstick::ALSA), "
        "SMF/RMID/WRK file I/O (Drumstick::File), realtime MIDI I/O "
        "(Drumstick::RT) and MIDI widgets (Drumstick::Widgets)"
    )
    license = "GPL-3.0-only"
    homepage = "https://drumstick.sourceforge.io"
    url = "https://github.com/pedrolcl/drumstick"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Gui/Widgets/Network/Test/Xml come from the plain qtbase
        # package (its own relocatable Qt6Config.cmake, cmake_find_mode=none).
        # DBus is intentionally NOT required (USE_DBUS=OFF).
        self.requires("qtbase/6.11.1")
        # Qt6::Core5Compat (QTextCodec) used by libdrumstick-file.
        self.requires("qt5compat/6.11.1")
        # Qt6::LinguistTools is NOT required: patch 0004 skips the widgets
        # .qm translations on HarmonyOS (lrelease/lupdate host tools cannot
        # run on the OHOS build host).
        # ALSA sequencer (libasound) resolved via pkg-config alsa.pc.
        self.requires("alsa-lib/1.2.16.1")

    def validate(self):
        if self.settings.os not in ("OHOS",):
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration(
                "drumstick/2.11.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # qtbase / qt5compat ship their own relocatable Qt6*.cmake
        # configs (cmake_find_mode="none"); expose each package folder so
        # find_package(Qt6) and find_package(Qt6Core5Compat) resolve from
        # the installed configs.
        prefix_paths = []
        for dep_name in ("qtbase", "qt5compat", "alsa-lib"):
            dep_node = self.dependencies.get(dep_name)
            if dep_node is None:
                continue
            package_folder = getattr(dep_node, "package_folder", None)
            if package_folder:
                prefix_paths.append(str(package_folder))
        if prefix_paths:
            tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefix_paths)

        qtbase_folder = self.dependencies["qtbase"].package_folder
        qt5compat_folder = self.dependencies["qt5compat"].package_folder
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_folder, "lib", "cmake", "Qt6"
        )
        # Platform/HarmonyOS.cmake (include Linux.cmake) lives under qtbase's
        # cmake platforms dir; without it CMake treats HarmonyOS as an unknown
        # platform.
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qtbase_folder, "lib", "cmake", "Qt6", "platforms"
        )
        # qt5compat uses the default CMakeDeps find mode, so CMakeDeps
        # generates Qt6Core5CompatConfig.cmake whose find_dependency(qtbase)
        # fails because qtbase ships its own relocatable config
        # (cmake_find_mode=none, no qtbaseConfig.cmake). Point the *_DIR
        # cache variable at the package's own installed config so
        # find_package(Qt6Core5Compat) loads the real targets (same
        # workaround as libdrumstick/2.10.0).
        tc.cache_variables["Qt6Core5Compat_DIR"] = os.path.join(
            qt5compat_folder, "lib", "cmake", "Qt6Core5Compat"
        )

        # ── drumstick build options ──
        tc.variables["BUILD_ALSA"] = "ON"
        tc.variables["BUILD_FILE"] = "ON"
        tc.variables["BUILD_RT"] = "ON"
        tc.variables["BUILD_WIDGETS"] = "ON"
        tc.variables["BUILD_UTILS"] = "OFF"      # library-only package (R38)
        tc.variables["BUILD_DOCS"] = "OFF"
        tc.variables["BUILD_FRAMEWORKS"] = "OFF"
        tc.variables["STATIC_DRUMSTICK"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 关键：跳过 CMake 的 RPATH 处理（CMAKE_SKIP_RPATH=TRUE）。
        # cmake.install() 默认会用 patchelf 清理/重写安装后库的 RPATH，
        # 这会破坏 OHOS 动态加载器所需的 ELF 结构（.rela 段被重排），
        # 导致安装后（conan package 内）的 libdrumstick-*.so 无法加载
        # （test_package 报 "Error loading shared library ... Permission
        # denied"）。关闭后安装的库保持 build 产物原样，运行时依赖由
        # build()/test() 显式注入的 LD_LIBRARY_PATH 提供
        # （同 libdrumstick/2.10.0 先例）。
        tc.variables["CMAKE_SKIP_RPATH"] = "TRUE"
        # Optional backends: keep the dependency closure minimal.
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["USE_NETWORK"] = "ON"       # Qt6Network from qtbase
        tc.variables["USE_PULSEAUDIO"] = "OFF"
        tc.variables["USE_PIPEWIRE"] = "OFF"
        tc.variables["USE_FLUIDSYNTH"] = "OFF"
        tc.variables["USE_SONIVOX"] = "OFF"
        # Upstream CTest suite (alsaTest1, fileTest1/2/3, rtTest, widgetsTest).
        tc.variables["BUILD_TESTING"] = "ON"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        # pkg_check_modules(ALSA ...) needs PKG_CONFIG_PATH pointing at each
        # dependency's lib/pkgconfig directory (alsa.pc / QtCore.pc).
        pkg_config_paths = []
        for dep_name in ("alsa-lib", "qtbase"):
            dep_node = self.dependencies.get(dep_name)
            if dep_node is None:
                continue
            package_folder = getattr(dep_node, "package_folder", None)
            if package_folder:
                pc_dir = os.path.join(str(package_folder), "lib", "pkgconfig")
                if os.path.isdir(pc_dir):
                    pkg_config_paths.append(pc_dir)
        for pc_dir in pkg_config_paths:
            self.buildenv_info.prepend_path("PKG_CONFIG_PATH", pc_dir)

        # Qt build tools (moc/uic/rcc/lrelease) and the upstream test binaries
        # are OHOS ELF executables that need libc++_shared.so (OHOS SDK llvm
        # lib) and the qtbase shared libraries at runtime (same requirement as
        # libdrumstick/2.10.0).  Inject both into the build/run environment.
        # SDK 路径允许经 OHOS_SDK_LLVM_LIB 环境变量覆盖（CI/机器相关路径不
        # 落入配方，默认值仅作本地兜底，与 test_package 一致）。
        sdk_llvm_lib = os.environ.get(
            "OHOS_SDK_LLVM_LIB",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib",
        )
        # CMAKE_SKIP_RPATH=TRUE disables the build-tree RUNPATH, so the CTest
        # binaries can no longer locate the freshly-built libdrumstick-*.so
        # from the build tree on their own — the build lib dir must be on
        # LD_LIBRARY_PATH for cmake.test() (same as libdrumstick/2.10.0).
        build_lib = os.path.join(self.build_folder, "lib")
        ld_paths = [
            build_lib,
            os.path.join(qtbase_folder, "lib"),
            os.path.join(sdk_llvm_lib, "aarch64-linux-ohos"),
            os.path.join(sdk_llvm_lib, "aarch64-linux-ohos", "c++"),
        ]
        for path in ld_paths:
            self.buildenv_info.append_path("LD_LIBRARY_PATH", path)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream CTest suite. Some tests (alsaTest2 / rtTest on a Linux-like
        # system) are only registered when /dev/snd exists; on this OHOS
        # device they are not registered and are reported in notes.md.
        # NOTE: this recipe's own buildenv_info does NOT apply to its own
        # build, so the loader path (freshly built libdrumstick-*.so, Qt6
        # shared libs, OHOS libc++_shared.so) must be re-applied explicitly
        # for the ctest run, otherwise every test fails at relocation.
        qtbase_folder = self.dependencies["qtbase"].package_folder
        sdk_llvm_lib = os.environ.get(
            "OHOS_SDK_LLVM_LIB",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib",
        )
        env = Environment()
        for path in (
            os.path.join(self.build_folder, "lib"),
            os.path.join(qtbase_folder, "lib"),
            os.path.join(sdk_llvm_lib, "aarch64-linux-ohos"),
            os.path.join(sdk_llvm_lib, "aarch64-linux-ohos", "c++"),
        ):
            env.append_path("LD_LIBRARY_PATH", path)
        with env.vars(self).apply():
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Drumstick installs its own complete, relocatable CMake package files
        # (lib/cmake/drumstick/drumstick-config.cmake + per-component
        # drumstick-{alsa,file,rt,widgets}-config.cmake with the
        # Drumstick::* namespace). Reuse them so consumers get the upstream
        # targets via find_package(Drumstick COMPONENTS ALSA ...).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        # Conan-level component metadata (targets resolved from the installed
        # upstream configs; these entries keep the Conan graph/dependency info
        # consistent for consumers that inspect cpp_info directly).
        self.cpp_info.libs = [
            "drumstick-alsa", "drumstick-rt", "drumstick-file",
            "drumstick-widgets",
        ]

        alsa = self.cpp_info.components["alsa"]
        alsa.libs = ["drumstick-alsa"]
        alsa.set_property("cmake_target_name", "Drumstick::ALSA")

        file_comp = self.cpp_info.components["file"]
        file_comp.libs = ["drumstick-file"]
        file_comp.set_property("cmake_target_name", "Drumstick::File")

        rt = self.cpp_info.components["rt"]
        rt.libs = ["drumstick-rt"]
        rt.set_property("cmake_target_name", "Drumstick::RT")

        widgets = self.cpp_info.components["widgets"]
        widgets.libs = ["drumstick-widgets"]
        widgets.requires = ["rt"]
        widgets.set_property("cmake_target_name", "Drumstick::Widgets")
