import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class OpenLibmConan(ConanFile):
    name = "openlibm"
    version = "0.8.8.2"
    description = "Portable standalone C mathematical library"
    homepage = "https://github.com/JuliaMath/openlibm"
    license = "MIT, ISC, BSD-2-Clause, FDLIBM, LGPL-2.1-or-later (tests)"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # The official tag is v0.8.8, but Make.inc still says 0.8.0.
        # Keep installed pkg-config/CMake metadata at this Conan revision.
        toolchain.variables["OPENLIBM_PACKAGE_VERSION"] = str(self.version)
        # Conan maps OHOS/armv8 to an unknown CMake processor on the target;
        # openlibm selects its source directory from this cache variable.
        if str(self.settings.arch) == "armv8":
            toolchain.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        toolchain.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake reads the version before project(), so pass it on the configure
        # command line; the toolchain file is loaded only during project().
        variables = {"OPENLIBM_PACKAGE_VERSION": str(self.version)}
        if str(self.settings.arch) == "armv8":
            # CMake resets the processor to unknown for native OHOS; pass the
            # target architecture on the configure command line as well.
            variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        cmake.configure(variables=variables)
        cmake.build()
        if can_run(self):
            self.output.info("Upstream v0.8.8 CMake has no test target; test_package consumer is run separately")
        else:
            self.output.info("Cross build: target test execution deferred to authorized target validation")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        for rel in ("lib/libopenlibm.a", "include/openlibm_math.h",
                    "licenses/LICENSE.md", "lib/pkgconfig/openlibm.pc"):
            if not os.path.isfile(os.path.join(self.package_folder, rel)):
                raise RuntimeError("missing packaged artifact: " + rel)
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "openlibm.pc")
        with open(pc_path, encoding="utf-8") as pc:
            if "Version: " + str(self.version) not in pc.read().splitlines():
                raise RuntimeError("installed pkg-config version differs from Conan package")

    def package_info(self):
        self.cpp_info.libs = ["openlibm"]
        self.cpp_info.set_property("cmake_file_name", "openlibm")
        self.cpp_info.set_property("cmake_target_name", "openlibm::openlibm")
        self.cpp_info.set_property("pkg_config_name", "openlibm")
