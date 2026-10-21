#!/usr/bin/env python3
"""Conan recipe — qpack 0.0.21 (upstream setuptools C extension)."""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class QpackConan(ConanFile):
    name = "qpack"
    version = "0.0.21"
    description = "QPack serializer with its native Python C extension"
    license = "MIT"
    homepage = "https://github.com/cesbit/qpack"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", run=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qpack's native recipe is supported on Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Private, hash-pinned build dependency; nothing is installed globally.
        get(self, **self.conan_data["build_tools"]["setuptools"],
            destination=os.path.join(self.source_folder, "_build_tools"))

    def generate(self):
        compiler = self.conf.get("tools.build:compiler_executables", default={},
                                 check_type=dict).get("c")
        if not compiler:
            raise ConanException("the profile must specify the target C compiler")
        python_home = self.dependencies["python"].package_folder
        toolchain = AutotoolsToolchain(self)
        toolchain.extra_cflags = ["-fPIC"]
        toolchain.extra_ldflags = ["-L" + os.path.join(python_home, "lib"), "-lpython3.12"]
        environment = toolchain.environment()
        environment.define("LDSHARED", shlex.quote(compiler) + " -shared")
        environment.append("CPPFLAGS", "-I" + shlex.quote(os.path.join(python_home, "include/python3.12")))
        toolchain.generate(environment)

    def build(self):
        python_home = self.dependencies["python"].package_folder
        python = os.path.join(python_home, "bin", "python3")
        if not os.path.isfile(python):
            raise ConanException("the published Python dependency lacks bin/python3")
        environment = Environment()
        environment.define_path("PYTHONHOME", python_home)
        environment.define_path("PYTHONPATH", os.path.join(self.source_folder, "_build_tools"))
        with environment.vars(self, scope="build").apply(), chdir(self, self.source_folder):
            self.run(shlex.join([python, "-B", "-c",
                "import json,setuptools; import distutils.core; "
                "print(json.dumps({'setuptools':setuptools.__version__, "
                "'file':setuptools.__file__, 'distutils':distutils.core.__file__})); "
                "assert setuptools.__version__ == '84.0.0'"]), env=["conanbuild", "conanrun"])
            self.run(shlex.join([python, "-B", "setup.py", "build_ext",
                "--build-lib", os.path.join(self.build_folder, "python"),
                "--build-temp", os.path.join(self.build_folder, "temp")]),
                env=["conanbuild", "conanrun"])
        extensions = glob.glob(os.path.join(self.build_folder, "python/qpack/_qpack*.so"))
        if len(extensions) != 1:
            raise ConanException("the upstream build did not produce exactly one native extension")
        if self.settings.os == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise ConanException("the existing OHOS binary-sign-tool is unavailable")
            self.run(shlex.join([signer, "sign", "-inFile", extensions[0],
                                "-outFile", extensions[0], "-selfSign", "1"]), env="conanbuild")

    def package(self):
        destination = os.path.join(self.package_folder, "lib/python/qpack")
        copy(self, "*.py", src=os.path.join(self.source_folder, "qpack"), dst=destination)
        if len(copy(self, "_qpack*.so", src=os.path.join(self.build_folder, "python/qpack"),
                    dst=destination)) != 1:
            raise ConanException("the package must contain its native C extension")
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Python loads this extension; downstream C linkers must not link it as libqpack.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib/python"))
