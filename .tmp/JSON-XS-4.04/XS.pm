=head1 NAME

JSON::XS - JSON serialising/deserialising, done correctly and fast

=encoding utf-8

JSON::XS - 正しくて高速な JSON シリアライザ/デシリアライザ
           (http://fleur.hio.jp/perldoc/mix/lib/JSON/XS.html)

=head1 SYNOPSIS

 use JSON::XS;

 # exported functions, they croak on error
 # and expect/generate UTF-8

 $utf8_encoded_json_text = encode_json $perl_hash_or_arrayref;
 $perl_hash_or_arrayref  = decode_json $utf8_encoded_json_text;

 # OO-interface

 $coder = JSON::XS->new->ascii->pretty->allow_nonref;
 $pretty_printed_unencoded = $coder->encode ($perl_scalar);
 $perl_scalar = $coder->decode ($unicode_json_text);

 # Note that JSON version 2.0 and above will automatically use JSON::XS
 # if available, at virtually no speed overhead either, so you should
 # be able to just:
 
 use JSON;

 # and do the same things, except that you have a pure-perl fallback now.

=head1 DESCRIPTION

This module converts Perl data structures to JSON and vice versa. Its
primary goal is to be I<correct> and its secondary goal is to be
I<fast>. To reach the latter goal it was written in C.

See MAPPING, below, on how JSON::XS maps perl values to JSON values and
vice versa.

=head2 FEATURES

=over

=item * correct Unicode handling

This module knows how to handle Unicode, documents how and when it does
so, and even documents what "correct" means.

=item * round-trip integrity

When you serialise a perl data structure using only data types supported
by JSON and Perl, the deserialised data structure is identical on the Perl
level. (e.g. the string "2.0" doesn't suddenly become "2" just because
it looks like a number). There I<are> minor exceptions to this, read the
MAPPING section below to learn about those.

=item * strict checking of JSON correctness

There is no guessing, no generating of illegal JSON texts by default,
and only JSON is accepted as input by default (the latter is a security
feature).

=item * fast

Compared to other JSON modules and other serialisers such as Storable,
this module usually compares favourably in terms of speed, too.

=item * simple to use

This module has both a simple functional interface as well as an object
oriented interface.

=item * reasonably versatile output formats

You can choose between the most compact guaranteed-single-line format
possible (nice for simple line-based protocols), a pure-ASCII format
(for when your transport is not 8-bit clean, still supports the whole
Unicode range), or a pretty-printed format (for when you want to read that
stuff). Or you can combine those features in whatever way you like.

=back

=cut

package JSON::XS;

use common::sense;

our $VERSION = '4.04';
our @ISA = qw(Exporter);

our @EXPORT = qw(encode_json decode_json);

use Exporter;
use XSLoader;

use Types::Serialiser ();

=head1 FUNCTIONAL INTERFACE

The following convenience methods are provided by this module. They are
exported by default:

=over

=item $json_text = encode_json $perl_scalar

Converts the given Perl data structure to a UTF-8 encoded, binary string
(that is, the string contains octets only). Croaks on error.

This function call is functionally identical to:

   $json_text = JSON::XS->new->utf8->encode ($perl_scalar)

Except being faster.

=item $perl_scalar = decode_json $json_text

The opposite of C<encode_json>: expects a UTF-8 (binary) string and tries
to parse that as a UTF-8 encoded JSON text, returning the resulting
reference. Croaks on error.

This function call is functionally identical to:

   $perl_scalar = JSON::XS->new->utf8->decode ($json_text)

Except being faster.

=back


=head1 A FEW NOTES ON UNICODE AND PERL

Since this often leads to confusion, here are a few very clear words on
how Unicode works in Perl, modulo bugs.

=over

=item 1. Perl strings can store characters with ordinal values > 255.

This enables you to store Unicode characters as single characters in a
Perl string - very natural.

=item 2. Perl does I<not> associate an encoding with your strings.

... until you force it to, e.g. when matching it against a regex, or
printing the scalar to a file, in which case Perl either interprets your
string as locale-encoded text, octets/binary, or as Unicode, depending
on various settings. In no case is an encoding stored together with your
data, it is I<use> that decides encoding, not any magical meta data.

=item 3. The internal utf-8 flag has no meaning with regards to the
encoding of your string.

Just ignore that flag unless you debug a Perl bug, a module written in
XS or want to dive into the internals of perl. Otherwise it will only
confuse you, as, despite the name, it says nothing about how your string
is encoded. You can have Unicode strings with that flag set, with that
flag clear, and you can have binary data with that flag set and that flag
clear. Other possibilities exist, too.

If you didn't know about that flag, just the better, pretend it doesn't
exist.

=item 4. A "Unicode String" is simply a string where each character can be
validly interpreted as a Unicode code point.

If you have UTF-8 encoded data, it is no longer a Unicode string, but a
Unicode string encoded in UTF-8, giving you a binary string.

=item 5. A string containing "high" (> 255) character values is I<not> a UTF-8 string.

It's a fact. Learn to live with it.

=back

I hope this helps :)


