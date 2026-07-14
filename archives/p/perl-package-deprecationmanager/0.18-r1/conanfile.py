#!/usr/bin/env python3
"""Conan recipe for perl-package-deprecationmanager 0.18-r1 (Package::DeprecationManager CPAN module).

This is a pure-Perl module built with ExtUtils::MakeMaker (Makefile.PL).
Build steps: perl Makefile.PL -> make -> make install

Dependencies: Package::Stash, Params::Util, Sub::Install, Sub::Util, List::Util, Carp
Note: Package::Stash is vendored (built from source) because the conan recipe
      for perl-package-stash is not yet published to the remote registry.
      When it is published, restore the requirements() method and remove the
      vendored build block.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlPackageDeprecationManagerConan(ConanFile):
    name = "perl-package-deprecationmanager"
    version = "0.18-r1"
    description = "Manage deprecation warnings for your distribution (Package::DeprecationManager CPAN module)"
    license = "artistic_2"
    homepage = "https://metacpan.org/dist/Package-DeprecationManager"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."

    def source(self):
        # Download Package::DeprecationManager (extracted to source root)
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download Package::Stash (vendored dependency, extracted to subdirectory)
        stash_data = self.conan_data["stash_sources"]
        get(self, **stash_data, strip_root=True,
            destination=os.path.join(self.source_folder, "Package-Stash"))

    def build(self):
        apply_conandata_patches(self)

        pkg_lib = os.path.join(self.package_folder, "lib", "perl5")

        # Step 1: Build and install Package::Stash (vendored dependency).
        # When perl-package-stash/0.40-r1 is published to conan remote,
        # restore self.requires() and remove this block.
        stash_dir = os.path.join(self.source_folder, "Package-Stash")
        if os.path.isdir(stash_dir):
            self.run("perl Makefile.PL --pureperl-only INSTALL_BASE={}".format(self.package_folder),
                     cwd=stash_dir)
            self.run("make PUREPERL_ONLY=1", cwd=stash_dir)
            self.run("make install PUREPERL_ONLY=1", cwd=stash_dir)

        # Step 2: Build Package::DeprecationManager (needs Package::Stash on PERL5LIB)
        self.run('PERL5LIB="{}:$PERL5LIB" perl Makefile.PL INSTALL_BASE={}'.format(
            pkg_lib, self.package_folder))
        self.run('PERL5LIB="{}:$PERL5LIB" make'.format(pkg_lib))

    def package(self):
        # Install Package::DeprecationManager (Package::Stash already installed in build())
        pkg_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.run('PERL5LIB="{}:$PERL5LIB" make install'.format(pkg_lib))

    def package_info(self):
        # Perl module: expose lib path for consumers
        perl5_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl5_lib)
