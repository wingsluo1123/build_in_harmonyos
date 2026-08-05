import os
import sys

from conan import ConanFile


class AsciidocTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["asciidoc"]
        pkg_root = pkg.package_folder
        bin_dir = os.path.join(pkg_root, "bin")

        asciidoc_bin = os.path.join(bin_dir, "asciidoc")

        # Smoke test: version check
        # With pip install --target, Python modules are at package root
        # The wrapper scripts auto-set PYTHONPATH, so just run directly
        self.run(f'"{asciidoc_bin}" --version')

        # Functional test: convert an AsciiDoc document to HTML
        test_adoc = os.path.join(self.build_folder, "test.adoc")
        output_html = os.path.join(self.build_folder, "test.html")
        with open(test_adoc, "w") as f:
            f.write("= Test Document\n\nHello *world*.\n")

        self.run(f'"{asciidoc_bin}" -o "{output_html}" "{test_adoc}"')

        if not os.path.exists(output_html):
            raise AssertionError("asciidoc did not produce output HTML")

        self.output.info("asciidoc test passed: HTML output generated")
