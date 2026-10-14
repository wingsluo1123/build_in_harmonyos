#!/usr/bin/env python3
"""Consumer smoke test for the japa 0.9.4 OHOS package.

japa is an X11 GUI tool, so on the headless OHOS device the packaged binary
cannot be driven to a "GUI rendered" pass.  The test is layered exactly like
the jaaa 0.9.2 one:

  Layer 1 (artifact)  : pristine packaged ELF must be AArch64, declare only
                        bare-soname DT_NEEDED entries and leak no host prefix.
  Layer 2 (codesign)  : the exec copy must carry exactly one .codesign section.
  Layer 3 (runtime)   : test_japa.sh proves the loader resolves the whole
                        shared-library closure (`-h` banner), that a bare run
                        fails at the X display step (not in the loader), and
                        honestly SKIPs the JACK/ALSA/GUI capability cases.
"""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class JapaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_japa.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            raise ConanException("japa target consumers are not runnable")
        pkg_bin = os.path.join(self._package_bin_dir(), "japa")
        runtime_root = str(Path(self.build_folder, "runtime-libs"))
        staged_dir = str(Path(self.build_folder, "staged-bin"))
        work_dir = str(Path(self.build_folder, "smoke-work"))
        Path(staged_dir).mkdir(parents=True, exist_ok=True)
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        self.output.info("JAPA_TEST_RUNTIME_PATH=%s" % runtime_root)
        # Layer 1 is asserted against the pristine packaged artifact.
        self._check_artifact_layer(pkg_bin)
        # Layers 2 and 3 need a writable, signed copy: the Conan cache package
        # folder is read-only on OHOS (chmod there raises EACCES, E046/HMDFS),
        # and XPM refuses to exec an unsigned ELF, so the binary is staged into
        # the test build folder and signed there -- exactly the closure
        # treatment the packaged .so files get below.
        staged = os.path.join(staged_dir, "japa")
        if os.path.lexists(staged):
            os.unlink(staged)
        shutil.copy2(pkg_bin, staged)
        os.chmod(staged, (os.stat(staged).st_mode & 0o777) | 0o755)
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_runtime(runtime_root)
            self._sign_ohos_elf(staged, force=True)
            self._check_codesign_layer(staged)
        script = os.path.join(self.source_folder, "test_japa.sh")
        os.chmod(script, (os.stat(script).st_mode & 0o777) | 0o755)
        if str(self.settings.os) == "OHOS":
            self.run(
                'LD_LIBRARY_PATH="%s" "%s" "%s" "%s"' % (runtime_root, script, staged_dir, work_dir),
                env="conanrun",
            )
        else:
            self.run('"%s" "%s" "%s"' % (script, staged_dir, work_dir), env="conanrun")

    # -- artifact layer ----------------------------------------------------

    def _check_artifact_layer(self, binary):
        readelf = self._tool("llvm-readelf")
        header = self._readelf(readelf, ["-h", binary])
        machine = ""
        for line in header.splitlines():
            if line.strip().startswith("Machine:"):
                # readelf pads the value column, so compare on the token.
                machine = line.split(":", 1)[1].strip()
        if machine != "AArch64":
            raise ConanException(
                "japa must be an AArch64 ELF, readelf reports Machine=%r" % machine
            )
        self.output.info("JAPA_ARTIFACT_PASS machine=AArch64")

        dynamic = self._readelf(readelf, ["-d", binary])
        needed = []
        for line in dynamic.splitlines():
            if "(NEEDED)" in line:
                needed.append(line.split("[", 1)[1].split("]", 1)[0])
        if not needed:
            raise ConanException("japa declares no NEEDED shared libraries")
        for entry in needed:
            if "/" in entry:
                raise ConanException("DT_NEEDED leaks an absolute path: %s" % entry)
        self.output.info("JAPA_ARTIFACT_PASS needed=%s" % ",".join(needed))

        # No host installation prefix may survive in the produced binary.
        with open(binary, "rb") as stream:
            blob = stream.read()
        if b"/usr/local" in blob:
            raise ConanException("japa binary leaks the host prefix /usr/local")
        self.output.info("JAPA_ARTIFACT_PASS host_prefix_leak=none")

    def _check_codesign_layer(self, staged):
        """The copy we actually exec must carry exactly one .codesign section.

        Zero means XPM will refuse it (exec fails with an unrelated
        Permission denied, which would be misread as a missing library); more
        than one means a botched re-sign.
        """
        readelf = self._tool("llvm-readelf")
        sections = self._readelf(readelf, ["-SW", staged])
        count = sections.count(".codesign")
        if count != 1:
            raise ConanException(
                "staged japa must carry exactly one .codesign section, found %d" % count
            )
        self.output.info("JAPA_ARTIFACT_PASS codesign_sections=1")

    def _tool(self, name):
        found = shutil.which(name) or "/data/service/hnp/bin/%s" % name
        if not os.path.isfile(found):
            raise ConanException("required OHOS tool is missing: %s" % name)
        return found

    @staticmethod
    def _readelf(readelf, args):
        try:
            return subprocess.run(
                [readelf] + args,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ConanException("readelf %r failed: %s" % (args, error)) from error

    # -- package layout ----------------------------------------------------

    def _package_bin_dir(self):
        package = self.dependencies["japa"]
        for bindir in package.cpp_info.bindirs:
            path = Path(bindir)
            if not path.is_absolute():
                path = Path(package.package_folder, bindir)
            if path.is_dir():
                return str(path)
        raise ConanException("japa package has no bin directory")

    # -- OHOS runtime closure ----------------------------------------------

    def _prepare_ohos_runtime(self, runtime_root):
        root = Path(runtime_root)
        # A previous interrupted run may have left the staging directory
        # behind; recreate it cleanly so conan create is idempotent.
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=False, exist_ok=False)
        copied = 0
        for _, dependency in self.dependencies.items():
            if getattr(dependency, "build", False) or getattr(dependency, "test", False):
                continue
            if not dependency.package_folder:
                continue
            package_root = Path(dependency.package_folder).resolve(strict=True)
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for entry in sorted(source_dir.iterdir(), key=lambda item: item.name):
                    if not (entry.name.endswith(".so") or ".so." in entry.name):
                        continue
                    source = entry.resolve(strict=True)
                    if not source.is_file():
                        raise ConanException(
                            "runtime shared library is not regular: %s" % entry
                        )
                    try:
                        source.relative_to(package_root)
                    except ValueError as error:
                        raise ConanException(
                            "runtime library escapes its package: %s" % entry
                        ) from error
                    destination = root / entry.name
                    if destination.exists():
                        if not self._same_bytes(destination, source):
                            raise ConanException(
                                "runtime library basename collision: %s" % entry.name
                            )
                        continue
                    shutil.copy2(source, destination)
                    shutil.copymode(source, destination)
                    copied += 1
        if copied == 0:
            raise ConanException("OHOS runtime library closure is empty")
        for library in sorted(root.iterdir(), key=lambda item: item.name):
            self._sign_ohos_elf(str(library), force=True)
        return root

    @staticmethod
    def _same_bytes(left, right):
        if left.stat().st_size != right.stat().st_size:
            return False
        with left.open("rb") as left_stream, right.open("rb") as right_stream:
            while True:
                left_block = left_stream.read(1024 * 1024)
                right_block = right_stream.read(1024 * 1024)
                if left_block != right_block:
                    return False
                if not left_block:
                    return True

    def _sign_ohos_elf(self, path, force=False):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        existing = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.count(".codesign")
        if existing == 1 and not force:
            os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o755)
        elif existing not in (0, 1):
            raise ConanException("ELF has an invalid .codesign count: %s" % path)
        else:
            objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
            if existing == 1 and not os.path.isfile(objcopy):
                raise ConanException("required OHOS objcopy is missing")
            unsigned = "%s.unsigned" % path
            temporary = "%s.signed" % path
            for candidate in (unsigned, temporary):
                if os.path.lexists(candidate):
                    raise ConanException("stale signing output exists: %s" % candidate)
            sign_input = path
            try:
                if existing == 1:
                    shutil.copy2(path, unsigned)
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        check=True,
                        timeout=30,
                    )
                    sign_input = unsigned
                subprocess.run(
                    [signer, "sign", "-inFile", sign_input, "-outFile", temporary,
                     "-selfSign", "1"],
                    check=True,
                    stdout=sys.stderr,
                    timeout=60,
                )
                sections = subprocess.run(
                    [readelf, "-SW", temporary],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout
                if sections.count(".codesign") != 1:
                    raise ConanException("signed ELF has invalid .codesign: %s" % path)
                os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
                os.replace(temporary, path)
            finally:
                for candidate in (temporary, unsigned):
                    if os.path.lexists(candidate):
                        os.unlink(candidate)
        final_sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if (
            final_sections.count(".codesign") != 1
            or not stat.S_IMODE(os.stat(path).st_mode) & stat.S_IXUSR
        ):
            raise ConanException("final signed ELF validation failed: %s" % path)
