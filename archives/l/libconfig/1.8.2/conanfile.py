"""libconfig's complete C/C++ CMake build and upstream suite."""
import io
import os
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, get

from ohos_sign import sign_elf


class LibconfigConan(ConanFile):
    name = "libconfig"
    version = "1.8.2"
    description = "Structured configuration processing with C and C++ APIs"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/hyperrealm/libconfig"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports = "ohos_sign.py"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("LIBCONFIG_SOURCE_ARCHIVE")
        if local:
            archive = Path(local).resolve(strict=True)
            if not archive.is_file():
                raise ConanException("local source archive must be a regular file")
            source.update(url=archive.as_uri(), filename=archive.name)
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_CXX"] = True
        tc.variables["BUILD_TESTS"] = True
        if str(self.settings.os) == "OHOS":
            # HarmonyOS has no stock CMake platform module: without a
            # SONAME, the linker records ../out/libconfig.so in DT_NEEDED.
            for language in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"] = ":"
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os) == "OHOS":
            for p in sorted(Path(self.build_folder, "out").iterdir()):
                if p.is_file() and not p.is_symlink() and p.read_bytes()[:4] == b"\x7fELF":
                    sign_elf(p)
        if can_run(self):
            output = io.StringIO()
            runtime = Environment()
            # VirtualRunEnv covers dependencies, not this not-yet-packaged
            # library. CTest changes cwd to source/tests; use the computed
            # build-tree output directory only during this test invocation.
            if str(self.settings.os) == "OHOS" and self.options.shared:
                runtime.prepend_path("LD_LIBRARY_PATH", str(Path(self.build_folder, "out")))
            try:
                with runtime.vars(self).apply():
                    self.run('ctest --test-dir "{}" --output-on-failure -V --no-tests=error'.format(self.build_folder), stdout=output, env="conanrun")
            finally:
                self.output.info(output.getvalue())
            text = output.getvalue()
            cases = re.findall(r"TT_SUITE_TEST\(LibConfigTests,\s*(\w+)\)", Path(self.source_folder, "tests/tests.c").read_text())
            if len(cases) != 16 or "16 tests; 16 passed, 0 failed" not in text:
                raise ConanException("upstream tinytest case inventory/result mismatch")
            self.output.info("UPSTREAM_16_OF_16_PASS")

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            for p in sorted(Path(self.package_folder, "lib").glob("*.so*")):
                if p.is_file() and not p.is_symlink():
                    sign_elf(p)
        copy(self, "COPYING.LIB", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libconfig")
        self.cpp_info.set_property("cmake_target_name", "libconfig::libconfig")
        for key, library, target, pkg in (("c", "config", "libconfig::config", "libconfig"),
                                          ("cpp", "config++", "libconfig::config++", "libconfig++")):
            component = self.cpp_info.components[key]
            component.libs = [library]
            component.set_property("cmake_target_name", target)
            component.set_property("pkg_config_name", pkg)
            if not self.options.shared:
                component.defines = ["LIBCONFIG_STATIC"]
                if key == "cpp": component.defines.append("LIBCONFIGXX_STATIC")
