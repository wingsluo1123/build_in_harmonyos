/*======================================================================
  test.c - SACLIB consumer-side functional test (OHOS adaptation)

  Every assertion is on an exact invariant of SACLIB's arbitrary-precision
  integer arithmetic and of its list/garbage-collected heap, so a SACLIB that
  merely links cannot pass:

    1. A = 2^100 and B = 3^60 are both far beyond one 29-bit BETA digit, and
       their sum, difference and products all exceed one machine word, so every
       operation here runs SACLIB's multi-precision kernels (IPROD/ISUM/IDIF).
    2. (A + B) * (A - B) must equal A^2 - B^2 exactly.  This is a closed
       invariant of the arithmetic, checked with IEQ on the full big integers.
    3. The same identity is evaluated modulo the prime 1000003 through MDHOM
       and must give 956067, which pins the magnitude down independently of
       SACLIB's own comparison: a kernel that returns a plausible but wrong
       value cannot satisfy both (2) and (3).
    4. GC() is called explicitly between the steps.  SACLIB's collector walks
       the stack from GCSI()'s own frame up to the address recorded by
       BEGINSACLIB, so it only survives if the system-dependent GC() spilled the
       operand registers onto the stack, which is exactly what sysdep/ohosAarch64
       has to get right for AArch64/AAPCS64.  An incomplete spill shows up here
       as corrupted operands, not as a build error.
    5. LIST2/LIST1/LENGTH/FIRST/SECOND exercise the SPACE/SPACEB1 addressing,
       the NIL == BETA convention and the heap cell allocation path.

  Exit code 0 = every assertion held, non-zero = at least one failed.
======================================================================*/
#include "saclib.h"

#include <stdio.h>
#include <stdlib.h>

static int failures = 0;

static void check(int condition, const char *what)
{
	if (condition) {
		printf("ok   - %s\n", what);
	} else {
		printf("FAIL - %s\n", what);
		failures++;
	}
	fflush(stdout);
}

int main(int argc, char **argv)
{
	Word A, B, S, D, lhs, rhs, Amod, Bmod, L, M;

	printf("saclib %d.%d.%d functional test\n",
	       SACMAJVERS, SACMINVERS, SACREVVERS);

	ARGSACLIB(argc, argv, &argc, &argv);
	BEGINSACLIB((Word *)&argc);

	A = IEXP(2, 100);
	B = IEXP(3, 60);

	check(ISIGNF(A) > 0, "2^100 is a positive SACLIB integer");
	check(ISIGNF(B) > 0, "3^60 is a positive SACLIB integer");
	check(ILENGTH(A) > 1, "2^100 occupies more than one BETA digit");
	check(ILENGTH(B) > 1, "3^60 occupies more than one BETA digit");

	/* (A + B)(A - B) == A^2 - B^2, computed through two different routes. */
	S = ISUM(A, B);
	D = IDIF(A, B);
	lhs = IPROD(S, D);
	rhs = IDIF(IPROD(A, A), IPROD(B, B));
	check(IEQ(lhs, rhs) == 1, "(A+B)(A-B) == A^2 - B^2 exactly");

	/* Independent magnitude check: the same identity modulo 1000003. */
	Amod = MDHOM(1000003, lhs);
	Bmod = MDHOM(1000003, rhs);
	check(Amod == Bmod, "the identity also holds modulo 1000003");
	check(Amod == 956067,
	      "(2^100+3^60)(2^100-3^60) mod 1000003 == 956067");

	/* The collector has to preserve precisely the live big integers. */
	GC();
	check(IEQ(ISUM(A, B), S) == 1, "ISUM result survives a GC()");
	GC();
	GC();
	check(IEQ(IDIF(A, B), D) == 1, "IDIF result survives two more GC() calls");
	check(IEQ(IPROD(A, B), IPROD(B, A)) == 1, "IPROD is commutative");

	/* Heap list cells: LIST2 allocates two cells through AVAIL. */
	L = LIST2(A, B);
	check(LENGTH(L) == 2, "LIST2 built a two-element list");
	check(IEQ(FIRST(L), A) == 1, "FIRST of the list is A");
	check(IEQ(SECOND(L), B) == 1, "SECOND of the list is B");

	M = LIST1(S);
	check(LENGTH(M) == 1, "LIST1 built a one-element list");
	check(IEQ(FIRST(M), S) == 1, "FIRST of the one-element list is A + B");

	ENDSACLIB(SAC_FREEMEM);

	if (failures == 0) {
		printf("PASS - saclib arithmetic/list/GC functional test\n");
		return EXIT_SUCCESS;
	}
	printf("FAIL - %d assertion(s) failed\n", failures);
	return EXIT_FAILURE;
}
