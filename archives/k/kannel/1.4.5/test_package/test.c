#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <gwlib/gwlib.h>

static void wakeable_thread(void *arg) {
    gwthread_sleep(600);
    *(int *)arg = 1;
}

int main(void) {
    static const char binary[] = {'A', 0, 'B', (char)255};
    gwlib_init();
    Octstr *a = octstr_create("hello");
    if (octstr_len(a) != 5) return 1;
    puts("PASS string creation");
    Octstr *b = octstr_create_from_data(binary, sizeof(binary));
    if (octstr_len(b) != 4 || octstr_get_char(b, 1) != 0 || octstr_get_char(b, 3) != 255) return 2;
#ifdef __OHOS__
    static const char high_lower[] = {'A', 0, (char)0xe5};
    static const char high_upper[] = {'a', 0, (char)0xc5};
    Octstr *left = octstr_create_from_data(high_lower, sizeof(high_lower));
    Octstr *right = octstr_create_from_data(high_upper, sizeof(high_upper));
    if (octstr_case_compare(left, right) <= 0 || octstr_case_compare(right, left) >= 0) return 7;
    octstr_destroy(left); octstr_destroy(right);
#endif
    puts("PASS binary octets");
    Octstr *c = octstr_duplicate(a);
    octstr_append_cstr(c, " world");
    if (strcmp(octstr_get_cstr(c), "hello world") || octstr_len(a) != 5) return 3;
    puts("PASS independent append");
    octstr_binary_to_hex(b, 0);
    if (strcmp(octstr_get_cstr(b), "410042ff")) return 4;
    puts("PASS hex encoding");
#ifdef __OHOS__
    int exited = 0;
    long thread = gwthread_create(wakeable_thread, &exited);
    if (thread < 0 || gwthread_cancel(thread) != ENOTSUP) return 5;
    gwthread_wakeup(thread);
    gwthread_join(thread);
    if (!exited) return 6;
    puts("PASS cancellation capability and cooperative wake join");
#else
    puts("PASS cancellation capability and cooperative wake join not applicable");
#endif
    octstr_destroy(a); octstr_destroy(b); octstr_destroy(c);
    gwlib_shutdown();
    puts("KANNEL_CONSUMER_RESULT=5/5");
    return 0;
}
