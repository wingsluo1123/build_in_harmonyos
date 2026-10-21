from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout
import os


class Irclog2htmlConan(ConanFile):
    name = "irclog2html"
    version = "4.0.0"
    description = "Convert IRC logs to HTML"
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://mg.pov.lt/irclog2html/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        self.run("python3 -m compileall -q src/irclog2html", cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "src", "irclog2html")
        target = os.path.join(self.package_folder, "lib", "python", "irclog2html")
        copy(self, "*.py", src=source, dst=target, keep_path=False,
             excludes=["tests/*"])
        if not copy(self, "irclog.css", src=source, dst=target,
                    keep_path=False):
            raise ConanException("irclog.css is missing from the package")
        if not copy(self, "COPYING", src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False):
            raise ConanException("upstream COPYING license file is missing")
        bin_dir = os.path.join(self.package_folder, "bin")
        commands = {
            "irclog2html": ("irclog2html", "main"),
            "logs2html": ("logs2html", "main"),
            "irclogsearch": ("irclogsearch", "main"),
            "irclogserver": ("irclogserver", "main"),
        }
        os.makedirs(bin_dir, exist_ok=True)
        for command, (module, function) in commands.items():
            path = os.path.join(bin_dir, command)
            save(self, path, "\n".join((
                "#!/usr/bin/env python3",
                "import os, sys",
                "sys.path.insert(0, os.path.abspath(os.path.join(",
                "    os.path.dirname(__file__), '..', 'lib', 'python'))) ",
                f"from irclog2html.{module} import {function}",
                f"{function}()",
                "",
            )))
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
