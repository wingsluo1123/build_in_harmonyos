#!/usr/bin/env perl
# gen_makefile2.pl — 完整处理 Makefile.SH，含条件逻辑和变量替换
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

# 3. 处理脚本：跟踪条件状态，提取 heredoc 内容
my $output = '';
my $in_heredoc = 0;
my $delim = '!GROK!THIS!';
my $skip = 0;  # 条件跳过栈
my @cond_stack;

sub val {
    my $name = shift;
    return exists $cfg{$name} ? $cfg{$name} : '';
}

sub eval_cond {
    my $expr = shift;
    $expr =~ s/\$(\w+)/val($1)/ge;
    # 简单求值
    return 1 if $expr =~ /^1$/ || $expr =~ /true/i;
    return 0 if $expr =~ /^0$/ || $expr =~ /false/i || $expr =~ /^undef$/ || $expr eq '';
    # 处理 != 比较
    if ($expr =~ /^(\S+)\s*!=\s*(\S+)$/) { return val($1) ne $2 ? 1 : 0; }
    if ($expr =~ /^(\S+)\s*=\s*(\S+)$/)  { return val($1) eq $2 ? 1 : 0; }
    # 非空检查
    if ($expr =~ /^(\w+)$/) { return val($1) ? 1 : 0; }
    return 1;
}

for my $line (@lines) {
    if ($in_heredoc) {
        if ($line =~ /^!GROK!THIS!\s*$/) {
            $in_heredoc = 0;
            next;
        }
        # 变量替换
        $line =~ s/\$\{(\w+)\}/val($1)/ge;
        $line =~ s/\$([A-Za-z_]\w*)/val($1)/ge;
        $output .= $line;
        next;
    }

    # 处理条件
    if ($line =~ /^\s*if\s+(.*)/) {
        my $r = eval_cond($1);
        push @cond_stack, $skip;
        $skip = 1 if !$r;
        next;
    }
    if ($line =~ /^\s*elsif\s+(.*)/) {
        my $r = eval_cond($1);
        $skip = $cond_stack[-1] ? 1 : ($r ? 0 : 1);
        next;
    }
    if ($line =~ /^\s*else\s*$/) {
        $skip = $cond_stack[-1] ? 1 : ($skip ? 0 : 1);
        next;
    }
    if ($line =~ /^\s*(fi|endif)\s*$/) {
        $skip = pop @cond_stack // 0;
        next;
    }

    next if $skip;

    # 检测 heredoc 开始
    if ($line =~ /<<\s*!GROK!THIS!/) {
        $in_heredoc = 1;
        next;
    }
}

# 写入 Makefile
open(my $out, '>', $out_file) or die "Cannot write $out_file: $!";
print $out $output;
close($out);

my $size = length($output);
my $lc = ($output =~ tr/\n//);
print "Makefile: $size bytes, $lc lines\n";
