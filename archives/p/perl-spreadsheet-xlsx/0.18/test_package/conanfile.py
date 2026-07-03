#!/usr/bin/env python3
"""Conan test_package for perl-spreadsheet-xlsx 0.18.

Verifies that Spreadsheet::XLSX can be loaded and basic XLSX parsing works.
"""
import os

from conan import ConanFile


class PerlSpreadsheetXlsxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # Pure Perl module, no build step needed

    def test(self):
        perl = "/data/service/hnp/bin/perl"

        # Find the package's lib directory from the dependency
        pkg_folder = None
        for name, dep in self.dependencies.items():
            if hasattr(dep, "package_folder"):
                pkg_folder = dep.package_folder
                break

        # Build PERL5LIB from the package folder
        perl5lib_paths = []
        if pkg_folder:
            for root, _, files in os.walk(pkg_folder):
                if any(f.endswith(".pm") for f in files):
                    perl5lib_paths.append(root)

        # Also add system Perl library paths for dependencies
        perl5lib_paths.append("/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0")
        perl5lib_paths.append("/storage/Users/currentUser/usr/local/lib/perl5")

        # Add existing PERL5LIB
        existing = os.environ.get("PERL5LIB", "")
        if existing:
            perl5lib_paths.append(existing)

        perl5lib = ":".join(perl5lib_paths)

        # Use a writable temp directory (OpenHarmony /tmp is read-only)
        tmpdir = self.build_folder or os.path.expanduser("~/.opendesk-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        tmpfile = os.path.join(tmpdir, f"test_xlsx_{os.getpid()}.xlsx")

        # Write the Perl test script to a file (avoids shell escaping issues)
        test_script_path = os.path.join(tmpdir, f"test_{os.getpid()}.pl")
        with open(test_script_path, "w") as f:
            f.write(r'''
use strict;
use warnings;
use Spreadsheet::XLSX;

# Verify module loaded with correct version
my $version = $Spreadsheet::XLSX::VERSION;
die "Test failed: VERSION not defined" unless defined $version;
die "Test failed: expected version 0.18, got $version" unless $version eq '0.18';

# Create a minimal valid XLSX file in-memory using Archive::Zip
# and verify Spreadsheet::XLSX can parse it
use Archive::Zip;

my $tmpfile = shift @ARGV;

# Build a minimal XLSX (ZIP archive with required XML parts)
my $zip = Archive::Zip->new();

# [Content_Types].xml
$zip->addString(<<'CT', '[Content_Types].xml');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
CT

# _rels/.rels
$zip->addString(<<'RELS', '_rels/.rels');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
RELS

# xl/workbook.xml
$zip->addString(<<'WB', 'xl/workbook.xml');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>
<sheet name="TestSheet" sheetId="1" r:id="rId1"/>
</sheets>
</workbook>
WB

# xl/_rels/workbook.xml.rels
$zip->addString(<<'WBRELS', 'xl/_rels/workbook.xml.rels');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
WBRELS

# xl/worksheets/sheet1.xml
$zip->addString(<<'SHEET', 'xl/worksheets/sheet1.xml');
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
<row r="1">
<c r="A1" t="str"><v>Hello</v></c>
<c r="B1" t="str"><v>World</v></c>
</row>
</sheetData>
</worksheet>
SHEET

# Write the ZIP file
unless ($zip->writeToFileNamed($tmpfile) == Archive::Zip::AZ_OK) {
    die "Failed to write test XLSX file";
}

# Parse the XLSX file with Spreadsheet::XLSX
my $excel = Spreadsheet::XLSX->new($tmpfile);

# Verify we got at least one worksheet
die "Test failed: no worksheets" unless $excel->{Worksheet} && @{$excel->{Worksheet}} > 0;

my $sheet = $excel->{Worksheet}[0];
die "Test failed: sheet name mismatch" unless $sheet->{Name} eq 'TestSheet';

# Clean up
unlink $tmpfile;

print "OK: Spreadsheet::XLSX smoke test passed\n";
''')

        # Set PERL5LIB in the process environment so self.run() inherits it
        os.environ["PERL5LIB"] = perl5lib

        # Use self.run() so CI L0d gate recognizes a real test invocation
        self.run(f'{perl} {test_script_path} {tmpfile}')

        # Clean up test script
        if os.path.exists(test_script_path):
            os.remove(test_script_path)
