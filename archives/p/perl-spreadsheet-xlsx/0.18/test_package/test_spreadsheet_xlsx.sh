#!/bin/sh
# test_spreadsheet_xlsx.sh — Test script for perl-spreadsheet-xlsx 0.18
# Verifies that Spreadsheet::XLSX module files are correctly packaged and loadable.
# Called from test_package/conanfile.py test() method.
# Usage: sh test_spreadsheet_xlsx.sh <package_folder>

set -e

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "FAIL: package folder argument required"
    exit 1
fi

# Find Perl interpreter dynamically (R33: no hardcoded paths)
PERL=$(command -v perl 2>/dev/null || echo "")
if [ -z "$PERL" ]; then
    echo "FAIL: perl not found in PATH"
    exit 1
fi

# Find XLSX.pm in the package (avoid hardcoding Perl version)
XLSX_PM=$(find "$PKG_FOLDER" -name "XLSX.pm" -path "*/Spreadsheet/XLSX.pm" 2>/dev/null | head -1)
if [ -z "$XLSX_PM" ]; then
    echo "FAIL: Spreadsheet/XLSX.pm not found in package: $PKG_FOLDER"
    exit 1
fi

# Derive lib directory from .pm path (XLSX.pm is at <lib>/Spreadsheet/XLSX.pm)
SITE_LIB=$(dirname "$(dirname "$XLSX_PM")")

# Verify Fmt2007.pm exists
FMT2007_PM="${SITE_LIB}/Spreadsheet/XLSX/Fmt2007.pm"
if [ ! -f "$FMT2007_PM" ]; then
    echo "FAIL: Spreadsheet/XLSX/Fmt2007.pm not found: $FMT2007_PM"
    exit 1
fi

# Verify Utility2007.pm exists
UTIL2007_PM="${SITE_LIB}/Spreadsheet/XLSX/Utility2007.pm"
if [ ! -f "$UTIL2007_PM" ]; then
    echo "FAIL: Spreadsheet/XLSX/Utility2007.pm not found: $UTIL2007_PM"
    exit 1
fi

# Build PERL5LIB: package lib + system Perl @INC + user-local site_perl (dynamic)
# System @INC covers standard Perl lib paths; user-local site_perl covers
# modules installed via cpanm/cpan to $HOME/usr/local (common on OHOS)
EXISTING_PERL5LIB="${PERL5LIB:-}"
SYSTEM_PERL5LIB=$($PERL -e 'print join(":", @INC)' 2>/dev/null || echo "")
PERL_VERSION=$($PERL -e 'print substr($^V, 1)' 2>/dev/null || echo "")
USER_SITE_PERL="$HOME/usr/local/lib/site_perl/${PERL_VERSION}"
USER_LIB_PERL="$HOME/usr/local/lib/perl5"
PERL5LIB="${SITE_LIB}:${SYSTEM_PERL5LIB}"
if [ -n "$PERL_VERSION" ] && [ -d "$USER_SITE_PERL" ]; then
    PERL5LIB="${PERL5LIB}:${USER_SITE_PERL}"
fi
if [ -d "$USER_LIB_PERL" ]; then
    PERL5LIB="${PERL5LIB}:${USER_LIB_PERL}"
fi
# Preserve any pre-existing PERL5LIB
if [ -n "$EXISTING_PERL5LIB" ]; then
    PERL5LIB="${PERL5LIB}:${EXISTING_PERL5LIB}"
fi
export PERL5LIB

# Use a writable temp directory (OpenHarmony /tmp is read-only, E002)
TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"
TMPFILE="${TMPDIR}/test_xlsx_$$.xlsx"
TEST_SCRIPT="${TMPDIR}/test_spreadsheet_xlsx_$$.pl"

# Write the Perl test script to a temp file (avoids shell escaping issues)
cat > "$TEST_SCRIPT" <<'PERLEOF'
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
PERLEOF

# Run the Perl test
$PERL "$TEST_SCRIPT" "$TMPFILE"

# Clean up
rm -f "$TEST_SCRIPT" "$TMPFILE"

echo "test perl-spreadsheet-xlsx 0.18: OK"
