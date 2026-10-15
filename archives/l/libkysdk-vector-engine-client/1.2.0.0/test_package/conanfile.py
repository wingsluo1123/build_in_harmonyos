#!/usr/bin/env python3
"""Conan consumer test for libkysdk-vector-engine-client 1.2.0.0.

The test program links the installed shared library and drives the public
VectorDB::Database API against a dead endpoint (127.0.0.1:1): no server is
needed — the client must build a real gRPC channel (InsecureChannelCredentials
+ CreateCustomChannel + WaitForConnected) and come back with a non-OK Status
carrying a non-empty message instead of crashing or hanging.

The library DSO absorbs the static grpc/protobuf/abseil/zlib archives it was
built against, so the consumer only needs the tested package at runtime.

OHOS-specific assertions (beyond the smoke call):
  - the generated .pb.cc/.grpc.pb.cc code was produced on device by the
    registry's aarch64 protoc + grpc_cpp_plugin and compiled into the shipped
    DSO — asserted via the milvus stub symbols being present in the .so;
  - DT_SONAME is present, relative, and equals
    libkysdk-vector-engine-client.so.1 (CMake lacks Platform/HarmonyOS.cmake;
    the recipe injects the soname flags — CI L5a mirrors this check);
  - the pkg-config file lands inside the prefix at lib/pkgconfig (upstream
    install() would have written the absolute /pkgconfig).
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibkysdkVectorEngineClientTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Declared directly so their package_folder is available in generate():
        # the tested package's own config find_dependency()s grpc/protobuf
        # (both cmake_find_mode=none, must be located explicitly), and the
        # KylinAiProto config / proto layout live inside
        # libkylin-ai-system-private.
        self.requires("grpc/1.84.0")
        self.requires("protobuf/33.6")
        self.requires("abseil-cpp/20260107.1")
        self.requires("openssl/3.5.6")
        self.requires("libkylin-ai-system-private/1.2.0.0")
        self.requires("nlohmann_json/3.12.0")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()
        CMakeDeps(self).generate()

        grpc = self.dependencies["grpc"]
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        openssl = self.dependencies["openssl"]

        tc = CMakeToolchain(self)
        # Five-piece wiring for the cmake_find_mode=none registry packages.
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc.package_folder, "lib", "cmake", "grpc").replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range").replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Build-phase execution (build uid): the test binary needs the tested
        # DSO and its libstdc++-style runtime on LD_LIBRARY_PATH.
        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                run_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        with run_env.vars(self).apply():
            cmake.test()

    def test(self):
        exe = os.path.join(self.build_folder, "test_vector_client")
        if not os.path.isfile(exe):
            raise Exception("consumer test binary not built: {0}".format(exe))

        if can_run(self):
            self.run(exe, env="conanrun")
        else:
            self.output.info("cannot run test_vector_client on this host")

        # Package payload must be complete and relocated inside the prefix.
        dep = self.dependencies["libkysdk-vector-engine-client"]
        checks = {
            "public header Database.h": os.path.join(
                dep.package_folder, "include", "kysdk-vector-engine-client",
                "Database.h"),
            "shared library": os.path.join(
                dep.package_folder, "lib", "libkysdk-vector-engine-client.so"),
            "pkg-config file (lib/pkgconfig, not absolute /pkgconfig)": os.path.join(
                dep.package_folder, "lib", "pkgconfig",
                "kysdk-vector-engine-client.pc"),
            "license": os.path.join(dep.package_folder, "licenses", "LICENSE"),
        }
        for label, path in checks.items():
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                raise Exception(
                    "libkysdk-vector-engine-client {0} missing or empty: {1}".format(
                        label, path))
        self.output.info(
            "libkysdk-vector-engine-client payload verified in {0}".format(
                dep.package_folder))

        # OHOS adaptation: DT_SONAME must exist and be the bare relative name
        # (same rule as CI L5a; the recipe injects the soname flags because
        # CMake lacks Platform/HarmonyOS.cmake).
        so = os.path.join(dep.package_folder, "lib",
                          "libkysdk-vector-engine-client.so")
        readelf = "/data/service/hnp/bin/readelf"
        if not os.path.isfile(readelf):
            readelf = "readelf"
        out = subprocess.run([readelf, "-d", so], capture_output=True,
                             text=True).stdout
        sonames = re.findall(r"\(SONAME\).*\[(.*)\]", out)
        if not sonames:
            raise Exception("DT_SONAME missing on {0}".format(so))
        if sonames[0] != "libkysdk-vector-engine-client.so.1":
            raise Exception(
                "unexpected DT_SONAME {0} on {1}".format(sonames[0], so))
        needed = re.findall(r"\(NEEDED\).*\[(.*)\]", out)
        stub_symbols_present = bool(
            subprocess.run([readelf, "--dyn-syms", "-W", so],
                           capture_output=True, text=True).stdout.count("milvus"))
        if not stub_symbols_present:
            raise Exception(
                "on-device generated milvus stub symbols not found in {0}".format(so))
        self.output.info(
            "OHOS checks: DT_SONAME={0}, NEEDED={1}, on-device proto "
            "codegen symbols present".format(sonames[0], ",".join(needed)))
