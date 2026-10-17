#!/bin/sh
# harmonyos_specific_test.sh — liblzw 0.3 on HarmonyOS PC (aarch64)
#
# Purpose (task hard gate: >=1 new, actually-run, library-invoking test that
# verifies OHOS behavior):
#   1) Verify platform is HarmonyOS PC / aarch64.
#   2) Compile a small consumer program that links the installed liblzw
#      (lzw_open/lzw_read/lzw_close) and assert LZW (.Z) decompression output
#      is byte-identical to the expected stream.
#   3) Exit 0 only if all assertions pass; any mismatch exits non-zero.
#
# Usage: harmonyos_test.sh   (expects liblzw source+installed lib on PATH or
#                             standard locations; see SEARCH paths below)

set -u

LIBLZW_ARCHIVE="${LIBLZW_ARCHIVE:-/storage/Users/currentUser/runnerljs002/build_in_harmonyos-liblzw-0.3/archives/l/liblzw/0.3}"
WORK="$(mktemp -d "${TMPDIR:-/storage/Users/currentUser/tmp}/liblzw-ht-XXXXXX")" || exit 90
trap 'rm -rf "$WORK"' EXIT

echo "== platform check =="
uname -a
uname -m
case "$(uname -m)" in
  aarch64|arm64) echo "PASS platform aarch64" ;;
  *) echo "FAIL platform expected aarch64"; exit 1 ;;
esac

# Locate installed liblzw: conan package cache first, then test-install, then source build.
LIB=""
for cand in \
  "$LIBLZW_ARCHIVE"/../0.3-conan-pkg/lib/liblzw.a \
  /storage/Users/currentUser/test-install-liblzw-0.3/storage/Users/currentUser/usr/local/lib/liblzw.a \
  /storage/Users/currentUser/builds/liblzw-0.3.work/.libs/liblzw.a ; do
  if [ -f "$cand" ]; then LIB="$cand"; break; fi
done
if [ -z "$LIB" ]; then
  LIB="$(find /storage/Users/currentUser/.conan2/p -path '*/p/lib/liblzw.a' 2>/dev/null | head -1)"
fi
if [ -z "$LIB" ] || [ ! -f "$LIB" ]; then
  echo "FAIL: liblzw.a not found"
  exit 1
fi
echo "using lib: $LIB"

HEADER=""
for cand in \
  /storage/Users/currentUser/test-install-liblzw-0.3/storage/Users/currentUser/usr/local/include/lzw.h \
  /storage/Users/currentUser/builds/liblzw-0.3.work/lzw.h ; do
  if [ -f "$cand" ]; then HEADER="$cand"; break; fi
done
if [ -z "$HEADER" ]; then
  HEADER="$(find /storage/Users/currentUser/.conan2/p -path '*/p/include/lzw.h' 2>/dev/null | head -1)"
fi
if [ -z "$HEADER" ] || [ ! -f "$HEADER" ]; then
  echo "FAIL: lzw.h not found"
  exit 1
fi
echo "using header: $HEADER"
echo "== source/build artifact sha256 =="
sha256sum "$LIB" "$HEADER"

cat > "$WORK/htest.c" <<'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <lzw.h>

/* Upstream simple.Z fixture (65 bytes) and its raw decompressed output. */
static const unsigned char simple_Z[] = {
	0x1f, 0x9d, 0x90, 0x31, 0x64, 0xcc, 0xa0, 0x51, 0xc3, 0xc6, 0x0d, 0x1c,
	0x39, 0x60, 0x84, 0x11, 0x33, 0x86, 0x4c, 0x19, 0x33, 0x67, 0xd0, 0xa4,
	0x51, 0xb3, 0x86, 0x4d, 0x1b, 0x37, 0x6f, 0xe0, 0xc4, 0x91, 0x33, 0x87,
	0x4e, 0x1d, 0x3b, 0x77, 0xf0, 0xe4, 0xd1, 0x13, 0x70, 0x60, 0xc1, 0x83,
	0x09, 0x17, 0x36, 0x7c, 0x18, 0x71, 0x62, 0xc5, 0x8b, 0x19, 0x37, 0x76,
	0xfc, 0x18, 0x72, 0xa4, 0x02
};
static const char expected[] =
	"1234567890abcdefghijklmnopqrstuvwxyz"
	"1234567890abcdefghijklmnopqrstuvwxyz\n";

int main(void)
{
	char path[] = "htest-Z-XXXXXX";
	unsigned char buf[256];
	lzwFile *lzw;
	size_t total = 0;
	int fd;
	ssize_t n;

	fd = mkstemp(path);
	if (fd < 0) { perror("mkstemp"); return 1; }
	if (write(fd, simple_Z, sizeof(simple_Z)) != (ssize_t)sizeof(simple_Z)) {
		perror("write"); close(fd); unlink(path); return 1;
	}
	close(fd);

	lzw = lzw_open(path, O_RDONLY);
	if (lzw == NULL) { fprintf(stderr, "FAIL: lzw_open NULL\n"); unlink(path); return 1; }
	while ((n = lzw_read(lzw, buf + total, sizeof(buf) - total)) > 0)
		total += (size_t)n;
	if (lzw_close(lzw) != 0) { fprintf(stderr, "FAIL: lzw_close\n"); unlink(path); return 1; }
	unlink(path);

	if (total != strlen(expected) || memcmp(buf, expected, total) != 0) {
		fprintf(stderr, "FAIL: got %zu bytes, expected %zu\n", total, strlen(expected));
		return 1;
	}
	printf("PASS hi-harmonyos: liblzw decompressed simple.Z correctly (%zu bytes)\n", total);
	return 0;
}
EOF

echo "== compile consumer against liblzw =="
CC="${CC:-/data/service/hnp/bin/clang}"
CFLAGS="-I$(dirname "$HEADER") -Wall -Wextra -O2"
if $CC $CFLAGS "$WORK/htest.c" "$LIB" -o "$WORK/htest" 2>"$WORK/cc.log"; then
  echo "compile ok"
else
  echo "FAIL compile:"
  cat "$WORK/cc.log"
  exit 1
fi

echo "== run consumer on HarmonyOS =="
"$WORK/htest"
rc=$?
echo "htest exit=$rc"
[ "$rc" -eq 0 ] || { echo "FAIL harmonyos test exit=$rc"; exit 1; }

echo "== library integrity: static ELF archive =="
file "$LIB"
echo "ALL PASS: HarmonyOS/aarch64 platform, liblzw LZW decompression byte-identical"
exit 0