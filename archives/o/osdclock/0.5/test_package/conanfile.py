#!/usr/bin/env python3
"""Conan test_package — osdclock 0.5.

osdclock is a command line tool, so the test really executes the installed
binary (R34) through test_osdclock.sh: the usage paths plus the no-X-display
initialisation failure path of libxosd 2.2.14, and a readelf check that the
executable's DT_NEEDED records libxosd.so.2.  See test_package/MANIFEST.yml
for the per-case rationale and the upstream test audit (osdclock 0.5 has no
automated test suite: its Makefile defines only all/install/clean/tar).

HMDFS: the dependency packages ship `libX.so -> libX.so.6 -> libX.so.6.4.0`
symlink chains whose symlink entries are unreadable on the OHOS cache
filesystem, so the runtime loader cannot resolve the recorded sonames from the
dependency libdirs.  generate() materialises real copies of every needed
shared object (under all soname aliases) into <build>/realdep_libs and the
test script prepends that directory to LD_LIBRARY_PATH — the same workaround
used by xgamma/libxosd (pitfall #29/#36 in the adaptation notes).
"""
import os
import shutil

from conan import ConanFile


class OsdclockTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _WANTED_SO_STEMS = (
        "libxosd.so", "libX11.so", "libXext.so", "libXinerama.so",
        "libxcb.so", "libXau.so", "libXdmcp.so",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _so_aliases(name):
        """libX11.so.6.4.0 -> libX11.so.6.4.0, libX11.so.6, libX11.so."""
        if ".so" not in name:
            return [name]
        idx = name.find(".so")
        stem = name[:idx + 3]
        rest = name[idx + 3:]
        aliases = [name, stem]
        if rest.startswith("."):
            major = rest[1:].split(".")[0]
            if major:
                aliases.insert(1, f"{stem}.{major}")
        return aliases

    def generate(self):
        mirror = os.path.join(self.build_folder, "realdep_libs")
        os.makedirs(mirror, exist_ok=True)
        done = set()
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isdir(libdir):
                    continue
                for entry in sorted(os.listdir(libdir)):
                    if ".so" not in entry:
                        continue
                    aliases = self._so_aliases(entry)
                    if aliases[-1] not in self._WANTED_SO_STEMS:
                        continue
                    src = os.path.join(libdir, entry)
                    try:
                        with open(src, "rb") as handle:
                            if handle.read(4) != b"\x7fELF":
                                continue
                    except OSError:
                        continue          # unreadable symlink entry
                    for alias in aliases:
                        if alias in done:
                            continue
                        try:
                            shutil.copyfile(src, os.path.join(mirror, alias))
                            done.add(alias)
                        except OSError:
                            pass
        self.output.info(
            f"HMDFS: materialised {len(done)} runtime shared objects into "
            f"{mirror}")
        self._real_lib_dir = mirror

    def test(self):
        dep = self.dependencies["osdclock"]
        binary = os.path.join(dep.package_folder, "bin", "osd_clock")
        shell = (os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
                 or shutil.which("sh") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_osdclock.sh")
        real_libs = getattr(self, "_real_lib_dir", "")
        self.run(f'"{shell}" "{script}" "{binary}" "{real_libs}"',
                 env="conanrun")
