"""Build the upstream pure Python wheel and run its original pytest suite."""
import glob
import hashlib
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, unzip
from conan.tools.layout import basic_layout


class PortForConan(ConanFile):
    name = "port-for"
    version = "1.0.0"
    description = "Manage local TCP port associations without losing unordered port ranges"
    license = "MIT"
    homepage = "https://github.com/fizyk/port-for"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def requirements(self):
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", libs=False, run=True)

    def build_requirements(self):
        for ref in (
            "pytest/9.1.1#aa5f4d0049cf82ea3d3af0687e9cb837",
            "iniconfig/2.3.0#c831dd198deb51d8d999745a762d22b3",
            "packaging/26.3#c732201728a68e7ec0af958d078aa43c",
            "pluggy/1.6.0#6bc5d540fbca1124212ef8a72d05a876",
            "pygments/2.20.0.1#6b4d0d48d1925471aa0145d75ce983c5",
        ):
            self.test_requires(ref, run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        archive = os.getenv("PORT_FOR_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as stream:
                if hashlib.sha256(stream.read()).hexdigest() != source["sha256"]:
                    raise ConanException("port-for sdist SHA256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **source, strip_root=True, extract_filter="data")
        apply_conandata_patches(self)

    def generate(self):
        python = self.dependencies["python"].package_folder
        env = Environment()
        env.define("PYTHONHOME", python)
        env.prepend_path("PATH", os.path.join(python, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(python, "lib"))
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        env.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        env.define_path("PYTHONPATH", os.path.join(self.build_folder, "build-tools"))
        for name in ("pytest", "iniconfig", "packaging", "pluggy", "pygments"):
            package = self.dependencies[name].package_folder
            for relative in ("lib/python", "lib/python/site-packages", "lib/python3.12/site-packages"):
                env.prepend_path("PYTHONPATH", os.path.join(package, relative))
        env.vars(self).save_script("port-for-runtime")

    def build(self):
        tools = os.path.join(self.build_folder, "build-tools")
        os.makedirs(tools, exist_ok=True)
        for tool in self.conan_data["build_tools"].values():
            inputs = os.getenv("PORT_FOR_BUILD_TOOL_INPUT")
            filename = tool["url"].rsplit("/", 1)[-1]
            if tool["url"].startswith("file://"):
                archive = tool["url"][len("file://"):]
            elif inputs:
                archive = os.path.join(inputs, filename)
            else:
                get(self, **tool, destination=tools, extract_filter="data")
                continue
            with open(archive, "rb") as stream:
                if hashlib.sha256(stream.read()).hexdigest() != tool["sha256"]:
                    raise ConanException("port-for build tool SHA256 mismatch: " + filename)
            unzip(self, archive, destination=tools, extract_filter="data")
        python = os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")
        commands = [
            [python, "-B", "-c", "import setuptools,wheel; print(setuptools.__version__,wheel.__version__); "
             "assert setuptools.__version__ == '84.0.0'; assert wheel.__version__ == '0.45.1'"],
            [python, "-B", "-m", "pytest", "tests", "-ra", "--basetemp",
             os.path.join(self.build_folder, "pytest-tmp")],
            [python, "-B", "-c", "import setuptools.build_meta as backend; print(backend.build_wheel("
             + repr(os.path.join(self.build_folder, "dist")) + "))"],
        ]
        for command in commands:
            self.run(shlex.join(command), cwd=self.source_folder, env="port-for-runtime")

    def package(self):
        wheels = glob.glob(os.path.join(self.build_folder, "dist", "port_for-1.0.0-*.whl"))
        if len(wheels) != 1:
            raise ConanException("Expected one port-for upstream wheel")
        destination = os.path.join(self.package_folder, "lib", "python")
        unzip(self, wheels[0], destination=destination, extract_filter="data")
        if not os.path.isfile(os.path.join(destination, "port_for", "__init__.py")):
            raise ConanException("Built wheel lacks port_for package")
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        binary = os.path.join(self.package_folder, "bin", "port-for")
        os.makedirs(os.path.dirname(binary), exist_ok=True)
        with open(binary, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("#!/usr/bin/env python3.12\nfrom port_for.cmd import main\nmain()\n")
        os.chmod(binary, 0o755)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        python = self.dependencies["python"].package_folder
        self.runenv_info.define("PYTHONHOME", python)
        self.runenv_info.prepend_path("PATH", os.path.join(python, "bin"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(python, "lib"))
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
