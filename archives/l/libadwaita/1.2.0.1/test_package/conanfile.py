#!/usr/bin/env python3
"""Conan test_package — libadwaita 1.2.0.1.

Verifies the packaged libadwaita recipe is consumable: builds a minimal
Adwaita program against the package, links against libadwaita-1, and runs
it to confirm the package provides a usable pkg-config / cpp_info.
"""
import os
import shutil
import subprocess
import time
import uuid

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibadwaitaTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_gtk4_pc()
        # MesonToolchain doesn't write ar/ranlib from
        # tools.build:compiler_executables into the native file; meson then
        # probes bare llvm-ar which is NOT on PATH on OHOS (clang toolchain in
        # /data/service/hnp/bin) → configure aborts "Unknown linker(s)".
        # Pin the real tools by absolute path (same as the gtk4 recipe).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.generate()

    def _fix_gtk4_pc(self):
        """Repair the invalid public dependency emitted by gtk4 metadata."""
        pc_file = os.path.join(self.generators_folder, "gtk4.pc")
        if not os.path.isfile(pc_file):
            return
        with open(pc_file, encoding="utf-8") as handle:
            text = handle.read()
        fixed = text.replace(" none ", " graphene-gobject-1.0 ")
        if fixed == text:
            fixed = fixed.replace(" none\n", " graphene-gobject-1.0\n")
        if fixed != text:
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(fixed)
            self.output.info(
                "gtk4.pc: replaced invalid Requires token 'none' with "
                "graphene-gobject-1.0"
            )

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        from conan.tools.build import cross_building
        if cross_building(self):
            self.output.info("cross-building: skip test execution on build host")
            return
        if self.settings.os != "OHOS":
            Meson(self).test()
            return

        gtk = self.dependencies["gtk4"]
        glib = self.dependencies["glib"]
        broadwayd = os.path.join(gtk.package_folder, "bin", "gtk4-broadwayd")
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run(
            '{objcopy} --remove-section .codesign "{binary}" 2>/dev/null || true'.format(
                objcopy=objcopy, binary=broadwayd
            )
        )
        self.run(
            '{signer} sign -inFile "{binary}" -outFile "{binary}" -selfSign 1'.format(
                signer=signer, binary=broadwayd
            )
        )
        runtime_dir = os.path.join(
            os.environ.get("XDG_CACHE_HOME", "/data/storage/el2/base/cache"),
            "libadwaita-1.2.0.1-consumer",
        )
        os.makedirs(runtime_dir, exist_ok=True)
        socket_path = os.path.join(runtime_dir, "broadway1.socket")
        if os.path.exists(socket_path):
            os.unlink(socket_path)

        schema_source = os.path.join(gtk.package_folder, "share", "glib-2.0", "schemas")
        schema_dir = os.path.join(self.build_folder, "test-schemas")
        if os.path.isdir(schema_source):
            if not os.path.isdir(schema_dir):
                shutil.copytree(schema_source, schema_dir)
            schema_compiler = os.path.join(glib.package_folder, "bin", "glib-compile-schemas")
            glib_libdir = os.path.join(glib.package_folder, "lib")
            schema_ld_path = glib_libdir + os.pathsep + os.environ.get(
                "LD_LIBRARY_PATH", ""
            )
            self.run(
                'LD_LIBRARY_PATH="%s" "%s" "%s"'
                % (schema_ld_path, schema_compiler, schema_dir)
            )

        libdirs = []
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            libdir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(libdir):
                libdirs.append(libdir)
        environment = {
            "GDK_BACKEND": "broadway",
            "XDG_RUNTIME_DIR": runtime_dir,
            "GSETTINGS_BACKEND": "memory",
            "GSETTINGS_SCHEMA_DIR": schema_dir,
            "GTK_A11Y": "none",
            "DBUS_MACHINE_ID": uuid.uuid4().hex,
            "LD_LIBRARY_PATH": os.pathsep.join(libdirs),
        }
        fontconfig = self.dependencies.get("fontconfig")
        if fontconfig and fontconfig.package_folder:
            fonts_conf = os.path.join(
                fontconfig.package_folder, "etc", "fonts", "fonts.conf"
            )
            if os.path.isfile(fonts_conf):
                environment["FONTCONFIG_FILE"] = fonts_conf
        process = subprocess.Popen(
            [broadwayd], env=dict(os.environ, **environment),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        previous = {key: os.environ.get(key) for key in environment}
        try:
            started = time.time()
            while not os.path.exists(socket_path) and time.time() - started < 20:
                if process.poll() is not None:
                    raise ConanInvalidConfiguration("gtk4-broadwayd exited before creating its socket")
                time.sleep(0.25)
            if not os.path.exists(socket_path):
                raise ConanInvalidConfiguration("gtk4-broadwayd did not create its socket")
            os.environ.update(environment)
            self.run(
                'meson test -v -C "%s" --timeout-multiplier=16 --no-rebuild'
                % self.build_folder
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
