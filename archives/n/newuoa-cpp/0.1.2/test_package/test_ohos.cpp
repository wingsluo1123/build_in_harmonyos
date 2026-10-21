/*
 * HarmonyOS-specific test for newuoa-cpp 0.1.2 — C++ closure-const interface.
 *
 * Exercises the `newuoa_closure_const` public API (C++ closure over an
 * arbitrary callable with const data) as a business-layer consumer on
 * OHOS: minimizes a simple two-variable quadratic whose known minimum is
 * 0 at x = (3, -2) and asserts convergence on this platform.
 */
#include <cstdio>

#include <newuoa.h>

struct Objective {
    long *calls;

    static double eval(const void *data, long n, const double *x) {
        const Objective *self = static_cast<const Objective *>(data);
        ++(*self->calls);
        return (x[0] - 3.0) * (x[0] - 3.0) + (x[1] + 2.0) * (x[1] + 2.0);
    }
};

int main() {
    const long n = 2;
    const long npt = 6;
    double x[2] = {0.0, 0.0};
    double w[NEWUOA_WORKING_SPACE_SIZE(n, npt)];
    long calls = 0;

    Objective obj;
    obj.calls = &calls;
    NewuoaClosureConst closure = {&obj, &Objective::eval};

    const double result =
        newuoa_closure_const(&closure, n, npt, x, 1.0, 1e-6, 200, w);

    std::printf("result=%.6f calls=%ld x0=%.6f x1=%.6f\n",
                result, calls, x[0], x[1]);

    if (result > 1e-4) {
        std::fprintf(stderr, "ohos test: did not converge (result %.6f)\n",
                     result);
        return 1;
    }
    if (calls == 0) {
        std::fprintf(stderr, "ohos test: objective never called\n");
        return 1;
    }
    return 0;
}