=head1 OBJECT-ORIENTED INTERFACE

The object oriented interface lets you configure your own encoding or
decoding style, within the limits of supported formats.

=over

=item $json = new JSON::XS

Creates a new JSON::XS object that can be used to de/encode JSON
strings. All boolean flags described below are by default I<disabled>
(with the exception of C<allow_nonref>, which defaults to I<enabled> since
version C<4.0>).

The mutators for flags all return the JSON object again and thus calls can
be chained:

   my $json = JSON::XS->new->utf8->space_after->encode ({a => [1,2]})
   => {"a": [1, 2]}

=item $json = $json->ascii ([$enable])

=item $enabled = $json->get_ascii

If C<$enable> is true (or missing), then the C<encode> method will not
generate characters outside the code range C<0..127> (which is ASCII). Any
Unicode characters outside that range will be escaped using either a
single \uXXXX (BMP characters) or a double \uHHHH\uLLLLL escape sequence,
as per RFC4627. The resulting encoded JSON text can be treated as a native
Unicode string, an ascii-encoded, latin1-encoded or UTF-8 encoded string,
or any other superset of ASCII.

If C<$enable> is false, then the C<encode> method will not escape Unicode
characters unless required by the JSON syntax or other flags. This results
in a faster and more compact format.

See also the section I<ENCODING/CODESET FLAG NOTES> later in this
document.

The main use for this flag is to produce JSON texts that can be
transmitted over a 7-bit channel, as the encoded JSON texts will not
contain any 8 bit characters.

  JSON::XS->new->ascii (1)->encode ([chr 0x10401])
  => ["\ud801\udc01"]

=item $json = $json->latin1 ([$enable])

=item $enabled = $json->get_latin1

If C<$enable> is true (or missing), then the C<encode> method will encode
the resulting JSON text as latin1 (or iso-8859-1), escaping any characters
outside the code range C<0..255>. The resulting string can be treated as a
latin1-encoded JSON text or a native Unicode string. The C<decode> method
will not be affected in any way by this flag, as C<decode> by default
expects Unicode, which is a strict superset of latin1.

If C<$enable> is false, then the C<encode> method will not escape Unicode
characters unless required by the JSON syntax or other flags.

See also the section I<ENCODING/CODESET FLAG NOTES> later in this
document.

The main use for this flag is efficiently encoding binary data as JSON
text, as most octets will not be escaped, resulting in a smaller encoded
size. The disadvantage is that the resulting JSON text is encoded
in latin1 (and must correctly be treated as such when storing and
transferring), a rare encoding for JSON. It is therefore most useful when
you want to store data structures known to contain binary data efficiently
in files or databases, not when talking to other JSON encoders/decoders.

  JSON::XS->new->latin1->encode (["\x{89}\x{abc}"]
  => ["\x{89}\\u0abc"]    # (perl syntax, U+abc escaped, U+89 not)

=item $json = $json->utf8 ([$enable])

=item $enabled = $json->get_utf8

If C<$enable> is true (or missing), then the C<encode> method will encode
the JSON result into UTF-8, as required by many protocols, while the
C<decode> method expects to be handed a UTF-8-encoded string.  Please
note that UTF-8-encoded strings do not contain any characters outside the
range C<0..2