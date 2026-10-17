#!/usr/bin/env python3
"""test_package for maildrop — drives the installed command line tools.

The consumer is a mail administrator doing the two things this package exists
for: decode a real MIME message, and deliver a message into a Maildir through a
filter recipe. Both flows use only the tools the package installs, and both
assert on the resulting message content rather than on exit status alone.
"""
import os
import shutil

from conan import ConanFile


class MaildropTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # This target's /system/bin/sh cannot execute ELF binaries, so the flows
        # are wrapped in the shell this environment provides; the framework's own
        # templates point at the same interpreter through CONFIG_SHELL.
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/bin/sh")
        # The flows create messages, a Maildir and a filter file. Conan runs the
        # test package in place, so self.build_folder is this archive's own
        # test_package/ directory; the work directory therefore goes to the
        # environment's temporary area to keep every run artefact out of the
        # package that is being reviewed.
        base = os.environ.get("TMPDIR")
        if not base or not os.path.isdir(base):
            base = os.path.expanduser("~/tmp")
        os.makedirs(base, exist_ok=True)
        work = os.path.join(base, "maildrop-consumer-work")
        self.run(f"WORKDIR='{work}' '{bash}' test.sh", env="conanrun")
