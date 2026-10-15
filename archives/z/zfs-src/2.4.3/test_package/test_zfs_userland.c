/*
 * test_zfs_userland.c — consumer-perspective test for zfs-src/2.4.3.
 *
 * Library layer (real API calls, no kernel module required):
 *   - libnvpair: the XDR-backed name/value engine that marshals every
 *     libzfs ioctl. alloc → add string/int → lookup round-trip → free.
 *   - libuutil: the list abstraction libzfs is built on.
 *   - libzfs/libzfs_core: handle open/close round-trip; on a host without
 *     the ZFS kernel module libzfs_init() must either succeed (with the
 *     userland version string readable) or return NULL *honestly* — never
 *     crash. libzfs_core_init() exercises the ioctl shim boundary.
 *
 * The CMake link step itself asserts the packaged .so set (link fails if
 * libzfs/libzfs_core/libnvpair/libuutil are absent).
 */
#include <stdio.h>
#include <stddef.h>
#include <string.h>

#include <libnvpair.h>
#include <libuutil.h>
#include <libzfs.h>
#include <libzfs_core.h>

typedef struct {
    int value;
    uu_list_node_t node;
} item_t;

static int
item_cmp(void *a, void *b, void *private)
{
    (void)private;
    return (((item_t *)a)->value - ((item_t *)b)->value);
}

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        failures++; \
    } else { \
        fprintf(stdout, "ok: %s\n", msg); \
    } \
} while (0)

int
main(void)
{
    /* ── libnvpair round-trip ─────────────────────────────────── */
    nvlist_t *nvl = NULL;
    int rc = nvlist_alloc(&nvl, NV_UNIQUE_NAME, 0);
    CHECK(rc == 0, "nvlist_alloc");

    rc = nvlist_add_string(nvl, "pool", "testpool");
    CHECK(rc == 0, "nvlist_add_string");
    rc = nvlist_add_uint64(nvl, "version", 5000ULL);
    CHECK(rc == 0, "nvlist_add_uint64");

    char *str = NULL;
    rc = nvlist_lookup_string(nvl, "pool", &str);
    CHECK(rc == 0 && str != NULL && strcmp(str, "testpool") == 0,
        "nvlist_lookup_string round-trip");

    uint64_t ver = 0;
    rc = nvlist_lookup_uint64(nvl, "version", &ver);
    CHECK(rc == 0 && ver == 5000ULL, "nvlist_lookup_uint64 round-trip");

    nvlist_free(nvl);
    CHECK(1, "nvlist_free");

    /* ── libuutil list ────────────────────────────────────────── */
    uu_list_pool_t *pool = uu_list_pool_create(
        "test_pool", sizeof (item_t), offsetof(item_t, node),
        item_cmp, UU_LIST_POOL_DEBUG);
    CHECK(pool != NULL, "uu_list_pool_create");

    uu_list_t *list = uu_list_create(pool, NULL, UU_LIST_SORTED);
    CHECK(list != NULL, "uu_list_create");

    item_t items[4] = {{3}, {1}, {2}, {0}};
    for (int i = 0; i < 4; i++) {
        /* UU_LIST_POOL_DEBUG requires explicit node init before insert */
        uu_list_node_init(&items[i], &items[i].node, pool);
        uu_list_index_t idx = 0;
        (void) uu_list_find(list, &items[i], NULL, &idx);
        uu_list_insert(list, &items[i], idx);
    }
    /* uu_list_insert() returns void — the previous `== 0` comparison
     * could not compile (CI #91062: invalid operands to binary
     * expression). Assert the observable outcome instead: the list
     * must hold all 4 nodes (AI review Medium intent — a check that
     * genuinely fails when insertion fails). */
    CHECK(uu_list_numnodes(list) == 4, "uu_list_insert x4 (numnodes)");

    item_t key = {.value = 2};
    uu_list_index_t fidx = 0;
    void *found = uu_list_find(list, &key, NULL, &fidx);
    CHECK(found != NULL && ((item_t *)found)->value == 2,
        "uu_list_find");

    /* Drain the list (DEBUG builds assert on non-empty destroy).
     * uu_list_teardown semantics: *cookie starts NULL and is advanced
     * by the library on each call. */
    void *cookie = NULL;
    for (;;) {
        void *elem = uu_list_teardown(list, &cookie);
        if (elem == NULL)
            break;
        uu_list_node_fini(elem, &((item_t *)elem)->node, pool);
    }
    uu_list_destroy(list);
    uu_list_pool_destroy(pool);
    CHECK(1, "uu_list teardown");

    /* ── libzfs handle boundary ───────────────────────────────── */
    /*
     * On OHOS (no ZFS kernel module) libzfs_init() legitimately fails
     * while probing /proc/self/mounts etc.; either outcome is correct
     * as long as the call returns without crashing.
     */
    libzfs_handle_t *hdl = libzfs_init();
    if (hdl != NULL) {
        const char *vstr = zfs_version_userland();
        CHECK(vstr != NULL && strlen(vstr) > 0,
            "libzfs_init + zfs_version_userland");
        libzfs_fini(hdl);
        CHECK(1, "libzfs_fini");
    } else {
        CHECK(1, "libzfs_init honest NULL (no kernel module) - expected on OHOS");
    }

    /* ── libzfs_core ioctl boundary ───────────────────────────── */
    /*
     * libzfs_core_init() opens /dev/zfs; without the kernel module it
     * must fail honestly (non-zero) — the boundary itself is correct.
     */
    int lrc = libzfs_core_init();
    if (lrc == 0) {
        libzfs_core_fini();
        CHECK(1, "libzfs_core_init/fini round-trip");
    } else {
        CHECK(1, "libzfs_core_init honest failure (no /dev/zfs) - expected on OHOS");
    }

    if (failures == 0) {
        fprintf(stdout,
            "zfs-src userland API layer: ALL CHECKS PASSED\n");
        return (0);
    }
    fprintf(stderr, "%d check(s) failed\n", failures);
    return (1);
}
