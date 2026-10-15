# pathChirp 2.4.1 HarmonyOS PC adaptation

## Source and dependency evidence

Original Rice University release: http://www.spin.rice.edu/Software/pathChirp/pathchirp-2.4.1.tar.gz.
The 64,353-byte original archive is retained by the FreeBSD official distcache, with SHA256 independently recorded at https://cgit.freebsd.org/ports/tree/benchmarks/pathchirp/distinfo.
No third-party build/runtime libraries are required: system C/POSIX sockets and libm only.

Source URL exception: the upstream HTTPS endpoint fails its TLS connection, and the FreeBSD distcache HTTPS certificate fails hostname verification on both Windows and the HarmonyOS device. Additional official distribution mirrors return 404. The recipe therefore uses the FreeBSD HTTP original-release cache with the independently verified pinned SHA256. TLS verification was never disabled. PF7's HTTP source finding is explicitly disclosed in the PR; no personal fork, binary download or downstream repack is used.

## Build

Native HarmonyOS 6.0 AArch64, Clang 15; both Conan profiles are ci/conan/profiles/ohos-aarch64. Build the exact source groups in the upstream Makefile with GNU89 inline semantics. Package all three executable programs and upstream documentation/licenses. The distributed config.h uses the portable gettimeofday timestamp fallback; no claim of kernel SO_TIMESTAMP support or privileged realtime scheduling.

## Portability patch

Upstream pathchirp_run sends exactly 100 bytes of colon-separated parameters, including argv[0]. Conan's absolute installed program path consumes most of that frame: the receiver silently uses the default UDP port, causing an empty estimate file. Send the full NUL-terminated frame, handle partial TCP writes/reads and reject a receiver frame larger than its buffer. This is a POSIX fix, without injected platform macros.

## Upstream test inventory

The original archive contains 13 C source files, zero test directories, zero test scripts, zero check/test targets and zero formal upstream cases. README describes a three-program manual experiment. Three delivered programs are not three upstream test cases. The upstream suite pass rate is not applicable.

## Consumer tests

Two separately named cases in test_package/test.py, both invoked from Conan test():
1. check_versions: all three installed programs report exact upstream version 2.4.1.
2. check_ohos_loopback_storage: require the actual HarmonyOS kernel and writable /storage/Users/currentUser; run installed sender, receiver and master, communicate over TCP/UDP loopback, perform a 12-second bandwidth experiment, then parse nonempty finite, nonnegative bandwidth samples written in that user storage. This is the single HarmonyOS-specific end-to-end case, counted once.

Initial empty-result failures were preserved in the local report; after the protocol fix, both cases passed and the end-to-end run produced 5 samples. Loopback validates the functional measurement pipeline, not accuracy on a remote congested physical link. The receiver uses upstream fixed TCP port 7365; tests must run serially and fail if the port is occupied.
