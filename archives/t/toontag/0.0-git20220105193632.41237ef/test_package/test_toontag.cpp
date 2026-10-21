// test_toontag.cpp — toontag consumer test (R34: real API usage).
//
// Exercises three independent parts of the packaged libtoontag:
//  1. tag::find_quartic_real_roots  (tag/quartic.h,  compiled in libtoontag)
//  2. tag::computeAbsoluteOrientation / computeRotation (tag/absorient.h,
//     header-inline but validated against the packaged headers + lib)
//  3. tag::getEssentialMatrix / tag::se3_from_E (tag/helpers.h + libtoontag)
//
// 8 explicit checks; any failure returns non-zero. Deterministic: fixed
// inputs, no randomness, no fixtures, prints one CHECK line per assertion.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <vector>

#include <tag/absorient.h>
#include <tag/five_point.h>
#include <tag/helpers.h>
#include <tag/quartic.h>

#include <TooN/TooN.h>
#include <TooN/se3.h>

static int g_passed = 0;

#define CHECK(name, cond)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("CHECK %s PASS\n", name);                              \
            ++g_passed;                                                        \
        } else {                                                               \
            std::printf("CHECK %s FAIL\n", name);                              \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main() {
    // --- 1. quartic solver: x^4 - 5x^2 + 4 = 0 -> roots -2,-1,1,2 ---
    // Polynomial form: x^4 + B x^3 + C x^2 + D x + E, so B=0,C=-5,D=0,E=4.
    double roots[4] = {0, 0, 0, 0};
    int nroots = tag::find_quartic_real_roots(0.0, -5.0, 0.0, 4.0, roots);
    CHECK("quartic-count", nroots == 4);
    std::sort(roots, roots + 4);
    const double want[4] = {-2.0, -1.0, 1.0, 2.0};
    bool roots_ok = true;
    for (int i = 0; i < 4; ++i) {
        if (std::fabs(roots[i] - want[i]) > 1e-6) {
            roots_ok = false;
        }
    }
    CHECK("quartic-roots", roots_ok);

    // --- 2. absolute orientation: recover a known SE3 from point pairs ---
    const TooN::SE3<> pose(
        TooN::SO3<>::exp(TooN::makeVector(0.0, 0.0, 0.5235987755982988)),
        TooN::makeVector(1.0, 2.0, 3.0));
    std::vector<TooN::Vector<3> > a, b;
    const double pts[6][3] = {{0, 0, 0}, {1, 0, 0}, {0, 1, 0},
                              {0, 0, 1}, {1, 1, 0}, {1, 0, 1}};
    for (int i = 0; i < 6; ++i) {
        TooN::Vector<3> p = TooN::makeVector(pts[i][0], pts[i][1], pts[i][2]);
        a.push_back(p);
        b.push_back(pose * p);
    }
    const TooN::SE3<> est = tag::computeAbsoluteOrientation(a, b);
    const double trans_err =
        TooN::norm(est.get_translation() - pose.get_translation());
    CHECK("absorient-translation", trans_err < 1e-9);
    const TooN::Matrix<3> dR =
        est.get_rotation().get_matrix().T() * pose.get_rotation().get_matrix();
    double rot_err = 0.0;
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            const double want_v = (r == c) ? 1.0 : 0.0;
            rot_err += std::fabs(dR[r][c] - want_v);
        }
    }
    CHECK("absorient-rotation", rot_err < 1e-9);
    double residual = 0.0;
    for (size_t i = 0; i < a.size(); ++i) {
        residual += TooN::norm_sq(b[i] - est * a[i]);
    }
    CHECK("absorient-residual", residual < 1e-18);

    // --- 3. essential matrix round-trip from the same known pose ---
    const TooN::Matrix<3> E = tag::getEssentialMatrix(pose);
    double det = E[0][0] * (E[1][1] * E[2][2] - E[1][2] * E[2][1]) -
                 E[0][1] * (E[1][0] * E[2][2] - E[1][2] * E[2][0]) +
                 E[0][2] * (E[1][0] * E[2][1] - E[1][1] * E[2][0]);
    CHECK("essential-det-zero", std::fabs(det) < 1e-9);
    const std::vector<TooN::SE3<> > poses = tag::se3_from_E(E);
    CHECK("se3-from-E-count", poses.size() == 4);

    // --- 4. rotation-only fit is orthonormal ---
    const TooN::Matrix<3> R = tag::computeRotation(a, b);
    const TooN::Matrix<3> should_be_I = R * R.T();
    double ortho_err = 0.0;
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            const double want_v = (r == c) ? 1.0 : 0.0;
            ortho_err += std::fabs(should_be_I[r][c] - want_v);
        }
    }
    CHECK("rotation-orthonormal", ortho_err < 1e-9);

    std::printf("TOONTAG_CHECKS_PASSED=%d/8\n", g_passed);
    return (g_passed == 8) ? 0 : 1;
}
