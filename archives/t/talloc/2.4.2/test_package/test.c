#include <stdio.h>
#include <string.h>
#include <talloc.h>

int main(void) {
    /* Create a talloc context */
    void *ctx = talloc_new(NULL);
    if (!ctx) {
        fprintf(stderr, "FAIL: talloc_new returned NULL\n");
        return 1;
    }

    /* Allocate memory from the context */
    char *str = talloc_strdup(ctx, "hello talloc");
    if (!str) {
        fprintf(stderr, "FAIL: talloc_strdup returned NULL\n");
        talloc_free(ctx);
        return 1;
    }

    /* Verify the string content */
    if (strcmp(str, "hello talloc") != 0) {
        fprintf(stderr, "FAIL: string mismatch: %s\n", str);
        talloc_free(ctx);
        return 1;
    }

    /* Verify allocation size is reasonable */
    size_t str_size = talloc_get_size(str);
    if (str_size < 12) {  /* "hello talloc" is 12 chars + null */
        fprintf(stderr, "FAIL: str size too small: %zu\n", str_size);
        talloc_free(ctx);
        return 1;
    }

    /* Use talloc_realloc to grow the string */
    char *str2 = talloc_realloc(ctx, str, char, 32);
    if (!str2) {
        fprintf(stderr, "FAIL: talloc_realloc returned NULL\n");
        talloc_free(ctx);
        return 1;
    }

    printf("talloc test: %s (size=%zu, realloc_size=%zu)\n",
           str2, str_size, talloc_get_size(str2));

    /* Free everything - talloc_free should return 0 on success */
    int ret = talloc_free(ctx);
    if (ret != 0) {
        fprintf(stderr, "FAIL: talloc_free returned %d\n", ret);
        return 1;
    }

    printf("talloc 2.4.2: ALL TESTS PASSED\n");
    return 0;
}
