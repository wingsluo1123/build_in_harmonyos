import os
import sys

from conan import ConanFile


class AsciidocTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["asciidoc"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        lib_dir = os.path.join(pkg.package_folder, "lib")

        # Find site-packages for PYTHONPATH
        py_ver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site_packages = os.path.join(lib_dir, py_ver, "site-packages")

        asciidoc_bin = os.path.join(bin_dir, "asciidoc")

        # Smoke test: version check
        self.run('PYTHONPATH="%s" "%s" --version' % (site_packages, asciidoc_bin))

        # Functional test: convert an AsciiDoc document to HTML
        test_adoc = "test.adoc"
        with open(test_adoc, "w") as f:
            f.write("= Test Document\n\nHello *world*.\n")

        output_html = "test.html"
        self.run('PYTHONPATH="%s" "%s" -o "%s" "%s"' % (
            site_packages, asciidoc_bin, output_html, test_adoc))

        if not os.path.exists(output_html):
            raise AssertionError("asciidoc did not produce output HTML")

        self.output.info("asciidoc test passed: HTML output generated")
