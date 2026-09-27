/* Consumer contract test for zvbi 0.2.44.
 *
 * Exercises the installed package's public API surface with exact oracles
 * taken from the upstream sources the library implements (verified against
 * src/libzvbi.h, src/hamm.h and src/hamm-tables.h of the 0.2.44 tarball):
 *
 *  1. vbi_version(): fills major/minor/micro (libzvbi.h:2148) — must be
 *     0/2/44 for this package.
 *  2. vbi_ham8(): Hamming 8/4 *encoder* (nibble -> byte, _vbi_hamm8_fwd):
 *     vbi_ham8(0)==0x15, vbi_ham8(5)==0x73 (hamm-tables.h:55-58).
 *  3. vbi_unham8(): Hamming 8/4 *decoder* (_vbi_hamm8_inv): 0x15 decodes
 *     clean to 0, 0x14 is single-bit-corrected to 0, 0x16 (table value
 *     0xff, i.e. (int8_t)-1) is a double-bit error -> -1.  Upstream has
 *     no VBI_HAM_ERROR macro, so -1 is asserted literally.
 *  4. vbi_rev8()/vbi_rev16(): bit reversal round-trips.
 *  5. Raw decoder v1 API on a synthesized flat-grey line: parameters and
 *     TELETEXT_B slicing come up, and a line with no clock run-in decodes
 *     to 0 lines.
 *  6. A vbi_export object for the "text" backend can be created, lists an
 *     option (vbi_export_option_info_enum index 0 non-NULL) and is
 *     destroyed — this path pulls in the iconv-based charset layer.
 *     (Upstream has no vbi_export_option_keywords(); the enum function is
 *     the real API, libzvbi.h:930.)
 *
 * Any failure prints "not ok N - ..." and exits non-zero.
 */
#include <libzvbi.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int failures;

static void
check (int number, int condition, const char *what)
{

	if (condition) {
		printf ("ok %d - %s\n", number, what);
	} else {
		printf ("not ok %d - %s\n", number, what);
		++failures;
	}
}

int
main (void)
{
	/* Unbuffered so a crash leaves the exact check number in the log. */
	setvbuf (stdout, NULL, _IONBF, 0);
	/* 1. Version contract of the package. */
	{
		unsigned int major = 0, minor = 0, micro = 0;

		vbi_version (&major, &minor, &micro);
		check (1, major == 0 && minor == 2 && micro == 44,
		       "vbi_version() reports 0.2.44");
	}

	/* 2-3. Hamming 8/4 encode (vbi_ham8 maps nibble -> byte). */
	check (2, vbi_ham8 (0) == 0x15,
	       "vbi_ham8() encodes 0 to 0x15");
	check (3, vbi_ham8 (5) == 0x73,
	       "vbi_ham8() encodes 5 to 0x73");

	/* 4-6. Hamming 8/4 decode (vbi_unham8 maps byte -> nibble). */
	check (4, vbi_unham8 (0x15) == 0,
	       "vbi_unham8() decodes error-free 0x15 to 0");
	check (5, vbi_unham8 (0x14) == 0,
	       "vbi_unham8() corrects a single-bit error");
	check (6, vbi_unham8 (0x16) == -1,
	       "vbi_unham8() flags a double-bit error as -1");

	/* 7-8. Bit reversal round trip. */
	check (7, vbi_rev8 (vbi_rev8 (0xA5)) == 0xA5,
	       "vbi_rev8() is an involution");
	check (8, vbi_rev16 (0x1234) ==
	       (((unsigned int) vbi_rev8 (0x34) << 8) | vbi_rev8 (0x12)),
	       "vbi_rev16() reverses both bytes with byte swap");

	/* 9-11. Raw decoder v1 API: stack-allocated decoder, parameters for
	 * 625-line TELETEXT_B, then decode a flat-grey image.  Per the
	 * vbi_raw_decode() contract (decoder.c) the raw image must hold
	 * rd->count[0] + rd->count[1] scan lines of rd->bytes_per_line
	 * bytes, and out must hold that many vbi_sliced records.  A field
	 * with no clock run-in must produce zero sliced lines. */
	{
		vbi_raw_decoder rd;
		unsigned int covered;
		unsigned int added;
		int max_rate = 0;
		static uint8_t raw_image[64 * 2048];
		static vbi_sliced sliced[64];
		unsigned int n_alloc_lines;
		int n_lines;

		vbi_raw_decoder_init (&rd);
		covered = vbi_raw_decoder_parameters (&rd,
						      VBI_SLICED_TELETEXT_B,
						      /* scanning */ 625,
						      &max_rate);
		check (9, (covered & VBI_SLICED_TELETEXT_B) != 0,
		       "vbi_raw_decoder_parameters() covers TELETEXT_B");

		added = vbi_raw_decoder_add_services (&rd,
						      VBI_SLICED_TELETEXT_B,
						      /* strict */ TRUE);
		check (10, (added & VBI_SLICED_TELETEXT_B) != 0,
		       "vbi_raw_decoder_add_services() slices TELETEXT_B");

		n_alloc_lines = rd.count[0] + rd.count[1];
		memset (raw_image, 128, sizeof (raw_image));
		memset (sliced, 0, sizeof (sliced));
		n_lines = -1;
		if (rd.bytes_per_line > 0 &&
		    rd.bytes_per_line <= 2048 &&
		    n_alloc_lines > 0 && n_alloc_lines <= 64) {
			n_lines = vbi_raw_decode (&rd, raw_image, sliced);
		}
		check (11, n_lines == 0,
		       "vbi_raw_decode() rejects an image without run-in");

		vbi_raw_decoder_destroy (&rd);
	}

	/* 12. Export machinery: create the text backend, list one option,
	 * destroy.  This path pulls in the iconv-based charset layer. */
	{
		vbi_export *export;
		char *errstr = NULL;

		export = vbi_export_new ("text", &errstr);
		check (12, export != NULL &&
		       vbi_export_option_info_enum (export, 0) != NULL,
		       "vbi_export text backend creates and lists options");
		if (export != NULL)
			vbi_export_delete (export);
	}

	if (0 == failures) {
		printf ("ZVBI_TEST PASS\n");
		return 0;
	}
	printf ("ZVBI_TEST FAIL (%d failure(s))\n", failures);
	return 1;
}
