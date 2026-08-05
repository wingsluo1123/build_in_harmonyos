#!/usr/bin/env python3
"""Conan recipe for aqua v2.60.0."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AquaConan(ConanFile):
    name = "aqua"
    version = "v2.60.0"
    description = "Declarative version manager for CLI tools"
    license = "MIT"
    homepage = "https://github.com/aquaproj/aqua"
    url = "https://github.com/aquaproj/aqua"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                "The upstream pre-built aqua package used for OHOS PC is linux/arm64 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        # Local mirror fallback for environments where GitHub is unreachable
        local_mirror = os.path.join(
            os.environ.get("HOME", ""), "tmp", sources["filename"]
        )
        if os.path.isfile(local_mirror):
            import shutil
            dst = os.path.join(self.source_folder, sources["filename"])
            shutil.copy2(local_mirror, dst)
            self.output.info(f"Using local mirror: {local_mirror}")
        else:
            download(self, sources["url"], sources["filename"], sha256=sources["sha256"])
        self.run(f'tar xzf "{sources["filename"]}"')

    def build(self):
        apply_conandata_patches(self)
        self.output.info(
            "Using upstream pre-built aqua linux/arm64 release package; "
            "the OHOS CI worker currently does not provide a Go toolchain."
        )

    def package(self):
        binary = self.conan_data["build"]["binary"]
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Copy from source_folder (already extracted in source()) so patches
        # applied in build() are reflected in the packaged binary.
        copy(self, binary, src=self.source_folder, dst=bin_dir, keep_path=False)
        binary_path = os.path.join(bin_dir, binary)
        os.chmod(binary_path,
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)
        self._sign_ohos_binary(binary_path)
        license_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_src):
            copy(self, "LICENSE", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        readme_src = os.path.join(self.source_folder, "README.md")
        if os.path.isfile(readme_src):
            copy(self, "README.md", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "aqua"),
                 keep_path=False)

    def _sign_ohos_binary(self, binary_path):
        if str(self.settings.os) != "OHOS":
            return

        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; the OHOS release worker must sign aqua"
            )
            return

        signed_path = binary_path + ".signed"
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{binary_path}" || true',
                quiet=True,
            )
        self.run(
            f'"{signer}" sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        os.replace(signed_path, binary_path)
        os.chmod(binary_path,
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
