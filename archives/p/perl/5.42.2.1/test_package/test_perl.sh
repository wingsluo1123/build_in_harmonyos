#!/usr/bin/env sh
set -eu

: "${PERL:=perl}"

"$PERL" -e 'die "unexpected version $]" unless $] >= 5.042002 && $] < 5.043; print "perl $] ok\n"'
"$PERL" -MConfig -MFile::Spec -e 'print "os=$Config::Config{osname}; arch=$Config::Config{archname}; sep=", File::Spec->catfile(qw(a b)), "\n"'
"$PERL" -MFcntl -MPOSIX -e 'die "Fcntl constants unavailable" unless defined Fcntl::O_RDONLY(); print "XS modules ok\n"'
"$PERL" -e 'use strict; use warnings; my $x = 21 * 2; die unless $x == 42; print "script ok\n"'
