//
// Smoke test for pxr-ts 26.08 on HarmonyOS PC (aarch64).
//
// Exercises the packaged TsSpline API (construction, value type, knot
// insertion, evaluation) and, because target "ts" pulls in vt/gf/tf/arch,
// also touches one interface from each of those bundled modules so that a
// missing or mis-ordered static library is caught at link time.
//
#include <pxr/pxr.h>
#include <pxr/base/ts/spline.h>
#include <pxr/base/ts/knot.h>
#include <pxr/base/arch/errno.h>
#include <pxr/base/tf/getenv.h>
#include <pxr/base/vt/value.h>
#include <pxr/base/gf/vec3d.h>

#include <cerrno>
#include <cmath>
#include <iostream>
#include <string>

PXR_NAMESPACE_USING_DIRECTIVE

#define CHECK(cond, msg)                                 \
    do {                                                 \
        if (!(cond)) {                                   \
            std::cerr << "FAIL: " << msg << std::endl;   \
            return 1;                                    \
        }                                                \
    } while (0)

int main() {
    // ---- ts: spline value type ----
    TsSpline spline(Ts_GetType<double>());
    CHECK(spline.GetValueType() == Ts_GetType<double>(),
          "TsSpline value type is not double");

    // ---- ts: knot round-trip ----
    TsTypedKnot<double> k0;
    k0.SetTime(0.0);
    k0.SetValue(0.0);
    CHECK(k0.GetTime() == 0.0, "knot GetTime mismatch");
    double k0v = -1.0;
    CHECK(k0.GetValue(&k0v) && std::abs(k0v - 0.0) < 1e-9,
          "knot GetValue mismatch");

    TsTypedKnot<double> k1;
    k1.SetTime(1.0);
    k1.SetValue(10.0);

    CHECK(spline.SetKnot(k0), "SetKnot(k0) rejected");
    CHECK(spline.SetKnot(k1), "SetKnot(k1) rejected");

    // ---- ts: evaluation ----
    // Exact knot times are interpolation-independent, so these are tight.
    double v = -1.0;
    CHECK(spline.Eval(0.0, &v) && std::abs(v - 0.0) < 1e-9,
          "Eval(0.0) != 0.0");
    CHECK(spline.Eval(1.0, &v) && std::abs(v - 10.0) < 1e-9,
          "Eval(1.0) != 10.0");

    // Between the knots the curve must stay inside the knot value range,
    // whatever interpolation mode the default knot uses.
    double mid = -1.0;
    CHECK(spline.Eval(0.5, &mid), "Eval(0.5) failed");
    CHECK(mid >= 0.0 && mid <= 10.0, "Eval(0.5) outside knot value range");

    // ---- arch / tf / vt / gf: prove the bundled closure really links ----
    std::string err = ArchStrerror(ENOENT);
    CHECK(!err.empty(), "ArchStrerror(ENOENT) returned empty string");

    std::string path = TfGetenv("PATH", "");
    CHECK(!path.empty(), "TfGetenv(PATH) returned empty string");

    VtValue vtVal(3.5);
    CHECK(vtVal.IsHolding<double>(), "VtValue not holding double");

    GfVec3d vec(1.0, 2.0, 3.0);
    CHECK(vec[2] == 3.0, "GfVec3d component mismatch");

    std::cout << "pxr-ts smoke test: OK (Eval(1.0)=" << v
              << ", Eval(0.5)=" << mid
              << ", ArchStrerror(ENOENT)=\"" << err << "\")" << std::endl;
    return 0;
}
