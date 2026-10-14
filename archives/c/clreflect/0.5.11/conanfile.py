#!/usr/bin/env python3
"""Conan recipe for clreflect 0.5.11 — C++ runtime reflection library (Celtoys/clReflect).

Products (upstream CMake, no install rules — packaging is manual):
  - static libraries: libclReflectCore.a, libclReflectCpp.a, libclReflectUtil.a
  - CLI tools (R38, commands.json): clReflectScan (clang-based scanner),
    clReflectMerge, clReflectExport
  - test executable clReflectTest + generated clReflectTest.cppbin (upstream suite)

OHOS-specific notes:
  - clReflectScan is a ClangTool consumer. The OHOS SDK ships LLVM 15 as a
    monolith (libclang-cpp.so + libLLVM-15.so) built with the libc++ `__h`
    ABI namespace, while the default toolchain + system libc++_shared.so use
    `__n1`. clReflectScan therefore compiles scan-local copies of the core
    sources with a custom __config_site (`__h`) and links the SDK monolith;
    the shipped libraries stay on the default ABI for consumers (E218 pattern,
    cf. castxml 0.7.0).
  - lld map files (non-PIE test binary) are parsed by a patched MapFileParser.
  - Upstream test pipeline runs clReflectScan → clReflectMerge → clReflectExport
    at build time; SDK LLVM libs must be on LD_LIBRARY_PATH for the scanner.

Usage: conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, mkdir
from conan.tools.env import Environment
import os


class ClreflectConan(ConanFile):
    name = "clreflect"
    version = "0.5.11"
    description = "C++ runtime reflection using clang (Celtoys/clReflect)"
    license = "MIT"
    homepage = "https://github.com/Celtoys/clReflect"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # OHOS SDK LLVM root (has include/ and lib/); override via env if SDK moves
    _default_llvm_root = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform gate must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "clreflect is supported only on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _llvm_root(self):
        return os.environ.get("OHOS_SDK_LLVM_ROOT", self._default_llvm_root)

    def generate(self):
        llvm_root = self._llvm_root()
        tc = CMakeToolchain(self)

        # Point clReflectScan's CMakeLists at the SDK LLVM monolith
        tc.variables["LLVM_INSTALL_DIR"] = llvm_root

        # Custom libc++ __config_site forcing the __h ABI namespace, so the
        # scanner's clang/LLVM template instantiations match the SDK monolith.
        config_site_dir = os.path.join(self.build_folder, "custom-config")
        mkdir(self, config_site_dir)
        config_site = os.path.join(config_site_dir, "__config_site")
        with open(config_site, "w") as f:
            f.write("""// Custom __config_site — override ABI namespace to __h
#ifndef _LIBCPP___CONFIG_SITE
#define _LIBCPP___CONFIG_SITE
#define _LIBCPP_ABI_VERSION 1
#define _LIBCPP_ABI_NAMESPACE __h
#define _LIBCPP_HAS_NO_VENDOR_AVAILABILITY_ANNOTATIONS
#define _LIBCPP_ENABLE_ASSERTIONS_DEFAULT 0
#endif
""")
        tc.variables["CLREFLECT_CONFIG_SITE_DIR"] = config_site_dir

        # clReflectTest is linked non-PIE (see 0003-src-clReflectTest-CMakeLists.txt.patch)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        llvm_root = self._llvm_root()
        env = Environment()
        env.append_path("LD_LIBRARY_PATH", os.path.join(llvm_root, "lib"))
        env.append_path("LD_LIBRARY_PATH",
                        os.path.join(llvm_root, "lib", "aarch64-linux-ohos", "c++"))

        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            # clReflectGenCppbin (ALL) runs clReflectScan/Merge/Export to build
            # the test database; clReflectTest needs it next to the binary.
            cmake.build()

            # Run the upstream test suite (loads clReflectTest.cppbin)
            test_bin = os.path.join(self.package_folder, "bin", "clReflectTest")
            if os.path.exists(test_bin):
                self.run(f"cd {os.path.dirname(test_bin)} && ./clReflectTest")

    def package(self):
        import shutil
        # CMake output dirs == CMAKE_INSTALL_PREFIX (conan sets it to the
        # package folder), so libclReflect*.a and the CLI tools are already in
        # package_folder/lib and package_folder/bin — verify, don't re-copy.
        for lib in ("libclReflectCore.a", "libclReflectCpp.a", "libclReflectUtil.a"):
            if not os.path.exists(os.path.join(self.package_folder, "lib", lib)):
                raise ConanException(f"missing packaged library {lib}")
        for tool in ("clReflectScan", "clReflectMerge", "clReflectExport"):
            if not os.path.exists(os.path.join(self.package_folder, "bin", tool)):
                raise ConanException(f"missing packaged tool {tool}")

        # Public headers: inc/clcpp, inc/clutl and the tool-facing clReflectCore
        # headers under src/ (Database.h etc.) are part of the public API.
        for inc_dir in ("clcpp", "clutl"):
            copy(self, "*", os.path.join(self.source_folder, "inc", inc_dir),
                 dst=os.path.join(self.package_folder, "include", inc_dir))
        copy(self, "*.h", os.path.join(self.source_folder, "src", "clReflectCore"),
             dst=os.path.join(self.package_folder, "include", "clReflectCore"))
        copy(self, "*.h", os.path.join(self.source_folder, "src", "clReflectCpp"),
             dst=os.path.join(self.package_folder, "include", "clReflectCpp"))
        copy(self, "*.h", os.path.join(self.source_folder, "src", "clReflectUtil"),
             dst=os.path.join(self.package_folder, "include", "clReflectUtil"))
        copy(self, "LICENSE", self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["clReflectCpp", "clReflectCore", "clReflectUtil"]
        self.cpp_info.bindirs = ["bin"]

        # Runtime path to the SDK LLVM monolith (libclang-cpp.so / libLLVM-15.so)
        llvm_root = self._llvm_root()
        llvm_lib = os.path.join(llvm_root, "lib")
        self.runenv_info.append("LD_LIBRARY_PATH", llvm_lib)
        self.buildenv_info.append("LD_LIBRARY_PATH", llvm_lib)
