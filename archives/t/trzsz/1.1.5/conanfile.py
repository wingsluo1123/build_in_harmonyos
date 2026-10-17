import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TrzszConan(ConanFile):
    name = "trzsz"
    version = "1.1.5"
    description = "Terminal file transfer with length and MD5 checks"
    license = "MIT"
    homepage = "https://github.com/trzsz/trzsz"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("python/3.12.9#d8eda770878152bea40b42db9f7024cd", run=True)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("This recipe is scoped to OHOS")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="trzsz-source-1.1.5.tar.gz", strip_root=True)
        # The three real PyPI sdists supply their original complete egg-info.
        # Core code and original test links come from the matching pinned commit.
        for name, source in self.conan_data["distributions"].items():
            get(self, **source, destination=os.path.join(self.source_folder, "sdists", name),
                strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        namespace = os.path.join(site, "trzsz")
        os.makedirs(namespace, exist_ok=True)
        for part, module in (("trzsz-libs", "libs"), ("trzsz-svr", "svr")):
            shutil.copytree(os.path.join(self.source_folder, part, "trzsz", module),
                            os.path.join(namespace, module),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(os.path.join(self.source_folder, "trzsz-libs", "trzsz", "__init__.py"),
                     os.path.join(namespace, "__init__.py"))
        shutil.copy2(os.path.join(self.source_folder, "trzsz", "__version__.py"),
                     os.path.join(namespace, "__version__.py"))
        for part in ("trzsz", "trzsz-libs", "trzsz-svr"):
            metadata = glob.glob(os.path.join(self.source_folder, "sdists", part, "*.egg-info"))
            if len(metadata) != 1:
                raise ConanInvalidConfiguration("Expected one upstream egg-info for " + part)
            shutil.copytree(metadata[0], os.path.join(site, os.path.basename(metadata[0])))
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for name, module in (("trz", "recv"), ("tsz", "send")):
            launcher = os.path.join(bindir, name)
            with open(launcher, "w", encoding="utf-8", newline="\n") as stream:
                stream.write("#!/usr/bin/env python3\nimport os\nimport sys\n"
                             "sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname("
                             "os.path.realpath(__file__))), 'lib', 'python3.12', 'site-packages'))\n"
                             "from trzsz.svr." + module + " import main\nmain()\n")
            os.chmod(launcher, 0o755)
        # Preserve original tests and their real directory symlinks for the two
        # upstream discover commands, using the same patched source as this package.
        source = os.path.join(self.package_folder, "share", "trzsz", "source")
        os.makedirs(os.path.dirname(source), exist_ok=True)
        shutil.copytree(self.source_folder, source, symlinks=True,
                        ignore=shutil.ignore_patterns("sdists", "__pycache__", "*.pyc"))
        licenses = os.path.join(self.package_folder, "licenses")
        os.makedirs(licenses, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "LICENSE.md"), os.path.join(licenses, "LICENSE.md"))

    def package_info(self):
        # This exact published interpreter requires a command-scoped PYTHONHOME.
        python_home = self.dependencies["python"].package_folder
        self.runenv_info.define_path("PYTHONHOME", python_home)
        self.runenv_info.define_path("TRZSZ_PYTHON_HOME", python_home)
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define("TRZSZ_PACKAGE_FOLDER", self.package_folder)
        self.runenv_info.define("TRZSZ_SOURCE_DIR", os.path.join(
            self.package_folder, "share", "trzsz", "source"))
