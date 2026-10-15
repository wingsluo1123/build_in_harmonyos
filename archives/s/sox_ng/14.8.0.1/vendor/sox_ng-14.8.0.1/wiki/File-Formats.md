# Formats

Audio files come in many formats like `wav`, `mp3` and so on,
and each of these may support different [encodings](Encodings)
inside the file. This article is about the overall formats.

When decoding, SoX recognizes what the format of the audio file is
in `src/formats.c:open_read()` in this order:

* the name passed as `-t` before the input filename
* the filename's extension
* the contents of the file's header, necessary when reading a file with
  no extension, with an unknown extension or from standard input or a pipe
  (the magic contents it knows are listed in `auto_detect_format()` in
  `src/formats.c`)

It looks these up in the `names` field of all the available
[format handlers](Format-Handlers) and uses that format handler
to decode the file. If several format handlers can decode the
same file format, it chooses the first one in its list of handlers,
which are in the order listed in `src/formats.h`:

* first, the always built-in handlers
* then, the handlers that could be [dynamically loaded](Dynamic-Formats)
  but that were built in when the version of SoX in use was compiled
* last, the dynamically-loaded handlers

When encoding, either it must recognize the filename extension or you
must say `-t whatever`, where `whatever` is a filename extension that it knows:
those listed by `sox_ng --help` at the `AUDIO FILE FORMATS:` line.

Note that filename extensions and handler names do not always correspond.
For example, ".amrnb" files are handled by the `amr-nb` handler and
many filename extensions can be handled by the `sndfile` and `ffmpeg`
handlers.
