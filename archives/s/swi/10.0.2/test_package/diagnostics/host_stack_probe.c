#define _GNU_SOURCE
#include <SWI-Prolog.h>
#include <dlfcn.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    Dl_info runtime;
    if (!dladdr((void *)PL_initialise, &runtime))
        return 9;
    printf("RUNTIME_LIBRARY=%s\n", runtime.dli_fname);
    stack_t original, current;
    if (sigaltstack(NULL, &original) != 0)
        return 10;
    printf("INITIAL_STACK_FLAGS=%d SIZE=%zu POINTER=%p\n", original.ss_flags, original.ss_size, original.ss_sp);
    void *memory = malloc(SIGSTKSZ);
    if (!memory)
        return 12;
    stack_t host = {0};
    host.ss_sp = memory;
    host.ss_size = SIGSTKSZ;
    if (sigaltstack(&host, NULL) != 0)
        return 13;

    char *argv[] = {"b_host_stack", "-q", "-f", "none", NULL};
    if (!PL_initialise(4, argv))
        return 14;
    if (sigaltstack(NULL, &current) != 0)
        return 15;
    int preserved_init = current.ss_flags == host.ss_flags &&
        current.ss_sp == memory && current.ss_size == host.ss_size;
    printf("HOST_STACK_AT_INIT=%s\n", preserved_init ? "preserved" : "overwritten");
    fflush(stdout);
    term_t goal = PL_new_term_ref();
    int called = PL_chars_to_term("42 =:= 6*7", goal) && PL_call(goal, NULL);
    printf("REAL_PROLOG_CALL=%d\n", called);
    fflush(stdout);
    int cleanup = PL_cleanup(0);
    if (sigaltstack(NULL, &current) != 0)
        return 16;
    int preserved_cleanup = current.ss_flags == host.ss_flags &&
        current.ss_sp == memory && current.ss_size == host.ss_size;
    printf("HOST_STACK_AFTER_CLEANUP=%s\n", preserved_cleanup ? "preserved" : "lost");
    fflush(stdout);
    if (sigaltstack(&original, NULL) != 0)
        return 17;
    free(memory);
    printf("HOST_STACK_TEST=%s\n", preserved_init && preserved_cleanup && called && cleanup == PL_CLEANUP_SUCCESS ? "passed" : "failed");
    return preserved_init && preserved_cleanup && called && cleanup == PL_CLEANUP_SUCCESS ? 0 : 1;
}
