#!/usr/bin/env python3
"""Conan recipe for tubeup 2026.5.8 — VOD service to Archive.org uploader.

tubeup is a pure-Python CLI (setuptools build backend). It downloads videos
with yt-dlp and uploads them to archive.org through the internetarchive
library. No C/C++ compilation is involved, so the package follows the
python-require template: copy the ``tubeup`` package into
``lib/python3.12/site-packages`` and generate the ``bin/tubeup`` entry point.

Dependency policy (W0/R36, awscli precedent): only dependencies that are
actually published on the ohpcd registry are declared as Conan requires.
``internetarchive``, ``docopt`` and ``tqdm`` are published; ``yt-dlp`` is not
published yet, so it stays an optional runtime dependency guarded by
patches/0001-guard-optional-yt-dlp.patch. ``internetarchive`` imports
``jsonpatch`` (and its ``jsonpointer`` dependency) at import time but neither
has a Conan package on ohpcd, so the two single-module pure-Python packages
are installed into the staging area shipped with this package. All gaps are
documented in README.md and the archive notes.md instead of being silently
dropped.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)

# internetarchive 5.10.1 has no Conan package for these two, and neither is
# available through cmd-pkgs; pinned so the packaged runtime is reproducible.
JSONPATCH_PINS = "jsonpatch==1.35 jsonpointer==3.2.1"


class TubeupConan(ConanFile):
    name = "tubeup"
    version = "2026.5.8"
    package_type = "python-require"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/bibanon/tubeup"
    description = "VOD service to Archive.org uploader (pure Python CLI)."
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published on ohpcd. yt-dlp is intentionally NOT declared: it is not
        # published yet, so declaring it would violate R36 (see module docstring).
        self.requires("internetarchive/5.10.1")
        self.requires("docopt/0.6.2")
        self.requires("tqdm/4.70.1")

    def configure(self):
        self.settings.rm_safe("os.version")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        if not os.path.isdir(os.path.join(self.source_folder, "tubeup")):
            raise ConanException("tubeup source package is missing")

        # internetarchive 5.10.1 imports jsonpatch/jsonpointer at import time,
        # but the published internetarchive package neither bundles them nor
        # declares them, and neither has a Conan package on ohpcd. Stage them so
        # the packaged tubeup is importable on a clean consumer.
        stage = os.path.join(self.build_folder, "py-stage")
        shutil.rmtree(stage, ignore_errors=True)
        os.makedirs(stage, exist_ok=True)
        self.run(
            f"'{sys.executable}' -m pip install --no-compile "
            f"--no-warn-script-location --target='{stage}' {JSONPATCH_PINS}"
        )
        if not os.path.isfile(os.path.join(stage, "jsonpatch.py")):
            raise ConanException(f"jsonpatch staging failed: {stage}")

    def package(self):
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        os.makedirs(site, exist_ok=True)

        src_pkg = os.path.join(self.source_folder, "tubeup")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"tubeup package missing: {src_pkg}")
        shutil.copytree(
            src_pkg,
            os.path.join(site, "tubeup"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

        stage = os.path.join(self.build_folder, "py-stage")
        if not os.path.isdir(stage):
            raise ConanException(f"staging missing: {stage}")
        for entry in os.listdir(stage):
            source = os.path.join(stage, entry)
            target = os.path.join(site, entry)
            if os.path.isdir(source):
                shutil.copytree(
                    source, target,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
            else:
                shutil.copy2(source, target)

        # Generate the console-script entry point (upstream
        # `[project.scripts] tubeup = "tubeup.__main__:main"`).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        site_rel = os.path.join("lib", pyver, "site-packages")
        script = (
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "_pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))\n"
            f'_sp = os.path.join(_pkg_root, "{site_rel}")\n'
            "if _sp not in sys.path:\n"
            "    sys.path.insert(0, _sp)\n"
            "from tubeup.__main__ import main\n"
            'if __name__ == "__main__":\n'
            "    main()\n"
        )
        script_path = os.path.join(bin_dir, "tubeup")
        with open(script_path, "w") as handle:
            handle.write(script)
        os.chmod(script_path, 0o755)

    def package_info(self):
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.runenv_info.append_path("PYTHONPATH", site)
