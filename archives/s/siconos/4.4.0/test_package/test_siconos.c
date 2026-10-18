#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "NumericsMatrix.h"
#include "LinearComplementarityProblem.h"
#include "LCP_Solvers.h"
#include "NonSmoothDrivers.h"
#include "SiconosBlas.h"
#include "SiconosLapack.h"
#include "SolverOptions.h"
#include "lcp_cst.h"
static int checks = 0, failures = 0;
static void check(int ok, const char *name) {
  ++checks; if (!ok) ++failures;
  printf("[%s] %s\n", ok ? "PASS" : "FAIL", name);
}
int main(void) {
  NumericsMatrix *a = NM_create(NM_DENSE, 2, 2);
  check(a != NULL && a->matrix0 != NULL, "dense allocation");
  if (!a || !a->matrix0) return 1;
  /* Non-symmetric column-major matrix exposes layout mistakes. */
  a->matrix0[0] = 3; a->matrix0[1] = 1;
  a->matrix0[2] = 2; a->matrix0[3] = 4;
  double rhs[2] = {7, 9};
  check(NM_gesv(a, rhs, true) == 0, "dense LAPACK solve");
  check(fabs(rhs[0] - 1) < 1e-12 && fabs(rhs[1] - 2) < 1e-12,
        "dense solution and column-major layout");
  double x[2] = {1, 2}, y[2] = {0, 0};
  NM_gemv(1, a, x, 0, y);
  check(fabs(y[0] - 7) < 1e-12 && fabs(y[1] - 9) < 1e-12,
        "preserved matrix and BLAS product");
  NM_free(a);
  NumericsMatrix *identity = NM_eye(3);
  check(identity != NULL, "sparse identity allocation");
  if (!identity) return 1;
  double sx[3] = {2, -3, 7}, sy[3] = {1, 1, 1};
  NM_gemv(2, identity, sx, 3, sy);
  check(fabs(sy[0] - 7) < 1e-12 && fabs(sy[1] + 3) < 1e-12 &&
        fabs(sy[2] - 17) < 1e-12, "sparse CXSparse product");
  NM_free(identity);
  a = NM_create(NM_DENSE, 2, 2);
  if (!a || !a->matrix0) return 1;
  a->matrix0[0] = 2; a->matrix0[1] = -1;
  a->matrix0[2] = -1; a->matrix0[3] = 2;
  double q[2] = {-1, -1};
  LinearComplementarityProblem problem = {2, a, q};
  const int solvers[] = {SICONOS_LCP_LEMKE, SICONOS_LCP_PGS, SICONOS_LCP_QP};
  const char *names[] = {"Lemke", "PGS", "Fortran QL0001"};
  for (int k = 0; k < 3; ++k) {
    SolverOptions *options = solver_options_create(solvers[k]);
    if (!options) return 1;
    double z[2] = {0, 0}, w[2] = {0, 0};
    char label[96];
    snprintf(label, sizeof(label), "%s LCP convergence", names[k]);
    check(linearComplementarity_driver(&problem, z, w, options) == 0, label);
    snprintf(label, sizeof(label), "%s complementarity solution", names[k]);
    check(fabs(z[0] - 1) < 1e-6 && fabs(z[1] - 1) < 1e-6 &&
          fabs(w[0]) < 1e-6 && fabs(w[1]) < 1e-6,
          label);
    solver_options_delete(options);
    free(options);
  }
  q[0] = 2; q[1] = 3;
  SolverOptions *options = solver_options_create(SICONOS_LCP_LEMKE);
  if (!options) return 1;
  double z[2] = {0, 0}, w[2] = {0, 0};
  check(linearComplementarity_driver(&problem, z, w, options) == 0,
        "noncontact LCP convergence");
  check(fabs(z[0]) < 1e-12 && fabs(z[1]) < 1e-12 &&
        fabs(w[0] - 2) < 1e-12 && fabs(w[1] - 3) < 1e-12,
        "noncontact branch preserves positive residual");
  solver_options_delete(options); free(options); NM_free(a);
  printf("CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
  return failures ? 1 : 0;
}
