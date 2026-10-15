#!/usr/bin/env python3
"""Conan recipe for libkysdk-vector-engine-client 1.2.0.0 (CMake, shared library).

Upstream: https://gitee.com/openkylin/libkysdk-vector-engine-client
Source:   release asset of tag debian/1.2.0.0-1
          (libkysdk-vector-engine-client_1.2.0.0.orig.tar.gz == upstream/1.2.0.0
          content; strip_root top dir libkysdk-vector-engine-client-1.2.0.0)

A C++17 gRPC client SDK for the Kylin vector database engine (derived from
milvus-sdk-cpp; soname libkysdk-vector-engine-client.so.1).  The build runs
protobuf/gRPC code generation at build time from the .proto definitions
published by libkylin-ai-system-private (KylinAiProto CMake package) using the
registry's protoc and grpc_cpp_plugin (both aarch64 OHOS binaries, natively
executable on the build host).

Adaptation notes (HarmonyOS PC / aarch64, native build):

- grpc and protobuf export ``cmake_find_mode=none``, so CMakeDeps generates no
  config files for them; gRPC_DIR / Protobuf_DIR / utf8_range_DIR / absl_DIR
  are pinned at the configs inside the registry packages (five-piece wiring,
  mirrors the grpc recipe's own test_package and DRAFT-grpc-component-rich-
  integration).
- Upstream resolves gRPC through pkg-config (``pkg_check_modules(GRPC REQUIRED
  IMPORTED_TARGET grpc)`` — the produced PkgConfig::GRPC target is never used,
  a pure existence check) and links bare ``grpc++``/``protobuf``.  The registry
  grpc.pc ``Requires:`` a long list of absl_* modules that are not installed
  (kylin-ai-document-service precedent), so patch 0001 switches to the CMake
  config targets gRPC::grpc++/protobuf::libprotobuf and adds an explicit
  ``zlib::zlib`` link: libgrpc.a references zlib symbols (message_compress) but
  grpc's installed config does not propagate zlib (grpc recipe test_package
  evidence).
- Proto code generation: KylinAiProtoGenerate.cmake reads
  ``${PROTOBUF_PROTOC_EXECUTABLE}`` (all-caps; protobuf's module-compat layer
  only ever exports the CamelCase ``Protobuf_PROTOC_EXECUTABLE``) and runs
  ``find_program(GRPC_CPP_PLUGIN grpc_cpp_plugin)``.  Both names are pinned to
  the registry binaries as CMake cache variables (pre-seeding a cache variable
  makes find_program a no-op), and KYLAI_GRPC_PROTOCOL_DIR points at the
  protocol directory shipped inside the libkylin-ai-system-private package
  (DRAFT-8959 variable-ization pattern, kylin-ai-document-service precedent).
- ``install()`` destinations use ``${CMAKE_INSTALL_LIBDIR}``, which upstream
  leaves undefined: the .pc would land at the absolute /pkgconfig (out-of-prefix
  write, permission denied on device).  The recipe pins CMAKE_INSTALL_LIBDIR=lib
  (build-system variable only, no source change beyond patch 0001).
- The registry zlib/1.3.1 archive is static with non-PIC objects; on aarch64
  those cannot be absorbed into a shared library unless symbols are made
  non-preemptible, so the DSO link gets ``-Wl,--exclude-libs,ALL`` (same
  technique as kylin-ai-document-service).
- CMake has no Platform/HarmonyOS.cmake, so the SONAME flags stay empty and
  shared libraries would be linked without DT_SONAME.  The target sets
  VERSION 0.0.1 / SOVERSION 1; supplying the flags makes lld emit a real
  soname (libkysdk-vector-engine-client.so.1) — CI L5a requires DT_SONAME.
- Upstream gates the real gRPC client on ``CMAKE_SYSTEM_PROCESSOR MATCHES
  "x86_64|aarch64"`` and silently falls back to the sw_64 stub branch
  (ENABLE_SW_ARCH — every method returns NOT_SUPPORTED) otherwise.  On this
  CI the conan CMakeToolchain renders an empty generic_system block, so cmake
  falls back to uname-based host detection ("unknown" on this device) and
  clobbers the processor; generate() pins CMAKE_SYSTEM_NAME=HarmonyOS +
  CMAKE_SYSTEM_PROCESSOR=aarch64 through a tools.cmake.cmaketoolchain:
  user_toolchain snippet, which makes CMakeDetermineSystem take the cross
  branch that respects the toolchain values (verified on-device).
- Upstream ships no test suite (no test/ directory, no enable_testing/CTest
  anywhere) — validated via the consumer test_package instead.
- The demo/ subdirectory (ENABLE_DEMO, default OFF) is left disabled: it drags
  in libuuid, which is not part of this package's dependency closure.
"""
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class LibkysdkVectorEngineClientConan(ConanFile):
    name = "libkysdk-vector-engine-client"
    version = "1.2.0.0"
    description = ("Kylin vector database engine client SDK "
                   "(gRPC client, derived from milvus-sdk-cpp)")
    license = "Apache-2.0"
    homepage = "https://gitee.com/openkylin/libkysdk-vector-engine-client"
    url = "https://gitee.com/openkylin/libkysdk-vector-engine-client"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        check_min_cppstd(self, "17")
        # Upstream CMakeLists builds the real gRPC client only for
        # x86_64|aarch64; every other arch takes the sw_64 stub branch.
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libkysdk-vector-engine-client supports aarch64 (armv8) only")

    def requirements(self):
        # Static grpc++/grpc/gpr + protobuf archives are absorbed into this
        # DSO.  grpc/1.84.0 pins protobuf/33.6 exactly (33.6.1 fails the graph
        # with "Version conflict ... originates from grpc/1.84.0").
        self.requires("grpc/1.84.0")
        self.requires("protobuf/33.6")
        # Provides find_package(KylinAiProto) with the protocol .proto files
        # (share/kylin-ai/protocols/grpc) and the KylinAiProtoGenerate.cmake
        # macros the project's CMakeLists calls for code generation.
        self.requires("libkylin-ai-system-private/1.2.0.0")
        # Underscore-spelled recipe: nlohmann-json/3.11.2 is a different,
        # older package.
        self.requires("nlohmann_json/3.12.0")
        # libgrpc.a references zlib symbols but grpc's installed config does
        # not propagate zlib, so the link closure needs it explicitly.
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The Gitee release endpoint answers a curl user-agent; other UAs get
        # an HTML challenge page instead of the tarball.
        get(self, **self.conan_data["sources"]["1.2.0.0"],
            headers={"User-Agent": "curl/8.0"}, strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        # Upstream gates the real gRPC client on
        # ``CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|aarch64"`` and silently
        # falls back to the sw_64 stub branch (ENABLE_SW_ARCH, every method
        # returns NOT_SUPPORTED) otherwise.  On this CI the conan 2.29.1
        # CMakeToolchain renders an *empty* generic_system block (no
        # CMAKE_SYSTEM_NAME / CMAKE_SYSTEM_PROCESSOR at all), so cmake's
        # CMakeDetermineSystem takes the host branch and — with uname -p/-m
        # unavailable on this device — clobbers the processor to "unknown"
        # (CI round-1/2 evidence: "-- Building for unknown architecture",
        # SwClientImpl compiled).  Fix with a user toolchain snippet (the
        # user_toolchain block renders first in conan_toolchain.cmake):
        # CMAKE_SYSTEM_NAME=HarmonyOS switches CMakeDetermineSystem to the
        # cross branch, which respects the toolchain's
        # CMAKE_SYSTEM_PROCESSOR=aarch64 (OHOS armv8 triplet is
        # aarch64-linux-ohos).  Verified on-device with the exact CI
        # toolchain: project() then sees "aarch64" and takes the real client
        # branch.
        processor_snippet = os.path.join(
            self.generators_folder, "ohos-system-processor.cmake")
        save(self, processor_snippet,
             "set(CMAKE_SYSTEM_NAME HarmonyOS)\n"
             "set(CMAKE_SYSTEM_PROCESSOR aarch64)\n")
        self.conf.define("tools.cmake.cmaketoolchain:user_toolchain",
                         [processor_snippet])

        protobuf = self.dependencies["protobuf"]
        grpc = self.dependencies["grpc"]
        abseil = self.dependencies["abseil-cpp"]
        openssl = self.dependencies["openssl"]
        kylin_ai = self.dependencies["libkylin-ai-system-private"]

        tc = CMakeToolchain(self)
        # aarch64 GNUInstallDirs may select lib64/; upstream install() rules
        # use ${CMAKE_INSTALL_LIBDIR} undefined (the .pc would fall to the
        # absolute /pkgconfig).  Pin it so everything stays inside the prefix.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # find_package(KylinAiProto): the provider publishes the config for
        # this component (CMakeDeps only emits the top-level package config).
        tc.variables["KylinAiProto_DIR"] = os.path.join(
            kylin_ai.package_folder, "share", "KylinAiProto", "cmake"
        ).replace("\\", "/")
        # KylinAiProtoGenerate.cmake resolves the .proto sources against
        # ${KYLAI_GRPC_PROTOCOL_DIR}/${PATH} (DRAFT-8959 variable).
        tc.variables["KYLAI_GRPC_PROTOCOL_DIR"] = os.path.join(
            kylin_ai.package_folder, "share", "kylin-ai", "protocols", "grpc"
        ).replace("\\", "/")
        # Five-piece wiring for the cmake_find_mode=none registry packages.
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc.package_folder, "lib", "cmake", "grpc").replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range").replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")
        # grpc's ssl.cmake locates OpenSSL through the built-in FindOpenSSL
        # module (pulled in via the gRPC config's find_dependency chain).
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        # protobuf's config only provides the module-mode variables when this
        # compatibility flag is on; KylinAiProtoGenerate.cmake reads the
        # all-caps PROTOBUF_PROTOC_EXECUTABLE spelling directly, which the
        # module-compat layer never exports on its own — pin both spellings.
        tc.variables["protobuf_MODULE_COMPATIBLE"] = "ON"
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = os.path.join(
            protobuf.package_folder, "bin", "protoc").replace("\\", "/")
        tc.variables["PROTOBUF_PROTOC_EXECUTABLE"] = os.path.join(
            protobuf.package_folder, "bin", "protoc").replace("\\", "/")
        # Pre-seed the name KylinAiProtoGenerate.cmake's find_program() uses;
        # a defined cache variable makes find_program return immediately.
        tc.variables["GRPC_CPP_PLUGIN"] = os.path.join(
            grpc.package_folder, "bin", "grpc_cpp_plugin").replace("\\", "/")
        # CMake has no Platform/HarmonyOS.cmake: without these the DSO would
        # carry no DT_SONAME (the target sets VERSION/SOVERSION 0.0.1/1).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Absorb the non-PIC zlib/1.3.1 static archive objects into this DSO
        # (R_AARCH64_ADR_PREL_PG_HI21 otherwise rejected by lld); also keeps
        # the linked static-dependency symbols out of the dynamic symbol
        # table.  Same technique as kylin-ai-document-service.
        tc.extra_sharedlinkflags = ["-Wl,--exclude-libs,ALL"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["kysdk-vector-engine-client"]
        # Headers install under include/kysdk-vector-engine-client/; public
        # headers are gRPC/protobuf-free, so consumers only need this include
        # root and the shared library (static deps are absorbed into the DSO).
        self.cpp_info.includedirs = ["include"]
