/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Consumer test for the OHOS SPDK package.  Uses only CPU-only SPDK library
 * entry points (crc32 / crc32c / base64) so it runs without the DPDK EAL
 * runtime (hugepages / vfio / uio) that OHOS does not provide.
 */
#include <spdk/crc32.h>
#include <spdk/base64.h>
#include <spdk/util.h>

#include <stdio.h>
#include <string.h>
#include <stdint.h>

static int fails;

#define CHECK(cond, msg) do { \
	if (!(cond)) { printf("FAIL: %s\n", msg); fails++; } \
	else { printf("ok: %s\n", msg); } \
} while (0)

int main(void)
{
	const char *s = "123456789";
	size_t len = strlen(s);

	/* Standard CRC check values for the ASCII string "123456789". */
	uint32_t crc32c = spdk_crc32c_update(s, len, 0xFFFFFFFFu) ^ 0xFFFFFFFFu;
	CHECK(crc32c == 0xe3069283u, "crc32c KAT == 0xe3069283");
	uint32_t crc32 = spdk_crc32_ieee_update(s, len, 0xFFFFFFFFu) ^ 0xFFFFFFFFu;
	CHECK(crc32 == 0xcbf43926u, "crc32_ieee KAT == 0xcbf43926");

	/* CRC-32C: incremental update must equal the one-shot value. */
	uint32_t one = spdk_crc32c_update(s, len, 0);
	uint32_t inc = spdk_crc32c_update(s + 5, len - 5,
					  spdk_crc32c_update(s, 5, 0));
	CHECK(one == inc, "crc32c incremental == one-shot");

	/* CRC-32 (IEEE): same consistency property. */
	uint32_t ione = spdk_crc32_ieee_update(s, len, 0);
	uint32_t iinc = spdk_crc32_ieee_update(s + 5, len - 5,
					       spdk_crc32_ieee_update(s, 5, 0));
	CHECK(ione == iinc, "crc32_ieee incremental == one-shot");

	/* Base64 standard alphabet encode (RFC 4648 test vector). */
	char b64[64];
	int rc = spdk_base64_encode(b64, s, len);
	CHECK(rc == 0 && strcmp(b64, "MTIzNDU2Nzg5") == 0, "base64 encode");

	/* Base64 decode round trip. */
	unsigned char dec[32];
	size_t dlen = 0;
	rc = spdk_base64_decode(dec, &dlen, b64);
	CHECK(rc == 0 && dlen == len && memcmp(dec, s, len) == 0,
	      "base64 decode round trip");

	printf("fails=%d\n", fails);
	if (fails == 0) {
		printf("SPDK_CONSUMER_OK\n");
		return 0;
	}
	printf("SPDK_CONSUMER_FAIL\n");
	return 1;
}
