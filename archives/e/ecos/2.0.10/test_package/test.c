#include <ecos.h>
#include <ecos_bb.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;
static int checks = 0;
#define CHECK(label, expression) do { ++checks; if (!(expression)) { ++failures; fprintf(stderr, "FAIL: %s\n", label); } } while (0)

int main(void) {
    /* Arrays passed to ECOS must remain alive until cleanup. */
    pfloat gx[2] = {-1, 1}, c[1] = {1}, h[2] = {-2, 5};
    idxint gp[2] = {0, 2}, gi[2] = {0, 1};
    pwork *w;
    idxint rc;
    CHECK("version", strcmp(ECOS_ver(), "2.0.10") == 0);
#ifdef EXPECT_LONG
    CHECK("long index ABI", sizeof(idxint) == sizeof(SuiteSparse_long));
#else
    CHECK("32bit index ABI", sizeof(idxint) == sizeof(int));
#endif
    w = ECOS_setup(1, 2, 0, 2, 0, NULL, 0, gx, gp, gi, NULL, NULL, NULL, c, h, NULL);
    CHECK("LP setup", w != NULL);
    if (w) {
        w->stgs->verbose = 0; rc = ECOS_solve(w);
        CHECK("LP optimal status", rc == ECOS_OPTIMAL);
        CHECK("LP minimizer", fabs(w->x[0] - 2) < 1e-6);
        CHECK("LP primal residual", w->info->pres < 1e-6);
        CHECK("LP dual residual", w->info->dres < 1e-6);
        c[0] = -1; ECOS_updateData(w, gx, NULL, c, h, NULL);
        rc = ECOS_solve(w);
        CHECK("update optimal status", rc == ECOS_OPTIMAL);
        CHECK("update maximizer", fabs(w->x[0] - 5) < 1e-6);
        ECOS_cleanup(w, 0);
    }
    c[0] = 1; h[0] = -3; h[1] = 1;
    w = ECOS_setup(1, 2, 0, 2, 0, NULL, 0, gx, gp, gi, NULL, NULL, NULL, c, h, NULL);
    CHECK("infeasible setup", w != NULL);
    if (w) {
        w->stgs->verbose = 0; rc = ECOS_solve(w);
        CHECK("infeasible status", rc == ECOS_PINF);
        ECOS_cleanup(w, 0);
    }
    { /* min -x, x >= 0 */
        pfloat ug[1] = {-1}, uc[1] = {-1}, uh[1] = {0};
        idxint up[2] = {0, 1}, ui[1] = {0};
        w = ECOS_setup(1, 1, 0, 1, 0, NULL, 0, ug, up, ui, NULL, NULL, NULL, uc, uh, NULL);
        CHECK("unbounded setup", w != NULL);
        if (w) { w->stgs->verbose = 0; rc = ECOS_solve(w); CHECK("unbounded status", rc == ECOS_DINF); ECOS_cleanup(w, 0); }
    }
    { /* min t, (t,3,4) in the Lorentz cone; optimum t=5. */
        pfloat sg[1] = {-1}, sc[1] = {1}, sh[3] = {0, 3, 4};
        idxint sp[2] = {0, 1}, si[1] = {0}, cone[1] = {3};
        w = ECOS_setup(1, 3, 0, 0, 1, cone, 0, sg, sp, si, NULL, NULL, NULL, sc, sh, NULL);
        CHECK("SOCP setup", w != NULL);
        if (w) { w->stgs->verbose = 0; rc = ECOS_solve(w); CHECK("SOCP optimal status", rc == ECOS_OPTIMAL); CHECK("SOCP minimizer", fabs(w->x[0] - 5) < 1e-6); CHECK("SOCP primal residual", w->info->pres < 1e-6); ECOS_cleanup(w, 0); }
    }
    { /* min x, x >= .5, x boolean; optimum x=1. */
        pfloat bg[1] = {-1}, bc[1] = {1}, bh[1] = {-0.5};
        idxint bp[2] = {0, 1}, bi[1] = {0}, bools[1] = {0};
        ecos_bb_pwork *bb = ECOS_BB_setup(1, 1, 0, 1, 0, NULL, 0, bg, bp, bi, NULL, NULL, NULL, bc, bh, NULL, 1, bools, 0, NULL, NULL);
        CHECK("BB setup", bb != NULL);
        if (bb) { bb->stgs->verbose = 0; rc = ECOS_BB_solve(bb); CHECK("BB optimal status", rc == ECOS_OPTIMAL); CHECK("BB boolean minimizer", fabs(bb->x[0] - 1) < 1e-6); ECOS_BB_cleanup(bb, 0); }
    }
    printf("ECOS_CONSUMER: %d/%d checks passed\n", checks - failures, checks);
    return failures ? 1 : 0;
}
