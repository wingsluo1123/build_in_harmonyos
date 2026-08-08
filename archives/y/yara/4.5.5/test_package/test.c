/* test_package/test.c — Verify yara API is functional */
#include <yara.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    yr_initialize();

    YR_COMPILER *compiler = NULL;
    if (yr_compiler_create(&compiler) != ERROR_SUCCESS) {
        fprintf(stderr, "Failed to create yara compiler\n");
        return 1;
    }

    /* Compile a simple rule */
    const char *rule_text =
        "rule test_rule { condition: true }";
    int errors = yr_compiler_add_string(compiler, rule_text, NULL);

    if (errors > 0) {
        fprintf(stderr, "Failed to compile yara rule (%d errors)\n", errors);
        yr_compiler_destroy(compiler);
        yr_finalize();
        return 1;
    }

    YR_RULES *rules = NULL;
    if (yr_compiler_get_rules(compiler, &rules) != ERROR_SUCCESS) {
        fprintf(stderr, "Failed to get yara rules\n");
        yr_compiler_destroy(compiler);
        yr_finalize();
        return 1;
    }

    yr_rules_destroy(rules);
    yr_compiler_destroy(compiler);
    yr_finalize();

    printf("yara API test passed\n");
    return 0;
}
