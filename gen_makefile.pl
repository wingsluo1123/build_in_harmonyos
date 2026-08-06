#!/usr/bin/env perl
# gen_makefile.pl — 用 Perl 处理 Makefile.SH 生成 Makefile
# 解决 HarmonyOS 上 shell heredoc 不工作的问题

use strict;
use warnings;

my $dir = $ARGV[0] || '.';
my $config_file = "$dir/config.sh";
my $sh_file = "$dir/Makefile.SH";
my $out_file = "$dir/Makefile";

# 1. 读取 config.sh
my %config;
open(my $cf, '<', $config_file) or die "Cannot open $config_file: $!";
while (<$cf>) {
    chomp;
    if (/^(\w+)='(.*)'\s*$/ || /^(\w+)=(.*)\s*$/) {
        $config{$1} = $2;
    }
}
close($cf);

# 2. 读取 Makefile.SH
open(my $sh, '<', $sh_file) or die "Cannot open $sh_file: $!";
my @lines = <$sh>;
close($sh);

# 3. Process heredoc blocks with variable substitution
my $output = '';
my $in_heredoc = 0;

for my $line (@lines) {
    if (!$in_heredoc) {
        if ($line =~ /<<\s*!GROK!THIS!/) {
            $in_heredoc = 1;
            next;
        }
    } else {
        if ($line =~ /^!GROK!THIS!\s*$/) {
            $in_heredoc = 0;
            next;
        }
        # Variable substitution: replace known vars, leave unknown as-is.
        # Use s!!! to avoid delimiter conflict with paths containing /.
        # Iterate over config keys instead of while+regex to prevent infinite loop.
        for my $key (keys %config) {
            $line =~ s!\$\{$key\}!$config{$key}!g;
            next unless $key =~ /^[A-Za-z_]\w*$/;
            $line =~ s!\$$key\b!$config{$key}!g;
        }
        $output .= $line;
    }
}

# 4. Write Makefile
open(my $out, '>', $out_file) or die "Cannot write $out_file: $!";
print $out $output;
close($out);

my $size = length($output);
my $lines_count = scalar(() = $output =~ /\n/g);
print "Makefile generated: $size bytes, $lines_count lines\n";
