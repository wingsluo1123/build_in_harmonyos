#!/usr/bin/env python3
"""Conan recipe for Wt 4.14.0 — Emweb C++ Web Toolkit.

Upstream facts (emweb/wt tag 4.14.0):
  - CMake project (cmake_minimum_required 3.13...3.22), builds libwt plus the
    reference wthttp connector library; the examples embed wthttp to serve
    HTTP. Dual licensed (GPL-2.0 / commercial).
  - Dependency lookup is NOT plain find_package(Boost): cmake/WtFindBoost.txt
    wraps find_package(Boost 1.66 COMPONENTS program_options thread) (+system
    only for Boost < 1.69, +filesystem only when
    WT_CPP17_FILESYSTEM_IMPLEMENTATION=boost) and then prefers IMPORTED
    targets (Boost::<comp>) when they exist — conan CMakeDeps satisfies this
    path directly. Asio comes from boost headers (WT_ASIO_IMPLEMENTATION=boost
    default): boost/1.91.0.1.4 is REQUIRED for this — the .1.1 package is a
    selective component build whose BOOST_INCLUDE_LIBRARIES set ships no
    boost/asio headers, while .1.4's set includes Boost.Log whose CMakeLists
    references Boost.Asio, so the superproject dependency scanner transitively
    installs the asio headers into the package (first create attempt failed on
    boost/asio/version.hpp not found with .1.1 — decisive evidence).
  - Minimal dependency face (task W0, three published deps):
      boost/1.91.0.1.1 + zlib/1.3.1.1 + openssl/3.5.7.
    Every optional feature that would pull more deps is OFF: HARU, PANGO,
    SQLITE/POSTGRES/FIREBIRD/MYSQL (Wt::Dbo backends), OpenGL/GLEW, UNWIND,
    SAML, GraphicsMagick (raster paint). Wt::Dbo core and Wt::Test are OFF to
    keep the package surface minimal for the platform archive.
    WT_CPP17_FILESYSTEM_IMPLEMENTATION=std avoids the boost::filesystem
    component entirely (C++17 <filesystem>, libc++ supports it).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.scm import Version


class WtConan(ConanFile):
    name = "wt"
    version = "4.14.0"
    description = "Wt (Emweb C++ Web Toolkit): C++ library for developing web applications"
    license = "GPL-2.0-only"  # dual licensed GPL-2.0 / commercial (see LICENSE)
    homepage = "https://github.com/emweb/wt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    topics = ("web", "framework", "toolkit", "http", "server")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        # boost 1.91 (transitive) needs C++17; Wt 4.14 works with it.
        if Version(self.settings.compiler.cppstd) < 17 if self.settings.compiler.cppstd else self.settings.compiler.get_safe("cppstd"):
            self.output.warning("C++17 recommended (boost 1.91)")

    def requirements(self):
        # WtFindBoost.txt needs program_options + thread components and the
        # header-only asio; boost/1.91.0.1.4 ships all of them (the .1.1
        # selective build lacks the boost/asio headers — see module docstring).
        self.requires("boost/1.91.0.1.4", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (CMake ships no
        # Platform/HarmonyOS module). OHOS is POSIX: force the Linux platform
        # (chain-wide convention; libsoundio 48c47b83 / abcmidi / adios2 /
        # kpeople5 merged precedents). No-op for CMake 3.x workers.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        # Library variant: Wt uses its own SHARED_LIBS option
        tc.variables["SHARED_LIBS"] = bool(self.options.shared)
        # No examples / tests / fuzzers / docs in the archive package
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_FUZZ"] = False
        tc.variables["INSTALL_EXAMPLES"] = False
        tc.variables["INSTALL_DOCUMENTATION"] = False
        # Minimal dependency face: everything optional OFF
        tc.variables["ENABLE_SSL"] = True            # openssl in graph
        tc.variables["ENABLE_HARU"] = False
        tc.variables["ENABLE_PANGO"] = False
        tc.variables["ENABLE_SQLITE"] = False
        tc.variables["ENABLE_POSTGRES"] = False
        tc.variables["ENABLE_FIREBIRD"] = False
        tc.variables["ENABLE_MYSQL"] = False
        tc.variables["ENABLE_OPENGL"] = False
        tc.variables["ENABLE_UNWIND"] = False
        tc.variables["ENABLE_SAML"] = False
        tc.variables["ENABLE_LIBWTTEST"] = False     # Wt::Test harness
        tc.variables["ENABLE_LIBWTDBO"] = False      # Wt::Dbo ORM core
        # std::filesystem instead of boost::filesystem
        tc.variables["WT_CPP17_FILESYSTEM_IMPLEMENTATION"] = "std"
        # boost::asio from the boost headers package
        tc.variables["WT_ASIO_IMPLEMENTATION"] = "boost"
        # Belt and braces: keep every optional find_package from locating
        # anything outside the conan graph.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_PNG"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_GLEW"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenGL"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_HPDF"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Asciidoctor"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if str(self.settings.os) == "OHOS":
            libdir = os.path.join(self.package_folder, "lib")
            if os.path.isdir(libdir):
                for name in sorted(os.listdir(libdir)):
                    path = os.path.join(libdir, name)
                    # Sign only real ELF files; symlinks resolve to them.
                    if ".so" in name and os.path.isfile(path) and not os.path.islink(path):
                        self._sign_ohos_elf(path)

    @staticmethod
    def _sign_ohos_elf(path):
        # ki18n 6.26.0.1 / kitemmodels 6.18.0.1 / libsoundio 2.0.0 precedent:
        # re-sign packaged shared libraries with the OHOS build-time codesign
        # section so the loader accepts them.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged artifact: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".wt-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "wt")
        self.cpp_info.set_property("pkg_config_name", "wt")

        wt = self.cpp_info.components["wt"]
        wt.set_property("cmake_target_name", "wt::wt")
        wt.libs = ["wt"]
        wt.requires = [
            "boost::headers",
            "boost::thread",
            "boost::system",
            "openssl::openssl",
            "zlib::zlib",
        ]

        wthttp = self.cpp_info.components["wthttp"]
        wthttp.set_property("cmake_target_name", "wt::wthttp")
        wthttp.libs = ["wthttp"]
        wthttp.requires = [
            "wt",
            "boost::headers",
            "boost::thread",
            "boost::program_options",
            "openssl::openssl",
            "zlib::zlib",
        ]

        if self.settings.os in ("Linux", "OHOS"):
            wt.system_libs = ["pthread", "dl"]
            wthttp.system_libs = ["pthread", "dl"]
