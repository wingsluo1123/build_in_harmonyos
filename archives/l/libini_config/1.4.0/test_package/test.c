#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ini_configobj.h>

static int test_ini_config(void)
{
    static const char input[] =
        "[main]\n"
        "answer = 42\n"
        "name = libini_config\n";
    struct ini_cfgfile *file_ctx = NULL;
    struct ini_cfgobj *config = NULL;
    struct value_obj *value = NULL;
    char *name = NULL;
    int error = 0;
    int answer;

    error = ini_config_file_from_mem((void *)input, (uint32_t)strlen(input),
                                     &file_ctx);
    if (error != 0) {
        fprintf(stderr, "ini_config_file_from_mem failed: %d\n", error);
        return 1;
    }
    printf("CASE PASS: file_from_mem\n");

    error = ini_config_create(&config);
    if (error != 0) {
        fprintf(stderr, "ini_config_create failed: %d\n", error);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    printf("CASE PASS: config_create\n");

    error = ini_config_parse(file_ctx, INI_STOP_ON_ANY, INI_MV1S_ALLOW, 0,
                             config);
    if (error != 0) {
        fprintf(stderr, "ini_config_parse failed: %d\n", error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    printf("CASE PASS: config_parse\n");

    error = ini_get_config_valueobj("main", "answer", config,
                                    INI_GET_FIRST_VALUE, &value);
    if (error != 0 || value == NULL) {
        fprintf(stderr, "ini_get_config_valueobj(answer) failed: %d\n", error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    printf("CASE PASS: get_answer_valueobj\n");

    answer = ini_get_int_config_value(value, 1, 0, &error);
    if (error != 0 || answer != 42) {
        fprintf(stderr, "INI integer value was %d (error %d)\n", answer, error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    printf("CASE PASS: int_value_42\n");

    value = NULL;
    error = ini_get_config_valueobj("main", "name", config,
                                    INI_GET_FIRST_VALUE, &value);
    if (error != 0 || value == NULL) {
        fprintf(stderr, "ini_get_config_valueobj(name) failed: %d\n", error);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    printf("CASE PASS: get_name_valueobj\n");

    name = ini_get_string_config_value(value, &error);
    if (error != 0 || name == NULL || strcmp(name, "libini_config") != 0) {
        fprintf(stderr, "INI string value was unexpected (error %d)\n", error);
        free(name);
        ini_config_destroy(config);
        ini_config_file_destroy(file_ctx);
        return 1;
    }
    printf("CASE PASS: string_value_libini_config\n");

    free(name);
    ini_config_destroy(config);
    ini_config_file_destroy(file_ctx);
    return 0;
}

int main(void)
{
    if (test_ini_config() != 0) {
        return EXIT_FAILURE;
    }
    puts("libini_config public API test passed");
    return EXIT_SUCCESS;
}
