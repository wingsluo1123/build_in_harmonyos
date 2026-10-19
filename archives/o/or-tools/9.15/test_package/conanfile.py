#!/usr/bin/env python3
"""Conan consumer tests for or-tools 9.15 (CMake)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


def _prune_ar_member(src, dst, member_to_drop):
    """Copy an ar archive, dropping one member by real name (pure Python).

    Replaces ``llvm-ar d`` so the consumer test does not depend on any
    external tool being on PATH (CI workers run conan with a minimal PATH
    that does not include the OHOS toolchain dir; subprocess calls from
    generate() do not inherit the profile [buildenv] PATH either).
    Supports GNU long-name tables (``//`` + ``/#N`` refs, as produced by
    llvm-ar) and BSD ``#1/len`` names. The stale symbol-table member
    (``/`` or ``__.SYMDEF*``) is dropped too: after member removal its
    index no longer matches, and whole-archive linking does not need it.
    """
    with open(src, "rb") as f:
        data = f.read()
    if not data.startswith(b"!<arch>\n"):
        raise RuntimeError("%s: not a valid ar archive" % src)

    pos = 8
    n = len(data)
    members = []  # (name_field, size, data_start)
    long_names = b""
    while pos < n:
        if pos + 60 > n:
            break
        hdr = data[pos:pos + 60]
        name_field = hdr[0:16].rstrip()
        size_field = hdr[48:58].strip()
        try:
            size = int(size_field or b"0")
        except ValueError:
            break
        data_start = pos + 60
        if data_start + size > n:
            break
        if name_field == b"//":
            long_names = data[data_start:data_start + size]
        members.append((name_field, size, data_start))
        pos = data_start + size
        if size % 2 == 1:  # even-boundary padding
            pos += 1

    def real_name(name_field, data_start):
        if name_field.startswith(b"/") and len(name_field) > 1:
            try:
                off = int(name_field[1:])
            except ValueError:
                return name_field.decode("utf-8", "replace")
            end = long_names.find(b"/\n", off)
            if end == -1:
                end = long_names.find(b"\n", off)
            if end == -1:
                end = len(long_names)
            return long_names[off:end].decode("utf-8", "replace")
        return name_field.decode("utf-8", "replace")

    out = bytearray(b"!<arch>\n")
    dropped = False
    for name_field, size, data_start in members:
        name = real_name(name_field, data_start)
        if name == member_to_drop:
            dropped = True
            continue
        if name_field == b"/" or name.startswith("__.SYMDEF"):
            continue  # stale symbol table
        out += data[data_start - 60:data_start]
        out += data[data_start:data_start + size]
        if size % 2 == 1:
            out += b"\n"
    if not dropped:
        raise RuntimeError(
            "%s: member %r not found in archive" % (src, member_to_drop)
        )
    with open(dst, "wb") as f:
        f.write(bytes(out))


class ORToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # protobuf (33.6.1 / 34.1 alike) ships cmake_find_mode=none, but the
        # ortools-config.cmake emitted by CMakeDeps references
        # protobuf::protobuf; force CMakeDeps to emit protobuf-config.cmake.
        self.dependencies["protobuf"].cpp_info.set_property("cmake_find_mode", "config")
        CMakeDeps(self).generate()

        # NOTE: we deliberately do NOT inject protobuf_DIR here. The test_package
        # consumes or-tools through Conan CMakeDeps, whose ortools config builds
        # an aggregate "or-tools_DEPS_TARGET" that references protobuf::protobuf
        # (the Conan recipe target name). Injecting protobuf_DIR would shadow
        # CMakeDeps' protobuf-config.cmake with the package's own config (which
        # only defines protobuf::libprotobuf), leaving protobuf::protobuf
        # undefined and failing configure with:
        #   The link interface of target "or-tools_DEPS_TARGET" contains:
        #   protobuf::protobuf  but the target was not found.
        tc = CMakeToolchain(self)
        # protobuf/33.6.1 public headers pull in utf8_range symbols
        # (utf8_range_IsValid / utf8_range_ValidPrefix); the CMakeDeps
        # protobuf config does not propagate that archive, so add it to the
        # link line for the consumer executable.
        protobuf_lib = os.path.join(
            self.dependencies["protobuf"].package_folder, "lib",
        ).replace("\\", "/")
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"-L{protobuf_lib} -lutf8_range -lutf8_validity"
        )
        # ortools::ortools is an INTERFACE target (no TARGET_FILE), so the
        # test CMakeLists cannot wrap it with --whole-archive itself; hand
        # over the real archive path so solver-registration objects
        # (kRegisterGlop etc.) are kept and MPSolver finds its factories.
        # Whole-archive also pulls model_builder_helper.cc.obj, which
        # references GurobiSolveProto — that symbol lives in
        # gurobi_interface.cc.obj, excluded upstream when no GUROBI SDK is
        # present, so prune the dangling object from a copy first.
        # Pure-Python (no llvm-ar on PATH in CI workers' minimal env).
        ortools_lib = os.path.join(
            self.dependencies["or-tools"].package_folder, "lib", "libortools.a"
        )
        pruned_lib = os.path.join(self.build_folder, "libortools_pruned.a")
        _prune_ar_member(ortools_lib, pruned_lib, "model_builder_helper.cc.obj")
        tc.cache_variables["OR_TOOLS_LIB"] = pruned_lib.replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder,
            "lib", "cmake", "absl",
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
