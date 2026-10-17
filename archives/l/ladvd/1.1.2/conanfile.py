#!/usr/bin/env python3
"""Conan recipe for building and packaging ladvd 1.1.2 on HarmonyOS."""

import hashlib
import os
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LadvdConan(ConanFile):
    name = "ladvd"
    version = "1.1.2"
    package_type = "application"

    description = "LLDP/CDP/EDP/FDP/NDP link-layer discovery daemon"
    license = "ISC"
    homepage = "https://github.com/sspans/ladvd"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "generated/*",
            src=self.recipe_folder,
            dst=self.export_sources_folder,
        )

    def requirements(self):
        self.requires("libevent/2.1.13")
        self.requires("libpcap/1.10.6")

    def build_requirements(self):
        self.test_requires("check/0.15.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ladvd supports only Linux-family targets, including OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--with-systemdsystemunitdir=no",
        ])
        if self.settings.os == "OHOS" and self.settings_build.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()

        self.buildenv.define("TMPDIR", self._runtime_tmp)
        self.buildenv.define("TEMP", self._runtime_tmp)
        if self.settings.os == "OHOS":
            self.buildenv.define("CONFIG_SHELL", "/bin/sh")
            self.buildenv.define("SHELL", "/bin/sh")

    def build(self):
        os.makedirs(self._runtime_tmp, exist_ok=True)
        apply_conandata_patches(self)
        generated = os.path.join(self.export_sources_folder, "generated")
        copy(self, "*", src=generated, dst=self.source_folder)
        self._harden_configure_tmpdir()
        # The hardening rewrite updates configure's mtime.  Refresh the whole
        # generated set afterwards so coarse-resolution target filesystems do
        # not see configure.ac as newer and invoke autoreconf during make.
        self._refresh_generated_timestamps(generated)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if self._can_execute_target:
            autotools.make(target="check", args=["-j1", "TESTS="])
            if self.settings.os == "OHOS":
                for name in self.conan_data["upstream_test_files"]:
                    executable = os.path.join(
                        self.build_folder,
                        "tests",
                        os.path.splitext(os.path.basename(name))[0],
                    )
                    self._sign_ohos_elf(executable)
            runenv = VirtualRunEnv(self).environment()
            # Test requirements are not part of dependencies.host, but their
            # target libraries are needed while the freshly built Check
            # executables run.  Iterate the complete graph view so libcheck
            # is present together with the regular host requirements.
            for dependency in self.dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    runenv.prepend_path(
                        "LD_LIBRARY_PATH",
                        os.path.join(dependency.package_folder, libdir),
                    )
            with runenv.vars(self).apply():
                autotools.make(target="check", args=["-j1"])
        else:
            # Build every upstream test executable during cross validation even
            # though only a native OHOS worker may execute them.
            autotools.make(target="check", args=["-j1", "TESTS="])
            self.output.warning(
                "Cross build compiled but did not execute the upstream Check "
                "suite; native OHOS W3/CI remains mandatory"
            )

    def package(self):
        Autotools(self).install()
        if self.settings.os == "OHOS" and self._is_native_ohos:
            self._sign_ohos_elf(
                os.path.join(self.package_folder, "bin", "ladvd")
            )
        copy(
            self,
            "LICENSE",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

    @property
    def _runtime_tmp(self):
        if self.settings.os == "OHOS":
            base = os.path.join(os.path.expanduser("~"), "tmp")
            build_id = hashlib.sha256(
                self.build_folder.encode("utf-8")
            ).hexdigest()[:12]
            return os.path.join(base, "ladvd-conan-" + build_id)
        return os.path.join(self.build_folder, "tmp")

    @property
    def _is_native_ohos(self):
        return self.settings.os == "OHOS" and os.uname().sysname in (
            "HarmonyOS",
            "OHOS",
        )

    @property
    def _can_execute_target(self):
        if not can_run(self):
            return False
        return self.settings.os != "OHOS" or self._is_native_ohos

    def _harden_configure_tmpdir(self):
        configure = os.path.join(self.source_folder, "configure")
        # Autoconf's mktemp branch always creates a mode-0700 directory.  Some
        # HarmonyOS storage workers map that directory to an owner which cannot
        # create config.status scratch files such as subs1.awk.  A plain mkdir
        # with a per-process name preserves isolation while inheriting the
        # worker's usable directory mode.  Merely removing `umask 077` is not
        # sufficient because mktemp -d itself still forces mode 0700.
        replace_in_file(
            self,
            configure,
            """{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
}""",
            """{
  tmp=./conf$$-${RANDOM-0}
  mkdir "$tmp" &&
  test -d "$tmp"
}""",
        )
        with open(configure, "r", encoding="utf-8") as handle:
            rewritten = handle.read()
        if 'mktemp -d "./confXXXXXX"' in rewritten or "umask 077" in rewritten:
            raise ConanException(
                "configure HMDFS scratch-directory rewrite did not apply"
            )

    def _refresh_generated_timestamps(self, generated_root):
        # Wait for the patched source mtimes to fall behind without placing
        # distributed files in the future: Automake's clock sanity check
        # rejects future timestamps, while equal/coarser timestamps can make
        # `make` regenerate configure on target storage filesystems.
        time.sleep(1)
        stamp = time.time()
        for root, _, files in os.walk(generated_root):
            for name in files:
                relative = os.path.relpath(
                    os.path.join(root, name), generated_root
                )
                destination = os.path.join(self.source_folder, relative)
                if os.path.isfile(destination):
                    os.utime(destination, (stamp, stamp))

    def _sign_ohos_elf(self, path):
        if not os.path.isfile(path):
            raise ConanException("Expected OHOS ELF is missing: " + path)
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        if not objcopy or not signer or not readelf:
            raise ConanException("OHOS ELF signing tools are unavailable")

        self.run(shlex.join([objcopy, "--remove-section", ".codesign", path]))
        signed = path + ".signed"
        self.run(shlex.join([
            signer,
            "sign",
            "-inFile",
            path,
            "-outFile",
            signed,
            "-selfSign",
            "1",
        ]))
        mode = os.stat(path).st_mode
        os.replace(signed, path)
        os.chmod(path, mode)

        result = subprocess.run(
            [readelf, "-S", path],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout.count(".codesign") != 1:
            raise ConanException("Invalid .codesign section count in " + path)
