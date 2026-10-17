#include <SWI-Prolog.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    stack_t original, current, host = {0};
    if (sigaltstack(NULL, &original) != 0)
        return 10;
    void *host_memory = malloc(SIGSTKSZ);
    if (!host_memory)
        return 11;
    host.ss_sp = host_memory;
    host.ss_size = SIGSTKSZ;
    if (sigaltstack(&host, NULL) != 0)
        return 12;
    char *argv[] = {"embed_swi", "-q", "-f", "none", NULL};
    if (!PL_initialise(4, argv))
        return 1;
    if (sigaltstack(NULL, &current) != 0 || current.ss_flags != host.ss_flags ||
        current.ss_sp != host_memory || current.ss_size != host.ss_size)
        return 13;
    fid_t frame = PL_open_foreign_frame();
    term_t args = PL_new_term_refs(2);
    if (!PL_put_atom_chars(args, "HarmonyOS"))
        return 2;
    predicate_t predicate = PL_predicate("atom_length", 2, "system");
    if (!PL_call_predicate(NULL, PL_Q_NODEBUG, predicate, args))
        return 3;
    int length = 0;
    if (!PL_get_integer(args + 1, &length) || length != 9)
        return 4;
    PL_discard_foreign_frame(frame);
    if (PL_cleanup(0) != PL_CLEANUP_SUCCESS)
        return 5;
    if (sigaltstack(NULL, &current) != 0 || current.ss_flags != host.ss_flags ||
        current.ss_sp != host_memory || current.ss_size != host.ss_size)
        return 14;
    if (sigaltstack(&original, NULL) != 0)
        return 15;
    free(host_memory);
    puts("HOST_ALTSTACK: preserved across PL_initialise and PL_cleanup(0)");
    puts("EMBEDDING: 1/1 passed");
    return 0;
}
