/*
 * test_package/test.c — R34 test for guile 2.2.7
 *
 * Compiles and links against libguile-2.2, then evaluates Scheme (+ 1 2)
 * via the C API to verify the library is functional.
 */
#include <libguile/__scm.h>
#include <libguile/threads.h>      /* scm_with_guile */
#include <libguile/strports.h>    /* scm_c_eval_string */
#include <libguile/numbers.h>     /* scm_to_int */
#include <stdio.h>
#include <stdlib.h>

static void *inner_main(void *data)
{
    SCM result = scm_c_eval_string("(+ 1 2)");
    int val = scm_to_int(result);
    printf("guile test: (+ 1 2) = %d\n", val);
    fflush(stdout);
    if (val != 3) {
        fprintf(stderr, "FAIL: expected 3, got %d\n", val);
        return (void *)(intptr_t)1;
    }
    printf("guile test: PASS\n");
    return NULL;
}

int main(void)
{
    scm_with_guile(inner_main, NULL);
    return 0;
}
