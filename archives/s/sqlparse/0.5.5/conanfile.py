import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SqlparseConan(ConanFile):
    name = "sqlparse"
    version = "0.5.5"
    license = "BSD-3-Clause"
    description = "Non-validating Python SQL parser and formatter"
    homepage = "https://github.com/andialbrecht/sqlparse"
    package_type = "application"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        test_env = Environment()
        paths = []
        # CI's Python may have neither pytest nor pip. Use checked source archives.
        for name, dependency in self.conan_data["test_dependencies"].items():
            if name in ("exceptiongroup", "tomli") and sys.version_info >= (3, 11):
                continue
            folder = os.path.join(self.build_folder, "test-dependencies", name)
            get(self, **dependency, destination=folder, strip_root=True)
            paths.append(os.path.join(folder, "src"))
        test_env.prepend_path("PYTHONPATH", paths)
        test_env.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        temp_dir = os.path.join(self.build_folder, "pytest-tmp")
        with test_env.vars(self).apply():
            self.run(f'"{sys.executable}" -m pytest --collect-only -q tests',
                     cwd=self.source_folder)
            test_command = (f'"{sys.executable}" -m pytest -q '
                            f'--basetemp="{temp_dir}" tests')
            log_path = os.path.join(self.build_folder, "pytest.log")
            with open(log_path, "w", encoding="utf-8") as log:
                result = self.run(test_command, cwd=self.source_folder,
                                  stdout=log, stderr=log, ignore_errors=True)
            with open(log_path, encoding="utf-8") as log:
                output = log.read()
            self.output.info(output)
            if result:
                if "BlockingIOError: [Errno 11] Resource temporarily unavailable" not in output:
                    raise ConanException("Official pytest suite failed; see pytest.log")
                self.output.warning("Worker process resources exhausted; retrying the full suite once")
                self.run(test_command, cwd=self.source_folder)

    def package(self):
        copy(self, "*.py", src=os.path.join(self.source_folder, "sqlparse"),
             dst=os.path.join(self.package_folder, "lib", "python", "sqlparse"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        module_dir = os.path.join(self.package_folder, "lib", "python")
        self.runenv_info.prepend_path("PYTHONPATH", module_dir)
        self.buildenv_info.prepend_path("PYTHONPATH", module_dir)
