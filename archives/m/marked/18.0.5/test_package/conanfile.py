#!/usr/bin/env python3
"""Conan test_package for marked 18.0.5 — JavaScript import test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MarkedTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get the package folder of the marked dependency
            marked_root = self.dependencies["marked"].package_folder
            esm_path = os.path.join(marked_root, "lib", "node_modules", "marked", "lib", "marked.esm.js")
            pkg_json = os.path.join(marked_root, "lib", "node_modules", "marked", "package.json")

            # Test 1: ESM module import — parse markdown and verify HTML
            self.run(
                f'node --input-type=module -e "'
                f"import {{ marked }} from '{esm_path}'; "
                f"const html = marked.parse('# Hello World\\n\\nThis is **bold**.'); "
                f"if (!html.includes('<h1>Hello World</h1>')) process.exit(1); "
                f"if (!html.includes('<strong>bold</strong>')) process.exit(1); "
                f"console.log('marked ESM import test: PASS');"
                f'"',
                env="conanrun",
            )

            # Test 2: Version check via package.json
            self.run(
                f'node -e "'
                f"const pkg = require('{pkg_json}'); "
                f"if (pkg.version !== '18.0.5') process.exit(1); "
                f"console.log('marked version:', pkg.version);"
                f'"',
                env="conanrun",
            )
