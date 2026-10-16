"""Package the fixed mrtparse 1.6 Python module and upstream examples/samples."""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, unzip
from conan.tools.layout import basic_layout


class MrtparseConan(ConanFile):
    name = "mrtparse"
    version = "1.6"
    description = "MRT routing-record parser with extended timestamp decoding"
    license = "Apache-2.0"
    homepage = "https://github.com/t2mune/mrtparse"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "LICENSE.upstream", src=self.recipe_folder, dst=self.export_sources_folder)

    def source(self):
        archive = os.environ.get("MRTPARSE_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as stream:
                digest = hashlib.sha256(stream.read()).hexdigest()
            if digest != self.conan_data["sources"]["sha256"]:
                raise ConanException("mrtparse source archive SHA-256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **self.conan_data["sources"], extract_filter="data")
        apply_conandata_patches(self)

    def build(self):
        self.run("python3 -m compileall -q mrtparse", cwd=self.source_folder)

    def package(self):
        module = os.path.join(self.package_folder, "lib", "python", "mrtparse")
        if not copy(self, "*.py", src=os.path.join(self.source_folder, "mrtparse"), dst=module):
            raise ConanException("mrtparse module was not packaged")
        for directory in ("examples", "samples"):
            copy(self, "*", src=os.path.join(self.source_folder, directory),
                 dst=os.path.join(module, directory))
        if not copy(self, "LICENSE.upstream", src=self.export_sources_folder,
                    dst=os.path.join(self.package_folder, "licenses"), keep_path=False):
            raise ConanException("mrtparse upstream Apache-2.0 license was not packaged")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
