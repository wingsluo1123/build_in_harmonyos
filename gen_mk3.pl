#!/usr/bin/env perl
# gen_mk3.pl — 提取 Makefile.SH 中所有 heredoc 内容
use strict;
use warnings;

my $dir = $ARGV[0] || '.';
my $config_file = "$dir/config.sh";
my $sh_file = "$dir/Makefile.SH";
my $out_file = "$dir/Makefile";

# 1. 读取 config.sh
my %cfg;
open(my $cf, '<', $config_file) or die "Cannot open $config_file: $!";
while (<$cf>) {
    chomp;
    if (/^(\w+)='(.*)'$/) { $cfg{$1} = $2; }
    elsif (/^(\w+)=(.*)$/) { $cfg{$1} = $2; }
}
close($cf);

# 2. 读取 Makefile.SH
open(my $sh, '<', $sh_file) or die "Cannot open $sh_file: $!";
my @lines = <$sh>;
close($sh);

# 3. 提取所有 heredoc 内容
my $output = '';
my $in_heredoc = 0;
my $delim = '';

for my $line (@lines) {
    if (!$in_heredoc) {
        # 检测任何 heredoc 开始
        # 格式: ... <<DELIM 或 ... <<'DELIM' 或 ... <<"DELIM"
        if ($line =~ /<<\s*'?([^\s']+?)'?\s*$/) {
            my $d = $1;
            # 去除可能的尾部字符
            $d =~ s/['"]//g;
            $delim = $d;
            $in_heredoc = 1;
            next;
        }
    } else {
        # 检测 heredoc 结束（行首匹配分隔符）
        my $d = $delim;
        $d =~ s/['"]//g;
        if ($line =~ /^\Q$d\E\s*$/) {
            $in_heredoc = 0;
            next;
        }
        # 变量替换（只对 !GROK!THIS! 和 EOF 块做替换，不对 !NO!SUBS! 做替换）
        if ($delim !~ /NO.*SUBS/) {
            $line =~ s/\$\{(\w+)\}/exists $cfg{$1} ? $cfg{$1} : "\${$1}"/ge;
            $line =~ s/\$([A-Za-z_]\w*)/exists $cfg{$1} ? $cfg{$1} : "\$$1"/ge;
        }
        $output .= $line;
    }
}

# 4. 写入 Makefile
open(my $out, '>', $out_file) or die "Cannot write $out_file: $!";
print $out $output;
close($out);

my $size = length($output);
my $lc = ($output =~ tr/\n//);
print "Makefile: $size bytes, $lc lines\n";
