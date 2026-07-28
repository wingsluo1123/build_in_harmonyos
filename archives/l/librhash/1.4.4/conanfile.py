#!/usr/bin/env python3
"""Conan recipe — librhash 1.4.4 (configure + make)"""
import os, glob, re, shutil
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

class LibrhashConan(ConanFile):
    name = "librhash"
    version = "1.4.4"
    description = "LibRHash shared library for computing hash sums（哈希计算库，configure+make 构建，鸿蒙 PC 适配）"
    license = "0BSD"
    homepage = "https://github.com/rhash/RHash"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = "llvm-ar"

        # cflags driven by fPIC option (not hardcoded); -O2 for Release-like build.
        # Note: configure() removes the fPIC option when shared=True, so we must
        # also force -fPIC for shared builds (shared objects always need PIC).
        cflags = "-O2"
        if self.options.shared or self.options.get_safe("fPIC", False):
            cflags += " -fPIC"

        # Configure: build only the librhash library; target depends on shared/static.
        args = [
            "./configure",
            f"--cc={cc}",
            f"--ar={ar}",
            f"--prefix={self.package_folder}",
            f"--libdir={os.path.join(self.package_folder, 'lib')}",
            f"--extra-cflags='{cflags}'",
        ]
        if self.options.shared:
            args += ["--enable-lib-shared", "--disable-static"]
        else:
            # librhash configure controls the librhash library via --enable-lib-static
            # (not --enable-static, which flips the rhash binary link mode).
            # --disable-lib-shared suppresses the shared lib; --disable-shared is NOT
            # a recognized configure option (configure exits 1 on it).
            args += ["--enable-lib-static", "--disable-lib-shared"]
        args.append("--disable-openssl")
        self.run(" ".join(args))

        # Fix Makefile: remove SOLINK_TARGET dependency that fails when
        # LIBRHASH_SO_MAJ == LIBRHASH_SHARED (the test returns non-zero
        # and breaks the build before the .so is actually compiled).
        self.run("sed -i 's/$(SOLINK_TARGET)//' librhash/Makefile")

        # Build librhash only (not the rhash command-line tool); target bound to shared.
        make_target = "lib-shared" if self.options.shared else "lib-static"
        self.run(f"make -C librhash -j1 {make_target}")

        # Sign shared lib for OHOS (static libs don't need signing)
        if self.settings.os == "OHOS" and self.options.shared:
            libdir = os.path.join(self.source_folder, "librhash")
            sos = glob.glob(os.path.join(libdir, "*.so*"))
            # Tool paths read from environment with sensible defaults so the
            # recipe works across CI workers and local dev setups. Missing tools
            # are reported rather than silently swallowed.
            objcopy = os.environ.get("LLVM_OBJCOPY", "llvm-objcopy")
            signer = os.environ.get("BINARY_SIGN_TOOL", "binary-sign-tool")
            readelf = os.environ.get("LLVM_READELF", "llvm-readelf")
            # If no .so was produced by `make lib-shared`, signing is moot —
            # surface the real defect rather than a misleading "tool not found".
            if not sos:
                return
            # Validate objcopy is executable once up front (loud fail on missing tool).
            if not shutil.which(objcopy):
                raise ConanException(f"objcopy not found: {objcopy}")
            if not shutil.which(signer):
                raise ConanException(f"signer not found: {signer}")
            if not shutil.which(readelf):
                raise ConanException(f"readelf not found: {readelf}")
            for so in sos:
                if os.path.islink(so):
                    continue
                # Strip .codesign only when the exact section is present: llvm-objcopy
                # exits non-zero if the section is absent. Anchor the readelf probe to
                # a whitespace boundary so `.codesign_backup` etc. don't false-positive.
                buf = StringIO()
                self.run(f'{readelf} -S "{so}"', stdout=buf, stderr=StringIO(), ignore_errors=True)
                if re.search(r'\.codesign(?=\s)', buf.getvalue()):
                    # ignore_errors: tolerate a stale probe result (e.g. a section named
                    # `.codesign_v2` that the regex accepted but objcopy strips narrowly).
                    self.run(f'{objcopy} --remove-section .codesign "{so}"', ignore_errors=True)
                self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package(self):
        # Install librhash library and headers manually
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)

        # Copy headers
        copy(self, "rhash.h", src=os.path.join(self.source_folder, "librhash"),
              dst=incdir)
        copy(self, "rhash_torrent.h", src=os.path.join(self.source_folder, "librhash"),
              dst=incdir)

        # Copy library
        src_libdir = os.path.join(self.source_folder, "librhash")
        for lib in glob.glob(os.path.join(src_libdir, "*.so*")):
            copy(self, os.path.basename(lib), src=src_libdir, dst=libdir)
        for lib in glob.glob(os.path.join(src_libdir, "*.a")):
            copy(self, os.path.basename(lib), src=src_libdir, dst=libdir)

        # Create librhush.so symlink → librhash.so.1 (Conan CMakeDeps needs unversioned .so)
        so_path = os.path.join(libdir, "librhash.so")
        so_maj = os.path.join(libdir, "librhash.so.1")
        if os.path.isfile(so_maj) and not os.path.exists(so_path):
            os.symlink("librhash.so.1", so_path)

        # Create librhush.so → librhash.so.1 symlink for linker resolution
        so_major = "librhash.so.1"
        so_link = os.path.join(libdir, "librhash.so")
        if os.path.exists(os.path.join(libdir, so_major)) and not os.path.exists(so_link):
            if os.path.islink(so_link) or os.path.exists(so_link):
                os.remove(so_link)
            os.symlink(so_major, so_link)

        # Create librhash.so symlink → librhash.so.1 so CMakeDeps can find it
        so_maj = "librhash.so.1"
        so_link = os.path.join(libdir, "librhash.so")
        if os.path.isfile(os.path.join(libdir, so_maj)) and not os.path.exists(so_link):
            os.symlink(so_maj, so_link)

    def package_info(self):
        self.cpp_info.libs = ["rhash"]
        self.cpp_info.set_property("cmake_file_name", "Rhash")
        self.cpp_info.set_property("cmake_target_name", "Rhash::Rhash")
        self.cpp_info.set_property("pkg_config_name", "librhash")
