// test_package/test_plib.cc — plib 1.8.5 consumer functional test (sg module).
//
// Links against the packaged plib static libraries and calls the real sg
// (3D math) API with numeric assertions.  Exits non-zero on any failure so
// `conan create` / CI L1/L2 record a real failure.
#include <plib/sg.h>

#include <cmath>
#include <cstdio>

static int failures = 0;

static void check(const char *what, bool cond, const char *detail)
{
    std::printf("%s: %s (%s)\n", cond ? "ok" : "FAIL", what, detail);
    if (!cond)
        ++failures;
}

int main()
{
    sgVec3 a, b, c;

    sgSetVec3(a, 1.0f, 2.0f, 3.0f);
    sgSetVec3(b, 4.0f, 5.0f, 6.0f);

    // vector addition
    sgAddVec3(c, a, b);
    check("sgAddVec3", c[0] == 5.0f && c[1] == 7.0f && c[2] == 9.0f,
          "a+b == (5,7,9)");

    // length
    SGfloat len = sgLengthVec3(a);
    check("sgLengthVec3", std::fabs((double) len - std::sqrt(14.0)) < 1e-4,
          "|(1,2,3)| == sqrt(14)");

    // copy + scale
    sgVec3 d;
    sgCopyVec3(d, a);
    sgScaleVec3(d, 2.0f);
    check("sgScaleVec3", d[0] == 2.0f && d[1] == 4.0f && d[2] == 6.0f,
          "2*(1,2,3) == (2,4,6)");

    // dot product
    SGfloat dot = sgScalarProductVec3(a, b);
    check("sgScalarProductVec3", std::fabs((double) dot - 32.0) < 1e-4,
          "a.b == 1*4+2*5+3*6 == 32");

    std::printf("PLIB_SG_TESTS failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
