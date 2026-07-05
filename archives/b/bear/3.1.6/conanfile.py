import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BearConan(ConanFile):
    name = "bear"
    version = "3.1.6"
    description = "Bear - tool to generate compilation database for clang tooling"
    license = "GPL-3.0"
    homepage = "https://github.com/rizsotto/Bear"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["ENABLE_UNIT_TESTS"] = "OFF"
        tc.variables["ENABLE_FUNC_TESTS"] = "OFF"
        tc.variables["ENABLE_MULTILIB"] = "OFF"
        tc.variables["ENABLE_GRPC"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix all third_party download URLs to use mirror (GitHub not accessible on OHOS)
        tp = os.path.join(self.source_folder, "third_party")
        mirror = "https://ghfast.top/"

        # fmt
        fmt_mk = os.path.join(tp, "fmt", "CMakeLists.txt")
        replace_in_file(self, fmt_mk,
                        "https://github.com/fmtlib/fmt/archive/",
                        mirror + "https://github.com/fmtlib/fmt/archive/")

        # nlohmann_json
        json_mk = os.path.join(tp, "nlohmann_json", "CMakeLists.txt")
        replace_in_file(self, json_mk,
                        "https://github.com/nlohmann/json/archive/",
                        mirror + "https://github.com/nlohmann/json/archive/")

        # spdlog
        spdlog_mk = os.path.join(tp, "spdlog", "CMakeLists.txt")
        replace_in_file(self, spdlog_mk,
                        "https://github.com/gabime/spdlog/archive/",
                        mirror + "https://github.com/gabime/spdlog/archive/")

        # Disable grpc entirely - replace CMakeLists.txt with minimal stub
        grpc_cm = os.path.join(tp, "grpc", "CMakeLists.txt")
        if os.path.exists(grpc_cm):
            with open(grpc_cm, 'w') as f:
                f.write('# grpc disabled for OHOS build\nadd_custom_target(grpc_dependency)\n')

        # Fix spdlog: it can't find fmt because CMAKE_PREFIX_PATH doesn't include
        # the fmt install directory. Set SPDLOG_FMT_EXTERNAL=OFF to use bundled fmt.
        spdlog_cm = os.path.join(tp, "spdlog", "CMakeLists.txt")
        if os.path.exists(spdlog_cm):
            replace_in_file(self, spdlog_cm,
                            "-DSPDLOG_FMT_EXTERNAL:BOOL=ON",
                            "-DSPDLOG_FMT_EXTERNAL:BOOL=OFF",
                            False)

        # Fix CMAKE_PREFIX_PATH: BearSource ExternalProject doesn't get the
        # dependency install directories in CMAKE_PREFIX_PATH. The Conan toolchain
        # overrides CMAKE_INSTALL_PREFIX, so deps are installed to CMAKE_INSTALL_PREFIX
        # (the Conan package folder), not to DEPENDENCIES_INSTALL_PREFIX/xxx_dependency.
        # Add CMAKE_INSTALL_PREFIX to the search path so BearSource finds the deps.
        main_cm = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.exists(main_cm):
            replace_in_file(self, main_cm,
                            "-DCMAKE_PREFIX_PATH:PATH=${CMAKE_PREFIX_PATH}",
                            "-DCMAKE_PREFIX_PATH:PATH=${CMAKE_INSTALL_PREFIX};${DEPENDENCIES_INSTALL_PREFIX}/fmt_dependency;${DEPENDENCIES_INSTALL_PREFIX}/nlohmann_json_dependency;${DEPENDENCIES_INSTALL_PREFIX}/spdlog_dependency;${CMAKE_PREFIX_PATH}",
                            False)

        # Patch BearSource CMakeLists.txt to skip gRPC/PkgConfig
        # (ENABLE_GRPC=OFF is set but BearSource still unconditionally requires PkgConfig)
        bear_cs = os.path.join(self.source_folder, "source", "CMakeLists.txt")
        if os.path.exists(bear_cs):
            with open(bear_cs, "r") as f:
                content = f.read()
            # Comment out PkgConfig and gRPC lines
            content = content.replace(
                "find_package(PkgConfig REQUIRED)\npkg_check_modules(gRPC REQUIRED IMPORTED_TARGET protobuf grpc++)",
                "# gRPC disabled for OHOS build\n# find_package(PkgConfig REQUIRED)\n# pkg_check_modules(gRPC REQUIRED IMPORTED_TARGET protobuf grpc++)"
            )
            with open(bear_cs, "w") as f:
                f.write(content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
