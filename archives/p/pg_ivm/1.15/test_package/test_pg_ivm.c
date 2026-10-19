/*
 * test_pg_ivm.c — pg_ivm 包的冒烟测试。
 *
 * 校验包内产物齐全且是真货（R34：实质依赖被测包产物）：
 *   1) lib/pg_ivm.so            存在、是 64 位 ELF 共享对象（ELFCLASS64 + ET_DYN）；
 *   2) 该 .so 带 OHOS 标识段     文件内含 ".note.ohos.ident"（未 strip 掉平台标识）；
 *   3) extension/pg_ivm.control 存在且声明 default_version；
 *   4) extension/ 下至少存在一个 pg_ivm--*.sql 脚本。
 *
 * 功能性验证（CREATE EXTENSION + IMMV 增量刷新 + 上游回归）由
 * test_package/conanfile.py 驱动设备上的真实 PostgreSQL 集群完成。
 */
/* memmem(3) 是 GNU 扩展，需在包含头文件前声明 _GNU_SOURCE。 */
#define _GNU_SOURCE
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int check_elf(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", path);
        return 1;
    }
    unsigned char magic[20];
    size_t n = fread(magic, 1, sizeof(magic), f);
    fclose(f);
    if (n < 4 || magic[0] != 0x7f || magic[1] != 'E' ||
        magic[2] != 'L' || magic[3] != 'F') {
        fprintf(stderr, "FAIL: %s is not a valid ELF file\n", path);
        return 1;
    }
    if (magic[4] != 0x02) {           /* ELFCLASS64 */
        fprintf(stderr, "FAIL: %s is not a 64-bit ELF\n", path);
        return 1;
    }
    if (magic[16] != 0x03) {          /* ET_DYN: shared object */
        fprintf(stderr, "FAIL: %s is not a shared object (e_type=%u)\n",
                path, magic[16]);
        return 1;
    }
    printf("PASS: %s is a valid 64-bit ELF shared object\n", path);
    return 0;
}

/* OHOS 交付的共享库带 .note.ohos.ident 标识段；缺失通常意味着交付物被
 * strip 过或根本不是 OHOS 工具链产物。 */
static int check_ohos_ident(const char *path)
{
    const char *needle = ".note.ohos.ident";
    const size_t needle_len = strlen(needle);
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", path);
        return 1;
    }
    int found = 0;
    static char buf[1 << 16];
    size_t keep = needle_len - 1;
    size_t carry = 0;
    size_t got;
    while ((got = fread(buf + carry, 1, sizeof(buf) - carry, f)) > 0) {
        size_t total = carry + got;
        if (memmem(buf, total, needle, needle_len) != NULL) {
            found = 1;
            break;
        }
        if (total >= keep) {
            memmove(buf, buf + total - keep, keep);
            carry = keep;
        } else {
            carry = total;
        }
    }
    fclose(f);
    if (!found) {
        fprintf(stderr, "FAIL: %s has no %s section\n", path, needle);
        return 1;
    }
    printf("PASS: %s carries the %s section\n", path, needle);
    return 0;
}

static int count_sql_scripts(const char *ext_dir)
{
    DIR *d = opendir(ext_dir);
    if (!d) {
        fprintf(stderr, "FAIL: cannot open %s\n", ext_dir);
        return -1;
    }
    int count = 0;
    struct dirent *e;
    while ((e = readdir(d)) != NULL) {
        const char *n = e->d_name;
        if (strncmp(n, "pg_ivm--", 8) == 0 && strstr(n, ".sql") != NULL) {
            count++;
        }
    }
    closedir(d);
    return count;
}

int main(int argc, char *argv[])
{
    const char *pkg_dir = getenv("PG_IVM_PACKAGE_DIR");
    if (!pkg_dir && argc > 1) {
        pkg_dir = argv[1];
    }
    if (!pkg_dir) {
        fprintf(stderr, "PG_IVM_PACKAGE_DIR not set and no arg given\n");
        return 1;
    }

    char so_path[4096], ctl_path[4096], ext_dir[4096];
    snprintf(so_path, sizeof(so_path), "%s/lib/pg_ivm.so", pkg_dir);
    snprintf(ctl_path, sizeof(ctl_path), "%s/extension/pg_ivm.control", pkg_dir);
    snprintf(ext_dir, sizeof(ext_dir), "%s/extension", pkg_dir);

    struct stat st;
    if (stat(so_path, &st) != 0) {
        fprintf(stderr, "FAIL: pg_ivm.so not found at %s\n", so_path);
        return 1;
    }
    printf("PASS: pg_ivm.so exists (%ld bytes)\n", (long)st.st_size);
    if (check_elf(so_path) != 0) {
        return 1;
    }
    if (check_ohos_ident(so_path) != 0) {
        return 1;
    }

    if (stat(ctl_path, &st) != 0) {
        fprintf(stderr, "FAIL: pg_ivm.control not found at %s\n", ctl_path);
        return 1;
    }
    FILE *cf = fopen(ctl_path, "r");
    if (!cf) {
        fprintf(stderr, "FAIL: cannot open %s\n", ctl_path);
        return 1;
    }
    char ctl[4096];
    size_t got = fread(ctl, 1, sizeof(ctl) - 1, cf);
    ctl[got] = '\0';
    fclose(cf);
    if (strstr(ctl, "default_version") == NULL) {
        fprintf(stderr, "FAIL: pg_ivm.control has no default_version\n");
        return 1;
    }
    printf("PASS: pg_ivm.control declares default_version\n");

    int scripts = count_sql_scripts(ext_dir);
    if (scripts <= 0) {
        fprintf(stderr, "FAIL: no pg_ivm--*.sql script found in %s\n", ext_dir);
        return 1;
    }
    printf("PASS: %d pg_ivm--*.sql script(s) packaged\n", scripts);

    return 0;
}
