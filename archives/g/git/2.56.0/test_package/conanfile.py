#!/usr/bin/env python3
"""Conan test_package — git 2.56.0 (CLI application).

R34: exercises the packaged git binary end-to-end (version, init, commit,
log, tag, branch, merge, fsck, clone) instead of a print-only stub.
"""
import os
import shutil

from conan import ConanFile


class GitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bindir = self.dependencies["git"].cpp_info.bindirs[0]
        git = os.path.join(bindir, "git")
        pkgbindir = os.path.dirname(bindir)
        # conan installs with --prefix=/ + DESTDIR: fix up git's runtime paths
        # NB: do NOT set GIT_TEST_ASSUME_DIFFERENT_OWNER here, not even empty:
        # git parses an empty boolean env value as TRUE.
        # PATH must put the packaged git first: git spawns helper subcommands
        # (git-refs etc.) via PATH, and the system git 2.45.2 would break them.
        bindir = os.path.dirname(git)
        pkgroot = os.path.dirname(bindir)
        libexec = os.path.join(pkgroot, "libexec", "git-core")
        templates = os.path.join(pkgroot, "share", "git-core", "templates")
        env = ["PATH={}:{}".format(bindir, os.environ.get("PATH", ""))]
        if os.path.isdir(libexec):
            env.append("GIT_EXEC_PATH={}".format(libexec))
        if os.path.isdir(templates):
            env.append("GIT_TEMPLATE_DIR={}".format(templates))

        def run(cmd):
            # inline env prefix: conan's env= wrapper does not reliably reach
            # helper subcommands spawned by git itself
            prefix = 'PATH="{bindir}:$PATH" GIT_EXEC_PATH="{lex}" GIT_TEMPLATE_DIR="{tpl}"'.format(
                bindir=bindir, lex=libexec, tpl=templates)
            self.run(f"{prefix} {cmd}")

        pkg = os.path.join(self.build_folder, "gitrepo")
        for stale in (pkg, pkg + "-clone"):
            shutil.rmtree(stale, ignore_errors=True)

        # 1. binary runs and reports the packaged version
        run(f'"{git}" --version')

        # 2. real workflow: init → identity → commit → log → tag → branch →
        #    merge → fsck → clone
        run(f'"{git}" init -q -b main "{pkg}"')
        run(f'"{git}" -C "{pkg}" config user.name conan-test')
        run(f'"{git}" -C "{pkg}" config user.email conan@test.local')
        with open(os.path.join(pkg, "a.txt"), "w") as f:
            f.write("hello-git\n")
        run(f'"{git}" -C "{pkg}" add a.txt')
        run(f'"{git}" -C "{pkg}" commit -qm "init commit"')
        run(f'"{git}" -C "{pkg}" log --oneline | grep -q "init commit"')
        run(f'"{git}" -C "{pkg}" tag v1.0')
        run(f'"{git}" -C "{pkg}" switch -qc feature')
        with open(os.path.join(pkg, "a.txt"), "a") as f:
            f.write("feature\n")
        run(f'"{git}" -C "{pkg}" commit -qam feature')
        run(f'"{git}" -C "{pkg}" switch -q main')
        run(f'"{git}" -C "{pkg}" merge --no-edit feature')
        run(f'"{git}" -C "{pkg}" fsck --no-dangling')
        run(f'"{git}" clone -q "{pkg}" "{pkg}-clone"')
        run(f'"{git}" -C "{pkg}-clone" log --oneline | grep -q "init commit"')
        print("git test_package: ALL CHECKS PASSED")
