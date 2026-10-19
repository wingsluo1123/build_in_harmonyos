import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


# Explicit product inputs: keep in sync with the consumer inventory assertion.
HAP_SOURCES = (
    '.gitignore',
    'AppScope/app.json5',
    'AppScope/resources/base/element/string.json',
    'AppScope/resources/base/media/app_icon.svg',
    'README.md',
    'build-profile.json5',
    'entry/build-profile.json5',
    'entry/hvigorfile.ts',
    'entry/oh-package.json5',
    'entry/src/main/cpp/CMakeLists.txt',
    'entry/src/main/cpp/types/libwvkbd_napi/index.d.ts',
    'entry/src/main/cpp/types/libwvkbd_napi/oh-package.json5',
    'entry/src/main/cpp/wvkbd_napi.cpp',
    'entry/src/main/ets/extension/InputMethodService.ts',
    'entry/src/main/ets/pages/KeyboardPanel.ets',
    'entry/src/main/module.json5',
    'entry/src/main/resources/base/element/string.json',
    'entry/src/main/resources/base/media/app_icon.svg',
    'entry/src/main/resources/base/profile/input_method_config.json',
    'entry/src/main/resources/base/profile/main_pages.json',
    'hvigor/hvigor-config.json5',
    'hvigorfile.ts',
    'hvigorw.bat',
    'oh-package.json5',
)


class WvkbdConan(ConanFile):
    name = "wvkbd"
    version = "0.15"
    package_type = "static-library"
    license = "GPL-3.0-only"
    homepage = "https://github.com/jjsullivan5196/wvkbd"
    description = "wvkbd default keyboard core and HarmonyOS system input method source"
    topics = ("keyboard", "input-method", "harmonyos")
    settings = "os", "compiler", "build_type", "arch"
    # Conan's shell activation script snapshots each variable with printenv.
    # Apply the same build environment in-process for process-limited CI workers.
    virtualbuildenv = False
    exports_sources = ("harmonyos/core/*",) + tuple(
        "harmonyos/ime_app/" + path for path in HAP_SOURCES)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            destination="upstream", strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["WVKBD_BUILD_TESTS"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        with VirtualBuildEnv(self).vars().apply():
            cmake.configure(build_script_folder=os.path.join(self.source_folder, "harmonyos", "core"))
            cmake.build()
        # Official v0.15 has no test/check target or test sources. See MANIFEST.yml.
        # The same adapted-core cases execute through test_package and the device HAP.

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", os.path.join(self.source_folder, "upstream"),
             os.path.join(self.package_folder, "licenses"))
        for path in HAP_SOURCES:
            destination = os.path.join(self.package_folder, "share", "wvkbd", str(self.version), path)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(os.path.join(self.source_folder, "harmonyos", "ime_app", path), destination)

        # Test resources are separate from product HAP inputs and public headers.
        for filename in ("core_cases.c", "core_cases.h"):
            copy(self, filename, os.path.join(self.source_folder, "harmonyos", "core", "tests"),
                 os.path.join(self.package_folder, "share", "wvkbd", str(self.version), "test-support"))

    def package_info(self):
        self.cpp_info.libs = ["wvkbd_core"]
        self.cpp_info.set_property("cmake_file_name", "wvkbd")
        self.cpp_info.set_property("cmake_target_name", "wvkbd::core")
