#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/gadap/{version}/test_package/conanfile.py
"""
import os
import shlex

from conan import ConanFile


class GadapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Directly compile test.cc with the toolchain compiler, linking
        # against the tested gadap package and its dependencies. Avoids
        # CMake build requirement which has no OHOS binary in the Conan cache.
        gadap_pkg = self.dependencies[self.tested_reference_str]
        cpp = gadap_pkg.cpp_info.aggregated_components()
        inc = list(cpp.includedirs)
        lib = list(cpp.libdirs)
        libs = list(cpp.libs)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")

        # R33: compiler from Conan conf, not shell env vars.
        cxxflags = [f"-I{d}" for d in inc]
        libdirs = [f"-L{d}" for d in lib]

        # Add conan libxml2 lib dir (transitive dependency, provides libxml2)
        # Iterate over direct and transitive deps
        for dep_ref in self.dependencies.values():
            dep_cpp = dep_ref.cpp_info.aggregated_components()
            for d in dep_cpp.libdirs:
                if f"-L{d}" not in libdirs:
                    libdirs.append(f"-L{d}")
            for d in dep_cpp.includedirs:
                if f"-I{d}" not in cxxflags:
                    cxxflags.append(f"-I{d}")

        # System libraries from cmd-pkgs (libdap/curl/libtirpc).
        # libxml2 comes from conan dependency (not cmd-pkgs).
        prefix = os.path.expanduser("~/usr/local")
        sys_libdirs = [f"-L{prefix}/lib64", f"-L{prefix}/lib"]
        sys_libs = ["-ldap", "-ldapserver", "-ldapclient",
                     "-lcurl", "-ltirpc"]

        conan_libs = [f"-l{l}" for l in libs]

        out = os.path.join(self.build_folder, "test_gadap")
        src = os.path.join(self.source_folder, "test.cc")

        cmd = [
            cxx, "-std=c++17", "-stdlib=libc++",
            *cxxflags,
            "-o", out,
            src,
            *libdirs,
            *sys_libdirs,
            *conan_libs,
            *sys_libs,
            "-lxml2",
        ]
        cmd_str = " ".join(shlex.quote(str(c)) for c in cmd)
        self.output.info(f"Build command: {cmd_str}")
        self.run(cmd_str, env="conanrun")

    def test(self):
        # R34: test must call the tested package's API — test.cc calls
        # gadap_numopen() and gadap_open() from the gadap library.
        test_bin = os.path.join(self.build_folder, "test_gadap")
        self.run(shlex.quote(test_bin), env="conanrun")
