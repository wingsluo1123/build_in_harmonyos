# Image checks and kernel-facing filesystem tests answer different questions

## Error feature

A formatter or checker can run on a regular image file even when the target kernel cannot mount that filesystem or implement its private ioctl interface. A version banner proves neither kernel support nor the permissions needed for filesystem operations.

This draft is based on a static audit of the official `f2fs-tools` v1.16.0 source and this session's explicit not-run evidence. It does not claim a successful HarmonyOS build or kernel-facing test result.

## Trigger conditions

- **Platform:** Linux-derived or HarmonyOS PC systems where user-space filesystem utilities are installed separately from kernel filesystem support.
- **Build systems:** Autotools/Conan packages that emit image-manipulation programs and kernel-facing tools.
- **Source pattern:** a command-line utility issues `ioctl()` with `F2FS_IOC_*` or `FS_IOC_*` requests, while upstream tests mount images or write to block devices.
- **Test pattern:** formatter/fsck checks can use regular files, while integration cases need a compatible kernel, loop devices, mount permission, and stress tools.

## Root cause

The tools cross two execution boundaries. `mkfs.f2fs` and `fsck.f2fs` can operate on a scratch regular file; `f2fs_io` calls filesystem ioctls directly on file descriptors and depends on the mounted filesystem and kernel implementation. Upstream `scripts/verify.sh` additionally mounts loop images, resizes them, and invokes `fsstress`. `scripts/spo_test.sh` uses a raw block device, kernel module insertion, and forced reboot. These signals must be reported separately.

In v1.16.0, `tools/f2fs_io/f2fs_io.c` includes `<linux/fs.h>` and issues `ioctl(fd, F2FS_IOC_..., ...)` requests. `mkfs.f2fs` and `fsck.f2fs` also provide image-only command paths. The upstream audit declares 113 cases: 108 pair-matrix scenarios, one standalone stress scenario, three SHA-512 vectors, and one SPO scenario. The 108 pair cases contain 360 resize invocations and 180 nested `fsstress -n 10000` calls; the independent stress case invokes `fsstress -n 5000`.

## Recommended handling

1. Pin and build the package, then run consumer checks that format and check a scratch regular-file image. Report this separately from kernel behavior.
2. Run the complete upstream scenario inventory on a compatible target with F2FS loop-mount support, mount permission, a writable isolated test root, `fsstress`, and the `~/grub` fixture required by the first sload mode.
3. Keep the SPO power-loss case separate. Require an explicitly disposable block device and a matching kernel source; preserve raw command output and reboot evidence.
4. Print one PASS, FAIL, or SKIP line per case and a summary. If the target cannot be reached, mark each case not-run and retain the concrete transport output; do not convert that into an F2FS test failure or pass.
5. For an ioctl failure, preserve the raw errno and ioctl name. Distinguish unsupported commands (`ENOTTY`/`EOPNOTSUPP`) from missing mount, device, or permission (`ENODEV`/`EPERM`/`EACCES`).

## Generality evidence

An independent filesystem package shows the same boundary in its consumer test contract. `archives/e/e2fsprogs/1.47.4/test_package/test.c` calls `com_err()` to check a linked library; its `test_package/MANIFEST.yml` declares `make check` as the upstream command and one library-consumer assertion. Those package checks do not claim to exercise a mounted filesystem or the target kernel. This is a static cross-package comparison only; no e2fsprogs test was run in this session.

The distinction is broader than an f2fs-tools recipe detail: a package smoke test can establish that a user-space command or library is callable, while a kernel-facing test needs its own mount/ioctl/device evidence. The two result sets should therefore remain separate for filesystem utilities.

## Duplicate check

- `E265` covers OHOS test-environment differences for filesystem-image suites: writable `TMPDIR`, shell and locale behavior, missing Valgrind, and alternate memory checking. It does not treat an image-only command as evidence of F2FS ioctl or mounted-kernel support.
- `E178` covers missing Autotools during `autoreconf`; it is related to the separate build-bootstrap correction in this package. It does not define the image-versus-kernel test boundary.
- `E068` covers Python `ctypes.util.find_library()` invoking unavailable `ldconfig`; it does not establish filesystem behavior.

## Prohibited shortcuts

- Treating `mkfs.f2fs -V`, `fsck.f2fs -V`, or `f2fs_io help` as proof that an ioctl works.
- Counting the whole resize matrix as one case or omitting standalone stress, compile-guarded SHA-512 vectors, or the SPO scenario.
- Running `spo_test.sh` against a shared device, a guessed `/dev/sd*` path, or a target whose contents may be destroyed.
- Hiding an actual test failure as a skip or attributing a missing dependency library to a platform boundary.

## Verification commands

Image-only consumer checks, using an isolated scratch location:

```sh
truncate -s 128M "$TMPDIR/f2fs-consumer.img"
mkfs.f2fs -f "$TMPDIR/f2fs-consumer.img"
fsck.f2fs -f "$TMPDIR/f2fs-consumer.img"
```

Kernel-facing checks must use the actual package binaries and target kernel. The upstream `verify.sh` source expects a loop-capable F2FS environment and `~/xfstests/ltp/fsstress`. The SPO start path additionally requires a dedicated disposable block device; it is not part of ordinary package creation.

## Current evidence and boundary

The prescribed two-hop device probe in this session returned `TcpTestSucceeded=false` with `ssh: connect to host 114.212.20.39 port 22: Connection timed out`. This exact transport output is the session's not-run evidence, not an f2fs-tools test failure. All 113 upstream cases are recorded not-run with per-case evidence in `archives/f/f2fs-tools/1.16.0/reports/upstream-test-results.tsv`. A local MinGW compile attempt for the SHA-512 source stopped at missing host header `mntent.h`; no vector executable ran. The SPO case additionally remains unlaunched because the script targets `/dev/sdb1` and forces reboot without an identified disposable device.

This evidence is about session reachability and test boundaries; it does not claim that HarmonyOS lacks F2FS support or that the upstream tests pass. The build bootstrap failure is handled separately by declaring the Autotools chain in Conan and calling `autoreconf -fiv`.

## Difference from existing knowledge

`E265` covers general OHOS filesystem-image test compatibility issues such as writable temporary paths, shell/locale differences, and absent test tools. This draft focuses on the separate user-space/kernel ioctl contract and on splitting image-only checks from mounted, privileged, and destructive scenarios. `E068` concerns Python `ctypes.util.find_library()` invoking a missing `ldconfig`; it does not establish whether f2fs-tools configuration or F2FS ioctls work.

## Evidence and metadata

- Upstream: `https://git.kernel.org/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git`, tag `v1.16.0`, peeled commit `06c027abc6153c4a97cba5317844e8dcaaee3cf7`.
- Kernel-facing source: `tools/f2fs_io/f2fs_io.c` and `tools/f2fs_io/f2fs_io.h`.
- Upstream test definitions: `scripts/verify.sh`, `scripts/spo_test.sh`, and the three `UNITTEST` vectors in `tools/sha512.c`.
- Independent package comparison: `archives/e/e2fsprogs/1.47.4/test_package/test.c` and `archives/e/e2fsprogs/1.47.4/test_package/MANIFEST.yml` (static inspection only).
- Package integration: `archives/f/f2fs-tools/1.16.0/test_package/run_consumer_checks.py`.
- Contributor: `iKalous_OscarP`; this remains a draft for maintainer review.
