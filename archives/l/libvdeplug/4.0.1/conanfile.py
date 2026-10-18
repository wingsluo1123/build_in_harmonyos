from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
import os


class LibvdeplugConan(ConanFile):
    name = "libvdeplug"
    version = "4.0.1"
    description = "VDE: Virtual Distributed Ethernet - modular plug-in library (vdeplug4)"
    license = ("LGPL-2.1-or-later", "GPL-2.0-or-later")
    homepage = "https://github.com/rd235/vdeplug4"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libexecs provides coprocsp() used by the cmd:// plugin (vdeplug_cmd)
        self.requires("libexecs/1.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # E1013: CMake sees HarmonyOS as an unknown platform; SONAME/RPATH
            # flags are all empty. Restore the Platform/Linux.cmake values via
            # CMAKE_USER_MAKE_RULES_OVERRIDE (applied after the platform module).
            rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
            # Build with the final RPATH so install never rewrites the ELF
            # (RPATH_CHANGE would break the OHOS code signature).
            tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
            tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN;$ORIGIN/../lib"

        dep = self.dependencies["libexecs"]
        include_dir = dep.cpp_info.includedirs[0]
        lib_dir = dep.cpp_info.libdirs[0]
        # Upstream CMake does include_directories(<project dirs>) only and links
        # the cmd plugin with a raw "-lexecs"; feed libexecs through the cache.
        tc.variables["CMAKE_C_FLAGS"] = f"-I{include_dir}"
        tc.variables["CMAKE_LIBRARY_PATH"] = lib_dir
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = f"-L{lib_dir}"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = f"-L{lib_dir}"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["vdeplug"]
        # Plugin modules (libvdeplug_*.so) are installed into lib/vdeplug/ and
        # resolved at runtime via dladdr relative to libvdeplug.so itself.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
