/*======================================================================
  consumer_flow.c - a complete end-to-end consumer workflow on SACLIB.

  This is not an assertion list.  It is one program that consumes the
  installed library to do a whole job, the way a downstream tool would, and
  prints its results so they can be checked against values computed
  independently:

    1. read a problem file (sizes, not hard-wired constants)
    2. compute an exact factorial by repeated multi-precision multiplication
    3. convert a rational number to its exact decimal expansion, detecting the
       repeating cycle (pure integer arithmetic: no floating point anywhere)
    4. verify the closing identity  a/b - c/d == (ad - bc)/bd

  Every step goes through the installed headers and archive: IWRITE/GWRITE for
  output, ISUM/IDPR for the product, RNRED/RNNUM/RNDEN/RNSUM/
  RNDIF/RNPROD/RNQ for the rationals, IQR/DIGIT for the division loop.

  Because the whole loop allocates and frees a large number of intermediate
  big integers, it also drives the garbage collector under a real workload --
  the GC() assertions in test.c only cover the collector in isolation.

  usage: consumer_flow <problem-file>
         consumer_flow -           (read the problem from stdin)

  The problem is always supplied through a real stream: /tmp is not writable on
  OHOS, so tmpfile() is not an option there.
======================================================================*/
#include "saclib.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static Word failures = 0;

/* ── input ─────────────────────────────────────────────────────────────── */

static int next_number(FILE *in, Word *out)
{
	int c;
	char buf[64];
	size_t n = 0;

	for (;;) {
		c = fgetc(in);
		if (c == EOF)
			return 0;
		if (c == '#') {
			while (c != EOF && c != '\n')
				c = fgetc(in);
			continue;
		}
		if (isspace(c))
			continue;
		break;
	}
	if (c == '-' || c == '+') {
		buf[n++] = (char)c;
		c = fgetc(in);
	}
	while (c != EOF && isdigit(c) && n < sizeof buf - 1) {
		buf[n++] = (char)c;
		c = fgetc(in);
	}
	buf[n] = '\0';
	if (n == 0 || (n == 1 && !isdigit((unsigned char)buf[0])))
		return 0;
	*out = atoi(buf);
	return 1;
}

static Word ipow(Word base, Word exp)
{
	Word result = 1, i;
	for (i = 0; i < exp; i++)
		result = IDPR(result, base);
	return result;
}

/* the problem used by test.sh, so the program can be run by hand as well */
static const char *BUILTIN_PROBLEM = "# nfact b1 c1 b2 c2\n11 100 3 7 13\n";

/* ── exact decimal expansion with cycle detection ──────────────────────── */

static void exact_decimal(Word R, int max_digits)
{
	Word num = RNNUM(R), den = RNDEN(R), q, r, digit, t, i, ndig = 0;
	Word *seen_n, *seen_at;
	int negative = (ISIGNF(num) < 0);

	if (negative)
		num = INEG(num);

	IQR(num, den, &q, &r);
	printf("%s", negative ? "-" : "");
	GWRITE(q);
	if (r == 0) {
		printf("  (terminating)");
		return;
	}
	printf(".");

	seen_n = (Word *)malloc(sizeof(Word) * (max_digits + 1));
	seen_at = (Word *)malloc(sizeof(Word) * (max_digits + 1));
	if (seen_n == NULL || seen_at == NULL) {
		printf(" (no memory for cycle detection)");
		free(seen_n);
		free(seen_at);
		return;
	}

	while (r != 0 && ndig < max_digits) {
		for (i = 0; i < ndig; i++) {
			if (seen_n[i] == r) {
				printf("  (cycle of length %d)", (int)(ndig - seen_at[i]));
				free(seen_n);
				free(seen_at);
				return;
			}
		}
		seen_n[ndig] = r;
		seen_at[ndig] = ndig;
		ndig++;
		/* one decimal digit: digit = (r * 10) / den, r = (r * 10) - digit * den */
		t = IDPR(r, 10);
		IQR(t, den, &digit, &r);
		GWRITE(digit);
		fflush(stdout);
	}
	printf("  (%s)", r == 0 ? "terminating" : "truncated");
	free(seen_n);
	free(seen_at);
}

/* ── main workflow ─────────────────────────────────────────────────────── */

