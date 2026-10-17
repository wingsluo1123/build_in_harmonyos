#define _GNU_SOURCE
#include <SWI-Prolog.h>
#include <dlfcn.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static stack_t original;
static void *host_memory;
static int init_preserved;
static stack_t host_registration;

extern int __real_PL_initialise(int argc, char **argv);

static void verify_host_after_cleanup(void)
{
    stack_t current;
    int preserved = sigaltstack(NULL, &current) == 0 &&
        current.ss_flags == host_registration.ss_flags &&
        current.ss_sp == host_registration.ss_sp && current.ss_size == host_registration.ss_size;
    printf("UPSTREAM_CALC_HOST_STACK_INIT=%s\n", init_preserved ? "preserved" : "overwritten");
    printf("UPSTREAM_CALC_HOST_STACK_AFTER_PL_HALT=%s\n", preserved ? "preserved" : "lost");
    if (sigaltstack(&original, NULL) != 0)
        _Exit(81);
    free(host_memory);
    fflush(stdout);
    if (!init_preserved || !preserved)
        _Exit(1);
}

int __wrap_PL_initialise(int argc, char **argv)
{
    Dl_info runtime;
    if (!dladdr((void *)__real_PL_initialise, &runtime))
        return 0;
    printf("RUNTIME_LIBRARY=%s\n", runtime.dli_fname);
    stack_t host = {0}, current;
    if (sigaltstack(NULL, &original) != 0 || !(host_memory = malloc(SIGSTKSZ)))
        return 0;
    host.ss_sp = host_memory;
    host.ss_size = SIGSTKSZ;
    host_registration = host;
    if (sigaltstack(&host, NULL) != 0 || atexit(verify_host_after_cleanup) != 0)
        return 0;
    int result = __real_PL_initialise(argc, argv);
    if (!result)
        return 0;
    init_preserved = sigaltstack(NULL, &current) == 0 &&
        current.ss_flags == host_registration.ss_flags &&
        current.ss_sp == host_registration.ss_sp && current.ss_size == host_registration.ss_size;

    const char *source = getenv("SWI_CALC_SOURCE");
    if (!source)
        return 0;
    term_t file = PL_new_term_ref();
    if (!PL_put_atom_chars(file, source) ||
        !PL_call_predicate(NULL, PL_Q_NODEBUG, PL_predicate("consult", 1, "system"), file))
        return 0;
    return result;
}
