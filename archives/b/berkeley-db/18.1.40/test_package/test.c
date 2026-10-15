/* berkeley-db 18.1.40 消费者 API 契约测试（链接 berkeley-db::berkeley-db，真实执行器）
 *
 * 逐用例输出 TEST PASS/FAIL，末行 TEST SUMMARY；任一失败 exit(1)。
 * 覆盖：db_version 版本核对、db_create/db->close 生存期、
 *       in-memory Btree 的 open/put/get/del 全链路 + 数据逐字节回读校验。
 */
#include <stdio.h>
#include <string.h>

#include <db.h>

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        g_checks++;                                                            \
        if (cond) {                                                            \
            printf("  CHECK PASS: %s\n", (what));                              \
        } else {                                                               \
            printf("  CHECK FAIL: %s (%s:%d)\n", (what), __FILE__, __LINE__);  \
            g_fails++;                                                         \
        }                                                                      \
    } while (0)

static void case_done(const char *name, int fails_before)
{
    if (g_fails == fails_before) {
        printf("TEST PASS: %s\n", name);
    } else {
        printf("TEST FAIL: %s\n", name);
    }
}

static void test_version(void)
{
    int f0 = g_fails;
    printf("TEST CASE: db_version\n");
    int major = 0, minor = 0, patch = 0;
    char *ver = db_version(&major, &minor, &patch);
    printf("  (db_version banner: %s)\n", ver != NULL ? ver : "(null)");
    CHECK(ver != NULL, "db_version 返回非空版本串");
    CHECK(major == 18, "主版本号 == 18");
    CHECK(minor == 1, "次版本号 == 1");
    CHECK(patch == 40, "补丁号 == 40");
    /* db_version() 返回 DB_VERSION_STRING 全 banner（形如
     * "Berkeley DB 18.1.40: (May 29, 2020)"），非裸版本号，故按包含校验。 */
    CHECK(ver != NULL && strstr(ver, "18.1.40") != NULL,
          "版本串包含 \"18.1.40\"");
    case_done("db_version", f0);
}

static void test_create_close(void)
{
    int f0 = g_fails;
    printf("TEST CASE: db_create / db->close\n");
    DB *dbp = NULL;
    int rc = db_create(&dbp, NULL, 0);
    CHECK(rc == 0 && dbp != NULL, "db_create 返回 0 且句柄非空");
    if (dbp != NULL) {
        rc = dbp->close(dbp, 0);
        CHECK(rc == 0, "db->close 返回 0");
    }
    case_done("db_create / db->close", f0);
}

static void test_memory_rw(void)
{
    int f0 = g_fails;
    printf("TEST CASE: in-memory Btree open/put/get/del\n");

    DB *dbp = NULL;
    DBT key, data;
    int rc = db_create(&dbp, NULL, 0);
    CHECK(rc == 0 && dbp != NULL, "db_create 返回 0 且句柄非空");
    if (dbp == NULL) {
        /* CHECK 宏只记账不中断；句柄为空时后续 dbp->open 会空指针解引用，
         * 须提前收敛为用例失败（与 test_create_close 的防护同款）。 */
        case_done("in-memory Btree open/put/get/del", f0);
        return;
    }

    /* 内存态 Btree：file == NULL + DB_CREATE（不落盘，免除文件系统依赖） */
    rc = dbp->open(dbp, NULL, NULL, NULL, DB_BTREE, DB_CREATE, 0);
    CHECK(rc == 0, "db->open(NULL, DB_BTREE, DB_CREATE) 返回 0");

    memset(&key, 0, sizeof(key));
    memset(&data, 0, sizeof(data));
    key.data = (void *)"hello";
    key.size = 5;
    data.data = (void *)"world";
    data.size = 5;
    rc = dbp->put(dbp, NULL, &key, &data, 0);
    CHECK(rc == 0, "db->put 写入键值返回 0");

    memset(&data, 0, sizeof(data));
    rc = dbp->get(dbp, NULL, &key, &data, 0);
    CHECK(rc == 0, "db->get 读回返回 0");
    CHECK(data.size == 5 && memcmp(data.data, "world", 5) == 0,
          "读回值与写入值逐字节一致");

    rc = dbp->del(dbp, NULL, &key, 0);
    CHECK(rc == 0, "db->del 删除键返回 0");
    memset(&data, 0, sizeof(data));
    rc = dbp->get(dbp, NULL, &key, &data, 0);
    CHECK(rc == DB_NOTFOUND, "删除后 db->get 返回 DB_NOTFOUND");

    rc = dbp->close(dbp, 0);
    CHECK(rc == 0, "db->close 返回 0");
    case_done("in-memory Btree open/put/get/del", f0);
}

int main(void)
{
    printf("== berkeley-db 18.1.40 consumer API contract test ==\n");
    test_version();
    test_create_close();
    test_memory_rw();
    printf("TEST SUMMARY: %d checks, %d failed -> %s\n",
           g_checks, g_fails, g_fails == 0 ? "ALL PASS" : "FAILURES PRESENT");
    return g_fails == 0 ? 0 : 1;
}
