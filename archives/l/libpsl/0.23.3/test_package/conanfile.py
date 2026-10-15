from conan import ConanFile
from conan.tools.build import can_run
import os


class LibpslTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cpp = self.dependencies["libpsl"].cpp_info
        inc = " ".join(f"-I{d}" for d in cpp.includedirs)
        libdir = " ".join(f"-L{d}" for d in cpp.libdirs)
        rpath = " ".join(f"-Wl,-rpath,{d}" for d in cpp.libdirs)
        libs = " ".join(f"-l{lib}" for lib in cpp.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_libpsl.c -o test_libpsl {inc} {libdir} {rpath} {libs}")

    def test(self):
        if can_run(self):
            self.run("./test_libpsl", env="conanrun")
