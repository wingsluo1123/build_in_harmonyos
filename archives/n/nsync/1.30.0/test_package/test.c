#include <stdio.h>
#include <stdlib.h>
#include <nsync_mu.h>
#include <nsync_cv.h>
#include <nsync_once.h>
#include <nsync_counter.h>

void init_routine(void) {
    /* no-op initializer */
}

int main(void) {
    /* Test 1: nsync_mu (mutex) */
    printf("Testing nsync_mu... ");
    nsync_mu mu;
    nsync_mu_init(&mu);
    nsync_mu_lock(&mu);
    nsync_mu_unlock(&mu);
    printf("PASS\n");

    /* Test 2: nsync_once (run-once initialization) */
    printf("Testing nsync_run_once... ");
    nsync_once once = NSYNC_ONCE_INIT;
    nsync_run_once(&once, init_routine);
    printf("PASS\n");

    /* Test 3: nsync_cv (condition variable) */
    printf("Testing nsync_cv... ");
    nsync_cv cv;
    nsync_cv_init(&cv);
    printf("PASS\n");

    /* Test 4: nsync_counter (waitable counter) */
    printf("Testing nsync_counter... ");
    nsync_counter c = nsync_counter_new(1);
    nsync_counter_add(c, -1);
    nsync_counter_free(c);
    printf("PASS\n");

    printf("\nAll nsync tests passed!\n");
    return 0;
}
