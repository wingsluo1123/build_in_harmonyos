# Terminology

This was supposed to be a list of terms used in SoX but it's
turning into an introduction to how SoX works internally.
The same thing happened to whoever wrote `libsox.3`.

## File formats

A file format is type of audio file, such as `wav`, `aiff` or  `au`,
which usually corresponds to the same file name extension,
though one file format can have several file name extensions,
aush as `3gp` and `3gpp` which are the same.

In the source code, these are present in:

* the list of `names` that a format handler can read and/or write
* the characters after the dot in the name of files that SoX is reading
  or writing;
* the file type auto detection table in `src/formats.c`

and used by

* `sox_find_format()`, to find a format handler for a file according to
  the target file's name

## Encodings

Each File Format is a container for audio data which may be encoded
in different ways. For example, the `wav` format can contain
uncompressed PCM data, A-law, mu-law or even MP3 data and a host of others.

There is more on the page [Formats and Encodings](Formats-and-encodings).

### Internals

All the encodings that SoX can handle are listed in `sox_ng.h` in
the enum `sox_encoding_t` and each Format Handler says which encodings
it can write into the File Formats it handles.

## Format Handlers

A format handler is a code module that can read and/or write
certain file formats.

For the most part, there is a one-to-one correspondence between
file formats, their filename extension, the name of the format handler
and even the source file the handler lives in, such as `flac` and `nsp`,
and most of them read and write that format
but one handler may be able to read several file formats (of which `sndfile`
is the example par excellence) and one file format may be handled by several
different handlers.

### Static format handlers

Most of the format handlers, `wav`, `aiff` and so on, are compiled
into `libsox` and the `sox` program links to them.

### Dynamic format handlers

Others can be built-in or compiled as dynamic libraries
using `./configure --with-flac=dyn` which creates a
separately-installed library file called `libsox_fmt_flac.{a,la,so,dll}`
and `./configure --with-dyn-default` builds all the dynamic format handlers
it can as separate libraries.

The `export-symbols-regex` line in `src/Makefile.am` lists functions
in `libsox` that are called by the dynamic formats.

Debian packages these separately from the `libsox` package so that it could
include free software handlers in the main repository and the patented ones,
`amrnb`, `amrwb` and `mp3`, in the `non-free` repositories.
The idea was also that people dould be able to publish their own
format handlers that could be added to existing SoX installations,
but this seems never to have happened, with LADSPA and VST taking the
high ground in this area.

### Internals

A format handler is created by an `LSX_FORMAT_HANDLE(whatever)` clause
in some source code file. That is a macro, defined in `src/sox_i.h`,
that expands to a function `lsx_whatever_format_fn(void)` which returns
a pointer to a `sox_format_handler_t`, which is a small struct containing,
among a few other things:

* `names`: the list of file formats that it can read or write;

If it can read a file format it will have some of:

* Its `startread` function is handed a `sox_format_t *` and is called
  when the input file has already been opened. It does anything required
  before it starts reading samples, often reading the file's header
  to find out the sample rate, the number of channels and the way data
  are encoded in the rest of the file, and allocating memory.
  It returns SOX_SUCCESS if the file looks and reading can proceed
  or SOX_EOF if not.
* `read` is handed a `sox_format_t *`, a pointer to a buffer of `sox_sample_t`
  and the length of that buffer (in samples, not sample frames).
  The `sox_format_t` contains stuff that `startread` filled in and more,
  which it uses to reads data from the file using the `FILE` pointer therein
  and writes up to `sox_sample_t`s into the buffer it was handed.
  It returns the number of samples that it wrote into the buffer,
  always a multiple of the number of channels.
* `stopread` does anything needed when no more reading is required
  such as freeing any memory that was allocated during `startread`.
  It does not have to close the input file; that is done for it afterwards.
* `seek` repositions the reader to a different point in the input file
  for the next call to its `read` function.

* `startwrite` is similar to `startread` when a file is to be written to;
* `write` is handed a buffer full of SoX samples in the 32-bit signed format
  that SoX uses internally and
* `stopwrite` is called when all samples have been processed, often rewrites
  the length of the file in its header and frees any memory allocated in
  `startwrite`.

Any of these can be `NULL` to say it is not necessary or not supported
but `read` must be non-NULL for it to be considered able to read the
file formats it lists, and `write` to say it can write those formats.

The `read`, `write` and `seek` functions in the format handler's
source file can be called anything in real life as those symbols
are local to the format handler and are only called via the pointers
in the `sox_format_handler_t` whose address the `lsx_*_format_fn` returns.

`src/skelform.c` is a tiny example of a format handler and
details about what is in a `sox_format_t` can be found in `sox_ng.h`
in the description of the `sox_format` structure.

## Effects

Effects are what follow the input and output file names on the SoX
command line, each followed by its own set of parameters.

An effects chain is a sequence of effects, each of whose output feeds
into the input of the following effect.

### Internals

Like the format handlers, each SoX effect is defined by one tiny function that
returns a `sox_effect_handler_t` a pointer to a `sox_effect_handler` structure
containing pointers to the functions that make it work:

* `getopts` is called once at startup to look at the effect's arguments,
   allocates memory that lasts the lifetime of the effect and initializes
   any libraries that it uses;
* `start` is called once per channel before passing data through it;
* `flow` copies samples from input to output, probably modifying them;
* `drain` is called when all audio data has been given to `flow`,
  in case it has any more samples that it hasn't output yet,
* `stop` is called once per channel, and
* `kill` is called just once to shut down any libraries that it used
  and to free memory that was allocated in `getopts`.

Each of these is handed a pointer to a `sox_effect` structure
in which it can find out which channel it is processing (the `flow`),
the total number of channels (in `flows`) and the characteristics
of the input and output signals.

Other goodies in the `sox_effect_handler` are the effect's name,
its help and the logical OR of a number of flags describing how it operates.
There is a full list of them in `sox_ng.h`, but the most interesting ones are:

* `SOX_EFF_CHAN`, `SOX_EFF_RATE` and `SOX_EFF_LENGTH` to say whether it might
  change the number of channels, the sample rate or the length of the audio
  and
* `SOX_EFF_MCHAN` to say that it processes all the channels together,
  in which case `start`, `flow`, `drain` and `stop` are called once per
  audio frame with the samples of the channels interleaved
  (left, right, left, right).
  Otherwise, the four functions are called once per channel, each processing
  a mono signal and these multiple invocations can be done in parallel.

## Effects

A SoX effect is a function that returns the address of a sox_effect_t.

That contains function pointers to the effect's functions::

* getopts
* start
* stop
* drain
* stop
* kilol

I should get a T-Shirt made with those six words on it to see if anyone
ever happens to know what they are!
