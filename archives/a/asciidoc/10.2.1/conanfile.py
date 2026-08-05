#!/usr/bin/env python3
"""Conan recipe for asciidoc — Python text document format processor.

asciidoc converts AsciiDoc documents to HTML, DocBook and other formats.
It provides two command-line tools: asciidoc and a2x.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AsciidocConan(ConanFile):
    name = "asciidoc"
    version = "10.2.1"
    description = "AsciiDoc is a text document format for writing notes, documentation, articles, books, ebooks, web pages, man pages and blogs."
    license = "GPL-2.0-or-later"
    homepage = "https://asciidoc.org/"
    url = "https://asciidoc.org/"

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Python package: install via pip to a flat staging directory
        # pip install --target creates: asciidoc/, bin/asciidoc, bin/a2x, asciidoc-10.2.1.dist-info/
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'python3 -m pip install "{self.source_folder}" --no-deps --target="{staging}"')

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        # Copy everything: Python package, bin scripts, dist-info
        copy(self, "*", src=staging, dst=self.package_folder)
        # Replace entry point scripts with self-contained wrappers
        bin_dir = os.path.join(self.package_folder, "bin")
        for script_name in ("asciidoc", "a2x"):
            script_path = os.path.join(bin_dir, script_name)
            if os.path.exists(script_path):
                self._create_wrapper(script_path, script_name)

    def _create_wrapper(self, script_path, entry_name):
        """Replace setuptools entry point with a wrapper that auto-sets PYTHONPATH."""
        modules = {
            "asciidoc": "asciidoc.asciidoc",
            "a2x": "asciidoc.a2x",
        }
        module = modules.get(entry_name)
        if not module:
            return
        wrapper = (
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "_d = os.path.dirname(os.path.abspath(__file__))\n"
            "_p = os.path.dirname(_d)\n"
            "if _p not in sys.path:\n"
            "    sys.path.insert(0, _p)\n"
            f"from {module} import cli\n"
            "sys.exit(cli())\n"
        )
        with open(script_path, "w") as f:
            f.write(wrapper)
        try:
            os.chmod(script_path, 0o755)
        except OSError:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
