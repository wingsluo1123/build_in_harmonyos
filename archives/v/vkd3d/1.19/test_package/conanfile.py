#!/usr/bin/env python3
"""Conan test_package for vkd3d 1.19 — Conan L1 official test.

Consumer view: an external program that links the *installed* vkd3d package and
exercises the public shader-compiler API declared in ``vkd3d_shader.h``.

The test deliberately uses the part of vkd3d that needs **no GPU and no Vulkan
device** — the standalone DXBC/DXIL to SPIR-V compiler front end — so that it is
a real, self-contained assertion on the packaged artefact:

1. ``vkd3d_shader_compile()`` compiles HLSL source to a DXBC/TPF container
   (``vkd3d_shader_hlsl_source_info``, profile ``vs_5_0``).
2. ``vkd3d_shader_compile()`` compiles that container to SPIR-V binary.
3. The resulting blob must start with the SPIR-V magic number ``0x07230203``.
4. A deliberately invalid source must NOT be reported as ``VKD3D_OK``.

``test()`` really runs the compiled binary (R34/PF3: no print-only stub).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Vkd3dTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries directly in some
        # environments; wrap with bash (same proven pattern as libmaxminddb/zlib).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if os.path.exists(bash):
            self.run('%s -c "./test_vkd3d"' % bash, env="conanrun")
        else:
            self.run("./test_vkd3d", env="conanrun")
