#include <SWI-Prolog.h>
#include <signal.h>
#include <stdint.h>

static foreign_t native_sum(term_t left, term_t right, term_t result)
{
    int64_t a, b;
    if (!PL_get_int64_ex(left, &a) || !PL_get_int64_ex(right, &b))
        return FALSE;
    return PL_unify_int64(result, a + b);
}

static foreign_t native_altstack_token(term_t token)
{
    stack_t current;
    if (sigaltstack(NULL, &current) != 0)
        return PL_resource_error("alternate_signal_stack");
    uint64_t value = (current.ss_flags & SS_DISABLE) ? 0 : (uintptr_t)current.ss_sp;
    return PL_unify_uint64(token, value);
}

install_t install(void)
{
    PL_register_foreign("native_sum", 3, native_sum, 0);
    PL_register_foreign("native_altstack_token", 1, native_altstack_token, 0);
}
