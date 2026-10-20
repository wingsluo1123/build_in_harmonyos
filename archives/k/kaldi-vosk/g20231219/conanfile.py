#!/usr/bin/env python3
"""Kaldi Vosk CPU libraries (CMake), native tests and one OpenFST runtime."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class KaldiVoskConan(ConanFile):
    name = "kaldi-vosk"
    version = "g20231219"
    description = "Vosk Kaldi fork: native CPU features, models, training libraries and streaming WFST decoding"
    license = "Apache-2.0"
    homepage = "https://github.com/alphacep/kaldi"
    url = "https://github.com/alphacep/kaldi"
    topics = ("speech-recognition", "kaldi", "vosk", "wfst", "openblas")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True,
                       "openfst/*:shared": False, "openfst/*:fPIC": True}
    exports = "components.json"
    exports_sources = "licenses/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This recipe supports the Linux and OHOS CPU builds")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("The validated OHOS architecture is armv8")
        if self.dependencies["openfst"].options.shared:
            raise ConanInvalidConfiguration("The recipe uses the published PIC static OpenFST package")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Shared Kaldi owns libfst.a exactly once in libkaldi-fst-runtime.so.
        # Consumers inherit its headers, but must not re-link the archive.
        self.requires("openfst/1.8.4", headers=True, libs=not bool(self.options.shared),
                      transitive_headers=True, transitive_libs=not bool(self.options.shared))
        self.requires("openblas/0.3.34", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self, generator="Ninja")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        ninja = Path(compilers.get("c", "clang")).parent / "ninja"
        if not ninja.is_file():
            ninja = Path(shutil.which("ninja") or "ninja")
        subprocess.run([str(ninja), "--version"], check=True)
        tc.variables["CMAKE_MAKE_PROGRAM"] = str(ninja)
        tc.variables["Python3_EXECUTABLE"] = sys.executable
        tc.variables["KALDI_VERSION"] = self.version
        tc.variables["KALDI_CONFIG_VERSION"] = "2023.12.19"
        tc.variables["KALDI_BUILD_EXE"] = False
        tc.variables["KALDI_BUILD_TEST"] = True
        tc.variables["MATHLIB"] = "OpenBLAS"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_CUDA"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_CUDAToolkit"] = True
        if self.options.shared:
            tc.variables["KALDI_OPENFST_STATIC_LIBRARY"] = str(
                Path(self.dependencies["openfst"].package_folder) / "lib/libfst.a")
        tc.generate()

    def _environment(self):
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("OPENBLAS_NUM_THREADS", "1")
        env.define("OMP_NUM_THREADS", "1")
        tmp = Path(self.build_folder) / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        env.define("TMPDIR", str(tmp))
        runtime = [str(p.parent) for p in Path(self.build_folder).glob("src/*/*.so")]
        runtime.append(self.build_folder)
        runtime.extend(str(Path(dep.package_folder) / "lib")
                       for dep in self.dependencies.host.values() if dep.package_folder)
        for path in reversed(list(dict.fromkeys(runtime))):
            env.prepend_path("LD_LIBRARY_PATH", path)
        return env

    def _sign(self, paths):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration("binary-sign-tool is required for native OHOS execution")
        for path in sorted(set(map(str, paths))):
            subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                            "-selfSign", "1"], check=True)

    def build(self):
        apply_conandata_patches(self)
        with self._environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        reports = Path(self.build_folder) / "reports"
        reports.mkdir(exist_ok=True)
        with self._environment().vars(self).apply():
            ctest = shutil.which("ctest")
            listed = subprocess.run([ctest, "--test-dir", self.build_folder,
                                     "--show-only=json-v1"], capture_output=True, check=True)
            (reports / "upstream-inventory.json").write_bytes(listed.stdout)
            inventory = json.loads(listed.stdout)
            tests = inventory["tests"]
            if len(tests) != 125:
                raise ConanInvalidConfiguration(f"Expected 125 CPU upstream tests, discovered {len(tests)}")
            libraries = list(Path(self.build_folder).glob("src/*/*.so"))
            libraries += list(Path(self.build_folder).glob("*.so"))
            self._sign([t["command"][0] for t in tests] + libraries)
            command = [ctest, "--test-dir", self.build_folder, "--output-on-failure", "-j1",
                       "--timeout", "1200", "--output-junit", str(reports / "upstream.xml")]
            with (reports / "upstream.log").open("w", encoding="utf-8") as out:
                process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True)
                for line in process.stdout:
                    out.write(line)
                    out.flush()
                    self.output.info(line.rstrip())
                rc = process.wait()
            cases = ET.parse(reports / "upstream.xml").getroot().findall("testcase")
            passed = sum(c.find("failure") is None and c.find("skipped") is None for c in cases)
            skipped = sum(c.find("skipped") is not None for c in cases)
            failed = len(cases) - passed - skipped
            summary = dict(discovered=len(tests), executed=len(cases), passed=passed,
                           failed=failed, skipped=skipped, unexecuted=len(tests)-len(cases), rc=rc)
            (reports / "upstream-summary.json").write_text(json.dumps(summary, indent=2))
            if rc or failed or skipped or len(cases) != len(tests):
                raise ConanInvalidConfiguration(f"Upstream CPU tests failed: {summary}")
            self.output.info(f"UPSTREAM_TEST_RESULT: PASS={passed} FAIL={failed} SKIP={skipped} TOTAL={len(cases)}")

    def package(self):
        with self._environment().vars(self).apply():
            CMake(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.build_folder, "reports"),
             os.path.join(self.package_folder, "res", "verification"))
        if self.options.shared:
            copy(self, "OpenFST-COPYING", os.path.join(self.export_sources_folder, "licenses"),
                 os.path.join(self.package_folder, "licenses", "openfst"))
        self._sign(Path(self.package_folder).glob("lib/*.so"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kaldi-vosk")
        self.cpp_info.set_property("cmake_target_name", "kaldi-vosk::kaldi-vosk")
        components = json.loads((Path(self.recipe_folder) / "components.json").read_text())
        if self.options.shared:
            runtime = self.cpp_info.components["fst-runtime"]
            runtime.libs = ["kaldi-fst-runtime"]
            runtime.set_property("cmake_target_name", "Kaldi::fst-runtime")
            runtime.requires = ["openfst::openfst"]
        for name, dependencies in components.items():
            component = self.cpp_info.components[name]
            component.libs = ["kaldi-" + name]
            component.includedirs = ["include/kaldi"]
            component.defines = ["HAVE_OPENBLAS=1", "KALDI_NO_PORTAUDIO=1"]
            component.system_libs = ["m", "pthread", "dl"]
            component.requires = dependencies + ["openblas::openblas"]
            component.requires += ["fst-runtime"] if self.options.shared else ["openfst::openfst"]
            component.set_property("cmake_target_name", "Kaldi::" + name)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
