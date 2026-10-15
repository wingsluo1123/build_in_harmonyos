#!/usr/bin/env python3
"""Conan recipe — pawk 0.8.1 (single Python module and CLI)."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PawkConan(ConanFile):
    name = "pawk"
    version = "0.8.1"
    description = "PAWK Python line processor with Unicode-aware CLI delimiters"
    license = "MIT"
    homepage = "https://github.com/alecthomas/pawk"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    exports_sources = "upstream/*", "pawk_entry.py"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        python = self.dependencies["python"].package_folder
        env = Environment()
        env.define("PYTHONHOME", python)
        env.define("PYTHONUTF8", "1")
        env.define("PYTHONIOENCODING", "utf-8")
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(python, "lib"))
        env.vars(self).save_script("pawk-runtime")

    def build(self):
        python = os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")
        tests = os.path.join(self.export_sources_folder, "upstream")
        command = [python, "-B", os.path.join(tests, "run_upstream.py"),
                   "--module-folder", self.source_folder,
                   "--tests-file", os.path.join(tests, "pawk_test.py")]
        self.run(shlex.join(command), env="pawk-runtime")

    def package(self):
        copy(self, "pawk.py", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "python3.12", "site-packages"), keep_path=False)
        copy(self, "COPYING", src=os.path.join(self.export_sources_folder, "upstream"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        wrapper = os.path.join(self.package_folder, "bin", "pawk")
        os.makedirs(os.path.dirname(wrapper), exist_ok=True)
        with open(os.path.join(self.export_sources_folder, "pawk_entry.py"), "rb") as source:
            with open(wrapper, "wb") as target:
                target.write(source.read())
        os.chmod(wrapper, 0o755)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages"))
