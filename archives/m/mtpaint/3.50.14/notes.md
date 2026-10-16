# mtpaint 3.50.14 HarmonyOS PC adaptation notes

Issue: 认领前置 (申请人 momimgya, 队伍 干)
Branch: feat/mtpaint-3.50.14
Target path: archives/m/mtpaint/3.50.14

## Summary

mtPaint 3.50.14 (Mark Tyler's painting program, maintained by Dmitry Groshev)
is a GTK+ painting program for icons and pixel art. Upstream uses a bespoke
mini-configure shell script plus hand-written Makefiles (NOT GNU Autotools).
This recipe configures GTK+3 + release optimizations with jpeg/tiff/lcms2
codecs enabled and JPEG-2000/WebP disabled (registry scope, path A base
adaptation), installs a binary-only package (bin/mtpaint), and verifies it
headless via --version/--help (both exit before gtk_init) plus artifact
checks. Upstream ships no test suite (audited, no_tests precedent).

## Upstream

- Homepage: https://github.com/wjaguar/mtPaint
- Website: http://mtpaint.sourceforge.net
- Version: 3.50.14 (2026-03-05, commit 8304376e8861a8a603371b0f188db30f9cafdc17)
- License: GPL-3.0-only
- Fetch: https://deb.debian.org/debian/pool/main/m/mtpaint/mtpaint_3.50.14.orig.tar.gz
  (fallback https://ftp.debian.org/debian/pool/main/m/mtpaint/mtpaint_3.50.14.orig.tar.gz)
- SHA256: 1062ec6c9fddb5a402b0c22e958f28814cc128428d03e8fa9d71c9982b985256
  (cross-verified: Launchpad 3.50.14-1 page + Debian ACCEPTED tracker message)
- Why Debian URL (R39): SourceForge file hosting is stale (latest asset is
  3.50 from 2021); GitHub wjaguar/mtPaint publishes no release artifact
  (tags page: no releases). The Debian .orig is the upstream 3.50.14 source
  as shipped for 3.50.14-1. Both listed URLs serve the identical file, so one
  sha256 covers the list.

## Build configuration

```
./configure gtk3 release jpeg tiff lcms2 nojp2 nowebp --prefix=/
make -j1
make install DESTDIR=<package_folder>
```

- `gtk3`: registry gtk/3.24.43 (broadway backend, no X11/Wayland).
- `jpeg tiff`: libjpeg-turbo + libtiff support explicitly on.
- `lcms2`: LittleCMS2 color management explicitly on.
- `nojp2 nowebp`: JPEG-2000/WebP off (keeps dep scope to registry codecs).
- freetype: auto-detected (text tool); intl/man off (binary-only package).
- `--prefix=/` → `make install DESTDIR=` lands binary at `bin/mtpaint`.
- R15: --build/--host never passed (mini-configure only uses --host for MinGW).
- R26: not a system-name library (no /lib pollution concern); GUI tool links
  shared (default dynamic, Conan-managed dep chain).
- R32: validate() accepts os in ("Linux", "OHOS").
- R33: no ${CC}/${CFLAGS} in self.run(); compiler comes from conf + isfile
  fallback probe; pkg-config path built from PkgConfigDeps output + host deps.

## Dependencies (all transitive_headers/libs)

- gtk/3.24.43, zlib/1.3.1.1, libpng/1.6.58, libjpeg-turbo/3.2.0,
  libtiff/4.7.2.2, freetype/2.14.3, lcms2/2.19 (无 giflib: 上游 3.50.03
  commit 40bde45 起 GIF 收发已内置, configure 无 gif 探测、src 不链接
  -lgif; 之前直需的 giflib/6.1.3 只会引入非硬化配方在 OHOS 源码构建失败)
  + pixman/0.46.4 (force=True, transitive-only unification:
  conancenter cairo/1.18.4 pulls pixman/0.43.4 vs ohpcd
  cairo-gobject/1.18.4.2 + local cairo/1.18.4 pin 0.46.4)
  + fontconfig/2.18.1.1 (force=True) + expat/2.8.2.1 (force=True):
  cairo-gobject/1.18.4.2 + cairo/1.18.4 + pango/1.50.14.1.1 pin 2.18.1.1
  vs conancenter branch pulling 2.17.1 (cogl/clutter force precedent,
  klavaro coupled expat pin)
  + libtiff/4.7.2 (plain require, converges on ohpcd
  gdk-pixbuf/2.44.6.1's own pin): the published gdk-pixbuf/2.44.6.1
  binary was built against 4.7.2; pinning the newer local 4.7.2.2
  invalidated its package_id ("Main binary package missing" + "No
  compatible configuration found") and forced single-job source
  rebuilds until the preflight SSH session dropped.
- configure(): freetype compression closure (ayatana-ido precedent):
  conancenter freetype wins remote order with with_brotli/bzip2/png/
  harfbuzz/zlib True, pulling cmake leaves (brotli/1.1.0) that fail
  "System is unknown to cmake"; aligned to OHOS freetype's all-no set.
- requirements(): libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc +
  libepoxy/1.5.10#92f7e70c459ed2e6a96cd82549e82391 (override=True,
  ayatana-ido/0.10.4-v2 precedent, RREVs quoted verbatim): glib's bare
  libffi resolves to the CCI recipe (CCI patch
  0008-3.4.4-invalid-CFI-advance_loc.patch) whose configure dies with
  "/data/service/hnp/bin/bash: inaccessible or not found" (Error 127);
  gtk's bare libepoxy exists on both remotes and the CCI one drags a
  meson->ninja tool edge failing with "System is unknown to cmake".
  Same versions, package_id-preserving.
- build_requirements(): tool_requires("pkgconf/3.0.5") + absolute
  $PKG_CONFIG export (xmlsec/1.3.12 precedent): HMBS injects only
  cmake/make/ninja/python3, so the mini-configure's gtk+-3.0/libpng
  probes die with "Failed to find required GTK+3 libraries"; the
  in-repo pkgconf installs no pkg-config alias, hence $PKG_CONFIG
  points at the verified-runnable pkgconf binary outright (candidates
  verified with --version, not isfile: tool bindir, PATH, HNP
  preinstalled fallback).
- generate()/build(): host-deps CPPFLAGS/LDFLAGS injection (yudit/3.1.0
  precedent): the mini-configure handles lcms2/png/jpeg/tiff/z with
  plain `LIB_NAME <lib>` (only -l<lib>, no pkg-config --cflags) and
  bakes $CPPFLAGS/$LDFLAGS into CFLAG/LDFLAG. lcms2 is outside gtk's
  Requires closure, so without this png.c fails with `lcms2.h file not
  found` while gtk/png probes pass. Collected from every host dep via
  cpp_info.aggregated_components() (absolute, dedup, existing dirs).

## Upstream test audit (no_tests)

- Top Makefile targets: all/install/uninstall/clean only.
- src/Makefile targets: all/clean/install/uninstall only.
- No tests/, test/, t/, spec/ dir; no *_test.c/test_*.c; no TEST(/TEST_F,
  def test_, enable_testing/add_test, meson test registration.
- `make check` → "No rule to make target 'check'.  Stop."
- build() runs no upstream suite (upstream_test_in_build: false).
- Evidence: test_package/test.sh prints HMBS_UPSTREAM_TEST_RESULT
  status=no_tests every run; test_package/conanfile.py re-emits it.

## test_package (6 checks, test.sh)

1. `mtpaint --version` — exit 0, non-empty, mentions mtpaint.
2. `mtpaint --help` — exit 0, non-empty, mentions usage.
3. Binary size — file non-empty and > 100KB (rejects truncated install).
4. `--version` re-run — contains exact 3.50.14 (determinism, anti-silent-skip).
5. `readelf -h` — ELF type EXEC/DYN.
6. `readelf -d` — NEEDED entries reference gtk/gdk/glib/libpng/libjpeg/libtiff.
- Markers: HMBS_TEST_PACKAGE_RESULT(discovered=6/passedCount=6 on success) +
  HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0/executed=0).
- Anti-false-pass: every output asserted non-empty; version asserted twice;
  artifact size asserted numerically (toybox-tar lesson).

## R34 compliance

Application package: test_package executes the real installed binary with
real flags (--version/--help) and inspects the real artifact (size/ELF/
NEEDED). No print-only shell test; L1e destructive check applies (binary
removal breaks the run).

## Validation status

- 本轮仅完成未提交工作树 (no commit/push/PR per task rule).
- 待 HMBS 后台真机预检: conan create + rule4 (markers above) + CI.
- 依赖若在真机缺失 (W0), 按门禁反馈补齐版本后重验.

## References

- knowledge: bwm-ng/0.6.3 no_tests precedent (mini shell/TMPDIR/markers),
  gtk/3.24.43 broadway backend notes, ylva/1.7 manual audit format.
- Review rules: .gitcode/review-memory.md (R34/R39/R15/R26/R32/R33),
  .gitcode/code-style.md (shebang/docstring, class name, method order,
  package_type application + bindirs).
