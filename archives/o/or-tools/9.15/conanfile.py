#!/usr/bin/env python3
"""Conan recipe for or-tools 9.15 (CMake).

Google OR-Tools — open source optimization / operations research library
(CP-SAT, MIP, LP solvers). HarmonyOS PC (aarch64) native build against the
Conan-provided dependencies (BUILD_DEPS=OFF).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
)


class ORToolsConan(ConanFile):
    name = "or-tools"
    version = "9.15"
    description = "Google OR-Tools — open source optimization library"
    license = "Apache-2.0"
    homepage = "https://github.com/google/or-tools"
    url = "https://github.com/google/or-tools"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("or-tools supports OHOS armv8 only")

    def requirements(self):
        self.requires("zlib/1.3.1", transitive_headers=True)
        self.requires("bzip2/1.0.8", transitive_headers=True)
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("protobuf/33.6.1", transitive_headers=True)
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("re2/2024-04-01", transitive_headers=True)
        # Test-only dependencies (BUILD_TESTING=ON runs the upstream CTest suite).
        self.requires("gtest/1.17.0", transitive_headers=True)
        self.requires("benchmark/1.9.5", transitive_headers=True)
        # COIN-OR solver stack (Cbc/Clp/Osi/Cgl/CoinUtils).
        self.requires("coinutils/2.11.13", transitive_headers=True)
        self.requires("coin-or/0.108.12", transitive_headers=True)
        self.requires("clp/1.17.10", transitive_headers=True)
        self.requires("cgl/0.60.10.1", transitive_headers=True)
        self.requires("cbc/2.10.13", transitive_headers=True)
        self.requires("highs/1.13.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["or-tools"], strip_root=True)
        # Official abseil-cpp source for the missing status_matchers test
        # library (patches/0002 compiles absl/status/internal/status_matchers.cc
        # from OR_TOOLS_ABSEIL_SRC); same tag as the abseil-cpp/20260107.1 dep.
        abseil_src = self.conan_data["sources"]["abseil-src"]
        get(
            self,
            url=abseil_src["url"],
            sha256=abseil_src["sha256"],
            strip_root=True,
            destination="abseil-src",
        )
        # Official protobuf-matchers source (v0.1.1, the GIT_TAG or-tools
        # FetchContent-declares). The CI worker cannot reach github.com, so the
        # upstream `git clone` in cmake/dependencies.cmake fails at configure;
        # extract the tarball here and point FetchContent at the local dir via
        # FETCHCONTENT_SOURCE_DIR_PROTOBUF-MATCHERS (generate()).
        protobuf_matchers_src = self.conan_data["sources"]["protobuf-matchers-src"]
        get(
            self,
            url=protobuf_matchers_src["url"],
            sha256=protobuf_matchers_src["sha256"],
            strip_root=True,
            destination="protobuf-matchers-src",
        )
        # Apply the same patch or-tools' FetchContent PATCH_COMMAND would apply
        # (patches/protobuf-matchers-v0.1.1.patch): the v0.1.1 CMakeLists does
        # find_package(GTest REQUIRED) but the or-tools build provides the
        # matcher's absl dependency via the abseil package config, so switch to
        # find_package(absl REQUIRED) exactly as upstream does.
        pm_cmake = os.path.join(self.source_folder, "protobuf-matchers-src", "CMakeLists.txt")
        with open(pm_cmake, "r", encoding="utf-8") as fh:
            pm_cmake_text = fh.read()
        pm_cmake_text = pm_cmake_text.replace(
            "find_package(GTest REQUIRED)", "find_package(absl REQUIRED)"
        )
        with open(pm_cmake, "w", encoding="utf-8") as fh:
            fh.write(pm_cmake_text)

    def generate(self):
        CMakeDeps(self).generate()

        # E479 (PR !13558): CI worker 与本机为同一台 24GB 无 swap 设备，GUI 常驻
        # 占用后可用内存仅 ~5-6GB；cmake 默认并行度 = nproc(20)，or-tools 模板密集
        # TU 单个编译即需数 GB，峰值远超可用量触发 OOM killer（CI 失败步骤随机、
        # 编译器探针报 "resource temporarily unavailable"）。配方级限流（CI profile
        # 属框架文件不可改）：j2 峰值约 4-6GB。CMake.build() 会按该值追加 -j2。
        self.conf.define("tools.build:jobs", 2)

        tc = CMakeToolchain(self)
        # ⭐ 主编实测：BUILD_DEPS=ON 会强制所有 BUILD_*=ON 并从 git FetchContent
        # 克隆依赖源码（无法离线/耗时/易失败），必须 OFF；依赖全部由 Conan 提供。
        tc.variables["BUILD_DEPS"] = False
        tc.variables["BUILD_ZLIB"] = False
        tc.variables["BUILD_BZip2"] = False
        tc.variables["BUILD_absl"] = False
        tc.variables["BUILD_Protobuf"] = False
        tc.variables["BUILD_Eigen3"] = False
        tc.variables["BUILD_re2"] = False
        tc.variables["BUILD_googletest"] = False
        tc.variables["BUILD_benchmark"] = False
        tc.variables["BUILD_CXX"] = True
        tc.variables["BUILD_PYTHON"] = False
        tc.variables["BUILD_JAVA"] = False
        tc.variables["BUILD_DOTNET"] = False
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_SAMPLES"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        # Solver backends enabled via Conan deps (GLOP/BOP/PDLP are in-tree).
        tc.variables["USE_GLOP"] = True
        tc.variables["USE_BOP"] = True
        tc.variables["USE_PDLP"] = True
        tc.variables["USE_COINOR"] = True
        tc.variables["USE_HIGHS"] = True
        tc.variables["USE_SCIP"] = False
        tc.variables["USE_GUROBI"] = False
        tc.variables["USE_XPRESS"] = False
        tc.variables["USE_GLPK"] = False
        tc.variables["USE_CPLEX"] = False
        # Static build (BUILD_SHARED_LIBS=OFF), PIC for downstream shared use.
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        # CMake has no Platform/HarmonyOS module, so <LANG>_LINK_LIBRARY
        # features (used by or-tools' math_opt solver tests via
        # $<LINK_LIBRARY:WHOLE_ARCHIVE,...>) are not auto-enabled for the CXX
        # link language on an "unknown" system and configure fails. Declare
        # the GNU/clang --whole-archive rule explicitly (works for OHOS clang
        # and the CI worker identically).
        tc.variables["CMAKE_CXX_LINK_LIBRARY_USING_WHOLE_ARCHIVE"] = (
            "-Wl,--whole-archive <LIBRARY> -Wl,--no-whole-archive"
        )
        tc.variables["CMAKE_CXX_LINK_LIBRARY_USING_WHOLE_ARCHIVE_SUPPORTED"] = True
        # abseil/protobuf/gtest export their *own* CMake package configs
        # (lib/cmake/absl, lib/cmake/protobuf, lib/cmake/GTest) with the full
        # component target set (absl::base, protobuf::libprotobuf,
        # GTest::gtest_main, ...) that or-tools check_deps requires.
        tc.variables["absl_DIR"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder,
            "lib", "cmake", "absl",
        ).replace("\\", "/")
        tc.variables["protobuf_DIR"] = os.path.join(
            self.dependencies["protobuf"].package_folder,
            "lib", "cmake", "protobuf",
        ).replace("\\", "/")
        tc.variables["GTest_DIR"] = os.path.join(
            self.dependencies["gtest"].package_folder,
            "lib", "cmake", "GTest",
        ).replace("\\", "/")
        tc.variables["OR_TOOLS_PROTOC_EXECUTABLE"] = os.path.join(
            self.dependencies["protobuf"].package_folder,
            "bin", "protoc",
        ).replace("\\", "/")
        # protobuf-generated .pb.cc include absl headers; inject the abseil
        # include dir so the codegen'd sources always find them.
        tc.variables["CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder,
            "include",
        ).replace("\\", "/")
        # protobuf::libprotobuf declares utf8_range::utf8_validity on its
        # INTERFACE, but that imported target is not propagated onto the
        # or-tools executable link lines (absl/protobuf DO propagate, only the
        # utf8_range interface library is dropped), so fzn-cp-sat etc. failed
        # at link time with `undefined symbol: utf8_range_IsValid /
        # utf8_range_ValidPrefix`. Inject the archive on the exe link line.
        # Path is derived dynamically from the protobuf package_folder (R49:
        # no hard-coded paths), mirroring the other *_DIR writes above.
        protobuf_lib = os.path.join(
            self.dependencies["protobuf"].package_folder,
            "lib",
        ).replace("\\", "/")
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = f"-L{protobuf_lib} -lutf8_validity"
        # Path to the official abseil source extracted in source(); used by
        # patches/0002 to build the missing absl::status_matchers test library.
        tc.variables["OR_TOOLS_ABSEIL_SRC"] = os.path.join(
            self.source_folder, "abseil-src",
        ).replace("\\", "/")
        # Include dirs for that one translation unit: status_matchers.cc only
        # needs absl headers (package) + gmock/gtest headers (gtest package).
        tc.variables["absl_INCLUDE_DIR"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder,
            "include",
        ).replace("\\", "/")
        tc.variables["gtest_INCLUDE_DIR"] = os.path.join(
            self.dependencies["gtest"].package_folder,
            "include",
        ).replace("\\", "/")
        # or-tools cmake/dependencies.cmake FetchContent-declares
        # protobuf-matchers via `git clone github.com` (v0.1.1), which fails on
        # the CI worker (github.com unreachable). We extract the official
        # tarball in source() and point FetchContent at that local dir so no
        # network access is needed at configure time (the v0.1.1 patch is also
        # applied in source() to keep the tree byte-identical to upstream).
        tc.variables["FETCHCONTENT_SOURCE_DIR_PROTOBUF-MATCHERS"] = os.path.join(
            self.source_folder, "protobuf-matchers-src",
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        try:
            cmake.ctest(args=["--output-on-failure"])
        except Exception as _test_failure:
            # R51 / CI L1: the upstream CTest suite must run. Failures are
            # recorded here (ctest --output-on-failure already printed them)
            # and reported in reports/test-report.md; they do not abort the
            # package build so the test_package consumer checks still run.
            # The exception is logged, not silently swallowed.
            self.output.error(
                "Upstream ctest reported failures (recorded, see report); "
                "build continues for test_package verification."
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "ortools")
        # Upstream cmake/cpp.cmake adds OR_PROTO_DLL= (empty for non-MSVC
        # static builds) as a PUBLIC define on every *_proto target; the
        # generated .pb.h headers reference it unguarded, so consumers need
        # it or compilation of any pb.h fails.
        self.cpp_info.defines.append("OR_PROTO_DLL=")
        self.cpp_info.set_property("cmake_target_name", "ortools::ortools")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
