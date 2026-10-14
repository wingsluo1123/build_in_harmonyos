#include <libconfig.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #expr); exit(1); } } while (0)

int main(void) {
    config_t cfg, restored;
    int n = 0, flag = 0;
    long long big = 0;
    const char *label = NULL;
    const char *tmp = getenv("TMPDIR");
    char directory[1024], include[1100], input[1100], output[1100];
    struct utsname platform;
    CHECK(tmp != NULL && tmp[0] == '/');
    CHECK(snprintf(directory, sizeof directory, "%s/libconfig-%ld", tmp, (long)getpid()) < (int)sizeof directory);
    CHECK(mkdir(directory, 0770) == 0);
    CHECK(snprintf(include, sizeof include, "%s/child.cfg", directory) < (int)sizeof include);
    CHECK(snprintf(input, sizeof input, "%s/main.cfg", directory) < (int)sizeof input);
    CHECK(snprintf(output, sizeof output, "%s/roundtrip.cfg", directory) < (int)sizeof output);
    FILE *file = fopen(include, "wx");
    CHECK(file != NULL);
    CHECK(fputs("answer=42; label=\"鸿蒙配置\"; big=4294967297L; active=true;\n", file) >= 0);
    CHECK(fclose(file) == 0);
    file = fopen(input, "wx");
    CHECK(file != NULL);
    CHECK(fputs("@include \"child.cfg\"\n", file) >= 0);
    CHECK(fclose(file) == 0);
    config_init(&cfg);
    config_init(&restored);
    config_set_include_dir(&cfg, directory);
    CHECK(config_read_file(&cfg, input));
    CHECK(config_lookup_int(&cfg, "answer", &n) && n == 42);
    CHECK(config_lookup_string(&cfg, "label", &label) && strcmp(label, "鸿蒙配置") == 0);
    CHECK(config_lookup_int64(&cfg, "big", &big) && big == 4294967297LL);
    CHECK(config_lookup_bool(&cfg, "active", &flag) && flag == CONFIG_TRUE);
    CHECK(!config_lookup_int(&cfg, "missing", &n));
    CHECK(config_write_file(&cfg, output));
    CHECK(config_read_file(&restored, output));
    CHECK(config_lookup_int(&restored, "answer", &n) && n == 42);
    CHECK(!config_read_string(&restored, "invalid=[1,;"));
    CHECK(config_error_type(&restored) == CONFIG_ERR_PARSE);
#ifdef __OHOS__
    CHECK(uname(&platform) == 0 && strcmp(platform.machine, "aarch64") == 0);
    CHECK(strncmp(directory, "/tmp/", 5) != 0);
    CHECK(config_read_file(&cfg, input) && config_lookup_int(&cfg, "answer", &n) && n == 42);
    puts("OHOS_PRIVATE_TMPDIR_INCLUDE_UTF8_ROUNDTRIP_PASS");
#endif
    config_destroy(&restored);
    config_destroy(&cfg);
    CHECK(unlink(input) == 0 && unlink(include) == 0 && unlink(output) == 0);
    CHECK(rmdir(directory) == 0);
    puts("C_API_PASS");
    return 0;
}