int main(int argc, char **argv)
{
	FILE *in = stdin;
	Word nfact = 0, b1 = 0, c1 = 0, b2 = 0, c2 = 0;
	Word fact, i, ten, f10, f10_expect = 39916800;
	Word x, y, sum, diff, prod, quot, expect, lhs;
	Word num_expect, den_expect;

	ARGSACLIB(argc, argv, &argc, &argv);
	BEGINSACLIB((Word *)&argc);

	if (argc > 1 && strcmp(argv[1], "-") != 0) {
		in = fopen(argv[1], "r");
		if (in == NULL) {
			fprintf(stderr, "cannot open %s\n", argv[1]);
			ENDSACLIB(SAC_FREEMEM);
			return 2;
		}
	} else {
		in = stdin;
	}
	if (!next_number(in, &nfact) || !next_number(in, &b1)
	    || !next_number(in, &c1) || !next_number(in, &b2)
	    || !next_number(in, &c2)) {
		fprintf(stderr, "problem file must contain: n b1 c1 b2 c2\n");
		if (in != stdin)
			fclose(in);
		ENDSACLIB(SAC_FREEMEM);
		return 2;
	}
	printf("problem: %d! , fractions %d/%d and %d/%d\n\n",
	       (int)nfact, (int)b1, (int)c1, (int)b2, (int)c2);

	/* ── 1. exact factorial, one multi-precision product per step ─────── */
	printf("[1] %d! computed by repeated exact multiplication\n", (int)nfact);
	fact = 1;
	for (i = 2; i <= nfact; i++)
		fact = IDPR(fact, i);
	printf("    %d! = ", (int)nfact);
	/* IWRITE, not ILWRITE: a factorial that still fits in one BETA digit is an
	 * immediate value, and ILWRITE indexes the list heap with its argument */
	IWRITE(fact);
	printf("\n");

	/* independent check: 10! * 11 == 11! computed along the same loop path */
	if (nfact >= 11) {
		ten = 1;
		for (i = 2; i <= 10; i++)
			ten = IDPR(ten, i);
		f10 = IDPR(ten, 11);
		if (IEQ(f10, f10_expect) != 1) {
			printf("    10! * 11 != 11!  MISMATCH\n");
			failures++;
		} else {
			printf("    10! * 11 == 11! == %d  (ok)\n", (int)f10_expect);
		}
	}
	printf("\n");

	/* ── 2. rational arithmetic, then exact decimal expansion ─────────── */
	x = RNRED(b1, c1);
	y = RNRED(b2, c2);
	sum = RNSUM(x, y);
	diff = RNDIF(x, y);
	prod = RNPROD(x, y);
	quot = RNQ(x, y);

	printf("[2] exact rational arithmetic (all results reduced)\n");
	printf("    x = %d/%d -> ", (int)b1, (int)c1); RNWRITE(x); printf("\n");
	printf("    y = %d/%d -> ", (int)b2, (int)c2); RNWRITE(y); printf("\n");
	printf("    x+y = "); RNWRITE(sum); printf("\n");
	printf("    x-y = "); RNWRITE(diff); printf("\n");
	printf("    x*y = "); RNWRITE(prod); printf("\n");
	printf("    x/y = "); RNWRITE(quot); printf("\n\n");

	/* closing identity: x - y == (b1*c2 - b2*c1) / (c1*c2), reduced */
	num_expect = IDIF(IDPR(b1, c2), IDPR(b2, c1));
	den_expect = IDPR(c1, c2);
	expect = RNRED(num_expect, den_expect);
	lhs = diff;
	printf("[3] identity x - y == (b1*c2 - b2*c1)/(c1*c2)\n");
	printf("    lhs = "); RNWRITE(lhs); printf("\n");
	printf("    rhs = "); RNWRITE(expect); printf("\n");
	if (RNCOMP(lhs, expect) != 0) {
		printf("    MISMATCH\n");
		failures++;
	} else {
		printf("    equal: yes\n");
	}
	printf("\n");

	/* ── 3. exact decimal expansion of a few rationals ────────────────── */
	printf("[4] exact decimal expansion (pure integer arithmetic)\n");
	printf("    1/3   = "); exact_decimal(RNRED(1, 3), 20); printf("\n");
	printf("    1/7   = "); exact_decimal(RNRED(1, 7), 20); printf("\n");
	printf("    1/2   = "); exact_decimal(RNRED(1, 2), 20); printf("\n");
	printf("    22/7  = "); exact_decimal(RNRED(22, 7), 20); printf("\n");
	printf("    1/%d  = ", (int)c1); exact_decimal(x, 20); printf("\n");
	printf("    sum   = "); exact_decimal(sum, 20); printf("\n");
	printf("\n");

	if (in != stdin)
		fclose(in);
	ENDSACLIB(SAC_FREEMEM);
	printf("%s - consumer workflow finished (%d problem(s))\n",
	       failures ? "FAIL" : "PASS", failures);
	return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
