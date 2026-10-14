#include <aml.h>
#include <neatvnc.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    fputs("NEATVNC_CONSUMER_MAIN_ENTERED\n", stderr);
    if (strstr(nvnc_version, "1.0.1") == NULL) {
        fputs("unexpected NeatVNC version\n", stderr);
        return 1;
    }
    fputs("NEATVNC_CONSUMER_VERSION_OK\n", stderr);
    struct aml *loop = aml_new();
    if (loop == NULL) {
        fputs("aml_new failed\n", stderr);
        return 2;
    }
    aml_set_default(loop);
    struct nvnc *server = nvnc_new();
    if (server == NULL) {
        fputs("nvnc_new failed\n", stderr);
        aml_set_default(NULL);
        aml_unref(loop);
        return 3;
    }
    fputs("NEATVNC_CONSUMER_NEW_OK\n", stderr);
    nvnc_del(server);
    fputs("NEATVNC_CONSUMER_DEL_OK\n", stderr);
    aml_set_default(NULL);
    aml_unref(loop);
    puts("NeatVNC installed API lifecycle passed");
    return 0;
}
