#!/usr/bin/env python3
"""Consumer test for dynamorio on OHOS PC.

Builds a standalone DynamoRIO application against the packaged library and, in
test(), executes it (and the packaged command line launcher) through
``self.run()`` so the engine is actually exercised on the host.
"""
import io
import os
import shutil
import struct
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

_OBJCOPY = ("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
_SIGNER = ("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
# The CI conan build environment does not carry /data/service/hnp/bin on PATH,
# so readelf has to be resolved by absolute path (same as the signing tools).
_READELF = ("readelf", "/data/service/hnp/bin/readelf", "/data/service/hnp/bin/llvm-readelf")


def _find(cands):
    for c in cands:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        else:
            w = shutil.which(c)
            if w:
                return w
    return None


def _codesign_record(path):
    readelf = _find(_READELF)
    if readelf is None:
        return None
    out = subprocess.run([readelf, "-SW", path], capture_output=True, text=True).stdout
    off = None
    for line in out.splitlines():
        if ".codesign" in line:
            parts = line.split()
            try:
                off = int(parts[parts.index(".codesign") + 3], 16)
            except (ValueError, IndexError):
                return None
    if off is None or off + 0x18 > os.path.getsize(path):
        return None
    with open(path, "rb") as fh:
        fh.seek(off + 0x10)
        return struct.unpack("<Q", fh.read(8))[0]


def ohos_resign(path):
    """Restore a valid OHOS .codesign block.

    Linking against libdynamorio_static.a makes lld's --code-sign pass emit a
    record that does not match the file, and OHOS then refuses to execute it.
    """
    rec = _codesign_record(path)
    if rec is None or rec == os.path.getsize(path):
        return
    objcopy, signer = _find(_OBJCOPY), _find(_SIGNER)
    if not objcopy or not signer:
        return
    tmp = tempfile.mkdtemp(prefix="ohos-resign-")
    try:
        n, s = os.path.join(tmp, "n.elf"), os.path.join(tmp, "s.elf")
        subprocess.run([objcopy, "--remove-section=.codesign", path, n], check=True)
        subprocess.run([signer, "sign", "-selfSign", "1", "-inFile", n, "-outFile", s],
                       check=True, capture_output=True, timeout=600)
        os.remove(path)
        shutil.copy2(s, path)
        os.chmod(path, 0o755)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        tc = CMakeToolchain(self)
        tc.cache_variables["DynamoRIO_DIR"] = os.path.join(pkg, "cmake")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # As in the recipe: on OHOS the system name has to be forced, otherwise
        # CMake derives "HarmonyOS" from uname, finds no platform module, leaves
        # UNIX undefined and DynamoRIO's headers take their Windows branch
        # (dr_app.h would expand DR_APP_API to __declspec(dllimport)).
        cli_args = []
        if self.settings.os == "OHOS":
            cli_args = ["-DCMAKE_SYSTEM_NAME=OHOS", "-DCMAKE_SYSTEM_PROCESSOR=aarch64"]
        cmake.configure(cli_args=cli_args)
        cmake.build()

    def test(self):
        # can_run() is False here because the OHOS profile sets
        # tools.build.cross_building:can_run=False, yet the build profile targets the
        # same OS/arch as the host (the OHOS toolchain runs natively on the OHOS PC),
        # so the produced binaries are runnable.  Only skip a genuine cross-build.
        if str(self.settings.arch) != str(self.settings_build.arch) or \
           str(self.settings.os) != str(self.settings_build.os):
            self.output.warning("cross-built for %s/%s: skipping execution"
                                % (self.settings.os, self.settings.arch))
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder

        # 1. The packaged launcher must be executable (this is what the
        #    .codesign repair in the recipe is for).  self.run() raises on a
        #    non-zero exit code, so the return code is checked implicitly.
        drrun = os.path.join(pkg, "bin64", "drrun")
        self.output.info("running packaged launcher: %s" % drrun)
        launcher_out = io.StringIO()
        self.run('"%s" -version < /dev/null' % drrun,
                 stdout=launcher_out, stderr=launcher_out, env="conanrun")
        launcher_log = launcher_out.getvalue()
        self.output.info("drrun output:\n%s" % launcher_log)
        assert "drrun version" in launcher_log, \
            "unexpected drrun output: %r" % launcher_log

        # 2. The DBI engine itself: execute the standalone client that build()
        #    linked against the packaged library.  cwd is the test_package build
        #    folder, where CMake placed the executable in bin/.
        exe = os.path.join(self.build_folder, "bin", "dr_standalone_smoke")
        assert os.path.exists(exe), "smoke executable not found at %s" % exe
        ohos_resign(exe)
        self.output.info("running packaged engine smoke: %s" % exe)
        engine_out = io.StringIO()
        self.run('"%s" < /dev/null' % exe,
                 stdout=engine_out, stderr=engine_out, env="conanrun")
        combined = engine_out.getvalue()
        self.output.info("dr_standalone_smoke output:\n%s" % combined)
        # Only markers produced outside the engine-active window are asserted: DR
        # currently drops application stdout written while it is in control.
        for marker in ("pre-DR init", "pre-DR start", "all done"):
            assert marker in combined, "missing marker %r in engine output" % marker
