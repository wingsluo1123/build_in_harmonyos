#!/usr/bin/env python3
"""Conan recipe for pglast 8.2 (native setuptools C-extension build)."""

import os
from pathlib import Path
import shutil
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class PglastConan(ConanFile):
    name = "pglast"
    version = "8.2"
    description = "PostgreSQL SQL and PL/pgSQL parser, AST and statement prettifier"
    license = "GPL-3.0-or-later", "BSD-3-Clause", "PostgreSQL"
    homepage = "https://github.com/lelit/pglast"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True

    def requirements(self):
        self.requires("python/3.12.9", run=True)

    def build_requirements(self):
        self.tool_requires("setuptools/84.0.0")
        self.tool_requires("cython/3.3.0")
        self.tool_requires("pytest/9.1.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS") or cross_building(self):
            raise ConanInvalidConfiguration("pglast requires a native Linux/OHOS Python build")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("This recipe validates the AArch64 Python ABI")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def export_sources(self):
        export_conandata_patches(self)

    def _python(self):
        return os.path.join(self.dependencies["python"].package_folder, "bin", "python3")

    def _sign(self, path):
        if self.settings.os != "OHOS":
            return
        signer = shutil.which("binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy")
        if not signer or not objcopy:
            raise ConanException("OHOS execution requires binary-sign-tool and llvm-objcopy")
        temporary = str(path) + ".signing"
        shutil.copy2(path, temporary)
        try:
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(f'"{signer}" sign -inFile "{temporary}" '
                     f'-outFile "{temporary}" -selfSign 1')
            os.chmod(temporary, 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _test_tools(self):
        # Test-only wheels are official, SHA256-pinned and isolated from the payload.
        # These optional test packages have no published Conan recipes on ohpcd.
        tools = Path(self.build_folder) / "test-tools"
        tools.mkdir(exist_ok=True)
        for data in self.conan_data["test_tools"].values():
            archive = tools / data["filename"]
            download(self, data["url"], str(archive), sha256=data["sha256"])
            with zipfile.ZipFile(archive) as wheel:
                wheel.extractall(tools)
        return tools

    def build(self):
        staging = Path(self.build_folder) / "staging"
        built = Path(self.build_folder) / "python-package"
        copy(self, "*", src=self.source_folder, dst=str(staging))
        tools = self._test_tools()
        python = self._python()
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        environment = Environment()
        environment.define("CC", compiler)
        environment.define("LDSHARED", f"{compiler} -shared")
        # OHOS dlopen namespaces do not expose interpreter symbols to an
        # extension unless it declares libpython in its own DT_NEEDED.
        python_lib = os.path.join(self.dependencies["python"].package_folder, "lib")
        environment.append("LDFLAGS", f'-L"{python_lib}" -lpython3.12')
        environment.define("AR", shutil.which("llvm-ar") or "ar")
        # The release's extracted AArch64 popcount unit advertises SVE and
        # omits unused Neon helper bodies. Use upstream's complete portable
        # implementation instead of raising the target ISA requirement.
        environment.append("CFLAGS", "-U__ARM_NEON")
        environment.define("MAKEFLAGS", "-j1")
        environment.define("PYTHONHOME", self.dependencies["python"].package_folder)
        environment.define("PYTHONDONTWRITEBYTECODE", "1")
        environment.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        # Use mypy's supported filesystem cache. The Python dependency's
        # SQLite extension is unavailable; this changes no type-check rules.
        config = Path(self.build_folder) / "test-config"
        save(self, str(config / "mypy" / "config"), "[mypy]\nsqlite_cache = False\n")
        environment.define_path("XDG_CONFIG_HOME", str(config))
        environment.prepend_path("PYTHONPATH", str(tools))
        with environment.vars(self).apply():
            self.run(f'"{python}" -c "import setuptools, Cython; '
                     'print(setuptools.__version__, Cython.__version__)"',
                     env=["conanbuild", "conanrun"])
            # mypy's C runtime is test-only. Build it for the actual OHOS ABI;
            # Linux wheels cannot be used as OHOS extension modules.
            tool_source = Path(self.build_folder) / "librt-source"
            get(self, **self.conan_data["test_sources"]["librt"],
                destination=str(tool_source), strip_root=True)
            self.run(f'"{python}" -c "import setuptools,runpy; '
                     'runpy.run_path(\'setup.py\',run_name=\'__main__\')" '
                     f'build --build-base "{self.build_folder}/librt-output" '
                     f'--build-lib "{tools}"', cwd=str(tool_source),
                     env=["conanbuild", "conanrun"])
            for extension in tools.rglob("*.so"):
                self._sign(extension)
            # The release sdist includes the upstream-generated parser.c;
            # do not regenerate it or modify upstream C/Python/test sources.
            self.run(f'"{python}" setup.py build --build-base "{self.build_folder}/output" '
                     f'--build-lib "{built}"', cwd=str(staging),
                     env=["conanbuild", "conanrun"])
            self.run(f'"{python}" setup.py egg_info --egg-base "{built}"',
                     cwd=str(staging), env=["conanbuild", "conanrun"])
            for extension in built.rglob("*.so"):
                self._sign(extension)
            # A source-side package masks build-lib when pytest imports from cwd.
            # Run from the private build directory and retain original tests/config.
            environment.prepend_path("PYTHONPATH", str(built))
        with environment.vars(self).apply():
            self.run(f'"{python}" -m mypy --version', env=["conanbuild", "conanrun"])
            # Upstream skips an absent optional type checker itself. ty's
            # official Linux/musl AArch64 binary SIGSEGVs on this kernel;
            # run its unchanged tests separately on the Windows host.
            # Only override optional coverage instrumentation. The packaged
            # Python's _sqlite3 has an unresolved sqlite3_initialize symbol;
            # all original semantic tests are still collected and executed.
            self.run(f'"{python}" -m pytest -o "addopts=" -c "{staging}/pyproject.toml" '
                     f'"{staging}/tests" --import-mode=importlib '
                     f'--junitxml="{self.build_folder}/upstream-tests.xml"',
                     cwd=self.build_folder, env=["conanbuild", "conanrun"])

    def package(self):
        built = Path(self.build_folder) / "python-package"
        site = Path(self.package_folder) / "lib" / "python3.12" / "site-packages"
        copy(self, "*", src=str(built), dst=str(site), excludes=("*.pyc", "__pycache__/*"))
        for extension in site.rglob("*.so"):
            self._sign(extension)
        if not list((site / "pglast").glob("parser*.so")):
            raise ConanException("pglast parser extension is missing from the installed package")
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "libpg_query"),
             dst=os.path.join(self.package_folder, "licenses", "libpg_query"))
        # Resolve the Python interpreter from Conan runenv and payload from this
        # script's location, keeping both paths relocatable.
        command = os.path.join(self.package_folder, "bin", "pgpp")
        save(self, command, '#!/usr/bin/env python3\nimport pathlib\nimport sys\n'
             'root = pathlib.Path(__file__).resolve().parent.parent\n'
             'sys.path.insert(0, str(root / "lib" / "python3.12" / "site-packages"))\n'
             'from pglast.__main__ import main\nmain()\n')
        os.chmod(command, 0o755)

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("PGLAST_PACKAGE_ROOT", site)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
