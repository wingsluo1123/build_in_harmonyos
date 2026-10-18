#!/usr/bin/env python3
"""Conan test_package for GNU Mailutils 3.20 (HarmonyOS PC).

The package is tested as a library consumer, a HarmonyOS target, and a real
mail client. The E2E case creates an mbox and reads its message through the
packaged `mail` executable.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MailutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _cache_library_dirs(self, package):
        """Library directories in this create's Conan cache.

        VirtualRunEnv omits libgnutls.so.30 even though the packaged
        libmailutils needs it. The cache that produced this package has the
        shared-library closure.
        """
        # package is <conan_home>/p/b/<id>/p or <conan_home>/p/<id>/p
        root = package
        for _ in range(3):
            root = os.path.dirname(root)
        found = []
        if not os.path.isdir(root):
            return found
        names = os.listdir(root)
        for name in names:
            candidate = os.path.join(root, name, "p", "lib")
            if os.path.isdir(candidate):
                found.append(candidate)
        build_root = os.path.join(root, "b")
        if os.path.isdir(build_root):
            for name in os.listdir(build_root):
                candidate = os.path.join(build_root, name, "p", "lib")
                if os.path.isdir(candidate):
                    found.append(candidate)
        return found

    def _merge_shared_library_path(self, package):
        extra = self._cache_library_dirs(package)
        if not extra:
            return
        prefix = ":".join(extra)
        generators = os.path.join(self.build_folder, "generators")
        if not os.path.isdir(generators):
            return
        for name in os.listdir(generators):
            if not (name.startswith("conanrunenv-") and name.endswith(".sh")):
                continue
            full = os.path.join(generators, name)
            with open(full, encoding="utf-8", errors="replace") as handle:
                lines = handle.read().split("\n")
            updated = []
            for line in lines:
                if line.startswith("export LD_LIBRARY_PATH="):
                    current = line.split("=", 1)[1].strip().strip('"')
                    suffix = current[current.index("${"):] if "${" in current else ""
                    existing = current.split("${", 1)[0].rstrip(":")
                    merged = prefix if not existing else prefix + ":" + existing
                    line = 'export LD_LIBRARY_PATH="%s%s"' % (merged, suffix)
                updated.append(line)
            with open(full, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("\n".join(updated))

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        self._merge_shared_library_path(package)
        cmake = CMake(self)
        cmake.test()
        here = os.path.dirname(os.path.abspath(__file__))
        for script_name in ("test_ohos_mailutils.sh", "test_mail_flow.sh"):
            script = os.path.join(here, script_name)
            self.run('sh "%s" "%s"' % (script, package), env="conanrun")
