#!/usr/bin/env python3
"""Conan recipe - PLAST 2.3.2 (Parallel Local Sequence Alignment Search Tool).

PLAST compares two sequence sets (query vs. reference bank) with a
seed-and-extend heuristic: it is a bank-to-bank oriented, multithreaded
alternative to BLAST.  Upstream ships

  * a C++11 static library        -> lib/libPlastLibrary.a + include/**
  * the command line tool         -> bin/PlastCmd
  * a BLAST bank builder          -> bin/makeplastdb
  * an optional JNI/Java binding  -> src/launcher/jni

The two SIMD hit-iterator stages are written against x86 SSE2/SSE3 intrinsics
and upstream only advertises "Intel/AMD 64bit processor providing SSE2+".
Instead of dropping those kernels (which changes the hit filtering semantics),
the recipe routes them through SIMDe - the same approach Debian uses and that
was proposed upstream in PLAST-software/plast-library#8 - so the very same
kernels are compiled for aarch64 through NEON.

Adaptation summary (see patches/ and notes.md):

  0001  cmake_minimum_required 2.6 -> 3.10 and moved before project()
  0002  the JNI/Java binding becomes optional (OHOS ships no JDK)
  0003  -msse3 is only passed on x86 targets
  0004  SSE kernels compiled through SIMDe + SIMDE_INCLUDE_DIR plumbing
  0005  upstream unit tests run offline on the in-tree FASTA fixtures
  0006  'register' storage class specifier removed (rejected in C++17)
  0007  SystemCommand scratch file goes under TMPDIR (/tmp is read only)
  0008  upstream unit tests write their scratch files under TMPDIR
  0009  fgetc result kept in an int (EOF sentinel where char is unsigned)
  0010  PlastLibraryTest reports failures and returns a non zero status
  0011  tests whose test/db fixtures are not shipped are skipped
  0012  reading frame direction kept in an int (reverse strand indexing)
  0013  generated misc/api/version.hpp installed at its canonical path
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PlastConan(ConanFile):
    name = "plast"
    version = "2.3.2"
    description = ("Parallel Local Sequence Alignment Search Tool: fast bank-to-bank "
                   "protein and nucleotide similarity search")
    license = "AGPL-3.0-only"
    homepage = "https://plast.inria.fr/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Upstream only builds the static target (the PlastLibrary-dynamic target is
    # commented out in src/CMakeLists.txt), so this is a static library package
    # that also ships the PlastCmd / makeplastdb executables.
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SIMDe supplies the portable SSE intrinsics used by the three
        # SmallGapHitIteratorSSE8 / UngapHitIteratorSSE8 / UngapHitIteratorSSE16
        # translation units.
        self.requires("simde/0.8.2")
        # CppUnit is used by the upstream PlastLibraryTest executable only, and
        # that executable is built and run while the package itself is created
        # (see build() below); nothing that is installed into the package links
        # against it, so it is a test requirement and stays out of the
        # dependency graph of every consumer.
        self.test_requires("cppunit/1.15.1")

    def validate(self):
        # R32: platform checks must accept OHOS next to Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "plast/2.3.2 is only supported on Linux and OHOS, not on "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # E092: on OHOS the Conan CMakeToolchain maps os=OHOS to
        # CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake has no platform module.
        # PLAST drives its whole OS abstraction layer (threads, time, files,
        # memory mapped files) from the __LINUX__ macro that its root
        # CMakeLists.txt sets in the "Linux" branch, so map the platform onto
        # Linux; this combination is the established convention in this repo.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # The SIMD kernels include <simde/x86/sse3.h>; PLAST has no
        # find_package() for it, so hand the include directory over explicitly.
        tc.cache_variables["SIMDE_INCLUDE_DIR"] = \
            self.dependencies["simde"].cpp_info.includedirs[0]

        # test/unit/CMakeLists.txt locates CppUnit with a bare find_path().
        # Seeding the cache makes it use the Conan package; find_library() then
        # finds libcppunit.a through the "<include>/../lib" hint path.
        tc.cache_variables["CPPUNIT_INCLUDE_DIR"] = \
            self.dependencies["cppunit"].cpp_info.includedirs[0]

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()

        # E074 / P020: HMDFS 不支持 mkfifo（实机 `mkfifo` 返回 Operation not
        # permitted），GNU make 的 jobserver 因此只能退化为 pipe；递归 make 在
        # 子 make 拿不到有效 jobserver 时会按“无限并行”运行，PLAST 有 146 个源
        # 文件（161 个编译步骤），20 路并发瞬间耗尽 worker 的进程/线程配额，表现为
        #   make: jobserver mkfifo: ...: Operation not permitted
        #   /bin/sh: can't fork - try again
        #   make[2]: *** [.../BasicAlgoIndexator.cpp.o] Error 127
        # （CI 构建 #93278 的失败根因）。实测 `make -j20 -j1` 时 MAKEFLAGS 为
        # `-j1`（最后一个 -j 生效）且不再建立 jobserver，故显式追加 -j1。
        cmake.build(build_tool_args=["-j1"])

        # Upstream CppUnit suite: 18 registered suites / 96 test cases actually
        # added to the runner out of the 108 test cases the sources register
        # (the 19th suite, TestMisc, is never registered by upstream main.cpp).
        # PLAST is compiled natively for the target platform, so the suite can
        # be executed right here when we are not cross building.
        if can_run(self):
            cmake.build(target="test", build_tool_args=["-j1"])
        else:
            self.output.info("cross building: upstream unit tests not executed")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["PlastLibrary"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        # Consumers link libPlastLibrary.a only: the SIMD kernels are already
        # inlined through SIMDe, and CppUnit is used by the test executable.
        self.cpp_info.requires = []
        self.cpp_info.set_property("cmake_file_name", "plast")
        self.cpp_info.set_property("cmake_target_name", "plast::plast")
