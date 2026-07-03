#!/usr/bin/env python3
"""Conan test_package — perl-sql-translator (SQL::Translator)
L1-L2 test: verify module files installed AND run functional conversion tests.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlSqlTranslatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-sql-translator"]
        pkg_folder = dep.package_folder
        self.output.info(f"Package folder: {pkg_folder}")

        # L1: File existence checks
        translator_pm = os.path.join(pkg_folder, "lib", "perl5", "SQL", "Translator.pm")
        assert os.path.exists(translator_pm), f"SQL/Translator.pm not found at {translator_pm}"
        self.output.info("✅ Found SQL/Translator.pm")

        pm_files = glob.glob(os.path.join(pkg_folder, "lib", "perl5", "SQL", "**", "*.pm"), recursive=True)
        self.output.info(f"✅ Found {len(pm_files)} .pm files under SQL/")
        assert len(pm_files) > 50, f"Expected >50 .pm files, got {len(pm_files)}"

        # Check for sqlt script
        sqlt_bin = os.path.join(pkg_folder, "lib", "perl5", "bin", "sqlt")
        assert os.path.exists(sqlt_bin), f"sqlt script not found at {sqlt_bin}"
        self.output.info("✅ Found sqlt script")

        # L2: Functional test — MySQL to PostgreSQL DDL conversion
        perl5lib = os.path.join(pkg_folder, "lib", "perl5")
        perl5lib_arch = os.path.join(perl5lib, "aarch64-linux")
        env = os.environ.copy()
        env["PERL5LIB"] = f"{perl5lib_arch}:{perl5lib}"

        test_code = r"""
use SQL::Translator;
my $mysql = q{
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE
);
};
my $tr = SQL::Translator->new();
$tr->parser("MySQL");
$tr->producer("PostgreSQL");
my $result = $tr->translate(data => \$mysql);
die "Translation failed" unless $result;
die "Missing CREATE TABLE" unless $result =~ /CREATE TABLE/i;
die "Missing serial" unless $result =~ /serial/i;
print "FUNC_TEST_PASS\n";
"""

        result = subprocess.run(
            ["perl", "-e", test_code],
            capture_output=True, text=True, env=env, timeout=30
        )
        if result.returncode != 0:
            self.output.error(f"Functional test failed:\n{result.stderr}")
            assert False, "Functional test (MySQL->PostgreSQL) failed"
        if "FUNC_TEST_PASS" in result.stdout:
            self.output.info("✅ Functional test: MySQL -> PostgreSQL conversion PASS")
        else:
            self.output.error(f"Unexpected output: {result.stdout}")
            assert False, "Functional test did not produce expected output"
