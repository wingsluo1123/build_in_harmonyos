#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <chm_lib.h>

int main(void)
{
    /* Test: chm_open on a non-existent file must return NULL */
    struct chmFile *h = chm_open("/nonexistent/chmlib_test_file_does_not_exist.chm");
    if (h != NULL) {
        fprintf(stderr, "FAIL: chm_open returned non-NULL for a non-existent file\n");
        chm_close(h);
        return 1;
    }

    /* Test: chm_close(NULL) should be safe (defensive check) */
    chm_close(NULL);

    /* Test: chm_resolve_object on NULL handle returns failure */
    struct chmUnitInfo ui;
    memset(&ui, 0, sizeof(ui));
    int ret = chm_resolve_object(NULL, "/test", &ui);
    if (ret != CHM_RESOLVE_FAILURE) {
        fprintf(stderr, "FAIL: chm_resolve_object on NULL handle expected CHM_RESOLVE_FAILURE\n");
        return 1;
    }

    printf("chmlib test PASSED: all API safety checks passed\n");
    return 0;
}
