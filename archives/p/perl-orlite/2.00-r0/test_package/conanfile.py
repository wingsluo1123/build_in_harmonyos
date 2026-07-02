#!/usr/bin/env python3
"""Conan test_package — perl-orlite (ORLite) 2.00-r0

L1 test: verify ORLite.pm is packaged and its API is correct.
Uses mock DBD::SQLite to test ORLite's pure Perl logic without
requiring the DBD::SQLite .so (E046 SELinux platform limitation).
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class PerlorliteTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # Pure Perl module — no compilation needed

    def test(self):
        # L2 smoke test: verify ORLite.pm is packaged and discoverable
        user_lib = os.path.expanduser("~/usr/local/lib/site_perl/5.42.0")
        user_lib2 = os.path.expanduser("~/usr/local/lib/perl5")
        extra_lib = f"{user_lib}:{user_lib2}"

        # Test 1: Verify ORLite.pm file presence
        self.run(
            f'PERL5LIB={extra_lib}:$PERL5LIB perl -e '
            f'\'my @f = grep {{ -f "$_/ORLite.pm" }} @INC; '
            f'die "ORLite.pm not found\\n" unless @f; '
            f'print "ORLite.pm found at: $f[0]\\n";\'',
            env="conanrun"
        )

        # Test 2: Verify ORLite version and API via mock DBD::SQLite
        # Mock approach: inject DBD::SQLite stub into %INC to bypass .so loading
        mock_test = (
            f'PERL5LIB={extra_lib}:$PERL5LIB perl -e \''
            # Inject mock DBD::SQLite
            f'BEGIN {{ '
            f'  $INC{{"DBD/SQLite.pm"}} = "/dev/null/mock"; '
            f'  package DBD::SQLite; our $VERSION = "1.78"; '
            f'  sub driver {{ bless {{}}, "DBD::SQLite::dr" }} '
            f'  package DBD::SQLite::dr; '
            f'  sub connect {{ bless {{ Name => "test" }}, "DBD::SQLite::db" }} '
            f'  sub disconnect_all {{ 1 }} '
            f'  package DBD::SQLite::db; '
            f'  sub prepare {{ bless {{}}, "DBD::SQLite::st" }} '
            f'  sub do {{ 1 }} sub selectrow_arrayref {{ [0] }} '
            f'  sub selectall_arrayref {{ [] }} sub selectrow_hashref {{ {{}} }} '
            f'  sub table_info {{ bless {{}}, "DBD::SQLite::st" }} '
            f'  sub tables {{ () }} sub FETCH {{ undef }} sub STORE {{ 1 }} '
            f'  sub disconnect {{ 1 }} sub commit {{ 1 }} sub rollback {{ 1 }} '
            f'  sub begin_work {{ 1 }} sub quote {{ "\\"$_[1]\\" "}} '
            f'  package DBD::SQLite::st; '
            f'  sub execute {{ 1 }} sub fetchrow_arrayref {{ undef }} '
            f'  sub fetchall_arrayref {{ [] }} sub finish {{ 1 }} '
            f'  sub FETCH {{ undef }} sub STORE {{ 1 }} sub rows {{ 0 }} '
            f'}} '
            # Load ORLite with mock params
            f'use ORLite {{ file => "/tmp/orlite_test_mock.db", create => 1, package => "TestDB" }}; '
            # Verify API
            f'die "version mismatch" unless $ORLite::VERSION eq "2.00"; '
            f'die "no TestDB" unless %TestDB::; '
            f'for my $m (qw(connect prepare do selectall_arrayref dbh begin commit rollback iterate)) {{ '
            f'  die "missing $m" unless TestDB->can($m); '
            f'}} '
            f'print "ORLite API test passed\\n"; '
            f'\''
        )
        self.run(mock_test, env="conanrun")
