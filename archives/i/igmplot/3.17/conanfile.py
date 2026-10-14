#!/usr/bin/env python3
"""Conan recipe - IGMPlot 3.17 (custom C++ Makefile)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Upstream ships 35 official samples (samples/01_example .. samples/24_example)
# and the official runner source/scripts/IGMPLOT_test_samples.py.
#
# The runner is strictly sequential, and 15 of the 35 inputs are grid
# computations that need far more wall clock than a CI worker allows:
# measured on an x86-64 baseline, test08/test09/test10/test16 need ~88 s each,
# test23 ~100 s, and test11/test12/test14/test17/test20/test21/test22/test24/
# test34/test35 exceed 120 s each (test11 alone reports ~3.5 % progress after
# 120 s, i.e. roughly one hour for a single sample).  `conan create` on the CI
# worker has a 3600 s budget and contributors are not allowed to touch
# ci/config/build_timeouts.txt (review rule 21), so the recipe runs the
# 20-sample tier that completes in seconds and asserts the exact count.
#
# The remaining inputs stay untouched in samples/ and their measured runtime is
# documented in the PR description; nothing is deleted, renamed or rewritten.
CI_SAMPLES = (
    "01_example/test01",
    "01_example/test02",
    "02_example/test03",
    "03_example/test04",
    "03_example/test05",
    "03_example/test06",
    "03_example/test07",
    "05_example/test13",
    "07_example/test15",
    "09_example/test18",
    "10_example/test19",
    "16_example/test25",
    "17_example/test26",
    "18_example/test27",
    "19_example/test28",
    "20_example/test29",
    "21_example/test30",
    "21_example/test31",
    "22_example/test32",
    "23_example/test33",
)


class IgmplotConan(ConanFile):
    name = "igmplot"
    version = "3.17"
    description = "Detect and prepare molecular interaction plots from electron density"
    license = "CeCILL-C"
    homepage = "http://igmplot.univ-reims.fr/"
    url = "http://igmplot.univ-reims.fr/download/IGMPlot-3.17.zip"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ci_sample_tree(self):
        """Mirror the CI-tier samples into a clean root for the official runner."""
        samples_root = os.path.join(self.source_folder, "samples")
        ci_root = os.path.join(self.source_folder, "samples-ci")
        for rel in CI_SAMPLES:
            src = os.path.join(samples_root, rel)
            if not os.path.isdir(src):
                raise ConanException(f"upstream sample is missing: {rel}")
            dst = os.path.join(ci_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst)
        return ci_root

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or "clang++"

        # IGMPlot has no configure script.  Pass the compiler explicitly and
        # build without OpenMP, which is not part of the OHOS toolchain.
        self.run(
            f"make -j1 CppCompilerExec={cxx} OpenMP=NO",
            cwd=os.path.join(self.source_folder, "source"),
        )

        # Run the official runner over the CI-tier samples.  The runner always
        # exits 0, so the result is re-checked below: exactly len(CI_SAMPLES)
        # "OK" lines and no "KO see" line, otherwise the build fails.
        ci_root = self._ci_sample_tree()
        self.run(
            "python3 source/scripts/IGMPLOT_test_samples.py "
            f"source/IGMPLOT {os.path.basename(ci_root)} "
            "> igmplot-samples.log 2>&1",
            cwd=self.source_folder,
        )
        self.run(
            "python3 -c 'import pathlib,sys; "
            "lines=pathlib.Path(\"igmplot-samples.log\").read_text("
            "encoding=\"utf-8\",errors=\"replace\").splitlines(); "
            "ok=sum(line.endswith(\" OK\") for line in lines); "
            "bad=sum(\"KO see\" in line for line in lines); "
            f"sys.exit(0 if ok == {len(CI_SAMPLES)} and bad == 0 else 1)'",
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "IGMPLOT",
            src=os.path.join(self.source_folder, "source"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
