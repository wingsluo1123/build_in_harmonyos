/*
 * test_package consumer probe — cairo-dock/3.5.0 (R34: real API, no stub).
 *
 * cairo-dock installs the shared GLDI library (lib/libgldi.so) together with
 * its public headers (include/cairo-dock/...).  This translation unit is built
 * and executed against the packaged artefacts exactly the way a dock plug-in
 * would: it links -lgldi through the generated pkg-config file and calls two
 * of the exported helper functions that do not need a display.
 *
 * Why these two functions:
 *   - cairo_dock_get_version_from_string() is the helper libgldi itself uses
 *     to parse GLDI_VERSION at startup (cairo-dock-core.c:102); asserting its
 *     result proves the consumer is running *this* library build.
 *   - cairo_dock_string_contains() is a second, independent exported symbol
 *     (token matching helper used all over the dock).
 *
 * Both are pure: no GTK init, no display, no D-Bus - so the probe is
 * headless-safe (see the R40 note in test_package/conanfile.py).
 */
#include <stdio.h>
#include <string.h>

#include <glib.h>

/* Public API: include/cairo-dock/gldit/cairo-dock-utils.h (self-contained
 * apart from the generated gldi-config.h sitting next to it). */
#include <cairo-dock/gldit/cairo-dock-utils.h>

static int failures = 0;

static void check(int condition, const char *what)
{
    printf("  [%s] %s\n", condition ? "OK" : "FAIL", what);
    if (!condition)
        failures++;
}

int main(void)
{
    /* --- 1. exported helper: version string parsing ------------------- */
    int major = -1, minor = -1, micro = -1;
    cairo_dock_get_version_from_string("3.5.0", &major, &minor, &micro);
    printf("cairo_dock_get_version_from_string(\"3.5.0\") -> %d.%d.%d\n",
           major, minor, micro);
    check(major == 3 && minor == 5 && micro == 0,
          "version helper parses 3.5.0 into 3/5/0");

    /* Partial version strings must not crash nor invent numbers. */
    major = -1; minor = -1; micro = -1;
    cairo_dock_get_version_from_string("2.4", &major, &minor, &micro);
    check(major == 2 && minor == 4 && micro == -1,
          "version helper leaves the missing micro component untouched");

    /* --- 2. exported helper: token containment ------------------------ */
    gboolean found = cairo_dock_string_contains("cairo opengl wayland", "opengl", " ");
    check(found == TRUE, "token helper finds 'opengl' in a space separated list");
    found = cairo_dock_string_contains("cairo opengl wayland", "gtk", " ");
    check(found == FALSE, "token helper rejects an absent token");

    /* --- 3. GLDI_VERSION from the packaged gldi-config.h -------------- */
    /* The header is generated at build time from CMake's VERSION; a bump of
     * the ported version must be reflected here (see test_package/conanfile.py
     * which asserts the same string in the installed header). */
    printf("GLDI_VERSION (packaged gldi-config.h) = %s\n", GLDI_VERSION);
    check(strcmp(GLDI_VERSION, "3.5.0") == 0,
          "packaged gldi-config.h reports GLDI_VERSION 3.5.0");

    if (failures) {
        fprintf(stderr, "test_cairo_dock: %d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("test_cairo_dock: libgldi consumer link + API probe OK\n");
    return 0;
}
