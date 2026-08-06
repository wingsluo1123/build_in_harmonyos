#!/usr/bin/env python3
"""Conan recipe for ImageMagick 7.1.2-23 (full build).

ImageMagick is a complete image processing suite supporting 200+ image formats.
This recipe builds ImageMagick with all available delegates for HarmonyOS.
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ImagemagickFullConan(ConanFile):
    name = "imagemagick-full"
    version = "7.1.2-23"
    description = "Complete image processing suite supporting 200+ image formats"
    license = "Apache-2.0"
    homepage = "https://imagemagick.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1")
        self.requires("openjpeg/2.5.4")
        self.requires("libwebp/1.6.0")
        self.requires("libxml2/2.15.3.1")
        self.requires("zstd/1.5.7")
        self.requires("fftw/3.3.10")
        # Direct requirements for transitive deps so PkgConfigDeps generates .pc files
        self.requires("zlib/1.3.1.1")
        self.requires("xz/5.6.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Use PkgConfigDeps to generate .pc files for all dependencies
        from conan.tools.gnu import PkgConfigDeps
        pkg = PkgConfigDeps(self)
        pkg.generate()

        tc = AutotoolsToolchain(self)
        # E119: Fix sockaddr_storage redefinition on HarmonyOS
        # Create a config.site file that sets CPPFLAGS with the macro guard
        if "OHOS" in str(self.settings.os):
            import os
            site_path = os.path.join(self.generators_folder, "config.site")
            with open(site_path, "w") as f:
                f.write("CPPFLAGS=\"-D_UAPI_LINUX_SOCKET_H\"\n")
                f.write("export CPPFLAGS\n")
            tc.configure_args.append(f"CONFIG_SITE={site_path}")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # Delegate configuration - enable all available, disable missing ones
        tc.configure_args.append("--with-jpeg")
        tc.configure_args.append("--with-png")
        tc.configure_args.append("--with-tiff")
        tc.configure_args.append("--with-freetype")
        tc.configure_args.append("--with-fontconfig")
        tc.configure_args.append("--with-openjp2")
        tc.configure_args.append("--with-webp")
        tc.configure_args.append("--with-xml")
        tc.configure_args.append("--with-fftw")
        tc.configure_args.append("--without-heic")
        tc.configure_args.append("--without-djvu")
        tc.configure_args.append("--without-raw")
        tc.configure_args.append("--disable-openmp")
        tc.generate()

        # Create missing pkg-config aliases for name mismatches
        gen_dir = self.generators_folder
        self._create_pc_aliases(gen_dir)

    def _create_pc_aliases(self, gen_dir):
        """Create .pc files for deps that PkgConfigDeps doesn't auto-generate."""
        # Create libopenjp2.pc alias (ImageMagick looks for libopenjp2)
        openjpeg_pc = os.path.join(gen_dir, "openjpeg.pc")
        if os.path.exists(openjpeg_pc) and not os.path.exists(os.path.join(gen_dir, "libopenjp2.pc")):
            shutil.copy(openjpeg_pc, os.path.join(gen_dir, "libopenjp2.pc"))

        # Create liblzma.pc alias if xz.pc exists but liblzma.pc doesn't
        xz_pc = os.path.join(gen_dir, "xz.pc")
        if os.path.exists(xz_pc) and not os.path.exists(os.path.join(gen_dir, "liblzma.pc")):
            shutil.copy(xz_pc, os.path.join(gen_dir, "liblzma.pc"))

        # Create libwebpmux.pc and libwebpdemux.pc if libwebp is present
        # Check by looking for existing libwebp.pc to find the package folder
        libwebp_pc = os.path.join(gen_dir, "libwebp.pc")
        if os.path.exists(libwebp_pc):
            # Extract prefix from libwebp.pc
            webp_prefix = None
            with open(libwebp_pc, "r") as f:
                for line in f:
                    if line.startswith("prefix="):
                        webp_prefix = line.strip().split("=", 1)[1]
                        break
            if webp_prefix:
                for libname, pcname in [("webpmux", "libwebpmux"), ("webpdemux", "libwebpdemux")]:
                    pc_path = os.path.join(gen_dir, f"{pcname}.pc")
                    if not os.path.exists(pc_path):
                        solib = os.path.join(webp_prefix, "lib", f"lib{libname}.so")
                        if glob.glob(solib + "*"):
                            with open(pc_path, "w") as f:
                                f.write(f"prefix={webp_prefix}\n")
                                f.write(f"libdir=${{prefix}}/lib\n")
                                f.write(f"includedir=${{prefix}}/include\n\n")
                                f.write(f"Name: {pcname}\nDescription: {pcname}\nVersion: 1.6.0\n")
                                f.write(f"Libs: -L${{libdir}} -l{libname}\n")
                                f.write(f"Cflags: -I${{includedir}}\n")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = [
            "MagickCore-7.Q16HDRI",
            "MagickWand-7.Q16HDRI",
            "Magick++-7.Q16HDRI",
        ]
        self.cpp_info.includedirs = ["include/ImageMagick-7"]
        self.cpp_info.set_property("pkg_config_name", "ImageMagick")
