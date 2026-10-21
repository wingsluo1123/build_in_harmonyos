#!/usr/bin/env python3
"""Conan recipe for target-factory 2.5 - Vitis AI DPU target description factory.

target-factory maps DPU target names / fingerprints to their hardware
description (bank groups, DPU versions, ISA versions) and is used by vart to
select the DPU runner configuration.  Upstream is a CMake project that builds
libtarget-factory plus the 3 test binaries when BUILD_TEST is enabled.
"""

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    copy,
)
import glob
import json
import os
import re
import subprocess

required_conan_version = ">=2.0"


class TargetFactoryConan(ConanFile):
    name = "target-factory"
    version = "2.5"
    description = "Vitis AI factory for DPU target description files (target name/fingerprint to hardware description)"
    license = "Apache-2.0"
    homepage = "https://github.com/Xilinx/Vitis-AI"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("unilog/2.5")
        # target_factory.hpp includes the generated target.pb.h, which in turn
        # includes google/protobuf headers.  protobuf stays private: its
        # registry recipe sets cmake_find_mode=none, so it cannot be wired
        # through cpp_info.requires without breaking CMakeDeps consumers (a
        # generated find_dependency(protobuf) would never resolve).
        self.requires("protobuf/21.12", visible=False)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The Debian orig tarball extracts its files at the archive root (no
        # single top-level directory), so no strip_root.
        get(self, **self.conan_data["sources"])

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TEST"] = True
        tc.variables["BUILD_PYTHON"] = False
        # The Conan protobuf package keeps upstream's CMake config files;
        # protobuf_generate_cpp is only defined with module compatibility on.
        tc.variables["protobuf_MODULE_COMPATIBLE"] = True
        protoc = os.path.join(
            self.dependencies["protobuf"].package_folder, "bin", "protoc"
        )
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = protoc
        tc.variables["CMAKE_SKIP_RPATH"] = True
        # HarmonyOS is not mapped to the Linux CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined: the library
        # gets no DT_SONAME (CI L5a) and install(EXPORT) marks the target
        # IMPORTED_NO_SONAME (CI L5c).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # unilog, glog and gflags are published without a DT_SONAME, so
        # linking CMakeDeps' imported targets would copy their absolute
        # package paths into our DT_NEEDED (CI L5b).  Hand the recipe the
        # names and search directories the patch links with instead.
        by_name = []
        libdirs = []
        for ref in ("unilog", "glog", "gflags"):
            dep = self.dependencies[ref]
            by_name.append(ref)
            libdirs.extend(
                os.path.join(dep.package_folder, d) for d in dep.cpp_info.libdirs
            )
        by_name.append("pthread")
        tc.variables["TARGET_FACTORY_SONAME_LIBS"] = ";".join(by_name)
        tc.variables["TARGET_FACTORY_SONAME_LIBDIRS"] = ";".join(libdirs)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _test_env(self):
        # The build tree has no install rpath (CMAKE_SKIP_RPATH), and the
        # test binaries are executed before packaging, so point the loader at
        # the build tree and every dependency package explicitly.
        env = os.environ.copy()
        libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    libdirs.append(lib)
        for so in glob.glob(
            os.path.join(self.build_folder, "**", "libtarget-factory.so*"),
            recursive=True,
        ):
            libdirs.append(os.path.dirname(so))
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + [env.get("LD_LIBRARY_PATH", "")]
        )
        return env

    def _run_upstream_tests(self):
        binaries = ["test_factory", "test_fingerprint", "test_lib_info"]
        marker = {
            "status": "failed",
            "framework": "executables",
            "command": "./test/{test_factory,test_fingerprint,test_lib_info}",
            "discovered": len(binaries),
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        passed = 0
        failed = 0
        try:
            found = {}
            for name in binaries:
                hits = glob.glob(
                    os.path.join(self.build_folder, "**", "test", name),
                    recursive=True,
                )
                if hits:
                    found[name] = hits[0]
            run_dir = os.path.join(self.build_folder, "test-run")
            os.makedirs(run_dir, exist_ok=True)

            test_env = self._test_env()

            def run(name, args):
                nonlocal passed, failed
                bin_path = found.get(name)
                if not bin_path:
                    failed += 1
                    self.output.warning(f"{name}: NOT FOUND")
                    return ""
                try:
                    out = subprocess.check_output(
                        [bin_path] + args,
                        cwd=run_dir,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=test_env,
                    )
                    passed += 1
                    self.output.info(f"{name} PASSED: {out[-1200:]}")
                    return out
                except subprocess.CalledProcessError as exc:
                    failed += 1
                    self.output.warning(
                        f"{name} FAILED rc={exc.returncode}: "
                        f"{(exc.output or '')[-2000:]}"
                    )
                    return ""

            factory_out = run("test_factory", ["DPUCAHX8H_ISA2"])
            match = re.search(r"fingerprint\s+0x([0-9a-fA-F]+)", factory_out)
            if match:
                run("test_fingerprint", [match.group(1)])
            else:
                failed += 1
                self.output.warning(
                    "could not read the fingerprint from test_factory output"
                )
            run("test_lib_info", [])

            marker.update(
                {
                    "status": "passed" if failed == 0 else "failed",
                    "executed": passed + failed,
                    "passed": passed,
                    "failed": failed,
                }
            )
        except Exception as exc:  # pragma: no cover - build-time diagnostics
            failed += 1
            marker["reason"] = str(exc)
            self.output.warning(f"upstream test execution failed: {exc}")
        msg = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker)}"
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as fh:
                json.dump(marker, fh)
        except OSError:
            pass
        if failed:
            raise ConanException(
                "target-factory upstream tests failed: "
                + f"{failed} failure(s), see the HMBS marker above"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "Copyright.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["target-factory"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "target-factory")
        self.cpp_info.set_property(
            "cmake_target_name", "target-factory::target-factory"
        )
        # protobuf is deliberately not listed: its registry package sets
        # cmake_find_mode=none, so CMakeDeps generates no config for it and a
        # find_dependency(protobuf) would always fail for consumers.  The
        # static protobuf archive is already linked into libtarget-factory;
        # consumers that include the generated target.pb.h locate protobuf's
        # own CMake config themselves (see test_package).
        self.cpp_info.requires = ["unilog::unilog"]
