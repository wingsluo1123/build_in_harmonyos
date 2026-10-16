/* GSL linker stubs for the static upstream GTest binary (indi-eqmod rule4).
 *
 * These symbols are referenced by libindiAlignmentDriver.a (BuiltInMathPlugin)
 * but are NEVER executed by the 8 upstream test cases: the tests exercise
 * encoder/hemisphere/scope-limits pure logic and only *construct* the EQMod
 * device (which registers math plugins without running any transform).
 * Providing them lets the static link close without pulling a full GSL build;
 * any accidental call would be a test-path bug caught immediately by the
 * assertion mismatch, not silently hidden.
 *
 * Signatures follow GSL 2.8 public API for documentation clarity.
 */
#include <stddef.h>

typedef struct gsl_matrix gsl_matrix;
typedef struct gsl_vector gsl_vector;
typedef struct gsl_permutation gsl_permutation;

/* gsl_matrix / gsl_vector / gsl_permutation memory API */
gsl_matrix *gsl_matrix_alloc(size_t n1, size_t n2) { (void)n1; (void)n2; return NULL; }
void gsl_matrix_free(gsl_matrix *m) { (void)m; }
double gsl_matrix_get(const gsl_matrix *m, size_t i, size_t j) { (void)m; (void)i; (void)j; return 0.0; }
int gsl_matrix_set(gsl_matrix *m, size_t i, size_t j, double x) { (void)m; (void)i; (void)j; (void)x; return 0; }
int gsl_matrix_set_zero(gsl_matrix *m) { (void)m; return 0; }
int gsl_matrix_set_identity(gsl_matrix *m) { (void)m; return 0; }
int gsl_matrix_memcpy(gsl_matrix *dest, const gsl_matrix *src) { (void)dest; (void)src; return 0; }

gsl_vector *gsl_vector_alloc(size_t n) { (void)n; return NULL; }
void gsl_vector_free(gsl_vector *v) { (void)v; }
double gsl_vector_get(const gsl_vector *v, size_t i) { (void)v; (void)i; return 0.0; }
int gsl_vector_set(gsl_vector *v, size_t i, double x) { (void)v; (void)i; (void)x; return 0; }
int gsl_vector_set_zero(gsl_vector *v) { (void)v; return 0; }

gsl_permutation *gsl_permutation_alloc(size_t n) { (void)n; return NULL; }
void gsl_permutation_free(gsl_permutation *p) { (void)p; }

/* BLAS / LINALG used by BuiltInMathPlugin::CalculateTransformMatrices */
int gsl_blas_dgemm(void *CblasTransA, double alpha, const gsl_matrix *A,
                   const gsl_matrix *B, double beta, gsl_matrix *C)
{
    (void)CblasTransA; (void)alpha; (void)A; (void)B; (void)beta; (void)C; return 0;
}
int gsl_blas_dgemv(void *CblasNoTrans, double alpha, const gsl_matrix *A,
                   const gsl_vector *x, double beta, gsl_vector *y)
{
    (void)CblasNoTrans; (void)alpha; (void)A; (void)x; (void)beta; (void)y; return 0;
}
int gsl_linalg_LU_decomp(gsl_matrix *A, gsl_permutation *p, int *signum)
{
    (void)A; (void)p; (void)signum; return 0;
}
double gsl_linalg_LU_det(gsl_matrix *LU, int signum) { (void)LU; (void)signum; return 0.0; }
int gsl_linalg_LU_invert(const gsl_matrix *LU, const gsl_permutation *p, gsl_matrix *inverse)
{
    (void)LU; (void)p; (void)inverse; return 0;
}
