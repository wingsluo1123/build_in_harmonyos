#!/usr/bin/env python3
"""Boost 1.84.0 Conan recipe for OpenHarmony."""

import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import chdir, copy, get, save
from conan.tools.layout import basic_layout


class BoostConan(ConanFile):
    name = "boost"
    version = "1.84.0"
    description = "Boost 1.84.0 with compiled program_options and date_time for OHOS"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("Boost 1.84.0 OHOS recipe requires os=OHOS")
        if str(self.settings.compiler) != "clang":
            raise ConanInvalidConfiguration("Boost 1.84.0 OHOS recipe requires clang")
        if str(self.settings.compiler.libcxx) != "libc++":
            raise ConanInvalidConfiguration("Boost 1.84.0 OHOS recipe requires libc++")
        if str(self.settings.arch) not in ("armv8", "armv8.3"):
            raise ConanInvalidConfiguration("Boost 1.84.0 OHOS recipe requires armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = str(executables.get("c", "/data/service/hnp/bin/clang"))
        cxx = str(executables.get("cpp", "/data/service/hnp/bin/clang++"))
        if not os.path.isabs(cc) or not os.path.isabs(cxx):
            raise ConanInvalidConfiguration("OHOS compiler paths must be absolute")
        return cc, cxx

    def _ohos_flags(self, target):
        """Return explicit OHOS sysroot and libc++ flags for HNP clang."""
        sysroot = self.conf.get("tools.build:sysroot", default="", check_type=str)
        if not sysroot:
            sysroot = os.environ.get("OHOS_SYSROOT", "")
        if not sysroot:
            candidates = glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"
            )
            if candidates:
                sysroot = sorted(candidates)[-1]
        if not sysroot or not os.path.isdir(sysroot):
            raise ConanInvalidConfiguration(
                "OHOS SDK sysroot not found; set tools.build:sysroot or OHOS_SYSROOT"
            )

        llvm = os.path.join(os.path.dirname(sysroot), "llvm")
        libcxx_v1 = os.path.join(llvm, "include", "libcxx-ohos", "include", "c++", "v1")
        config_sites = glob.glob(
            os.path.join(llvm, "include", "**", "__config_site"), recursive=True
        )
        if not os.path.isdir(libcxx_v1):
            raise ConanInvalidConfiguration(
                f"OHOS libc++ headers not found: {libcxx_v1}"
            )
        if not config_sites:
            raise ConanInvalidConfiguration(
                f"OHOS libc++ __config_site not found below: {llvm}/include"
            )

        include_dirs = [
            libcxx_v1,
            *[os.path.dirname(path) for path in sorted(config_sites)],
            os.path.join(sysroot, "usr", "include"),
            os.path.join(sysroot, "usr", "include", target),
        ]
        include_flags = []
        for include_dir in include_dirs:
            if include_dir not in include_flags and os.path.isdir(include_dir):
                include_flags.append(include_dir)

        cxxflags = [
            f"-target {target}",
            f"--sysroot={sysroot}",
            "-nostdinc++",
            "-stdlib=libc++",
            "-D__OHOS_FAMILY__=1",
            "-D_LIBCPP_HAS_NO_C_LOCALE",
            "-DBOOST_DISABLE_THREADS",
        ]
        if self.options.fPIC:
            cxxflags.append("-fPIC")
        cxxflags.extend(f"-isystem {path}" for path in include_flags)
        linkflags = [
            f"-target {target}",
            f"--sysroot={sysroot}",
            "-stdlib=libc++",
            f"-L{os.path.join(llvm, 'lib', target)}",
            f"-L{os.path.join(sysroot, 'usr', 'lib', target)}",
        ]
        return sysroot, " ".join(cxxflags), " ".join(linkflags)

    def build(self):
        cc, cxx = self._toolchain()
        target = "aarch64-linux-ohos"
        _, cxxflags, linkflags = self._ohos_flags(target)
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        user_config = os.path.join(self.source_folder, "user-config-ohos.jam")
        save(
            self,
            user_config,
            "using clang : ohos : \"{}\" : <cxxflags>\"{}\" <linkflags>\"{}\" ;\n".format(
                cxx, cxxflags, linkflags
            ),
        )
        stage = os.path.join(self.build_folder, "stage")
        os.makedirs(stage, exist_ok=True)

        with chdir(self, self.source_folder):
            os.environ["PATH"] = os.path.dirname(cc) + os.pathsep + os.environ.get("PATH", "")
            self.run(
                "CC={} CXX={} {} bootstrap.sh --with-toolset=clang".format(
                    shlex.quote(cc), shlex.quote(cxx), shlex.quote(shell)
                )
            )
            b2 = shlex.quote(os.path.join(self.source_folder, "b2"))
            command = (
                "CC={} CXX={} CONFIG_SHELL={} SHELL={} {} "
                "--user-config={} --build-dir={} --layout=system "
                "toolset=clang-ohos target-os=linux binary-format=elf "
                "architecture=arm address-model=64 threading=multi cxxstd=17 "
                "variant={} link={} --with-program_options --with-date_time "
                "--prefix={} -j1 -q install"
            ).format(
                shlex.quote(cc),
                shlex.quote(cxx),
                shlex.quote(shell),
                shlex.quote(shell),
                b2,
                shlex.quote(user_config),
                shlex.quote(self.build_folder),
                "debug" if str(self.settings.build_type) == "Debug" else "release",
                "shared" if self.options.shared else "static",
                shlex.quote(stage),
            )
            self.run(command)

        for component in ("program_options", "date_time"):
            found = glob.glob(os.path.join(stage, "lib", f"libboost_{component}*.a"))
            found += glob.glob(os.path.join(stage, "lib", f"libboost_{component}*.so*"))
            if not found:
                raise ConanException(f"b2 did not produce libboost_{component}")

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(self, "boost/*", src=os.path.join(stage, "include"), dst=os.path.join(self.package_folder, "include"))
        for component in ("program_options", "date_time"):
            copy(self, f"libboost_{component}*.a", src=os.path.join(stage, "lib"), dst=os.path.join(self.package_folder, "lib"))
            copy(self, f"libboost_{component}*.so*", src=os.path.join(stage, "lib"), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        _, cxxflags, linkflags = self._ohos_flags("aarch64-linux-ohos")
        self.cpp_info.cxxflags = shlex.split(cxxflags)
        self.cpp_info.exelinkflags = shlex.split(linkflags)
        self.cpp_info.sharedlinkflags = shlex.split(linkflags)
        self.cpp_info.components["headers"].libs = []
        self.cpp_info.components["headers"].set_property("cmake_target_name", "Boost::headers")
        for component in ("program_options", "date_time"):
            cpp = self.cpp_info.components[component]
            cpp.libs = [f"boost_{component}"]
            cpp.requires = ["headers"]
            cpp.set_property("cmake_target_name", f"Boost::{component}")
