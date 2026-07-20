use strict;
use warnings;
use Crypt::OpenSSL::Guess;

my $inc = openssl_inc_paths();
print "include path: $inc\n";

my $lib = openssl_lib_paths();
print "lib path: $lib\n";

print "OK\n";
