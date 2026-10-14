/* libmtd 2.3.1-3 consumer test package — real end-to-end consumer workflow.
 *
 * Exercises the packaged artifacts the way a third-party consumer would:
 *   - compile against the public headers (libmtd.h / libubi.h / libubigen.h
 *     and the kernel UAPI headers under mtd/)
 *   - link the static archives (libmtd.a / libubi.a / libubigen.a /
 *     libscan.a / libmissing.a)
 *   - run the real public APIs and assert their documented behavior
 *
 * Device-aware assertions: hosts without /dev/mtd* / /dev/ubi* (e.g.
 * HarmonyOS PC, which boots from UFS/NVMe) must see libmtd_open()/
 * libubi_open() degrade gracefully to NULL (never crash); hosts that do
 * expose raw flash must get usable handles. Functional coverage comes from
 * libubigen, whose UBI image generation helpers are pure computations.
 */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <libmtd.h>
#include <libubi.h>
/* libubigen.h forward-declares struct ubi_ec_hdr/ubi_vid_hdr without
 * including the UBI on-flash layout, so ubi-media.h must come first. */
#include <mtd/ubi-media.h>
#include <libubigen.h>
#include <mtd/mtd-abi.h>

static int failures = 0;
#define CHECK(cond) do { \
    if (cond) { printf("PASS: %s\n", #cond); } \
    else { printf("FAIL: %s\n", #cond); failures++; } \
} while (0)

int main(void)
{
    int has_mtd_dev = (access("/dev/mtd0", F_OK) == 0);
    int has_ubi_dev = (access("/dev/ubi_ctrl", F_OK) == 0);

    /* 1. Library handles follow the device presence contract. */
    libmtd_t mtd = libmtd_open();
    libubi_t ubi = libubi_open();
    printf("INFO: has_mtd_dev=%d has_ubi_dev=%d libmtd_open=%p libubi_open=%p\n",
           has_mtd_dev, has_ubi_dev, (void *)mtd, (void *)ubi);
    if (has_mtd_dev)
        CHECK(mtd != NULL);
    else
        CHECK(mtd == NULL);   /* graceful degradation, never crash */
    if (has_ubi_dev)
        CHECK(ubi != NULL);
    else
        CHECK(ubi == NULL);
    if (mtd)
        libmtd_close(mtd);
    if (ubi)
        libubi_close(ubi);

    /* 2. libubigen functional path: initialize image info and verify the
     *    derived geometry fields follow the documented derivation
     *    (peb=128K, min_io=subpage=4K, vid_hdr_offs auto, ubi ver 1). */
    struct ubigen_info ui;
    const int peb_size = 128 * 1024;
    const int min_io = 4096;
    ubigen_info_init(&ui, peb_size, min_io, min_io, 0, 1, 0x12345678u);
    CHECK(ui.peb_size == peb_size);
    CHECK(ui.vid_hdr_offs == min_io);        /* EC_HDR_SIZE=64 rounds up to min_io */
    CHECK(ui.data_offs == 2 * min_io);       /* vid_hdr + VID_HDR_SIZE(64) rounds up */
    CHECK(ui.leb_size == peb_size - ui.data_offs);
    CHECK(ui.max_volumes == 128);            /* UBI_MAX_VOLUMES cap */
    CHECK(ui.vtbl_size == ui.max_volumes * UBI_VTBL_RECORD_SIZE);
    CHECK(ui.image_seq == 0x12345678u);

    /* 3. EC header generation: magic must be big-endian "UBI#", erase
     *    counter stored big-endian, image sequence carried over. */
    struct ubi_ec_hdr hdr;
    memset(&hdr, 0, sizeof(hdr));
    ubigen_init_ec_hdr(&ui, &hdr, 42);
    CHECK(memcmp(&hdr.magic, "UBI#", 4) == 0);  /* UBI_EC_HDR_MAGIC, stored BE */
    {
        const unsigned char *ec = (const unsigned char *)&hdr.ec;
        uint64_t val = 0;
        int i;
        for (i = 0; i < 8; i++)
            val = (val << 8) | ec[i];
        CHECK(val == 42);
    }
    {
        const unsigned char *sq = (const unsigned char *)&hdr.image_seq;
        uint32_t seq = ((uint32_t)sq[0] << 24) | ((uint32_t)sq[1] << 16) |
                       ((uint32_t)sq[2] << 8) | (uint32_t)sq[3];
        CHECK(seq == 0x12345678u);
    }

    /* 4. Kernel UAPI headers packaged and usable: compile-time sizes from
     *    mtd-abi.h / ubi-user.h must be sane. */
    CHECK(sizeof(struct mtd_info_user) >= 16);
    CHECK(sizeof(struct ubi_attach_req) >= 16);

    printf("%s: %d failure(s)\n", failures ? "FAILED" : "ALL TESTS PASSED",
           failures);
    return failures ? 1 : 0;
}
