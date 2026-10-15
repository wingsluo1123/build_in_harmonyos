# Distro MXE

MXE is a cross-compilation environment for Linux that creates
Windows executables. It already has a configuration file
to build `sox.exe' from `sox-14.4.2`.

It's just too easy make it build `sox.exe`:
Install the other packages it depends on
(see https://mxe.cc/#requirements) then

    git clone https://github.com/mxe/mxe.git
    cd mxe
    wget -O src/sox_ng.mk https://codeberg.org/sox_ng/sox_ng/releases/download/sox_ng-14.4.5/sox_ng.mk
    make sox_ng

and `sox.exe` will appear, after a long pause, as

    usr/i686-w64-mingw32.static/bin/sox.exe

This has been adapted for `sox_ng`. See issue #65

### FreeBSD

The [Requirements page]() says you need to install `python3`
but you need to install `python`. You also need `zip` and `lzip`
and `pkgconf`.
`p7zip` has gone from FreeBSD so remove the line `7za` from
`Makefile` as well as `unzip` (provided by `zip`).

Use `gmake`, not `make` (which is `dmake`).

## Things for mxe.cc to do

`src/sox.mk` lists as build dependencies:

    $(PKG)_DEPS     := cc file flac lame libltdl libmad libpng libsndfile \
                       opencore-amr opus twolame vorbis wavpack

but that wants to be `opusfile`, not `opus`.

It also wants `libid3tag` and in the configuration section

    --without-id3tag \

wants to be

    --with-id3tag \

See also the bottom of [Distros] about build dependencies.
