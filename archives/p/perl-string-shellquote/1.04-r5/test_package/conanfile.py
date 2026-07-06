#!/usr/bin/env python3
"""Conan test_package for perl-string-shellquote.

Verifies that String::ShellQuote is installed and functional.
Tests: module loading, shell_quote(), shell_quote_best_effort(),
       shell_comment_quote(), and the shell-quote CLI tool.
"""
import os

from conan import ConanFile


class PerlStringShellQuoteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_perl_lib(self):
        """Find the Perl library path containing String/ShellQuote.pm."""
        dep = self.dependencies["perl-string-shellquote"]
        pkg_folder = dep.package_folder
        for root, dirs, files in os.walk(pkg_folder):
            if "ShellQuote.pm" in files:
                # Go up to the lib root (parent of String/)
                return os.path.dirname(os.path.dirname(root))
        raise Exception("Could not find ShellQuote.pm in package")

    def _find_shell_quote_bin(self):
        """Find the shell-quote executable in the installed package."""
        dep = self.dependencies["perl-string-shellquote"]
        pkg_folder = dep.package_folder
        for root, dirs, files in os.walk(pkg_folder):
            if "shell-quote" in files:
                return os.path.join(root, "shell-quote")
        return None  # CLI tool is optional on some platforms

    def test(self):
        perl_lib = self._find_perl_lib()
        shell_quote_bin = self._find_shell_quote_bin()

        test_script = os.path.join(self.recipe_folder, "run_test.sh")
        if shell_quote_bin:
            self.run(f'sh "{test_script}" "{perl_lib}" "{shell_quote_bin}"')
        else:
            self.run(f'sh "{test_script}" "{perl_lib}"')
