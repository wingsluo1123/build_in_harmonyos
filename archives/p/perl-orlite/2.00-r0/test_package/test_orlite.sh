#!/bin/sh
# test_package/test_orlite.sh — L1 test for perl-orlite (ORLite) 2.00-r0
# Verifies ORLite.pm is packaged and its API is correct.
# Uses mock DBD::SQLite to test ORLite's pure Perl logic without
# requiring the DBD::SQLite .so (E046 SELinux platform limitation).
set -eu

# Dynamically discover Perl library paths (avoid hardcoding version numbers)
PERL_VERSION=$(perl -MConfig -e 'print $Config{version}')
PERL_ARCH=$(perl -MConfig -e 'print $Config{archname}')

USER_LIB1="$HOME/usr/local/lib/site_perl/${PERL_VERSION}"
USER_LIB2="$HOME/usr/local/lib/perl5"
USER_LIB3="$HOME/usr/local/lib/perl5/${PERL_ARCH}"
USER_LIB4="$HOME/usr/local/lib/site_perl/${PERL_VERSION}/${PERL_ARCH}"

EXTRA_LIB="${USER_LIB1}:${USER_LIB2}:${USER_LIB3}:${USER_LIB4}"
export PERL5LIB="${EXTRA_LIB}:${PERL5LIB:-}"

echo "[test] ORLite.pm file presence check"
perl -e 'my @f = grep { -f "$_/ORLite.pm" } @INC; die "ORLite.pm not found\n" unless @f; print "ORLite.pm found at: $f[0]\n";'
echo "✅ ORLite.pm presence OK"

echo "[test] ORLite version and API via mock DBD::SQLite"
perl -e '
BEGIN {
  $INC{"DBD/SQLite.pm"} = "/dev/null/mock";
  package DBD::SQLite; our $VERSION = "1.78";
  sub driver { bless {}, "DBD::SQLite::dr" }
  package DBD::SQLite::dr;
  sub connect { bless { Name => "test" }, "DBD::SQLite::db" }
  sub disconnect_all { 1 }
  package DBD::SQLite::db;
  sub prepare { bless {}, "DBD::SQLite::st" }
  sub do { 1 } sub selectrow_arrayref { [0] }
  sub selectall_arrayref { [] } sub selectrow_hashref { {} }
  sub table_info { bless {}, "DBD::SQLite::st" }
  sub tables { () } sub FETCH { undef } sub STORE { 1 }
  sub disconnect { 1 } sub commit { 1 } sub rollback { 1 }
  sub begin_work { 1 } sub quote { "\"$_[1]\"" }
  package DBD::SQLite::st;
  sub execute { 1 } sub fetchrow_arrayref { undef }
  sub fetchall_arrayref { [] } sub finish { 1 }
  sub FETCH { undef } sub STORE { 1 } sub rows { 0 }
}
use ORLite { file => "/tmp/orlite_test_mock.db", create => 1, package => "TestDB" };
die "version mismatch" unless $ORLite::VERSION eq "2.00";
die "no TestDB" unless %TestDB::;
for my $m (qw(connect prepare do selectall_arrayref dbh begin commit rollback iterate)) {
  die "missing $m" unless TestDB->can($m);
}
print "ORLite API test passed\n";
'
echo "✅ ORLite API mock test OK"
