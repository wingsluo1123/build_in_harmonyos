# Distro OpenBSD

`OpenBSD` bases its SoX on `sox.sf.net` commit `42b355` with 7 patches

## Links

* [Package page](https://openports.pl/path/audio/sox)

## Patches

    Legend
    -  Not required

| Patch | Issue |
| :---- | :---: |
| `Update to latest commit (20210509) This fixes following CVEs:` | - |
| `CVE-2019-13590` | #20 |
| `CVE-2019-8357` | #19 |
| `CVE-2019-8356` | #18 |
| `CVE-2019-8355` | #17 |
| `CVE-2019-8354` | #15 |
| `CVE-2017-18189` | #14 |
| `CVE-2017-15642` | #13 |
| `CVE-2017-15372` | #12 |
| `CVE-2017-15371` | #11 |
| `CVE-2017-15370` | #16 |
| `CVE-2017-11359` | #9 |
| `CVE-2017-11358` | #8 |
| `CVE-2017-11332` | #7 |
| `fix man page` | #250 |
| `opus: bump consumers after update to 1.4` | - |
| `Update WWW to use HTTPS for sourceforge.net projects` | - |
| `pulseaudio: Update to 16.1` | - |
| `Move man to share/man` | - |
| `libid3tag: Bump PORTREVISION of dependent ports for shlib change` | - |

In the post [backport CVE fixes audio/sox](https://www.mail-archive.com/ports%40openbsd.org/msg107748.html):

| Patch | Issue |
| :---- | :---: |
| `mirror git checkout as a release tarball` | - |
| `bump library minor to 4.1 because of addition of symbols` | - |
| `remove iconv from WANTLIB and LIB_DEPENDS as reported by make port-lib-depends-check` | - |
| `rename CONFIGURE_ARGS` | - |
| `compile extras target during do-test` | - |
| `remove upstreamed patches` | - |

And `sox_ng` already has a fix for:

| Patch | Issue |
| :---- | :---: |
| `sndio: handle 24-bit samples properly on OpenBSD` | #143 |

## Build dependencies

### With the package manager

    pkg_add libogg flac libvorbis opus opusfile mpg123 lame twolame wavpack libid3tag gsm png opencore-amr

See also the notes at the bottom of [Distros](Distros) about build dependencies
and recommended packages.

### Manual installation

#### opus

On OpenBSD 7.5 (cfarm220) you have to remove the first four lines
of `Makefile.am", run `automake` and `configure --disable-dependency-tracking`

It then dies saying

    make: don't know how to make -msse4.1

#### opusfile

Fails because `libopus` is not installed.

## Compiling sox_ng

You have to `./configure --without-sunaudio`
otherwise compilation fails saying

    sox_ng.c: error: use of undeclared identifier 'audio_info_t'
    sox_ng.c:1326:37: error: use of undeclared identifier 'AUDIO_SETINFO'

Issue #121

In a custom installation with the build dependencies installed under $HOME,
`configure` failed to find libpng, so there were no spectrograms.

In a standard installation of OpenBSD 7.6 I had to say:

    ldconfig /usr/local/lib

as root before almost anything would work.

## Other build dependencies and runtime dependencies

See the bottom of [Distros](Distros) about build dependencies and
package recommendations.
