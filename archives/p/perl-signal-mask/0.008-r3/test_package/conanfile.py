#!/usr/bin/env python3
"""Conan test_package — perl-signal-mask 0.008-r3

Tests that Signal::Mask and Signal::Pending can be loaded
and basic signal mask operations work correctly.
Uses test_signal_mask.sh which exercises the module's API.
"""
import os
import glob

from conan import ConanFile
from conan.tools.layout import basic_layout


def _find_ipc_signal_paths():
    """Dynamically find Perl lib paths containing IPC/Signal.pm.

    Searches system Perl site_perl, $HOME/usr/local/lib, and /usr/local/lib
    using glob — no subprocess or perl binary call required.
    """
    paths = []
    seen = set()

    # 1. System Perl site_perl (HNP-managed Perl installation)
    for p in glob.glob("/data/service/hnp/perl.org/perl_*/lib/site_perl/*/"):
        ap = os.path.abspath(p)
        if ap not in seen and os.path.exists(os.path.join(ap, "IPC", "Signal.pm")):
            paths.append(ap)
            seen.add(ap)

    # 2. $HOME/usr/local/lib paths (user-installed Perl modules)
    home = os.environ.get("HOME", "")
    if home:
        for sub in ["usr/local/lib/perl5", "usr/local/lib/site_perl",
                     "usr/local/lib/perl5/site_perl/*"]:
            for p in glob.glob(os.path.join(home, sub)):
                ap = os.path.abspath(p)
                if os.path.isdir(ap) and ap not in seen:
                    if os.path.exists(os.path.join(ap, "IPC", "Signal.pm")):
                        paths.append(ap)
                        seen.add(ap)

    # 3. /usr/local/lib paths
    for sub in ["perl5", "site_perl", "perl5/site_perl/*"]:
        for p in glob.glob(os.path.join("/usr/local/lib", sub)):
            ap = os.path.abspath(p)
            if os.path.isdir(ap) and ap not in seen:
                if os.path.exists(os.path.join(ap, "IPC", "Signal.pm")):
                    paths.append(ap)
                    seen.add(ap)

    return paths


class PerlSignalMaskTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg = self.dependencies["perl-signal-mask"]
        pkg_folder = pkg.package_folder

        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Mask.pm"), recursive=True)
        if not pm_files:
            raise Exception("Mask.pm not found in package")

        # lib_dir is the directory containing the "Signal" directory
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Build PERL5LIB: package lib dir + IPC::Signal paths
        perl5lib_parts = [lib_dir]
        perl5lib_parts.extend(_find_ipc_signal_paths())

        perl5lib = ":".join(p for p in perl5lib_parts if p)

        test_script = os.path.join(self.source_folder, "test_signal_mask.sh")
        self.run(f'PERL5LIB={perl5lib} sh {test_script}', env="conanrun")
