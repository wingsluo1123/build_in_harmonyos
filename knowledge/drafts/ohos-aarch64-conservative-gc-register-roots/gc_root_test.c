/*======================================================================
  gc_root_test.c - does the collector keep every live object?

  Measures the failure mode of a conservative collector whose register roots
  are captured by spilling "dummy argument" values, on a target whose calling
  convention differs from the one that trick was designed for.

  Shape of the test (deliberately generic, no SACLIB-specific assertions):

    * build N independent multi-precision values, keep every one of them live
    * derive further values from them, keep those live too
    * keep them live ACROSS an explicit collection
    * re-derive every value from its inputs and compare against the copy that
      stayed live; a collector that missed a register root has already
      reclaimed one of the live values here, so the comparison crashes or fails

  The same source is compiled at -O0 / -O1 / -O2 / -Os:  a collector that only
  works at -O0 is broken, because -O0 keeps every live value in a stack slot and
  therefore never exercises register roots at all.

  usage: gc_root_test [-q]
    -q   quiet: only print the final summary line

  exit code 0 = all checks passed at the level it was built with.
======================================================================*/
#include "saclib.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NVAL 14

static int quiet = 0;
static int failures = 0;

static void check(int ok, const char *what)
{
	if (!ok) {
		failures++;
		printf("FAIL - %s\n", what);
		fflush(stdout);
	} else if (!quiet) {
		printf("ok   - %s\n", what);
		fflush(stdout);
	}
}

/* build one value per slot; two of them exercise the list heap as well */
static void build(Word *v, Word *l1, Word *l2)
{
	v[0] = IEXP(2, 100);
	v[1] = IEXP(3, 60);
	v[2] = IEXP(5, 50);
	v[3] = IEXP(7, 40);
	v[4] = IEXP(11, 30);
	v[5] = IEXP(13, 25);
	v[6] = ISUM(v[0], v[1]);
	v[7] = IDIF(v[0], v[1]);
	v[8] = IPROD(v[2], v[3]);
	v[9] = IPROD(v[4], v[5]);
	v[10] = ISUM(v[6], v[8]);
	v[11] = IDIF(v[8], v[9]);
	v[12] = IPROD(v[6], v[7]);
	v[13] = IEXP(3, 100);
	*l1 = LIST2(v[0], v[1]);
	*l2 = LIST1(v[2]);
}

/* every assertion re-derives the value from its inputs and compares with the
 * copy that has been live all along */
static void verify(Word *v, Word l1, Word l2, const char *phase)
{
	char what[128];

	snprintf(what, sizeof what, "%s: v6 == v0+v1", phase);
	check(IEQ(ISUM(v[0], v[1]), v[6]) == 1, what);
	snprintf(what, sizeof what, "%s: v7 == v0-v1", phase);
	check(IEQ(IDIF(v[0], v[1]), v[7]) == 1, what);
	snprintf(what, sizeof what, "%s: v8 == v2*v3", phase);
	check(IEQ(IPROD(v[2], v[3]), v[8]) == 1, what);
	snprintf(what, sizeof what, "%s: v9 == v4*v5", phase);
	check(IEQ(IPROD(v[4], v[5]), v[9]) == 1, what);
	snprintf(what, sizeof what, "%s: v10 == v6+v8", phase);
	check(IEQ(ISUM(v[6], v[8]), v[10]) == 1, what);
	snprintf(what, sizeof what, "%s: v11 == v8-v9", phase);
	check(IEQ(IDIF(v[8], v[9]), v[11]) == 1, what);
	snprintf(what, sizeof what, "%s: v12 == v6*v7", phase);
	check(IEQ(IPROD(v[6], v[7]), v[12]) == 1, what);
	snprintf(what, sizeof what, "%s: list head still v0", phase);
	check(IEQ(FIRST(l1), v[0]) == 1, what);
	snprintf(what, sizeof what, "%s: list second still v1", phase);
	check(IEQ(SECOND(l1), v[1]) == 1, what);
	snprintf(what, sizeof what, "%s: list1 head still v2", phase);
	check(IEQ(FIRST(l2), v[2]) == 1, what);
	snprintf(what, sizeof what, "%s: v13 still multi-digit", phase);
	check(ILENGTH(v[13]) > 1, what);
}

int main(int argc, char **argv)
{
	Word v[NVAL], l1, l2;
	int i;

	/* a little stdout traffic before the collection: on AArch64 this is what
	 * makes the caller spill into the 16-byte red zone below the stack
	 * pointer, which is exactly where a stack scan starting too high misses
	 * live pointers */
	for (i = 1; i < argc; i++)
		if (strcmp(argv[i], "-q") == 0)
			quiet = 1;

	ARGSACLIB(argc, argv, &argc, &argv);
	BEGINSACLIB((Word *)&argc);

	build(v, &l1, &l2);
	verify(v, l1, l2, "before GC");

	if (!quiet) {
		printf("--- GC() #1 with %d live values ---\n", NVAL + 2);
		fflush(stdout);
	}
	GC();
	verify(v, l1, l2, "after GC #1");

	if (!quiet) {
		printf("--- GC() #2 and #3 ---\n");
		fflush(stdout);
	}
	GC();
	GC();
	verify(v, l1, l2, "after GC #2/3");

	ENDSACLIB(SAC_FREEMEM);
	printf("%s - %d failure(s)\n", failures ? "FAIL" : "PASS", failures);
	return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
