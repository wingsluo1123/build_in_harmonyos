#!/usr/bin/env python3
"""test_package for libu2f-host 1.1.10 — consumer smoke test.

Compiles and links a small consumer program against libu2f-host (and its
transitive hidapi / json-c dependencies) and exercises the public read-only
API.  No physical U2F hardware is required.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class Libu2fHostTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("json-c/0.17")
        self.requires("hidapi/0.14.0")
        self.requires("libusb/1.0.27")

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def _check_package_layout(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        header = os.path.join(pkg, "include", "u2f-host", "u2f-host.h")
        if not os.path.exists(header):
            raise ConanException("missing libu2f-host header: " + header)
        if not (os.path.exists(os.path.join(pkg, "lib", "libu2f-host.so"))
                or os.path.exists(os.path.join(pkg, "lib", "libu2f-host.a"))):
            raise ConanException("missing libu2f-host library under " + pkg + "/lib")

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        cc = shutil.which(os.environ.get("CC", "clang")) or "clang"

        pkg = self.dependencies[self.tested_reference_str].package_folder
        jsonc = self.dependencies["json-c"].package_folder
        hidapi = self.dependencies["hidapi"].package_folder
        libusb = self.dependencies["libusb"].package_folder
        src = os.path.join(self.source_folder, "test_consumer.c")
        exe = os.path.join(self.build_folder, "test_consumer")
        flags = " ".join([
            f"-I{pkg}/include",
            f"-I{pkg}/include/u2f-host",
            f"-I{jsonc}/include",
            f"-I{jsonc}/include/json-c",
            f"-I{hidapi}/include/hidapi",
            f"-L{pkg}/lib",
            f"-L{jsonc}/lib",
            f"-L{hidapi}/lib",
            f"-L{libusb}/lib",
            "-Wl,--allow-shlib-undefined",
            "-lu2f-host -lhidapi-libusb -ljson-c -lusb-1.0",
        ])
        self.run(f"{cc} -o {exe} {src} {flags}")

        # --- rule4: compile the verbatim upstream test (tests/basic.c) ---
        # config.h shim: installed headers do not ship config.h; basic.c only
        # needs U2FH_VERSION_STRING from it.
        ver = str(self.dependencies[self.tested_reference_str].ref.version)
        shimdir = os.path.join(self.build_folder, "upstream_shim")
        os.makedirs(shimdir, exist_ok=True)
        with open(os.path.join(shimdir, "config.h"), "w") as f:
            f.write(f'#define U2FH_VERSION_STRING "{ver}"\n')
        # Test-env shim .so: constructor opts libusb out of device discovery
        # (headless CI has no accessible /dev/bus/usb; plain libusb_init()
        # fails there and basic.c would abort at u2fh_devs_init). Injected as
        # a DT_NEEDED library so the upstream test source stays verbatim.
        uinc = os.path.join(libusb, "include")
        self.run(f"{cc} -shared -fPIC -o {self.build_folder}/libu2f_test_shim.so "
                 f"{os.path.join(self.source_folder, 'u2f_test_shim.c')} "
                 f"-I{uinc} -L{libusb}/lib -lusb-1.0 -Wl,--allow-shlib-undefined")
        exe2 = os.path.join(self.build_folder, "upstream_basic")
        src2 = os.path.join(self.source_folder, "upstream_basic.c")
        # NOTE: $ORIGIN must reach the linker verbatim — a bare "$ORIGIN" in the
        # f-string is expanded by the shell to an empty string and the rpath
        # silently breaks (loader then fails on libu2f_test_shim.so).
        self.run(f"{cc} -o {exe2} {src2} -I{shimdir} -L{self.build_folder} {flags} "
                 f"-lu2f_test_shim -Wl,-rpath,\$ORIGIN")

    def test(self):
        self._check_package_layout()
        if cross_building(self):
            self.output.info("cross-building: link-only verification")
            return
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        exe = os.path.join(self.build_folder, "test_consumer")
        self.output.info("run consumer program (read-only library API)")
        self.run(f"{bash} -c '{exe}'", env="conanrun")

        # --- rule4: run the upstream test suite (tests/basic.c, verbatim) ---
        # With no U2F key present u2fh_devs_discover() returns
        # U2FH_NO_U2F_DEVICE, which basic.c accepts as a pass — the exact
        # behaviour of upstream's `make check` in CI.
        exe2 = os.path.join(self.build_folder, "upstream_basic")
        self.output.info("UPSTREAM_TEST basic (tests/basic.c): running")
        self.run(f"{bash} -c '{exe2}'", env="conanrun")
        self.output.info("UPSTREAM_TEST basic: PASS (1/1)")
