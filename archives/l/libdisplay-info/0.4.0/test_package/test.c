/*
 * Consumer test for libdisplay-info 0.4.0.
 *
 * Parses a real EDID (upstream's test/data/acer-p1276.edid fixture, embedded
 * below) and verifies the values the library derives from it:
 *
 *   - the EDID is accepted and di_info_parse_edid() returns a valid handle
 *   - the vendor/product identification is parsed (manufacturer "ACR",
 *     product 0x1616)
 *   - di_info_get_make() resolves the manufacturer name through the vendor
 *     table that is generated from hwdata's pnp.ids at build time
 *   - di_info_get_model()/di_info_get_serial() return the display descriptor
 *     strings (upstream formats those through its memory-stream helper)
 *   - malformed input (all-zero block, truncated buffer) is rejected
 *
 * A wrong value means the package is not usable by consumers, so the test
 * binary exits non-zero instead of only printing a message.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libdisplay-info/edid.h>
#include <libdisplay-info/info.h>

static const unsigned char acer_p1276_edid[256] = {
	0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x04, 0x72, 0x16, 0x16,
	0x3e, 0x13, 0x00, 0x00, 0x17, 0x17, 0x01, 0x03, 0x0e, 0x00, 0x00, 0x00,
	0x2f, 0x41, 0xf0, 0x9e, 0x5c, 0x58, 0x89, 0x25, 0x16, 0x53, 0x5f, 0x3f,
	0xcf, 0x80, 0x31, 0x7c, 0x45, 0x7c, 0x61, 0x7c, 0x81, 0x80, 0xa9, 0x40,
	0x95, 0x00, 0x81, 0xc0, 0x81, 0x00, 0x64, 0x19, 0x00, 0x40, 0x41, 0x00,
	0x26, 0x30, 0x18, 0x88, 0x36, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x18,
	0x00, 0x00, 0x00, 0xfd, 0x00, 0x32, 0x78, 0x1e, 0x64, 0x11, 0x00, 0x0a,
	0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x00, 0x00, 0x00, 0xfc, 0x00, 0x50,
	0x31, 0x32, 0x37, 0x36, 0x0a, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20,
	0x00, 0x00, 0x00, 0xff, 0x00, 0x4a, 0x47, 0x47, 0x31, 0x31, 0x30, 0x30,
	0x31, 0x35, 0x39, 0x30, 0x30, 0x0a, 0x01, 0xa2, 0x02, 0x03, 0x04, 0x00,
	0x66, 0x21, 0x56, 0xaa, 0x51, 0x00, 0x1e, 0x30, 0x46, 0x8f, 0x33, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x1e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0xab,
};

static int
check_str(const char *what, char *got, const char *want)
{
	int failed = 0;

	if (got == NULL) {
		fprintf(stderr, "FAIL: %s is NULL, expected '%s'\n", what, want);
		failed = 1;
	} else if (strcmp(got, want) != 0) {
		fprintf(stderr, "FAIL: %s is '%s', expected '%s'\n", what, got, want);
		failed = 1;
	} else {
		fprintf(stdout, "ok: %s = '%s'\n", what, got);
	}
	free(got);
	return failed;
}

int
main(void)
{
	unsigned char invalid_edid[128] = { 0 };
	const struct di_edid_vendor_product *vendor_product;
	struct di_info *info;
	const struct di_edid *edid;
	int failed = 0;

	/* Malformed input must be rejected. */
	info = di_info_parse_edid(invalid_edid, sizeof(invalid_edid));
	if (info != NULL) {
		fprintf(stderr, "FAIL: all-zero EDID was accepted\n");
		di_info_destroy(info);
		failed = 1;
	} else {
		fprintf(stdout, "ok: all-zero EDID rejected\n");
	}
	info = di_info_parse_edid(invalid_edid, 10);
	if (info != NULL) {
		fprintf(stderr, "FAIL: truncated EDID was accepted\n");
		di_info_destroy(info);
		failed = 1;
	} else {
		fprintf(stdout, "ok: truncated EDID rejected\n");
	}

	/* Real EDID must be parsed. */
	info = di_info_parse_edid(acer_p1276_edid, sizeof(acer_p1276_edid));
	if (info == NULL) {
		fprintf(stderr, "FAIL: valid EDID was rejected\n");
		return 1;
	}
	fprintf(stdout, "ok: valid EDID parsed\n");

	edid = di_info_get_edid(info);
	if (edid == NULL) {
		fprintf(stderr, "FAIL: di_info_get_edid() returned NULL\n");
		di_info_destroy(info);
		return 1;
	}
	fprintf(stdout, "ok: di_info_get_edid() returned an EDID\n");

	if (di_info_get_failure_msg(info) != NULL) {
		fprintf(stderr, "FAIL: valid EDID reported a failure message: %s\n",
		        di_info_get_failure_msg(info));
		failed = 1;
	} else {
		fprintf(stdout, "ok: no failure message for a valid EDID\n");
	}

	vendor_product = di_edid_get_vendor_product(edid);
	if (vendor_product == NULL) {
		fprintf(stderr, "FAIL: missing vendor/product identification\n");
		di_info_destroy(info);
		return 1;
	}
	if (memcmp(vendor_product->manufacturer, "ACR", 3) != 0) {
		fprintf(stderr, "FAIL: manufacturer is '%.3s', expected 'ACR'\n",
		        vendor_product->manufacturer);
		failed = 1;
	} else {
		fprintf(stdout, "ok: manufacturer = '%.3s'\n", vendor_product->manufacturer);
	}
	if (vendor_product->product != 0x1616) {
		fprintf(stderr, "FAIL: product is 0x%04X, expected 0x1616\n",
		        vendor_product->product);
		failed = 1;
	} else {
		fprintf(stdout, "ok: product = 0x%04X\n", vendor_product->product);
	}

	/* hwdata's pnp.ids is looked up here (build-time data dependency). */
	failed |= check_str("make", di_info_get_make(info), "Acer Technologies");
	failed |= check_str("model", di_info_get_model(info), "P1276");
	failed |= check_str("serial", di_info_get_serial(info), "JGG110015900");

	di_info_destroy(info);

	if (failed) {
		fprintf(stderr, "test_libdisplay_info: FAILED\n");
		return 1;
	}
	fprintf(stdout, "test_libdisplay_info: all checks passed\n");
	return 0;
}
