import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HwinfoConan(ConanFile):
    name = "hwinfo"
    version = "25.2"
    description = "Hardware information tool from openSUSE"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/openSUSE/hwinfo"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
             filename="hwinfo-25.2.tar.xz")

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Create version.h (Makefile's git2log fails without .git directory)
        version_h = os.path.join(src, "src", "hd", "version.h")
        with open(version_h, "w") as f:
            f.write('#define HD_VERSION_STRING "25.2"\n')

        # Create uuid/uuid.h header (system lacks libuuid-dev package)
        uuid_dir = os.path.join(src, "uuid")
        os.makedirs(uuid_dir, exist_ok=True)
        uuid_h = os.path.join(uuid_dir, "uuid.h")
        with open(uuid_h, "w") as f:
            f.write(
                "#ifndef _UUID_UUID_H\n"
                "#define _UUID_UUID_H\n\n"
                "#include <sys/types.h>\n"
                "#include <stdint.h>\n\n"
                "typedef uint8_t uuid_t[16];\n\n"
                "struct uuid {\n"
                "    uint32_t    time_low;\n"
                "    uint16_t    time_mid;\n"
                "    uint16_t    time_hi_and_version;\n"
                "    uint16_t    clock_seq;\n"
                "    uint16_t    node[6];\n"
                "};\n\n"
                "void uuid_generate(uuid_t out);\n"
                "void uuid_generate_random(uuid_t out);\n"
                "void uuid_generate_time(uuid_t out);\n"
                "void uuid_generate_time_safe(uuid_t out);\n\n"
                "void uuid_unparse(const uuid_t uu, char *out);\n"
                "void uuid_unparse_lower(const uuid_t uu, char *out);\n"
                "void uuid_unparse_upper(const uuid_t uu, char *out);\n\n"
                "int uuid_parse(const char *in, uuid_t uu);\n"
                "void uuid_copy(uuid_t dst, const uuid_t src);\n"
                "void uuid_clear(uuid_t uu);\n"
                "int uuid_is_null(const uuid_t uu);\n"
                "int uuid_compare(const uuid_t uu1, const uuid_t uu2);\n\n"
                "void uuid_unpack(const uuid_t in, struct uuid *ptr);\n"
                "void uuid_pack(struct uuid *out, const uuid_t in);\n\n"
                "time_t uuid_time(const uuid_t uu, struct timeval *ret_tv);\n"
                "int uuid_type(const uuid_t uu);\n"
                "int uuid_variant(const uuid_t uu);\n\n"
                "#define UUID_VARIANT_NCS    0\n"
                "#define UUID_VARIANT_DCE    1\n"
                "#define UUID_VARIANT_MICROSOFT 2\n"
                "#define UUID_VARIANT_OTHER  3\n\n"
                "#endif /* _UUID_UUID_H */\n"
            )

        # Generate lex.yy.c using flex (Makefile expects 'lex' command which doesn't exist)
        cdb_dir = os.path.join(src, "src", "isdn", "cdb")
        self.run(f'flex -o "{cdb_dir}/lex.yy.c" "{cdb_dir}/isdn_cdb.lex"')

        # Find system libuuid from HNP packages
        uuid_lib_dirs = glob.glob("/data/service/hnp/**/libuuid.a", recursive=True)
        uuid_lib_dir = os.path.dirname(uuid_lib_dirs[0]) if uuid_lib_dirs else ""
        if not uuid_lib_dir:
            raise Exception("libuuid not found in HNP packages")

        # Get compiler from Conan conf (R33: never use shell env vars)
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, str):
            import json
            compilers = json.loads(compilers) if compilers else {}
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        # Build with make
        # HWINFO_VERSION=25.2 skips git2log (which requires .git directory)
        # Include paths: src root for uuid/uuid.h, src/hd for hd.h
        # Library path: uuid_lib_dir for libuuid
        self.run(
            f'make CC={cc} AR={ar} RANLIB={ranlib} -j1 '
            f'HWINFO_VERSION=25.2 '
            f'CFLAGS+="-I{src} -I{src}/src/hd" '
            f'LDFLAGS+="-Lsrc -L{uuid_lib_dir}" '
            f'SO_LIBS="-luuid" '
            f'SLIBS="-lhd -luuid"',
            cwd=src
        )

    def package(self):
        src = self.source_folder

        # Copy executables
        copy(self, "hwinfo", src, os.path.join(self.package_folder, "bin"))
        copy(self, "check_hd", os.path.join(src, "src", "ids"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "convert_hd", os.path.join(src, "src", "ids"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "getsysinfo", src, os.path.join(self.package_folder, "bin"))
        copy(self, "mk_isdnhwdb", os.path.join(src, "src", "isdn", "cdb"),
             os.path.join(self.package_folder, "bin"))

        # Copy shared library (actual file + symlinks from src/)
        copy(self, "libhd.so.25.2", os.path.join(src, "src"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        # Create symlinks manually (conan copy doesn't handle symlinks well)
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        so25 = os.path.join(lib_dir, "libhd.so.25")
        if os.path.lexists(so25):
            os.remove(so25)
        os.symlink("libhd.so.25.2", so25)
        so = os.path.join(lib_dir, "libhd.so")
        if os.path.lexists(so):
            os.remove(so)
        os.symlink("libhd.so.25", so)

        # Copy static library
        copy(self, "libhd.a", os.path.join(src, "src"),
             os.path.join(self.package_folder, "lib"), keep_path=False)

        # Copy headers
        copy(self, "hd.h", os.path.join(src, "src", "hd"),
             os.path.join(self.package_folder, "include"))

        # Copy data files
        copy(self, "ISDN.CDB.*", os.path.join(src, "src", "isdn", "cdb"),
             os.path.join(self.package_folder, "share", "hwinfo"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["hd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        # Set runtime library path for system libuuid dependency
        uuid_so = glob.glob("/data/service/hnp/**/libuuid.so*", recursive=True)
        if uuid_so:
            uuid_dir = os.path.dirname(uuid_so[0])
            self.runenv_info.append("LD_LIBRARY_PATH", [uuid_dir])
