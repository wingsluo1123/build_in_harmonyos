#!/usr/bin/env python3
"""Consumer test for pam_script 1.1.9.

The package payload is a loadable PAM module, so the consumer test cannot link
against it.  It builds a small C program that dlopen()s the installed
lib/security/pam_script.so and drives it through a real linux-pam stack using
pam_start_confdir() with a private configuration directory, then checks the
documented onerr= semantics (success vs. the upstream default fail).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PamScriptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("linux-pam/1.7.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _module_path(self):
        dep = self.dependencies["pam_script"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib/security"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)
        return os.path.join(libdir, "pam_script.so").replace("\\", "/")

    @staticmethod
    def _write_service(confdir, name, module, scriptdir, extra_args):
        tail = [module] + ([extra_args] if extra_args else []) + ["dir={}".format(scriptdir)]
        lines = [
            " ".join(["auth", "required"] + tail),
            " ".join(["account", "required"] + tail),
        ]
        with open(os.path.join(confdir, name), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def test(self):
        if not can_run(self):
            self.output.warning("cross-built consumer cannot run on this host")
            return

        module = self._module_path()
        if not os.path.isfile(module):
            raise ConanInvalidConfiguration("pam_script module missing: {}".format(module))

        confdir = os.path.join(self.build_folder, "pam-conf")
        scriptdir = os.path.join(self.build_folder, "pam-scripts")
        os.makedirs(confdir, exist_ok=True)
        os.makedirs(scriptdir, exist_ok=True)

        # The script directory is intentionally unprivileged: upstream's
        # check_path_perms() requires root:root ownership, so both stacks end
        # at the permission gate and only the onerr= mapping differs.
        self._write_service(confdir, "pam15853ok", module, scriptdir, "onerr=success")
        self._write_service(confdir, "pam15853fail", module, scriptdir, "")

        exe = os.path.join(self.cpp.build.bindirs[0], "test_pam_script")
        if str(self.settings.os) == "OHOS":
            self._sign_executable(exe)
        self.run('"{}" "{}" "{}"'.format(exe, module, confdir), env="conanrun")

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool")
        original_mode = os.stat(executable).st_mode
        temporary = "{}.signing".format(executable)
        try:
            shutil.copy2(executable, temporary)
            self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, temporary))
            self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, temporary, temporary))
            os.chmod(temporary, original_mode)
            os.replace(temporary, executable)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
        ]
        sdk_root = os.path.join(os.path.expanduser("~"), ".harmonybrew", "opt")
        candidates.extend(sorted(glob.glob(
            os.path.join(sdk_root, "ohos-sdk*", "bin", name)), reverse=True))
        candidates.append(shutil.which(name) or "")
        return next((path for path in candidates if path and os.path.isfile(path)), "")
