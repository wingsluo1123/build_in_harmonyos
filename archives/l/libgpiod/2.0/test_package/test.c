#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <gpiod.h>

int main(void) {
    int failures = 0;

    /* Test 1: API version string */
    const char *version = gpiod_api_version();
    if (!version || strlen(version) == 0) {
        fprintf(stderr, "FAIL: gpiod_api_version() returned NULL or empty\n");
        failures++;
    } else {
        printf("libgpiod API version: %s\n", version);
        if (version[0] != '2') {
            fprintf(stderr, "FAIL: unexpected major version: %s\n", version);
            failures++;
        }
    }

    /* Test 2: Line settings allocation and configuration */
    struct gpiod_line_settings *settings = gpiod_line_settings_new();
    if (!settings) {
        fprintf(stderr, "FAIL: gpiod_line_settings_new() returned NULL\n");
        failures++;
    } else {
        /* Set direction to output and verify */
        int ret = gpiod_line_settings_set_direction(settings, GPIOD_LINE_DIRECTION_OUTPUT);
        if (ret != 0) {
            fprintf(stderr, "FAIL: gpiod_line_settings_set_direction() failed\n");
            failures++;
        } else {
            enum gpiod_line_direction dir = gpiod_line_settings_get_direction(settings);
            if (dir != GPIOD_LINE_DIRECTION_OUTPUT) {
                fprintf(stderr, "FAIL: direction mismatch: got %d, expected %d\n",
                        dir, GPIOD_LINE_DIRECTION_OUTPUT);
                failures++;
            } else {
                printf("Line settings direction: output (OK)\n");
            }
        }
        gpiod_line_settings_free(settings);
    }

    /* Test 3: GPIO chip device check on non-existent path */
    bool is_gpio = gpiod_is_gpiochip_device("/dev/nonexistent_gpio_chip");
    if (is_gpio) {
        fprintf(stderr, "FAIL: gpiod_is_gpiochip_device() returned true for non-existent device\n");
        failures++;
    } else {
        printf("Non-existent device correctly identified as non-GPIO (OK)\n");
    }

    /* Test 4: Chip open on invalid path (should fail gracefully) */
    struct gpiod_chip *chip = gpiod_chip_open("/dev/nonexistent_gpio_chip");
    if (chip != NULL) {
        fprintf(stderr, "FAIL: gpiod_chip_open() should return NULL for non-existent device\n");
        gpiod_chip_close(chip);
        failures++;
    } else {
        if (errno == 0) {
            fprintf(stderr, "WARN: errno not set after failed chip_open\n");
        }
        printf("Chip open on invalid path correctly returned NULL (OK)\n");
    }

    if (failures == 0) {
        printf("test libgpiod 2.0: ALL TESTS PASSED\n");
        return 0;
    } else {
        fprintf(stderr, "test libgpiod 2.0: %d test(s) FAILED\n", failures);
        return 1;
    }
}
