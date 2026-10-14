#!/usr/bin/env python3
"""Conan recipe — laptop-mode-tools 1.74 (pure POSIX sh power-management CLI).

rickysarraf/laptop-mode-tools: laptop power management toolset (laptop_mode
CLI + 33 modules + helpers + configuration). No compilation at all: upstream
Makefile's only real target is `install`, driven by the environment-variable
powered install.sh. This recipe therefore:

  1. applies three minimal OHOS adaptation patches (env-driven install
     component gates, runtime portability of laptop_mode, conf.d module
     defaults for unavailable helper tools),
  2. verifies every shipped shell script with `bash -n`,
  3. runs the patched upstream install.sh in DESTDIR staging mode
     (non-root, INIT_D=none, ACPI/APM/PMU disabled, GUI/udev/pm-utils
     integration off) and checks the installed file inventory,
  4. packages the staged tree with the sbin entry points also exposed
     under bin/ for Conan CLI consumers.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.layout import basic_layout


class LaptopModeToolsConan(ConanFile):
    name = "laptop-mode-tools"
    version = "1.74"
    description = (
        "Laptop power management toolset: laptop_mode CLI with configurable "
        "power-saving modules (pure POSIX sh, no compiled components)"
    )
    license = "GPL-2.0-only"
    homepage = "https://github.com/rickysarraf/laptop-mode-tools"
    url = "https://github.com/rickysarraf/laptop-mode-tools"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _install_cmd(self):
        # install.sh drives every copy through $INSTALL (default
        # `install -o root -g root`, which fails for non-root). OHOS worker
        # has no coreutils install; busybox install supports -d/-m.
        install = shutil.which("install")
        if not install:
            busybox = shutil.which("busybox") or "/data/service/hnp/bin/busybox"
            if os.path.isfile(busybox):
                install = f"{busybox} install"
            else:
                raise ConanException(
                    "no 'install' or 'busybox' program available for staging"
                )
        return install

    def build(self):
        apply_conandata_patches(self)

        bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
        src = self.source_folder

        # 1) Syntax-check every shell script that ships in the package.
        scripts = ["usr/sbin/laptop_mode", "usr/sbin/lm-profiler",
                   "usr/sbin/lm-syslog-setup", "install.sh"]
        for group in ("modules", "module-helpers"):
            d = os.path.join(src, "usr", "share", "laptop-mode-tools", group)
            scripts += sorted(
                os.path.join("usr/share/laptop-mode-tools", group, f)
                for f in os.listdir(d)
            )
        for script in scripts:
            self.run(f'"{bash}" -n "{os.path.join(src, script)}"')

        # 2) Run the patched upstream install.sh in DESTDIR staging mode.
        #    Environment-variable driven: non-root safe, and all OHOS
        #    inapplicable integration targets disabled (init.d, systemd,
        #    acpi/apm/pmu, udev, pm-utils, GUI/polkit).
        stage = os.path.join(self.build_folder, "stage")
        install = self._install_cmd()
        env = (
            f'DESTDIR="{stage}" '
            f'INIT_D=none '
            f'MAN_D="/usr/share/man" '
            f'INSTALL="{install}" '
            f'SYSTEMD=no '
            f'ACPI=disabled APM=disabled PMU=disabled '
            f'INSTALL_GUI=no INSTALL_UDEV=no INSTALL_PM_UTILS=no'
        )
        self.run(f'cd "{src}" && env {env} /bin/sh ./install.sh')

        # 3) Verify the staged inventory.
        def must_exist(rel):
            if not os.path.exists(os.path.join(stage, rel)):
                raise ConanException(f"staged install missing {rel}")

        for rel in ("usr/sbin/laptop_mode", "usr/sbin/lm-profiler",
                    "usr/sbin/lm-syslog-setup",
                    "etc/laptop-mode/laptop-mode.conf",
                    "etc/laptop-mode/lm-profiler.conf",
                    "etc/laptop-mode/conf.d/board-specific",
                    "usr/share/man/man8/laptop_mode.8"):
            must_exist(rel)
        n_modules = len(os.listdir(
            os.path.join(stage, "usr/share/laptop-mode-tools/modules")))
        n_helpers = len(os.listdir(
            os.path.join(stage, "usr/share/laptop-mode-tools/module-helpers")))
        n_conf = len([f for f in os.listdir(
            os.path.join(stage, "etc/laptop-mode/conf.d"))
            if f.endswith(".conf")])
        if n_modules != 33:
            raise ConanException(f"expected 33 modules, staged {n_modules}")
        if n_helpers < 2:
            raise ConanException(f"expected >=2 module helpers, staged {n_helpers}")
        if n_conf != 31:
            raise ConanException(f"expected 31 conf.d files, staged {n_conf}")
        # Integration components must NOT be staged on OHOS.
        for forbidden in ("etc/init.d", "lib/udev", "usr/share/polkit-1",
                          "lib/systemd", "usr/lib/pm-utils"):
            if os.path.exists(os.path.join(stage, forbidden)):
                raise ConanException(
                    f"OHOS-inapplicable component staged: {forbidden}"
                )

        # 4) Smoke: the version entry point must work without an installed
        #    /etc/laptop-mode/laptop-mode.conf (patched behaviour).
        self.run(
            f'cd "{src}" && '
            f'env PWD="{src}" /bin/sh "{os.path.join(stage, "usr/sbin/laptop_mode")}" --version '
            f'| grep -q "Laptop Mode Tools {self.version}"'
        )

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        # Staged tree (usr/, etc/, man) preserved as-is.
        copy(self, "*", src=stage, dst=self.package_folder)
        # Entry points also exposed under bin/ for Conan CLI consumers.
        copy(self, "*", src=os.path.join(stage, "usr", "sbin"),
             dst=os.path.join(self.package_folder, "bin"))
        for name in os.listdir(os.path.join(self.package_folder, "bin")):
            os.chmod(os.path.join(self.package_folder, "bin", name), 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc",
                              "laptop-mode-tools"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
