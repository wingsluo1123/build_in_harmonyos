#!/usr/bin/env python3
"""Conan recipe — proj 9.3.1 (cmake)

PROJ is a generic coordinate transformation software.
This recipe builds a static library for OpenHarmony (aarch64).
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class ProjConan(ConanFile):
    name = "proj"
    version = "9.3.1"
    description = "PROJ - generic coordinate transformation software"
    license = "MIT"
    homepage = "https://proj.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.49.1")
        self.requires("libtiff/4.7.2")
        self.requires("xz/5.6.2")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        """Self-discover OHOS NDK ohos.toolchain.cmake."""
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "ohos.toolchain.cmake not found: set OHOS_NDK_HOME or profile [conf] user_toolchain")

    def _find_sqlite3_binary(self):
        """Find sqlite3 CLI binary from conan dependency or system."""
        # Try conan dependency package
        try:
            sqlite_pkg = self.dependencies["sqlite3"].package_folder
            bin_path = os.path.join(sqlite_pkg, "bin", "sqlite3")
            if os.path.isfile(bin_path):
                return bin_path
        except Exception:
            pass
        # Try system path
        for p in ["/usr/bin/sqlite3", "/bin/sqlite3"]:
            if os.path.isfile(p):
                return p
        return None

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()

        # Get dependency paths
        sqlite_pkg = self.dependencies["sqlite3"].package_folder
        tiff_pkg = self.dependencies["libtiff"].package_folder
        xz_pkg = self.dependencies["xz"].package_folder

        # Find sqlite3 library (static or shared)
        sqlite_lib = None
        for name in ["libsqlite3.a", "libsqlite3.so"]:
            hit = glob.glob(os.path.join(sqlite_pkg, "lib", "**", name), recursive=True)
            if hit:
                sqlite_lib = hit[0]
                break
        if not sqlite_lib:
            sqlite_lib = os.path.join(sqlite_pkg, "lib", "libsqlite3.a")

        # Find tiff library
        tiff_lib = None
        for name in ["libtiff.a", "libtiff.so"]:
            hit = glob.glob(os.path.join(tiff_pkg, "lib", "**", name), recursive=True)
            if hit:
                tiff_lib = hit[0]
                break
        if not tiff_lib:
            tiff_lib = os.path.join(tiff_pkg, "lib", "libtiff.so")

        # Find sqlite3 binary
        sqlite3_bin = self._find_sqlite3_binary()

        # Build directory
        bdir = os.path.join(self.build_folder, "build-ohos")
        pkgdir = self.package_folder
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_TESTING=OFF",
            '-DCMAKE_C_FLAGS="-fPIC -O2 -fuse-ld=bfd"',
            '-DCMAKE_CXX_FLAGS="-fPIC -O2 -fuse-ld=bfd"',
            '-DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=bfd"',
            '-DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=bfd"',
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(pkgdir),
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DENABLE_CURL=OFF",
            "-DENABLE_TIFF=OFF",
            "-DBUILD_PROJSYNC=OFF",
            "-DNLOHMANN_JSON=internal",
            '-DCMAKE_AR=/data/service/hnp/bin/llvm-ar',
            '-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib',
            '-DSQLITE3_INCLUDE_DIR="{}"'.format(os.path.join(sqlite_pkg, "include")),
            '-DSQLITE3_LIBRARY="{}"'.format(sqlite_lib),
            '-DTIFF_INCLUDE_DIR="{}"'.format(os.path.join(tiff_pkg, "include")),
            '-DTIFF_LIBRARY="{}"'.format(tiff_lib),
            '-DCMAKE_PREFIX_PATH="{};{}"'.format(tiff_pkg, xz_pkg),
        ])
        if sqlite3_bin:
            defs += ' -DEXE_SQLITE3="{}"'.format(sqlite3_bin)

        # Configure
        self.run('PKG_CONFIG_PATH= cmake -B "{}" -S "{}" {}'.format(
            bdir, self.source_folder, defs))
        # Build
        self.run('cmake --build "{}" -j1'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """Sign ELF binaries for OpenHarmony."""
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
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1 2>/dev/null || true'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["proj"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++_shared"]
