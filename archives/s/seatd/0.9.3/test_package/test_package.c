#include <stdio.h>
#include "libseat.h"

static void enable_seat(struct libseat *seat, void *userdata) {
    (void)seat;
    (void)userdata;
}

static void disable_seat(struct libseat *seat, void *userdata) {
    (void)userdata;
    libseat_disable_seat(seat);
}

int main(void) {
    const struct libseat_seat_listener listener = {
        .enable_seat = enable_seat,
        .disable_seat = disable_seat,
    };
    struct libseat *seat = libseat_open_seat(&listener, NULL);
    if (seat == NULL) {
        printf("seatd test OK: libseat API linked; no seat backend is available\n");
        return 0;
    }
    libseat_close_seat(seat);
    printf("seatd test OK: libseat API opened and closed a seat\n");
    return 0;
}
