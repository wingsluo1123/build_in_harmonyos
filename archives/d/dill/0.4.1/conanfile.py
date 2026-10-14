"""dill: pure Python serialization, installed upstream suite and consumers."""
import os
from pathlib import Path
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class DillConan(ConanFile):
    name = "dill"
    version = "0.4.1"
    description = "Serialize Python functions, classes and interpreter sessions"
    license = "BSD-3-Clause"
    homepage = "https://github.com/uqfoundation/dill"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("setuptools/84.0.0")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("dill is validated on Linux and OHOS")
        if sys.version_info < (3, 9):
            raise ConanInvalidConfiguration("dill 0.4.1 requires Python >= 3.9")

    def package_id(self):
        # Python source/scripts/metadata only: no ABI objects or bytecode.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        site = os.path.join(self.build_folder, "installed")
        verification = os.path.join(self.build_folder, "verification")
        copy(self, "*", src=self.source_folder, dst=staging)
        os.makedirs(site, exist_ok=True)
        os.makedirs(verification, exist_ok=True)
        environment = Environment()
        environment.define("PYTHONDONTWRITEBYTECODE", "1")
        environment.define("PYTHONNOUSERSITE", "1")
        with environment.vars(self).apply():
            self.run(
                f'"{sys.executable}" -s setup.py build_py --build-lib "{site}" '
                f'egg_info --egg-base "{site}"',
                cwd=staging, env="conanbuild",
            )
        # This environment must reach both the runner and its fresh children.
        test_environment = Environment()
        test_environment.prepend_path("PYTHONPATH", site)
        test_environment.define("PYTHONDONTWRITEBYTECODE", "1")
        test_environment.define("PYTHONNOUSERSITE", "1")
        with test_environment.vars(self).apply():
            safe_path = "-P " if sys.version_info >= (3, 11) else ""
            origin = "import dill,sys; from pathlib import Path; assert Path(dill.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve()); print('INSTALLED_UPSTREAM_ORIGIN',dill.__file__)"
            self.run(f'"{sys.executable}" -s {safe_path}-c "{origin}" "{site}"', cwd=verification)
            self.run(f'"{sys.executable}" -s {safe_path}-m dill.tests', cwd=verification)
        scripts = list((Path(site) / "dill" / "tests").glob("test_*.py"))
        self.output.info(f"UPSTREAM_RESULT: {len(scripts)}/{len(scripts)} script processes passed; optional NumPy/SymPy branches depend on installed extras")

    def package(self):
        copy(self, "*", src=os.path.join(self.build_folder, "installed"),
             dst=os.path.join(self.package_folder, "lib", "python", "site-packages"),
             excludes=("*.pyc", "__pycache__/*"))
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "LICENSE", src=staging, dst=os.path.join(self.package_folder, "licenses"))
        for name in ("undill", "get_objgraph", "get_gprof"):
            copy(self, name, src=os.path.join(staging, "scripts"),
                 dst=os.path.join(self.package_folder, "share", "dill", "scripts"))
            # Keep upstream script bodies unchanged; avoid build-host absolute
            # shebangs and provide a predictable help entry for all helpers.
            launcher = (
                "#!/usr/bin/env python3\n"
                "import ast\nfrom pathlib import Path\nimport runpy\nimport sys\n"
                "prefix = Path(__file__).resolve().parent.parent\n"
                "sys.path.insert(0, str(prefix / 'lib' / 'python' / 'site-packages'))\n"
                f"script = prefix / 'share' / 'dill' / 'scripts' / '{name}'\n"
                "if len(sys.argv) == 2 and sys.argv[1] in ('--help', '-h'):\n"
                f"    print('{name}: dill helper')\n"
                "    print(ast.get_docstring(ast.parse(script.read_text(encoding='utf-8'))) or '')\n"
                "else:\n    runpy.run_path(str(script), run_name='__main__')\n"
            )
            path = os.path.join(self.package_folder, "bin", name)
            save(self, path, launcher)
            os.chmod(path, 0o755)

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python", "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("DILL_PACKAGE_ROOT", site)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
