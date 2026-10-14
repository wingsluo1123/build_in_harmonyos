#!/usr/bin/env python3
"""Conan recipe for HPX 1.11.0 — The C++ Standards Library for Parallelism and
Concurrency (https://hpx.stellar-group.org/).

OHOS (HarmonyOS PC, aarch64) adaptation highlights
--------------------------------------------------
* Asio: HPX unconditionally requires standalone Asio (>= 1.12.0); the registry
  has no asio package yet, so the official chriskohlhoff/asio tag archive
  (tag asio-1-21-0, the version HPX itself pins via HPX_WITH_ASIO_TAG_DEFAULT)
  is downloaded from conandata ``deps`` and injected with
  -DHPX_WITH_FETCH_ASIO=ON -DFETCHCONTENT_SOURCE_DIR_ASIO=<repo root>.
  HPX then installs the Asio headers alongside its own headers (upstream
  supported mechanism; no network access during configure).
* Coroutine context switching: on arm64 HPX enables Boost.Context by default
  (HPX_WITH_GENERIC_CONTEXT_COROUTINES ON).  Boost.Context cannot be built for
  OHOS aarch64 in this ecosystem, so the POSIX/ucontext backend is selected
  (HPX_WITH_GENERIC_CONTEXT_COROUTINES=OFF).  OHOS musl declares only the
  ucontext_t type; the implementations come from the published
  libucontext/1.5.2 package and the missing declarations plus the platform
  branch are added by patches/ (platform-only; no other platform behaviour is
  touched).
* Allocator: HPX_WITH_MALLOC=system (tcmalloc is unavailable on OHOS; this is
  the upstream documented way to opt out of the default allocator).
* Boost: the registry's newer boost component builds (1.90/1.91) do not ship
  the complete Boost header tree that HPX needs (accumulators, spirit,
  phoenix, parameter); boost/1.85.0 ships the whole tree plus the compiled
  filesystem/regex/program_options/iostreams libraries.

Upstream tests are not part of this package build (they comprise thousands of
CTest cases that exceed the CI budget); a representative subset is executed
separately on HarmonyOS PC and reported in reports/test-report.md (R51).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    unzip,
)


class HpxConan(ConanFile):
    name = "hpx"
    version = "1.11.0"
    description = ("HPX: a general purpose C++ runtime system for parallel and "
                   "distributed applications of any scale")
    license = "BSL-1.0"
    homepage = "https://hpx.stellar-group.org/"
    url = "https://github.com/TheHPXProject/hpx"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    implements = ["auto_shared_fpic"]

    exports_sources = "patches/*"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # HPX's public headers include Boost headers (e.g. hpx/config/version.hpp
        # includes <boost/version.hpp>), and HPX is a shared library while the
        # boost package is a static/header one.  Conan 2 by default skips such
        # static dependencies for transitive consumers, which would leave
        # consumers without the Boost headers; declare the transitive headers
        # requirement explicitly.
        self.requires("boost/1.85.0", transitive_headers=True)
        # HPX's public headers include <hwloc.h> (topology.hpp) and HPX's own
        # CMake links Hwloc::hwloc PUBLIC, so consumers need both the headers
        # and the library through the dependency chain.
        self.requires("hwloc/2.14.0", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libucontext/1.5.2")
        # hwloc (and its cairo/libpng subtree) is published against zlib/1.3.1.1
        # while boost/1.85.0 requires zlib/1.3.1.  Unify on the registry's fixed
        # revision 1.3.1.1 (R37: adaptation fix of the same upstream 1.3.1,
        # ABI identical); both published binaries stay valid.
        self.requires("zlib/1.3.1.1", override=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"hpx is adapted for Linux and OHOS, not {self.settings.os}")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS adaptation provides the ucontext coroutine backend "
                "for aarch64 (armv8) only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Conan's toolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so HPX's
        # own FindHwloc / FindBoost modules never run; the targets must come
        # from the Conan generated configs.  HPX links Boost::boost and
        # Hwloc::hwloc (capitalized), while the registry recipes name their
        # targets boost::boost_headers / hwloc::hwloc.  Provide the canonical
        # aliases.
        deps.set_property("boost::boost_headers", "cmake_target_aliases",
                          ["Boost::boost"])
        deps.set_property("hwloc", "cmake_target_aliases", ["Hwloc::hwloc"])
        deps.generate()

        tc = CMakeToolchain(self)
        # -- C++ standard --------------------------------------------------------
        # Conan sets CMAKE_CXX_STANDARD from compiler.cppstd; tell HPX to use it.
        tc.variables["HPX_USE_CMAKE_CXX_STANDARD"] = True
        # -- allocator / coroutines ---------------------------------------------
        tc.variables["HPX_WITH_MALLOC"] = "system"
        tc.variables["HPX_WITH_GENERIC_CONTEXT_COROUTINES"] = False
        # -- FetchContent dependencies ------------------------------------------
        tc.variables["HPX_WITH_FETCH_ASIO"] = True
        tc.variables["HPX_WITH_FETCH_HWLOC"] = False
        # -- package scope -------------------------------------------------------
        tc.variables["HPX_WITH_TESTS"] = False
        tc.variables["HPX_WITH_COMPILE_ONLY_TESTS"] = False
        tc.variables["HPX_WITH_FAIL_COMPILE_TESTS"] = False
        tc.variables["HPX_WITH_EXAMPLES"] = False
        # HPX 1.11.0's pkgconfig generation embeds target-dependent generator
        # expressions ($<TARGET_PROPERTY:TYPE>) in file(GENERATE INPUT ...)
        # without a target context, which is a hard error with CMake >= 4
        # (the OHOS worker toolchain ships CMake 4.x).  OHOS consumers obtain
        # HPX through CMake/Conan; upstream already defaults this option to
        # OFF for non-Linux/Apple/MSVC platforms.
        tc.variables["HPX_WITH_PKGCONFIG"] = False
        # -- OHOS shared-library flags -------------------------------------------
        # CMake has no platform module for the system name the CI profile maps
        # OHOS to (HarmonyOS), so its generic linker rules omit the SONAME and
        # build-tree RPATH flags; without them shared libraries record
        # relative-path DT_NEEDED entries (e.g. "../lib/libhpx_core.so") that
        # cannot be resolved at runtime.  Same handling as the registry's boost
        # recipes for OHOS.
        if self.settings.os == "OHOS":
            for language in ("C", "CXX"):
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        # -- libucontext link position is injected in build() through
        #    CMAKE_CXX_STANDARD_LIBRARIES (must appear at the end of the link
        #    line for the static archive's symbols to be pulled).
        tc.generate()

    def _libucontext_libdir(self):
        return os.path.join(
            self.dependencies["libucontext"].package_folder, "lib"
        ).replace("\\", "/")

    def build(self):
        apply_conandata_patches(self)
        asio_root = self._prepare_asio()
        cmake = CMake(self)
        cli_args = []
        if self.settings_build.os == "Windows":
            # The Windows DevEco cross profile uses the SDK's ohos.toolchain.cmake
            # as user_toolchain.  That file pre-defines CMAKE_CXX_FLAGS in the
            # cache, so Conan's CMAKE_*_FLAGS_INIT injection is ignored; it also
            # passes --gcc-toolchain=... to clang, which clang reports as
            # "argument unused during compilation", and HPX's configure feature
            # tests compile with -Werror, turning that warning into a hard
            # configure failure.  Inject the suppression through the cache
            # before the toolchain is processed (the CI profile does not use
            # the SDK toolchain and is unaffected).
            cli_args.append(
                "-DCMAKE_CXX_FLAGS=-Wno-unused-command-line-argument")
        # libucontext (static, PIC) provides the ucontext context switching
        # functions used by the POSIX coroutine backend.  It must appear at the
        # end of the link line (standard libraries position), otherwise the
        # archive is processed before the objects that reference its symbols.
        cmake_variables = {
            "FETCHCONTENT_SOURCE_DIR_ASIO": asio_root,
            "CMAKE_CXX_STANDARD_LIBRARIES":
                f"-L{self._libucontext_libdir()} "
                "-lucontext -lucontext_posix -lm",
        }
        cmake.configure(
            variables=cmake_variables,
            cli_args=cli_args,
        )
        cmake.build()

    def _prepare_asio(self):
        """Download and extract standalone Asio for FetchContent injection.

        Returns the Asio repository root (the directory containing the
        ``asio/include`` sub-tree expected by HPX_SetupAsio.cmake).
        """
        entry = self.conan_data["deps"]["asio"]
        deps_dir = os.path.join(self.build_folder, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        tarball = os.path.join(deps_dir, entry["filename"])
        if not os.path.exists(tarball):
            download(self, entry["url"], tarball, sha256=entry["sha256"])
        extract_dir = os.path.join(deps_dir, "asio")
        if not os.path.isdir(os.path.join(extract_dir, "asio", "include")):
            os.makedirs(extract_dir, exist_ok=True)
            unzip(self, tarball, extract_dir, strip_root=True)
        self.output.info(f"Asio source root: {extract_dir}")
        return extract_dir

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """Sign the packaged shared libraries for HarmonyOS.

        HarmonyOS refuses to load shared libraries without a valid .codesign
        section (the unsigned build-tree .so fails with "Error loading shared
        library ..." at runtime).  Sign self-contained (selfSign) with the SDK
        tools; same handling as the registry's boost recipes.
        """
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools are unavailable; the shared libraries "
                "must be signed before they can be loaded on OHOS.")
            return
        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"),
            recursive=True)
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(f'"{signer}" sign -inFile "{temporary}" '
                     f'-outFile "{temporary}" -selfSign 1')
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if os.path.isfile(p)), "")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "HPX")
        self.cpp_info.set_property("cmake_target_name", "HPX::hpx")
        # libhpx_init.a provides the hpx::init/hpx_main entry machinery (its
        # main.o is only pulled from the archive when the consumer does not
        # define its own main); libhpx.so carries the full runtime and
        # libhpx_core.so the local runtime core (both shared).
        self.cpp_info.libs = ["hpx_init", "hpx", "hpx_core"]
        # Consumers need the Boost headers (HPX public headers include them)
        # and the hwloc shared library.  libucontext is statically linked into
        # the HPX libraries; the entry is required by Conan's package_info
        # validation for direct dependencies (its node is skipped for
        # consumers, so it does not end up in their link interface).
        self.cpp_info.requires = [
            "boost::boost_headers",
            "hwloc::hwloc",
            "libucontext::libucontext",
        ]
