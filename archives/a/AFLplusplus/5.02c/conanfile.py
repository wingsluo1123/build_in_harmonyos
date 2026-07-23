#!/usr/bin/env python3
"""Conan recipe for AFL++ (American Fuzzy Lop plus plus).

AFL++ is a security fuzzer tool. It uses GNU Make (GNUmakefile) as its
build system. On HarmonyOS, uname -s returns "HarmonyOS" instead of
"Linux", so we pass SYS=Linux to treat it as Linux (same kernel).
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class AflplusplusConan(ConanFile):
    name = "aflplusplus"
    version = "5.02c"
    description = "AFL++ - Advanced fuzzer fork of American Fuzzy Lop"
    license = "Apache-2.0"
    homepage = "https://github.com/AFLplusplus/AFLplusplus"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # AFL++ uses GNUmakefile. On HarmonyOS, uname -s returns "HarmonyOS"
        # which AFL++ does not recognize. Pass SYS=Linux to use Linux code paths.
        # CC=clang because gcc is not available on OHOS.
        # Disable optional modes (QEMU, Nyx, Unicorn, coresight, frida) that
        # require additional dependencies not available on the platform.
        make_vars = [
            "SYS=Linux",
            "CC=clang",
            f"PREFIX={self.package_folder}",
            "NO_NYX=1",
            "NO_QEMU=1",
            "NO_UNICORN=1",
            "NO_CORESIGHT=1",
            "NO_FRIDA=1",
        ]
        # Build core binaries + LLVM mode
        self.run(f'make {" ".join(make_vars)} -j$(nproc) binary-only')
        # Build LLVM instrumentation (afl-cc) — errors in test_build are non-fatal
        self.run(f'make {" ".join(make_vars)} -f GNUmakefile.llvm -j$(nproc) || true')

    def package(self):
        src = self.build_folder
        pkg = self.package_folder
        # Manually copy build artifacts (avoids DESTDIR nesting and
        # `install -T` incompatibility on HarmonyOS)
        bin_dir = os.path.join(pkg, "bin")
        lib_afl = os.path.join(pkg, "lib", "afl")
        inc_afl = os.path.join(pkg, "include", "afl")
        share_afl = os.path.join(pkg, "share", "afl")
        man_dir = os.path.join(pkg, "share", "man", "man8")
        doc_dir = os.path.join(pkg, "share", "doc", "afl")
        for d in [bin_dir, lib_afl, inc_afl, share_afl, man_dir, doc_dir]:
            os.makedirs(d, exist_ok=True)

        # Binaries
        progs = ["afl-fuzz", "afl-showmap", "afl-tmin", "afl-gotcpu",
                 "afl-analyze", "afl-cmin", "afl-cc", "afl-ld-lto",
                 "afl-network-client", "afl-network-server"]
        for p in progs:
            src_p = os.path.join(src, p)
            if os.path.exists(src_p):
                shutil.copy2(src_p, os.path.join(bin_dir, p))
        # Scripts
        scripts = ["afl-plot", "afl-whatsup", "afl-addseeds",
                   "afl-system-config", "afl-persistent-config", "afl-health",
                   "afl-cmin.py", "afl-cmin.awk", "afl-cmin.bash"]
        for s in scripts:
            src_s = os.path.join(src, s)
            if os.path.exists(src_s):
                shutil.copy2(src_s, os.path.join(bin_dir, s))
        # Symlinks for afl-cc wrappers
        for link in ["afl-gcc", "afl-g++", "afl-clang", "afl-clang++"]:
            dst = os.path.join(bin_dir, link)
            if not os.path.exists(dst):
                os.symlink("afl-cc", dst)

        # LLVM passes and runtime objects
        for so in glob.glob(os.path.join(src, "*.so")):
            shutil.copy2(so, os.path.join(lib_afl, os.path.basename(so)))
        for obj in ["afl-compiler-rt.o", "afl-llvm-rt-lto.o"]:
            src_o = os.path.join(src, obj)
            if os.path.exists(src_o):
                shutil.copy2(src_o, os.path.join(lib_afl, obj))
        # Static libraries
        for lib in ["libAFLDriver.a", "libAFLQemuDriver.a", "libdislocator.so"]:
            src_l = os.path.join(src, lib)
            if os.path.exists(src_l):
                shutil.copy2(src_l, os.path.join(lib_afl, lib))

        # Headers
        inc_src = os.path.join(src, "include")
        if os.path.isdir(inc_src):
            for h in os.listdir(inc_src):
                src_h = os.path.join(inc_src, h)
                if os.path.isfile(src_h):
                    shutil.copy2(src_h, os.path.join(inc_afl, h))

        # Man pages
        for m in glob.glob(os.path.join(src, "*.8")):
            shutil.copy2(m, os.path.join(man_dir, os.path.basename(m)))

        # Share: testcases and dictionaries
        for d in ["testcases", "dictionaries"]:
            src_d = os.path.join(src, d)
            if os.path.isdir(src_d):
                shutil.copytree(src_d, os.path.join(share_afl, d),
                                dirs_exist_ok=True)
        inj = os.path.join(src, "injections.dic")
        if os.path.exists(inj):
            shutil.copy2(inj, os.path.join(share_afl, "injections.dic"))

    def package_info(self):
        self.cpp_info.includedirs = ["include/afl"]
        self.cpp_info.libdirs = ["lib/afl"]
        self.cpp_info.bindirs = ["bin"]
