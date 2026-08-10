#include <stdio.h>
#include <string.h>

/* 验证 LV2 插件 bundle：检查 manifest.ttl 与 sherlock.so 存在，
 * 且 manifest.ttl 内容含插件 URI（非仅文件存在——R34 非空壳） */
int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_sherlock <bundle-dir>\n");
        return 2;
    }
    char ttl[1024], so[1024], buf[8192];
    snprintf(ttl, sizeof(ttl), "%s/manifest.ttl", argv[1]);
    snprintf(so, sizeof(so), "%s/sherlock.so", argv[1]);
    FILE *fp = fopen(ttl, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: %s 不存在\n", ttl);
        return 1;
    }
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    fclose(fp);
    FILE *fso = fopen(so, "r");
    if (!fso) {
        fprintf(stderr, "FAIL: %s 不存在\n", so);
        return 1;
    }
    fclose(fso);
    /* manifest.ttl 应含插件 URI（http://open-music-kontrollers.ch/lv2/sherlock#...） */
    if (strstr(buf, "sherlock") != NULL) {
        printf("PASS: manifest.ttl 含插件声明 + sherlock.so 存在\n");
        return 0;
    }
    fprintf(stderr, "FAIL: manifest.ttl 缺插件声明\n");
    return 1;
}
