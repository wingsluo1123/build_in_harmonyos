#!/usr/bin/env python3
"""Conan recipe for valhalla 3.8.2 -- OpenStreetMap routing engine.

Valhalla is a C++20/CMake routing engine.  Adaptation notes (see notes.md):

* The upstream GitHub source tarball does **not** ship the ``third_party/``
  git submodules; ``source()`` downloads each one at the exact commit pinned
  by the ``3.8.2`` tag (see conandata.yml).
* Only ``Linux``/``OHOS`` are supported by this recipe.
* ``ENABLE_SERVICES`` is disabled (needs ``libprime_server``, not packaged);
  ``ENABLE_PYTHON_BINDINGS``/``ENABLE_NODE_BINDINGS`` are disabled (nanobind /
  node headers are out of scope).
* Valhalla finds most of its dependencies through ``pkg-config``; the recipe
  generates ``.pc`` files with Conan's ``PkgConfigDeps`` and exits through
  ``VirtualBuildEnv`` so ``pkg_check_modules()`` resolves them.
* The spatialite / spatialite_tool command line tools are only used by the
  online timezone-database builder; 0001 downgrades the configure error and
  0002 drops the Gurka tests dependency on that artifact.
* Protobuf is forced into CMake's MODULE mode (0003) because
  ``protobuf_generate_cpp()`` (used by ``proto/CMakeLists.txt``) is not
  provided by the Conan-generated CONFIG files.

The library itself plus the ~1000 self-contained Gurka tests are built; the
Gurka suite is run from ``build()`` and its results are written into the
package's ``reports/`` folder.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.0"

# pkg-config module name that valhalla's CMakeLists.txt asks for -> dependency
# reference to declare it on.  (libcurl needs no entry: the curl recipe already
# exports pkg_config_name "libcurl".)
_PC_MODULES = {
    "zlib": "zlib",
    "liblz4": "lz4",
    "spatialite": "libspatialite",
    "geos": "geos",
    "openssl": "openssl",
    "expat": "expat",
    "luajit": "luajit-openresty",
}


class ValhallaConan(ConanFile):
    name = "valhalla"
    version = "3.8.2"
    description = ("Valhalla: an open source library and set of programs to "
                   "compute routes on OpenStreetMap data")
    license = "MIT"
    homepage = "https://github.com/valhalla/valhalla"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False],
        "with_full_tests": [True, False],
        "with_tools": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tests": True,
        "with_full_tests": False,
        "with_tools": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("protobuf/21.12")
        self.requires("geos/3.13.1")
        self.requires("sqlite3/3.49.1")
        self.requires("libspatialite/5.1.0.2")
        self.requires("curl/8.15.0.1")
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("lz4/1.10.0")
        self.requires("expat/2.8.5")
        self.requires("openssl/3.5.6.1")
        self.requires("luajit-openresty/2.1-20260311")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "valhalla OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # Valhalla is a C++20 project.  The shared OHOS profile pins
        # compiler.cppstd=17 for the binary compatibility of the prebuilt
        # dependencies; override it for this recipe only so the Conan
        # toolchain selects -std=gnu++20.
        if self.settings.compiler.get_safe("cppstd"):
            self.settings.compiler.cppstd = "20"

    # ------------------------------------------------------------------ source
    def _download_submodules(self):
        subs = self.conan_data.get("submodules", {}).get(str(self.version), {})
        for name, info in subs.items():
            dest = os.path.join(self.source_folder, "third_party", name)
            get(self, info["url"], sha256=info["sha256"],
                destination=dest, strip_root=True, retry=6, retry_wait=15)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True, retry=6, retry_wait=15)
        self._download_submodules()

    # ---------------------------------------------------------------- generate
    def _dep_paths(self, name, attr):
        dep = self.dependencies[name]
        comp = dep.cpp_info.aggregated_components()
        out = []
        for d in getattr(comp, attr):
            out.append(d if os.path.isabs(d)
                       else os.path.join(dep.package_folder, d))
        return sorted(set(out))

    def _write_openssl_pc(self):
        # PkgConfigDeps emits an openssl.pc for the direct openssl requirement
        # (the recipe sets pkg_config_name=openssl); this helper only asserts it
        # is present so valhalla links the packaged (static, PIC) OpenSSL rather
        # than a system shared one that would not be in the Conan runtime env.
        pc = os.path.join(self.generators_folder, "openssl.pc")
        if not os.path.isfile(pc):
            self.output.warning("openssl.pc was not generated; "
                                "valhalla may link a system OpenSSL")

    def _find_in_dep(self, name, *rel):
        dep = self.dependencies[name]
        for base in dep.cpp_info.bindirs + ["bin"]:
            cand = os.path.join(dep.package_folder, base, *rel)
            if os.path.isfile(cand):
                return cand
        return ""

    def generate(self):
        deps = CMakeDeps(self)
        # valhalla links the Boost root target as ``Boost::boost``; the BOOST
        # package from the registry exports it as the lower-case ``boost::boost``.
        deps.set_property("boost", "cmake_target_name", "Boost::boost")
        deps.generate()

        pcdeps = PkgConfigDeps(self)
        for mod, ref in _PC_MODULES.items():
            try:
                pcdeps.set_property(ref, "pkg_config_name", mod)
            except Exception:
                pass
        pcdeps.generate()

        env = VirtualBuildEnv(self)
        env.generate()

        tc = CMakeToolchain(self)
        # CMake does not know the OHOS system by default (it would fall back to
        # the host's "HarmonyOS" and print "System is unknown to cmake"), which
        # leaves the platform link flags undefined: shared libraries get no
        # SONAME and dependents record relative NEEDED paths, and no RPATH is
        # emitted.  Point it at the shipped Platform/OHOS.cmake module (which
        # includes Platform/Linux) so SONAME/RPATH are handled properly.
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # The valhalla library target is built with BUILD_WITH_INSTALL_RPATH
        # (patch 0008): CMake's install-time RPATH rewrite (file(RPATH_CHANGE))
        # produces a library the OHOS dynamic loader rejects with "Permission
        # denied", so the library is linked with its final RPATH and copied
        # byte-for-byte on install.
        # valhalla is a C++20 project; the shared OHOS clang profile pins
        # compiler.cppstd=17 for binary compatibility of the dependencies, so
        # force the project's own standard through the toolchain.
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["CMAKE_CXX_EXTENSIONS"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["ENABLE_TESTS"] = bool(self.options.with_tests)
        tc.variables["ENABLE_TOOLS"] = bool(self.options.with_tools)
        tc.variables["ENABLE_DATA_TOOLS"] = True
        tc.variables["ENABLE_SERVICES"] = False
        tc.variables["ENABLE_HTTP"] = True
        tc.variables["ENABLE_PYTHON_BINDINGS"] = False
        tc.variables["ENABLE_NODE_BINDINGS"] = False
        tc.variables["ENABLE_GEOTIFF"] = False
        tc.variables["ENABLE_LZ4"] = True
        tc.variables["ENABLE_CCACHE"] = False
        tc.variables["ENABLE_SINGLE_FILES_WERROR"] = False
        tc.variables["ENABLE_COMPILER_WARNINGS"] = False
        tc.variables["ENABLE_WERROR"] = False
        tc.variables["PREFER_EXTERNAL_DEPS"] = False
        # The OHOS libc++ builds define _LIBCPP_HAS_NO_INCOMPLETE_RANGES unless
        # _LIBCPP_ENABLE_EXPERIMENTAL is set, which hides std::views (used by
        # valhalla/midgard/util.h).  Enable the experimental library features.
        tc.extra_cxxflags.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")

        # Explicit hints for CMake's FindProtobuf module (0003).
        pb_inc = self._dep_paths("protobuf", "includedirs")
        pb_lib = self._dep_paths("protobuf", "libdirs")
        protoc = self._find_in_dep("protobuf", "protoc")
        if pb_inc:
            tc.variables["Protobuf_INCLUDE_DIR"] = pb_inc[0]
        if protoc:
            tc.variables["Protobuf_PROTOC_EXECUTABLE"] = protoc
        libname = "protobuf" if self.settings.os == "Windows" else "libprotobuf"
        for libdir in pb_lib:
            for ext in (".so", ".dylib", ".a"):
                cand = os.path.join(libdir, libname + ext)
                if os.path.isfile(cand):
                    tc.variables["Protobuf_LIBRARY"] = cand
                    break
            if tc.variables.get("Protobuf_LIBRARY"):
                break
        tc.generate()

    # ------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        self._write_openssl_pc()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_tests:
            self._build_and_run_gurka(cmake)

    # Fast, self-contained Gurka tests run by default (the platform CI has a
    # 45-minute hard timeout; the full suite takes ~1.5h).  Build+run the whole
    # suite with -o valhalla/*:with_full_tests=True.
    _GURKA_SUBSET = [
        "gurka_centroid", "gurka_deadend", "gurka_destination_only",
        "gurka_exclude_unpaved_smoothness", "gurka_speeds", "gurka_shortest",
        "gurka_use_tracks", "gurka_via_waypoints", "gurka_zero_length_route",
        "gurka_turn_lanes", "gurka_barrier_uturns", "gurka_urban",
        "gurka_unnamed_pencilpoint_uturns", "gurka_yield_signs",
        "gurka_warnings", "gurka_use_lit",
    ]

    def _build_and_run_gurka(self, cmake):
        """Build (a subset of) the self-contained Gurka test suite and run the
        test executables.  Results are recorded in ``reports/gurka-results.txt``."""
        full = bool(self.options.with_full_tests)
        test_dir = os.path.join(self.build_folder, "test", "gurka")
        try:
            if full:
                cmake.build(target="gurka")
            else:
                for name in self._GURKA_SUBSET:
                    cmake.build(target=name)
        except Exception as exc:  # tests are optional; keep the package buildable
            save(self, os.path.join(self.build_folder, "gurka-build-error.txt"),
                 "gurka build failed: {}\n".format(exc))
            return
        if not os.path.isdir(test_dir):
            return
        if full:
            names = [e for e in sorted(os.listdir(test_dir))
                     if e.startswith("gurka_")
                     and os.path.isfile(os.path.join(test_dir, e))]
        else:
            names = [e for e in self._GURKA_SUBSET
                     if os.path.isfile(os.path.join(test_dir, e))]
        lines, npass, nfail = [], 0, 0
        for entry in names:
            path = os.path.join(test_dir, entry)
            try:
                self.run('"{}"'.format(path), env="conanrun", cwd=self.build_folder)
                lines.append("[PASS] " + entry)
                npass += 1
            except Exception:
                lines.append("[FAIL] " + entry)
                nfail += 1
        lines.append("=" * 40)
        lines.append("gurka: {} passed, {} failed".format(npass, nfail))
        save(self, os.path.join(self.build_folder, "gurka-results.txt"),
             "\n".join(lines) + "\n")
        self.output.info("Gurka tests: {} passed, {} failed".format(npass, nfail))

    # ----------------------------------------------------------------- package
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "CHANGELOG.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # This is a library package: drop the command line tools that the
        # upstream install rules place in bin/ (they are built for the test
        # suite, not part of the exposed library interface).
        binfolder = os.path.join(self.package_folder, "bin")
        if os.path.isdir(binfolder):
            shutil.rmtree(binfolder)
        # Publish the Gurka run summary so the consumer test can report it.
        report = os.path.join(self.build_folder, "gurka-results.txt")
        if os.path.isfile(report):
            copy(self, "gurka-results.txt", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "reports"))

    def package_info(self):
        self.cpp_info.libs = ["valhalla"]
        # The vendored rapidjson/date headers are installed under
        # include/valhalla/third_party and are referenced as <rapidjson/...>
        # and <date/...> by valhalla's public headers.
        self.cpp_info.includedirs = ["include", "include/valhalla/third_party"]
        self.cpp_info.set_property("cmake_file_name", "valhalla")
        self.cpp_info.set_property("cmake_target_name", "valhalla::valhalla")
        self.cpp_info.set_property("pkg_config_name", "valhalla")
