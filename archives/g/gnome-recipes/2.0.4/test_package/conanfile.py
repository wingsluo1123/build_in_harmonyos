#!/usr/bin/env python3
"""Consumer test for the packaged gnome-recipes application."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GnomeRecipesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # bin/gnome-recipes binds shared libarchive.so.13 at load time
        # (gnome-autoar is static; its archive-filter calls are relocated
        # into the main binary).  As a transitive-only requirement it would
        # be marked "Skipped" by the graph: no package_folder, no runenv
        # entry, and the loader would fall back to the reduced OHOS system
        # libarchive.so.13 ("archive_write_add_filter_gzip: symbol not
        # found").  Declare it explicitly (same version as the recipe, so
        # it dedups without conflict) -- see knowledge draft
        # E669-app-consumer-run-closure-skips-transitive-so-libs.
        self.requires("libarchive/3.8.7")

    def test(self):
        tested_name = self.tested_reference_str.split("/")[0]
        package = self.dependencies[tested_name].package_folder
        run_binary = "1" if can_run(self) else "0"
        shell = os.environ.get("CONFIG_SHELL", "bash")
        script = os.path.join(self.source_folder, "test_gnome_recipes.sh")
        # Enumerate dependency folders for the runtime library path.  Do not
        # read cpp_info here: componentized packages (libarchive) may carry
        # empty root libdirs while the .so files live in lib/ (E669).
        ld_dirs = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for sub in ("lib", "lib64"):
                _dir = os.path.join(dep.package_folder, sub)
                if os.path.isdir(_dir) and _dir not in ld_dirs:
                    ld_dirs.append(_dir)
        ld_arg = ":".join(ld_dirs)
        # The script checks installed resources in every profile and executes
        # GApplication's --help path only when the target is runnable.
        self.run(
            f'"{shell}" "{script}" "{package}" "{run_binary}" "{ld_arg}"',
            env="conanrun",
        )
