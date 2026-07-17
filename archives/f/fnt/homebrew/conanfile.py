#!/usr/bin/env python3
"""Conan recipe for fnt — a font manager shell script (no compilation needed)."""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout
import os


class FntConan(ConanFile):
    name = "fnt"
    version = "homebrew"
    description = "Apt for fonts, the missing font manager for macOS/linux"
    license = "MIT"
    homepage = "https://github.com/alexmyczko/fnt"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Fix shebang for OpenHarmony (HMDFS doesn't have /usr/bin/env bash)
        fnt_path = os.path.join(self.source_folder, "fnt")
        if os.path.exists(fnt_path):
            with open(fnt_path) as f:
                content = f.read()
            # Fix shebang
            content = content.replace("#!/usr/bin/env bash", "#!/data/service/hnp/bin/bash")
            # Add HarmonyOS to platform detection
            content = content.replace(
                "Linux|GNU/kFreeBSD|GNU)",
                "Linux|GNU/kFreeBSD|GNU|HarmonyOS)"
            )
            with open(fnt_path, "w") as f:
                f.write(content)

    def package(self):
        import shutil
        dst_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin, exist_ok=True)
        src_fnt = os.path.join(self.source_folder, "fnt")
        dst_fnt = os.path.join(dst_bin, "fnt")
        shutil.copyfile(src_fnt, dst_fnt)
        # Try system chmod as fallback for HMDFS
        os.system("chmod 755 " + dst_fnt)
        copy(self, "fnt.1", src=self.source_folder, dst=os.path.join(self.package_folder, "man", "man1"))
        copy(self, "completions/_fnt", src=self.source_folder, dst=os.path.join(self.package_folder, "zsh", "site-functions"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []