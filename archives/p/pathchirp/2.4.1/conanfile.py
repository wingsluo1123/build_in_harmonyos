#!/usr/bin/env python3
"""Conan package for the three pathChirp 2.4.1 command-line programs."""

import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches
from conan.tools.layout import basic_layout


class PathchirpConan(ConanFile):
    name = "pathchirp"
    version = "2.4.1"
    description = "UDP path available-bandwidth measurement tools"
    license = "Rice-University AND Maryland"
    homepage = "http://www.spin.rice.edu/Software/pathChirp/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    exports_sources = "patches/*"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        source_sets = {
            "pathchirp_run": ["pathchirp_run.c"],
            "pathchirp_snd": ["pathchirp_snd.c", "realtime.c", "hash.c"],
            "pathchirp_rcv": [
                "realtime.c", "pathchirp_rcv.c", "alloc_rcv.c",
                "chirps_rcv.c", "compute_bw_contextsw_rcv.c",
                "loss_reorder_rcv.c", "open_files_rcv.c",
                "parse_cmd_line_rcv.c", "signal_alrm_rcv.c",
                "control_rcv.c", "hash.c",
            ],
        }
        output_dir = os.path.join(self.source_folder, "Bin", "ohos")
        os.makedirs(output_dir, exist_ok=True)
        for name, sources in source_sets.items():
            source_args = " ".join(f"Src/{source}" for source in sources)
            output = f"Bin/ohos/{name}"
            # The 2003 source uses GNU89 inline linkage semantics.
            self.run(
                f"{cc} -std=gnu89 -O2 -fno-strict-aliasing -I. "
                f"{source_args} -o {output} -lm",
                cwd=self.source_folder,
            )

    def package(self):
        binary_dir = os.path.join(self.source_folder, "Bin", "ohos")
        for name in ("pathchirp_run", "pathchirp_snd", "pathchirp_rcv"):
            copy(self, name, src=binary_dir,
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"))
        copy(self, "pathchirp_snd.c", src=os.path.join(self.source_folder, "Src"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
