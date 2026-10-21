#!/usr/bin/env python3
"""Conan test_package for vtr 9.0.0 -- L1 consumer test.

VTR is an application (a CAD tool suite), not a library, so this test does not
link against anything: it drives the *installed* flow end to end and asserts on
the artifacts that come out.  Running `--version` would prove nothing here.

The test deliberately uses VTR's OWN bundled benchmark circuit and architecture
(k6_N10_mem32K_40nm.xml, single_wire.v - the pair used by the upstream
`vtr_reg_basic` suite).  That makes it a test of the packaged tree as well as of
the binaries: had vtr_flow/benchmarks or vtr_flow/arch not been packaged, the
flow could not even start.

Stage-by-stage assertions live in assert_flow.py, which inspects the produced
.net/.place/.route artifacts and the VPR log, so a build that silently skipped
synthesis, packing, placement, routing or timing analysis cannot pass.

File location: archives/v/vtr/9.0.0/test_package/conanfile.py
"""
import os
import shutil

from conan import ConanFile


class VtrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _vtr_root(self):
        dep = self.dependencies["vtr"]
        root = dep.package_folder
        if not root:
            raise RuntimeError("vtr package folder is not available")
        return root

    def _python(self):
        # The flow is a Python program; use the interpreter running this recipe
        # so no PATH search can pick up a different one.
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found:
                return found
        return "python3"

    def test(self):
        root = self._vtr_root()
        flow = os.path.join(root, "vtr_flow", "scripts", "run_vtr_flow.py")
        circuit = os.path.join(root, "vtr_flow", "benchmarks", "verilog", "single_wire.v")
        arch = os.path.join(root, "vtr_flow", "arch", "timing", "k6_N10_mem32K_40nm.xml")

        for path in (flow, circuit, arch):
            if not os.path.isfile(path):
                raise RuntimeError("packaged VTR tree is incomplete, missing: " + path)

        temp_dir = os.path.join(self.build_folder, "vtr_test_run")
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

        # A real end-to-end CAD run:
        #   elaboration (parmys/yosys, or odin) -> ABC synthesis + tech mapping
        #   -> VPR packing -> placement -> routing -> timing analysis
        #
        # The interpreter is invoked DIRECTLY, never behind a shell.  With a
        # shell prefix ("<bash> <python3> <script> ...") the shell reads the
        # interpreter's ELF as a script and aborts with
        #     <python3>: cannot execute binary file        (exit 126)
        # No shell indirection is needed anyway: conan already runs the string
        # through a shell, and "sh -c 'python3 ...'" resolves the interpreter
        # by fork+exec in the kernel - no shell has to understand ELF.
        self.run(
            '"{}" "{}" "{}" "{}" -temp_dir "{}" -name test_package'.format(
                self._python(), flow, circuit, arch, temp_dir),
            env="conanrun")

        # Stage-level assertions on the artifacts and the VPR log.
        checker = os.path.join(self.recipe_folder, "assert_flow.py")
        self.run(
            '"{}" "{}" "{}"'.format(self._python(), checker, temp_dir),
            env="conanrun")
