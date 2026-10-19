#!/usr/bin/env python3
"""Conan recipe for utm 0.8.1 (pure Python)."""
import os
import shlex
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, download, get, save


class UtmConan(ConanFile):
    name = "utm"
    version = "0.8.1"
    description = "Bidirectional UTM-WGS84 coordinate conversion for Python"
    license = "MIT"
    homepage = "https://github.com/Turbo87/utm"
    url = "https://github.com/Turbo87/utm"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("The command launcher requires Linux or OHOS")
        if sys.version_info < (3, 9):
            raise ConanInvalidConfiguration("The pinned pytest runner requires Python 3.9+")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        deps = os.path.join(self.source_folder, "_test_deps")
        os.makedirs(deps, exist_ok=True)
        for artifact in self.conan_data["test_dependencies"]:
            wheel = os.path.join(deps, artifact["url"].rsplit("/", 1)[1])
            download(self, artifact["url"], wheel, sha256=artifact["sha256"])
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(deps)
            os.remove(wheel)

    def build(self):
        python = shlex.quote(sys.executable)
        env = Environment()
        env.prepend_path("PYTHONPATH", os.path.join(self.source_folder, "_test_deps"))
        env.prepend_path("PYTHONPATH", self.source_folder)
        env.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        with env.vars(self).apply():
            self.run(f"{python} -m pytest --collect-only -q test", cwd=self.source_folder)
            report = shlex.quote(os.path.join(self.build_folder, "upstream-tests.xml"))
            temporary = shlex.quote(os.path.join(self.build_folder, "pytest-tmp"))
            self.run(f"{python} -m pytest -v test --basetemp={temporary} "
                     f"--junitxml={report}", cwd=self.source_folder)

    def package(self):
        module_dir = os.path.join(self.package_folder, "share", "utm")
        copy(self, "*.py", src=os.path.join(self.source_folder, "utm"),
             dst=os.path.join(module_dir, "utm"))
        copy(self, "*", src=os.path.join(self.source_folder, "utm.egg-info"),
             dst=os.path.join(module_dir, "utm.egg-info"))
        copy(self, "utm-converter", src=os.path.join(self.source_folder, "scripts"),
             dst=module_dir)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        launcher = os.path.join(self.package_folder, "bin", "utm-converter")
        save(self, launcher, f"#!{os.path.realpath(sys.executable)}\n" + '''import os
import runpy
import sys

module_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "share", "utm"))
sys.path.insert(0, module_dir)
if sys.argv[1:] == ["--version"]:
    import utm
    print("utm-converter " + utm.__version__)
else:
    runpy.run_path(os.path.join(module_dir, "utm-converter"), run_name="__main__")
''')
        os.chmod(launcher, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "share", "utm"))
