#!/usr/bin/env python3
"""Conan recipe — nanopb 0.4.9.1 (CMake static runtime library)."""

import os
import importlib.util
import shlex
import stat
import shutil
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class NanopbConan(ConanFile):
    name = "nanopb"
    version = "0.4.9.1"
    description = "Protocol Buffers implementation with small code size"
    license = "zlib"
    homepage = "https://jpa.kapsi.fi/nanopb/"
    url = "https://github.com/nanopb/nanopb"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_STATIC_LIBS"] = True
        tc.variables["nanopb_BUILD_RUNTIME"] = True
        tc.variables["nanopb_BUILD_GENERATOR"] = False

        # CMake does not recognize OHOS as a target platform. The Conan
        # profile still supplies the actual OHOS compiler and architecture.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if self.settings.os == "OHOS":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        self._prepare_test_tools()

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Nanopb's upstream official suite is maintained as SCons tests.
        # Keep it in the Conan build so CI can verify the complete runtime.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "cc") if compilers else "cc"
        cxx = compilers.get("cpp", "c++") if compilers else "c++"
        protoc_path = shutil.which("protoc")
        if protoc_path:
            protoc = protoc_path
        else:
            # SCons treats PROTOC as the path to one executable. Passing
            # "python -m grpc_tools.protoc" directly works in a shell, but
            # SCons then tries to execute the whole string as a file and
            # fails on clean OHOS workers. Create a tiny executable wrapper
            # in the Conan build folder so SCons gets a real path.
            protoc = os.path.join(self.build_folder, "nanopb-protoc")
            save(
                self,
                protoc,
                "#!" + sys.executable + "\n"
                "import runpy\n"
                'runpy.run_module("grpc_tools.protoc", run_name="__main__")\n',
            )
            os.chmod(
                protoc,
                os.stat(protoc).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
        tests_dir = shlex.quote(self.source_folder + "/tests")
        plugin = shlex.quote(
            "--plugin=protoc-gen-nanopb="
            + self.source_folder
            + "/generator/protoc-gen-nanopb "
        )
        command = (
            "{python} -m SCons -C {tests} CC={cc} CXX={cxx} PROTOC={protoc} "
            "PROTOCFLAGS={plugin} NOVALGRIND=1 NODEFARGS=1"
        ).format(
            python=shlex.quote(sys.executable),
            tests=tests_dir,
            cc=shlex.quote(str(cc)),
            cxx=shlex.quote(str(cxx)),
            protoc=shlex.quote(protoc),
            plugin=plugin,
        )
        self.run(command)

    def _prepare_test_tools(self):
        """Make SCons and the Python protoc fallback visible to test commands."""

        configured_dir = os.environ.get("CONAN_TEST_TOOLS_DIR")
        repo_root = os.environ.get("CI_REPO_ROOT")
        tool_dirs = [
            path
            for path in (
                configured_dir,
                os.path.join(repo_root, ".ci-test-tools") if repo_root else None,
                os.path.join(
                    os.path.expanduser("~"),
                    ".cache",
                    "build_in_harmonyos",
                    "test-tools",
                ),
            )
            if path
        ]
        tool_dirs = list(dict.fromkeys(tool_dirs))

        def has_module(module_name):
            try:
                return importlib.util.find_spec(module_name) is not None
            except (ImportError, ModuleNotFoundError):
                return False

        def has_module_in_dirs(module_name):
            return any(
                os.path.isdir(os.path.join(path, module_name))
                for path in tool_dirs
            )

        local_tools = os.path.join(self.build_folder, "test-tools")
        os.makedirs(local_tools, exist_ok=True)
        python = shlex.quote(sys.executable)
        target = shlex.quote(local_tools)

        if not has_module("SCons") and not has_module_in_dirs("SCons"):
            self.output.info("SCons not found; installing the pinned test tool")
            self.run(
                f"{python} -m pip install --target {target} --upgrade "
                "--disable-pip-version-check --no-warn-script-location "
                "SCons==4.10.0"
            )
            tool_dirs.insert(0, local_tools)

        if not shutil.which("protoc") and not has_module("grpc_tools") and not has_module_in_dirs("grpc_tools"):
            self.output.info("protoc not found; installing the pinned Python fallback")
            self.run(
                f"{python} -m pip install --target {target} --upgrade "
                "--disable-pip-version-check --no-deps protobuf==7.35.1 "
                "grpcio-tools==1.81.0"
            )
            if local_tools not in tool_dirs:
                tool_dirs.insert(0, local_tools)

        pythonpath = [path for path in tool_dirs if os.path.isdir(path)]
        existing_pythonpath = os.environ.get("PYTHONPATH")
        if existing_pythonpath:
            pythonpath.append(existing_pythonpath)
        if pythonpath:
            os.environ["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(pythonpath))
            self.output.info(
                "Nanopb test-tool PYTHONPATH: "
                + os.environ["PYTHONPATH"]
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include/nanopb"]
        self.cpp_info.libs = ["protobuf-nanopb"]
        self.cpp_info.set_property("cmake_file_name", "nanopb")
        self.cpp_info.set_property(
            "cmake_target_name", "nanopb::protobuf-nanopb-static"
        )
