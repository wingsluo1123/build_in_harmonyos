import os
from pathlib import Path
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv


# Independent expected inventory; product inputs exclude test-only sources.
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


def verify_hap_sources(folder):
    expected = set(HAP_SOURCES) | {"test-support/core_cases.c", "test-support/core_cases.h"}
    actual = {path.relative_to(folder).as_posix()
              for path in Path(folder).rglob("*") if path.is_file()}
    if actual != expected:
        # Counts only: unexpected paths may contain local signing or device data.
        raise ConanException(
            "HAP source inventory mismatch: missing={}, unexpected={}".format(
                len(expected - actual), len(actual - expected)))
    return len(HAP_SOURCES)


class WvkbdConsumer(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"
    virtualbuildenv = False

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        test_support_dir = os.path.join(
            self.dependencies["wvkbd"].package_folder, "share", "wvkbd", "0.15", "test-support")
        toolchain = CMakeToolchain(self)
        toolchain.variables["WVKBD_TEST_SUPPORT_DIR"] = test_support_dir.replace("\\", "/")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        with VirtualBuildEnv(self).vars().apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])

    def test(self):
        count = verify_hap_sources(Path(self.dependencies["wvkbd"].package_folder) /
                                   "share" / "wvkbd" / "0.15")
        self.output.info("HAP_SOURCE_INVENTORY_PASS count={}".format(count))
        if self.settings.os == "OHOS":
            prefix = "user.wvkbd:"
            fields = ("hdc", "hdc_serial", "sdk", "hvigor", "node", "base_sdk", "signing_config",
                      "ime_hap", "editor_hap")
            values = {field: self.conf.get(prefix + field, default=os.environ.get("WVKBD_" + field.upper(), ""))
                      for field in fields}
            if not any(values.values()):
                self.output.warning("SKIP device execution: no user.wvkbd:* device configuration; no device pass claimed")
                return
            env = os.environ.copy()
            for field, value in values.items():
                env["WVKBD_" + field.upper()] = str(value)
            env["WVKBD_GENERATORS"] = str(self.generators_folder)
            libraries = list(Path(self.build_folder).rglob("libwvkbd_test_consumer.a"))
            if len(libraries) != 1:
                raise ConanException("Expected one Conan-built device consumer archive")
            env["WVKBD_CONSUMER_LIBRARY"] = str(libraries[0])
            env["WVKBD_PACKAGE_ROOT"] = str(Path(self.dependencies["wvkbd"].package_folder) /
                                              "share" / "wvkbd" / "0.15")
            result = subprocess.run([sys.executable, str(Path(self.source_folder) /
                                    "run_harmonyos_device_test.py")], env=env, check=False)
            if result.returncode:
                raise ConanException("HarmonyOS device acceptance failed; no device pass claimed")
        elif can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
        else:
            self.output.warning("SKIP consumer execution: target cannot run on this build host")
