import os
import shutil
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class Pkcs11ToolsConan(ConanFile):
    name = "pkcs11-tools"
    version = "2.6.0"
    description = "Command-line tools for managing objects on PKCS#11 compatible security tokens/smartcards"
    license = "Apache-2.0"
    homepage = "https://github.com/Mastercard/pkcs11-tools"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*", src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_folder, "patches"))

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain sets CC, CXX, CFLAGS, CPPFLAGS, LDFLAGS from profile and dependencies
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        gen = os.path.join(self.recipe_folder, "patches", "generated")

        # Copy pre-generated autotools files (configure, Makefile.in, etc.)
        # These files are necessary because the source tarball does not include
        # a configure script (it requires gnulib bootstrap), and the CI environment
        # does not have gnulib/automake/libtool to regenerate them.
        for item in os.listdir(gen):
            src_path = os.path.join(gen, item)
            dst_path = os.path.join(src, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)

        # Ensure oasis-pkcs11 headers are in the right place
        oasis_headers = os.path.join(src, "include", "oasis-pkcs11", "working", "3-00-current")
        os.makedirs(oasis_headers, exist_ok=True)
        published_dir = os.path.join(src, "include", "oasis-pkcs11", "published", "3-00")
        if os.path.isdir(published_dir):
            for hdr in os.listdir(published_dir):
                if hdr.endswith(".h"):
                    shutil.copy2(os.path.join(published_dir, hdr), os.path.join(oasis_headers, hdr))

        # Create conftmp dir for HMDFS compatibility (configure uses fixed temp dir)
        conftmp = os.path.join(src, ".conftmp")
        os.makedirs(conftmp, exist_ok=True)

        # Build in-source (gnulib's Makefile doesn't support VPATH/out-of-source builds)
        configure_args = [
            "--prefix=/usr/local",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ]

        # Set PKG_CONFIG_PATH for OpenSSL detection (not a compiler flag, R33 compliant)
        openssl = self.dependencies["openssl"]
        os.environ["PKG_CONFIG_PATH"] = os.path.join(openssl.package_folder, "lib", "pkgconfig")

        self.run(f'./configure {" ".join(configure_args)}', env=["conanbuild"], cwd=src)
        self.run("make -j1", env=["conanbuild"], cwd=src)

    def package(self):
        self.run(f'make install DESTDIR="{self.package_folder}"', env=["conanbuild"], cwd=self.source_folder)

        # Reorganize: move from usr/local/bin to bin
        local_bin = os.path.join(self.package_folder, "usr", "local", "bin")
        pkg_bin = os.path.join(self.package_folder, "bin")
        if os.path.isdir(local_bin):
            os.makedirs(pkg_bin, exist_ok=True)
            for f in os.listdir(local_bin):
                shutil.move(os.path.join(local_bin, f), os.path.join(pkg_bin, f))
            shutil.rmtree(os.path.join(self.package_folder, "usr"), ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
