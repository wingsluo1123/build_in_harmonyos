/* test_kafs_client.c — consumer test for kafs-client/0.5.
 *
 * Exercises the installed libkafs_client without touching the network:
 *  1. profile file parsing (kafs_profile_parse_file)
 *  2. string lookup (kafs_profile_get_string)
 *  3. string counting (kafs_profile_count_strings)
 *  4. bool/constant helpers (kafs_lookup_bool, kafs_lookup_constant)
 *  5. record-source/status stringifiers
 *  6. server-list alloc/free (no DNS involved)
 *
 * Each check prints CASE <n> PASS and the program exits 0 only when all
 * pass. Counts below must match HMBS_TEST_PACKAGE_RESULT discovered.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <kafs/profile.h>
#include <kafs/cellserv.h>
#include <kafs/reporting.h>

static void test_error(const char *fmt, ...)
{
    (void)fmt;
}

int main(int argc, char *argv[])
{
    const char *conf = (argc > 1) ? argv[1] : "kafs_test.conf";
    struct kafs_report report;
    struct kafs_profile root;
    const struct kafs_profile *child;
    const char *val;
    unsigned int nr = 0;
    int rc, passed = 0;

    memset(&report, 0, sizeof(report));
    report.error = test_error;
    memset(&root, 0, sizeof(root));

    /* CASE 1: parse a small static config file (offline). */
    rc = kafs_profile_parse_file(&root, conf, &report);
    if (rc != 0) {
        printf("CASE 1 FAIL: parse %s rc=%d\n", conf, rc);
        return 1;
    }
    printf("CASE 1 PASS: parsed %s\n", conf);
    passed++;

    /* CASE 2: string lookup finds thiscell. */
    val = kafs_profile_get_string(&root, "thiscell", &report);
    /* thiscell lives under [defaults]; fall back to a direct child scan. */
    if (!val) {
        const struct kafs_profile *defs =
            kafs_profile_find_first_child(&root, kafs_profile_value_is_list,
                                          "defaults", &report);
        if (defs)
            val = kafs_profile_get_string(defs, "thiscell", &report);
    }
    if (!val || strcmp(val, "test.example.com") != 0) {
        printf("CASE 2 FAIL: thiscell=%s\n", val ? val : "(null)");
        return 1;
    }
    printf("CASE 2 PASS: thiscell=%s\n", val);
    passed++;

    /* CASE 3: string counting API works (returns 0, count in nr). */
    rc = kafs_profile_count_strings(&root, "thiscell", &nr);
    if (rc != 0) {
        printf("CASE 3 FAIL: count rc=%d\n", rc);
        return 1;
    }
    printf("CASE 3 PASS: count_strings rc=0 nr=%u\n", nr);
    passed++;

    /* CASE 4: bool + constant helpers (pure, no I/O). */
    if (kafs_lookup_bool("yes", -1) != 1 || kafs_lookup_bool("no", -1) != 0) {
        printf("CASE 4 FAIL: bool helper\n");
        return 1;
    }
    {
        static const struct kafs_constant_table tbl[] = {
            { "alpha", 1 },
            { "beta", 2 },
        };
        if (kafs_lookup_constant(tbl, "beta", -1) != 2) {
            printf("CASE 4 FAIL: constant helper\n");
            return 1;
        }
    }
    printf("CASE 4 PASS: bool/constant helpers\n");
    passed++;

    /* CASE 5: record-source + lookup-status stringifiers. */
    child = NULL;
    (void)child;
    val = kafs_record_source(kafs_record_from_config);
    if (!val || !val[0]) {
        printf("CASE 5 FAIL: record_source\n");
        return 1;
    }
    val = kafs_lookup_status(kafs_lookup_good);
    if (!val || !val[0]) {
        printf("CASE 5 FAIL: lookup_status\n");
        return 1;
    }
    printf("CASE 5 PASS: source/status strings: %s / %s\n",
           kafs_record_source(kafs_record_from_config),
           kafs_lookup_status(kafs_lookup_good));
    passed++;

    /* CASE 6: server-list alloc/free (memory only, no DNS). */
    {
        struct kafs_server_list *sl = kafs_alloc_server_list(&report);
        if (!sl) {
            printf("CASE 6 FAIL: alloc_server_list\n");
            return 1;
        }
        kafs_free_server_list(sl);
    }
    printf("CASE 6 PASS: alloc/free server list\n");
    passed++;

    printf("ALL %d CASES PASSED\n", passed);
    return 0;
}
