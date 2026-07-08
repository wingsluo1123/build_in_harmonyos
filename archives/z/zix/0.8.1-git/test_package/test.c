#include <stdio.h>
#include <stdlib.h>
#include <zix/zix.h>
#include <zix/allocator.h>

int main(void) {
    const ZixAllocator* allocator = zix_default_allocator();
    void* ptr = zix_malloc(allocator, 128);
    if (!ptr) {
        fprintf(stderr, "zix_malloc failed\n");
        return 1;
    }
    zix_free(allocator, ptr);
    printf("zix allocator test: OK\n");
    return 0;
}
