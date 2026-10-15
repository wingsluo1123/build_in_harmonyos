"""dyncall/dyncallback/dynload with the ELF ARM64 aggregate PCS."""
import os
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

from dyncall_sign import sign_elf


class DyncallConan(ConanFile):
    name = "dyncall"
    version = "1.4"
    description = "Dynamic C calls, callbacks and loading with AAPCS64 aggregate support"
    license = "ISC"
    homepage = "https://dyncall.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports = "dyncall_sign.py", "dyncall_upstream.py"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("This validated recipe targets HarmonyOS PC AArch64")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("DYNCALL_SOURCE_ARCHIVE")
        if local:
            archive = Path(local).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("source archive must be a regular file")
            source.update(url=archive.as_uri(), filename=archive.name)
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["DC_BUILD_TESTS"] = True
        toolchain.variables["LANG_CXX"] = True
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.shared or self.options.fPIC)
        # Unknown CMake platform modules do not provide the ELF SONAME flag.
        toolchain.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The root minimum-policy check runs before project() loads the toolchain.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        if can_run(self):
            driver = Path(self.recipe_folder, "dyncall_upstream.py")
            self.run('"{}" "{}" "{}"'.format(sys.executable, driver, self.build_folder))

    def package(self):
        CMake(self).install()
        if self.options.shared:
            for library in ("dyncall_s", "dyncallback_s", "dynload_s"):
                sign_elf(Path(self.package_folder, "lib", "lib" + library + ".so"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dyncall")
        self.cpp_info.bindirs = []
        for component, library in (("dyncall", "dyncall_s"), ("dyncallback", "dyncallback_s"), ("dynload", "dynload_s")):
            info = self.cpp_info.components[component]
            info.libs = [library]
            info.set_property("cmake_target_name", "dyncall::" + component)
        self.cpp_info.components["dyncallback"].requires = ["dyncall"]
        # On this musl-based target dlopen/dlsym are supplied by the C runtime.
