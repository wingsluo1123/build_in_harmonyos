"""SymPol: build the original lrs/cdd engines and run both upstream test entries."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, export_conandata_patches, get, replace_in_file, unzip


class SympolConan(ConanFile):
    name = "sympol"
    version = "0.1.9"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tremlin/SymPol"
    description = "Polyhedral description conversion up to symmetry"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "upstream.py", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("gmp/6.3.0.1", transitive_headers=True, transitive_libs=True)
        # PermLib is header-only and was published against Boost 1.90. Use one
        # Boost header/library version consistently across the complete graph.
        self.requires("boost/1.91.0.1.4", force=True, transitive_headers=True, transitive_libs=True)
        self.requires("permlib/0.2.9", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        local_archive = self.conf.get("user.sympol:source_archive", default=None)
        if local_archive:
            check_sha256(self, local_archive, self.conan_data["sources"]["sha256"])
            unzip(self, local_archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Upstream overwrites the toolchain's module path. Preserve Conan's
        # dependency modules and explicitly consume the separately released
        # PermLib headers, absent from the Git tag archive.
        replace_in_file(
            self, os.path.join(self.source_folder, "CMakeLists.txt"),
            'set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/external/cmake/Modules")',
            'list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/external/cmake/Modules")\n'
            'find_package(permlib CONFIG REQUIRED)\n'
            'include_directories(${permlib_INCLUDE_DIRS})',
        )
        replace_in_file(
            self, os.path.join(self.source_folder, "CMakeLists.txt"),
            'FIND_PACKAGE(GMP REQUIRED)\ninclude_directories(${GMP_INCLUDE_DIR})',
            'find_package(gmp CONFIG REQUIRED)\n'
            'set(GMP_LIBRARIES gmp::gmp)\n'
            'get_target_property(GMP_INCLUDE_DIR gmp::gmp INTERFACE_INCLUDE_DIRECTORIES)\n'
            'include_directories(${GMP_INCLUDE_DIR})',
        )
        # The tag's bundled lrs/cdd CMake targets expose relative SONAMEs
        # (../external/...), which the OHOS loader rejects. They are private
        # implementation engines, so keep the public sympol library shared but
        # link these two bundled targets statically.
        for relative in (
            os.path.join("external", "lrslib-042c", "CMakeLists.txt"),
            os.path.join("external", "cddlib-094f", "CMakeLists.txt"),
        ):
            if "lrslib" in relative:
                replace_in_file(self, os.path.join(self.source_folder, relative),
                                "add_library(lrsgmp SHARED", "add_library(lrsgmp STATIC")
                replace_in_file(self, os.path.join(self.source_folder, relative),
                                "add_library(lrsgmp STATIC lrslib.c lrsgmp.c)",
                                "add_library(lrsgmp STATIC lrslib.c lrsgmp.c)\nset_target_properties(lrsgmp PROPERTIES POSITION_INDEPENDENT_CODE ON)")
            else:
                replace_in_file(self, os.path.join(self.source_folder, relative),
                                "add_library(cddgmp SHARED", "add_library(cddgmp STATIC")
                replace_in_file(self, os.path.join(self.source_folder, relative),
                                "cddio_f.c)\n\ntarget_link_libraries(cddgmp",
                                "cddio_f.c)\nset_target_properties(cddgmp PROPERTIES POSITION_INDEPENDENT_CODE ON)\n\ntarget_link_libraries(cddgmp")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMake 4 evaluates cmake_minimum_required before project() loads the
        # toolchain. This must be a command-line cache variable, not a value
        # defined too late inside conan_toolchain.cmake.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            # HarmonyOS's CMake platform lacks these ELF platform defaults.
            # Set them before linking rather than modifying a signed ELF.
            for language in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"] = ":"
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        # The build CLI and libsympol are adjacent; installed bin/../lib is
        # adjacent too. Use the same link-time RPATH in both layouts so CMake
        # install does not rewrite the signed file.
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        # Keep the loader token inside the toolchain file: passing it as a
        # double-quoted CMake CLI cache argument lets the shell expand it away.
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN;$ORIGIN/../lib"
        # These are optional alternative symmetry backends, not required by
        # the original 28 CLI regressions or either registered CTest entry.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Eigen3"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Bliss"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        helper = os.path.join(self.source_folder, "upstream.py")
        self.run(shlex.join([sys.executable, helper, self.source_folder, self.build_folder]), env="conanrun")

    def package(self):
        CMake(self).install()
        # The original install(FILES) flattens matrix/ and yal/. Preserve the
        # layout used by public #include directives in the installed headers.
        copy(self, "*.h", src=os.path.join(self.source_folder, "sympol"),
             dst=os.path.join(self.package_folder, "include", "sympol"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sympol", "lrsgmp", "cddgmp"]
        self.cpp_info.set_property("cmake_file_name", "sympol")
        self.cpp_info.set_property("cmake_target_name", "sympol::sympol")
        self.cpp_info.requires = ["gmp::gmp", "boost::program_options", "permlib::permlib"]
