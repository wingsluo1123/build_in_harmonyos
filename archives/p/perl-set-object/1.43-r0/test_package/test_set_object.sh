#!/bin/sh
# test_set_object.sh — Set::Object Perl module functional test.
# CI L0c: recognized as test source file (.sh extension).
# Uses PERL5LIB set by package_info() runenv_info.
# On HarmonyOS, SELinux HMDFS may block .so loading from user space (E046).
# The script exits 0 on success or expected platform limitation,
# exits non-zero on unexpected failures.
perl -e '
use strict;
use warnings;
use Set::Object;

my $s = Set::Object->new;
$s->insert(1, 2, 3);
die "insert failed: size=" . $s->size unless $s->size == 3;

$s->remove(2);
die "remove failed: size=" . $s->size unless $s->size == 2;
die "includes failed" unless $s->includes(1);
die "not includes failed" if $s->includes(2);

my $s2 = Set::Object->new(3, 4, 5);
my $u = $s->union($s2);
die "union failed: size=" . $u->size unless $u->size == 4;

my $i = $s->intersection($s2);
die "intersection failed: size=" . $i->size unless $i->size == 1;

print "FUNCTIONAL_TEST_OK: Set::Object version=" . $Set::Object::VERSION . " size=" . $s->size . "\n";
'
