#!/usr/bin/env python3
"""Conan recipe — mwrap 1.3.5 (HarmonyOS PC adaptation).

MWrap is a standalone MATLAB/Octave MEX gateway generator: the build
artifact is a single executable (package_type = "application", no
library component, hence no shared/static option).

Upstream provides a CMake build path (CMakeLists.txt) which requires
Bison + Flex at build time (find_package(BISON/FLEX REQUIRED) — the
tarball ships only mwrap.y / mwrap.l, no pre-generated parser).
Both tools are consumed via tool_requires from the ohpcd artifact
registry (W0 verified: bison/3.8.2 rev 27704878, flex/2.6.4 rev
dae89385), so the CI clean environment needs no system bison/flex.

MEX compilation backends (MWRAP_COMPILE_MEX / MWRAP_BUILD_EXAMPLES)
stay OFF: they need MATLAB / Octave toolchains that do not exist on
OHOS or in CI.  Upstream CTest cases (mwrap.test_syntax,
mwrap.test_typecheck) run inside build() via cmake.test().
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class MwrapConan(ConanFile):
    name = "mwrap"
    version = "1.3.5"
    description = "MWrap — MEX gateway generator for MATLAB and Octave"
    license = "MIT"
    homepage = "https://github.com/zgimbutas/mwrap"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Pure code generator: MEX backends need MATLAB/Octave, which are
        # unavailable on OHOS and in CI.  Keep the default OFF state explicit.
        tc.variables["MWRAP_BUILD_EXAMPLES"] = False
        tc.variables["MWRAP_COMPILE_MEX"] = False
        tc.generate()
        bison_pkg = self.dependencies.build.get("bison")
        if bison_pkg and bison_pkg.package_folder:
            self._bison_pkgdatadir = os.path.join(
                bison_pkg.package_folder, "share", "bison")

    def build(self):
        apply_conandata_patches(self)
        # The ohpcd bison/3.8.2 tool package ships a binary compiled with
        # datarootdir=prefix=/ (it looks for /share/bison/m4sugar/m4sugar.m4,
        # which does not exist on OHOS).  Point BISON_PKGDATADIR at the
        # package's own share/bison so the relocatable binary finds its data
        # files.  Verified locally: without it bison exits with "cannot open:
        # No such file or directory"; with it the parser generates fine.
        pkgdatadir = getattr(self, "_bison_pkgdatadir", None)
        if pkgdatadir:
            os.environ["BISON_PKGDATADIR"] = pkgdatadir
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试 ──
        # 上游共 12 个测试条目：CTest 默认配置注册 2 个日志比对用例
        #（mwrap.test_syntax / mwrap.test_typecheck，OHOS 可实跑）；另有 9 个
        # mwrap_add_mex MEX 生成目标 + 1 个 mwrap.octave.test_all Octave 运行时
        # 用例，仅 MWRAP_COMPILE_MEX=ON 且存在 MATLAB/Octave 工具链时注册，
        # OHOS/CI 无此环境，环境受限不参与（非删除/跳过）。
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
