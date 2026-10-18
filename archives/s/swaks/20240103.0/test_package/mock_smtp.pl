#!/usr/bin/env perl
#
# Minimal SMTP sink for the swaks consumer test.
#
# This is NOT part of the swaks package: it is the test fixture that gives the
# packaged CLI something real to talk to.  It is written against core Perl only
# (IO::Socket::IP with an IO::Socket::INET fallback for the TCP mode), so it
# runs wherever the packaged swaks runs.
#
# Usage:
#   mock_smtp.pl --listen <host>:<port> --ready-file <f> --transcript <f> [--reject-rcpt]
#   mock_smtp.pl --stdio                   --transcript <f> [--reject-rcpt]
#
# * --listen with port 0 lets the OS pick a free port; the chosen port is
#   written to the ready file as "PORT=<n>" so the caller never guesses one.
# * --stdio speaks the same protocol over STDIN/STDOUT for swaks' --pipe
#   transport.
# * Every line received from the client is appended to the transcript file
#   with its CRLF normalised to LF, so the shell test can anchor on whole
#   lines with a portable BRE.
# * --reject-rcpt answers 550 to RCPT TO, which lets the test prove that
#   swaks really reports what the server said.

use strict;
use warnings;

my %opt = (host => '127.0.0.1', port => 0, reject_rcpt => 0, stdio => 0);

while (defined(my $arg = shift @ARGV)) {
    if ($arg eq '--listen') {
        my $value = shift @ARGV;
        defined $value or die "mock_smtp.pl: --listen needs <host>:<port>\n";
        $value =~ /^([^:]+):(\d+)$/ or die "mock_smtp.pl: bad --listen value '$value'\n";
        ($opt{host}, $opt{port}) = ($1, $2);
    }
    elsif ($arg eq '--ready-file')  { $opt{ready}      = shift @ARGV; }
    elsif ($arg eq '--transcript')  { $opt{transcript} = shift @ARGV; }
    elsif ($arg eq '--reject-rcpt') { $opt{reject_rcpt} = 1; }
    elsif ($arg eq '--stdio')       { $opt{stdio} = 1; }
    else { die "mock_smtp.pl: unknown argument '$arg'\n"; }
}
defined $opt{transcript} or die "mock_smtp.pl: --transcript is required\n";

open(my $log, '>', $opt{transcript})
    or die "mock_smtp.pl: cannot write $opt{transcript}: $!\n";
_autoflush($log);

my ($in, $out, $listener);

if ($opt{stdio}) {
    $in  = \*STDIN;
    $out = \*STDOUT;
}
else {
    my $class = _socket_class();
    $listener = $class->new(
        LocalHost => $opt{host},
        LocalPort => $opt{port},
        Listen    => 5,
        ReuseAddr => 1,
    ) or die "mock_smtp.pl: cannot listen on $opt{host}:$opt{port}: $@\n";

    if (defined $opt{ready}) {
        open(my $ready, '>', $opt{ready})
            or die "mock_smtp.pl: cannot write $opt{ready}: $!\n";
        print {$ready} 'PORT=' . $listener->sockport . "\n";
        close($ready);
    }

    $in = $listener->accept() or die "mock_smtp.pl: accept failed: $!\n";
    $out = $in;
}
_autoflush($out);

print {$out} "220 mock-smtp-ohos ESMTP swaks consumer test\r\n";

my $in_data = 0;

while (defined(my $line = <$in>)) {
    my $record = $line;
    $record =~ s/\r\n\z/\n/;
    print {$log} $record;

    my $command = $line;
    $command =~ s/\r?\n\z//;

    if ($in_data) {
        if ($command eq '.') {
            $in_data = 0;
            print {$out} "250 2.0.0 queued as MOCK1\r\n";
        }
        next;
    }

    if ($command =~ /^(EHLO|HELO|LHLO)\b/i) {
        print {$out} "250-mock-smtp-ohos\r\n250-8BITMIME\r\n250 HELP\r\n";
    }
    elsif ($command =~ /^MAIL FROM:/i) {
        print {$out} "250 2.1.0 sender ok\r\n";
    }
    elsif ($command =~ /^RCPT TO:/i) {
        print {$out} $opt{reject_rcpt}
            ? "550 5.1.1 mailbox unavailable\r\n"
            : "250 2.1.5 recipient ok\r\n";
    }
    elsif ($command =~ /^DATA\b/i) {
        print {$out} "354 end data with <CR><LF>.<CR><LF>\r\n";
        $in_data = 1;
    }
    elsif ($command =~ /^RSET\b/i) {
        print {$out} "250 2.0.0 reset\r\n";
    }
    elsif ($command =~ /^NOOP\b/i) {
        print {$out} "250 2.0.0 ok\r\n";
    }
    elsif ($command =~ /^QUIT\b/i) {
        print {$out} "221 2.0.0 bye\r\n";
        last;
    }
    else {
        print {$out} "250 2.0.0 ok\r\n";
    }
}

close($log);
close($in) if !$opt{stdio};
close($listener) if defined $listener;
exit 0;

sub _autoflush {
    my $handle = shift;
    my $previous = select($handle);
    $| = 1;
    select($previous);
    return;
}

sub _socket_class {
    for my $module (qw(IO::Socket::IP IO::Socket::INET)) {
        my $file = $module;
        $file =~ s{::}{/}g;
        $file .= '.pm';
        return $module if eval { require $file; 1 };
    }
    die "mock_smtp.pl: neither IO::Socket::IP nor IO::Socket::INET is loadable\n";
}
