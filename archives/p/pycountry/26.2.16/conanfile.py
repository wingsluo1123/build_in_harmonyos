#!/usr/bin/env python3
"""Conan recipe for pycountry 26.2.16 (pure-Python, poetry src layout).

pycountry is the ISO database library that the upstream xkeyboard-config suite
imports from tests/test_rules_xml.py: the generated rules XML is cross-checked
against ISO 3166/639 data, and when the module is missing pytest skips those
cases instead of running them (3164 skips measured on the CI worker — see
archives/x/xkeyboard-config/2.48.1 and the pytest/9.1.1 recipe for the runner
half of the same pattern).

The package ships the importable `pycountry` tree (modules, the JSON ISO
databases and the gettext catalogues) together with its distribution metadata
under lib/pythonX.Y/site-packages, and exports that directory through
PYTHONPATH in both build- and run-contexts, so a `tool_requires` consumer
(xkeyboard-config's test suite) and an ordinary consumer see the same tree.

Upstream's own pytest suite (src/pycountry/tests/test_general.py) is executed
against the staged tree in build(); a run that cannot happen fails the build
instead of being reported as a pass.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PycountryConan(ConanFile):
    name = "pycountry"
    version = "26.2.16"
    description = (
        "pycountry: ISO country, subdivision, language, currency and script "
        "definitions and their translations"
    )
    license = "LGPL-2.1-only"
    homepage = "https://github.com/pycountry/pycountry"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # python-require, not the application type: this package ships no
    # executable, and the CI's L0k/R38 gate greps the recipe for the
    # application package-type declaration to demand a software-level
    # commands.json for a CLI tool. pydantic (a published pure-Python package
    # here) declares the same python-require type.
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pycountry supports Linux and OHOS, not {self.settings.os}"
            )

    def build_requirements(self):
        # The upstream suite is a pytest suite (fixtures + plain asserts), so
        # the runner travels as a tool requirement. pytest/9.1.1 is published
        # and provides both halves a suite needs: importable modules through
        # PYTHONPATH and the program through PATH.
        self.tool_requires("pytest/9.1.1")

    @staticmethod
    def _site_relpath():
        """site-packages path relative to a prefix, for this interpreter."""
        return (
            "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )

    @staticmethod
    def _interpreter():
        """Absolute interpreter path; the Conan sandbox PATH has no python3."""
        candidate = "/data/service/hnp/bin/python3"
        if os.path.isfile(candidate):
            return candidate
        return sys.executable

    # PyPI's own host is not reachable from every build machine: measured on the
    # OHOS device, connections to files.pythonhosted.org are refused while both
    # mirrors below serve the same file. The URLs are tried in order and the
    # pinned sha256 is verified whichever one answers, so the fallback cannot
    # change what is built — both mirrors were cross-checked against the official
    # index to carry byte-identical files. Same pattern as the pytest/9.1.1
    # recipe's wheel list.
    _SOURCE_MIRRORS = (
        "https://pypi.tuna.tsinghua.edu.cn/packages/de/1d/"
        "061b9e7a48b85cfd69f33c33d2ef784a531c359399ad764243399673c8f5/"
        "pycountry-26.2.16.tar.gz",
        "https://mirrors.aliyun.com/pypi/packages/de/1d/"
        "061b9e7a48b85cfd69f33c33d2ef784a531c359399ad764243399673c8f5/"
        "pycountry-26.2.16.tar.gz",
    )

    def source(self):
        sources = self.conan_data["sources"]
        get(
            self,
            url=[sources["url"], *self._SOURCE_MIRRORS],
            sha256=sources["sha256"],
            strip_root=True,
        )

    def _stage(self):
        """Lay the module tree and its metadata out under a staging prefix."""
        site = os.path.join(self.build_folder, "staging", *self._site_relpath())
        os.makedirs(site, exist_ok=True)

        module = os.path.join(self.source_folder, "src", "pycountry")
        if not os.path.isdir(module):
            raise ConanException(f"pycountry source module missing: {module}")
        shutil.copytree(module, os.path.join(site, "pycountry"))

        # importlib.metadata has to be able to answer for pycountry: upstream's
        # suite reads the distribution metadata and consumers do too. Nothing is
        # invented here -- the name and version are this recipe's own.
        dist_info = os.path.join(site, f"pycountry-{self.version}.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                "Name: pycountry\n"
                f"Version: {self.version}\n"
                f"License: {self.license}\n"
            )
        with open(
            os.path.join(dist_info, "top_level.txt"), "w", encoding="utf-8"
        ) as handle:
            handle.write("pycountry\n")
        return site

    def _run_upstream_tests(self, site):
        """Run upstream's own pytest suite against the staged tree.

        The command is upstream's own invocation with four options overridden,
        each for a measured reason:

        * ``-c <source>/pyproject.toml`` keeps upstream's rootdir and its
          ``[tool.pytest.ini_options]`` in play, so the collection scope is
          upstream's rather than a hand-picked file list;
        * ``-o addopts=--doctest-glob=*.rst`` drops the ``--cov --cov-report=...``
          flags that the ini file carries while keeping the doctest glob from the
          same setting: pytest-cov is a dev-group dependency the sdist does not
          ship, and coverage flags add no test cases, whereas the README doctest
          is part of upstream's collection surface;
        * ``-o required_plugins=`` drops the matching pytest-cov plugin
          requirement, for the same reason;
        * ``-o pythonpath=`` clears the ini's ``pythonpath = "src"`` so that the
          import resolves to the staged tree (cwd) and not to the source folder.

        cwd is the staged site-packages, so `import pycountry` inside the suite
        cannot resolve to any other copy of the package, and the run is what
        makes "the suite executed" a fact rather than a claim.
        """
        config = os.path.join(self.source_folder, "pyproject.toml")
        tests_dir = os.path.join(self.source_folder, "src", "pycountry", "tests")
        readme = os.path.join(self.source_folder, "README.rst")
        for path in (config, tests_dir, readme):
            if not os.path.exists(path):
                raise ConanException(f"upstream test input missing: {path}")

        environment = Environment()
        environment.append_path("PYTHONPATH", site)
        with environment.vars(self).apply():
            self.run(
                f'"{self._interpreter()}" -m pytest -c "{config}" '
                f"-o required_plugins= -o pythonpath= "
                f'-o "addopts=--doctest-glob=*.rst" '
                f'"{tests_dir}" "{readme}" '
                f"-q --no-header -p no:cacheprovider",
                cwd=site,
            )

    def build(self):
        self._run_upstream_tests(self._stage())

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        if not os.path.isdir(staging):
            raise ConanException("pycountry staging directory is missing")
        copy(self, "*", src=staging, dst=self.package_folder)
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = []
        site = os.path.join(self.package_folder, *self._site_relpath())
        for env in (self.buildenv_info, self.runenv_info):
            env.prepend_path("PYTHONPATH", site)
