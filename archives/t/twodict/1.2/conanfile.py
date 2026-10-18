"""Native OHOS verification and packaging of the single twodict module."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TwodictConan(ConanFile):
    name = "twodict"
    version = "1.2"
    license = "Unlicense"
    description = "Two way ordered dictionary for Python"
    homepage = "https://github.com/MrS0m30n3/twodict"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        self.tool_requires("python/3.12.9")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        interpreter = os.path.join(self.dependencies.build["python"].package_folder,
                                   "bin", "python3")
        # Keep upstream's custom suite, including nested TestSetItem classes.
        # The patched runner returns its actual wasSuccessful() result.
        self.run(f"{shlex.quote(interpreter)} -B test_twodict.py -v",
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        module = copy(self, "twodict.py", src=self.source_folder,
                      dst=os.path.join(self.package_folder, "lib", "python"))
        license_file = copy(self, "LICENSE", src=self.source_folder,
                            dst=os.path.join(self.package_folder, "licenses"),
                            keep_path=False)
        if not module or not license_file:
            raise ConanException("twodict module or upstream license was not packaged")

    def package_id(self):
        # Only Python source is packaged, with no native ABI artifacts.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
