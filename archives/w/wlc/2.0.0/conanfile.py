"""Build the fixed upstream wheel and retain the complete offline unittest suite."""
import glob
import hashlib
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save, unzip
from conan.tools.layout import basic_layout


class WlcConan(ConanFile):
    name = "wlc"
    version = "2.0.0"
    description = "Command-line client and Python API for Weblate"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/WeblateOrg/wlc"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def requirements(self):
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", libs=False, run=True)

    def build_requirements(self):
        self.test_requires("pyyaml/6.0.2#945ede326d62a17c4827815da56bb22e")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        archive = os.getenv("WLC_SOURCE_ARCHIVE")
        if archive:
            with open(archive, "rb") as handle:
                if hashlib.sha256(handle.read()).hexdigest() != source["sha256"]:
                    raise ConanException("wlc source SHA256 mismatch")
            unzip(self, archive, strip_root=True, extract_filter="data")
        else:
            get(self, **source, strip_root=True, extract_filter="data")
        apply_conandata_patches(self)

    def _extract_wheel(self, item, destination):
        inputs = os.getenv("WLC_WHEEL_INPUT")
        if inputs:
            archive = os.path.join(inputs, item["url"].rsplit("/", 1)[-1])
            with open(archive, "rb") as handle:
                if hashlib.sha256(handle.read()).hexdigest() != item["sha256"]:
                    raise ConanException("wlc dependency wheel SHA256 mismatch: " + archive)
            unzip(self, archive, destination=destination, extract_filter="data")
        else:
            get(self, **item, destination=destination, extract_filter="data")

    def generate(self):
        python = self.dependencies["python"].package_folder
        yaml = self.dependencies["pyyaml"].package_folder
        env = Environment()
        env.define("PYTHONHOME", python)
        env.prepend_path("PATH", os.path.join(python, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(python, "lib"))
        env.define("PYTHONPATH", os.pathsep.join([
            os.path.join(self.build_folder, "build-tools"),
            os.path.join(yaml, "lib", "python", "site-packages"),
        ]))
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        env.unset("WLC_KEY")
        env.unset("WLC_URL")
        env.vars(self).save_script("wlc-build")

    def build(self):
        python = os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")
        tools = os.path.join(self.build_folder, "build-tools")
        for group in ("runtime_wheels", "build_test_wheels"):
            for item in self.conan_data[group].values():
                self._extract_wheel(item, tools)
        commands = [
            [python, "-B", "-c", "import sys,setuptools,yaml; assert sys.version_info[:3] == (3,12,9); "
             "assert setuptools.__version__ == '84.0.0'; assert yaml.__version__ == '6.0.2'; print(sys.version)"],
            [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"],
            [python, "-B", "-c", "from setuptools.build_meta import build_wheel; print(build_wheel("
             + repr(os.path.join(self.build_folder, "dist")) + "))"],
        ]
        for command in commands:
            self.run(shlex.join(command), cwd=self.source_folder, env="wlc-build")

    def package(self):
        wheels = glob.glob(os.path.join(self.build_folder, "dist", "wlc-2.0.0-*.whl"))
        if len(wheels) != 1:
            raise ConanException("Expected exactly one built wlc wheel")
        site = os.path.join(self.package_folder, "lib", "python")
        unzip(self, wheels[0], destination=site, extract_filter="data")
        for item in self.conan_data["runtime_wheels"].values():
            self._extract_wheel(item, site)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for pattern in ("LICENSE*", "COPYING*", "NOTICE*"):
            copy(self, pattern, src=site, dst=os.path.join(self.package_folder, "licenses", "dependencies"))
        launcher = os.path.join(self.package_folder, "bin", "wlc")
        save(self, launcher, '#!/bin/sh\nexec python3.12 -c \'from wlc.main import main; main()\' "$@"\n')
        os.chmod(launcher, 0o755)

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
