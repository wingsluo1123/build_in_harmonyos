from conan import ConanFile
from conan.tools.files import get, copy
import os
import sys


class JiratuiConan(ConanFile):
    name = "jiratui"
    version = "1.10.1"
    description = "A Textual User Interface for interacting with Atlassian Jira from your shell"
    license = "MIT"
    homepage = "https://jiratui.sh/"
    url = "https://github.com/whyisdifficult/jiratui"
    topics = ("jira", "tui", "cli", "terminal", "task-management")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        install_prefix = os.path.join(self.build_folder, "staging")
        os.makedirs(install_prefix, exist_ok=True)

        # jiratui 是纯 Python 包，直接安装预编译 wheel（py3-none-any）
        # 不从 sdist 构建，避免触发 uv_build -> maturin -> rust 构建链
        self.run(
            f'{sys.executable} -m pip install --target {install_prefix} --no-deps jiratui==1.10.1'
        )

        deps = [
            "click>=8.4.2,<9.0.0",
            "gitpython>=3.1.47,<3.2.0",
            "httpx>=0.28.1",
            "marklas==0.8.2",
            "puremagic>=2.2.0,<3.0.0",
            "pydantic-settings[yaml]>=2.14.2,<3.0.0",
            "python-dateutil>=2.9.0.post0",
            "python-json-logger>=4.1.0,<5.0.0",
            "textual-autocomplete>=4.0.6",
            "textual-image>=0.13.2,<0.14.0",
            "textual[syntax]>=8.2.7,<9.0.0",
            "urllib3>=2.6.3,<2.8.0",
            "xdg-base-dirs>=6.0.2",
            "mistune>=3.2",
        ]
        for dep in deps:
            self.run(f'{sys.executable} -m pip install --target {install_prefix} "{dep}"')

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        if os.path.exists(staging):
            copy(self, "*", staging, self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        self.runenv_info.define("PYTHONPATH", [
            os.path.join(self.package_folder, "lib"),
            self.package_folder,
        ])
