import os
import shutil
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy


class FaissConan(ConanFile):
    name = "faiss"
    version = "1.14.3"
    description = "A library for efficient similarity search and clustering of dense vectors"
    license = "MIT"
    homepage = "https://github.com/facebookresearch/faiss"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        copy(self, "blas_stub.c", src=os.path.join(self.recipe_folder, "patches"),
             dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["FAISS_ENABLE_GPU"] = False
        tc.variables["FAISS_ENABLE_MKL"] = False
        tc.variables["FAISS_ENABLE_PYTHON"] = False
        tc.variables["FAISS_ENABLE_METAL"] = False
        tc.variables["FAISS_ENABLE_C_API"] = False
        tc.variables["FAISS_ENABLE_EXTRAS"] = False
        tc.variables["FAISS_OPT_LEVEL"] = "generic"
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CMAKE_LINK_WHAT_YOU_USE"] = False
        stub_lib = os.path.join(self.build_folder, "libblas_stub.a")
        tc.variables["BLAS_LIBRARIES"] = stub_lib
        tc.variables["LAPACK_LIBRARIES"] = stub_lib
        tc.generate()

    def build(self):
        # Build BLAS stub (OpenBLAS not available on OHOS)
        stub_src = os.path.join(self.source_folder, "blas_stub.c")
        if not os.path.exists(stub_src):
            stub_src = os.path.join(self.recipe_folder, "patches", "blas_stub.c")
        self.run(f"clang -c -O2 {stub_src} -o {self.build_folder}/blas_stub.o")
        self.run(f"llvm-ar rcs {self.build_folder}/libblas_stub.a {self.build_folder}/blas_stub.o")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Merge BLAS stub into libfaiss.a so all symbols are in one library
        libfaiss = os.path.join(self.build_folder, "faiss", "libfaiss.a")
        if os.path.exists(libfaiss):
            self.run(f"llvm-ar rs {libfaiss} {self.build_folder}/blas_stub.o")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove FAISS-installed CMake config to avoid conflict with Conan CMakeDeps
        for d in ["lib/cmake/faiss", "share"]:
            full = os.path.join(self.package_folder, d)
            if os.path.isdir(full):
                shutil.rmtree(full)

    def package_info(self):
        self.cpp_info.libs = ["faiss"]
        self.cpp_info.system_libs = ["omp"]
        self.cpp_info.set_property("cmake_file_name", "faiss")
        self.cpp_info.set_property("cmake_target_name", "faiss::faiss")
        # OpenMP runtime library path
        import glob
        omp_dirs = glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos")
        if omp_dirs:
            self.runenv_info.append_path("LD_LIBRARY_PATH", omp_dirs[0])
