/* util-linux test_package consumer probe.
 *
 * 真实调用三个交付库的公开 API，验证链接 + 运行期初始化：
 *   - libblkid : blkid_new_probe_from_filename() / blkid_do_safeprobe()
 *   - libuuid  : uuid_generate() / uuid_unparse_upper() / uuid_parse()
 *   - libmount : mnt_new_context() / mnt_free_context()
 */
#include <blkid/blkid.h>
#include <libmount/libmount.h>
#include <uuid/uuid.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_blkid(void)
{
    /* OHOS 的 /tmp 只读（E002），临时文件落在 TMPDIR 或当前目录 */
    const char *base = getenv("TMPDIR");
    char path[1024];
    if (base == NULL || base[0] == '\0')
        base = ".";
    snprintf(path, sizeof(path), "%s/util-linux-test-package-probe.bin", base);

    FILE *f = fopen(path, "wb");
    if (f == NULL) {
        fprintf(stderr, "FAIL: cannot create probe file %s\n", path);
        return 1;
    }
    fwrite("util-linux test package", 1, 23, f);
    fclose(f);

    blkid_probe pr = blkid_new_probe_from_filename(path);
    remove(path);
    if (pr == NULL) {
        fprintf(stderr, "FAIL: blkid_new_probe_from_filename() returned NULL\n");
        return 1;
    }
    /* 对待测文件做一次安全探测；返回 0（探测成功）或 1（无匹配）都算链路可用 */
    int rc = blkid_do_safeprobe(pr);
    if (rc < 0) {
        fprintf(stderr, "FAIL: blkid_do_safeprobe() returned %d\n", rc);
        blkid_free_probe(pr);
        return 1;
    }
    blkid_free_probe(pr);
    printf("  libblkid : blkid_new_probe_from_filename/do_safeprobe OK (rc=%d)\n", rc);
    return 0;
}

static int check_uuid(void)
{
    uuid_t uu;
    char out[37];

    uuid_generate(uu);
    uuid_unparse_upper(uu, out);
    if (strlen(out) != 36 || out[8] != '-' || out[13] != '-' || out[18] != '-' || out[23] != '-') {
        fprintf(stderr, "FAIL: uuid_unparse_upper produced malformed string '%s'\n", out);
        return 1;
    }

    uuid_t parsed;
    if (uuid_parse(out, parsed) != 0) {
        fprintf(stderr, "FAIL: uuid_parse('%s') failed\n", out);
        return 1;
    }
    if (uuid_compare(uu, parsed) != 0) {
        fprintf(stderr, "FAIL: uuid round-trip mismatch\n");
        return 1;
    }
    printf("  libuuid  : uuid_generate/unparse_upper/parse OK (%s)\n", out);
    return 0;
}

static int check_mount(void)
{
    struct libmnt_context *ctx = mnt_new_context();
    if (ctx == NULL) {
        fprintf(stderr, "FAIL: mnt_new_context() returned NULL\n");
        return 1;
    }
    mnt_free_context(ctx);
    printf("  libmount : mnt_new_context/mnt_free_context OK\n");
    return 0;
}

int main(void)
{
    if (check_blkid() != 0)
        return 1;
    if (check_uuid() != 0)
        return 1;
    if (check_mount() != 0)
        return 1;

    printf("util-linux OK\n");
    return 0;
}
