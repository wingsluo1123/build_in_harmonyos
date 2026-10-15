/* test_libgweather4.c — consumer-side round-trip against the packaged library.
 *
 * Exercises the parts of the API surface that do NOT need geocode-glib: the
 * location database (Locations.bin), nearest-city search by distance, the
 * country tree, and the forecast object lifecycle.  The degraded scope of this
 * port is gweather_location_detect_nearest_city() only, which is checked
 * separately in test_detect_degraded.c.
 *
 * The point of the distance assertions is that they exercise the GVariant
 * database we generated at build time: a malformed blob would not load at all,
 * and a blob missing the coordinates or timezone children would resolve the
 * wrong city or report no timezone.  So the checks below are deliberately
 * specific (Australia/Sydney, Europe/London) rather than just non-NULL.
 */
#include <glib.h>
/* The package installs headers to include/libgweather-4.0/libgweather/ (meson
 * derives that from libgweather_api_version), and upstream's own gweather.pc
 * advertises `subdirs: libgweather_full_version`, so the supported include
 * form is <libgweather/gweather.h> with include/libgweather-4.0 on the path. */
#include <libgweather/gweather.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, fmt, ...)                                              \
    do {                                                                   \
        if (cond) {                                                        \
            g_print ("ok   - " fmt "\n", ##__VA_ARGS__);                   \
        } else {                                                           \
            g_print ("FAIL - " fmt "\n", ##__VA_ARGS__);                   \
            failures++;                                                    \
        }                                                                  \
    } while (0)

/* Round-trip 1: the packaged Locations.bin loads at all, and the world node
 * has the properties the database format defines for it. */
static void
test_world_lookup (void)
{
    GWeatherLocation *world = gweather_location_get_world ();
    const char *name;

    CHECK (world != NULL, "world location loaded from the packaged Locations.bin");
    if (world == NULL)
        return;

    /* The world node is the <gweather> root of Locations.xml, and that element
     * carries no name (its only attributes are format="1.0"; its children are
     * named-timezone/region).  gen_locations_variant.py's get_name() therefore
     * yields ('', '') for it, and gweather_location_get_name() maps the empty
     * string to NULL via EMPTY_TO_NULL (gweather-location.c:296).  Upstream's
     * own suite agrees: it asserts g_assert_nonnull(world) and nothing about a
     * world name.  So NULL is the CORRECT answer here — assert it, and do it
     * without feeding it to g_ascii_strcasecmp, whose NULL precondition aborts
     * the process with GLib-FATAL-CRITICAL (that is how this was first found). */
    name = gweather_location_get_name (world);
    CHECK (name == NULL, "world node has no name (got '%s')", name ? name : "(null)");

    CHECK (gweather_location_get_level (world) == GWEATHER_LOCATION_WORLD,
           "world level is GWEATHER_LOCATION_WORLD (%d)",
           (int) gweather_location_get_level (world));
    CHECK (gweather_location_has_coords (world) == FALSE,
           "world has no coordinates");

    g_object_unref (world);
}

/* Round-trip 2: nearest-city search by distance.  This is the real consumer
 * path (libgnome-desktop's weather popup picks a city this way) and it walks
 * the whole location tree, so it only succeeds if the generated database is
 * correct. */
static void
test_nearest_city_by_distance (void)
{
    GWeatherLocation *world = gweather_location_get_world ();
    GWeatherLocation *near;
    double lat = 0.0, lon = 0.0;
    const char *tz;

    if (world == NULL) {
        CHECK (FALSE, "world location loaded");
        return;
    }

    /* Sydney Opera House. */
    near = gweather_location_find_nearest_city (world, -33.8568, 151.2153);
    CHECK (near != NULL, "find_nearest_city resolved a city near Sydney");
    if (near == NULL) {
        g_object_unref (world);
        return;
    }

    CHECK (gweather_location_get_level (near) >= GWEATHER_LOCATION_CITY,
           "resolved level >= CITY (%d)", (int) gweather_location_get_level (near));
    CHECK (gweather_location_has_coords (near),
           "resolved city has coordinates");

    gweather_location_get_coords (near, &lat, &lon);
    CHECK (fabs (lat + 33.86) < 1.0, "latitude is near Sydney (%.3f)", lat);
    CHECK (fabs (lon - 151.21) < 1.0, "longitude is near Sydney (%.3f)", lon);

    /* The nested timezones array is the part of the blob that a tuple/dict-entry
     * mistake would most likely corrupt, so assert the real zone name. */
    tz = gweather_location_get_timezone_str (near);
    CHECK (tz != NULL && strcmp (tz, "Australia/Sydney") == 0,
           "timezone is Australia/Sydney (got '%s')", tz ? tz : "(null)");

    CHECK (gweather_location_get_country (near) != NULL,
           "resolved city reports a country ('%s')",
           gweather_location_get_country (near) ? gweather_location_get_country (near) : "(null)");

    g_object_unref (near);
    g_object_unref (world);
}

/* Round-trip 3: the same search on the other side of the world, so a blob that
 * happened to work for one hemisphere cannot pass. */
static void
test_nearest_city_london (void)
{
    GWeatherLocation *world = gweather_location_get_world ();
    GWeatherLocation *near;
    double lat = 0.0, lon = 0.0;
    const char *tz;

    if (world == NULL) {
        CHECK (FALSE, "world location loaded");
        return;
    }

    near = gweather_location_find_nearest_city (world, 51.5072, -0.1276);
    CHECK (near != NULL, "find_nearest_city resolved a city near London");
    if (near == NULL) {
        g_object_unref (world);
        return;
    }

    gweather_location_get_coords (near, &lat, &lon);
    CHECK (fabs (lat - 51.5) < 1.5, "latitude is near London (%.3f)", lat);
    CHECK (fabs (lon + 0.12) < 1.5, "longitude is near London (%.3f)", lon);

    tz = gweather_location_get_timezone_str (near);
    CHECK (tz != NULL && strcmp (tz, "Europe/London") == 0,
           "timezone is Europe/London (got '%s')", tz ? tz : "(null)");

    g_object_unref (near);
    g_object_unref (world);
}

/* Round-trip 4: walk the location tree with next_child().  This proves the
 * {sq} country index and the a{...} child arrays are populated, and gives a
 * count that a truncated blob cannot fake.
 *
 * Level note (learned from a real failure): the world's DIRECT children are
 * <region> nodes, not <country> — Locations.xml nests every <country> inside one
 * of the 9 <region> elements (9 regions vs 245 countries in the shipped XML,
 * and gen_locations_variant.py maps them to levels 1 and 2 respectively).  So
 * the world level yields regions, and a second next_child() hop yields the
 * countries.  Asserting ">100 countries" at the world level counted regions
 * (11) and failed. */
static void
test_location_tree (void)
{
    GWeatherLocation *world = gweather_location_get_world ();
    GWeatherLocation *region, *country;
    guint n_regions = 0, n_countries = 0, n_with_cities = 0;

    if (world == NULL) {
        CHECK (FALSE, "world location loaded");
        return;
    }

    region = NULL;
    while ((region = gweather_location_next_child (world, region)) != NULL) {
        if (gweather_location_get_level (region) != GWEATHER_LOCATION_REGION) {
            g_print ("     unexpected world child level %d ('%s')\n",
                     (int) gweather_location_get_level (region),
                     gweather_location_get_name (region) ? "(noname)" : "(noname)");
            continue;
        }
        n_regions++;
        country = NULL;
        while ((country = gweather_location_next_child (region, country)) != NULL) {
            if (gweather_location_get_level (country) != GWEATHER_LOCATION_COUNTRY)
                continue;
            n_countries++;
            /* A country with at least one city proves the city index inside the
             * country record resolved, not just the country's own entry. */
            if (gweather_location_find_nearest_city (country,
                                                     0.0, 0.0) != NULL ||
                gweather_location_next_child (country, NULL) != NULL)
                n_with_cities++;
        }
    }

    g_print ("     regions=%u countries=%u with-children=%u\n",
             n_regions, n_countries, n_with_cities);
    CHECK (n_regions >= 9, "at least 9 regions present (got %u)", n_regions);
    CHECK (n_countries > 200, "at least 200 countries present (got %u)", n_countries);
    CHECK (n_with_cities > 100,
           "at least 100 countries have children (got %u)", n_with_cities);

    g_object_unref (world);
}

/* Round-trip 5: forecast object lifecycle (the main consumers API). */
static void
test_forecast_objects (void)
{
    GWeatherLocation *world = gweather_location_get_world ();
    GWeatherLocation *near;
    GWeatherInfo *info;
    char *name = NULL;

    if (world == NULL) {
        CHECK (FALSE, "world location loaded");
        return;
    }

    near = gweather_location_find_nearest_city (world, 52.52, 13.405);
    if (near == NULL) {
        CHECK (FALSE, "find_nearest_city resolved a city near Berlin");
        g_object_unref (world);
        return;
    }

    info = gweather_info_new (near);
    CHECK (info != NULL, "GWeatherInfo created for the resolved location");
    if (info != NULL) {
        CHECK (gweather_info_get_location (info) == near,
               "GWeatherInfo round-trips its location");
        CHECK (gweather_info_is_valid (info) == FALSE,
               "a freshly created GWeatherInfo has no forecast data yet");
        name = gweather_info_get_location_name (info);
        CHECK (name != NULL && *name != '\0',
               "GWeatherInfo reports a location name ('%s')", name ? name : "(null)");
        g_free (name);
        g_object_unref (info);
    }

    g_object_unref (near);
    g_object_unref (world);
}

int
main (int argc, char **argv)
{
    g_test_init (&argc, &argv, NULL);

    g_print ("# libgweather4 consumer test\n");
    g_print ("# version: %d.%d.%d\n",
             GWEATHER_MAJOR_VERSION, GWEATHER_MINOR_VERSION,
             GWEATHER_MICRO_VERSION);

    test_world_lookup ();
    test_nearest_city_by_distance ();
    test_nearest_city_london ();
    test_location_tree ();
    test_forecast_objects ();

    g_print ("# failures: %d\n", failures);
    return failures == 0 ? 0 : 1;
}
