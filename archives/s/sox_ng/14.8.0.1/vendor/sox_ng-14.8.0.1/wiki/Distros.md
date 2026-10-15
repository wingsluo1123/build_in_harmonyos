# Distros

About 50 non-derivative software distributions package `sox` either
from 14.4.2 with different selections of patches or
from commit 42b355 with a different array of patches.

We add Debian derivative Ubuntu because it may have different patches
and has a separate, well-nourished issue tracker.

If there is a page of distro-specific notes, the link on the distro name
in the following table will take you to it;
distro-generic notes are after the table.

## Distros that package sox_ng

Last updated from [Repology](https://repology.org/project/sox/versions) on 2025-11-15

| Distro | Pages | Version | Notes |
| :----- | :---- | :------ | :---- |
| [ArchLinux](Distro-Arch) | [Package](https://archlinux.org/packages/extra/x86_64/sox) | 14.6.1.2 |
| ArchPOWER | [`powerpc` package list](https://repo.archlinuxpower.org/base/powerpc) | 14.6.0.4 |
| Artix | [Package page](https://packages.artixlinux.org/packages/world/x86_64/sox) | 14.6.1.2 |
| AUR | [sox-ng-git](https://aur.archlinux.org/packages/sox-ng-git) | 14.5.0.2 |
| [Debian](Distro-Debian) | [Package](http://packages.debian.org/sox)<BR>[Patches](https://sources.debian.org/patches/sox/14.4.2+git20190427-3.5/)<BR>[Bugs](https://bugs.debian.org/cgi-bin/pkgreport.cgi?src=sox)<BR>[Mailing list](https://lists.debian.org/cgi-bin/search?P=sox&B=Gdebian-multimedia) | debian-multimedia@lists.debian.org | 14.7.1 in testing and unstable,<BR>which migrates to stable in mid 2027 |
| [Gentoo](Distro-Gentoo) | [ebuilds](https://gitweb.gentoo.org/repo/gentoo.git/tree/media-sound/sox) | 14.4.4.1<BR>14.7.0.9 |
| [Haiku](Distro-Haiku) | [Recipe](https://github.com/haikuports/haikuports/blob/master/media-sound/sox/sox_ng-14.5.0.3.recipe) | 14.5.0.3 |
| [Homebrew](Distro-Homebrew) | [Package](https://formulae.brew.sh/formula/sox_ng) | 14.6.1.2<BR>HEAD | Package is `sox_ng` |
| [KaOS](Distro-KaOS) | [Package](https://kaosx.us/packages/view.php?name=main/sox-14.6.1.2-1) | 14.6.1.2 | Still says Upstream URL: https://sox.sourceforge.net/ |
| LiGurOS | [Repository](https://gitlab.com/liguros/liguros-repo/-/tree/stable/media-sound/sox)| 14.4.4.1<BR>14.6.0.4 |
| Manjaro | [Packages](https://manjaristas.org/branch_compare?q=sox) | Stable: 14.6.0.4<BR>Testing: 14.6.1.2 | For `x64` and `arm` |
| [MSYS2 mingw](Distro-MSYS2) | [Package](https://packages.msys2.org/packages/mingw-w64-clang-x86_64-sox-ng) | 14.6.1.2 | Package is `sox-ng` |
| [OpenBSD](Distro-OpenBSD) | [Package](https://openports.pl/path/audio/sox) | 14.4.4 with [1 patch](https://github.com/openbsd/ports/blob/5c3f631f433c1322275260c68f788499cf3d7663/audio/sox/patches/patch-src_formats_c) replacing wget with ftp | Still says WWW: https://sox.sourceforge.net/ |
| OpenMandriva | [Package](https://github.com/OpenMandrivaAssociation/sox)<BR>[Issues](https://github.com/OpenMandrivaAssociation/distribution/issues?q=is%3Aissue%20sox) | 14.6.0.4 |
| [OpenWrt](Distro-OpenWrt) | [Package](https://openwrt.org/packages/pkgdata/sox)<BR>[Git tree](https://github.com/openwrt/packages/tree/master/sound/sox)<BR>[Patches](https://github.com/openwrt/packages/tree/master/sound/sox/patches) | 14.5.1.1 | Package is `sox_ng` |
| Parabola | [Package](https://www.parabola.nu/packages/?q=sox) | 14.6.1.2 |
| pkgsrc | [Package](https://pkgsrc.se/audio/sox_ng) | 14.6.0.2 | Package is `sox_ng` |
| [Rosa](Distro-Rosa) | [Package](https://abf.io/import/sox) | 14.5.0 |
| Solus | [Package](https://github.com/getsolus/packages/tree/main/packages/s/sox_ng/) | 14.6.1.2 | Package is `sox_ng` |
| stal/IX dev | [Package](https://github.com/stal-ix/ix/tree/main/pkgs/bin/sox) | 14.6.1.2 |
| [T2 SDE](Distro-T2SDE) | [Package](http://t2sde.org/packages/sox) | 14.6.1.2 |
| [Tribblix](Distro-Tribblix) | [Release notes for 0m37](http://tribblix.org/Changes/changes-in-0m37.html) | "14.4.4.0" |

and some distros' packages are [mirrored](https://mirror1.sox.rs) by the [Serbian Open eXchange](https://www.sox.rs/sr)!

## Distros that package sox

    Legend
    14.4.2  Last release of sox.sf.net from 2015-02-22
    42b355  Tip of the sox.sf.net repo on 2021-05-09

| Distro | Pages | Maintainers | Notes |
| :----- | :---- | :---------- | :---- |
| [80x24](Distro-80x24) | [Package](https://80x24.org/sox.git) | Eric Wong <normalperson@yhbt.net> and others | 14.4.2 with many commits, patches and branches |  
| [Alpine Linux](Distro-Alpine) | [Packages](https://pkgs.alpinelinux.org/packages?name=sox)<BR>[Patches](https://git.alpinelinux.org/aports/tree/community/sox) | Natanael Copa | 14.4.2 with 19 patches |
| [ALT Linux](Distro-ALTLinux) | [Package](https://packages.altlinux.org/en/sisyphus/srpms/sox)<BR>[Specfiles](https://packages.altlinux.org/en/sisyphus/srpms/sox/specfiles) | ded (Andrey Kovalev) | 14.4.2 with 26 patches: 19 CVEs & 6 bug fixes from Debian and one build system fix |
| [buildroot](Distro-buildroot) | [Patches](https://git.busybox.net/buildroot/tree/package/sox) | Last patch is from fontaine.fabrice@gmail.com | sox.sf.net commit 752416 (2021-02-01=42b355^) with 5 build system fixes |
| [CentOS](Distro-CentOS) | [Package](https://git.centos.org/rpms/sox)<BR>[Patches](https://git.centos.org/rpms/sox/blob/c7/f/SOURCES) |  | 14.4.1 with three patches |
| [CRUX](Distro-CRUX) | [Package](https://crux.nu/ports/crux-3.6/contrib/sox) | | 42b355 with one build system fix |
| [cygwin](Distro-cygwin) | [Package](https://cygwin.com/packages/summary/sox-src.html)<BR>[Commits](https://cygwin.com/cgit/cygwin-packages/sox)<BR>[Patches](https://cygwin.com/cgit/cygwin-packages/sox/tree) | ORPHANED | 14.4.2 with patches from fedoraproject |
| Exherbo | [Package](https://summer.exherbolinux.org/packages/media-sound/sox/index.html) | | 14.4.2 with no patches |
| [Fedora](Distro-Fedora) | [Package](https://packages.fedoraproject.org/pkgs/sox)<BR>[Patches](https://src.fedoraproject.org/rpms/sox/tree/rawhide)<BR>[Issues](https://bugzilla.redhat.com/buglist.cgi?component=sox) | The last committer is Florian Weimer <fweimer@redhat.com> | 14.4.2 with 13 patches |
| [Fink](https://www.finkproject.org) | [Package](https://pdb.finkproject.org/pdb/package.php/sox)<BR>[Info-File](https://raw.githubusercontent.com/fink/fink-distributions/refs/heads/master/10.9-libcxx/stable/main/finkinfo/sound/sox3-shlibs.info) | Hanspeter Niederstrasser <nieder@users.sourceforge.net> | 14.4.2 taken from Ubuntu with the Debian patches |
| [FreeBSD](Distro-FreeBSD) | [Package](https://www.freshports.org/audio/sox)<BR>[Patches](https://codeberg.org/FreeBSD/freebsd-ports/src/branch/main/audio/sox/files) | dnelson@allantgroup.com | gentoo's distfile of 42b355 with 2 patches: ["Fix man page"](https://cgit.freebsd.org/ports/commit/?id=0613b0fd68faf2d13925745831b046ed306dbbb8) and "src/output.c:flow()" |
| GNU Guix | [Package](https://packages.guix.gnu.org/packages/sox/14.4.2/)<BR>[Issues](https://issues.guix.gnu.org/search?query=sox%2014.4.2%20is:open) | | 14.4.2 with no patches. No issue is relevant. |
| Gobolinux | [Recipe](https://github.com/gobolinux/Recipes/blob/master/Sox/14.4.2/Recipe) | Hisham Muhammad <hisham@gobolinux.org> | 14.4.2 with no patches |
| [Macports](Distro-Macports) | [Package and Issues](https://ports.macports.org/port/sox/details/)<BR>[Portfile](https://github.com/macports/macports-ports/blob/master/audio/sox/Portfile)<BR>[Patches](https://github.com/macports/macports-ports/tree/master/audio/sox/files) | No maintainer | 14.4.2 with 2 patches |
| Mageia | [Package](http://sophie.zarb.org/rpms/105748d9b69c7cca6fb7015e9d2337fa/files)<BR>[Patches and RPM spec](http://sophie.zarb.org/rpms/105748d9b69c7cca6fb7015e9d2337fa/files) | zezinho | "sox-20200117.tar.xz" snapshot with 7 CVE patches from Debian |
| [MXE](Distro-MXE) | [Makefile](https://github.com/mxe/mxe/blob/master/src/sox.mk) [patch](https://github.com/mxe/mxe/blob/master/src/sox-1-fixes.patch) | Last commit by [mabrand](https://github.com/mabrand) | 14.4.2 with one patch |
| [NetBSD](Distro-NetBSD) | [Package](https://pkgsrc.se/audio/sox)<BR>[Patches](http://cvsweb.netbsd.org/bsdweb.cgi/pkgsrc/audio/sox/patches/) | | Appears to be 14.4.2 with 5 patches and some translations in the spec file |
| [NixOS](Distro-NixOS) | [Package](https://search.nixos.org/packages?show=sox) | Marc Weber <marco-oweber@gmx.de> | Based on 42b355 with patch [0001-musl-rewind-pipe-workaround](https://github.com/NixOS/nixpkgs/commit/42e689e5bddb852801bd1fd8acb11ceab758f67c)
| nixpkgs | [Package](https://github.com/NixOS/nixpkgs/tree/release-24.05/pkgs/applications/misc/audio/sox) | | As for NixOS |
| [OpenEmbedded](Distro-OpenEmbedded) | [Package & patches](https://layers.openembedded.org/layerindex/recipe/2270)<BR>[Recipe](https://git.openembedded.org/meta-openembedded/tree/meta-multimedia/recipes-multimedia/sox/sox_14.4.2.bb?h=master) | Koen Kooi koen@dominion.thruhere.net | sox-14.4.2 with 3 patches |
| [OpenEuler](Distro-OpenEuler) | [Package and patches](https://gitee.com/src-openeuler/sox/tree/openEuler-23.09/) | | sox-14.4.2.0.modified with 11 patches |
| [OpenIndiana](Distro-OpenIndiana) | [Package](https://github.com/OpenIndiana/oi-userland/tree/7942b0829973c7a732d67ca3e0bb240679fac40e/components/multimedia/sox)<BR>[Patches](https://github.com/OpenIndiana/oi-userland/tree/7942b0829973c7a732d67ca3e0bb240679fac40e/components/multimedia/sox/patches) | | 14.4.2 with 3 patches |
| openmamba | [Package](https://openmamba.org/en/packages/?tag=base&pkg=sox.source) | silvan | 14.4.2 apparently with no patches |
| [OpenSUSE](Distro-OpenSUSE) | [Package](https://packagehub.suse.com/packages/sox/)<BR>[Patches](https://packagehub.suse.com/packages/sox/14_4_2-bp155_3_3_1) | packagehub@suse.com | 14.4.2 with 19 CVE patches |
| OS4DEPOT | [Package](http://os4depot.net/index.php?function=showfile&file=audio/convert/sox.lha) | Submitter: Matthias Muench | 14.2.0 |
| Pisi Linux | [Package](https://github.com/pisilinux/main/tree/master/multimedia/sound/sox) | admins@pisilinux.org | Git snapshot? Last updated 2020-02-03 |
| [PLD Linux](Distro-PLDLinux) | [Package](https://git.pld-linux.org/?p=packages/sox.git)<BR>[Patches](https://git.pld-linux.org/?p=packages/sox.git;a=tree) | Last commits by Jan Palus <atler@pld-linux.org> and Jakub Bogusz <qboosh@pld-linux.org> | 14.4.2 with 3 patches |
| PureOS | [Package](https://software.pureos.net/package/src/pureos/landing/sox) | Maintainer: debian-multimedia@lists.debian.org<BR>Uploaders: Dennis Braun <d_braun@kabelmail.de>, Jaromír Mikeš <mira.mikes@seznam.cz> | sox_14.4.2+git20190427 Debian derivative with Debian's 28 patches |
| [Red Hat](Distro-RedHat) | [Bugs](https://bugzilla.redhat.com/buglist.cgi?component=sox) | Jiri Kucera <jkucera@redhat.com> | sox-14.4.2 with some patches |
| Scoop | [sox.json](https://github.com/ScoopInstaller/Main/blob/master/bucket/sox.json) | | 14.4.2 |
| Slackware | [Page](https://packages.slackware.com/?r=slackware-current&p=sox-14.4.2-i586-9.txz) | | Couldn't find the source. Seems plain 14.4.2 |
| SliTaz | [Package](https://pkg.slitaz.org/?info=sox) | Pascal Bellard <pascal.bellard​@slitaz.org> | 14.4.2 |
| Spack | [Package](https://packages.spack.io/package.html?name=sox) | sox is looking for a maintainer! | 14.4.2 |
| [Termux](Distro-Termux) | [Package](https://github.com/termux/termux-packages/tree/858771625/packages/sox) | "@termux" | 14.4.2 with 1 patch for Android |
| Trisquel | [Package](https://packages.trisquel.org/source/aramo-security/sox)<BR>[ChangeLog](https://packages.trisquel.org/changelogs/pool/main/s/sox/sox_14.4.2+git20190427-2/changelog) | It says that the maintainer is Ubuntu Developers | Seems to be a copy of Debian or Ubuntu |
| Ubuntu | [Package](https://packages.ubuntu.com/source/noble/sox)<BR>[ChangeLog](https://changelogs.ubuntu.com/changelogs/pool/universe/s/sox/sox_14.4.2+git20190427-4build4/changelog)<BR>[Bug reports](https://launchpad.net/ubuntu/+source/sox/+bugs) | Ubuntu Developers ubuntu-devel-discuss@lists.ubuntu.com | Debian derivative, maybe with extra patches |
| VoidLinux | [Package](https://github.com/void-linux/void-packages/tree/master/srcpkgs/sox) | Leah Neukirchen <leah@vuxu.org> | 14.4.2 with one patch #67  |

## Distros that do not package SoX

| Distro | Pages | Maintainers | Notes |
| :----- | :---- | :---------- | :---- |
| [AIX](Distro-AIX) | - | - | |
| [MINIX](Distro-MINIX) | - | info@minix3.org | |  

### Sources

* [Software distributions on Repology that package sox](https://repology.org/projects/sox)
* [Software distributions on pkgs.org that package sox](https://pkgs.org/search/?q=sox)

## `sox_ng` compared to `sox.sf.net`

### CVEs and bugs are fixed

`sox_ng` is a hard fork of `sox-14.4.2` including all the
Debian and Fedora patches with more successful fixes for some of the CVEs,
fixes all the unaddressed CVEs and more bug fixes from the distros.

There is [a regression test suite](https://codeberg.org/sox_ng/sox_ng/src/branch/main/test)
that runs SoX against a collection of the test files from CVEs and bug reports

For a summary of how `sox-14.4.2`, `sox.sf.net`, Debian and `sox_ng` fare,
see [Testing](Testing).

### Copyright is now regular

The copyright status of SoX was a mess (see [Copyright](Copyright))
but in `sox_ng` it has been sorted out
thanks to input from the FSF's legals
and to confirmations from dodgy files' original authors.

The package as a whole is GPLv2
because `src/opus.c` is based on `oggdec.c` which is GPLv2-only
but individual source files retain their more permissive,
GPLv2-compatible licences.

### Regular releases

`sox_ng` has time-based releases.
The first micro release with bug fixes happened on 18 August 2024
and the first minor release with new features on 18 October 2024,
with a following six-monthly cycle for each.

### "Upgrading" from `42b355`

If your distro opted for basing its package on the 2021 top of the `sox.sf.net`
git tree (affectionately known as 42b355), your users may lose some features
if you move to the first `sox_ng` micro release.
Other than bug fixes and changes and better input validation,
the only ones I am aware of are:
- `spectrogram -n` flag to normalize the brightness
- `spectrogram`: remove height limit of 8193 pixels
- Handle 192k sample rates in RIAA files
- Allow `combine` to merge a single file
- Handling of ID3 tags in more formats
- `WAV` files: allow the number of "valid bits" to be less than the sample size

### Extra build dependencies and package recommendations

From 14.5, it can use `fftw3` and `speexdsp` (which may also need `speex`)

SoX includes the source code for `libgsm`, `lpc10` and (since 14.6) `libdolbyb`.

* `libgsm` is now widespread in distros, so you can include it as a dep;
  this also applies to the original `sox` which autodetects its presence;
* [`libdolbyb`](https://codeberg.org/sox_ng/libdolbyb) was first released
  in early 2025 so you may wish to package that separately and include it
  as a builddep of `sox_ng`;
* [`lpc10`](https://github.com/jafingerhut/lpc10) doesn't have `.tar.gz`
  source releases yet, only `git clone`.

To be able to read URLs, your package should "recommend" installing

* 14.4: `wget`
* 14.5: `wget` or, if configured with `--with-curl`, `curl`.
* 14.6: `wget` or `wget2` or `curl`

For it to be able to launch `ffmpeg` on a pipe to be able to read
dozens more audio (and video!) formats, you will want to "recommend" `ffmpeg`

* 14.5: if configured `--with-ffmpeg`
* 14.6: if not configured `--without-ffmpeg`

It's not fatal if these aren't found at runtime; it just can't read
the extra filetypes.

### Replacing `sox` is optional

`sox_ng` installs as `sox_ng`, `{soxi,play,rec}_ng`, `sox_ng.h`,
`libsox_ng.{a,la,so}`, `sox_ng.pc` and similarly for the manual pages
but if you `./configure --enable-replace` it also makes links
`sox`, `play`, `sox.h` and so on so that other programs find
what they are used to.

According to your distro's norms, you may prefer to enable these links
and make it supplant the original `sox` (a "conflicting alternative")
or you may prefer to use your distro's "alternatives" mechanism
so that users can choose which to use.
