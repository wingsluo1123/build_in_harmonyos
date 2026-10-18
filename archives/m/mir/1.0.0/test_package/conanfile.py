import os
import shlex
import shutil
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import VirtualRunEnv


class MirTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.cache_variables["CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG"] = "-Wl,-rpath,"
            toolchain.cache_variables["CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG"] = "-Wl,-rpath-link,"
        toolchain.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.build_folder, "test_mir")
        if not os.path.isfile(binary):
            raise ConanException("Installed-library consumer binary is missing")
        if not can_run(self):
            raise ConanException("This test requires native OHOS ARM64 execution; no skip is allowed")
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            inspector = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
            signed = binary + ".signed"
            if os.path.lexists(signed):
                raise ConanException("Signing destination already exists")
            self.run(" ".join(shlex.quote(x) for x in [signer, "sign", "-inFile", binary,
                    "-outFile", signed, "-selfSign", "1"]), env="conanrun")
            self.run(" ".join(shlex.quote(x) for x in [inspector, "-S", signed])
                     + " | grep -F .codesign", env="conanrun")
            os.chmod(signed, os.stat(binary).st_mode)
            os.replace(signed, binary)
        self.run(shlex.quote(binary), env="conanrun")
