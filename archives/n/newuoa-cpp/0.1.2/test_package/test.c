/*
 * Consumer test for newuoa-cpp 0.1.2 — plain C public interface.
 *
 * A downstream application links against the installed libnewuoa (static)
 * using only the exported public header <newuoa.h> and the documented
 * `newuoa()` entry point, then verifies the optimizer converges to the
 * known minimum of the upstream example objective (-144 at
 * x = (-2*sqrt(5), -sqrt(5))).
 */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include <newuoa.h>

static size_t calls = 0;

static double objective(long n, const double *x) {
    assert(n == 2);
    ++calls;
    return -4 * x[0] * x[1] + 5 * x[0] * x[0] + 8 * x[1] * x[1]
         + 16 * sqrt(5.0) * x[0] + 8 * sqrt(5.0) * x[1] - 44.0;
}

int main(void) {
    const long n = 2;
    const long npt = (n + 1) * (n + 2) / 2;
    double x[2] = {0.0, -sqrt(5.0)};
    const size_t wsize = NEWUOA_WORKING_SPACE_SIZE(n, npt);
    double *w = calloc(wsize, sizeof(double));
    if (w == NULL) {
        fprintf(stderr, "calloc failed\n");
        return 2;
    }

    const double result = newuoa(objective, n, npt, x, 1e-3, 1e3, 100, w);
    free(w);

    printf("result=%.6f calls=%zu x0=%.6f x1=%.6f\n",
           result, calls, x[0], x[1]);

    /* Known optimum of the example objective is -144. */
    if (fabs(result - (-144.0)) > 1e-3) {
        fprintf(stderr, "consumer test: unexpected optimum %.6f\n", result);
        return 1;
    }
    if (calls == 0) {
        fprintf(stderr, "consumer test: objective never called\n");
        return 1;
    }
    return 0;
}
