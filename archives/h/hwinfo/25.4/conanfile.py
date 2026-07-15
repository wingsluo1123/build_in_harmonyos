import os
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class HwinfoConan(ConanFile):
    name = "hwinfo"
    version = "25.4"
    description = "Hardware detection tool from openSUSE"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/openSUSE/hwinfo"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Generate version.h (git2log fails without .git directory)
        version_h = os.path.join(src, "src", "hd", "version.h")
        os.makedirs(os.path.dirname(version_h), exist_ok=True)
        with open(version_h, "w") as f:
            f.write(f'#define HD_VERSION_STRING "{self.version}"\n')

        # Generate uuid/uuid.h (libuuid-compatible API, avoids ossp-uuid dependency)
        uuid_dir = os.path.join(src, "src", "hd", "uuid")
        os.makedirs(uuid_dir, exist_ok=True)
        with open(os.path.join(uuid_dir, "uuid.h"), "w") as f:
            f.write("#ifndef _UUID_UUID_H\n")
            f.write("#define _UUID_UUID_H\n\n")
            f.write("typedef unsigned char uuid_t[16];\n\n")
            f.write("void uuid_unparse_lower(const uuid_t uu, char *out);\n\n")
            f.write("#endif /* _UUID_UUID_H */\n")

        # Generate uuid_compat.c (minimal uuid_unparse_lower implementation)
        with open(os.path.join(src, "src", "hd", "uuid_compat.c"), "w") as f:
            f.write('#include "uuid/uuid.h"\n')
            f.write("#include <stdio.h>\n\n")
            f.write("void uuid_unparse_lower(const uuid_t uu, char *out)\n")
            f.write("{\n")
            f.write("    const unsigned char *u = uu;\n")
            f.write('    snprintf(out, 37,\n')
            f.write('        "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",\n')
            f.write("        u[0], u[1], u[2], u[3],\n")
            f.write("        u[4], u[5],\n")
            f.write("        u[6], u[7],\n")
            f.write("        u[8], u[9],\n")
            f.write("        u[10], u[11], u[12], u[13], u[14], u[15]);\n")
            f.write("}\n")

        # Create lex wrapper (OHOS has flex but not lex)
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        lex_wrapper = os.path.join(bin_dir, "lex")
        with open(lex_wrapper, "w") as f:
            f.write("#!/bin/sh\nexec flex \"$@\"\n")
        os.chmod(lex_wrapper, 0o755)

        # Build with make in source directory
        # SO_LIBS="" as make command-line override (not env var) to skip -luuid
        self.run(
            f'make -j1 HWINFO_VERSION={self.version} SO_LIBS=""',
            cwd=src,
            env=[f"PATH={bin_dir}:{os.environ.get('PATH', '')}"],
        )

    def package(self):
        pkg = self.package_folder
        bindir = os.path.join(pkg, "bin")
        libdir = os.path.join(pkg, "lib")
        incdir = os.path.join(pkg, "include")
        datadir = os.path.join(pkg, "share", "hwinfo")

        os.makedirs(bindir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        os.makedirs(datadir, exist_ok=True)

        src = self.source_folder

        # Binaries
        copy(self, "hwinfo", src, bindir)
        copy(self, "check_hd", os.path.join(src, "src", "ids"), bindir)
        copy(self, "convert_hd", os.path.join(src, "src", "ids"), bindir)
        copy(self, "getsysinfo", src, bindir)
        copy(self, "mk_isdnhwdb", os.path.join(src, "src", "isdn", "cdb"), bindir)

        # Libraries
        if self.options.shared:
            copy(self, "libhd.so*", os.path.join(src, "src"), libdir, symlinks=True)
        else:
            copy(self, "libhd.a", os.path.join(src, "src"), libdir)

        # Headers
        copy(self, "hd.h", os.path.join(src, "src", "hd"), incdir)

        # Data files
        copy(self, "ISDN.CDB.txt", os.path.join(src, "src", "isdn", "cdb"), datadir)
        copy(self, "ISDN.CDB.hwdb", os.path.join(src, "src", "isdn", "cdb"), datadir)

        # pkg-config
        pkgconfigdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pkgconfigdir, exist_ok=True)
        copy(self, "hwinfo.pc", src, pkgconfigdir)

    def package_info(self):
        self.cpp_info.libs = ["hd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
