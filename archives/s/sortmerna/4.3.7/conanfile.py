#!/usr/bin/env python3
"""Conan recipe for sortmerna 4.3.7 — CMake build system.

SortMeRNA is a local sequence alignment tool for filtering, mapping and
clustering rRNA reads from metatranscriptomic data (C++17, CMake).

OHOS adaptation notes:
  - rocksdb7/7.9.2 (published on ohpcd) replaces upstream's pinned RocksDB
    v7.10.2; sortmerna's CMake does find_package(RocksDB) without a version
    constraint, so 7.9.2 API is fully compatible.
  - 0001 patch: upstream rewrites RocksDB::rocksdb INTERFACE_LINK_LIBRARIES
    to "zlib;Threads" only. Conan 2 CMakeDeps encodes the library file path
    itself in that property, so the rewrite unlinks librocksdb.a entirely
    (verified: link fails with undefined rocksdb::DB::Open etc.) and would
    also drop the snappy/lz4/zstd/bzip2/gflags transitive deps. The patch
    removes the rewrite.
  - ZLIB_ROOT is pinned to the conan zlib package because upstream forces
    find_package(ZLIB MODULE REQUIRED) (config-mode packages are ignored).
  - CONCURRENTQUEUE_HOME points into the conan concurrentqueue package
    (moodycamel header directory).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SortmernaConan(ConanFile):
    name = "sortmerna"
    version = "4.3.7"
    description = "Local sequence alignment tool for filtering, mapping and clustering rRNA reads"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/sortmerna/sortmerna"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sortmerna supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib pinned to the same revision line rocksdb7/7.9.2 was built with
        self.requires("zlib/1.3.1.1")
        self.requires("rocksdb7/7.9.2")
        self.requires("concurrentqueue/1.0.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_TESTS"] = "OFF"
        # select the static RocksDB::rocksdb target in src/sortmerna/CMakeLists.txt
        tc.variables["ROCKSDB_USE_STATIC_LIBS"] = "ON"
        # upstream forces find_package(ZLIB MODULE REQUIRED): point the module
        # at the conan zlib package
        zlib_pkg = self.dependencies["zlib"]
        tc.cache_variables["ZLIB_ROOT"] = zlib_pkg.package_folder
        # moodycamel single header lives in include/concurrentqueue/moodycamel
        cq_pkg = self.dependencies["concurrentqueue"]
        tc.cache_variables["CONCURRENTQUEUE_HOME"] = os.path.join(
            cq_pkg.package_folder, "include", "concurrentqueue", "moodycamel"
        )
        tc.generate()

        deps = CMakeDeps(self)
        # sortmerna does find_package(RocksDB REQUIRED) and expects the
        # RocksDB::rocksdb / RocksDB::rocksdb-shared target names
        deps.set_property("rocksdb7", "cmake_file_name", "RocksDB")
        deps.set_property("rocksdb7", "cmake_target_name", "RocksDB::rocksdb")
        deps.set_property(
            "rocksdb7", "cmake_target_aliases", ["RocksDB::rocksdb-shared"]
        )
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # OHOS CI worker 进程创建受 AppSpawn 管控，-j20 会撞 fork(EAGAIN)
        # 压力（实测 CI #92180：make jobserver/ can't fork）；收敛到 -j4
        cmake.build(cli_args=["--parallel", "4"])

    def _ohos_tool(self, name, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = compilers.get(name) or default
        if candidate and os.path.exists(candidate):
            return candidate
        # local macOS cross builds: fall back to the LLVM bin dir that hosts
        # ar/ranlib (the device /data/service/hnp paths do not exist there)
        ar = compilers.get("ar")
        if ar:
            for cand in (name, f"llvm-{name}"):
                sibling = os.path.join(os.path.dirname(ar), cand)
                if os.path.exists(sibling):
                    return sibling
        return None

    def package(self):
        cmake = CMake(self)
        cmake.install()

        binary = os.path.join(self.package_folder, "bin", "sortmerna")
        if str(self.settings.os) == "OHOS" and os.path.exists(binary):
            sign_tool = self._ohos_tool(
                "sign_tool", "/data/service/hnp/bin/binary-sign-tool"
            )
            objcopy = self._ohos_tool(
                "objcopy", "/data/service/hnp/bin/llvm-objcopy"
            )
            if objcopy:
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{binary}" '
                    "2>/dev/null || true",
                    cwd=self.package_folder,
                )
            if sign_tool:
                signed = binary + ".signed"
                self.run(
                    f'"{sign_tool}" sign -inFile "{binary}" '
                    f'-outFile "{signed}" -selfSign 1',
                    cwd=self.package_folder,
                    quiet=True,
                )
                os.replace(signed, binary)
        if os.path.exists(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
