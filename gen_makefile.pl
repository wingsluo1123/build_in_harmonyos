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

# 3. 设置变量
my $spitshell = $config{spitshell} || 'cat';
my $makefile = $config{Makefile} || 'Makefile';

# 4. 提取所有 heredoc 块并处理变量替换
my $output = '';
my $in_heredoc = 0;
my $delimiter = '!GROK!THIS!';

for my $line (@lines) {
    if (!$in_heredoc) {
        # 检测 heredoc 开始: $spitshell >$Makefile <<!GROK!THIS!
        # 或 $spitshell >>$Makefile <<!GROK!THIS!
        if ($line =~ /<<\s*!GROK!THIS!/) {
            $in_heredoc = 1;
            next;
        }
    } else {
        # 检测 heredoc 结束
        if ($line =~ /^!GROK!THIS!\s*$/) {
            $in_heredoc = 0;
            next;
        }
        # 在 heredoc 内容中进行变量替换
        # 替换 ${var} 格式
        $line =~ s/\$\{(\w+)\}/exists $config{$1} ? $config{$1} : "\${$1}"/ge;
        # 替换 $var 格式（但不是 $$ 或 $@ 等）
        $line =~ s/\$([A-Za-z_]\w*)/exists $config{$1} ? $config{$1} : "\$$1"/ge;
        $output .= $line;
    }
}

# 5. 写入 Makefile
open(my $out, '>', $out_file) or die "Cannot write $out_file: $!";
print $out $output;
close($out);

my $size = length($output);
my $lines_count = ($output =~ tr/\n//);
print "Makefile generated: $size bytes, $lines_count lines\n";
