"""Version-specific Python multiprocessing with installed upstream regression."""
import os
from pathlib import Path
import platform
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MultiprocessConan(ConanFile):
    name = "multiprocess"
    version = "0.70.19"
    description = "Multiprocessing with dill serialization"
    license = "BSD-3-Clause"
    homepage = "https://github.com/uqfoundation/multiprocess"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    options = {"python_version": ["3.12.9"]}
    default_options = {"python_version": "3.12.9"}
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("dill/0.4.1", headers=False, libs=False, run=True)

    def build_requirements(self):
        self.tool_requires("setuptools/84.0.0")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration("Validated on OHOS and Linux")
        if platform.python_implementation() != "CPython" or platform.python_version() != str(self.options.python_version):
            raise ConanInvalidConfiguration("This version-specific package requires CPython 3.12.9")

    def package_id(self):
        # Retain interpreter selection and dill dependency identity.
        self.info.settings.clear()

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        get(self, **self.conan_data["test_support"]["3.12.9"],
            destination=os.path.join(self.source_folder, "_cpython"), strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        site = os.path.join(self.build_folder, "installed")
        verification = os.path.join(self.build_folder, "verification")
        support = os.path.join(self.build_folder, "test-support")
        copy(self, "*", src=self.source_folder, dst=staging, excludes=("_cpython/*",))
        os.makedirs(site, exist_ok=True)
        os.makedirs(verification, exist_ok=True)
        # Never prepend an entire unadapted CPython Lib: it would shadow the
        # running vendor interpreter's adapted subprocess/multiprocessing.
        copy(self, "*", src=os.path.join(self.source_folder, "_cpython", "Lib", "test"),
             dst=os.path.join(support, "test"))
        environment = Environment()
        environment.define("PYTHONDONTWRITEBYTECODE", "1")
        environment.define("PYTHONNOUSERSITE", "1")
        with environment.vars(self).apply():
            self.run(f'"{sys.executable}" -s setup.py build_py --build-lib "{site}" '
                     f'egg_info --egg-base "{site}"', cwd=staging, env="conanbuild")
        testing = Environment()
        testing.prepend_path("PYTHONPATH", support)
        testing.prepend_path("PYTHONPATH", site)
        testing.define("PYTHONDONTWRITEBYTECODE", "1")
        testing.define("PYTHONNOUSERSITE", "1")
        with testing.vars(self).apply():
            origin = "import multiprocess,sys; from pathlib import Path; assert Path(multiprocess.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve()); print('INSTALLED_UPSTREAM_ORIGIN',multiprocess.__file__)"
            self.run(f'"{sys.executable}" -s -P -c "{origin}" "{site}"',
                     cwd=verification, env="conanrun")
            self.run(f'"{sys.executable}" -s -P -m multiprocess.tests',
                     cwd=verification, env="conanrun")
            # The upstream runner does not discover this top-level test module.
            self.run(f'"{sys.executable}" -s -P -m unittest -v '
                     'multiprocess.tests.test_multiprocessing_main_handling',
                     cwd=verification, env="conanrun")

    def package(self):
        copy(self, "*", src=os.path.join(self.build_folder, "installed"),
             dst=os.path.join(self.package_folder, "lib", "python", "site-packages"),
             excludes=("*.pyc", "__pycache__/*"))
        for name in ("LICENSE", "COPYING"):
            copy(self, name, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python", "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("MULTIPROCESS_PACKAGE_ROOT", site)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
