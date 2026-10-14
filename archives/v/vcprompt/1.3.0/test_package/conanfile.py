#!/usr/bin/env python3
"""Consumer test for the packaged vcprompt 1.3.0 executable.

The test drives the *packaged* binary (no compiler needed) and asserts on real
behaviour:

1. `vcprompt -f %n:%b` inside a git working copy prints "vcprompt:<branch>".
2. the default format "[%n:%b] " prints the same branch information.
3. `vcprompt -F` lists the built-in VCS backends and, because this recipe is
   built with --with-sqlite3=no, does not advertise svn-1.7/svn-1.8.
4. a directory tree without any VCS metadata prints nothing at all.

The fake working copies use hand-written metadata (same technique as the
upstream tests/test-simple script), so the assertions do not depend on git,
hg, svn or fossil being installed on the machine.
"""
import os
import shlex
import shutil
import stat
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import load, save

FIXTURE_DIR = "fixture"
NESTED_DIR = "no-vc/nested"
BRANCH = "ohos-vcprompt-test"
VCS_NAME = "git"


class VcpromptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        binary = self._binary_path()
        if not os.path.exists(binary):
            raise ConanException(f"packaged vcprompt executable not found: {binary}")
        self._write_fixtures()
        self.output.info(f"packaged vcprompt: {binary}")

    def test(self):
        binary = self._binary_path()
        if not os.path.exists(binary):
            raise ConanException(f"packaged vcprompt executable not found: {binary}")

        fixture = os.path.join(self._workdir, FIXTURE_DIR)
        nested = os.path.join(self._workdir, NESTED_DIR)

        # 1. explicit format inside a git working copy
        #    %n is the VCS name (git), not the program name
        actual = self._run(binary, fixture, ["-f", "%n:%b"])
        expected = f"{VCS_NAME}:{BRANCH}"
        if actual != expected:
            raise ConanException(
                f"unexpected vcprompt output in git working copy: {actual!r} != {expected!r}"
            )
        self.output.info(f"[ok] %n:%b -> {actual}")

        # 2. default format
        actual = self._run(binary, fixture, [])
        if BRANCH not in actual or VCS_NAME not in actual:
            raise ConanException(f"default format lost branch info: {actual!r}")
        self.output.info(f"[ok] default format -> {actual}")

        # 3. feature list must match the build configuration (no sqlite3)
        features = self._run(binary, fixture, ["-F"]).split()
        for required in ("git", "hg", "cvs", "fossil", "svn-1.6"):
            if required not in features:
                raise ConanException(f"feature list is missing {required}: {features}")
        for unexpected in ("svn-1.7", "svn-1.8"):
            if unexpected in features:
                raise ConanException(
                    f"feature {unexpected} present although the recipe builds "
                    f"with --with-sqlite3=no: {features}"
                )
        self.output.info(f"[ok] -F -> {' '.join(features)}")

        # 4. no version control anywhere above the directory
        actual = self._run(binary, nested, ["-f", "%n:%b"])
        if actual != "":
            raise ConanException(
                f"expected no output outside any working copy, got {actual!r}"
            )
        self.output.info("[ok] no working copy -> empty output")

    def __del__(self):
        workdir = getattr(self, "_workdir_cache", None)
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    # ── helpers ──────────────────────────────────────────────────────────

    @property
    def _workdir(self):
        """Private scratch directory for the fixtures and captured output.

        Deliberately NOT under ``self.build_folder``: on the CI worker the
        checkout lives inside a git repository
        (``~/.cache/buildbot-worker/conan-pr-check/build``), so a fixture placed
        there inherits that repository and the "no version control anywhere
        above this directory" assertion would see ``git:main`` instead of empty
        output.  A directory under TMPDIR has no VCS above it; TMPDIR is a
        writable path on OHOS (see the recipe) so this also works on the device.
        """
        if getattr(self, "_workdir_cache", None) is None:
            self._workdir_cache = tempfile.mkdtemp(prefix="vcprompt-consumer-")
        return self._workdir_cache

    def _binary_path(self):
        bindir = self.dependencies["vcprompt"].cpp_info.bindirs[0]
        return os.path.join(bindir, "vcprompt")

    def _run(self, binary, cwd, extra_args):
        """Run the packaged binary in cwd and return its stripped stdout.

        The output is captured with a shell redirection because the binary has
        to execute on the target machine; the assertion itself is done here in
        Python so the test keeps working on a read-only /tmp.
        """
        label = "_".join(extra_args) or "default"
        out_file = os.path.join(self._workdir, f"out-{label.lstrip('-')}.txt")
        if os.path.exists(out_file):
            os.remove(out_file)
        command = " ".join(shlex.quote(part) for part in [binary, *extra_args])
        self.run(f"{command} > {shlex.quote(out_file)}", cwd=cwd, env="conanrun")
        if not os.path.exists(out_file):
            raise ConanException(f"vcprompt produced no output ({label})")
        return load(self, out_file).strip()

    def _write_fixtures(self):
        fixture = os.path.join(self._workdir, FIXTURE_DIR)
        git_dir = os.path.join(fixture, ".git")
        os.makedirs(os.path.join(git_dir, "refs", "heads"), exist_ok=True)
        save(self, os.path.join(git_dir, "HEAD"), f"ref: refs/heads/{BRANCH}\n")

        nested = os.path.join(self._workdir, NESTED_DIR)
        os.makedirs(nested, exist_ok=True)
        marker = os.path.join(nested, "file.txt")
        save(self, marker, "vcprompt local test fixture\n")
        os.chmod(marker, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
