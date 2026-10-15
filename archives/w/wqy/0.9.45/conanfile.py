import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class WqyConan(ConanFile):
    name = "wqy"
    version = "0.9.45"
    description = "WenQuanYi Zen Hei TrueType Collection for app-scoped HarmonyOS font loading"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/wqy/"
    url = "https://sourceforge.net/projects/wqy/"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # This is a data-only package; the hook exists for the repository's
        # recipe verifier and applies any future source patches consistently.
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "wqy-zenhei.ttc",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res", "fonts"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        documentation = os.path.join(self.package_folder, "res", "share", "doc", "wqy")
        copy(self, "README", src=self.source_folder, dst=documentation, keep_path=False)
        copy(self, "AUTHORS", src=self.source_folder, dst=documentation, keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["res"]
