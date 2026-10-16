#!/usr/bin/env python3
"""Conan recipe for ws 11.4.6 — IXWebSocket (WebSocket and HTTP client/server).

Upstream: https://github.com/machinezone/IXWebSocket (tag v11.4.6).
Alpine Linux packages this project under the name `ws` (after its CLI); this
recipe follows that naming and ships both libixwebsocket and the `ws`
command line tool (bin/ws).

Patches (see patches/): pure build-system fixes — cmake_minimum_required
bumped for CMake 4, spdlog switched from FetchContent to find_package, and
conan-provided imported targets wired in (zlib::zlib, openssl::openssl,
spdlog::spdlog, fmt::fmt). No platform macros, no source semantics changed.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class WsConan(ConanFile):
    name = "ws"
    version = "11.4.6"
    description = "WebSocket and HTTP client and server (IXWebSocket), with the ws CLI"
    license = "BSD-3-Clause"
    homepage = "https://github.com/machinezone/IXWebSocket"
    url = "https://github.com/machinezone/IXWebSocket"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.8.1")
        # spdlog and its external fmt are needed by the ws CLI. fmt must be a
        # DIRECT requirement: conan's skip_shared_packages policy empties the
        # cpp_info of dependencies pulled transitively through the shared
        # spdlog package, and the ws CLI compiles against <fmt/*.h> through
        # spdlog's public headers (verified: direct require -> complete
        # CMakeDeps data, transitive-only -> empty).
        self.requires("spdlog/1.11.0")
        self.requires("fmt/8.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # os=OHOS: conan defaults CMAKE_SYSTEM_NAME to "HarmonyOS" while the
        # installed cmake ships Modules/Platform/OHOS.cmake (and no
        # HarmonyOS.cmake); align them so platform variables get populated
        # (missing SONAME flags would otherwise poison downstream links).
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # Install to lib/ (64-bit defaults to lib64/ otherwise).
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # Must follow options.shared, never hardcode.
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["USE_TLS"] = True
        tc.variables["USE_ZLIB"] = True
        tc.variables["USE_WS"] = True    # build the ws CLI into bin/
        tc.variables["USE_TEST"] = False  # upstream tests run in notes.md (R51)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        # Generate CMakeDeps config files (find_package(spdlog/fmt/zlib/openssl))
        # for consumers of this package — the upstream CMake uses config mode.
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS PC XPM requires code signing for exec'd binaries and
        # dlopen'd shared libraries, otherwise running them fails with
        # "Operation not permitted". The signing tools only exist on OHOS
        # devices, hence the os guard.
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                # Skip versioned .so symlinks, sign the real ELF only.
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ws")
        self.cpp_info.set_property("cmake_target_name", "ws::ws")
        self.cpp_info.set_property("pkg_config_name", "ixwebsocket")
        self.cpp_info.libs = ["ixwebsocket"]
        # bin/ws command line tool (R38: declared in commands.json at the
        # software level).
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
