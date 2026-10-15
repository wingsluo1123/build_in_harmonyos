"""Build upstream MMLlib's pure wheel and run its complete unittest suite."""
import glob
import hashlib
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, unzip
from conan.tools.layout import basic_layout


class MMLlibConan(ConanFile):
    name = "mmllib"
    version = "1.4"
    description = "Music Macro Language parser and MusicXML converter"
    license = "MirOS"
    homepage = "https://edugit.org/nik/mmllib"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def requirements(self):
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        archive = os.getenv("MMLLIB_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as handle:
                if hashlib.sha256(handle.read()).hexdigest() != source["sha256"]:
                    raise ConanException("MMLlib source SHA256 mismatch")
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
        env.define("PYTHONPATH", os.path.join(self.build_folder, "build-tools"))
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        env.vars(self).save_script("mmllib-runtime")

    def build(self):
        python = os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")
        tools = os.path.join(self.build_folder, "build-tools")
        os.makedirs(tools, exist_ok=True)
        for tool in self.conan_data["build_tools"].values():
            inputs = os.getenv("MMLLIB_BUILD_TOOL_INPUT")
            filename = tool["url"].rsplit("/", 1)[-1]
            if tool["url"].startswith("file://"):
                archive = tool["url"][len("file://"):]
            elif inputs:
                archive = os.path.join(inputs, filename)
            else:
                get(self, **tool, destination=tools, extract_filter="data")
                continue
            with open(archive, "rb") as handle:
                if hashlib.sha256(handle.read()).hexdigest() != tool["sha256"]:
                    raise ConanException("MMLlib build tool SHA256 mismatch")
            unzip(self, archive, destination=tools, extract_filter="data")
        commands = [
            [python, "-B", "-m", "unittest", "discover", "-v"],
            [python, "-B", "-c", "import setuptools; assert setuptools.__version__ == '84.0.0'; "
             "import setuptools.build_meta as backend; print(backend.build_wheel(" +
             repr(os.path.join(self.build_folder, "dist")) + "))"],
        ]
        for command in commands:
            self.run(shlex.join(command), cwd=self.source_folder, env="mmllib-runtime")

    def package(self):
        wheels = glob.glob(os.path.join(self.build_folder, "dist", "mmllib-1.4-*.whl"))
        if len(wheels) != 1:
            raise ConanException("Expected exactly one MMLlib 1.4 wheel")
        destination = os.path.join(self.package_folder, "lib", "python")
        unzip(self, wheels[0], destination=destination, extract_filter="data")
        if not os.path.isfile(os.path.join(destination, "mmllib", "musicxml.py")):
            raise ConanException("Built wheel lacks mmllib.musicxml")
        copy(self, "LICENCE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for command in ("mml2musicxml", "mmllint"):
            binary = os.path.join(self.package_folder, "bin", command)
            os.makedirs(os.path.dirname(binary), exist_ok=True)
            with open(binary, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/usr/bin/env python3.12\nfrom mmllib.cmds import " + command +
                             "\nraise SystemExit(" + command + "())\n")
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
