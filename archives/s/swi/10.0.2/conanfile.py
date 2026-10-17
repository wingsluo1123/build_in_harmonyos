#!/usr/bin/env python3
"""Conan recipe for SWI-Prolog 10.0.2 (CMake, native OHOS/aarch64)."""

import io
import json
import os
import shlex
import shutil
import socket
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get, save


class SwiConan(ConanFile):
    name = "swi"
    version = "10.0.2"
    package_type = "application"
    license = "BSD-2-Clause"
    url = "https://www.swi-prolog.org/"
    homepage = "https://www.swi-prolog.org/"
    description = "SWI-Prolog native multithreaded runtime and headless packages"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"
    default_options = {"gmp/*:shared": False, "zlib/*:shared": False,
                       "pcre2/*:shared": False, "openssl/*:shared": False,
                       "libedit/*:shared": False, "ncurses/*:shared": False,
                       "libyaml/*:shared": False}

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("zlib/1.3.1.1", force=True)
        self.requires("pcre2/10.45")
        self.requires("openssl/3.5.6")
        self.requires("libarchive/3.7.7")
        self.requires("libedit/20240808")
        self.requires("ncurses/6.5")
        self.requires("libyaml/0.2.5")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("This recipe targets native OHOS/aarch64")
        if self.settings_build.os != self.settings.os or self.settings_build.arch != self.settings.arch:
            raise ConanInvalidConfiguration("The bootstrap and feature probes require native execution")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _info(self, name):
        return self.dependencies[name].cpp_info.aggregated_components()

    def _library(self, name, library):
        for directory in self._info(name).libdirs:
            candidate = os.path.join(directory, "lib" + library + ".a")
            if os.path.isfile(candidate):
                return candidate
        raise RuntimeError("Missing static dependency library: " + name + "/" + library)

    def _test_temporary(self):
        # HMDFS does not support pathname Unix sockets. Use an owned temporary
        # directory on a filesystem that can create the required endpoint.
        for parent in ("/data/storage/el2/base/temp", self.build_folder):
            if not os.path.isdir(parent):
                continue
            temporary = None
            try:
                temporary = tempfile.TemporaryDirectory(prefix="swi-", dir=parent)
                endpoint = os.path.join(temporary.name, "cap.sock")
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                    probe.bind(endpoint)
                os.unlink(endpoint)
                return temporary
            except OSError:
                if temporary is not None:
                    temporary.cleanup()
        raise ConanInvalidConfiguration("No writable test directory supports pathname Unix sockets")

    def generate(self):
        CMakeDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        tc.variables["CMAKE_HOST_CC"] = cc
        runner = os.path.join(self.generators_folder, "exec-native.sh")
        save(self, runner, 'exec "$@"\n')
        tc.variables["CMAKE_CROSSCOMPILING_EMULATOR"] = ";".join([shutil.which("bash") or "bash", runner])
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN;$ORIGIN/../lib/swipl/lib/aarch64-ohos"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH"] = False
        tc.variables["CMAKE_MAKE_PROGRAM"] = shutil.which("ninja") or "ninja"
        tc.variables["SWIPL_ARCH"] = "aarch64-ohos"
        tc.variables["USE_TCMALLOC"] = False
        tc.variables["CCACHE"] = False
        tc.variables["BUILD_TESTING"] = True
        tc.variables["INSTALL_DOCUMENTATION"] = False
        tc.variables["SWIPL_INSTALL_IN_LIB"] = False
        tc.variables["SWIPL_INSTALL_AS_LINK"] = False
        tc.variables["SYSTEM_LIBEDIT"] = True
        tc.variables["SWIPL_MODULE_LINK_LIBSWIPL"] = True
        for package in ("GUI", "JAVA", "PYTHON", "ODBC", "BDB", "TIPC"):
            tc.variables["SWIPL_PACKAGES_" + package] = False
        tc.variables["GMP_INCLUDE_DIRS"] = ";".join(self._info("gmp").includedirs)
        tc.variables["GMP_LIBRARIES"] = self._library("gmp", "gmp")
        for name in ("CURSES_CURSES_LIBRARY", "CURSES_NCURSES_LIBRARY"):
            tc.variables[name] = self._library("ncurses", "ncursesw")
        tc.variables["CURSES_INCLUDE_PATH"] = self._info("ncurses").includedirs[0]
        tc.variables["CURSES_FORM_LIBRARY"] = self._library("ncurses", "formw")
        tc.variables["ZLIB_INCLUDE_DIR"] = self._info("zlib").includedirs[0]
        tc.variables["ZLIB_LIBRARY_RELEASE"] = self._library("zlib", "z")
        tc.variables["OPENSSL_INCLUDE_DIR"] = self._info("openssl").includedirs[0]
        tc.variables["OPENSSL_SSL_LIBRARY"] = self._library("openssl", "ssl")
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = self._library("openssl", "crypto")
        tc.variables["PCRE_INCLUDE_DIR"] = self._info("pcre2").includedirs[0]
        tc.variables["PCRE_LIBRARY"] = self._library("pcre2", "pcre2-8")
        tc.variables["PCRE_LIBRARIES"] = self._library("pcre2", "pcre2-8")
        tc.variables["LIBYAML_INCLUDE_DIR"] = self._info("libyaml").includedirs[0]
        tc.variables["YAML_LIBRARY"] = self._library("libyaml", "yaml")
        tc.variables["LIBEDIT_INCLUDE_DIR"] = self._info("libedit").includedirs[0]
        tc.variables["LIBEDIT_LIBRARIES"] = ";".join([self._library("libedit", "edit"),
                                                    self._library("ncurses", "ncursesw")])
        tc.variables["LibArchive_INCLUDE_DIRS"] = ";".join(self._info("libarchive").includedirs)
        deps = os.path.join(self.generators_folder, "swi-dependencies.cmake")
        save(self, deps, "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\nfind_package(libarchive REQUIRED CONFIG)\n")
        tc.variables["CMAKE_PROJECT_SWI-Prolog_INCLUDE"] = deps
        tc.variables["LibArchive_LIBRARIES"] = "libarchive::archive"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        inventory = io.StringIO()
        self.run("ctest --show-only=json-v1", cwd=self.build_folder, stdout=inventory)
        tests = json.loads(inventory.getvalue())["tests"]
        names = {test["name"] for test in tests}
        required = {"archive:archive", "pcre:pcre", "yaml:yaml", "ssl:ssl"}
        if not required.issubset(names):
            raise RuntimeError("Required extension tests were not configured: " +
                               ", ".join(sorted(required - names)))
        save(self, os.path.join(self.build_folder, "upstream-test-inventory.json"), inventory.getvalue())
        runtime = VirtualRunEnv(self).environment()
        runtime.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "src"))
        with runtime.vars(self).apply():
            # Match the validated serial build and avoid worker process exhaustion.
            cmake.build(build_tool_args=["-j1"])
            with self._test_temporary() as temporary:
                self.run("TMP={tmp} TMPDIR={tmp} TEMP={tmp} ctest --output-on-failure --timeout 180 -j1".format(
                    tmp=shlex.quote(temporary)), cwd=self.build_folder)

    def package(self):
        runtime = VirtualRunEnv(self).environment()
        runtime.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "src"))
        with runtime.vars(self).apply():
            CMake(self).install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["lib/swipl/include"]
        self.cpp_info.libdirs = ["lib/swipl/lib/aarch64-ohos"]
        self.cpp_info.libs = ["swipl"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path("SWI_HOME_DIR", os.path.join(self.package_folder, "lib/swipl"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib/swipl/lib/aarch64-ohos"))
