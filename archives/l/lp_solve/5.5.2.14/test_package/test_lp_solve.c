/*
 * test_lp_solve.c — L1 smoke test for lp_solve library API
 * Solves a simple LP: maximize x1 + x2 subject to x1 + x2 <= 10
 * Expected objective value: 10.0
 */
#include <lp_lib.h>
#include <stdio.h>

int main(void) {
    lprec *lp = make_lp(0, 2);
    if (!lp) {
        fprintf(stderr, "ERROR: make_lp failed\n");
        return 1;
    }

    /* Objective: maximize x1 + x2 */
    set_maxim(lp);
    set_obj(lp, 1, 1.0);
    set_obj(lp, 2, 1.0);

    /* Constraint: x1 + x2 <= 10 */
    REAL row[] = {0, 1, 1};
    add_constraint(lp, row, LE, 10);

    int ret = solve(lp);
    if (ret != OPTIMAL) {
        fprintf(stderr, "ERROR: solve returned %d (expected OPTIMAL)\n", ret);
        delete_lp(lp);
        return 1;
    }

    double obj = get_objective(lp);
    double x1 = get_var_primalresult(lp, 1);
    double x2 = get_var_primalresult(lp, 2);

    printf("Objective: %.1f, x1=%.1f, x2=%.1f\n", obj, x1, x2);

    delete_lp(lp);

    /* Verify solution: objective should be 10.0 */
    if (obj < 9.99 || obj > 10.01) {
        fprintf(stderr, "ERROR: objective %.4f != 10.0\n", obj);
        return 1;
    }

    printf("PASS: lp_solve API test OK\n");
    return 0;
}
