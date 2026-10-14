#include <stdio.h>
#include <string.h>

#include <chewing/chewing.h>

static int checks_passed = 0;

#define CHECK(cond, label) do { \
    if (!(cond)) { \
        printf("FAIL: %s (line %d)\n", label, __LINE__); \
        return 1; \
    } \
    printf("PASS: %s\n", label); \
    checks_passed++; \
} while (0)

int main(void) {
    const char *ver = chewing_version();
    CHECK(ver != NULL && strlen(ver) > 0, "chewing_version non-empty");

    ChewingContext *ctx = chewing_new();
    CHECK(ctx != NULL, "chewing_new creates context");

    CHECK(chewing_set_KBType(ctx, KB_DEFAULT) == 0
        && chewing_get_KBType(ctx) == KB_DEFAULT, "KB type set/get roundtrip");

    chewing_set_ChiEngMode(ctx, CHINESE_MODE);
    CHECK(chewing_get_ChiEngMode(ctx) == CHINESE_MODE, "chinese/english mode roundtrip");

    chewing_set_candPerPage(ctx, 9);
    CHECK(chewing_get_candPerPage(ctx) == 9, "candPerPage set/get roundtrip");

    CHECK(chewing_Reset(ctx) == 0 && chewing_buffer_Check(ctx) == 0,
        "Reset clears preedit buffer");

    chewing_delete(ctx);

    printf("All %d libchewing consumer checks passed\n", checks_passed);
    if (checks_passed != 6) {
        printf("expected 6 checks, got %d\n", checks_passed);
        return 1;
    }
    return 0;
}
