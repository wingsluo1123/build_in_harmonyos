#!/usr/bin/env python3
"""Conan recipe for jigsaw-generator 0.2.7.

Upstream (juliangilbey/jigsaw-generator) is a pure Python 3 command-line tool
wrapped in a thin autoconf scaffolding. There is nothing to compile: the
entire `make` build target is a single `sed` substitution that turns
`jigsaw-generate.in` into the installed entry script, and `make install` only
copies files. The recipe reproduces that install layout in the conan package:

  bin/jigsaw-generate                  entry script (substituted, 0755)
  lib/jigsaw-generator/jigsaw/*.py     python package (imported via sys.path)
  lib/jigsaw-generator/templates/*     layout templates + default_config.ini
  share/man/man1/jigsaw-generate.1     man page
  share/doc/jigsaw-generator/*         README/COPYING/ChangeLog/AUTHORS/examples/doc(.tex)

Deliberate deviations from a literal `make install`:
  * `make -C doc build` runs pdflatex to produce doc/jigsaw-generator.pdf.
    A LaTeX install is not (and must not become) a build dependency, so the
    PDF is not built and only the .tex sources are packaged.
  * The entry script bakes pkgdatadir in as an absolute path, exactly like
    `make install --prefix`; here the "prefix" is the conan package folder.
    The layout is stable inside the conan cache, where CI builds and tests it.

Runtime (device-side) prerequisites, documented in README.md/notes.md:
python3 + PyYAML (not present in the ohpcd artifact repo, therefore NOT
declared as a conan dependency) and, for PDF output, pdflatex.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class JigsawGeneratorConan(ConanFile):
    name = "jigsaw-generator"
    version = "0.2.7"
    description = ("CLI tool that turns YAML puzzle definitions into printable "
                   "LaTeX jigsaw / card-sort puzzles")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/juliangilbey/jigsaw-generator"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Fail fast if the tarball layout is not what the recipe expects
        # (tag archive: flat tree, no nested package directory).
        for required in ("jigsaw-generate.in", "jigsaw/generate.py",
                         "jigsaw/__init__.py", "jigsaw/appdirs.py",
                         "templates/default_config.ini", "jigsaw-generate.1",
                         "examples/puzzle-smallhexagon.yaml"):
            p = os.path.join(self.source_folder, *required.split("/"))
            if not os.path.isfile(p):
                raise Exception(f"unexpected source layout: {required} missing")
        # Optional early syntax check when the host has python3 (CI OHOS
        # workers do not; the check is repeated in test_package/test.sh).
        # Bytecode goes to a throwaway cache dir (NOT the source tree) so no
        # .pyc can leak into the package; the check is non-fatal by design.
        if shutil.which("python3"):
            cachedir = os.path.join(self.build_folder, "synchk-cache")
            os.makedirs(cachedir, exist_ok=True)
            try:
                self.run("python3 -m py_compile --cache-dir %s "
                         "jigsaw-generate.in jigsaw/generate.py "
                         "jigsaw/appdirs.py" % cachedir,
                         cwd=self.source_folder, shell=True)
            except Exception as e:
                self.output.warning(
                    "optional python syntax check skipped: %s" % e)

    def package(self):
        pkgdatadir = os.path.join(self.package_folder, "lib", "jigsaw-generator")

        # Entry script: exactly the upstream Makefile.in `build` target
        #   sed -e 's|@pkgdatadir[@]|$(pkgdatadir)|;
        #         s|@PACKAGE_VERSION[@]|$(PACKAGE_VERSION)|;' jigsaw-generate.in
        with open(os.path.join(self.source_folder, "jigsaw-generate.in"),
                  encoding="utf-8") as f:
            entry = f.read()
        entry = entry.replace("@pkgdatadir@", pkgdatadir)
        entry = entry.replace("@PACKAGE_VERSION@", self.version)
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        entry_path = os.path.join(bindir, "jigsaw-generate")
        save(self, entry_path, entry)
        os.chmod(entry_path, 0o755)

        # Data dir (upstream: cp -R jigsaw templates $(pkgdatadir))
        os.makedirs(pkgdatadir, exist_ok=True)
        copy(self, "*", os.path.join(self.source_folder, "jigsaw"),
             os.path.join(pkgdatadir, "jigsaw"), keep_path=False)
        copy(self, "*", os.path.join(self.source_folder, "templates"),
             os.path.join(pkgdatadir, "templates"), keep_path=False)

        # Man page (upstream: cp jigsaw-generate.1 $(mandir)/man1)
        copy(self, "jigsaw-generate.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

        # Docs (upstream docdir minus the LaTeX-built PDF; see module
        # docstring). examples/ carries the sample puzzle YAML data.
        docdir = os.path.join(self.package_folder, "share", "doc",
                              "jigsaw-generator")
        for f in ("README.md", "COPYING", "ChangeLog", "AUTHORS"):
            copy(self, f, self.source_folder, docdir, keep_path=False)
        copy(self, "*", os.path.join(self.source_folder, "examples"),
             os.path.join(docdir, "examples"), keep_path=False)
        copy(self, "*.tex", os.path.join(self.source_folder, "doc"),
             os.path.join(docdir, "doc"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
