#!/usr/bin/env perl
# gen_mk4.pl — 模拟 shell 执行 Makefile.SH，处理条件逻辑和 heredoc
use strict;
use warnings;

my $dir = $ARGV[0] || '.';
my $config_file = "$dir/config.sh";
my $sh_file = "$dir/Makefile.SH";
my $out_file = "$dir/Makefile";

# 读取 config.sh
my %cfg;
open(my $cf, '<', $config_file) or die "Cannot open $config_file: $!";
while (<$cf>) {
    chomp;
    if (/^(\w+)='(.*)'$/) { $cfg{$1} = $2; }
    elsif (/^(\w+)=(.*)$/) { $cfg{$1} = $2; }
}
close($cf);

# 读取 Makefile.SH
open(my $sh, '<', $sh_file) or die "Cannot open $sh_file: $!";
my @lines = <$sh>;
close($sh);

# 变量替换函数
sub subst {
    my $s = shift;
    # 替换 ${var} 和 $var
    $s =~ s/\$\{(\w+)\}/exists $cfg{$1} ? $cfg{$1} : ""/ge;
    $s =~ s/\$([A-Za-z_]\w*)/exists $cfg{$1} ? $cfg{$1} : ""/ge;
    return $s;
}

# 条件求值
sub eval_test {
    my $expr = shift;
    $expr = subst($expr);
    # 处理 test 命令常见形式
    return 1 if $expr =~ /^\s*$/;  # 空 = true
    return 0 if $expr =~ /^false/;
    return 1 if $expr =~ /^true/;
    if ($expr =~ /^(\S+)\s*!=\s*(\S*)$/) { return ($1 ne $2) ? 1 : 0; }
    if ($expr =~ /^(\S+)\s*=\s*(\S*)$/) { return ($1 eq $2) ? 1 : 0; }
    if ($expr =~ /^-z\s+(.*)$/) { return length($1) == 0 ? 1 : 0; }
    if ($expr =~ /^-n\s+(.*)$/) { return length($1) > 0 ? 1 : 0; }
    if ($expr =~ /^-d\s+(.*)$/) { return -d $1 ? 1 : 0; }
    if ($expr =~ /^-f\s+(.*)$/) { return -f $1 ? 1 : 0; }
    if ($expr =~ /^-e\s+(.*)$/) { return -e $1 ? 1 : 0; }
    return 1;
}

# 处理脚本
my $output = '';
my $in_heredoc = 0;
my $delim = '';
my @cond_stack = ();  # 条件栈: [parent_skip, current_skip]

for (my $i = 0; $i < @lines; $i++) {
    my $line = $lines[$i];
    my $skip = @cond_stack ? $cond_stack[-1] : 0;

    if ($in_heredoc) {
        my $d = $delim;
        $d =~ s/['"]//g;
        if ($line =~ /^\Q$d\E\s*$/) {
            $in_heredoc = 0;
            next;
        }
        if (!$skip) {
            my $content = $line;
            # 只对非 !NO!SUBS! 块做变量替换
            if ($delim !~ /NO.*SUBS/) {
                $content = subst($content);
            }
            $output .= $content;
        }
        next;
    }

    next if $skip && $line !~ /^\s*(if|fi|else|elif|case|esac)\b/;

    # 条件处理
    if ($line =~ /^\s*if\s+(.*)/) {
        my $r = eval_test($1);
        push @cond_stack, ($skip || !$r) ? 1 : 0;
        next;
    }
    if ($line =~ /^\s*elif\s+(.*)/) {
        pop @cond_stack;
        my $parent = @cond_stack ? $cond_stack[-1] : 0;
        my $r = eval_test($1);
        push @cond_stack, ($parent || !$r) ? 1 : 0;
        next;
    }
    if ($line =~ /^\s*else\s*$/) {
        my $parent = @cond_stack > 1 ? $cond_stack[-2] : 0;
        $cond_stack[-1] = $parent ? 1 : ($cond_stack[-1] ? 0 : 1);
        next;
    }
    if ($line =~ /^\s*(fi|endif)\s*$/) {
        pop @cond_stack if @cond_stack;
        next;
    }

    # case 语句处理（简化：跳过所有 case 块内容，只处理 default 分支 *）
    if ($line =~ /^\s*case\s+.*\s+in\s*$/) {
        push @cond_stack, 0;  # 进入 case，默认不跳过
        next;
    }
    if ($line =~ /^\s*esac\s*$/) {
        pop @cond_stack if @cond_stack;
        next;
    }
    # case 分支模式
    if ($line =~ /^\s*\*\)\s*(.*)/) {
        # default 分支 *)
        my $cmd = $1;
        # 处理 default 分支中的 heredoc
        if ($cmd =~ /<<\s*(\S+)/) {
            $delim = $1;
            $in_heredoc = 1;
            next;
        }
        next;
    }
    if ($line =~ /^\s*[^*]\S*\)\s*(.*)/) {
        # 非默认分支，跳过
        next;
    }

    # 检测 heredoc 开始
    if ($line =~ /<<\s*'?([^\s'\"]+)'?\s*$/) {
        $delim = $1;
        $in_heredoc = 1;
        next;
    }
    # heredoc 可能不在行尾
    if ($line =~ /<<\s*'?([^\s'\"]+)'?/) {
        my $d = $1;
        # 确认这不是变量赋值的一部分
        if ($line =~ />+\s*\$\w+\s*<<\s*$d/ || $line =~ /<<\s*$d\s*$/) {
            $delim = $d;
            $in_heredoc = 1;
            next;
        }
    }
}

# 写入 Makefile
open(my $out, '>', $out_file) or die "Cannot write $out_file: $!";
print $out $output;
close($out);

my $size = length($output);
my $lc = ($output =~ tr/\n//);
print "Makefile: $size bytes, $lc lines\n";
