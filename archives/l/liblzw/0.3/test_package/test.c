/*
 * test_package consumer test for liblzw 0.3
 *
 * Verifies the installed liblzw can decompress a real LZW (.Z) stream:
 *  - writes the upstream simple.Z fixture bytes to a temp file
 *  - opens it via lzw_open(), reads it via lzw_read()
 *  - asserts the decompressed content matches the expected plaintext
 *    (the same fixture is covered upstream by `make check` testsuite.at)
 * Fails (non-zero exit) on any mismatch, so the test is substantive,
 * not a hollow print-only stub (R34).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

#include <lzw.h>

/* Upstream tests/simple.Z (65 bytes, LZW .Z stream, magic 0x1f 0x9d). */
static const unsigned char simple_Z[] = {
	0x1f, 0x9d, 0x90, 0x31, 0x64, 0xcc, 0xa0, 0x51, 0xc3, 0xc6, 0x0d, 0x1c,
	0x39, 0x60, 0x84, 0x11, 0x33, 0x86, 0x4c, 0x19, 0x33, 0x67, 0xd0, 0xa4,
	0x51, 0xb3, 0x86, 0x4d, 0x1b, 0x37, 0x6f, 0xe0, 0xc4, 0x91, 0x33, 0x87,
	0x4e, 0x1d, 0x3b, 0x77, 0xf0, 0xe4, 0xd1, 0x13, 0x70, 0x60, 0xc1, 0x83,
	0x09, 0x17, 0x36, 0x7c, 0x18, 0x71, 0x62, 0xc5, 0x8b, 0x19, 0x37, 0x76,
	0xfc, 0x18, 0x72, 0xa4, 0x02
};

/* Expected plaintext of simple.Z: raw decompressed bytes are two repeats of
 * the 36-char "1234567890abcdefghijklmnopqrstuvwxyz" cycle + "\n" (73 bytes).
 * (simple.good.bz2 in upstream tests is the simple.c program's formatted
 *  output, not the raw stream; the raw bytes are what uncompress.c emits.) */
static const char expected[] =
	"1234567890abcdefghijklmnopqrstuvwxyz"
	"1234567890abcdefghijklmnopqrstuvwxyz\n";

int main(void)
{
	/* On OHOS/HMDFS /tmp is a read-only filesystem; create the temp file in
	 * the CWD (the test_package build dir, which is writable) instead. */
	char path[] = "liblzw-test-XXXXXX";
	unsigned char buf[256];
	size_t total = 0;
	int fd;
	FILE *fp;
	lzwFile *lzw;
	ssize_t n;

	fd = mkstemp(path);
	if (fd < 0) {
		perror("mkstemp");
		return 1;
	}
	fp = fdopen(fd, "wb");
	if (fp == NULL) {
		perror("fdopen");
		unlink(path);
		return 1;
	}
	if (fwrite(simple_Z, 1, sizeof(simple_Z), fp) != sizeof(simple_Z)) {
		perror("fwrite");
		fclose(fp);
		unlink(path);
		return 1;
	}
	fclose(fp);

	lzw = lzw_open(path, O_RDONLY);
	if (lzw == NULL) {
		fprintf(stderr, "FAIL: lzw_open returned NULL\n");
		unlink(path);
		return 1;
	}
	while ((n = lzw_read(lzw, buf + total, sizeof(buf) - total)) > 0) {
		total += (size_t)n;
		if (total >= sizeof(buf)) {
			fprintf(stderr, "FAIL: output buffer overflow\n");
			lzw_close(lzw);
			unlink(path);
			return 1;
		}
	}
	if (lzw_close(lzw) != 0) {
		fprintf(stderr, "FAIL: lzw_close returned non-zero\n");
		unlink(path);
		return 1;
	}
	unlink(path);

	buf[total] = '\0';
	if (total != strlen(expected) || memcmp(buf, expected, total) != 0) {
		fprintf(stderr, "FAIL: decompressed %zu bytes, expected %zu\n",
			total, strlen(expected));
		fprintf(stderr, "got: %s\n", buf);
		return 1;
	}

	printf("PASS: liblzw decompressed simple.Z correctly (%zu bytes)\n", total);
	return 0;
}