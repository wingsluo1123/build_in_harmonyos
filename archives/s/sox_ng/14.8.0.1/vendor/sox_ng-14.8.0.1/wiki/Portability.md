# Portability

## Unix

`sox_ng` compiles and `testall.sh` and
[the regression test suite](Testing#regression-tests) succeed on
all of the GCC compile farm
[GCC Compile Farm hosts](https://portal.cfarm.net/machines/list),
that is to say:

### Architectures

#### Succeeded on

* aarch-64le
* arm-64le
* chrp-32be
* mips-64be
* ppc-64be
* ppc-64le
* riscv-64le
* sun4v-64be
* x86-32le
* x86-64le

#### Did not succeed on

* arm-64le (cfarm240):  `configure: machine 'aarch64c-unknown' not recognized`

### Operating Systems

#### Succeeded on

* [AIX](Distro-AIX) 7.4
* AlmaLinux 8.1 (cfarm185 aarch-64le)
  * though build dependencies libid3tag and libmad fail: `configure: error: cannot guess build type; you must specify one`
* AlmaLinux 9.4 (cfarm120 ppc-64le)
* [AlpineLinux](Distro-Alpine)
* [Archlinux](Distro-Arch)
* [CentOS](Distro-CentOS) 7.9 and 8
* [Debian](Distro-Debian) stretch buster bullseye bookworm and trixie
* [FreeBSD](Distro-FreeBSD) 14.1 amd64
* [Haiku](Distro-Haiku) R1/beta5
* MacOS X 12.6
* [OpenBSD 7.5](Distro-OpenBSD)
  * though you must `configure --without-sunaudio`
* OpenSUSE Leap 15.0 and 15.5
* Solaris 11.4
* Ubuntu jammy

#### Did not succeed on

[NetBSD](Distro-NetBSD) 64-bit:

    checking build system type... Invalid configuration `mipsn64eb-unknown-netbsd10.1': machine `mipsn64eb-unknown' not recognized
    configure: error: /bin/sh ./config.sub mipsn64eb-unknown-netbsd10.1 failed

[CheriBSD]

    checking build system type... Invalid configuration `aarch64c-unknown-freebsd15.0': machine `aarch64c-unknown' not recognized

## Haiku

Works the Unix way; unusual as it uses `gcc-2.95`.

## Mac OS X

Works the Unix way and also using `homebrew`. See issue #122.

## Minix

Needs a Minix system to test on. Issue #141.

## MS/DOS

Haven't tried yet. Issue #147.

## Windows

Works cross-compiling with `mxe`. See issue #65.
