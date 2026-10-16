/* phast consumer test (HarmonyOS PC / os=OHOS)
 *
 * 通过 phast 公共 C API 做特征值分解（eigen.h / matrix.h），
 * 运行期实际调用 libphast.a 内部经补丁直连的参考 LAPACK dgeev_，
 * 验证「消费者链接 phast::phast → 传递 lapack/3.12.1 → flang Fortran
 * 运行时」整条链在鸿蒙真机上的可行性。
 *
 * 用例：对称矩阵 [[2,1],[1,2]]，特征值应为 {3, 1}（实数）。
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

/* phast 公共头非自包含（上游即如此，依赖包含顺序）：
   vector.h/matrix.h 须先于 complex_vector.h/complex_matrix.h */
#include <phast/vector.h>
#include <phast/matrix.h>
#include <phast/complex.h>
#include <phast/complex_vector.h>
#include <phast/complex_matrix.h>
#include <phast/eigen.h>

static int failures = 0;

static void check(int cond, const char *what) {
  if (cond) {
    printf("PASS: %s\n", what);
  } else {
    printf("FAIL: %s\n", what);
    failures++;
  }
}

int main(void) {
  const int n = 2;
  const double tol = 1e-9;

  Matrix *m = mat_new(n, n);
  mat_set(m, 0, 0, 2.0);
  mat_set(m, 0, 1, 1.0);
  mat_set(m, 1, 0, 1.0);
  mat_set(m, 1, 1, 2.0);

  Zvector *eval = zvec_new(n);
  Zmatrix *revect = zmat_new(n, n);
  Zmatrix *levect = zmat_new(n, n);

  int rc = mat_diagonalize(m, eval, revect, levect);
  check(rc == 0, "mat_diagonalize returns 0 (LAPACK dgeev_ via phast)");

  if (rc == 0) {
    double e[2];
    int i;
    for (i = 0; i < n; i++) {
      Complex c = zvec_get(eval, i);
      e[i] = c.x;
      printf("  eval[%d] = %.12f + %.12fi\n", i, c.x, c.y);
      check(fabs(c.y) < tol, "eigenvalue is real (imaginary part ~ 0)");
    }
    int has3 = (fabs(e[0] - 3.0) < tol) || (fabs(e[1] - 3.0) < tol);
    int has1 = (fabs(e[0] - 1.0) < tol) || (fabs(e[1] - 1.0) < tol);
    check(has3, "eigenvalue 3.0 present");
    check(has1, "eigenvalue 1.0 present");
  }

  zvec_free(eval);
  zmat_free(revect);
  zmat_free(levect);
  mat_free(m);

  if (failures > 0) {
    printf("%d check(s) FAILED\n", failures);
    return 1;
  }
  printf("All phast consumer checks passed (HarmonyOS PC).\n");
  return 0;
}
