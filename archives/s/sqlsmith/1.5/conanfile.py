#!/usr/bin/env python3
"""Conan recipe — sqlsmith 1.5 (random SQL query generator for PostgreSQL).

sqlsmith is a command-line tool (single `sqlsmith` executable) that connects
to a live RDBMS and generates random SQL. Upstream supports PostgreSQL /
SQLite / MonetDB as "devices under test"; the PostgreSQL path (postgres.cc)
is the core product and the only one the upstream CMake build enables
unconditionally (SQLite / MonetDB are optional find_package probes).

HarmonyOS PC adaptation notes:

  * sqlsmith's CMakeLists.txt calls find_package(PostgreSQL)/find_package(PQXX)/
    find_package(Boost), which are not provided by the OHOS package registry.
    patch 0001 retargets the build onto the published Conan packages:
      - libpq/18.1          -> libpq::libpq    (postgres.cc uses the libpq C API)
      - libpqxx/8.0.1       -> libpqxx::pqxx   (postgres.hh uses pqxx::connection)
      - boost1.84-regex/1.84.0 -> boost1.84-regex::boost1.84-regex
    log.cc / monetdb.cc / sqlite.cc / sqlsmith.cc include <boost/regex.hpp>
    unconditionally, so Boost.Regex is a hard requirement regardless of the
    upstream std::regex configure probe (only the top of postgres.cc is gated
    on HAVE_BOOST_REGEX). The recipe therefore forces HAVE_BOOST_REGEX.

  * The OHOS shared profile pins compiler.cppstd=17; libpqxx 8.x requires C++
    20 (already the case for libpqxx/8.0.1 in this registry), so the C++20
    std level is forced through the CMakeToolchain cppstd block (same
    treatment as libpqxx/8.0.1).

  * sqlsmith's CMakeLists.txt has no install() rule; the recipe installs the
    built sqlsmith binary into package/bin manually, as with other standalone
    CLI tools in this registry (e.g. abcm2ps).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SqlsmithConan(ConanFile):
    name = "sqlsmith"
    version = "1.5"
    description = "Random SQL query generator (fuzzer) for PostgreSQL, SQLite and MonetDB"
    license = "GPL-3.0-only"
    homepage = "https://github.com/anse1/sqlsmith"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("postgresql", "sqlite", "monetdb", "fuzzing", "sql")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Hard dependencies of the PostgreSQL DUT (postgres.cc uses both the
        # libpq C API directly and the pqxx C++ wrapper):
        #   - libpqxx/8.0.1 is the only libpqxx published in the ohpcd
        #     registry and itself requires libpq/18.1, so the shared
        #     libpq/18.1 version keeps a single consistent libpq in the graph.
        #   - boost1.84-regex/1.84.0 is required by the <boost/regex.hpp>
        #     include used unconditionally by the core sources.
        self.requires("libpqxx/8.0.1")
        self.requires("libpq/18.1")
        self.requires("boost1.84-regex/1.84.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sqlsmith recipe supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # R32: settings.os judgement must include OHOS (cmake_system_name is
        # normally auto-mapped by the OHOS conan); make it explicit so the CI
        # cross build matches the local build (same approach as libpqxx/8.0.1).
        if str(self.settings.os) == "OHOS":
            toolchain.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            toolchain.blocks["generic_system"].values["cmake_system_processor"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # libpqxx 8.x headers require C++20; the shared OHOS profile pins
        # compiler.cppstd=17 and the CMakeToolchain cppstd block would inject
        # -std=c++17 on every compile line. Force C++20 (same as libpqxx).
        toolchain.blocks["cppstd"].values["cppstd"] = "20"
        toolchain.blocks["cppstd"].values["cppstd_extensions"] = "OFF"
        toolchain.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # sqlsmith's CMakeLists.txt defines no install() rule, so install the
        # built binary manually into package/bin (cmake_layout places the
        # executable at the top of the per-config build dir).
        binary = self._locate_binary()
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(binary, os.path.join(bin_dir, "sqlsmith"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _locate_binary(self):
        candidates = []
        build = getattr(self.cpp, "build", None)
        bindirs = getattr(build, "bindirs", None) or []
        for bdir in bindirs:
            candidates.append(os.path.join(self.build_folder, bdir, "sqlsmith"))
        candidates.append(os.path.join(self.build_folder, "sqlsmith"))
        for cand in candidates:
            if os.path.isfile(cand):
                return cand
        # Last resort: search the build tree for the produced executable.
        for root, _dirs, files in os.walk(self.build_folder):
            if "sqlsmith" in files:
                return os.path.join(root, "sqlsmith")
        raise ConanException("built sqlsmith executable not found under build folder")

    def package_info(self):
        # sqlsmith is an executable; expose only its bin dir on PATH.
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("PATH", os.path.join(self.package_folder, "bin"))
