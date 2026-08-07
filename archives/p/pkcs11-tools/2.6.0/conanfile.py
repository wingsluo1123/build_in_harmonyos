import os
import shutil
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
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
        # Don't use AutotoolsToolchain to avoid out-of-source build issues
        # gnulib's Makefile doesn't support VPATH builds
        pass

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        gen = os.path.join(self.recipe_folder, "patches", "generated")

        # Copy pre-generated autotools files (configure, Makefile.in, etc.)
        # Use dirs_exist_ok=True to merge with existing source files
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

        # Build in-source (gnulib doesn't support VPATH)
        openssl = self.dependencies["openssl"]
        openssl_root = openssl.package_folder

        configure_args = []
        configure_args.append("--prefix=/usr/local")
        configure_args.append("--bindir=${prefix}/bin")
        configure_args.append("--sbindir=${prefix}/bin")
        configure_args.append("--libdir=${prefix}/lib")
        configure_args.append("--includedir=${prefix}/include")
        configure_args.append("--oldincludedir=${prefix}/include")

        # Set environment variables for configure/make
        if openssl_root:
            os.environ["PKG_CONFIG_PATH"] = os.path.join(openssl_root, "lib", "pkgconfig")
            os.environ["CPPFLAGS"] = f"-I{os.path.join(openssl_root, 'include')}"
            os.environ["LDFLAGS"] = f"-L{os.path.join(openssl_root, 'lib')}"

        # Run configure in-source
        self.run(f'./configure {" ".join(configure_args)}', env=["conanbuild"], cwd=src)
        # Run make in-source
        self.run("make -j1", env=["conanbuild"], cwd=src)

    def package(self):
        # Run make install with DESTDIR to install to package folder
        openssl = self.dependencies["openssl"]
        openssl_root = openssl.package_folder
        if openssl_root:
            os.environ["PKG_CONFIG_PATH"] = os.path.join(openssl_root, "lib", "pkgconfig")
        self.run(f'make install DESTDIR="{self.package_folder}"', env=["conanbuild"], cwd=self.source_folder)

        # Reorganize: move from usr/local/bin to bin
        local_bin = os.path.join(self.package_folder, "usr", "local", "bin")
        pkg_bin = os.path.join(self.package_folder, "bin")
        if os.path.isdir(local_bin):
            os.makedirs(pkg_bin, exist_ok=True)
            for f in os.listdir(local_bin):
                shutil.move(os.path.join(local_bin, f), os.path.join(pkg_bin, f))
            # Clean up empty dirs
            shutil.rmtree(os.path.join(self.package_folder, "usr"), ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # The package provides command-line tools, not libraries
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
