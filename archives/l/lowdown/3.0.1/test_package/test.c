#include <stdio.h>
#include <string.h>
#include <sys/queue.h>
#include <lowdown.h>

int main(void) {
    const char *md = "# Hello HarmonyOS\n\nThis is a **test** of lowdown.\n";
    char *out = NULL;
    size_t outsz = 0;
    struct lowdown_opts opts;
    int ret;

    memset(&opts, 0, sizeof(opts));
    opts.type = LOWDOWN_HTML;
    opts.feat = LOWDOWN_FENCED | LOWDOWN_TABLES | LOWDOWN_AUTOLINK;
    opts.oflags = LOWDOWN_STANDALONE | LOWDOWN_SMARTY;

    ret = lowdown_buf(&opts, md, strlen(md), &out, &outsz, NULL);
    if (ret == 0 || out == NULL) {
        printf("FAIL: lowdown_buf returned %d, out=%p\n", ret, (void*)out);
        return 1;
    }

    /* Verify HTML output contains expected content */
    if (strstr(out, "<h1") == NULL) {
        printf("FAIL: no <h1> tag found in output\n");
        printf("Output: %s\n", out);
        return 1;
    }
    if (strstr(out, "Hello HarmonyOS") == NULL) {
        printf("FAIL: expected text not found in output\n");
        printf("Output: %s\n", out);
        return 1;
    }

    printf("PASS: lowdown HTML round-trip OK (%zu bytes output)\n", outsz);
    return 0;
}
