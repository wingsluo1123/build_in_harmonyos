#!/usr/bin/env python3
"""Conan test_package for zeGrapher 3.1.1.

zeGrapher is a Qt5 GUI application; upstream ships no test suite (no
tests/ directory, no test target in ZeGrapher.pro — see notes.md).  The
smoke test runs the packaged ZeGrapher binary headless under
QT_QPA_PLATFORM=offscreen: the app boots into the Qt event loop with no
CLI argument handling, so we assert it survives until a timeout kills it
(any crash / missing-lib / platform-plugin failure exits non-zero within
a second).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class ZegrapherTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _runtime_env(self, build_folder):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(build_folder, "test-home")
        xdg_runtime = os.path.join(build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        return env

    def generate(self):
        self._runtime_env(self.build_folder).vars(self).save_script(
            "conanrun_zegrapher_test"
        )

    def test(self):
        if not can_run(self):
            return
        app = self.dependencies.get("zegrapher")
        app_bin = (
            os.path.join(app.package_folder, "bin", "ZeGrapher") if app else None
        )
        if not app_bin or not os.path.isfile(app_bin):
            raise ConanException("ZeGrapher binary not found in package")
        env_vars = self._runtime_env(self.build_folder).vars(self, scope="run")
        smoke = os.path.join(os.path.dirname(__file__), "smoke_test.sh")
        with env_vars.apply():
            self.output.info("Running test_package smoke_test.sh")
            self.run('sh "%s" "%s"' % (smoke, app_bin))
