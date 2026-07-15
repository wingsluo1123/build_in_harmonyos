#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <readline/readline.h>
#include <readline/history.h>

int main(void) {
    /* Verify readline version API */
    if (rl_library_version == NULL) {
        fprintf(stderr, "FAIL: rl_library_version is NULL\n");
        return 1;
    }
    printf("readline version: %s\n", rl_library_version);

    if (rl_readline_version != 0x0802) {
        fprintf(stderr, "FAIL: rl_readline_version=0x%x, expected 0x802\n", rl_readline_version);
        return 1;
    }

    /* Test history API */
    add_history("test_command_1");
    add_history("test_command_2");

    HIST_ENTRY **entries = history_list();
    if (entries == NULL) {
        fprintf(stderr, "FAIL: history_list() returned NULL after add_history\n");
        return 1;
    }

    int count = 0;
    for (int i = 0; entries[i] != NULL; i++) {
        count++;
    }
    if (count != 2) {
        fprintf(stderr, "FAIL: expected 2 history entries, got %d\n", count);
        return 1;
    }

    printf("history entries: %d\n", count);
    printf("All readline API tests passed\n");
    return 0;
}
