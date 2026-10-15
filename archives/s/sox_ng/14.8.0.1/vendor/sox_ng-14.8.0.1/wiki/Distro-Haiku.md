# Distro Haiku

Haiku carries 14.4.2 with [a single patch](https://github.com/haikuports/haikuports/tree/master/media-sound/sox/patches)
to make pipe rewinding work the same way as glibc.

## Patches

| Patch | Issue |
| :---- | :---: |
| [Haiku acts like glibc](https://github.com/haikuports/haikuports/blob/master/media-sound/sox/patches/sox-14.4.2.patchset) | #166 |

## Fixes

A couple of fixes to 14.4.3.1 were necessary for Haiku. See issue #140.

## Installation

SoX needs libtool, which Haiku R1/beta4's Live CD installation does not include
and going to `HaikuDepot->libtool->Install` says

    nothing provides libtool_ltdl==2.4.6 needed by libtool-2.4.6-2

so I install `libtool` from source, whose installation needs `help2man`

(gnu.org is down at present, so fill in the wget URLs for the tarballs
or get them from elsewhere)

    PATH=$PATH:$HOME/bin
    CFLAGS=-I$HOME/include
    LDFLAGS=-L$HOME/lib
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/lib
    PKG_CONFIG_PATH=$HOME/lib/pkgconfig
    export PATH CFLAGS LDFLAGS LD_LIBRARY_PATH PKG_CONFIG_PATH

    wget help2man
    tar xf help2man-1.49.3.tar.xz
    cd help2man-1.49.3
    ./configure --prefix=$HOME
    make install
    cd ..

    wget libtool
    tar xf libtool-2.4.7.tar.xz
    cd libtool-2.4.7
    ./configure --prefix=$HOME
    make install
    cd ..

    git clone https://codeberg.org/sox_ng/sox_ng
    cd sox_ng
    autoreconf -i -I $HOME/share/aclocal
    ./configure --prefix=$HOME
    make
    make install
