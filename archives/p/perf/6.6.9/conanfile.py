import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerfConan(ConanFile):
    name = "perf"
    version = "6.6.9"
    description = "Linux performance analysis tool (perf) from kernel 6.6.9"
    license = "GPL-2.0-only"
    homepage = "https://perf.wiki.kernel.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.settings.os in ("Linux", "OHOS"):
            self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Fix shebang lines: HarmonyOS has no /bin/bash
        bash_path = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.exists("/bin/bash"):
            tools_dir = os.path.join(self.source_folder, "tools")
            self.run(
                f"find {tools_dir}/perf {tools_dir}/build {tools_dir}/scripts {tools_dir}/lib "
                f"-type f -exec grep -l '#!/bin/bash' {{}} \\; 2>/dev/null | "
                f"xargs sed -i 's|#!/bin/bash|#!{bash_path}|g' || true"
            )

        # Fix open() mode bits: OHOS fortify headers reject open(path, O_RDONLY, O_NONBLOCK)
        daemon_c = os.path.join(self.source_folder, "tools", "perf", "builtin-daemon.c")
        if os.path.exists(daemon_c):
            self.run(
                f"sed -i 's/open(ack_path, O_RDONLY, O_NONBLOCK)/"
                f"open(ack_path, O_RDONLY | O_NONBLOCK)/' {daemon_c}"
            )

        # Build perf from tools/perf/ in the kernel source tree
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # Ensure gcc symlink exists (kernel build system uses gcc for host tools)
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        gcc_link = os.path.join(bin_dir, "gcc")
        if not os.path.exists(gcc_link):
            os.symlink(cc, gcc_link)
        gxx_link = os.path.join(bin_dir, "g++")
        if not os.path.exists(gxx_link):
            os.symlink(cxx, gxx_link)

        env = [
            f"CC={cc}",
            f"CXX={cxx}",
            f"HOSTCC={cc}",
            f"HOSTCXX={cxx}",
            f"PATH={bin_dir}:{os.environ.get('PATH', '')}",
            f"TMPDIR={os.environ.get('TMPDIR', '/tmp')}",
        ]

        # R9: Use JOBS=1 to avoid mkfifo (not supported on HarmonyOS HMDFS)
        # NO_LIBELF: elfutils not available as prebuilt for OHOS
        # NO_LIBTRACEEVENT: libtraceevent not available on OHOS platform
        self.run(
            f"make -C {os.path.join(self.source_folder, 'tools', 'perf')} "
            f"JOBS=1 NO_LIBELF=1 NO_LIBTRACEEVENT=1 "
            f"CC={cc} HOSTCC={cc}",
            env=env
        )

    def package(self):
        # Copy the perf binary
        copy(self, "perf", os.path.join(self.source_folder, "tools", "perf"),
             os.path.join(self.package_folder, "bin"))
        # Copy perf helper scripts
        for script in ["perf-archive", "perf-iostat"]:
            src = os.path.join(self.source_folder, "tools", "perf", script)
            if os.path.exists(src):
                copy(self, script, os.path.dirname(src),
                     os.path.join(self.package_folder, "bin"))
        # Copy dlfilters
        dlfilters_src = os.path.join(self.source_folder, "tools", "perf", "dlfilters")
        if os.path.exists(dlfilters_src):
            copy(self, "*.so", dlfilters_src,
                 os.path.join(self.package_folder, "lib", "perf", "dlfilters"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
