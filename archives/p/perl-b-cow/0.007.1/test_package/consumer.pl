BEGIN {
 @INC=split /:/,$ENV{PERL5LIB};
 my @roots=split /:/,$ENV{BINDING_ROOTS};
 die "unbound include" if grep {my $p=$_;!grep {index($p,"$_/")==0} @roots} @INC;
}
use strict;
use warnings;
use B::COW qw(can_cow is_cow cowrefcnt);
die "real version drift" unless $B::COW::VERSION eq '0.007';
die "real COW support missing" unless can_cow();
die "undefined scalar reported COW" if is_cow(undef);
my $original='Harmony native copy-on-write fixture';my $copy=$original;
die "real shared scalar not COW" unless is_cow($original) && is_cow($copy);
die "real COW count missing" unless cowrefcnt($original)>0;
$copy.=' changed';
die "real copy-on-write isolation failed" unless $original eq 'Harmony native copy-on-write fixture' && $copy ne $original;
die "own package XS not loaded" unless grep {index($_,$ENV{B_COW_XS_ROOT}.'/auto/B/COW/')==0 && /\/COW\.so$/} @DynaLoader::dl_shared_objects;
print "CONSUMER_TEST_PASS=1/1\nactual matching XS COW introspection and write isolation\n";
