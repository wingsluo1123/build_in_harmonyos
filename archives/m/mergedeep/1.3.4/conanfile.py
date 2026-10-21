"""Package fixed upstream mergedeep and run its original stdlib test suite."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MergedeepConan(ConanFile):
    name = "mergedeep"
    version = "1.3.4"
    description = "Deep merge with strict type checks before recursive Mapping dispatch"
    license = "MIT"
    homepage = "https://github.com/clarketm/mergedeep"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def requirements(self):
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        python = self.dependencies["python"].package_folder
        env = Environment()
        env.define("PYTHONHOME", python)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(python, "lib"))
        env.vars(self).save_script("mergedeep-runtime")

    def build(self):
        python = os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")
        self.run(shlex.join([python, "-B", "-m", "unittest", "-v", "mergedeep.test_mergedeep"]),
                 cwd=self.source_folder, env="mergedeep-runtime")

    def package(self):
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "mergedeep")
        copy(self, "*.py", src=os.path.join(self.source_folder, "mergedeep"), dst=site)
        copy(self, "py.typed", src=self.source_folder, dst=site, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages"))
