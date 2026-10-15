# Forks 

This is a staging post for interesting work in the hundreds of forks of SoX.

When a fork's interesting commits have been added to the issues,
its line is deleted from here.

## Root forks

### Sourceforge

The 184 commits by Mans Rullgard on the master branch since sox-14.4.2
are such a hotchpotch of new work, bug fixes,
bug "fixes" that don't fix the bug they meant to,
bug "fixes" that fix non-bugs and change the way it behaves,
code refactorization and reformatting, build system rewrites and
new bugs, some of which make it fail CVEs that sox-14.4.2 passed,
that it can now be considered to be the most extensive and
well-furnished fork of `sox-14.4.2`.

There are [21 forks of it on sourceforge.net](https://sourceforge.net/p/sox/code/forks)

* [sox.sf.net](Fork-sox)
  * [cpaul4bt/sox](https://sourceforge.net/u/cpaul4bt/sox)
  * [sarinmal/sox](https://sourceforge.net/u/sarinmal/sox)
  * [gscelsi/sox](https://sourceforge.net/u/gscelsi/sox)
  * [tng2016/sox](https://sourceforge.net/u/tng2016/sox)
  * [nigkettle/sox](https://sourceforge.net/u/nigkettle/sox)
  * [jimregan/sox](https://sourceforge.net/u/jimregan/sox)
  * [aybeone/sox](https://sourceforge.net/u/aybeone/sox)
  * [dcsdarlan/sox](https://sourceforge.net/u/dcsdarlan/sox)
  * [rayrrr/sox](https://sourceforge.net/u/rayrrr/sox)
  * [janstary/sox](https://sourceforge.net/u/janstary/sox)
  * [flatmax/sox](https://sourceforge.net/u/flatmax/sox)
  * [c72578/sox](https://sourceforge.net/u/c72578/sox)
  * [ra1nb0w/sox](https://sourceforge.net/u/ra1nb0w/sox)
  * [h3nd24/sox](https://sourceforge.net/u/h3nd24/sox)
  * [stevehero/sox](https://sourceforge.net/u/stevehero/sox)
  * [martinwguy/sox](https://sourceforge.net/u/martinwguy/sox)
  * [mthrok/sox](https://sourceforge.net/u/mthrok/sox)
  * [spucrl/sox](https://sourceforge.net/u/spucrl/sox)
  * [joshuaword2/sox](https://sourceforge.net/u/joshuaword2/sox)
  * [genevera/sox](https://sourceforge.net/u/genevera/sox)
  * [hkctkuy/sox](https://sourceforge.net/u/hkctkuy/sox)

### GitHub

#### [Chris Bagwell](https://github.com/cbagwell/sox)

Forked from  3 commits after 14.4.2 with 47 forks:
* [mansr/sox](https://github.com/mansr/sox) 67 commits ahead: DSD/DSF/WSD, ID3, sdm, msvc fixes
  * [damien78/sox](https://github.com/damien78/sox) Build fixes for WIN32; lsx FIFO growth optimization; add 64bit sample to 8x1bit sample SDM conversion
  * [hyphop/sox](https://github.com/hyphop/sox) Add DSD output
  * [ohshitgorillas/sox](https://github.com/ohshitgorillas/sox) Increase limits
  * [pretony/sox](https://github.com/pretony/sox) Add streaming support to DSD
  * [simonefil/sox](https://github.com/simonefil/sox) MacOS compatibility fixes

#### [`dmkrepo/libsox`](https://github.com/dmkrepo/libsox)

Forked from 5 commits after sox.sf.net 14.4.2) with Mac-specific fixes
for Visual Studio

#### [`janstary/sox`](https://github.com/janstary/sox)

Forked from sox.sf.net commit 507b669 (the one after 42b355) with 2 branches:
* `build`: a new `configure` not based on autoconf (much faster!)
* `libsox`: a proper manual page instead of doxygen

## Packages using `libsox`

Apart from appreciating the compliments made, they could also be useful
for testing libsox, ensuring they link and work OK with a new version:
* [lzaf/sox](https://gitlab.com/lzaf/sox) uses libsox to convert/filter sound files calling it from go
* [vitronic/berry-libsox](https://gitlab.com/vitronic/berry-libsox) Berry bindings for libSoX
* [vitronic/lua-libsox](https://gitlab.com/vitronic/lua-libsox) Lua bindings for libSoX
