"""Conan recipe — avro-c 1.12.0 (Apache Avro C library).

Apache Avro C implementation with deflate, snappy, and lzma codecs.
Source: Apache Avro release tag on GitHub (full tarball, lang/c/ subdirectory)
License: Apache-2.0

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
R33: compiler flags from Conan Toolchain, no bare shell variables
R34: test_package calls avro API
"""
import os
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches


class AvroCConan(ConanFile):
    name = "avro-c"
    version = "1.12.0"
    description = "Apache Avro C library - data serialization with deflate, snappy, lzma codecs"
    license = "Apache-2.0"
    homepage = "https://avro.apache.org/"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("jansson/2.15.1")
        self.requires("zlib/1.3.1")
        self.requires("lzma/5.6.2")
        self.requires("snappy/1.2.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos"):
            raise ConanInvalidConfiguration(
                f"avro-c does not support OS: {self.settings.os}"
            )

    def source(self):
        # Manual download + extract: codeload URL lacks .tar.gz extension
        from conan.tools.files import download
        # Save the original source_folder (root) before generate() changes it
        self._source_root = self.source_folder
        sources = self.conan_data["sources"][self.version]
        archive = "avro-src-1.12.0.tar.gz"
        download(self, url=sources["url"], filename=archive, sha256=sources.get("sha256"))
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            if members:
                root = members[0].name.split("/")[0]
                for m in members:
                    if m.name.startswith(root + "/"):
                        m.name = m.name[len(root) + 1:]
                    elif m.name == root:
                        continue
                    tar.extract(m, path=".")
        os.remove(archive)
        # Apply patches here (before folders.source changes in generate())
        apply_conandata_patches(self)

    def generate(self):
        # Point CMake to lang/c/ subdirectory of the extracted Avro tarball
        self.folders.source = os.path.join("lang", "c")
        tc = CMakeToolchain(self)
        # snappy is a C++ library; linking into C project needs libc++ (Clang only)
        if self.settings.compiler == "clang":
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-lc++"
        tc.generate()
        cd = CMakeDeps(self)
        cd.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy license from the original source root (before folders.source change)
        src_root = getattr(self, "_source_root", self.source_folder)
        copy(self, "LICENSE", src=src_root,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["avro"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("c++")
