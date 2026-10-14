#include <libskk/libskk.h>
#include <stdio.h>
#include <string.h>

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "FAIL: %s\n", message); \
            goto cleanup; \
        } \
        ++checks; \
    } while (0)

int main(void) {
    int checks = 0;
    int result = 1;
    SkkEmptyDict *empty = NULL;
    SkkContext *context = NULL;
    const gchar *output = NULL;

    skk_init();
    empty = skk_empty_dict_new();
    CHECK(empty != NULL, "create empty dictionary");

    SkkDict *dictionaries[] = {SKK_DICT(empty)};
    context = skk_context_new(dictionaries, 1);
    CHECK(context != NULL, "create libskk context");

    CHECK(skk_context_process_key_events(context, "a i r"),
          "process romaji input");
    output = skk_context_peek_output(context); /* Borrowed from context. */
    CHECK(output != NULL && strcmp(output, "あい") == 0,
          "romaji input converts to hiragana");

    CHECK(strcmp(skk_context_get_preedit(context), "r") == 0,
          "incomplete romaji remains in preedit");
    result = 0;
    printf("libskk consumer assertions: %d passed\n", checks);

cleanup:
    if (context != NULL) {
        g_object_unref(context);
    }
    if (empty != NULL) {
        g_object_unref(empty);
    }
    return result;
}