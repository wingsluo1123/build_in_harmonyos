#include <stdio.h>
#include <stdlib.h>
#include <gc.h>

int main(void) {
    GC_INIT();

    /* Allocate some objects through the GC */
    int *p = (int *)GC_MALLOC(sizeof(int));
    if (p == NULL) {
        fprintf(stderr, "GC_MALLOC failed\n");
        return 1;
    }
    *p = 42;

    /* Trigger a collection */
    GC_gcollect();

    /* Verify the value survived collection */
    if (*p != 42) {
        fprintf(stderr, "Value lost after GC: expected 42, got %d\n", *p);
        return 1;
    }

    printf("test bdw-gc 8.2.6: OK (GC_MALLOC + GC_gcollect verified)\n");
    return 0;
}
