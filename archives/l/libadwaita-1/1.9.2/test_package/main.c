/* HarmonyOS-specific test — verify the libadwaita-1 package is consumable.
 *
 * This test deliberately does NOT call adw_init() (which would try to open a
 * display and fail on a headless HarmonyOS device); it exercises the
 * libadwaita public version API (adw_get_major/minor/micro_version, real
 * exported symbols from libadwaita-1) and asserts the packaged version,
 * confirming the package provides a usable pkg-config / cpp_info.
 *
 * NOTE: libadwaita ships the umbrella header <adwaita.h> (installed at
 * include/libadwaita-1/adwaita.h); all adw-*.h headers enforce that only
 * <adwaita.h> may be included directly.
 */
#include <adwaita.h>
#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(int argc, char **argv)
{
    /* Real libadwaita public API — exported version getters. */
    CHECK(adw_get_major_version() == 1, "adw_get_major_version() == 1");
    CHECK(adw_get_minor_version() == 9, "adw_get_minor_version() == 9");
    CHECK(adw_get_micro_version() == 2, "adw_get_micro_version() == 2");

    if (failures == 0) {
        printf("HARMONY_LIBADWAITA_TEST_PASS: libadwaita-1 1.9.2 package consumable, no display required\n");
        return 0;
    }
    printf("HARMONY_LIBADWAITA_TEST_FAIL: %d assertion(s) failed\n", failures);
    return 1;
}