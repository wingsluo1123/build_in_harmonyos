/* HarmonyOS-specific consumer test — initialize GTK and libadwaita through
 * Broadway, then exercise public Adwaita API from the installed package.
 */
#include <adwaita.h>
#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void)
{
    /* Runtime version API — real libadwaita-1 exported functions. */
    CHECK(adw_get_major_version() == ADW_MAJOR_VERSION,
          "adw_get_major_version() == ADW_MAJOR_VERSION");
    CHECK(adw_get_minor_version() == ADW_MINOR_VERSION,
          "adw_get_minor_version() == ADW_MINOR_VERSION");
    CHECK(adw_get_micro_version() == ADW_MICRO_VERSION,
          "adw_get_micro_version() == ADW_MICRO_VERSION");

    /* Compile-time version macros: this package is libadwaita 1.2.0. */
    CHECK(ADW_MAJOR_VERSION == 1 && ADW_MINOR_VERSION == 2 && ADW_MICRO_VERSION == 0,
          "ADW_MAJOR/MINOR/MICRO_VERSION == 1.2.0");
    CHECK(ADW_CHECK_VERSION(1, 2, 0), "ADW_CHECK_VERSION(1,2,0)");

    /* Initialization is the regression test for the former dual-GObject graph. */
    CHECK(!adw_is_initialized(), "adw_is_initialized() == FALSE before init");
    adw_init();
    CHECK(adw_is_initialized(), "adw_is_initialized() == TRUE after adw_init");

    AdwBin *bin = ADW_BIN(adw_bin_new());
    CHECK(ADW_IS_BIN(bin), "adw_bin_new() creates an AdwBin instance");
    g_object_ref_sink(bin);
    g_object_unref(bin);

    if (failures == 0) {
        printf("HARMONY_LIBADWAITA_TEST_PASS: shared GObject runtime and Adwaita API OK\n");
        return 0;
    }
    printf("HARMONY_LIBADWAITA_TEST_FAIL: %d assertion(s) failed\n", failures);
    return 1;
}
