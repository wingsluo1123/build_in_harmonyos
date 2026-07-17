# perl-sereal

**Sereal** — Fast, compact, powerful binary (de-)serialization format for Perl.

This is the front-end module that wraps Sereal::Encoder and Sereal::Decoder.
It provides a unified API for serializing and deserializing Perl data structures
using the Sereal binary format.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 5.004-r1 | published | 2026-06-30 |

## Dependencies

- **perl-sereal-encoder/5.004** — XS encoder module (Conan package)
- **perl-sereal-decoder/5.004-r3** — XS decoder module (Conan package)

## Build System

Perl ExtUtils::MakeMaker (Makefile.PL) — pure Perl module, no C/XS code.

## Usage

```bash
# Install via Conan
conan install --requires=perl-sereal/5.004-r1@ohpcd/stable

# Use in Perl
perl -e 'use Sereal qw(encode_sereal decode_sereal); my $enc = encode_sereal({key => "value"}); my $dec = decode_sereal($enc);'
```

## Notes

- .so runtime loading on HMDFS is limited by SELinux (E046)
- Install to system Perl path for runtime usage
- See `5.004-r1/notes.md` for detailed adaptation notes
