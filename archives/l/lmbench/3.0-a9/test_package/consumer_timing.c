/*
 * consumer_timing.c — lmbench consumer test (CI L1).
 *
 * Links against the packaged libmbench.a and calls tvsub() from the
 * packaged timing.h interface; asserts nothing itself, the test script
 * checks the printed positive delta.  This proves that the installed
 * headers and static library are usable by a consumer (not only the
 * benchmark binaries).
 */
#include <stdio.h>
#include <sys/types.h>
#include <sys/time.h>

typedef unsigned long long uint64;

#include "timing.h"

int
main(void)
{
	struct timeval t0, t1, d;
	volatile unsigned long x = 0;
	unsigned long i;

	gettimeofday(&t0, 0);
	for (i = 0; i < 1000000UL; i++) {
		x += i;
	}
	gettimeofday(&t1, 0);
	tvsub(&d, &t1, &t0);
	printf("consumer tvsub: %ld.%06ld s (x=%lu)\n",
	       (long)d.tv_sec, (long)d.tv_usec, x);
	return (d.tv_sec > 0 || d.tv_usec > 0) ? 0 : 1;
}
