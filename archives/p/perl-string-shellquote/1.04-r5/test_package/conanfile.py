#!/usr/bin/env python3
"""Conan test_package for perl-string-shellquote.

Verifies that String::ShellQuote is installed and functional.
Tests: module loading, shell_quote(), shell_quote_best_effort(),
       shell_comment_quote(), and the shell-quote CLI tool.
"""
import os
import tempfile

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

        # Set PERL5LIB so Perl can find the module
        old_perl5lib = os.environ.get("PERL5LIB", "")
        if old_perl5lib:
            os.environ["PERL5LIB"] = perl_lib + ":" + old_perl5lib
        else:
            os.environ["PERL5LIB"] = perl_lib

        try:
            # Write a comprehensive test script to avoid shell escaping issues
            test_script = (
                "use strict;\n"
                "use warnings;\n"
                "use String::ShellQuote "
                "qw(shell_quote shell_quote_best_effort shell_comment_quote);\n"
                "\n"
                "my $pass = 0;\n"
                "my $fail = 0;\n"
                "\n"
                "sub check {\n"
                "    my ($desc, $got, $expected) = @_;\n"
                "    if ($got eq $expected) {\n"
                "        $pass++;\n"
                "    } else {\n"
                "        print \"FAIL: $desc\\n"
                "  expected: [$expected]\\n"
                "  got:      [$got]\\n\";\n"
                "        $fail++;\n"
                "    }\n"
                "}\n"
                "\n"
                "# Module loaded successfully\n"
                "$pass++;\n"
                "\n"
                "# shell_quote basic\n"
                "check('shell_quote(hello world)', "
                "shell_quote('hello', 'world'), 'hello world');\n"
                "check('shell_quote(empty list)', shell_quote(), '');\n"
                "check('shell_quote(empty string)', "
                "shell_quote(''), \"''\");\n"
                "check('shell_quote(undef)', shell_quote(undef), \"''\");\n"
                "\n"
                "# shell_quote special chars\n"
                "check('shell_quote(foo*)', shell_quote('foo*'), "
                "\"'foo*'\");\n"
                "check('shell_quote(foo bar)', shell_quote('foo bar'), "
                "\"'foo bar'\");\n"
                "check('shell_quote(single quote)', "
                "shell_quote(\"'\"), \"\\\\'\");\n"
                "\n"
                "# shell_quote_best_effort\n"
                "check('best_effort(empty)', "
                "shell_quote_best_effort(), '');\n"
                "check('best_effort(foo*)', "
                "shell_quote_best_effort('foo*'), \"'foo*'\");\n"
                "\n"
                "# shell_comment_quote\n"
                "check('comment_quote(empty)', "
                "shell_comment_quote(''), '');\n"
                "check('comment_quote(foo)', "
                "shell_comment_quote('foo'), 'foo');\n"
                "check('comment_quote(newlines)', "
                "shell_comment_quote(\"foo\\nbar\"), \"foo\\n#bar\");\n"
                "\n"
                "# null byte handling\n"
                "eval { shell_quote(\"t\\x00\") };\n"
                "$pass++ if $@;\n"
                "my $r = shell_quote_best_effort(\"foo*\", \"as\\x00df\");\n"
                "$pass++ if $r =~ /foo\\*/;\n"
                "\n"
                "print \"$pass tests passed, $fail failed\\n\";\n"
                "exit($fail > 0 ? 1 : 0);\n"
            )
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pl", delete=False
            ) as f:
                f.write(test_script)
                test_file = f.name

            try:
                self.run(f'perl {test_file}')
            finally:
                os.unlink(test_file)

            # Test the shell-quote CLI tool if available
            shell_quote_bin = self._find_shell_quote_bin()
            if shell_quote_bin:
                self.run(f'perl "{shell_quote_bin}" hello world')

        finally:
            # Restore environment
            if old_perl5lib:
                os.environ["PERL5LIB"] = old_perl5lib
            else:
                os.environ.pop("PERL5LIB", None)
