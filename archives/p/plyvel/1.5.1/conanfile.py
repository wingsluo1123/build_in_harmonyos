"""Native Conan build of plyvel's released Cython-generated C++ extension."""
import os
from pathlib import Path
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PlyvelConan(ConanFile):
    name = "plyvel"
    version = "1.5.1"
    description = "Python interface to the LevelDB ordered key-value database"
    license = "BSD-3-Clause"
    homepage = "https://github.com/wbolster/plyvel"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    no_copy_source = True

    def requirements(self):
        self.requires("python/3.12.9", run=True)
        self.requires("leveldb/1.23", run=True, options={"shared": True})

    def build_requirements(self):
        self.tool_requires("setuptools/84.0.0")
        self.tool_requires("pytest/9.1.1")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS") or cross_building(self):
            raise ConanInvalidConfiguration("plyvel requires a native Linux/OHOS Python build")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("This recipe validates the AArch64 CPython 3.12 ABI")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def _sign(self, extension):
        if self.settings.os != "OHOS":
            return
        signer = shutil.which("binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy")
        if not signer or not objcopy:
            raise ConanException("OHOS extension loading requires binary-sign-tool and llvm-objcopy")
        temporary = str(extension) + ".signing"
        shutil.copy2(extension, temporary)
        try:
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(f'"{signer}" sign -inFile "{temporary}" -outFile "{temporary}" -selfSign 1')
            os.chmod(temporary, 0o755)
            os.replace(temporary, extension)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def build(self):
        apply_conandata_patches(self)
        staging = Path(self.build_folder) / "staging"
        built = Path(self.build_folder) / "python-package"
        copy(self, "*", src=self.source_folder, dst=str(staging))
        python_dep = self.dependencies["python"]
        leveldb_dep = self.dependencies["leveldb"]
        python = os.path.join(python_dep.package_folder, "bin", "python3")
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        environment = Environment()
        environment.define("CC", compilers.get("c", "clang"))
        environment.define("CXX", compilers.get("cpp", "clang++"))
        environment.define("LDSHARED", f'{compilers.get("cpp", "clang++")} -shared')
        # New setuptools uses a separate command for C++ extensions.
        environment.define("LDCXXSHARED", f'{compilers.get("cpp", "clang++")} -shared')
        environment.define("AR", shutil.which("llvm-ar") or "ar")
        environment.define_path("PYTHONHOME", python_dep.package_folder)
        environment.define("PYTHONDONTWRITEBYTECODE", "1")
        environment.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        # LevelDB 1.23 is built without RTTI. The custom Comparator subclass
        # must not import typeinfo that its shared base library does not export.
        environment.append("CXXFLAGS", "-fno-rtti")
        environment.append("CXXFLAGS", "-O2 -DNDEBUG" if self.settings.build_type == "Release" else "-g")
        for include in leveldb_dep.cpp_info.includedirs:
            environment.append("CFLAGS", f'-I"{include}"')
            environment.append("CXXFLAGS", f'-I"{include}"')
        for libdir in leveldb_dep.cpp_info.libdirs + python_dep.cpp_info.libdirs:
            environment.append("LDFLAGS", f'-L"{libdir}"')
        # OHOS extension namespaces require an explicit interpreter dependency.
        environment.append("LDFLAGS", "-lpython3.12")
        with environment.vars(self).apply():
            # The official sdist contains Cython 3.0.8 output. No regeneration.
            self.run(f'"{python}" setup.py build --build-base "{self.build_folder}/output" '
                     f'--build-lib "{built}"', cwd=str(staging), env=["conanbuild", "conanrun"])
            self.run(f'"{python}" setup.py egg_info --egg-base "{built}"',
                     cwd=str(staging), env=["conanbuild", "conanrun"])
            for extension in built.rglob("*.so"):
                self._sign(extension)
        environment.prepend_path("PYTHONPATH", str(built))
        with environment.vars(self).apply():
            self.run(f'"{python}" -m pytest -c "{staging}/setup.cfg" '
                     f'"{staging}/test" --import-mode=importlib '
                     f'--junitxml="{self.build_folder}/upstream-tests.xml"',
                     cwd=self.build_folder, env=["conanbuild", "conanrun"])

    def package(self):
        site = Path(self.package_folder) / "lib" / "python3.12" / "site-packages"
        copy(self, "*", src=os.path.join(self.build_folder, "python-package"),
             dst=str(site), excludes=("*.pyc", "__pycache__/*"))
        extensions = list((site / "plyvel").glob("_plyvel*.so"))
        if len(extensions) != 1:
            raise ConanException("Exactly one installed plyvel extension is required")
        self._sign(extensions[0])
        copy(self, "LICENSE.rst", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("PLYVEL_PACKAGE_ROOT", site)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
