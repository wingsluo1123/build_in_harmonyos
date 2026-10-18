/* Consumer test for levmar 2.6.
 *
 * Solves two non-linear least squares problems through the public API
 * (unconstrained `dlevmar_dif` and box constrained `dlevmar_bc_dif`, both of
 * which upstream declares without LAPACK) and checks the convergence contract
 * instead of only compiling against the library.
 */
#include <levmar.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NPAR 3
#define NMEAS 20

static const double TRUE_P[NPAR] = {5.0, 0.8, 0.35};

/* y = p0 * exp(-p1 * t) + p2 */
static void expmodel(double *p, double *hx, int m, int n, void *adata)
{
    const double *t = (const double *)adata;
    int i;

    (void)m;
    for (i = 0; i < n; ++i)
        hx[i] = p[0] * exp(-p[1] * t[i]) + p[2];
}

static int failures = 0;

static void check(int cond, const char *msg)
{
    if (cond) {
        printf("ok   : %s\n", msg);
    } else {
        printf("FAIL : %s\n", msg);
        ++failures;
    }
}

static int params_match(const double *p, double tol)
{
    return fabs(p[0] - TRUE_P[0]) < tol &&
           fabs(p[1] - TRUE_P[1]) < tol &&
           fabs(p[2] - TRUE_P[2]) < tol;
}

int main(void)
{
    double t[NMEAS], x[NMEAS], p[NPAR];
    double opts[LM_OPTS_SZ], info[LM_INFO_SZ];
    double *work;
    int i, ret;

    for (i = 0; i < NMEAS; ++i) {
        t[i] = 0.1 * (i + 1);
        x[i] = TRUE_P[0] * exp(-TRUE_P[1] * t[i]) + TRUE_P[2];
    }

    opts[0] = LM_INIT_MU;
    opts[1] = 1e-15;
    opts[2] = 1e-15;
    opts[3] = 1e-20;
    opts[4] = LM_DIFF_DELTA;

    work = (double *)malloc(LM_DIF_WORKSZ(NPAR, NMEAS) * sizeof(double));
    check(work != NULL, "work buffer allocated with LM_DIF_WORKSZ");
    if (work == NULL)
        return 1;

    /* 1) unconstrained minimisation, finite difference Jacobian */
    p[0] = 1.0;
    p[1] = 0.1;
    p[2] = 0.0;
    ret = dlevmar_dif(expmodel, p, x, NPAR, NMEAS, 1000, opts, info, work, NULL,
                      (void *)t);
    printf("dlevmar_dif    : ret=%d reason=%g |e|=%g p=(%.6f %.6f %.6f)\n",
           ret, info[6], info[1], p[0], p[1], p[2]);
    check(ret > 0 && ret < 1000, "dlevmar_dif converged before the iteration limit");
    check(info[1] < 1e-8, "dlevmar_dif final residual norm below 1e-8");
    check(params_match(p, 1e-3), "dlevmar_dif recovered the model parameters within 1e-3");

    /* 2) box constrained minimisation, still LAPACK free */
    {
        double lb[NPAR] = {0.0, 0.0, 0.0};
        double ub[NPAR] = {10.0, 5.0, 5.0};
        double dscl[NPAR] = {1.0, 1.0, 1.0};

        p[0] = 1.0;
        p[1] = 0.1;
        p[2] = 0.0;
        ret = dlevmar_bc_dif(expmodel, p, x, NPAR, NMEAS, lb, ub, dscl, 1000,
                             opts, info, work, NULL, (void *)t);
        printf("dlevmar_bc_dif : ret=%d reason=%g |e|=%g p=(%.6f %.6f %.6f)\n",
               ret, info[6], info[1], p[0], p[1], p[2]);
        check(ret > 0 && info[1] < 1e-8, "dlevmar_bc_dif converged inside the box");
        check(params_match(p, 1e-3),
              "dlevmar_bc_dif reached the same minimum as the unconstrained run");
    }

    /* 3) public constants of the generated header are usable by a consumer */
    check(LM_INFO_SZ == 10 && LM_ERROR == -1,
          "generated levmar.h exposes LM_INFO_SZ / LM_ERROR");

    free(work);
    printf("%s (%d failed assertion(s))\n", failures ? "TEST FAILED" : "TEST PASSED",
           failures);
    return failures ? 1 : 0;
}
