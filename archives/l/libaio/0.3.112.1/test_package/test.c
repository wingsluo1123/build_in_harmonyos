#include <stdio.h>
#include <libaio.h>

int main(void) {
    io_context_t ctx = 0;

    /* Verify io_queue_init API is callable (links against libaio).
     * On some HarmonyOS kernel configs the io_setup syscall returns
     * -ENOSYS; this is a platform limitation, not a library defect.
     * The test validates linkage + API availability, not syscall success. */
    int ret = io_queue_init(1, &ctx);
    if (ret < 0) {
        printf("io_queue_init returned %d (syscall may be unsupported)\n", ret);
    } else {
        printf("io_queue_init succeeded\n");
    }

    /* Always call release to verify the symbol resolves at link time */
    io_queue_release(ctx);

    /* Verify io_pgetevents returns -ENOSYS (stub) instead of crashing
     * with SIGSYS on OHOS. This is the key fix in 0.3.112.1. */
    struct io_event events[1];
    ret = io_pgetevents(ctx, 0, 1, events, NULL, NULL);
    if (ret == -38 /* -ENOSYS */) {
        printf("io_pgetevents correctly returns -ENOSYS (stub)\n");
    } else {
        printf("io_pgetevents returned %d (expected -38)\n", ret);
        return 1;
    }

    printf("test libaio 0.3.112.1: PASSED\n");
    return 0;
}
