#!/usr/bin/env python3
"""Consumer verification for lcmaps-plugins-verify-proxy 1.5.13."""

import os

from conan import ConanFile
from conan.tools.layout import basic_layout
from conan.tools.files import load


def _abs_dirs(cpp_info, kind):
    result = []
    package_folder = getattr(cpp_info, "package_folder", None)
    for directory in getattr(cpp_info, kind, []) or []:
        result.append(
            directory
            if os.path.isabs(directory) or not package_folder
            else os.path.join(package_folder, directory)
        )
    for component in (getattr(cpp_info, "components", None) or {}).values():
        for directory in getattr(component, kind, []) or []:
            result.append(
                directory
                if os.path.isabs(directory) or not package_folder
                else os.path.join(package_folder, directory)
            )
    return result


class LcmapsVerifyProxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Keep runtime dependencies direct so their package folders are
        # available while constructing the OHOS library search path.
        self.requires("lcmaps/1.6.7")
        self.requires("openssl/3.5.6.1.2")

    def layout(self):
        basic_layout(self)

    def test(self):
        package = self.dependencies["lcmaps-plugins-verify-proxy"]
        framework = self.dependencies["lcmaps"]
        package_root = package.package_folder
        framework_root = framework.package_folder

        executable = None
        for subdir in ("bin", "sbin"):
            candidate = os.path.join(package_root, subdir, "verify-proxy-tool")
            if os.path.isfile(candidate):
                executable = candidate
                break
        assert executable, "installed verify-proxy-tool is missing"

        libdirs = []
        for _, dependency in self.dependencies.host.items():
            if not getattr(dependency, "package_folder", None):
                continue
            libdirs.extend(_abs_dirs(dependency.cpp_info, "libdirs"))
        # OHOS resolves DT_NEEDED before Conan's virtual run environment can
        # help; make the LCMAPS and OpenSSL package lib dirs explicit.
        libdirs.append(os.path.join(framework_root, "lib"))
        library_path = ":".join(dict.fromkeys(libdirs))

        compilers = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = compilers.get("c", "clang")
        test_binary = os.path.join(
            self.build_folder, "test_lcmaps_plugins_verify_proxy"
        )
        self.run(
            f'"{cc}" -std=c11 -D_GNU_SOURCE -o "{test_binary}" '
            f'"{os.path.join(self.source_folder, "test.c")}" -ldl',
            env="conanrun",
        )

        help_output = os.path.join(
            self.build_folder, "verify-proxy-tool-help.txt"
        )
        self.run(
            f'LD_LIBRARY_PATH="{library_path}:$LD_LIBRARY_PATH" '
            f'"{executable}" -h > "{help_output}" 2>&1',
            env="conanrun",
        )
        help_text = load(self, help_output)
        assert "verify-proxy-tool" in help_text and "Usage:" in help_text, (
            f"verify-proxy-tool -h produced unexpected output: {help_text!r}"
        )
        self.run(
            f'LD_LIBRARY_PATH="{library_path}:$LD_LIBRARY_PATH" '
            f'"{test_binary}" "{package_root}" "{framework_root}"',
            env="conanrun",
        )
