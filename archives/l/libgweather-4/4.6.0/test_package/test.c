/* Consumer test for libgweather-4 4.6.0 (GWeather public API).
 *
 * Exercises the pure-local public API surface, mirroring the assertions
 * of upstream's tests/test_libgweather.c (test_no_code_serialize,
 * test_utc_sunset) without internal headers:
 *   - version macros
 *   - world locations DB load (Locations.bin via LIBGWEATHER_LOCATIONS_PATH)
 *   - nearest-city lookup (Eiffel Tower coords -> Paris)
 *   - timezone resolution for a city
 *   - METAR-free sun computation with providers disabled (no network)
 *   - location serialize/deserialize round-trip
 *
 * Runtime env (set by test_package/conanfile.py): LIBGWEATHER_LOCATIONS_PATH,
 * GSETTINGS_SCHEMA_DIR (compiled org.gnome.GWeather4 schema).
 */
#include <libgweather/gweather.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (cond) {                                             \
            printf("PASS: %s\n", msg);                          \
        } else {                                                \
            printf("FAIL: %s\n", msg);                          \
            failures++;                                         \
        }                                                       \
    } while (0)

int main(void)
{
    /* Test 1: version macros */
    printf("version: %u.%u.%u (expect 4.6.0)\n",
           GWEATHER_MAJOR_VERSION, GWEATHER_MINOR_VERSION, GWEATHER_MICRO_VERSION);
    CHECK(GWEATHER_MAJOR_VERSION == 4 && GWEATHER_MINOR_VERSION == 6
              && GWEATHER_MICRO_VERSION == 0,
          "version macros are 4.6.0");
    CHECK(GWEATHER_CHECK_VERSION(4, 6, 0), "GWEATHER_CHECK_VERSION(4,6,0)");

    /* Test 2: world locations DB loads */
    GWeatherLocation *world = gweather_location_get_world();
    CHECK(world != NULL, "gweather_location_get_world returns the world");
    GWeatherLocation *first = world ? gweather_location_next_child(world, NULL) : NULL;
    CHECK(first != NULL, "world has children (regions)");
    if (first)
        g_object_unref(first);

    /* Test 3: nearest-city lookup (upstream asserts Izhevsk for its coords;
     * Eiffel Tower coords must land on Paris) */
    GWeatherLocation *city =
        gweather_location_find_nearest_city(world, 48.858370, 2.294481);
    CHECK(city != NULL, "find_nearest_city(Eiffel Tower) returns a city");
    const char *cname = city ? gweather_location_get_name(city) : NULL;
    printf("nearest city: %s (expect Paris)\n", cname ? cname : "(null)");
    CHECK(cname && strcmp(cname, "Paris") == 0, "nearest city is Paris");
    CHECK(city && gweather_location_get_level(city) >= GWEATHER_LOCATION_CITY,
          "returned location level is CITY or deeper");

    /* Test 4: timezone resolution (4.x public API returns GLib GTimeZone) */
    GTimeZone *tz = city ? gweather_location_get_timezone(city) : NULL;
    const char *tzname = tz ? g_time_zone_get_identifier(tz) : NULL;
    printf("city timezone: %s\n", tzname ? tzname : "(null)");
    CHECK(tz != NULL && tzname != NULL, "city timezone resolves with a name");

    /* Test 5: station-code lookup + local sun computation (providers
     * disabled, mirroring upstream test_utc_sunset) */
    GWeatherLocation *utc = gweather_location_find_by_station_code(world, "@UTC");
    CHECK(utc != NULL, "find_by_station_code(@UTC) resolves");
    GWeatherInfo *info = utc ? gweather_info_new(utc) : NULL;
    CHECK(info != NULL, "gweather_info_new(@UTC)");
    if (info) {
        gweather_info_set_enabled_providers(info, GWEATHER_PROVIDER_NONE);
        gweather_info_update(info);
        char *sunset = gweather_info_get_sunset(info);
        printf("sunset: %s\n", sunset ? sunset : "(null)");
        CHECK(sunset != NULL, "sunset computed locally without providers");
        g_free(sunset);
        g_object_unref(info);
    }

    /* Test 6: serialize/deserialize round-trip (upstream
     * test_no_code_serialize surface) */
    GVariant *variant = city ? gweather_location_serialize(city) : NULL;
    CHECK(variant != NULL, "location serializes to GVariant");
    if (variant) {
        GWeatherLocation *back = gweather_location_deserialize(world, variant);
        CHECK(back != NULL, "deserialized location is non-NULL");
        CHECK(back && gweather_location_equal(city, back),
              "serialize/deserialize round-trip is equal");
        if (back)
            g_object_unref(back);
        g_variant_unref(variant);
    }

    if (city)
        g_object_unref(city);
    if (world)
        g_object_unref(world);

    if (failures == 0) {
        printf("ALL PASS\n");
        return 0;
    }
    printf("FAILED: %d\n", failures);
    return 1;
}
