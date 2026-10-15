#!/usr/bin/env python3
"""Conan recipe for Valkey 8.1.4 on Linux and HarmonyOS."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ValkeyConan(ConanFile):
    name = "valkey"
    version = "8.1.4"
    description = "High-performance in-memory key-value datastore"
    license = "BSD-3-Clause"
    homepage = "https://valkey.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _commands = (
        "valkey-server",
        "valkey-sentinel",
        "valkey-cli",
        "valkey-benchmark",
        "valkey-check-rdb",
        "valkey-check-aof",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Valkey' official integration suites are driven by Tcl. Tcl is a
        # build-only test tool and is not part of the packaged runtime.
        self.tool_requires("tcl/8.6.16")

    def generate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"valkey supports Linux/OHOS in this recipe, got {self.settings.os}"
            )
        VirtualBuildEnv(self).generate()

    def _make_tool_args(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        cxx = executables.get("cpp", "clang++")
        ar = executables.get("ar", "llvm-ar")
        ranlib = executables.get("ranlib", "llvm-ranlib")
        args = [
            f"CC={shlex.quote(cc)}",
            f"CXX={shlex.quote(cxx)}",
            f"LD={shlex.quote(cc)}",
            f"AR={shlex.quote(ar)}",
            f"RANLIB={shlex.quote(ranlib)}",
            # jemalloc is the upstream default but its growth paths are not
            # validated against the OHOS musl allocator; libc malloc is.
            "MALLOC=libc",
            "USE_SYSTEMD=no",
            "BUILD_TLS=no",
        ]
        if str(self.settings.os) == "OHOS":
            # /system/bin/install is the only signed system tool allowed to
            # create the install-mode file operations on HarmonyFS.
            args.append("INSTALL=/system/bin/install")
        return args

    def build(self):
        apply_conandata_patches(self)
        args = " ".join(self._make_tool_args())
        self.run(
            f"make -j1 {args}",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # The upstream Tcl suites execute the just-built target binaries. On
        # OHOS an unsigned ELF cannot be started, so sign the source-tree
        # commands first and package those exact tested files afterwards.
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            self._sign_ohos_binaries(os.path.join(self.source_folder, "src"))

        test_tmp = None
        test_env = ""
        if is_ohos:
            test_storage = "/data/storage/el2/base/cache"
            if not os.path.isdir(test_storage):
                raise ConanInvalidConfiguration(
                    f"OHOS user cache directory does not exist: {test_storage}"
                )
            test_tmp = tempfile.mkdtemp(prefix="valkey-test-", dir=test_storage)
            test_env = f"VALKEY_TEST_TMPDIR={shlex.quote(test_tmp)} VALKEY_TEST_SKIP_PROCESS_PAUSE=1 "

        try:
            module_make = shlex.quote(f"make -j1 {args}")
            # Only the two test_helper.tcl based entry points accept --clients;
            # runtest-sentinel and runtest-cluster go through
            # tests/{sentinel,cluster}/run.tcl -> tests/instances.tcl, whose
            # parse_options rejects it ("Unknown option --clients"). Verified in
            # the wrappers and in instances.tcl:278. Those two suites are far
            # smaller, so their default concurrency is fine.
            # Concurrency rationale (this is the only knob changed): with
            # --clients 1 a single entry point (runtest) had not finished after
            # ~51 minutes, while --clients 4 completed runtest and
            # runtest-moduleapi back to back in ~25 minutes including the
            # compile. Upstream's default is 16. Test set, judgement rules, skip
            # list and denominator are untouched.
            test_commands = (
                "sh ./runtest --clients 4",
                f"MAKE={module_make} sh ./runtest-moduleapi --clients 4",
                "sh ./runtest-sentinel",
                "sh ./runtest-cluster",
            )
            for command in test_commands:
                self.run(
                    f"{test_env}{command}",
                    cwd=self.source_folder,
                    env="conanbuild",
                )
        finally:
            if test_tmp:
                shutil.rmtree(test_tmp, ignore_errors=True)

    def package(self):
        if str(self.settings.os) == "OHOS":
            source_bin = os.path.join(self.source_folder, "src")
            package_bin = os.path.join(self.package_folder, "bin")
            for binary in self._commands:
                copy(self, binary, src=source_bin, dst=package_bin)
        else:
            args = " ".join(self._make_tool_args())
            prefix = shlex.quote(f"PREFIX={self.package_folder}")
            self.run(
                f"make install {prefix} {args}",
                cwd=self.source_folder,
                env="conanbuild",
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _sign_ohos_binaries(self, bindir):
        signer = self._find_tool(
            "binary-sign-tool",
            [
                "/data/service/hnp/bin/binary-sign-tool",
                "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            ],
        )
        objcopy = self._find_tool(
            "llvm-objcopy",
            [
                "/data/service/hnp/bin/llvm-objcopy",
                "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
            ],
        )
        commands = set(self._commands)
        for entry in os.scandir(bindir):
            if entry.name not in commands or not entry.is_file(follow_symlinks=False):
                continue
            binary = entry.path
            signed = binary + ".signed"
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(binary)}",
                quiet=True,
            )
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(binary)} "
                f"-outFile {shlex.quote(signed)} -selfSign 1",
                quiet=True,
            )
            os.replace(signed, binary)
            os.chmod(binary, 0o755)

    @staticmethod
    def _find_tool(name, fallbacks):
        found = shutil.which(name)
        if found:
            return found
        for candidate in fallbacks:
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            f"{name} is required to package valkey on OHOS"
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
