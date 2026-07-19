/* test.c — Consumer test for libmpc (GNU MPC) 1.4.1.
 *
 * This test substantively depends on the libmpc package by calling
 * its core API: mpc_init2, mpc_set_ui_ui, mpc_add, mpc_cmp_si_si,
 * mpc_clear. (R34 compliance)
 */
#include <stdio.h>
#include <mpc.h>

int main(void) {
    mpc_t a, b, c;

    /* Initialize with 256-bit precision */
    mpc_init2(a, 256);
    mpc_init2(b, 256);
    mpc_init2(c, 256);

    /* Set a = 1 + 2i, b = 3 + 4i */
    mpc_set_ui_ui(a, 1, 2, MPC_RNDNN);
    mpc_set_ui_ui(b, 3, 4, MPC_RNDNN);

    /* c = a + b = 4 + 6i */
    mpc_add(c, a, b, MPC_RNDNN);

    /* Verify: real(c) == 4, imag(c) == 6 */
    if (mpc_cmp_si_si(c, 4, 6) == 0) {
        printf("MPC test PASSED: (1+2i) + (3+4i) = 4+6i\n");
        mpc_clear(a);
        mpc_clear(b);
        mpc_clear(c);
        return 0;
    } else {
        printf("MPC test FAILED: expected 4+6i\n");
        mpc_clear(a);
        mpc_clear(b);
        mpc_clear(c);
        return 1;
    }
}
