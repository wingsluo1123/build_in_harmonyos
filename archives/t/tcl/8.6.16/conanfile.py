from conan import ConanFile
from conan.tools.files import collect_libs, get, copy
import os
from conan.tools.layout import basic_layout


class TclConan(ConanFile):
    name = "tcl"
    version = "8.6.16"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def build(self):
        # Standard Tcl autoconf build (unix/ subdirectory)
        prefix = os.environ.get("DEFAULT_PREFIX", "/usr/local")
        unix_dir = os.path.join(self.source_folder, "unix")
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        cxx = compiler_executables.get("cpp", "clang++")
        self.run(f"cd {unix_dir} && bash configure --prefix={prefix} --enable-shared={'yes' if self.options.shared else 'no'} CC={cc} CXX={cxx}", env="conanbuild")
        self.run(f"cd {unix_dir} && make -j$(nproc)", env="conanbuild")
        self.run(f"cd {unix_dir} && make install", env="conanbuild")

    def package(self):
        copy(self, "*", src=os.path.join(self.package_folder, "..", ".."), dst=self.package_folder)

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "tcl")
        self.cpp_info.set_property("cmake_target_name", "tcl::tcl")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
