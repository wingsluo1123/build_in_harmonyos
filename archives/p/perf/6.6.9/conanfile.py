#!/usr/bin/env python3
"""Conan recipe for perf 6.6.9 — Linux performance analysis tool.

perf is part of the Linux kernel source tree (tools/perf/).
It uses a custom Makefile-based build system.

This recipe:
1. Downloads Linux 6.6.9 kernel (for perf) and Linux 5.15 kernel (for libtraceevent)
2. Patches libtraceevent to remove kernel header dependencies
3. Builds libtraceevent as a static library
4. Patches perf to fix qsort_r (not available on OHOS/musl)
5. Builds perf with clang, WERROR=0
6. Packages the perf binary
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, patch as conan_patch
from conan.tools.layout import basic_layout


class PerfConan(ConanFile):
    name = "perf"
    version = "6.6.9"
    description = "Linux performance analysis tool (perf)"
    license = "GPL-2.0-only"
    homepage = "https://perf.wiki.kernel.org/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.settings.os in ("Linux", "OHOS"):
            # elfutils pulls in zlib, bzip2, zstd, etc. transitively
            self.requires("elfutils/0.195")
            self.requires("slang/2.3.3")
            self.requires("openssl/1.1.1w")
            self.requires("libcap/2.69")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Download main source (Linux 6.6.9 kernel)
        get(self, **self.conan_data["sources"]["linux_6_6_9"], strip_root=True)
        # Download libtraceevent source (from Linux 5.15 kernel)
        get(self, **self.conan_data["sources"]["linux_5_15"], strip_root=True,
            destination="libtraceevent_src")

    def _get_dep_includes(self):
        """Collect include paths from all dependencies."""
        includes = []
        libs = []
        for dep_name in self.deps_cpp_info.deps:
            dep = self.deps_cpp_info[dep_name]
            for inc in dep.include_paths:
                if inc not in includes:
                    includes.append(inc)
            for lib in dep.lib_paths:
                if lib not in libs:
                    libs.append(lib)
        return includes, libs

    def build(self):
        # Apply conandata patches (qsort_r fix for the 6.6.9 kernel)
        apply_conandata_patches(self)

        # Gather dependency include paths
        dep_includes, dep_libs = self._get_dep_includes()
        include_flag = " ".join(f"-I{p}" for p in dep_includes)
        lib_path = ":".join(dep_libs)

        # Step 1: Build libtraceevent from 5.15 kernel source
        # The 5.15 kernel source is extracted to libtraceevent_src/
        te_base = os.path.join(self.build_folder, "libtraceevent_src")
        # Find the traceevent directory
        te_src = None
        for root, dirs, files in os.walk(te_base):
            if "event-parse.c" in files and "trace-seq.c" in files:
                te_src = root
                break
        if not te_src:
            # Try standard path
            te_src = os.path.join(te_base, "linux-5.15", "tools", "lib", "traceevent")
            if not os.path.isdir(te_src):
                te_src = os.path.join(te_base, "tools", "lib", "traceevent")

        te_install = os.path.join(self.build_folder, "libtraceevent_install")
        os.makedirs(os.path.join(te_install, "lib"), exist_ok=True)
        os.makedirs(os.path.join(te_install, "include", "traceevent"), exist_ok=True)
        os.makedirs(os.path.join(te_install, "lib", "pkgconfig"), exist_ok=True)

        # Apply libtraceevent patches manually
        te_patch = os.path.join(self.recipe_folder, "patches", "9001-libtraceevent-remove-kernel-deps.patch")
        if os.path.exists(te_patch):
            conan_patch(self, te_patch, patch_directory=te_src)

        # Build libtraceevent
        te_sources = [
            "event-parse.c", "event-plugin.c", "trace-seq.c",
            "parse-filter.c", "parse-utils.c", "kbuffer-parse.c",
            "tep_strerror.c", "event-parse-api.c"
        ]
        te_headers = ["event-parse.h", "event-utils.h", "kbuffer.h", "trace-seq.h"]

        cc = "clang"
        cflags = "-fPIC -O2 -std=gnu99 -I."
        obj_files = []
        for src in te_sources:
            src_path = os.path.join(te_src, src)
            obj_path = os.path.join(te_src, src.replace(".c", ".o"))
            self.run(f'{cc} {cflags} -c "{src_path}" -o "{obj_path}"')
            obj_files.append(obj_path)

        te_lib = os.path.join(te_install, "lib", "libtraceevent.a")
        self.run(f'llvm-ar rcs "{te_lib}" {" ".join(obj_files)}')

        for hdr in te_headers:
            src_h = os.path.join(te_src, hdr)
            dst_h = os.path.join(te_install, "include", "traceevent", hdr)
            if os.path.exists(src_h):
                shutil.copy2(src_h, dst_h)

        # Create pkg-config file
        pc_content = f"""prefix={te_install}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: libtraceevent
Description: Linux trace event parsing library
Version: 1.1.0
Libs: -L${{libdir}} -ltraceevent
Cflags: -I${{includedir}}/traceevent
"""
        with open(os.path.join(te_install, "lib", "pkgconfig", "libtraceevent.pc"), "w") as f:
            f.write(pc_content)

        # Step 2: Build perf
        # Find the perf source directory in the extracted 6.6.9 kernel
        perf_src = os.path.join(self.build_folder, "linux-6.6.9", "tools", "perf")
        if not os.path.isdir(perf_src):
            perf_src = os.path.join(self.build_folder, "tools", "perf")

        env = os.environ.copy()
        env["PKG_CONFIG_PATH"] = os.path.join(te_install, "lib", "pkgconfig")
        if lib_path:
            env["LD_LIBRARY_PATH"] = lib_path + ":" + env.get("LD_LIBRARY_PATH", "")

        extra_cflags = f"-D__kernel_sa_family_t=sa_family_t {include_flag}".strip()

        self.run(
            f'make -C "{perf_src}" CC={cc} HOSTCC={cc} WERROR=0 '
            f'EXTRA_CFLAGS="{extra_cflags}" -j1',
            env=env
        )

    def package(self):
        # Find the perf source directory
        perf_src = os.path.join(self.build_folder, "linux-6.6.9", "tools", "perf")
        if not os.path.isdir(perf_src):
            perf_src = os.path.join(self.build_folder, "tools", "perf")

        self.copy("perf", dst="bin", src=perf_src)
        self.copy("perf-read-vdso32", dst="bin", src=perf_src)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
