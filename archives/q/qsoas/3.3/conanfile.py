#!/usr/bin/env python3
"""Conan recipe for QSoas 3.3 on HarmonyOS PC."""

import os
import re
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class QsoasConan(ConanFile):
    name = "qsoas"
    version = "3.3"
    description = "Scriptable scientific data analysis and fitting application"
    license = "GPL-2.0-or-later"
    homepage = "https://qsoas.org/"
    url = "https://github.com/fourmond/QSoas"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5/5.15.19")
        self.requires("mruby/3.3.0")
        self.requires("gsl/2.8")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("QSoas supports Linux-compatible targets")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("qsoas/3.3 targets HarmonyOS PC aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        env = Environment()
        for dependency in self.dependencies.values():
            root = dependency.package_folder
            if not root:
                continue
            env.prepend_path("PATH", os.path.join(root, "bin"))
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(root, "lib"))
        qtbase = self.dependencies["qt5"].package_folder
        env.define("QTDIR", qtbase)
        env.vars(self, scope="build").save_script("conanbuild_qsoas")

    def _relocated_qmake(self, qtbase):
        """Build a private, relocatable view of Qt's qmake metadata."""
        root = os.path.join(self.build_folder, "qt-qmake")
        mkspecs = os.path.join(root, "mkspecs")
        if os.path.isdir(root):
            shutil.rmtree(root)
        shutil.copytree(os.path.join(qtbase, "mkspecs"), mkspecs)

        modules = os.path.join(mkspecs, "modules")
        modules_inst = os.path.join(qtbase, "mkspecs", "modules-inst")
        if os.path.isdir(modules_inst):
            for name in os.listdir(modules_inst):
                if name.endswith(".pri"):
                    shutil.copy2(os.path.join(modules_inst, name), modules)

        assignments = {
            "QT_MODULE_BIN_BASE": os.path.join(qtbase, "bin"),
            "QT_MODULE_INCLUDE_BASE": os.path.join(qtbase, "include"),
            "QT_MODULE_LIB_BASE": os.path.join(qtbase, "lib"),
            "QT_MODULE_HOST_LIB_BASE": os.path.join(qtbase, "lib"),
        }
        for directory, _, names in os.walk(modules):
            for name in names:
                if not name.endswith(".pri"):
                    continue
                path = os.path.join(directory, name)
                with open(path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                for key, value in assignments.items():
                    content = re.sub(
                        rf"(?m)^{key}\s*=.*$", f"{key} = {value}", content
                    )
                # modules-inst records the build machine location of host tools.
                # Keep the tool name, but resolve it from the installed Qt package.
                content = re.sub(
                    r"(?m)^(QT_TOOL\.[^.]+\.binary\s*=\s*)(\S+)$",
                    lambda match: match.group(1) + os.path.join(
                        qtbase, "bin", os.path.basename(match.group(2))
                    ),
                    content,
                )
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)

        bindir = os.path.join(root, "bin")
        os.makedirs(bindir)
        qmake = os.path.join(bindir, "qmake")
        shutil.copy2(os.path.join(qtbase, "bin", "qmake"), qmake)
        os.chmod(qmake, stat.S_IMODE(os.stat(qmake).st_mode) | 0o755)
        save(
            self,
            os.path.join(bindir, "qt.conf"),
            "[EffectivePaths]\nPrefix=..\n"
            "[DevicePaths]\nPrefix={0}\n"
            "[Paths]\nPrefix={0}\nHostPrefix={0}\n"
            "Sysroot=\nSysrootifyPrefix=false\n"
            "TargetSpec=linux-clang\nHostSpec=linux-clang\n".format(qtbase),
        )
        return qmake

    def build(self):
        save(
            self,
            os.path.join(self.source_folder, "src", "helpbrowser-noqthelp.cc"),
            "\n",
        )
        apply_conandata_patches(self)
        save(
            self,
            os.path.join(self.source_folder, "src", "build.hh"),
            '#define SOAS_BUILD_INFO "Built reproducibly from QSoas 3.3 release source"\n',
        )

        qtbase = self.dependencies["qt5"].package_folder
        mruby = self.dependencies["mruby"].package_folder
        gsl = self.dependencies["gsl"].package_folder
        packaged_qmake = os.path.join(qtbase, "bin", "qmake")
        if not os.path.isfile(packaged_qmake):
            raise ConanInvalidConfiguration("qt5-qtbase package does not provide qmake")
        qmake = self._relocated_qmake(qtbase)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        command = [
            qmake,
            self.source_folder,
            "-spec",
            "linux-clang",
            "CONFIG+=release",
            "CONFIG-=debug",
            "CONFIG+=prebuilt_build_info",
            "CONFIG+=no_qthelp",
            "CONFIG+=no_qtsvg",
            "CONFIG+=no_libzip",
            "CONFIG+=no_qt_rpath",
            "RUBY=/qsoas-build-must-not-use-ruby",
            "VERSION=3.3",
            f"MRUBY_DIR={mruby}",
            f"GSL_DIR={gsl}",
        ]
        if compilers.get("c"):
            command.append(f"QMAKE_CC={compilers['c']}")
        if compilers.get("cpp"):
            command.append(f"QMAKE_CXX={compilers['cpp']}")
        subprocess.run(command, cwd=self.build_folder, check=True)
        makefile = os.path.join(self.build_folder, "Makefile")
        with open(makefile, "r", encoding="utf-8") as handle:
            generated = handle.read()
        stale_tool = re.search(r"/\.cache/conan2/p/b/qt[^\s]*/b/bin/", generated)
        if stale_tool:
            raise ConanInvalidConfiguration(
                "qmake generated a command using Qt's historical build cache"
            )
        self.run("make -j1 QMAKE_STRIP=", cwd=self.build_folder, env="conanbuild")

    def package(self):
        executable = os.path.join(self.build_folder, "QSoas")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration("qmake build did not produce QSoas")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        destination = os.path.join(bindir, "qsoas")
        shutil.copy2(executable, destination)
        os.chmod(destination, stat.S_IMODE(os.stat(destination).st_mode) | 0o755)
        shutil.copy2(
            os.path.join(self.source_folder, "LICENCE"),
            os.path.join(self.package_folder, "LICENCE"),
        )
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_executable(destination)

    def _sign_ohos_executable(self, path):
        tools = {}
        for name in ("llvm-readelf", "llvm-objcopy", "binary-sign-tool"):
            candidate = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
            if not os.path.isfile(candidate):
                raise ConanInvalidConfiguration(f"required OHOS tool is missing: {name}")
            tools[name] = candidate

        inspected = subprocess.run(
            [tools["llvm-readelf"], "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if ".codesign" in inspected:
            subprocess.run(
                [tools["llvm-objcopy"], "--remove-section", ".codesign", path],
                check=True,
                timeout=60,
            )
        signed = path + ".signed"
        environment = dict(os.environ)
        environment.pop("LD_LIBRARY_PATH", None)
        subprocess.run(
            [
                tools["binary-sign-tool"],
                "sign",
                "-inFile",
                path,
                "-outFile",
                signed,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
            env=environment,
        )
        os.replace(signed, path)
        os.chmod(path, stat.S_IMODE(os.stat(path).st_mode) | 0o755)
        verified = subprocess.run(
            [tools["llvm-readelf"], "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sum(".codesign" in line for line in verified.splitlines()) != 1:
            raise ConanInvalidConfiguration("packaged qsoas must contain one .codesign section")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib")
                )
