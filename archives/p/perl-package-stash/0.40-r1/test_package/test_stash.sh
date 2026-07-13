#!/bin/sh
# test_package/test_stash.sh — L1 smoke test wrapper for perl-package-stash
# Runs test_stash.pl which tests real Package::Stash API.
set -eu

script_dir=$(dirname "$0")

# Package::Stash requires Module::Implementation at runtime.
# On CI workers, this system-installed module may not be in the default @INC.
# Add system Perl lib paths so it can be found.
for sys_path in \
    /storage/Users/currentUser/usr/local/lib/perl5 \
    /storage/Users/currentUser/usr/local/lib/site_perl/5.42.0 \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0; do
    if [ -d "$sys_path" ]; then
        PERL5LIB="${PERL5LIB:+$PERL5LIB:}$sys_path"
    fi
done
export PERL5LIB

perl "$script_dir/test_stash.pl"
