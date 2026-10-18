#!/usr/bin/env python3
"""Conan recipe for synadm 0.49.2 - the Matrix Synapse admin CLI.

synadm is pure Python (setuptools; 15 .py files / ~4.7k lines, no compiled
extension, no build step beyond laying files down). Upstream ships no test
suite at all, so this recipe stages the tree itself instead of running
`setup.py install`: that keeps the package free of a setuptools/compiler
round-trip and makes the installed layout explicit.

Installed layout:
  bin/synadm                                   console entry point
  lib/pythonX.Y/site-packages/synadm/          the upstream package
  lib/pythonX.Y/site-packages/dns/             vendored, see conandata.yml
  lib/pythonX.Y/site-packages/click_option_group/
  lib/pythonX.Y/site-packages/requests_unixsocket/
  lib/pythonX.Y/site-packages/*.dist-info/     metadata for importlib.metadata
  licenses/                                    GPL-3.0-or-later + vendored

A dist-info tree is written for synadm and for each vendored dependency, not
just for show: synadm/api.py builds its User-Agent from
`importlib.metadata.version("synadm")` and `click.version_option()` (the
`synadm --version` flag) resolves the same metadata. Without it the packaged
CLI silently reports no version, and a consumer cannot tell an installed
synadm from an unbundled source checkout.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# conandata.yml keys carrying the vendored runtime dependencies. The
# rationale, the registry probe evidence and the licences are documented in
# conandata.yml next to the pinned URLs.
_VENDORED_KEYS = (
    "vendored_dnspython",
    "vendored_click_option_group",
    "vendored_requests_unixsocket",
)


class SynadmConan(ConanFile):
    name = "synadm"
    version = "0.49.2"
    description = (
        "Command line admin tool for Synapse (Matrix reference homeserver)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://codeberg.org/synadm/synadm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: the platform enum must be tested with `in`, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"synadm is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Exactly the runtime set synadm 0.49.2 declares in setup.py
        # install_requires, minus dnspython / click-option-group /
        # requests-unixsocket, which the OHOS registry does not carry and are
        # therefore vendored (see conandata.yml).
        #
        # run=True: without it a plain requires lands under "Skipped
        # binaries" and the dependency runenv never reaches the consumer of
        # this application (measured in the pytest/9.1.1 and interrogate/1.7.0
        # recipes).
        self.requires("click/8.4.2", run=True)
        self.requires("requests/2.22.0", run=True)
        self.requires("tabulate/0.10.0", run=True)
        self.requires("pyyaml/6.0.2", run=True)
        # The import closure of requests itself. requests/2.22.0 requires
        # certifi/chardet/idna/urllib3 without run=True, so from a consumer of
        # this package they are pruned as "Skipped binaries" and are not
        # visible to package_info() either; requests/2.22.0 only publishes its
        # own site-packages, so `import requests` then died with
        # "No module named 'chardet'" (measured here in conan create's
        # test_package run). Declaring them as direct requires of this
        # application is what makes their import paths publishable - they are
        # genuinely imported at runtime, not decoration.
        self.requires("certifi/2026.7.22", run=True)
        self.requires("chardet/5.2.0", run=True)
        self.requires("idna/3.18", run=True)
        self.requires("urllib3/2.7.0", run=True)

    @staticmethod
    def _site_relpath():
        """site-packages path relative to a prefix, for this interpreter."""
        return (
            "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )

    @staticmethod
    def _write_dist_info(site, dist, version, licence, top_level,
                         console_script=None):
        """Emit a minimal .dist-info so importlib.metadata can see `dist`.

        The directory name is normalized (PEP 427: dashes become underscores)
        while METADATA keeps the real distribution name - importlib.metadata
        only finds the distribution through the normalized directory name
        (measured: "click-option-group-0.5.9.dist-info" was invisible to
        version("click-option-group"), "click_option_group-..." was found).
        """
        info = os.path.join(
            site, f"{dist.replace('-', '_')}-{version}.dist-info")
        os.makedirs(info, exist_ok=True)
        with open(os.path.join(info, "METADATA"), "w",
                  encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                f"Name: {dist}\n"
                f"Version: {version}\n"
                f"License: {licence}\n"
            )
        with open(os.path.join(info, "top_level.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write(f"{top_level}\n")
        if console_script:
            with open(os.path.join(info, "entry_points.txt"), "w",
                      encoding="utf-8") as handle:
                handle.write(f"[console_scripts]\n{console_script}\n")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _vendored_src_dir(self, root, package):
        """Find an importable package directory under an extracted sdist.

        The three vendored projects do not agree on a layout (dnspython and
        requests-unixsocket are flat, click-option-group uses src/), and the
        sdist root directory name is version dependent, so the tree is
        searched instead of the path being guessed.
        """
        for dirpath, dirnames, _files in os.walk(root):
            if package in dirnames:
                candidate = os.path.join(dirpath, package)
                if os.path.isfile(os.path.join(candidate, "__init__.py")):
                    return candidate
            if dirpath == root:
                dirnames[:] = [
                    d for d in dirnames
                    if not d.endswith((".egg-info", ".dist-info"))
                ]
        raise ConanException(
            f"vendored package '{package}' not found under {root}"
        )

    def _vendor(self, site, licenses):
        """Lay the three registry-missing dependencies into the staging site.

        Each sdist is downloaded from the official PyPI with a pinned SHA256,
        its importable package tree is copied into the staging site-packages,
        a dist-info is emitted for discovery, and its licence text is
        collected next to synadm's own.
        """
        for key in _VENDORED_KEYS:
            entry = self.conan_data[key]
            root = os.path.join(
                self.build_folder, f"vendor-{entry['package']}")
            if os.path.isdir(root):
                shutil.rmtree(root)
            os.makedirs(root, exist_ok=True)
            get(
                self,
                entry["url"],
                sha256=entry["sha256"],
                filename=os.path.join(self.build_folder,
                                      os.path.basename(entry["url"])),
                destination=root,
                strip_root=True,
            )

            src = self._vendored_src_dir(root, entry["package"])
            shutil.copytree(
                src, os.path.join(site, entry["package"]),
                # requests-unixsocket ships testutils.py (imports waitress and
                # requests_mock, neither of which is a runtime requirement) and
                # a tests/ suite; both are import-time landmines in a runtime
                # package and the suite hardcodes /tmp paths, which HarmonyOS
                # mounts read-only.
                ignore=shutil.ignore_patterns(
                    "__pycache__", "tests", "test", "testutils.py",
                    "*.egg-info", "*.dist-info"),
            )
            self._write_dist_info(
                site,
                entry.get("dist", entry["package"]),
                entry["version"], entry["licence"], entry["package"],
            )
            licence_file = next(
                (
                    os.path.join(root, name)
                    for name in ("LICENSE", "LICENSE.txt", "COPYING",
                                 "COPYING.txt")
                    if os.path.isfile(os.path.join(root, name))
                ),
                None,
            )
            if licence_file:
                shutil.copy(
                    licence_file,
                    os.path.join(
                        licenses, f"LICENSE.{entry['dist']}-{entry['version']}"),
                )
            self.output.info(
                f"vendored {entry['package']} {entry['version']} "
                f"({entry['licence']})"
            )

    def _stage(self):
        """Lay the module, the vendored deps and the entry point out."""
        staging = os.path.join(self.build_folder, "staging")
        site = os.path.join(staging, *self._site_relpath())
        bin_dir = os.path.join(staging, "bin")
        licenses = os.path.join(staging, "licenses")
        for path in (site, bin_dir, licenses):
            os.makedirs(path, exist_ok=True)

        module = os.path.join(self.source_folder, "synadm")
        if not os.path.isdir(module):
            raise ConanException(
                f"synadm source package missing: {module}")
        shutil.copytree(
            module, os.path.join(site, "synadm"),
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        # Upstream console_scripts entry point (setup.py:
        # "synadm = synadm.cli:root"); the dist-info mirrors it for
        # entry-point aware tooling, the wrapper for a plain PATH lookup.
        self._write_dist_info(
            site, "synadm", self.version, "GPL-3.0-or-later", "synadm",
            console_script="synadm = synadm.cli:root\n",
        )
        path = os.path.join(bin_dir, "synadm")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/usr/bin/env python3\n"
                '"""Console entry point for synadm."""\n'
                "import sys\n"
                "from synadm.cli import root\n"
                "\n"
                'if __name__ == "__main__":\n'
                "    sys.exit(root())\n"
            )
        os.chmod(path, 0o755)

        self._vendor(site, licenses)
        return site, bin_dir, staging

    def build(self):
        site, _bin, _staging = self._stage()
        # No compiled code: the only meaningful build-time check is that the
        # staged tree (upstream module + vendored deps) really is valid
        # Python for the interpreter it will run under. __pycache__ is kept
        # out of the staged tree so it is not packaged.
        pycache = os.path.join(self.build_folder, "pycache")
        self.run(
            f'PYTHONPYCACHEPREFIX="{pycache}" '
            f'{sys.executable} -m compileall -q "{site}"'
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        if not os.path.isdir(staging):
            raise ConanException("synadm staging directory is missing")
        copy(self, "*", src=staging, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        for name in ("README.md", "PKG-INFO"):
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc",
                                  "synadm"), keep_path=False)

    def package_id(self):
        self.info.clear()

    @staticmethod
    def _find_site_packages(package_folder):
        """Locate a dependency's importable root, or None if it has none.

        Registry Python packages are published in both shapes - flat (the
        package folder itself holds the modules) and under
        lib/pythonX.Y/site-packages - so the layout is discovered rather than
        assumed. A C/C++ dependency (nothing here, but a future requests
        extra could pull one in) has no importable root and must not be
        injected into PYTHONPATH.
        """
        if not os.path.isdir(package_folder):
            return None
        if os.path.isdir(os.path.join(package_folder, "lib")):
            for dirpath, dirnames, _files in os.walk(package_folder):
                if "site-packages" in dirnames:
                    return os.path.join(dirpath, "site-packages")
        entries = os.listdir(package_folder)
        has_module = any(
            name.endswith(".py") for name in entries
        ) or any(
            os.path.isfile(os.path.join(package_folder, entry, "__init__.py"))
            for entry in entries
            if os.path.isdir(os.path.join(package_folder, entry))
        )
        return package_folder if has_module else None

    def package_info(self):
        site = os.path.join(self.package_folder, *self._site_relpath())
        bin_dir = os.path.join(self.package_folder, "bin")

        # Re-export the runtime dependencies' import paths. Not every
        # registry Python recipe publishes its own site-packages through the
        # Conan env objects (same failure mode measured in interrogate/1.7.0),
        # and it is not only the direct requires that are affected: the
        # registry requests/2.22.0 recipe does not publish chardet/idna/
        # urllib3/certifi either, so `import requests` died with
        # "No module named 'chardet'" until the whole host closure was walked
        # instead of just the four direct requires.
        dep_sites = []
        for dep in self.dependencies.host.values():
            folder = dep.package_folder
            if not folder or os.path.realpath(folder) == \
                    os.path.realpath(self.package_folder):
                continue
            dep_site = self._find_site_packages(folder)
            if not dep_site:
                continue
            dep_sites.append((str(dep.ref.name), dep_site))

        # PREPENDED, never appended: a host interpreter may carry its own
        # PYTHONPATH with a different copy of these modules, and appending
        # lets that copy win. Conan composes prepends stack-like (the last
        # call lands frontmost), so the dependencies go in first and this
        # package's own site last.
        for env in (self.buildenv_info, self.runenv_info):
            for _name, dep_site in reversed(dep_sites):
                env.prepend_path("PYTHONPATH", dep_site)
            env.prepend_path("PYTHONPATH", site)
            env.prepend_path("PATH", bin_dir)

        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.output.info(
            f"synadm {self.version} installed: {bin_dir}/synadm; "
            f"vendored dns/click_option_group/requests_unixsocket; "
            f"published {len(dep_sites)} dependency import path(s): "
            + ", ".join(name for name, _ in dep_sites)
        )
