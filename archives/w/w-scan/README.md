# w-scan

`w_scan` is a command-line DVB scanner that discovers channels and exports
channel lists or tuning data for VDR, VLC, Xine, MPlayer, dvbscan, XML, and
other consumers.

## OHOS Adaptation

- The upstream release archive contains generated Autotools files, so the recipe
  builds the C sources directly instead of invoking the `version` target. That
  target rewrites `version.h` and `configure.ac` and requires `autoconf`.
- A small CRLF-safe build-time replacement changes `#include <sys/errno.h>`
  to `#include <errno.h>` so the source builds with the OHOS/musl libc.
- The OHOS sysroot supplies the DVB UAPI headers. `iconv` and `clock_gettime`
  are available from the OHOS libc, so the package has no Conan dependencies.

## Dependencies

No external Conan dependencies are required for this release.

## Functional Verification

The upstream 20210218 source tree has no automated test suite and its normal
runtime path requires a DVB frontend device. The consumer test therefore uses
deterministic, hardware-independent CLI paths: version output, basic and
extended help, country and satellite listings, and rejection of an unknown
option. The test does not claim that a real DVB scan was performed.

## References

- https://wirbel.htpc-forum.de/w_scan/index2.html
- https://deb.debian.org/debian/pool/main/w/w-scan/w-scan_20210218.orig.tar.bz2
