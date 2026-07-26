#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zix/zix.h>
#include <zix/allocator.h>

int main(void) {
    ZixAllocator* allocator = zix_default_allocator();
    if (!allocator) {
        fprintf(stderr, "zix_default_allocator returned NULL\n");
        return 1;
    }
    void* ptr = zix_malloc(allocator, 128);
    if (!ptr) {
        fprintf(stderr, "zix_malloc failed\n");
        return 1;
    }
    /* Verify the allocation is usable */
    memset(ptr, 0, 128);
    zix_free(allocator, ptr);
    printf("zix allocator test: OK\n");
    return 0;
}
