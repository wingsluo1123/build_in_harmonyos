/* libdmapsharing 3.9.14 真实功能断言（消费者视角冒烟）：
 * 1) dmap_md5_generate 生成 DAAP 响应哈希（对照已知向量，与上游
 *    dmap-md5 单元测试同源）；
 * 2) dmap_md5_progressive_* 流式哈希 API 往返；
 * 3) dmap_utils_mime_to_format 映射（audio/wav -> wav、video/quicktime -> mp4）；
 * 4) GObject 类型系统注册：库内核心类型（DMAP_TYPE_AV_CONNECTION /
 *    DMAP_TYPE_AV_RECORD / DMAP_TYPE_SHARE / DMAP_TYPE_CONNECTION）可解析，
 *    能捕获“第二份 GObject 拷贝 -> cannot register existing type”问题。
 *
 * 测试末尾打印确定性汇总行（供 test_package/conanfile.py 解析取数）：
 *   DMAP_TEST_PACKAGE_RESULT_TOTAL=<total> PASSED=<passed> FAILED=<failed>
 */
#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <glib-object.h>

#include <libdmapsharing/dmap.h>

static int check_md5_known_vector(void)
{
    guchar hash[33] = { 0 };
    guchar *url = (guchar *) "test://foo";
    dmap_md5_generate(3, url, 2, hash, 0);
    if (memcmp(hash, "798A9D80B6F08E339603BE83E0FEAD03", 32) != 0) {
        fprintf(stderr, "md5 known-vector mismatch: %.32s\n", hash);
        return 1;
    }
    return 0;
}

static int check_md5_progressive(void)
{
    guchar buf[16] = { 0 };
    guchar hash1[33] = { 0 };
    guchar hash2[33] = { 0 };
    guchar *value = (guchar *) "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    DmapHashContext context;

    dmap_md5_progressive_init(&context);
    dmap_md5_progressive_update(&context, value, 5);
    dmap_md5_progressive_update(&context, value + 5, 5);
    dmap_md5_progressive_update(&context, value + 10, 5);
    dmap_md5_progressive_update(&context, value + 15, 5);
    dmap_md5_progressive_update(&context, value + 20, 5);
    dmap_md5_progressive_update(&context, value + 25, 1);
    dmap_md5_progressive_final(&context, buf);
    dmap_md5_progressive_to_string(buf, (gchar *) hash1);

    dmap_md5_generate(3, value, 2, hash2, 0);

    /* 单次生成与分批 update 的哈希必须一致 */
    if (strncmp((char *) hash1, (char *) hash2, 32) != 0) {
        fprintf(stderr, "progressive md5 mismatch: %s vs %s\n", hash1, hash2);
        return 1;
    }
    return 0;
}

static int check_mime_to_format(void)
{
    gchar *fmt;
    fmt = dmap_utils_mime_to_format("audio/wav");
    if (g_strcmp0(fmt, "wav") != 0) {
        fprintf(stderr, "mime audio/wav -> %s\n", fmt ? fmt : "(null)");
        g_free(fmt);
        return 1;
    }
    g_free(fmt);

    fmt = dmap_utils_mime_to_format("video/quicktime");
    if (g_strcmp0(fmt, "mp4") != 0) {
        fprintf(stderr, "mime video/quicktime -> %s\n", fmt ? fmt : "(null)");
        g_free(fmt);
        return 1;
    }
    g_free(fmt);

    if (dmap_utils_mime_to_format(NULL) != NULL) {
        fprintf(stderr, "mime NULL should map to NULL\n");
        return 1;
    }
    if (dmap_utils_mime_to_format("bad/mime") != NULL) {
        fprintf(stderr, "unknown mime should map to NULL\n");
        return 1;
    }
    return 0;
}

static int check_gobject_types(void)
{
    /* Force registration of each core type, then verify it resolves to the
     * expected canonical GType name. GObject types are lazily registered: the
     * type only enters the type system when its _get_type() is invoked, so we
     * must call each dmap_*_get_type() explicitly (merely linking and calling
     * g_type_from_name for a never-registered type returns 0). Calling
     * get_type() on a second GObject copy aborts with
     * "cannot register existing type", which this test surfaces. */
    struct { GType (*get_type)(void); const char *name; } const types[] = {
        { dmap_av_connection_get_type, "DmapAvConnection" },
        { dmap_av_record_get_type, "DmapAvRecord" },
        { dmap_share_get_type, "DmapShare" },
        { dmap_connection_get_type, "DmapConnection" },
    };
    size_t i;
    for (i = 0; i < sizeof(types) / sizeof(types[0]); i++) {
        GType t = types[i].get_type();
        if (t == 0) {
            fprintf(stderr, "type registration returned 0: %s\n", types[i].name);
            return 1;
        }
        if (g_type_from_name(types[i].name) != t) {
            fprintf(stderr, "type %s not registered under canonical name\n",
                    types[i].name);
            return 1;
        }
    }
    return 0;
}

int main(void)
{
    /* 每一项为独立用例：通过记 PASSED，失败记 FAILED，_TOTAL 为常数。 */
    int total = 4;
    int passed = 0;
    int failed = 0;

    if (check_md5_known_vector() == 0)
        passed++;
    else
        failed++;
    if (check_md5_progressive() == 0)
        passed++;
    else
        failed++;
    if (check_mime_to_format() == 0)
        passed++;
    else
        failed++;
    if (check_gobject_types() == 0)
        passed++;
    else
        failed++;

    printf("DMAP_TEST_PACKAGE_RESULT_TOTAL=%d PASSED=%d FAILED=%d\n",
           total, passed, failed);
    return failed == 0 ? 0 : 1;
}
