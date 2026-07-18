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
        source_data = self.conan_data["sources"]
        get(
            self,
            url=source_data["url"],
            sha256=source_data["sha256"],
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_STATIC_LIBS"] = True
        tc.variables["nanopb_BUILD_RUNTIME"] = True
        tc.variables["nanopb_BUILD_GENERATOR"] = False

        # CMake does not recognize OHOS as a target platform. The Conan
        # profile still supplies the actual OHOS compiler and architecture.
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.os) == "OHOS":
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
        real_cc = compilers.get("c", "cc") if compilers else "cc"
        real_cxx = compilers.get("cpp", "c++") if compilers else "c++"
        if self._is_ohos():
            # User-path .so files carry an HMDFS security label which rejects
            # Python dlopen even after ELF signing. Use native protoc and
            # sign the test executables produced by SCons instead.
            protoc = self._build_ohos_protoc(real_cc, real_cxx)
            # The upstream Python generator invokes a fallback subprocess as
            # ['protoc', ...] and does not inherit SCons' PROTOC construction
            # variable. Export the signed binary through PATH as well so that
            # nanopb_pb2.py generation uses the same OHOS-safe protoc.
            protoc_dir = os.path.dirname(protoc)
            os.environ["PROTOC"] = protoc
            os.environ["PATH"] = os.pathsep.join(
                path for path in (protoc_dir, os.environ.get("PATH", "")) if path
            )
            cc = self._make_ohos_compiler_wrapper(real_cc, "cc")
            cxx = self._make_ohos_compiler_wrapper(real_cxx, "cxx")
            os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
        else:
            cc = real_cc
            cxx = real_cxx
            protoc_path = shutil.which("protoc")
            if protoc_path:
                protoc = protoc_path
            else:
                # SCons needs a real executable path, not "python -m ...".
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
        shell_arg = ""
        if str(self.settings.os) == "OHOS":
            # SCons' POSIX platform defaults its construction SHELL variable
            # to the literal "sh" and invokes every action through it. The
            # OHOS worker provides bash at this path but does not provide a
            # /bin/sh-compatible command named "sh".
            shell = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or "/data/service/hnp/bin/bash"
            )
            shell_arg = " SHELL=" + shlex.quote(shell)
        command = (
            "{python} -m SCons -C {tests} CC={cc} CXX={cxx} PROTOC={protoc} "
            "PROTOCFLAGS={plugin} NOVALGRIND=1 NODEFARGS=1{shell_arg}"
        ).format(
            python=shlex.quote(sys.executable),
            tests=tests_dir,
            cc=shlex.quote(str(cc)),
            cxx=shlex.quote(str(cxx)),
            protoc=shlex.quote(protoc),
            plugin=plugin,
            shell_arg=shell_arg,
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

        if self._is_ohos():
            if not has_module("google.protobuf") and not has_module_in_dirs("google"):
                self.output.info(
                    "Python protobuf not found; installing the pinned pure-Python runtime"
                )
                self.run(
                    f"{python} -m pip install --target {target} --upgrade "
                    "--disable-pip-version-check --no-warn-script-location "
                    "--no-deps protobuf==7.35.1"
                )
                if local_tools not in tool_dirs:
                    tool_dirs.insert(0, local_tools)
        elif (
            not shutil.which("protoc")
            and not has_module("grpc_tools")
            and not has_module_in_dirs("grpc_tools")
        ):
            self.output.info("protoc not found; installing the pinned Python fallback")
            self.run(
                f"{python} -m pip install --target {target} --upgrade "
                "--disable-pip-version-check --no-warn-script-location "
                "--no-deps protobuf==7.35.1 grpcio-tools==1.81.0"
            )
            if local_tools not in tool_dirs:
                tool_dirs.insert(0, local_tools)

        # OHOS deliberately avoids importing native Python extensions from
        # user-writable paths. Its protoc is native and its generator uses
        # the pure-Python protobuf runtime.

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

    def _is_ohos(self):
        return str(self.settings.os).lower() == "ohos"

    def _build_ohos_protoc(self, cc, cxx):
        """Build and sign standalone protoc for the OHOS upstream tests."""
        protoc_source = self._prepare_ohos_protoc_source()
        protoc_build = os.path.join(self.build_folder, "nanopb-protoc-build")
        cmake = shutil.which("cmake") or "cmake"
        cmake_args = [
            cmake,
            "-S",
            protoc_source,
            "-B",
            protoc_build,
            "-G",
            "Unix Makefiles",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            "-DCMAKE_SYSTEM_NAME=Linux",
            "-DCMAKE_SYSTEM_PROCESSOR=aarch64",
            "-Dprotobuf_BUILD_TESTS=OFF",
            "-Dprotobuf_BUILD_SHARED_LIBS=OFF",
            "-Dprotobuf_BUILD_PROTOC_BINARIES=ON",
            "-Dprotobuf_WITH_ZLIB=OFF",
            "-DCMAKE_CXX_FLAGS=-stdlib=libc++",
        ]
        self.output.info("Building standalone OHOS protoc from protobuf source")
        self.run(" ".join(shlex.quote(str(arg)) for arg in cmake_args))
        self.run(
            " ".join(
                [
                    shlex.quote(cmake),
                    "--build",
                    shlex.quote(protoc_build),
                    "--target",
                    "protoc",
                    "--",
                    "-j1",
                ]
            )
        )

        protoc = os.path.join(protoc_build, "protoc")
        if not os.path.isfile(protoc):
            raise RuntimeError(f"protobuf build did not produce protoc: {protoc}")
        self._sign_ohos_elf(protoc)
        self._generate_ohos_nanopb_pb2(protoc, protoc_source)
        return protoc

    def _prepare_ohos_protoc_source(self):
        """Download protobuf only when the OHOS build actually needs protoc."""
        source_data = self.conan_data["sources"].get("protoc")
        if not source_data:
            raise RuntimeError("nanopb requires a protobuf source for OHOS protoc")

        protoc_source = os.path.join(self.source_folder, ".nanopb-protoc-source")
        if not os.path.isfile(os.path.join(protoc_source, "CMakeLists.txt")):
            get(
                self,
                url=source_data["url"],
                sha256=source_data["sha256"],
                destination=protoc_source,
                strip_root=True,
            )
        return protoc_source

    def _generate_ohos_nanopb_pb2(self, protoc, protobuf_source):
        """Pre-generate nanopb's Python bindings with the signed protoc."""
        proto_dir = os.path.join(self.source_folder, "generator", "proto")
        proto_file = os.path.join(proto_dir, "nanopb.proto")
        protobuf_include = os.path.join(protobuf_source, "src")
        generated = os.path.join(proto_dir, "nanopb_pb2.py")
        command = [
            protoc,
            f"--python_out={proto_dir}",
            proto_file,
            f"-I{proto_dir}",
            f"-I{protobuf_include}",
        ]
        self.output.info("Generating nanopb Python bindings with signed OHOS protoc")
        self.run(" ".join(shlex.quote(str(arg)) for arg in command))
        if not os.path.isfile(generated):
            raise RuntimeError(f"protoc did not generate nanopb Python bindings: {generated}")

    def _make_ohos_compiler_wrapper(self, compiler, name):
        """Sign each SCons test executable immediately after linking."""
        wrapper = os.path.join(self.build_folder, f"nanopb-{name}-signed")
        save(
            self,
            wrapper,
            "#!" + sys.executable + "\n"
            "import os\n"
            "import shutil\n"
            "import stat\n"
            "import subprocess\n"
            "import sys\n"
            f"REAL_COMPILER = {compiler!r}\n"
            "OBJCOPY = '/data/service/hnp/bin/llvm-objcopy'\n"
            "SIGNER = '/data/service/hnp/bin/binary-sign-tool'\n"
            "\n"
            "def output_path(args):\n"
            "    for index, arg in enumerate(args):\n"
            "        if arg == '-o' and index + 1 < len(args):\n"
            "            return args[index + 1]\n"
            "        if arg.startswith('-o') and len(arg) > 2:\n"
            "            return arg[2:]\n"
            "    return None\n"
            "\n"
            "def sign(path):\n"
            "    if not os.path.isfile(path):\n"
            "        return\n"
            "    with open(path, 'rb') as stream:\n"
            "        if stream.read(4) != b'\\x7fELF':\n"
            "            return\n"
            "    mode = os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH\n"
            "    os.chmod(path, mode)\n"
            "    subprocess.run([OBJCOPY, '--remove-section', '.codesign', path], check=False)\n"
            "    signed = path + '.nanopb-signed'\n"
            "    try:\n"
            "        subprocess.run([SIGNER, 'sign', '-inFile', path, '-outFile', signed, '-selfSign', '1'], check=True)\n"
            "        with open(signed, 'rb') as source, open(path, 'wb') as target:\n"
            "            shutil.copyfileobj(source, target)\n"
            "    finally:\n"
            "        if os.path.exists(signed):\n"
            "            os.unlink(signed)\n"
            "    if not (os.stat(path).st_mode & stat.S_IXUSR):\n"
            "        raise RuntimeError('signed OHOS test executable lost execute permission: ' + path)\n"
            "\n"
            "args = sys.argv[1:]\n"
            "result = subprocess.run([REAL_COMPILER] + args)\n"
            "if result.returncode == 0 and not any(flag in args for flag in ('-c', '-E', '-S')):\n"
            "    output = output_path(args)\n"
            "    if output:\n"
            "        sign(output)\n"
            "sys.exit(result.returncode)\n",
        )
        os.chmod(
            wrapper,
            os.stat(wrapper).st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )
        return wrapper

    def _sign_ohos_elf(self, path):
        """Sign an OHOS ELF while preserving its executable inode and mode."""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise RuntimeError("OHOS ELF signing requires llvm-objcopy and binary-sign-tool")

        mode = os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(path, mode)
        self.run(
            f"{shlex.quote(objcopy)} --remove-section .codesign "
            f"{shlex.quote(path)} 2>/dev/null || true"
        )
        signed = path + ".nanopb-signed"
        try:
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(path)} "
                f"-outFile {shlex.quote(signed)} -selfSign 1"
            )
            with open(signed, "rb") as source, open(path, "wb") as target:
                shutil.copyfileobj(source, target)
        finally:
            if os.path.exists(signed):
                os.unlink(signed)
        if not (os.stat(path).st_mode & stat.S_IXUSR):
            raise RuntimeError(f"signed OHOS ELF is not executable: {path}")

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
