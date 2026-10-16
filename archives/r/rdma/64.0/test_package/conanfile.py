#!/usr/bin/env python3
"""Conan test_package for rdma/64.0.

Three binaries are built against the Conan package and executed:

  test_rdma          L1 — consumer view of the public API
                     (ibv_get_device_list/ibv_free_device_list +
                      rdma_get_devices/rdma_free_devices)
  test_ohos_specific HarmonyOS-only behaviour that the port had to bridge
                     (__MUSL__/sockaddr_storage, __progname, rindex,
                      thread teardown, hardware-less enumeration)
  test_consumer      a compiling business consumer: enumerates devices through
                     both the verbs and the CMA entry points

The package ships both shared and static libraries. The test binaries link the
regular Conan target (`rdma::rdma`), i.e. the shared objects, and the package
`lib` directory is appended to LD_LIBRARY_PATH so the transitive dependency
librdmacm.so -> libibverbs.so resolves; the recipe links the shared objects with
an explicit SONAME so those names are relocatable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class RdmaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs \
            else self.build_folder

        env = Environment()
        env.append_path(
            "LD_LIBRARY_PATH",
            os.path.join(self.dependencies["rdma"].package_folder, "lib"))
        with env.vars(self).apply():
            self.run(os.path.join(bindir, "test_rdma"))
            self.run(os.path.join(bindir, "test_ohos_specific"))
            self.run(os.path.join(bindir, "test_consumer"))
