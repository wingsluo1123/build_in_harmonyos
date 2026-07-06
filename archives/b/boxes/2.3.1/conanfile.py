from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy
import os
import shutil
import glob

class BoxesConan(ConanFile):
    name = "boxes"
    version = "2.3.1"

    # Package type: application (standalone executable)
    package_type = "application"

    # Settings
    settings = "os", "arch", "compiler", "build_type"

    # export_sources: patches and compatibility layer files
    exports_sources = "patches/*", "files/*"

    def requirements(self):
        self.requires("pcre2/10.40")

    def configure(self):
        # Build only pcre2-32 (what boxes needs), static
        self.options["pcre2"].shared = False
        self.options["pcre2"].build_pcre2_8 = False
        self.options["pcre2"].build_pcre2_16 = False
        self.options["pcre2"].build_pcre2_32 = True
        self.options["pcre2"].build_pcre2grep = False

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        vendor = os.path.join(src, "vendor")
        os.makedirs(vendor, exist_ok=True)

        # ==================================================================
        # 1. Set up PCRE2 from Conan dependency
        #    The Makefile's flags_unix target hardcodes:
        #      -I../vendor/pcre2-10.40/ohos-install/include
        #      -L../vendor/pcre2-10.40/ohos-install/lib
        #    So we create that directory structure and copy pcre2 files in.
        # ==================================================================
        pcre2 = self.dependencies["pcre2"]
        pcre2_package_folder = pcre2.package_folder
        pcre2_inc_dir = os.path.join(pcre2_package_folder, "include")
        pcre2_lib_dir = os.path.join(pcre2_package_folder, "lib")

        pcre2_vendor_dir = os.path.join(vendor, "pcre2-10.40", "ohos-install")
        pcre2_vendor_inc = os.path.join(pcre2_vendor_dir, "include")
        pcre2_vendor_lib = os.path.join(pcre2_vendor_dir, "lib")
        os.makedirs(pcre2_vendor_inc, exist_ok=True)
        os.makedirs(pcre2_vendor_lib, exist_ok=True)

        # Copy pcre2 headers
        if os.path.isdir(pcre2_inc_dir):
            for f in os.listdir(pcre2_inc_dir):
                src_f = os.path.join(pcre2_inc_dir, f)
                if os.path.isfile(src_f):
                    shutil.copy2(src_f, os.path.join(pcre2_vendor_inc, f))

        # Copy pcre2 library (look for libpcre2-32.a)
        if os.path.isdir(pcre2_lib_dir):
            for f in os.listdir(pcre2_lib_dir):
                if "pcre2" in f.lower():
                    src_f = os.path.join(pcre2_lib_dir, f)
                    if os.path.isfile(src_f):
                        shutil.copy2(src_f, os.path.join(pcre2_vendor_lib, f))

        # Verify pcre2-32 library was copied
        pcre2_lib = os.path.join(pcre2_vendor_lib, "libpcre2-32.a")
        if not os.path.exists(pcre2_lib):
            # Try to find it anywhere in the vendor lib dir
            candidates = glob.glob(os.path.join(pcre2_vendor_lib, "*pcre2*32*"))
            if not candidates:
                raise Exception(f"pcre2-32 static library not found. Checked: {pcre2_vendor_lib}")

        # ==================================================================
        # 2. Create libunistring compatibility layer
        #    The Makefile's flags_unix target hardcodes:
        #      -I../vendor/libunistring-1.0/ohos-install/include
        #      -L../vendor/libunistring-1.0/ohos-install/lib
        # ==================================================================
        unistring_vendor_dir = os.path.join(vendor, "libunistring-1.0", "ohos-install")
        unistring_inc = os.path.join(unistring_vendor_dir, "include")
        unistring_lib = os.path.join(unistring_vendor_dir, "lib")
        os.makedirs(unistring_inc, exist_ok=True)
        os.makedirs(unistring_lib, exist_ok=True)

        # Copy compatibility headers from files/ directory
        files_dir = os.path.join(src, "files")
        if not os.path.exists(files_dir):
            # Fallback: search in source folder recursively
            for root, dirs, fns in os.walk(src):
                if "unitypes.h" in fns:
                    files_dir = root
                    break

        headers = ["unitypes.h", "uniconv.h", "unistr.h", "unictype.h", "localcharset.h", "unistdio.h", "uniwidth.h"]
        for hdr in headers:
            src_hdr = os.path.join(files_dir, hdr)
            if os.path.exists(src_hdr):
                shutil.copy2(src_hdr, os.path.join(unistring_inc, hdr))
            else:
                raise Exception(f"Header {hdr} not found in {files_dir}")

        # Compile compatibility library
        compat_src = os.path.join(files_dir, "libunistring_compat.c")
        if not os.path.exists(compat_src):
            raise Exception("libunistring_compat.c not found in " + files_dir)

        compat_obj = os.path.join(unistring_lib, "libunistring_compat.o")
        unistring_a = os.path.join(unistring_lib, "libunistring.a")

        self.run(f"clang -c {compat_src} -o {compat_obj} -I{unistring_inc} -O2 -Wno-implicit-function-declaration")
        self.run(f"llvm-ar rcs {unistring_a} {compat_obj}")

        # ==================================================================
        # 3. Build boxes using the original Makefile
        #    The flags_unix target sets up the vendor paths we created above.
        # ==================================================================
        globalconf = os.path.join(self.build_folder, "boxes-config")
        if not os.path.exists(globalconf):
            globalconf = os.path.join(src, "boxes-config")
        if not os.path.exists(globalconf):
            globalconf = "/data/storage/el2/base/haps/entry/files/boxes/boxes-config"

        self.run(
            f"make build "
            f"BOXES_PLATFORM=unix "
            f"CC=clang "
            f"LEX=flex "
            f"YACC=bison "
            f"CFLAGS_ADDTL='-include stddef.h -include localcharset.h' "
            f"GLOBALCONF='{globalconf}'",
            cwd=src
        )

    def package(self):
        # Copy the built executable
        src = self.source_folder
        boxes_bin = os.path.join(src, "out", "boxes")
        if os.path.exists(boxes_bin):
            copy(self, "boxes", src=os.path.join(src, "out"), dst=os.path.join(self.package_folder, "bin"))
        else:
            # Try alternate locations
            found = glob.glob(os.path.join(src, "**", "boxes"), recursive=True)
            for f in found:
                if os.path.isfile(f) and os.access(f, os.X_OK | os.R_OK):
                    copy(self, "boxes", src=os.path.dirname(f), dst=os.path.join(self.package_folder, "bin"))
                    break

        # Copy config file
        cfg = os.path.join(src, "boxes-config")
        if os.path.exists(cfg):
            copy(self, "boxes-config", src=src, dst=os.path.join(self.package_folder, "share/boxes"))

    def package_info(self):
        self.cpp_info.libs = []
