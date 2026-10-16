import os
import shlex
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

class PdPoolConan(ConanFile):
    name = "pd-pool"
    version = "0.2.3"
    description = "Hierarchical key/value storage external for Pure Data"
    license = "GPL-2.0-or-later"
    homepage = "https://grrrr.org/research/software/pool/"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires("pd-flext/0.6.4", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration("Pd loads pool as a shared external")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp", "clang++")
        dep = self.dependencies["pd-flext"]
        flags = ["-O2", "-fPIC", "-std=c++17", "-DFLEXT_INLINE", "-DFLEXT_ATTRIBUTES=1"]
        flags += dep.cpp_info.cxxflags
        flags += ["-I"+p for p in dep.cpp_info.includedirs]
        objects = []
        for name in ("data", "main", "pool"):
            obj = os.path.join(self.build_folder, name+".o")
            args = [compiler]+flags+["-c", os.path.join(self.source_folder, "source", name+".cpp"), "-o", obj]
            self.run(shlex.join(args), env="conanbuild")
            objects.append(obj)
        args = [compiler, "-shared", "-Wl,-z,relro,-z,now", "-o", "pool.pd_linux"]+objects
        args += ["-L"+p for p in dep.cpp_info.libdirs]+["-l"+lib for lib in dep.cpp_info.libs+dep.cpp_info.system_libs]
        self.run(shlex.join(args), env="conanbuild")
        self.output.info('HMBS_UPSTREAM_TEST_RESULT={"status":"skipped","reason":"Release has help patches but no automated suite","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}')

    def package(self):
        dest = os.path.join(self.package_folder, "lib", "pd-externals")
        copy(self, "pool.pd_linux", self.build_folder, dest)
        for name in ("pool-help.pd", "pool-0.2.dtd", "readme.txt"):
            copy(self, name, self.source_folder, dest)
        for name in ("license.txt", "gpl.txt"):
            copy(self, name, self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
