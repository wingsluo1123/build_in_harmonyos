#!/usr/bin/env python3
"""Conan recipe for rdma 64.0 (upstream project: linux-rdma/rdma-core).

rdma-core is the userspace RDMA/InfiniBand stack. It provides:
  - libibverbs  RDMA verbs API
  - librdmacm   RDMA connection manager
  - libibumad / libibmad / libibnetdisc  management datagram + fabric discovery
  - infiniband-diags diagnostic tools, ibacm/iwpmd/srp_daemon/rdma-ndd daemons

OHOS (HarmonyOS PC, aarch64) adaptation strategy
------------------------------------------------
Optional features that need packages the OHOS/CI environment does not
provide are disabled (same portable configuration used by the earlier
rdma-core 56.1 and 61.0 adaptations in this repository):
  ENABLE_RESOLVE_NEIGH=0  no libnl
  NO_PYVERBS=1            no Cython/numpy-backed Python bindings
  NO_MAN_PAGES=1          no pandoc
  NO_COMPAT_SYMS=1        no GNU symbol versioning (musl libc)
  ENABLE_VALGRIND=0       no valgrind headers
  ENABLE_WERROR=0         libc differences must not fail the build

Platform gaps are closed in the recipe instead of patching upstream:
  * -D__MUSL__=1        OHOS sys/socket.h guards sockaddr_storage with
                        #ifndef __MUSL__; OHOS musl does not define it,
                        so linux/socket.h and sys/socket.h collide (E119)
  * -D_GNU_SOURCE       OHOS string.h exposes strdupa() only under
                        _GNU_SOURCE, and rdma-core's own probe only sets
                        it on the uclibc path (CMakeLists HAS_CLOEXEC_GNU_SOURCE)
  * -include ohos-compat.h
                        fills the remaining libc symbol gaps (getpass,
                        rindex, program_invocation_short_name and the
                        POSIX thread-cancellation entry points) - see
                        compat/ohos-compat.h for the per-symbol rationale
  * CMAKE_INSTALL_LIBEXECDIR=libexec
                        Conan's toolchain defaults it to "bin", which
                        collides with bin/srp_daemon when srp_daemon
                        installs start_on_all_ports under ${LIBEXECDIR}
  * CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG
                        CMAKE_SYSTEM_NAME resolves to "HarmonyOS", for which
                        CMake ships no platform module, so shared libraries
                        are linked without a SONAME and their dependents
                        record a relative build-tree path as DT_NEEDED
  * SYSUSERS_DIR=lib/sysusers.d
                        upstream defaults it to the absolute
                        /usr/lib/sysusers.d and installs rdma-sysusers.conf
                        there, which `cmake --install` cannot create when
                        packaging into a Conan prefix

The only upstream source change is patches/0001, which replaces
pthread_cancel() in the rping example with a reserved-signal thread
teardown + join (knowledge E513), because OHOS does not implement
cancellation (pthread_cancel() returns ENOSYS).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

COMPAT_HEADER = os.path.join("compat", "ohos-compat.h")


class RdmaConan(ConanFile):
    name = "rdma"
    version = "64.0"
    description = ("RDMA core userspace libraries and daemons "
                   "(libibverbs, librdmacm, libibumad, libibmad, libibnetdisc)")
    license = "GPL-2.0 OR BSD-2-Clause"
    homepage = "https://github.com/linux-rdma/rdma-core"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "enable_static": [True, False],
        "enable_resolve_neigh": [True, False],
    }
    default_options = {
        "shared": False,
        "enable_static": True,
        "enable_resolve_neigh": False,
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "compat/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        # No external Conan dependencies: libnl / pyverbs / man / valgrind
        # are the only optional dependencies and are all disabled above.
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rdma only supports Linux and OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)

        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_STATIC"] = "ON" if self.options.enable_static else "OFF"
        tc.variables["ENABLE_RESOLVE_NEIGH"] = "ON" if self.options.enable_resolve_neigh else "OFF"
        tc.variables["NO_PYVERBS"] = "1"
        tc.variables["NO_MAN_PAGES"] = "1"
        tc.variables["NO_COMPAT_SYMS"] = "1"
        tc.variables["ENABLE_VALGRIND"] = "0"
        tc.variables["ENABLE_WERROR"] = "0"

        # See the module docstring: bin/srp_daemon collides with the
        # toolchain default of "bin" for CMAKE_INSTALL_LIBEXECDIR.
        tc.variables["CMAKE_INSTALL_LIBEXECDIR"] = "libexec"

        # rdma-core defaults SYSUSERS_DIR to the absolute /usr/lib/sysusers.d
        # and installs rdma-sysusers.conf there, which makes `cmake --install`
        # fail with "file cannot create directory" when packaging into a Conan
        # prefix. A relative path keeps the file inside the package.
        tc.variables["SYSUSERS_DIR"] = "lib/sysusers.d"

        # OHOS: sys/socket.h only skips its sockaddr_storage definition when
        # __MUSL__ is defined, which OHOS musl does not do (E119).
        tc.preprocessor_definitions["__MUSL__"] = "1"

        # OHOS: uname -s reports "HarmonyOS", so CMAKE_SYSTEM_NAME becomes
        # "HarmonyOS" and CMake finds no Modules/Platform/HarmonyOS.cmake.
        # The generic fallback never defines the SONAME flag, so every shared
        # library is linked without -soname and its dependents record the
        # build-tree path (lib/libibverbs.so) as DT_NEEDED - unloadable from
        # any other working directory. Restore the flag Linux.cmake would set.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        compat_header = os.path.join(self.export_sources_folder, COMPAT_HEADER)
        ohos_flags = ["-D_GNU_SOURCE", f"-include {compat_header}"]
        tc.extra_cflags.extend(ohos_flags)
        tc.extra_cxxflags.extend(ohos_flags)

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Static-link order: dependents before dependencies, so a single
        # left-to-right pass resolves every intra-package reference.
        self.cpp_info.libs = [
            "rdmacm",
            "ibnetdisc",
            "ibmad",
            "ibumad",
            "ibverbs",
        ]
        self.cpp_info.system_libs = ["pthread", "rt", "dl"]
        self.cpp_info.set_property("cmake_file_name", "rdma")
        self.cpp_info.set_property("cmake_target_name", "rdma::rdma")
