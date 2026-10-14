import os
import shlex
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, download, get


class WurlitzerConan(ConanFile):
    name = "wurlitzer"
    version = "3.1.1"
    description = "Capture native C stdout and stderr in Python context managers"
    license = "MIT"
    homepage = "https://github.com/minrk/wurlitzer"
    url = "https://github.com/minrk/wurlitzer"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("wurlitzer requires POSIX file descriptors")
        if sys.version_info < (3, 9):
            raise ConanInvalidConfiguration("The pinned upstream test runner requires Python 3.9+")

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
        env.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        with env.vars(self).apply():
            self.run(f'{python} -m pytest --collect-only -q test.py', cwd=self.source_folder)
            report = shlex.quote(os.path.join(self.build_folder, "upstream-tests.xml"))
            temporary = shlex.quote(os.path.join(self.build_folder, "pytest-tmp"))
            self.run(f'{python} -m pytest -v test.py --basetemp={temporary} '
                     f'--junitxml={report}', cwd=self.source_folder)

    def package(self):
        module_dir = os.path.join(self.package_folder, "share", "wurlitzer")
        copy(self, "wurlitzer.py", src=self.source_folder, dst=module_dir)
        copy(self, "*", src=os.path.join(self.source_folder, "wurlitzer.egg-info"),
             dst=os.path.join(module_dir, "wurlitzer.egg-info"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "share", "wurlitzer"))
