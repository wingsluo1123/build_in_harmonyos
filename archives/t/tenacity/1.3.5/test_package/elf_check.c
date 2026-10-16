/* tenacity 1.3.5 test_package — 产物验证（R34 非空壳补充）。
 *
 * 对打包出来的全部 lib-*.a 逐一校验：
 *   1) 文件头为合法 ar 归档魔数 "!<arch>\n"；
 *   2) 至少含一个 ELF relocatable 成员（magic 0x7f 'E' 'L' 'F'）；
 *   3) 该 ELF 成员为 AArch64（e_machine == EM_AARCH64 == 183，ELF 头偏移 18，
 *      小端 2 字节）——证明产物确实是为 OHOS PC aarch64 交叉编译的，而非宿主架构。
 *
 * 用法：./elf_check <lib-1.a> [lib-2.a ...]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EM_AARCH64 183

/* ar 成员头（60 字节固定）：name[16] mtime[12] uid[6] gid[6] mode[8] size[10] 0x60 0x0a */
typedef struct {
    char name[16];
    char mtime[12];
    char uid[6];
    char gid[6];
    char mode[8];
    char size[10];
    char end[2];
} ArHdr;

static long ar_size(const ArHdr *h) {
    char buf[11] = {0};
    memcpy(buf, h->size, 10);
    char *end = NULL;
    long v = strtol(buf, &end, 10);
    if (end == buf || v < 0)
        return -1;
    return v;
}

/* 扫描归档成员，返回：1 = 找到 AArch64 ELF 成员；0 = 无；-1 = 找到 ELF 但非 AArch64 */
static int check_aarch64_elf_member(FILE *f) {
    unsigned char hdr[60];
    int saw_elf = 0;
    while (1) {
        if (fread(hdr, 1, 60, f) != 60)
            break; /* 成员头读不完整 = 归档结束 */
        ArHdr *ah = (ArHdr *)hdr;
        long sz = ar_size(ah);
        if (sz < 0)
            break;
        if (sz == 0)
            break; /* 空成员 */

        unsigned char h[64];
        size_t got = 0;
        if (sz >= (long)sizeof(h)) {
            got = fread(h, 1, sizeof(h), f);
            if (got == sizeof(h) &&
                h[0] == 0x7f && h[1] == 'E' && h[2] == 'L' && h[3] == 'F') {
                unsigned int machine =
                    (unsigned int)h[18] | ((unsigned int)h[19] << 8);
                fclose(f);
                if (machine == EM_AARCH64)
                    return 1;
                saw_elf = 1;
                return -1;
            }
        }
        long skip = sz - (long)got;
        if (skip > 0 && fseek(f, skip, SEEK_CUR) != 0)
            break;
        if (sz % 2 == 1) { /* 奇数长度成员后有补齐 '\n' */
            if (fgetc(f) == EOF)
                break;
        }
    }
    fclose(f);
    return saw_elf ? -1 : 0;
}

static int check_one(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", path);
        return 1;
    }
    unsigned char magic[8] = {0};
    size_t n = fread(magic, 1, 8, f);
    if (n != 8 || memcmp(magic, "!<arch>\n", 8) != 0) {
        fprintf(stderr, "FAIL: %s is not a valid ar archive (magic=%.8s)\n",
                path, magic);
        fclose(f);
        return 1;
    }
    int r = check_aarch64_elf_member(f); /* 内部已 fclose */
    if (r == 1) {
        printf("OK  : %s (ar archive, AArch64 ELF member)\n", path);
        return 0;
    }
    if (r == 0)
        fprintf(stderr, "FAIL: %s has no ELF object member\n", path);
    else
        fprintf(stderr, "FAIL: %s has ELF member but not EM_AARCH64(%d)\n",
                path, EM_AARCH64);
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <lib-1.a> [lib-2.a ...]\n", argv[0]);
        return 2;
    }
    int bad = 0;
    for (int i = 1; i < argc; ++i)
        bad += check_one(argv[i]);
    if (bad) {
        fprintf(stderr, "FAIL: %d of %d archive(s) invalid\n", bad, argc - 1);
        return 1;
    }
    printf("OK: all %d archive(s) are ar archives with AArch64 ELF members\n",
           argc - 1);
    return 0;
}
