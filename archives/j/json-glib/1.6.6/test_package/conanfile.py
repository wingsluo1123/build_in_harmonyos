import os
import subprocess
from conan import ConanFile
from conan.tools.build import cross_building


class JsonGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        # transitive_headers=True so glib's headers are available to the test.
        self.requires(self.tested_reference_str, transitive_headers=True)

    def build(self):
        # Compile + link the consumer test against the public json-glib API
        # using the conan-generated pkg-config closure (json-glib-1.0 pulls in
        # gio-2.0/gobject-2.0/glib-2.0 + libintl/libffi/pcre2/zlib). This
        # verifies the header closure and the link graph in one step.
        cc = os.environ.get("CC", "clang")
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder
        cflags = subprocess.run(
            ["pkg-config", "--cflags", "json-glib-1.0"],
            capture_output=True, text=True, env=env).stdout.strip()
        libs = subprocess.run(
            ["pkg-config", "--libs", "json-glib-1.0"],
            capture_output=True, text=True, env=env).stdout.strip()
        self.run(f'{cc} test.c -o test_json_glib {cflags} {libs}')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile+link verified only")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_json_glib'", env="conanrun")
