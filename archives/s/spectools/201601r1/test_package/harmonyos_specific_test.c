/*
 * harmonyos_specific_test.c — spectools 201601r1 鸿蒙平台特有测试
 *
 * 编译期：__OHOS__ / __aarch64__ 硬绑定（非鸿蒙 AArch64 工具链直接 #error）
 * 运行期：对三个安装产物（argv[1..3]）做纯进程内 ELF64 解析——不依赖
 *   readelf/objdump 等外部工具（OHOS 运行环境不保证提供），每产物 6 项：
 *     1. ELF magic
 *     2. ELF64（EI_CLASS=ELFCLASS64）
 *     3. e_machine = EM_AARCH64
 *     4. PT_INTERP 为 aarch64 动态加载器（OHOS musl
 *        /lib/ld-musl-aarch64.so.1，或 OpenHarmony Linux 内核 rootfs 的
 *        /lib/ld-linux-aarch64.so.1），且不得为 x86_64 加载器
 *     5. 段表字符串表存在 ".note.ohos.ident"（OHOS 工具链产物标识）
 *     6. DT_NEEDED 含 libc.so（musl libc；libusb-compat/ncurses 为静态
 *        链接，链接完整性折叠进 libc）
 *   6 项 × 3 产物 = 18 项断言。
 *
 * 用法: harmonyos_specific_test <spectool_raw> <spectool_curses> <spectool_net>
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(__OHOS__)
#error "This test must be compiled with the HarmonyOS (OHOS) toolchain (__OHOS__ undefined)"
#endif

#if !defined(__aarch64__)
#error "This test must be compiled for AArch64 (__aarch64__ undefined)"
#endif

#define EI_CLASS_OFF 4
#define EM_AARCH64 0xB7
#define SIXTY_FOUR_MB (64L * 1024L * 1024L)

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg) do {                                   \
    checks++;                                                   \
    if (cond) {                                                 \
        printf("  ok: %s\n", msg);                              \
    } else {                                                    \
        printf("  FAIL: %s\n", msg);                            \
        failures++;                                             \
    }                                                           \
} while (0)

static uint16_t rd16(const unsigned char *p)
{
    return (uint16_t)(p[0] | (p[1] << 8));
}

static uint32_t rd32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint64_t rd64(const unsigned char *p)
{
    return (uint64_t)rd32(p) | ((uint64_t)rd32(p + 4) << 32);
}

static unsigned char *slurp(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    long n;
    unsigned char *buf;

    if (!f) {
        return NULL;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }
    n = ftell(f);
    if (n <= 0 || n > SIXTY_FOUR_MB) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    buf = (unsigned char *)malloc((size_t)n);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) {
        free(buf);
        fclose(f);
        return NULL;
    }
    fclose(f);
    *size = (size_t)n;
    return buf;
}

/* vaddr → 文件偏移（经 PT_LOAD 段映射） */
static int vaddr_to_off(const unsigned char *b, size_t sz, uint64_t phoff,
                        uint16_t phentsize, uint16_t phnum, uint64_t vaddr,
                        uint64_t *out)
{
    uint16_t i;

    for (i = 0; i < phnum; i++) {
        uint64_t o = phoff + (uint64_t)i * phentsize;
        uint64_t off, va, filesz;

        if (o + 56 > sz) {
            break;
        }
        if (rd32(b + o) != 1 /* PT_LOAD */) {
            continue;
        }
        off = rd64(b + o + 8);
        va = rd64(b + o + 16);
        filesz = rd64(b + o + 32);
        if (vaddr >= va && vaddr < va + filesz) {
            *out = off + (vaddr - va);
            return 1;
        }
    }
    return 0;
}

/* 有界字符串比较（strtab 内容不做 NUL 终止假设） */
static int streq_at(const unsigned char *b, size_t sz, uint64_t off,
                    const char *want)
{
    size_t wl = strlen(want);

    if (off + wl + 1 > sz) {
        return 0;
    }
    return memcmp(b + off, want, wl) == 0 && b[off + wl] == '\0';
}

