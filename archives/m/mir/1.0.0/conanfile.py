"""Native HarmonyOS ARM64 MIR library; full upstream suite is mandatory."""
import os
import shlex
import shutil
import sys
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MirConan(ConanFile):
    name = "mir"
    version = "1.0.0"
    description = "MIR interpreter, C11 frontend and ARM64 native code generator"
    license = "MIT"
    homepage = "https://github.com/vnmakarov/mir"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "native_*.py", os.path.join(self.recipe_folder, "test_package"),
             os.path.join(self.export_sources_folder, "test_package"))

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("This recipe validates native OHOS ARM64 only")
        if not self.options.fPIC:
            raise ConanInvalidConfiguration("Upstream builds PIC objects for both library variants")

    def layout(self):
        basic_layout(self, src_folder="upstream")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = executables.get("c", "clang")
        ar = executables.get("ar", "llvm-ar")
        helper = os.path.join(self.export_sources_folder, "test_package", "native_upstream.py")
        launcher = os.path.join(self.export_sources_folder, "test_package", "native_cc_launcher.py")
        args = [sys.executable, helper, "--source", self.source_folder,
                "--build", self.build_folder, "--launcher", launcher,
                "--cc", cc, "--ar", ar]
        self.run(" ".join(shlex.quote(x) for x in args), env="conanbuild")

    def package(self):
        headers = ("mir.h", "mir-gen.h", "mir-dlist.h", "mir-varr.h", "mir-htab.h")
        for header in headers:
            copy(self, header, self.source_folder, os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "c2mir.h", os.path.join(self.source_folder, "c2mir"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        if self.options.shared:
            library = os.path.join(self.build_folder, "libmir.so.1.0.0")
            if not os.path.isfile(library):
                raise ConanInvalidConfiguration("Expected upstream shared library is absent")
            libdir = os.path.join(self.package_folder, "lib")
            os.makedirs(libdir, exist_ok=True)
            # HMDFS aliases are ordinary copies of the same signed ELF, not
            # fragile symlinks or regenerated binaries with another identity.
            for name in ("libmir.so.1.0.0", "libmir.so.1", "libmir.so"):
                shutil.copyfile(library, os.path.join(libdir, name))
        else:
            copy(self, "libmir.a", self.build_folder, os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["mir"]
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "mir")
        self.cpp_info.set_property("cmake_target_name", "mir::mir")
