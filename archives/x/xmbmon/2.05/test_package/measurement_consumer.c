#include "measurement.h"
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    struct mbmon_measurements sample;
    errno = 0;
    if (mbmon_read_measurements(NULL) != -1 || errno != EINVAL) return 1;
    puts("PASS null-output error contract");
    for (unsigned iteration = 0; iteration < 20; ++iteration) {
        memset(&sample, 0xa5, sizeof(sample));
        if (mbmon_read_measurements(&sample) != 0 || !sample.valid_temperatures) return 2;
        for (unsigned index = 0; index < MBMON_CHANNEL_COUNT; ++index) {
            if (!(sample.valid_temperatures & (1u << index))) {
                if (!isnan(sample.temperatures[index])) return 3;
                continue;
            }
            if (!isfinite(sample.temperatures[index]) ||
                sample.temperatures[index] < -273.15f || sample.temperatures[index] > 1000.0f ||
                !sample.labels[index][0] || !memchr(sample.labels[index], 0, MBMON_LABEL_SIZE)) return 4;
            if (!iteration) printf("CHANNEL %u %s %.3f Celsius\n", index,
                sample.labels[index], sample.temperatures[index]);
        }
    }
    puts("PASS 20 native service snapshots with validity, names and Celsius values");
    printf("BACKEND %s\n", mbmon_measurement_backend());
    return 0;
}
