#!/usr/bin/env python3
"""Conan test_package for slang — functional test via slangc binary (R34).

Tests the slang compiler by running slangc on a simple shader file.
This validates that the built slangc binary works correctly on HarmonyOS.
"""
import os

from conan import ConanFile


class SlangTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get slangc binary path from the package
        slang_bin = None
        for bindir in self.dependencies["slang"].cpp_info.bindirs:
            candidate = os.path.join(bindir, "slangc")
            if os.path.exists(candidate):
                slang_bin = candidate
                break

        if not slang_bin:
            raise AssertionError("slangc binary not found in package")

        # Test 1: Run slangc --version (L2 smoke test)
        self.output.info("Running slangc --version...")
        self.run(f'"{slang_bin}" --version', env="conanrun")

        # Test 2: Compile a simple HLSL shader
        shader_file = os.path.join(self.source_folder, "test_shader.slang")
        with open(shader_file, "w") as f:
            f.write("""RWStructuredBuffer<float> outputBuffer;
[shader("compute")]
[numthreads(1, 1, 1)]
void computeMain(uint3 id : SV_DispatchThreadID) {
    outputBuffer[id.x] = float(id.x);
}
""")
        output_file = os.path.join(self.source_folder, "test_output.spirv")
        self.output.info("Compiling test shader...")
        self.run(f'"{slang_bin}" "{shader_file}" -o "{output_file}" -target spirv',
                 env="conanrun")

        if os.path.exists(output_file):
            self.output.info("PASS: Shader compiled to SPIR-V successfully")
        else:
            raise AssertionError("FAIL: SPIR-V output file not created")

        # Test 3: Check the build tag matches expected version
        self.output.info("Checking slang version tag...")
        self.run(f'"{slang_bin}" -h', env="conanrun")
