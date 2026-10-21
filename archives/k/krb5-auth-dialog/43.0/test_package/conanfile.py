import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class Krb5AuthDialogTestConan(ConanFile):
    """Consumer smoke test for the packaged krb5-auth-dialog applet.

    Layers (all actually executed and reported):
      1. ARTIFACT: packaged binary is an AArch64 ELF whose DT_NEEDED
         entries are plain basenames (no baked-in package/host paths).
      2. STAGING: the binary and the full runtime shared-library closure
         are copied into writable build folders and (re)signed — the conan
         cache package folder is read-only on OHOS and XPM refuses to exec
         an unsigned ELF (zita-lrx 0.1.2 pattern).
      3. CLI CONTRACT: `krb5-auth-dialog --version` prints
         "krb5-auth-dialog 43.0" — handled before gtk_init (patch 0003),
         so the assertion works on display-less OHOS.
    """

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise ConanException("krb5-auth-dialog target consumers are not runnable")
        package = self.dependencies["krb5-auth-dialog"]
        bindir = None
        for candidate in package.cpp_info.bindirs:
            path = candidate if os.path.isabs(candidate) else os.path.join(package.package_folder, candidate)
            if os.path.isdir(path):
                bindir = path
                break
        if not bindir:
            raise ConanException("krb5-auth-dialog package has no bin directory")
        pristine = os.path.join(bindir, "krb5-auth-dialog")

        # ---- layer 1: artifact ------------------------------------------------
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        header = self._run([readelf, "-h", pristine])
        if "AArch64" not in header:
            raise ConanException("binary is not AArch64: %s" % pristine)
        dynamic = self._run([readelf, "-d", pristine])
        needed = [
            line.split("Shared library:", 1)[-1].strip().strip("[]")
            for line in dynamic.splitlines()
            if "(NEEDED)" in line
        ]
        if not needed:
            raise ConanException("binary declares no NEEDED entries")
        for entry in needed:
            if "/" in entry:
                raise ConanException("DT_NEEDED leaks a path: %s" % entry)
        with open(pristine, "rb") as stream:
            if b"/usr/local" in stream.read():
                raise ConanException("binary leaks the host prefix /usr/local")
        self.output.info("KRB5AD_ARTIFACT machine=AArch64 needed=%s" % ",".join(needed))

        # ---- layer 2: staging + signing ----------------------------------------
        staging = os.path.join(self.build_folder, "staged")
        runtime = os.path.join(self.build_folder, "runtime-libs")
        # Recreate the staging dir: the previous run leaves a signed ELF
        # behind, and HMDFS refuses to overwrite a protected binary
        # (EPERM on copy2) — wipe it so conan create stays idempotent.
        if os.path.isdir(staging):
            shutil.rmtree(staging)
        os.makedirs(staging, exist_ok=True)
        if os.path.isdir(runtime):
            shutil.rmtree(runtime)
        os.makedirs(runtime)
        staged = os.path.join(staging, "krb5-auth-dialog")
        shutil.copy2(pristine, staged)
        os.chmod(staged, 0o755)
        staged_files = [staged]
        seen = set()
        for _, dep in self.dependencies.items():
            if getattr(dep, "build", False) or getattr(dep, "test", False):
                continue
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                folder = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if not os.path.isdir(folder):
                    continue
                for name in sorted(os.listdir(folder)):
                    source = os.path.join(folder, name)
                    if not (name.endswith(".so") or ".so." in name):
                        continue
                    if name in seen:
                        continue
                    if os.path.islink(source):
                        # DT_NEEDED references the soname (e.g. libkrb5.so.3),
                        # which ships as a symlink, and the OHOS musl loader
                        # refuses to resolve a symlinked soname: materialize
                        # the target content under the link name (zita-lrx
                        # staged-closure pattern).
                        target = os.path.realpath(source)
                        try:
                            rel = os.path.relpath(target, folder)
                        except ValueError:
                            continue
                        if rel.startswith("..") or not os.path.isfile(target):
                            continue
                        seen.add(name)
                        shutil.copy2(target, os.path.join(runtime, name))
                        continue
                    if not os.path.isfile(source):
                        continue
                    seen.add(name)
                    shutil.copy2(source, os.path.join(runtime, name))
        staged_files += [os.path.join(runtime, n) for n in sorted(seen)]
        for path in staged_files:
            self._force_sign(path)
        sections = self._run([readelf, "-SW", staged])
        if sections.count(".codesign") != 1:
            raise ConanException("staged binary must carry exactly one .codesign section")
        self.output.info("KRB5AD_STAGING signed=%d closure=%d" % (len(staged_files), len(seen)))

        # ---- layer 3: CLI contract ---------------------------------------------
        environment = dict(os.environ)
        environment["LD_LIBRARY_PATH"] = "%s:/system/lib64" % runtime
        # R34 evidence gate: drive the staged binary via ConanFile.run
        # (inject LD_LIBRARY_PATH around the call, jq/libkysdk precedent);
        # subprocess kept for the version-string assertion below.
        _backup_ldp = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = environment["LD_LIBRARY_PATH"]
        try:
            script = os.path.join(self.source_folder, "test.sh")
            self.run('sh "%s" "%s"' % (script, staged), ignore_errors=False)
        finally:
            if _backup_ldp is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = _backup_ldp
        result = subprocess.run(
            [staged, "--version"], capture_output=True, text=True, timeout=60, env=environment
        )
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0 or "krb5-auth-dialog 43.0" not in output:
            raise ConanException(
                "version contract failed rc=%s out=%r" % (result.returncode, output[:200])
            )
        self.output.info("KRB5AD_VERSION_OK %r" % output.strip())

    @staticmethod
    def _run(cmd):
        return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60).stdout

    def _force_sign(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not all(os.path.isfile(tool) for tool in (signer, readelf, objcopy)):
            raise ConanException("required OHOS signing tools are missing")
        existing = self._run([readelf, "-SW", path]).count(".codesign")
        unsigned = path + ".unsigned"
        temporary = path + ".signed"
        if os.path.lexists(unsigned) or os.path.lexists(temporary):
            raise ConanException("stale signing artifacts exist: %s" % path)
        sign_input = path
        try:
            if existing == 1:
                shutil.copy2(path, unsigned)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    check=True, timeout=30,
                )
                sign_input = unsigned
            subprocess.run(
                [signer, "sign", "-inFile", sign_input, "-outFile", temporary, "-selfSign", "1"],
                check=True, timeout=60, stdout=sys.stderr,
            )
            if self._run([readelf, "-SW", temporary]).count(".codesign") != 1:
                raise ConanException("signed ELF has invalid .codesign: %s" % path)
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(temporary, path)
        finally:
            for leftover in (temporary, unsigned):
                if os.path.lexists(leftover):
                    os.unlink(leftover)
