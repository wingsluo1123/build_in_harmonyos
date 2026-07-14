#!/bin/sh
# test_package/test_orlite.sh — L1 test for perl-orlite (ORLite) 2.00-r0
# Verifies ORLite.pm is packaged, version is correct, and API methods exist.
# Uses static analysis to avoid loading ORLite's full dependency chain
# (Params::Util, DBI, DBD::SQLite) which may not be installed on CI workers.
set -eu

echo "[test] ORLite.pm file presence check"
ORLITE_PATH=$(perl -e 'my @f = grep { -f "$_/ORLite.pm" } @INC; die "ORLite.pm not found\n" unless @f; print "$f[0]/ORLite.pm";')
echo "ORLite.pm found at: $(dirname "$ORLITE_PATH")"
echo "✅ ORLite.pm presence OK"

echo "[test] ORLite version verification"
perl -e "
  my \$f = '$ORLITE_PATH';
  open my \$fh, '<', \$f or die \"Cannot read \$f: \$!\";
  my \$content = do { local \$/; <\$fh> };
  close \$fh;

  # Extract version
  my (\$ver) = \$content =~ /\\\$VERSION\\s*=\\s*['\"]([^'\"\\s]+)/;
  die 'VERSION not found in ORLite.pm' unless \$ver;
  die \"version mismatch: got \$ver, expected 2.00\" unless \$ver eq '2.00';
  print \"ORLite version: \$ver\n\";
"
echo "✅ ORLite version OK"

echo "[test] ORLite API method verification (static analysis)"
perl -e "
  my \$f = '$ORLITE_PATH';
  open my \$fh, '<', \$f or die \"Cannot read \$f: \$!\";
  my \$content = do { local \$/; <\$fh> };
  close \$fh;

  # Verify file has substantial content
  my \$lines = \$content =~ tr/\\n//;
  die \"ORLite.pm too small (\$lines lines)\" if \$lines < 100;
  print \"ORLite.pm size: \$lines lines\n\";

  # Verify 9 core API methods are defined as subroutines
  my @required = qw(connect prepare do selectall_arrayref dbh begin commit rollback iterate);
  my @missing;
  for my \$m (@required) {
    unless (\$content =~ /^sub\\s+\$m\\b/m) {
      push @missing, \$m;
    }
  }
  if (@missing) {
    die 'Missing API methods: ' . join(', ', @missing) . \"\n\";
  }
  print 'All ' . scalar(@required) . ' core API methods verified: ' . join(', ', @required) . \"\n\";

  # Verify POD documentation exists
  unless (\$content =~ /^=head1/m) {
    die 'No POD documentation found';
  }
  my \$pod_heads = () = \$content =~ /^=head/gm;
  print \"POD sections: \$pod_heads\n\";
"
echo "✅ ORLite API verification OK"