static void check_binary(const char *path)
{
    unsigned char *b;
    size_t sz = 0;
    uint64_t phoff, shoff;
    uint16_t phentsize, phnum, shentsize, shnum, shstrndx;
    const char *interp = NULL;
    int interp_ok = 0, ident_ok = 0, libc_ok = 0;
    uint16_t i;

    printf("[%s]\n", path);
    b = slurp(path, &sz);
    if (!b) {
        printf("  FAIL: cannot read %s\n", path);
        checks += 6;
        failures += 6;
        return;
    }

    CHECK(sz >= 64 && b[0] == 0x7f && b[1] == 'E' && b[2] == 'L' && b[3] == 'F',
          "ELF magic");
    CHECK(sz >= 64 && b[4] == 2, "ELF64 (EI_CLASS=ELFCLASS64)");
    CHECK(sz >= 64 && rd16(b + 18) == EM_AARCH64,
          "AArch64 (e_machine=EM_AARCH64)");

    if (sz < 64) {
        free(b);
        return;
    }
    phoff = rd64(b + 32);
    phentsize = rd16(b + 54);
    phnum = rd16(b + 56);
    shoff = rd64(b + 40);
    shentsize = rd16(b + 58);
    shnum = rd16(b + 60);
    shstrndx = rd16(b + 62);

    /* 4. PT_INTERP：aarch64 动态加载器 */
    for (i = 0; i < phnum; i++) {
        uint64_t o = phoff + (uint64_t)i * phentsize;
        uint64_t io;

        if (o + 56 > sz) {
            break;
        }
        if (rd32(b + o) != 3 /* PT_INTERP */) {
            continue;
        }
        io = rd64(b + o + 8);
        if (io < sz && memchr(b + io, 0, sz - (size_t)io) != NULL) {
            interp = (const char *)(b + io);
        }
        break;
    }
    if (interp) {
        interp_ok = strstr(interp, "aarch64") != NULL &&
                    strstr(interp, "ld-") != NULL &&
                    strstr(interp, "x86_64") == NULL;
    }
    checks++;
    if (interp_ok) {
        printf("  ok: PT_INTERP is an AArch64 OHOS loader (%s)\n", interp);
    } else {
        printf("  FAIL: unexpected PT_INTERP (%s)\n", interp ? interp : "none");
        failures++;
    }

    /* 5. .note.ohos.ident（段名在 shstrtab 中） */
    if (shnum > 0 && shstrndx < shnum && shentsize >= 64) {
        uint64_t so = shoff + (uint64_t)shstrndx * shentsize;

        if (so + 64 <= sz) {
            uint64_t stroff = rd64(b + so + 24);
            uint64_t strsz = rd64(b + so + 32);
            uint64_t k;

            if (stroff + strsz <= sz) {
                for (k = 0; k + 16 <= strsz; k++) {
                    if (memcmp(b + stroff + k, ".note.ohos.ident", 16) == 0) {
                        ident_ok = 1;
                        break;
                    }
                }
            }
        }
    }
    checks++;
    if (ident_ok) {
        printf("  ok: .note.ohos.ident section present (OHOS toolchain signature)\n");
    } else {
        printf("  FAIL: .note.ohos.ident section missing\n");
        failures++;
    }

    /* 6. DT_NEEDED 含 libc.so */
    for (i = 0; i < phnum && !libc_ok; i++) {
        uint64_t o = phoff + (uint64_t)i * phentsize;
        uint64_t doff, dstrtab = 0, str_off = 0, k;

        if (o + 56 > sz) {
            break;
        }
        if (rd32(b + o) != 2 /* PT_DYNAMIC */) {
            continue;
        }
        doff = rd64(b + o + 8);
        if (doff + 16 > sz) {
            continue;
        }
        for (k = 0; doff + k * 16 + 16 <= sz; k++) {
            uint64_t tag = rd64(b + doff + k * 16);

            if (tag == 0 /* DT_NULL */) {
                break;
            }
            if (tag == 5 /* DT_STRTAB */) {
                dstrtab = rd64(b + doff + k * 16 + 8);
            }
        }
        if (dstrtab == 0 ||
            !vaddr_to_off(b, sz, phoff, phentsize, phnum, dstrtab, &str_off)) {
            continue;
        }
        for (k = 0; doff + k * 16 + 16 <= sz; k++) {
            uint64_t tag = rd64(b + doff + k * 16);
            uint64_t nameoff;

            if (tag == 0) {
                break;
            }
            if (tag != 1 /* DT_NEEDED */) {
                continue;
            }
            nameoff = rd64(b + doff + k * 16 + 8);
            if (str_off + nameoff < sz &&
                streq_at(b, sz, str_off + nameoff, "libc.so")) {
                libc_ok = 1;
                break;
            }
        }
    }
    checks++;
    if (libc_ok) {
        printf("  ok: DT_NEEDED contains libc.so (musl libc)\n");
    } else {
        printf("  FAIL: DT_NEEDED libc.so not found\n");
        failures++;
    }

    free(b);
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr,
                "usage: %s <spectool_raw> <spectool_curses> <spectool_net>\n",
                argv[0]);
        return 2;
    }

    check_binary(argv[1]);
    check_binary(argv[2]);
    check_binary(argv[3]);

    printf("\nHarmonyOS-specific test: %d checks, %d failures\n",
           checks, failures);
    return failures ? 1 : 0;
}
