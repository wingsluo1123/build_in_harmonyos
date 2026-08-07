#!/usr/bin/env perl
use strict;
use warnings;

# Test Mail::Header
use Mail::Header;
my $header = Mail::Header->new;
$header->add('From' => 'test@example.com');
$header->add('Subject' => 'Test message');
my $from = $header->get('From');
die "Mail::Header get failed" unless $from && $from =~ /test\@example\.com/;
print "Mail::Header ok\n";

# Test Mail::Internet
use Mail::Internet;
my $msg = Mail::Internet->new([
    "From: test\@example.com",
    "To: dest\@example.com",
    "Subject: Hello",
    "",
    "This is a test message.",
]);
my $head = $msg->head;
my $subject = $head->get('Subject');
die "Mail::Internet head get failed" unless $subject && $subject =~ /Hello/;
print "Mail::Internet ok\n";

# Test Mail::Address
use Mail::Address;
my $addr = Mail::Address->new('Test User', 'test@example.com');
die "Mail::Address name failed" unless $addr->name eq 'Test User';
die "Mail::Address address failed" unless $addr->address eq 'test@example.com';
print "Mail::Address ok\n";

# Test Mail::Util
use Mail::Util qw(mailaddress);
print "Mail::Util ok\n";

print "All MailTools tests passed\n";
