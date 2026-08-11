from conan import ConanFile
from conan.tools.files import get, copy, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class BragConan(ConanFile):
    name = "brag"
    version = "1.4.3"
    description = "Download and assemble multipart binaries from newsgroups"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/brag/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("tcl/8.6.16@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebang for OHOS
        import pathlib
        brag_file = pathlib.Path(self.source_folder) / "brag"
        content = brag_file.read_text()
        content = content.replace("#!/bin/sh", "#!/system/bin/sh")
        # tcl package installs tclsh8.6, not tclsh
        content = content.replace("exec tclsh", "exec tclsh8.6")
        brag_file.write_text(content)

    def package(self):
        copy(self, "brag", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "brag.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "CHANGES", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "brag"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "brag"), keep_path=False)
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "brag"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # tcl's tclsh8.6 is in its bin dir; add to PATH so brag can find it
        tcl_bindir = os.path.join(self.dependencies["tcl"].package_folder, "bin")
        if os.path.isdir(tcl_bindir):
            self.runenv_info.prepend_path("PATH", tcl_bindir)
            self.buildenv_info.prepend_path("PATH", tcl_bindir)
