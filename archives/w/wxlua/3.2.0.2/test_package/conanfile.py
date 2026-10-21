import io
import os
from pathlib import Path
import shlex
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
import importlib.util

class WxLuaTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        spec = importlib.util.spec_from_file_location("wxlua_gui_runner", Path(self.source_folder) / "gui_runner.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        run_gui = helper.run_gui
        package = self.dependencies["wxlua"].package_folder
        gtk = self.dependencies["gtk"].package_folder
        runtime = dict(os.environ)
        runtime.update(VirtualRunEnv(self).vars().items())

        def execute(command, child_env):
            environment = Environment()
            for name, value in child_env.items():
                environment.define(name, value)
            output = io.StringIO()
            with environment.vars(self).apply():
                self.run("timeout 120 " + shlex.join(str(x) for x in command), env=[], stdout=output, stderr=output)
            return output.getvalue()

        run_gui([Path(package) / "bin" / "wxLua", Path(self.source_folder) / "consumer.lua"],
                Path(gtk) / "bin" / "broadwayd", runtime,
                Path(self.build_folder) / "gui-evidence", "WXLUA_CONSUMER_PASS 10", executor=execute)

        binary_dir = Path(self.build_folder)
        run_gui([binary_dir / "consumer"], Path(gtk) / "bin" / "broadwayd", runtime,
                binary_dir / "cpp-evidence", "WXLUA_CPP_PASS 4", executor=execute)
        run_gui([binary_dir / "module_host"],
                Path(gtk) / "bin" / "broadwayd", runtime,
                binary_dir / "module-evidence", "WXLUA_MODULE_PASS", executor=execute)
